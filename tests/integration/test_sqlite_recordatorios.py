"""Pruebas de integración real con SQLite 3 en modo WAL (migraciones, repositorios, reconciliación)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from agenda_app.application.ports.notificaciones import (
    CallbackInteraccion,
    CapacidadesNotificacionSO,
    SolicitudNotificacion,
)
from agenda_app.container import construir_contenedor_notificaciones
from agenda_app.domain.entities.recordatorio import Recordatorio
from agenda_app.domain.enums import (
    EstadoRecordatorio,
    PlataformaSO,
    TipoOrigenRecordatorio,
)
from agenda_app.infrastructure.persistence.sqlite.database import SQLiteDatabase
from agenda_app.infrastructure.persistence.sqlite.migrations import aplicar_migraciones


class FixedClock:
    def __init__(self, dt: datetime) -> None:
        self.dt = dt

    def ahora_utc(self) -> datetime:
        return self.dt


class DummyAdapter:
    def __init__(self) -> None:
        self.programadas: list[SolicitudNotificacion] = []
        self.canceladas: list[int] = []

    async def obtener_capacidades(self) -> CapacidadesNotificacionSO:
        return CapacidadesNotificacionSO(
            plataforma=PlataformaSO.LINUX,
            soporta_programacion_nativa=False,
            soporta_acciones_rapidas=True,
        )

    async def solicitar_permisos(self) -> bool:
        return True

    async def puede_programar_exacto(self) -> bool:
        return True

    async def programar(self, solicitud: SolicitudNotificacion) -> None:
        self.programadas.append(solicitud)

    async def cancelar(self, id_notificacion_so: int) -> None:
        self.canceladas.append(id_notificacion_so)

    async def mostrar_inmediata(self, solicitud: SolicitudNotificacion) -> None:
        self.programadas.append(solicitud)

    def registrar_callbacks(
        self,
        on_tap: CallbackInteraccion | None = None,
        on_action: CallbackInteraccion | None = None,
    ) -> None:
        pass


@pytest.mark.asyncio
async def test_flujo_completo_sqlite_wal_y_reconciliacion(tmp_path: Path) -> None:
    db_file = tmp_path / "agenda_test.db"
    reloj = FixedClock(datetime(2026, 11, 23, 18, 0, tzinfo=timezone.utc))
    adaptador = DummyAdapter()

    contenedor = construir_contenedor_notificaciones(
        db_path=db_file,
        reloj=reloj,
        adaptador_personalizado=adaptador,
    )

    # Migraciones idempotentes: una segunda llamada no vuelve a aplicar la versión 1
    assert aplicar_migraciones(contenedor.db) == []

    # Verifica modo WAL real en disco (crítico para concurrencia App + Worker Linux)
    with contenedor.db.transaccion() as conn:
        modo = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        assert str(modo).lower() == "wal"

        # Insertamos un evento y una tarea reales para respetar FK estrictas
        ev_id = uuid4()
        tar_id = uuid4()
        now_iso = "2026-11-23T18:00:00.000000Z"
        conn.execute(
            "INSERT INTO eventos (id, titulo, descripcion, fecha_inicio, created_at, updated_at) "
            "VALUES (?, 'Parcial BD', 'Sala B', '2026-11-23T20:00:00Z', ?, ?)",
            (str(ev_id), now_iso, now_iso),
        )
        conn.execute(
            "INSERT INTO tareas (id, titulo, descripcion, fecha_limite, created_at, updated_at) "
            "VALUES (?, 'Entrega Diseño', 'Subir diagramas', '2026-11-24T18:00:00Z', ?, ?)",
            (str(tar_id), now_iso, now_iso),
        )

    # Programamos un recordatorio de evento (+1h) y uno de tarea (+12h)
    rec_ev = await contenedor.motor.programar_o_reprogramar(
        tipo_origen=TipoOrigenRecordatorio.EVENTO,
        item_id=ev_id,
        titulo="Parcial BD",
        cuerpo="Sala B",
        fecha_objetivo=reloj.dt + timedelta(hours=2),
        antelacion_minutos=60,
    )
    rec_tar = await contenedor.motor.programar_o_reprogramar(
        tipo_origen=TipoOrigenRecordatorio.TAREA,
        item_id=tar_id,
        titulo="Entrega Diseño",
        cuerpo="Subir diagramas",
        fecha_objetivo=reloj.dt + timedelta(hours=12),
        antelacion_minutos=30,
    )

    # Simular lectura concurrente desde segunda conexión (ej. worker systemd Linux)
    db_worker = SQLiteDatabase(db_file)
    with db_worker.transaccion() as conn2:
        total = conn2.execute("SELECT COUNT(*) FROM recordatorios").fetchone()[0]
        assert total == 2

    # Avanzar reloj 2 horas -> rec_ev queda vencido/perdido, rec_tar sigue pendiente futuro
    reloj.dt = reloj.dt + timedelta(hours=2)
    adaptador.programadas.clear()
    res = await contenedor.reconciliador.reconciliar()

    assert [r.id for r in res.perdidos_detectados] == [rec_ev.id]
    assert res.reprogramados_en_so == 1
    assert adaptador.programadas[0].titulo == "Entrega Diseño"
    assert adaptador.programadas[0].cuerpo == "Subir diagramas"

    # Persistir cambio de Ajustes (RN-14) y verificar recarga desde disco
    ajustes = contenedor.repo_ajustes.obtener()
    ajustes.minutos_posponer_defecto = 20
    contenedor.repo_ajustes.guardar(ajustes)
    assert contenedor.repo_ajustes.obtener().minutos_posponer_defecto == 20

    # Posponer rec_ev y confirmar estado POSPUESTO +20 min en SQLite
    pospuesto = await contenedor.motor.posponer_recordatorio(rec_ev.id)
    assert pospuesto is not None
    assert pospuesto.estado == EstadoRecordatorio.POSPUESTO
    assert pospuesto.fecha_disparo == reloj.dt + timedelta(minutes=20)
    assert isinstance(contenedor.repo_recordatorios.obtener_por_id(rec_ev.id), Recordatorio)

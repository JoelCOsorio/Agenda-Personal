"""Pruebas unitarias de MotorNotificaciones y StartupReconciler con dobles en memoria."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from agenda_app.application.ports.notificaciones import (
    ACCION_COMPLETAR_TAREA,
    ACCION_MARCAR_VISTO,
    ACCION_POSPONER,
    CallbackInteraccion,
    CapacidadesNotificacionSO,
    ContenidoNotificacion,
    EventoInteraccionNotificacion,
    SolicitudNotificacion,
)
from agenda_app.application.services.motor_notificaciones import MotorNotificaciones
from agenda_app.application.services.startup_reconciler import StartupReconciler
from agenda_app.domain.entities.configuracion import ConfiguracionSistema
from agenda_app.domain.entities.recordatorio import Recordatorio
from agenda_app.domain.enums import (
    EstadoRecordatorio,
    PlataformaSO,
    TipoOrigenRecordatorio,
)
from agenda_app.domain.rules.recordatorio_rules import ValidadorRecordatorio


class FakeClock:
    def __init__(self, actual: datetime) -> None:
        self._actual = actual

    def ahora_utc(self) -> datetime:
        return self._actual

    def avanzar(self, delta: timedelta) -> None:
        self._actual += delta


class InMemoryRepoRecordatorios:
    def __init__(self) -> None:
        self._datos: dict[UUID, Recordatorio] = {}
        self._seq = 0

    def guardar(self, recordatorio: Recordatorio) -> None:
        self._datos[recordatorio.id] = recordatorio

    def obtener_por_id(self, recordatorio_id: UUID) -> Recordatorio | None:
        return self._datos.get(recordatorio_id)

    def obtener_por_item(
        self, tipo_origen: TipoOrigenRecordatorio, item_id: UUID
    ) -> Recordatorio | None:
        for rec in self._datos.values():
            if rec.tipo_origen == tipo_origen and rec.item_id == item_id:
                return rec
        return None

    def obtener_pendientes_vencidos(self, ahora: datetime) -> list[Recordatorio]:
        return sorted(
            [r for r in self._datos.values() if r.esta_activo and r.fecha_disparo < ahora],
            key=lambda r: r.fecha_disparo,
        )

    def obtener_pendientes_futuros(
        self, ahora: datetime, hasta: datetime | None = None, limite: int = 200
    ) -> list[Recordatorio]:
        res = [
            r
            for r in self._datos.values()
            if r.esta_activo
            and r.fecha_disparo >= ahora
            and (hasta is None or r.fecha_disparo <= hasta)
        ]
        res.sort(key=lambda r: r.fecha_disparo)
        return res[:limite]

    def obtener_perdidos(self) -> list[Recordatorio]:
        return [r for r in self._datos.values() if r.estado == EstadoRecordatorio.PERDIDO]

    def siguiente_id_notificacion_so(self) -> int:
        self._seq += 1
        return self._seq

    def eliminar(self, recordatorio_id: UUID) -> None:
        self._datos.pop(recordatorio_id, None)


class InMemoryRepoAjustes:
    def __init__(self, config: ConfiguracionSistema | None = None) -> None:
        self._config = config or ConfiguracionSistema()

    def obtener(self) -> ConfiguracionSistema:
        return self._config

    def guardar(self, configuracion: ConfiguracionSistema) -> None:
        self._config = configuracion


class FakeNotificationAdapter:
    def __init__(
        self,
        *,
        plataforma: PlataformaSO = PlataformaSO.LINUX,
        soporta_acciones: bool = True,
        exactas: bool = True,
    ) -> None:
        self.plataforma = plataforma
        self.soporta_acciones = soporta_acciones
        self.exactas = exactas
        self.programadas: list[SolicitudNotificacion] = []
        self.canceladas: list[int] = []
        self.on_tap: CallbackInteraccion | None = None
        self.on_action: CallbackInteraccion | None = None

    async def obtener_capacidades(self) -> CapacidadesNotificacionSO:
        return CapacidadesNotificacionSO(
            plataforma=self.plataforma,
            soporta_programacion_nativa=self.plataforma != PlataformaSO.LINUX,
            soporta_acciones_rapidas=self.soporta_acciones,
            soporta_alarmas_exactas=self.exactas,
        )

    async def solicitar_permisos(self) -> bool:
        return True

    async def puede_programar_exacto(self) -> bool:
        return self.exactas

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
        self.on_tap = on_tap
        self.on_action = on_action


class FakeProveedorContenido:
    def obtener_contenido(
        self, tipo_origen: TipoOrigenRecordatorio, item_id: UUID
    ) -> ContenidoNotificacion | None:
        return ContenidoNotificacion(titulo="Examen Final", cuerpo="Aula 204")


@pytest.mark.asyncio
async def test_programar_reprogramar_y_cancelar_cumple_rn02_y_rn12() -> None:
    reloj = FakeClock(datetime(2026, 11, 23, 18, 0, tzinfo=timezone.utc))
    repo_rec = InMemoryRepoRecordatorios()
    repo_aj = InMemoryRepoAjustes()
    adaptador = FakeNotificationAdapter(soporta_acciones=True)
    motor = MotorNotificaciones(repo_rec, repo_aj, adaptador, reloj)

    ev_id = uuid4()
    rec1 = await motor.programar_o_reprogramar(
        tipo_origen=TipoOrigenRecordatorio.EVENTO,
        item_id=ev_id,
        titulo="Clase",
        cuerpo="Cálculo",
        fecha_objetivo=reloj.ahora_utc() + timedelta(hours=2),
        antelacion_minutos=30,
    )
    assert rec1.id_notificacion_so == 1
    assert len(adaptador.programadas) == 1
    assert len(adaptador.canceladas) == 0

    # Reprogramar el mismo evento debe cancelar el aviso previo y reutilizar la entidad (RN-02)
    rec2 = await motor.programar_o_reprogramar(
        tipo_origen=TipoOrigenRecordatorio.EVENTO,
        item_id=ev_id,
        titulo="Clase",
        cuerpo="Cálculo (nueva hora)",
        fecha_objetivo=reloj.ahora_utc() + timedelta(hours=4),
        antelacion_minutos=60,
    )
    assert rec2.id == rec1.id
    assert adaptador.canceladas == [1]
    assert len(adaptador.programadas) == 2

    # Cancelar (por eliminación o tarea completada RN-12)
    ok = await motor.cancelar_por_item(TipoOrigenRecordatorio.EVENTO, ev_id)
    assert ok is True
    assert rec2.estado == EstadoRecordatorio.CANCELADO
    assert adaptador.canceladas == [1, 1]


@pytest.mark.asyncio
async def test_posponer_usa_minutos_de_ajustes_y_degradacion_rn06() -> None:
    reloj = FakeClock(datetime(2026, 11, 23, 18, 0, tzinfo=timezone.utc))
    repo_rec = InMemoryRepoRecordatorios()
    ajustes = ConfiguracionSistema(minutos_posponer_defecto=25)
    repo_aj = InMemoryRepoAjustes(ajustes)

    # Caso A: SO SIN acciones rápidas -> degrada a tuple vacía (RN-06)
    adaptador_sin_botones = FakeNotificationAdapter(soporta_acciones=False)
    motor_sin = MotorNotificaciones(
        repo_rec, repo_aj, adaptador_sin_botones, reloj, FakeProveedorContenido()
    )
    tar_id = uuid4()
    rec = await motor_sin.programar_o_reprogramar(
        tipo_origen=TipoOrigenRecordatorio.TAREA,
        item_id=tar_id,
        titulo="Entregar proyecto",
        cuerpo="Subir PDF",
        fecha_objetivo=reloj.ahora_utc() + timedelta(hours=3),
        antelacion_minutos=15,
    )
    assert adaptador_sin_botones.programadas[0].acciones == ()

    # Caso B: SO CON acciones rápidas -> pulsar Posponer usa 25 min de Ajustes (RN-14)
    completadas: list[UUID] = []

    async def on_completar(tid: UUID) -> None:
        completadas.append(tid)

    adaptador_con_botones = FakeNotificationAdapter(soporta_acciones=True)
    motor_con = MotorNotificaciones(
        repo_rec,
        repo_aj,
        adaptador_con_botones,
        reloj,
        FakeProveedorContenido(),
        on_completar_tarea=on_completar,
    )

    payload = ValidadorRecordatorio.construir_payload(rec)
    reloj.avanzar(timedelta(hours=2, minutes=45))
    await motor_con.procesar_accion_rapida(
        EventoInteraccionNotificacion(payload=payload, action_id=ACCION_POSPONER)
    )

    actualizado = repo_rec.obtener_por_id(rec.id)
    assert actualizado is not None
    assert actualizado.estado == EstadoRecordatorio.POSPUESTO
    assert actualizado.fecha_disparo == reloj.ahora_utc() + timedelta(minutes=25)
    ids_botones = {a.id for a in adaptador_con_botones.programadas[-1].acciones}
    assert ids_botones == {ACCION_POSPONER, ACCION_MARCAR_VISTO, ACCION_COMPLETAR_TAREA}

    # Pulsar Completar tarea dispara callback de dominio y marca atendido
    await motor_con.procesar_accion_rapida(
        EventoInteraccionNotificacion(payload=payload, action_id=ACCION_COMPLETAR_TAREA)
    )
    assert completadas == [tar_id]
    assert actualizado.estado == EstadoRecordatorio.ATENDIDO


@pytest.mark.asyncio
async def test_startup_reconciler_detecta_perdidas_y_reprograma_futuros_rn05() -> None:
    reloj = FakeClock(datetime(2026, 11, 23, 18, 0, tzinfo=timezone.utc))
    repo_rec = InMemoryRepoRecordatorios()
    repo_aj = InMemoryRepoAjustes(ConfiguracionSistema(mostrar_alertas_perdidas_inicio=True))
    adaptador = FakeNotificationAdapter(soporta_acciones=True)
    motor = MotorNotificaciones(repo_rec, repo_aj, adaptador, reloj, FakeProveedorContenido())
    reconciliador = StartupReconciler(repo_rec, repo_aj, motor, adaptador, reloj)

    # Programamos uno a +1h y otro a +5h
    rec_1h = await motor.programar_o_reprogramar(
        tipo_origen=TipoOrigenRecordatorio.EVENTO,
        item_id=uuid4(),
        titulo="Reunión",
        cuerpo="Zoom",
        fecha_objetivo=reloj.ahora_utc() + timedelta(hours=1),
        antelacion_minutos=0,
    )
    rec_5h = await motor.programar_o_reprogramar(
        tipo_origen=TipoOrigenRecordatorio.TAREA,
        item_id=uuid4(),
        titulo="Ensayo",
        cuerpo="Entregar",
        fecha_objetivo=reloj.ahora_utc() + timedelta(hours=5),
        antelacion_minutos=0,
    )

    # Simulamos que el equipo estuvo apagado 2 horas
    adaptador.programadas.clear()
    reloj.avanzar(timedelta(hours=2))

    resultado = await reconciliador.reconciliar()
    assert [r.id for r in resultado.perdidos_detectados] == [rec_1h.id]
    assert rec_1h.estado == EstadoRecordatorio.PERDIDO
    assert rec_5h.estado == EstadoRecordatorio.PENDIENTE
    assert resultado.mostrar_aviso_perdidos is True
    assert resultado.reprogramados_en_so == 1
    assert adaptador.programadas[0].id_notificacion_so == rec_5h.id_notificacion_so

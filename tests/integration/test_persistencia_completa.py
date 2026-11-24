"""Pruebas de integración completa sobre SQLite 3 real en disco (WAL + FK estrictas)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agenda_app.application.ports.notificaciones import (
    ACCION_COMPLETAR_TAREA,
    CallbackInteraccion,
    CapacidadesNotificacionSO,
    EventoInteraccionNotificacion,
    SolicitudNotificacion,
)
from agenda_app.container import construir_contenedor_aplicacion
from agenda_app.domain.entities.evento import ReglaRecurrencia
from agenda_app.domain.enums import (
    EstadoRecordatorio,
    EstadoTarea,
    PlataformaSO,
    PrioridadTarea,
    TipoFrecuencia,
    TipoOrigenRecordatorio,
    VistaAgenda,
)
from agenda_app.domain.rules.recordatorio_rules import ValidadorRecordatorio


class FixedClock:
    def __init__(self, dt: datetime) -> None:
        self.dt = dt

    def ahora_utc(self) -> datetime:
        return self.dt


class StubAdapter:
    def __init__(self) -> None:
        self.programadas: list[SolicitudNotificacion] = []
        self.canceladas: list[int] = []
        self.on_action: CallbackInteraccion | None = None

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
        self.on_action = on_action


@pytest.mark.asyncio
async def test_persistencia_completa_integridad_rn13_y_callback_notificacion(tmp_path: Path) -> None:
    db_file = tmp_path / "agenda_full.db"
    reloj = FixedClock(datetime(2026, 11, 23, 18, 0, tzinfo=timezone.utc))
    adaptador = StubAdapter()

    app = construir_contenedor_aplicacion(
        db_path=db_file,
        reloj=reloj,
        adaptador_personalizado=adaptador,
    )

    # 1. Crear Categoría + Subcategorías + Contacto
    cat_uni = app.servicio_categorias.crear_categoria(nombre="Universidad", color_hex="#2563EB")
    sub_ing = app.servicio_categorias.crear_subcategoria(
        categoria_id=cat_uni.id, nombre="Ingeniería de Software"
    )
    sub_bd = app.servicio_categorias.crear_subcategoria(
        categoria_id=cat_uni.id, nombre="Bases de Datos"
    )
    profe = app.servicio_contactos.crear_contacto(
        nombre="Dra. Morales", correo="morales@uni.edu", etiqueta="Profesor"
    )

    # 2. Crear Evento recurrente vinculado a categoría, subcategoría, contacto y recordatorio
    evento = await app.servicio_eventos.crear_evento(
        titulo="Clase de Arquitectura",
        fecha_inicio=reloj.dt + timedelta(hours=2),
        fecha_fin=reloj.dt + timedelta(hours=4),
        categoria_id=cat_uni.id,
        subcategoria_id=sub_ing.id,
        contacto_ids=[profe.id],
        recurrencia=ReglaRecurrencia(
            frecuencia=TipoFrecuencia.SEMANAL,
            intervalo=1,
            dias_semana=("LU", "MI"),
            max_ocurrencias=4,
        ),
        recordatorio_antelacion_min=15,
    )

    # 3. Crear Tarea vinculada a categoría, subcategoría, contacto y recordatorio
    tarea = await app.servicio_tareas.crear_tarea(
        titulo="Implementar repositorios SQLite",
        fecha_limite=reloj.dt + timedelta(hours=10),
        prioridad=PrioridadTarea.ALTA,
        categoria_id=cat_uni.id,
        subcategoria_id=sub_bd.id,
        contacto_ids=[profe.id],
        recordatorio_antelacion_min=30,
    )

    # Verificar vistas con expansión de recurrencias (PROC-02)
    ocurrencias = app.servicio_eventos.obtener_ocurrencias_vista(
        reloj.dt,
        reloj.dt + timedelta(days=14),
        categoria_id=cat_uni.id,
    )
    assert len(ocurrencias) == 4

    # 4. RN-13: Eliminar contacto desvincula sin borrar el evento ni la tarea
    app.servicio_contactos.eliminar_contacto(profe.id)
    ev_reload = app.servicio_eventos.obtener_evento(evento.id)
    tar_reload = app.servicio_tareas.obtener_tarea(tarea.id)
    assert ev_reload is not None and ev_reload.contacto_ids == ()
    assert tar_reload is not None and tar_reload.contacto_ids == ()

    # 5. RN-13: Eliminar subcategoría conserva la categoría padre en el evento
    app.servicio_categorias.eliminar_subcategoria(sub_ing.id)
    ev_reload = app.servicio_eventos.obtener_evento(evento.id)
    assert ev_reload is not None
    assert ev_reload.categoria_id == cat_uni.id
    assert ev_reload.subcategoria_id is None

    # 6. RN-13: Eliminar categoría padre deja ambos en NULL sin borrar evento ni tarea
    app.servicio_categorias.eliminar_categoria(cat_uni.id)
    ev_reload = app.servicio_eventos.obtener_evento(evento.id)
    tar_reload = app.servicio_tareas.obtener_tarea(tarea.id)
    assert ev_reload is not None and ev_reload.categoria_id is None
    assert tar_reload is not None and tar_reload.categoria_id is None and tar_reload.subcategoria_id is None

    # 7. Integración extremo a extremo: acción rápida "Completar tarea" desde notificación
    rec_tarea = app.repo_recordatorios.obtener_por_item(TipoOrigenRecordatorio.TAREA, tarea.id)
    assert rec_tarea is not None
    payload = ValidadorRecordatorio.construir_payload(rec_tarea)
    assert adaptador.on_action is not None
    await adaptador.on_action(
        EventoInteraccionNotificacion(payload=payload, action_id=ACCION_COMPLETAR_TAREA)
    )

    tar_final = app.servicio_tareas.obtener_tarea(tarea.id)
    rec_final = app.repo_recordatorios.obtener_por_id(rec_tarea.id)
    assert tar_final is not None and tar_final.estado == EstadoTarea.COMPLETADA
    assert rec_final is not None and rec_final.estado == EstadoRecordatorio.CANCELADO

    # 8. Ajustes: actualizar y restablecer valores por defecto (RF-23, RF-24)
    app.servicio_ajustes.actualizar(
        minutos_posponer_defecto=30,
        vista_inicial_agenda=VistaAgenda.SEMANA,
        tema_oscuro=True,
    )
    assert app.servicio_ajustes.obtener().tema_oscuro is True
    app.servicio_ajustes.restablecer_defaults()
    cfg = app.servicio_ajustes.obtener()
    assert cfg.minutos_posponer_defecto == 10
    assert cfg.vista_inicial_agenda == VistaAgenda.MES
    assert cfg.tema_oscuro is False

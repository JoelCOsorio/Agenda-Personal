"""Pruebas unitarias de servicios de dominio usando SQLite en memoria y adaptadores falsos."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agenda_app.application.ports.notificaciones import (
    CallbackInteraccion,
    CapacidadesNotificacionSO,
    SolicitudNotificacion,
)
from agenda_app.container import construir_contenedor_aplicacion
from agenda_app.domain.enums import (
    EstadoRecordatorio,
    EstadoTarea,
    PlataformaSO,
    PrioridadTarea,
    TipoOrigenRecordatorio,
)
from agenda_app.domain.exceptions import (
    AccionPlataformaNoSoportadaError,
    ChoqueEventosError,
    JerarquiaCategoriaInvalidaError,
)


class FakeClock:
    def __init__(self, dt: datetime) -> None:
        self.dt = dt

    def ahora_utc(self) -> datetime:
        return self.dt


class FakeNotifAdapter:
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


class FakeLauncher:
    def __init__(self, plataforma: PlataformaSO) -> None:
        self._plataforma = plataforma
        self.uris_abiertas: list[str] = []

    def puede_llamar(self) -> bool:
        return self._plataforma == PlataformaSO.ANDROID

    async def abrir_uri(self, uri: str) -> bool:
        self.uris_abiertas.append(uri)
        return True


def _crear_app(plataforma: PlataformaSO = PlataformaSO.LINUX):
    reloj = FakeClock(datetime(2026, 11, 23, 18, 0, tzinfo=timezone.utc))
    adaptador = FakeNotifAdapter()
    lanzador = FakeLauncher(plataforma)
    app = construir_contenedor_aplicacion(
        page_platform=plataforma.value,
        db_path=":memory:",
        reloj=reloj,
        adaptador_personalizado=adaptador,
        lanzador_personalizado=lanzador,
    )
    return app, reloj, adaptador, lanzador


@pytest.mark.asyncio
async def test_servicio_eventos_choque_reprogramacion_y_historial() -> None:
    app, reloj, adaptador, _ = _crear_app()
    try:
        ev1 = await app.servicio_eventos.crear_evento(
            titulo="Examen Parcial",
            fecha_inicio=reloj.dt + timedelta(hours=2),
            fecha_fin=reloj.dt + timedelta(hours=4),
            recordatorio_antelacion_min=30,
        )
        assert len(adaptador.programadas) == 1

        # Intentar crear evento superpuesto debe lanzar ChoqueEventosError (RN-11)
        with pytest.raises(ChoqueEventosError) as exc_info:
            await app.servicio_eventos.crear_evento(
                titulo="Choque",
                fecha_inicio=reloj.dt + timedelta(hours=3),
                fecha_fin=reloj.dt + timedelta(hours=5),
            )
        assert exc_info.value.evento_en_conflicto_id == ev1.id
        assert exc_info.value.titulo_conflicto == "Examen Parcial"

        # Editar la hora de inicio reprograma automáticamente el recordatorio (RN-02)
        await app.servicio_eventos.editar_evento(
            ev1.id,
            fecha_inicio=reloj.dt + timedelta(hours=5),
            fecha_fin=reloj.dt + timedelta(hours=7),
            actualizar_fecha_fin=True,
        )
        assert len(adaptador.canceladas) == 1
        assert len(adaptador.programadas) == 2
        assert adaptador.programadas[-1].fecha_disparo == reloj.dt + timedelta(hours=4, minutes=30)

        # Avanzar el reloj más allá del evento -> aparece en historial (RN-04)
        reloj.dt += timedelta(hours=10)
        historial = app.servicio_eventos.obtener_historial()
        assert [e.id for e in historial] == [ev1.id]
    finally:
        app.db.cerrar()


@pytest.mark.asyncio
async def test_servicio_tareas_completar_cancela_y_reactivar_reestablece_rn12() -> None:
    app, reloj, adaptador, _ = _crear_app()
    try:
        tarea = await app.servicio_tareas.crear_tarea(
            titulo="Entregar diagrama de clases",
            fecha_limite=reloj.dt + timedelta(hours=6),
            prioridad=PrioridadTarea.ALTA,
            recordatorio_antelacion_min=60,
        )
        rec = app.repo_recordatorios.obtener_por_item(TipoOrigenRecordatorio.TAREA, tarea.id)
        assert rec is not None and rec.estado == EstadoRecordatorio.PENDIENTE

        # Completar cancela el recordatorio automáticamente (RN-12)
        await app.servicio_tareas.completar_tarea(tarea.id)
        rec = app.repo_recordatorios.obtener_por_item(TipoOrigenRecordatorio.TAREA, tarea.id)
        assert rec is not None and rec.estado == EstadoRecordatorio.CANCELADO
        assert adaptador.canceladas == [rec.id_notificacion_so]

        # Reactivar con fecha aún vigente vuelve a programar el recordatorio (RN-12)
        await app.servicio_tareas.reactivar_tarea(tarea.id, nuevo_estado=EstadoTarea.EN_PROGRESO)
        rec = app.repo_recordatorios.obtener_por_item(TipoOrigenRecordatorio.TAREA, tarea.id)
        assert rec is not None and rec.estado == EstadoRecordatorio.PENDIENTE
        assert len(adaptador.programadas) == 2
    finally:
        app.db.cerrar()


@pytest.mark.asyncio
async def test_contactos_acciones_por_plataforma_rn08_y_categorias_rn09() -> None:
    # Linux: mailto OK, tel bloqueado
    app_lin, _, _, lanz_lin = _crear_app(PlataformaSO.LINUX)
    try:
        c = app_lin.servicio_contactos.crear_contacto(
            nombre="Prof. García",
            telefono="+52 55 1234 5678",
            correo="garcia@uni.edu",
            etiqueta="Profesor",
        )
        assert app_lin.servicio_contactos.puede_llamar_en_plataforma_actual(c) is False
        assert await app_lin.servicio_contactos.abrir_correo_contacto(c.id) is True
        assert lanz_lin.uris_abiertas == ["mailto:garcia@uni.edu"]

        with pytest.raises(AccionPlataformaNoSoportadaError, match="llamadas telefónicas"):
            await app_lin.servicio_contactos.llamar_contacto(c.id)

        # Validar RN-09: subcategoría de otra categoría padre es rechazada
        cat_uni = app_lin.servicio_categorias.crear_categoria(nombre="Universidad")
        cat_per = app_lin.servicio_categorias.crear_categoria(nombre="Personal")
        sub_cal = app_lin.servicio_categorias.crear_subcategoria(
            categoria_id=cat_uni.id, nombre="Cálculo"
        )
        with pytest.raises(JerarquiaCategoriaInvalidaError, match="categoría padre"):
            app_lin.servicio_categorias.validar_jerarquia(cat_per.id, sub_cal.id)
    finally:
        app_lin.db.cerrar()

    # Android: tanto mailto como tel habilitados
    app_and, _, _, lanz_and = _crear_app(PlataformaSO.ANDROID)
    try:
        c2 = app_and.servicio_contactos.crear_contacto(
            nombre="Tutor", telefono="+52 55 9999 0000", correo="tutor@uni.edu"
        )
        assert app_and.servicio_contactos.puede_llamar_en_plataforma_actual(c2) is True
        assert await app_and.servicio_contactos.llamar_contacto(c2.id) is True
        assert lanz_and.uris_abiertas == ["tel:+525599990000"]
    finally:
        app_and.db.cerrar()

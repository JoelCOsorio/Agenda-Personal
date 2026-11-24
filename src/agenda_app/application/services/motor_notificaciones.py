"""Orquestador central del Motor Unificado de Notificaciones (PROC-03)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from uuid import UUID

from agenda_app.application.ports.notificaciones import (
    ACCION_COMPLETAR_TAREA,
    ACCION_MARCAR_VISTO,
    ACCION_POSPONER,
    AccionNotificacion,
    ContenidoNotificacion,
    EventoInteraccionNotificacion,
    IAdaptadorNotificaciones,
    IProveedorContenidoRecordatorio,
    SolicitudNotificacion,
)
from agenda_app.application.ports.reloj import IReloj
from agenda_app.application.ports.repositorios import (
    IRepositorioAjustes,
    IRepositorioRecordatorios,
)
from agenda_app.domain.entities.recordatorio import Recordatorio
from agenda_app.domain.enums import EstadoRecordatorio, TipoOrigenRecordatorio
from agenda_app.domain.rules.recordatorio_rules import ValidadorRecordatorio

CallbackCompletarTarea = Callable[[UUID], Awaitable[None]]
CallbackAbrirItem = Callable[[TipoOrigenRecordatorio, UUID], Awaitable[None]]


class MotorNotificaciones:
    """Gestiona programación, reprogramación, cancelación y acciones rápidas (RN-02..RN-14)."""

    def __init__(
        self,
        repo_recordatorios: IRepositorioRecordatorios,
        repo_ajustes: IRepositorioAjustes,
        adaptador: IAdaptadorNotificaciones,
        reloj: IReloj,
        proveedor_contenido: IProveedorContenidoRecordatorio | None = None,
        on_completar_tarea: CallbackCompletarTarea | None = None,
        on_abrir_item: CallbackAbrirItem | None = None,
    ) -> None:
        self._repo_recordatorios = repo_recordatorios
        self._repo_ajustes = repo_ajustes
        self._adaptador = adaptador
        self._reloj = reloj
        self._proveedor_contenido = proveedor_contenido
        self._on_completar_tarea = on_completar_tarea
        self._on_abrir_item = on_abrir_item

        self._adaptador.registrar_callbacks(
            on_tap=self.procesar_tap,
            on_action=self.procesar_accion_rapida,
        )

    async def programar_o_reprogramar(
        self,
        *,
        tipo_origen: TipoOrigenRecordatorio,
        item_id: UUID,
        titulo: str,
        cuerpo: str,
        fecha_objetivo: datetime,
        antelacion_minutos: int | None = None,
    ) -> Recordatorio:
        """Crea o actualiza el único recordatorio activo de un Evento o Tarea (RN-02, RN-03)."""
        ahora = self._reloj.ahora_utc()
        ajustes = self._repo_ajustes.obtener()
        antelacion = (
            ajustes.antelacion_recordatorio_defecto_min
            if antelacion_minutos is None
            else antelacion_minutos
        )

        fecha_disparo = ValidadorRecordatorio.calcular_y_validar_disparo(
            fecha_objetivo=fecha_objetivo,
            antelacion_minutos=antelacion,
            ahora=ahora,
        )

        existente = self._repo_recordatorios.obtener_por_item(tipo_origen, item_id)
        if existente is not None:
            await self._adaptador.cancelar(existente.id_notificacion_so)
            existente.reprogramar(
                nueva_fecha_disparo=fecha_disparo,
                nueva_antelacion_minutos=antelacion,
                ahora=ahora,
            )
            recordatorio = existente
        else:
            id_so = self._repo_recordatorios.siguiente_id_notificacion_so()
            recordatorio = Recordatorio(
                id_notificacion_so=id_so,
                tipo_origen=tipo_origen,
                evento_id=item_id if tipo_origen == TipoOrigenRecordatorio.EVENTO else None,
                tarea_id=item_id if tipo_origen == TipoOrigenRecordatorio.TAREA else None,
                antelacion_minutos=antelacion,
                fecha_disparo=fecha_disparo,
                estado=EstadoRecordatorio.PENDIENTE,
                created_at=ahora,
                updated_at=ahora,
            )

        self._repo_recordatorios.guardar(recordatorio)
        solicitud = await self._construir_solicitud(
            recordatorio=recordatorio,
            titulo=titulo,
            cuerpo=cuerpo,
            con_sonido=ajustes.sonido_notificaciones,
        )
        await self._adaptador.programar(solicitud)
        return recordatorio

    async def cancelar_por_item(
        self,
        tipo_origen: TipoOrigenRecordatorio,
        item_id: UUID,
    ) -> bool:
        """Cancela el recordatorio activo al eliminar ítem o completar tarea (RN-02, RN-12)."""
        existente = self._repo_recordatorios.obtener_por_item(tipo_origen, item_id)
        if existente is None:
            return False

        await self._adaptador.cancelar(existente.id_notificacion_so)
        if existente.estado != EstadoRecordatorio.CANCELADO:
            existente.cancelar(self._reloj.ahora_utc())
            self._repo_recordatorios.guardar(existente)
        return True

    async def posponer_recordatorio(
        self,
        recordatorio_id: UUID,
        minutos: int | None = None,
    ) -> Recordatorio | None:
        """Pospone un recordatorio usando minutos_posponer_defecto de Ajustes (RN-14)."""
        recordatorio = self._repo_recordatorios.obtener_por_id(recordatorio_id)
        if recordatorio is None:
            return None

        ahora = self._reloj.ahora_utc()
        ajustes = self._repo_ajustes.obtener()
        minutos_snooze = ajustes.minutos_posponer_defecto if minutos is None else minutos
        nueva_fecha = ahora + timedelta(minutes=minutos_snooze)

        await self._adaptador.cancelar(recordatorio.id_notificacion_so)
        recordatorio.posponer(nueva_fecha_disparo=nueva_fecha, ahora=ahora)
        self._repo_recordatorios.guardar(recordatorio)

        contenido = self._resolver_contenido(recordatorio)
        solicitud = await self._construir_solicitud(
            recordatorio=recordatorio,
            titulo=contenido.titulo,
            cuerpo=contenido.cuerpo,
            con_sonido=ajustes.sonido_notificaciones,
        )
        await self._adaptador.programar(solicitud)
        return recordatorio

    async def marcar_atendido(self, recordatorio_id: UUID) -> Recordatorio | None:
        """Marca un recordatorio (entregado o perdido) como atendido por el usuario."""
        recordatorio = self._repo_recordatorios.obtener_por_id(recordatorio_id)
        if recordatorio is None:
            return None
        recordatorio.marcar_atendido(self._reloj.ahora_utc())
        self._repo_recordatorios.guardar(recordatorio)
        return recordatorio

    async def reprogramar_en_so_si_activo(self, recordatorio: Recordatorio) -> None:
        """Registra en el SO un recordatorio ya existente en SQLite (usado por StartupReconciler)."""
        if not recordatorio.esta_activo:
            return
        ajustes = self._repo_ajustes.obtener()
        contenido = self._resolver_contenido(recordatorio)
        solicitud = await self._construir_solicitud(
            recordatorio=recordatorio,
            titulo=contenido.titulo,
            cuerpo=contenido.cuerpo,
            con_sonido=ajustes.sonido_notificaciones,
        )
        await self._adaptador.programar(solicitud)

    async def procesar_tap(self, evento: EventoInteraccionNotificacion) -> None:
        """Maneja el toque directo sobre una notificación nativa."""
        datos = ValidadorRecordatorio.parsear_payload(evento.payload)
        if datos is None:
            return
        await self.marcar_atendido(datos.recordatorio_id)
        if self._on_abrir_item is not None:
            await self._on_abrir_item(datos.tipo_origen, datos.item_id)

    async def procesar_accion_rapida(self, evento: EventoInteraccionNotificacion) -> None:
        """Enruta botones de acción rápida: Posponer, Marcar visto o Completar tarea."""
        datos = ValidadorRecordatorio.parsear_payload(evento.payload)
        if datos is None:
            return

        if evento.action_id == ACCION_POSPONER:
            await self.posponer_recordatorio(datos.recordatorio_id)
        elif evento.action_id == ACCION_MARCAR_VISTO:
            await self.marcar_atendido(datos.recordatorio_id)
        elif evento.action_id == ACCION_COMPLETAR_TAREA:
            await self.marcar_atendido(datos.recordatorio_id)
            if (
                datos.tipo_origen == TipoOrigenRecordatorio.TAREA
                and self._on_completar_tarea is not None
            ):
                await self._on_completar_tarea(datos.item_id)

    async def _construir_solicitud(
        self,
        *,
        recordatorio: Recordatorio,
        titulo: str,
        cuerpo: str,
        con_sonido: bool,
    ) -> SolicitudNotificacion:
        """Arma la solicitud aplicando degradación elegante si el SO no soporta acciones (RN-06)."""
        capacidades = await self._adaptador.obtener_capacidades()
        acciones: tuple[AccionNotificacion, ...] = ()

        if capacidades.soporta_acciones_rapidas:
            lista = [
                # En Android foreground=True asegura que Python reprograme el snooze de inmediato.
                AccionNotificacion(
                    id=ACCION_POSPONER,
                    titulo="Posponer",
                    abrir_en_primer_plano=True,
                ),
                AccionNotificacion(
                    id=ACCION_MARCAR_VISTO,
                    titulo="Marcar como visto",
                    abrir_en_primer_plano=False,
                ),
            ]
            if recordatorio.tipo_origen == TipoOrigenRecordatorio.TAREA:
                lista.append(
                    AccionNotificacion(
                        id=ACCION_COMPLETAR_TAREA,
                        titulo="Completar tarea",
                        abrir_en_primer_plano=True,
                    )
                )
            acciones = tuple(lista)

        return SolicitudNotificacion(
            id_notificacion_so=recordatorio.id_notificacion_so,
            titulo=titulo,
            cuerpo=cuerpo,
            fecha_disparo=recordatorio.fecha_disparo,
            payload=ValidadorRecordatorio.construir_payload(recordatorio),
            con_sonido=con_sonido,
            acciones=acciones,
        )

    def _resolver_contenido(self, recordatorio: Recordatorio) -> ContenidoNotificacion:
        if self._proveedor_contenido is not None:
            contenido = self._proveedor_contenido.obtener_contenido(
                recordatorio.tipo_origen,
                recordatorio.item_id,
            )
            if contenido is not None:
                return contenido
        etiqueta = (
            "Evento de Agenda"
            if recordatorio.tipo_origen == TipoOrigenRecordatorio.EVENTO
            else "Tarea Pendiente"
        )
        return ContenidoNotificacion(
            titulo=f"Recordatorio: {etiqueta}",
            cuerpo="Tienes una actividad programada.",
        )

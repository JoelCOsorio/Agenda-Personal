"""Adaptador de notificaciones nativas para Android vía flet-notifications."""

from __future__ import annotations

from typing import Any

import flet_notifications as ftn

from agenda_app.application.ports.notificaciones import (
    CapacidadesNotificacionSO,
    SolicitudNotificacion,
)
from agenda_app.domain.enums import PlataformaSO
from agenda_app.infrastructure.notifications.base_flet import (
    BaseAdaptadorFlet,
    construir_acciones_flet,
)

CANAL_ANDROID_ID = "agenda_recordatorios"
CANAL_ANDROID_NOMBRE = "Recordatorios de Agenda y Tareas"
CANAL_ANDROID_DESC = "Notificaciones locales de eventos y tareas programadas."


class AdaptadorNotificacionesAndroid(BaseAdaptadorFlet):
    """Implementa IAdaptadorNotificaciones para Android con degradación de alarmas exactas."""

    def __init__(self, cliente: Any | None = None) -> None:
        super().__init__(cliente=cliente)

    async def obtener_capacidades(self) -> CapacidadesNotificacionSO:
        exactas = await self.puede_programar_exacto()
        return CapacidadesNotificacionSO(
            plataforma=PlataformaSO.ANDROID,
            soporta_programacion_nativa=True,
            soporta_acciones_rapidas=True,
            soporta_alarmas_exactas=exactas,
            soporta_cancelacion_masiva=True,
        )

    async def puede_programar_exacto(self) -> bool:
        try:
            return bool(await self._cliente.can_schedule_exact_alarms())
        except Exception:
            return False

    async def programar(self, solicitud: SolicitudNotificacion) -> None:
        exactas = await self.puede_programar_exacto()
        modo = (
            ftn.AndroidScheduleMode.EXACT_ALLOW_WHILE_IDLE
            if exactas
            else ftn.AndroidScheduleMode.INEXACT_ALLOW_WHILE_IDLE
        )
        opciones = self._construir_opciones(solicitud.con_sonido)
        acciones = construir_acciones_flet(solicitud.acciones)

        try:
            await self._cliente.schedule(
                solicitud.id_notificacion_so,
                when=solicitud.fecha_disparo,
                title=solicitud.titulo,
                body=solicitud.cuerpo,
                payload=solicitud.payload,
                actions=acciones,
                match_components=None,
                options=opciones,
                schedule_mode=modo,
            )
        except ftn.NotificationPermissionException:
            # Degradación elegante si el permiso exacto fue revocado en medio del flujo (RN-06)
            if modo == ftn.AndroidScheduleMode.EXACT_ALLOW_WHILE_IDLE:
                await self._cliente.schedule(
                    solicitud.id_notificacion_so,
                    when=solicitud.fecha_disparo,
                    title=solicitud.titulo,
                    body=solicitud.cuerpo,
                    payload=solicitud.payload,
                    actions=acciones,
                    match_components=None,
                    options=opciones,
                    schedule_mode=ftn.AndroidScheduleMode.INEXACT_ALLOW_WHILE_IDLE,
                )
            else:
                raise

    async def cancelar(self, id_notificacion_so: int) -> None:
        await self._cliente.cancel(id_notificacion_so)

    async def mostrar_inmediata(self, solicitud: SolicitudNotificacion) -> None:
        await self._cliente.show(
            solicitud.id_notificacion_so,
            title=solicitud.titulo,
            body=solicitud.cuerpo,
            payload=solicitud.payload,
            actions=construir_acciones_flet(solicitud.acciones),
            options=self._construir_opciones(solicitud.con_sonido),
        )

    @staticmethod
    def _construir_opciones(con_sonido: bool) -> ftn.NotificationOptions:
        return ftn.NotificationOptions(
            android=ftn.AndroidOptions(
                channel=ftn.NotificationChannel(
                    id=CANAL_ANDROID_ID,
                    name=CANAL_ANDROID_NOMBRE,
                    description=CANAL_ANDROID_DESC,
                    importance=ftn.AndroidImportance.HIGH,
                    play_sound=con_sonido,
                ),
                priority=ftn.AndroidPriority.HIGH,
                silent=not con_sonido,
            )
        )

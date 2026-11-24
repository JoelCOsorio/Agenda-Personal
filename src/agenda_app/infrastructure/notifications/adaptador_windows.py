"""Adaptador de notificaciones nativas para Windows vía flet-notifications."""

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


class AdaptadorNotificacionesWindows(BaseAdaptadorFlet):
    """Implementa IAdaptadorNotificaciones para Windows (one-off y cancelación individual)."""

    def __init__(self, cliente: Any | None = None) -> None:
        super().__init__(cliente=cliente)

    async def obtener_capacidades(self) -> CapacidadesNotificacionSO:
        return CapacidadesNotificacionSO(
            plataforma=PlataformaSO.WINDOWS,
            soporta_programacion_nativa=True,
            soporta_acciones_rapidas=True,
            soporta_alarmas_exactas=True,
            soporta_cancelacion_masiva=False,  # Windows solo cancela individualmente
        )

    async def puede_programar_exacto(self) -> bool:
        return True

    async def programar(self, solicitud: SolicitudNotificacion) -> None:
        # Windows solo admite notificaciones únicas (match_components=None)
        await self._cliente.schedule(
            solicitud.id_notificacion_so,
            when=solicitud.fecha_disparo,
            title=solicitud.titulo,
            body=solicitud.cuerpo,
            payload=solicitud.payload,
            actions=construir_acciones_flet(solicitud.acciones),
            match_components=None,
            options=self._construir_opciones(solicitud.con_sonido),
        )

    async def cancelar(self, id_notificacion_so: int) -> None:
        # En Windows la cancelación siempre debe ser individual por id_notificacion_so
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
            windows=ftn.WindowsOptions(
                scenario=ftn.WindowsScenario.REMINDER,
                sound=ftn.WindowsSound.REMINDER if con_sonido else ftn.WindowsSound.SILENT,
            )
        )

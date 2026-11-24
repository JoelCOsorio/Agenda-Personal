"""Base común para adaptadores apoyados en flet-notifications."""

from __future__ import annotations

import asyncio
from typing import Any

import flet_notifications as ftn

from agenda_app.application.ports.notificaciones import (
    AccionNotificacion,
    CallbackInteraccion,
    EventoInteraccionNotificacion,
)


def construir_acciones_flet(
    acciones: tuple[AccionNotificacion, ...],
) -> list[ftn.NotificationAction] | None:
    if not acciones:
        return None
    return [
        ftn.NotificationAction(
            id=accion.id,
            title=accion.titulo,
            foreground=accion.abrir_en_primer_plano,
            cancel_notification=accion.cancelar_al_pulsar,
        )
        for accion in acciones
    ]


class BaseAdaptadorFlet:
    """Puente común para conectar callbacks async on_tap / on_action de flet_notifications."""

    def __init__(self, cliente: Any | None = None) -> None:
        self._cliente: Any = cliente if cliente is not None else ftn.Notifications()
        self._on_tap: CallbackInteraccion | None = None
        self._on_action: CallbackInteraccion | None = None
        self._enlazar_eventos()

    @property
    def cliente(self) -> Any:
        return self._cliente

    def _enlazar_eventos(self) -> None:
        async def _handle_tap(e: Any) -> None:
            if self._on_tap is None:
                return
            evento = EventoInteraccionNotificacion(
                payload=getattr(e, "payload", None),
                action_id=None,
                id_notificacion_so=getattr(e, "notification_id", None),
            )
            await self._on_tap(evento)

        async def _handle_action(e: Any) -> None:
            if self._on_action is None:
                return
            evento = EventoInteraccionNotificacion(
                payload=getattr(e, "payload", None),
                action_id=getattr(e, "action_id", None),
                id_notificacion_so=getattr(e, "notification_id", None),
            )
            await self._on_action(evento)

        self._cliente.on_tap = _handle_tap
        self._cliente.on_action = _handle_action

    def registrar_callbacks(
        self,
        on_tap: CallbackInteraccion | None = None,
        on_action: CallbackInteraccion | None = None,
    ) -> None:
        self._on_tap = on_tap
        self._on_action = on_action

    async def solicitar_permisos(self) -> bool:
        resultado = self._cliente.request_permissions()
        if asyncio.iscoroutine(resultado):
            return bool(await resultado)
        return bool(resultado)

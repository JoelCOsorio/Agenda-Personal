"""Fábrica de adaptadores de notificación según PlataformaSO (OCP / DIP)."""

from __future__ import annotations

from typing import Any

from agenda_app.application.ports.notificaciones import IAdaptadorNotificaciones
from agenda_app.application.ports.reloj import IReloj
from agenda_app.domain.enums import PlataformaSO
from agenda_app.infrastructure.notifications.adaptador_android import (
    AdaptadorNotificacionesAndroid,
)
from agenda_app.infrastructure.notifications.adaptador_linux import (
    AdaptadorNotificacionesLinux,
)
from agenda_app.infrastructure.notifications.adaptador_web import (
    AdaptadorNotificacionesWeb,
)
from agenda_app.infrastructure.notifications.adaptador_windows import (
    AdaptadorNotificacionesWindows,
)


def crear_adaptador_notificaciones(
    plataforma: PlataformaSO,
    *,
    cliente_flet: Any | None = None,
    reloj: IReloj | None = None,
) -> IAdaptadorNotificaciones:
    """Instancia el adaptador concreto para Android, Windows, Linux o Web."""
    if plataforma == PlataformaSO.ANDROID:
        return AdaptadorNotificacionesAndroid(cliente=cliente_flet)
    if plataforma == PlataformaSO.WINDOWS:
        return AdaptadorNotificacionesWindows(cliente=cliente_flet)
    if plataforma == PlataformaSO.WEB:
        return AdaptadorNotificacionesWeb(cliente=cliente_flet, reloj=reloj)
    return AdaptadorNotificacionesLinux(cliente=cliente_flet, reloj=reloj)

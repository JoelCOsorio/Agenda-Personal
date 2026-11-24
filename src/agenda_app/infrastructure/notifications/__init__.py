"""Adaptadores concretos de notificaciones para Android, Windows y Linux."""

from agenda_app.infrastructure.notifications.adaptador_android import (
    AdaptadorNotificacionesAndroid,
)
from agenda_app.infrastructure.notifications.adaptador_linux import (
    AdaptadorNotificacionesLinux,
)
from agenda_app.infrastructure.notifications.adaptador_windows import (
    AdaptadorNotificacionesWindows,
)
from agenda_app.infrastructure.notifications.factory import (
    crear_adaptador_notificaciones,
)

__all__ = [
    "AdaptadorNotificacionesAndroid",
    "AdaptadorNotificacionesLinux",
    "AdaptadorNotificacionesWindows",
    "crear_adaptador_notificaciones",
]

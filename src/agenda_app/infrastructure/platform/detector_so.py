"""Detección normalizada de la plataforma objetivo (Android, Windows, Linux)."""

from __future__ import annotations

import sys
from typing import Any

from agenda_app.domain.enums import PlataformaSO


def detectar_plataforma(page_platform: Any | None = None) -> PlataformaSO:
    """Detecta la plataforma desde ft.Page.platform o sys.platform."""
    if page_platform is not None:
        nombre = str(getattr(page_platform, "value", page_platform)).upper()
        if "ANDROID" in nombre:
            return PlataformaSO.ANDROID
        if "WINDOWS" in nombre:
            return PlataformaSO.WINDOWS
        if "LINUX" in nombre:
            return PlataformaSO.LINUX

    if sys.platform.startswith("win"):
        return PlataformaSO.WINDOWS
    return PlataformaSO.LINUX

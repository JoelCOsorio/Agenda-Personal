"""Detección normalizada de la plataforma objetivo (Android, Windows, Linux y Web)."""

from __future__ import annotations

import sys
from typing import Any

from agenda_app.domain.enums import PlataformaSO


def detectar_plataforma(
    page_platform: Any | None = None,
    *,
    is_web: bool = False,
) -> PlataformaSO:
    """Detecta la plataforma desde ft.Page.web, ft.Page.platform o sys.platform."""
    if is_web or sys.platform == "emscripten":
        return PlataformaSO.WEB

    if page_platform is not None:
        nombre = str(getattr(page_platform, "value", page_platform)).upper()
        if "WEB" in nombre:
            return PlataformaSO.WEB
        if "ANDROID" in nombre:
            return PlataformaSO.ANDROID
        if "WINDOWS" in nombre:
            return PlataformaSO.WINDOWS
        if "LINUX" in nombre:
            return PlataformaSO.LINUX

    if sys.platform.startswith("win"):
        return PlataformaSO.WINDOWS
    return PlataformaSO.LINUX

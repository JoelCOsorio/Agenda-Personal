"""Resolución unificada de rutas de almacenamiento local (Android, Windows, Linux)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_LINUX = "agenda-personal"
APP_DIR_WINDOWS = "AgendaPersonal"
DB_FILENAME = "agenda_personal.db"


def obtener_directorio_datos() -> Path:
    """Devuelve el directorio persistente de datos de la app según el SO actual."""
    # Prioridad 1: variable estándar de Flet (obligatoria en sandbox de Android)
    flet_storage = os.environ.get("FLET_APP_STORAGE_DATA")
    if flet_storage:
        ruta = Path(flet_storage)
    elif sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        ruta = base / APP_DIR_WINDOWS
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg) if xdg else (Path.home() / ".local" / "share")
        ruta = base / APP_DIR_LINUX

    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def obtener_ruta_db(ruta_personalizada: Path | str | None = None) -> Path:
    """Retorna la ruta del archivo SQLite local compartido (ej. Flet + worker Linux)."""
    if ruta_personalizada is not None:
        ruta = Path(ruta_personalizada)
        if str(ruta) != ":memory:":
            ruta.parent.mkdir(parents=True, exist_ok=True)
        return ruta
    return obtener_directorio_datos() / DB_FILENAME

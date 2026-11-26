# -*- mode: python ; coding: utf-8 -*-
"""Especificación PyInstaller alternativa para empaquetado de escritorio (Linux / Windows).

Nota: El mecanismo oficial y recomendado del proyecto es `uv run flet build <linux|windows|apk>`,
ya que compila nativamente Flutter y las extensiones como `flet-notifications`.
Este archivo `.spec` se proporciona como alternativa de escritorio con PyInstaller:

    uv run --with pyinstaller pyinstaller atempo.spec --clean
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

PROJECT_ROOT = Path(SPECPATH).resolve()
SRC_DIR = PROJECT_ROOT / "src"

datas = [
    (str(SRC_DIR / "assets"), "assets"),
    (
        str(SRC_DIR / "agenda_app" / "infrastructure" / "persistence" / "sqlite" / "sql"),
        "agenda_app/infrastructure/persistence/sqlite/sql",
    ),
]
binaries = []
hiddenimports = [
    "sqlite3",
    "zoneinfo",
    "tzdata",
]

# Recolectar recursos y binarios de Flet Desktop y extensiones instaladas
for pkg in ("flet", "flet_desktop", "flet_notifications"):
    try:
        p_datas, p_binaries, p_hidden = collect_all(pkg)
        datas += p_datas
        binaries += p_binaries
        hiddenimports += p_hidden
    except Exception:
        pass

if sys.platform.startswith("linux"):
    for pkg in ("desktop_notifier", "dbus_fast"):
        try:
            hiddenimports += collect_submodules(pkg)
        except Exception:
            pass

a = Analysis(
    [str(SRC_DIR / "main.py")],
    pathex=[str(SRC_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=list(dict.fromkeys(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "pytest_asyncio", "flet.testing"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Atempo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Atempo",
)

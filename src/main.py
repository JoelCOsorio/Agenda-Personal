"""Punto de entrada principal de Agenda Personal y Académica (Flet 1.x)."""

from __future__ import annotations

import flet as ft

from agenda_app.presentation.app import run_app


async def main(page: ft.Page) -> None:
    await run_app(page)


if __name__ == "__main__":
    ft.run(main)

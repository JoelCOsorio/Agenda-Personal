"""Smoke test de interfaz Flet 1.x para Agenda Personal (navegación entre los 4 módulos)."""

from __future__ import annotations

import flet.testing as ftt


async def test_navegacion_modulos_principales(flet_app: ftt.FletTestApp) -> None:
    """Arranca la app real y verifica que navega por Agenda, Tareas, Contactos y Ajustes."""
    tester = flet_app.tester
    await tester.pump_and_settle()

    # Arranca en Agenda con botón Hoy y selector de vistas
    assert (await tester.find_by_text("Hoy")).count >= 1
    assert (await tester.find_by_key("fab_principal")).count == 1

    # Navegar a Tareas
    await tester.tap(await tester.find_by_text("Tareas"))
    await tester.pump_and_settle()
    assert (await tester.find_by_text("Prioridad")).count >= 1

    # Navegar a Contactos
    await tester.tap(await tester.find_by_text("Contactos"))
    await tester.pump_and_settle()
    assert (await tester.find_by_text("Profesor")).count >= 1

    # Navegar a Ajustes
    await tester.tap(await tester.find_by_text("Ajustes"))
    await tester.pump_and_settle()
    assert (await tester.find_by_text("Modo oscuro")).count >= 1

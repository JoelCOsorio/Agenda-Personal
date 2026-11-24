"""Tema Material 3 (acento Índigo/Azul) con modo Claro y Oscuro en vivo."""

from __future__ import annotations

import flet as ft

from agenda_app.domain.entities.configuracion import ConfiguracionSistema
from agenda_app.domain.enums import PrioridadTarea

PALETA_COLORES_CATEGORIA: tuple[str, ...] = (
    "#3B82F6",  # Azul
    "#6366F1",  # Índigo
    "#8B5CF6",  # Violeta
    "#EC4899",  # Rosa
    "#EF4444",  # Rojo
    "#F59E0B",  # Ámbar
    "#10B981",  # Esmeralda
    "#14B8A6",  # Turquesa
    "#64748B",  # Pizarra
)


def construir_tema_claro() -> ft.Theme:
    return ft.Theme(
        color_scheme_seed=ft.Colors.INDIGO,
        use_material3=True,
    )


def construir_tema_oscuro() -> ft.Theme:
    return ft.Theme(
        color_scheme_seed=ft.Colors.INDIGO,
        use_material3=True,
    )


def aplicar_tema(page: ft.Page, configuracion: ConfiguracionSistema) -> None:
    """Aplica el modo claro/oscuro en vivo a partir de ConfiguracionSistema (RN-14)."""
    page.theme = construir_tema_claro()
    page.dark_theme = construir_tema_oscuro()
    page.theme_mode = (
        ft.ThemeMode.DARK if configuracion.tema_oscuro else ft.ThemeMode.LIGHT
    )


def color_prioridad(prioridad: PrioridadTarea) -> str:
    if prioridad == PrioridadTarea.ALTA:
        return "#DC2626"
    if prioridad == PrioridadTarea.MEDIA:
        return "#D97706"
    return "#059669"


def etiqueta_prioridad(prioridad: PrioridadTarea) -> str:
    return {
        PrioridadTarea.ALTA: "Alta",
        PrioridadTarea.MEDIA: "Media",
        PrioridadTarea.BAJA: "Baja",
    }[prioridad]

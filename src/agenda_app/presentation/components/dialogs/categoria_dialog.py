"""Diálogos de creación rápida y gestión completa de Categorías y Subcategorías (RF-21, RF-22)."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

import flet as ft

from agenda_app.container import ContenedorAplicacion
from agenda_app.domain.exceptions import DominioError
from agenda_app.presentation.theme import PALETA_COLORES_CATEGORIA


def abrir_dialogo_categoria_rapida(
    page: ft.Page,
    contenedor: ContenedorAplicacion,
    *,
    categoria_padre_id: UUID | None = None,
    on_creada: Callable[[UUID, UUID | None], None] | None = None,
) -> None:
    """Crea rápidamente una categoría (Nivel 1) o subcategoría (Nivel 2) en 2 clics (RF-22)."""
    es_sub = categoria_padre_id is not None
    color_sel = {"valor": PALETA_COLORES_CATEGORIA[0]}
    nombre_field = ft.TextField(
        label="Nombre de la subcategoría" if es_sub else "Nombre de la categoría",
        hint_text="Ej. Cálculo, Ingeniería de Software" if es_sub else "Ej. Universidad, Personal",
        autofocus=True,
    )
    error_txt = ft.Text("", color=ft.Colors.ERROR, size=12, visible=False)
    swatches_row = ft.Row(wrap=True, spacing=8)

    def _render_swatches() -> None:
        swatches_row.controls = [
            ft.Container(
                width=28,
                height=28,
                border_radius=14,
                bgcolor=hex_c,
                border=(
                    ft.Border.all(3, ft.Colors.ON_SURFACE)
                    if color_sel["valor"] == hex_c
                    else None
                ),
                on_click=lambda _, c=hex_c: _seleccionar_color(c),
            )
            for hex_c in PALETA_COLORES_CATEGORIA
        ]

    def _seleccionar_color(c: str) -> None:
        color_sel["valor"] = c
        _render_swatches()
        page.update()

    _render_swatches()

    def _guardar(_: ft.Event) -> None:
        try:
            if es_sub and categoria_padre_id is not None:
                sub = contenedor.servicio_categorias.crear_subcategoria(
                    categoria_id=categoria_padre_id,
                    nombre=nombre_field.value or "",
                    color_hex=color_sel["valor"],
                )
                page.pop_dialog()
                if on_creada:
                    on_creada(categoria_padre_id, sub.id)
            else:
                cat = contenedor.servicio_categorias.crear_categoria(
                    nombre=nombre_field.value or "",
                    color_hex=color_sel["valor"],
                )
                page.pop_dialog()
                if on_creada:
                    on_creada(cat.id, None)
        except Exception as exc:
            error_txt.value = str(exc)
            error_txt.visible = True
            page.update()

    dialogo = ft.AlertDialog(
        modal=True,
        title=ft.Text("Nueva subcategoría" if es_sub else "Nueva categoría"),
        content=ft.Column(
            tight=True,
            spacing=12,
            width=360,
            controls=[
                nombre_field,
                ft.Text("Color identificador:", size=12),
                swatches_row,
                error_txt,
            ],
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: page.pop_dialog()),
            ft.FilledButton("Guardar", on_click=_guardar),
        ],
    )
    page.show_dialog(dialogo)


def abrir_gestor_categorias(
    page: ft.Page,
    contenedor: ContenedorAplicacion,
    *,
    on_cambio: Callable[[], None] | None = None,
) -> None:
    """Gestor completo de Categorías y Subcategorías (RN-09, RN-13)."""
    lista = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

    def _refrescar() -> None:
        lista.controls.clear()
        categorias = contenedor.servicio_categorias.listar_categorias()
        if not categorias:
            lista.controls.append(
                ft.Text(
                    "Aún no hay categorías. Crea una (ej. Universidad, Personal, Trabajo).",
                    color=ft.Colors.ON_SURFACE_VARIANT,
                )
            )
            page.update()
            return

        for cat in categorias:
            subs = contenedor.servicio_categorias.listar_subcategorias(cat.id)
            chips_sub = [
                ft.Chip(
                    label=ft.Text(s.nombre, size=12),
                    leading=ft.Container(
                        width=10,
                        height=10,
                        border_radius=5,
                        bgcolor=s.color_hex or cat.color_hex,
                    ),
                    on_delete=lambda _, sid=s.id: _eliminar_sub(sid),
                    delete_icon_tooltip="Eliminar subcategoría (conserva ítems en categoría padre)",
                )
                for s in subs
            ]

            lista.controls.append(
                ft.Container(
                    padding=12,
                    border_radius=10,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                    border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                    content=ft.Column(
                        spacing=8,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Row(
                                        spacing=8,
                                        controls=[
                                            ft.Container(
                                                width=14,
                                                height=14,
                                                border_radius=7,
                                                bgcolor=cat.color_hex,
                                            ),
                                            ft.Text(cat.nombre, weight=ft.FontWeight.W_600),
                                        ],
                                    ),
                                    ft.Row(
                                        spacing=4,
                                        controls=[
                                            ft.IconButton(
                                                icon=ft.Icons.ADD,
                                                tooltip="Agregar subcategoría",
                                                on_click=lambda _, cid=cat.id: abrir_dialogo_categoria_rapida(
                                                    page,
                                                    contenedor,
                                                    categoria_padre_id=cid,
                                                    on_creada=lambda *_: _tras_cambio(),
                                                ),
                                            ),
                                            ft.IconButton(
                                                icon=ft.Icons.DELETE_OUTLINE,
                                                icon_color=ft.Colors.ERROR,
                                                tooltip="Eliminar categoría (no borra eventos ni tareas)",
                                                on_click=lambda _, cid=cat.id: _eliminar_cat(cid),
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            ft.Row(wrap=True, spacing=6, controls=chips_sub)
                            if chips_sub
                            else ft.Text(
                                "Sin subcategorías",
                                size=12,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                    ),
                )
            )
        page.update()

    def _tras_cambio() -> None:
        _refrescar()
        if on_cambio:
            on_cambio()

    def _eliminar_cat(cid: UUID) -> None:
        try:
            contenedor.servicio_categorias.eliminar_categoria(cid)
            _tras_cambio()
        except DominioError as exc:
            page.show_dialog(ft.SnackBar(ft.Text(str(exc))))

    def _eliminar_sub(sid: UUID) -> None:
        try:
            contenedor.servicio_categorias.eliminar_subcategoria(sid)
            _tras_cambio()
        except DominioError as exc:
            page.show_dialog(ft.SnackBar(ft.Text(str(exc))))

    _refrescar()

    dialogo = ft.AlertDialog(
        modal=False,
        title=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text("Categorías y Subcategorías"),
                ft.FilledTonalButton(
                    "Nueva categoría",
                    icon=ft.Icons.ADD,
                    on_click=lambda _: abrir_dialogo_categoria_rapida(
                        page,
                        contenedor,
                        on_creada=lambda *_: _tras_cambio(),
                    ),
                ),
            ],
        ),
        content=ft.Container(width=500, height=380, content=lista),
        actions=[ft.TextButton("Cerrar", on_click=lambda _: page.pop_dialog())],
    )
    page.show_dialog(dialogo)

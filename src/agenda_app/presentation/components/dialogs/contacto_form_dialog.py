"""Formulario modal para crear y editar Contactos (PROC-05, RF-17)."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from agenda_app.container import ContenedorAplicacion
from agenda_app.domain.entities.contacto import Contacto
from agenda_app.domain.exceptions import DominioError

ETIQUETAS_SUGERIDAS: tuple[str, ...] = ("Profesor", "Compañero", "Familia", "Trabajo", "Personal")


def abrir_formulario_contacto(
    page: ft.Page,
    contenedor: ContenedorAplicacion,
    *,
    contacto_editar: Contacto | None = None,
    on_guardado: Callable[[], None],
) -> None:
    nombre_f = ft.TextField(
        label="Nombre *",
        value=contacto_editar.nombre if contacto_editar else "",
        autofocus=True,
    )
    tel_f = ft.TextField(
        label="Teléfono",
        value=(contacto_editar.telefono or "") if contacto_editar else "",
        prefix_icon=ft.Icons.PHONE_OUTLINED,
    )
    correo_f = ft.TextField(
        label="Correo electrónico",
        value=(contacto_editar.correo or "") if contacto_editar else "",
        prefix_icon=ft.Icons.EMAIL_OUTLINED,
    )
    etiqueta_f = ft.TextField(
        label="Categoría / Etiqueta",
        hint_text="Profesor, Compañero, Familia, Trabajo...",
        value=(contacto_editar.etiqueta or "") if contacto_editar else "",
    )
    notas_f = ft.TextField(
        label="Notas",
        value=(contacto_editar.notas or "") if contacto_editar else "",
        multiline=True,
        min_lines=2,
        max_lines=3,
    )
    error_txt = ft.Text("", color=ft.Colors.ERROR, size=12, visible=False)

    chips_sug = ft.Row(
        wrap=True,
        spacing=6,
        controls=[
            ft.Chip(
                label=ft.Text(et, size=11),
                on_click=lambda _, val=et: (
                    setattr(etiqueta_f, "value", val),
                    page.update(),
                ),
            )
            for et in ETIQUETAS_SUGERIDAS
        ],
    )

    def _guardar(_: ft.Event) -> None:
        error_txt.visible = False
        try:
            if contacto_editar is None:
                contenedor.servicio_contactos.crear_contacto(
                    nombre=nombre_f.value or "",
                    telefono=tel_f.value or None,
                    correo=correo_f.value or None,
                    etiqueta=etiqueta_f.value or None,
                    notas=notas_f.value or None,
                )
            else:
                contenedor.servicio_contactos.editar_contacto(
                    contacto_editar.id,
                    nombre=nombre_f.value or "",
                    telefono=tel_f.value or None,
                    correo=correo_f.value or None,
                    etiqueta=etiqueta_f.value or None,
                    notas=notas_f.value or None,
                )
            page.pop_dialog()
            on_guardado()
        except DominioError as exc:
            error_txt.value = str(exc)
            error_txt.visible = True
            page.update()

    page.show_dialog(
        ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar contacto" if contacto_editar else "Nuevo contacto"),
            content=ft.Container(
                width=420,
                content=ft.Column(
                    tight=True,
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        error_txt,
                        nombre_f,
                        tel_f,
                        correo_f,
                        etiqueta_f,
                        chips_sug,
                        notas_f,
                    ],
                ),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: page.pop_dialog()),
                ft.FilledButton("Guardar", on_click=_guardar),
            ],
        )
    )

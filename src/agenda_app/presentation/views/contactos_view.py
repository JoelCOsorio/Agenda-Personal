"""Vista del Directorio de Contactos con acciones externas por SO (PROC-05, RN-08, RN-13)."""

from __future__ import annotations

from uuid import UUID

import flet as ft

from agenda_app.container import ContenedorAplicacion
from agenda_app.domain.entities.contacto import Contacto
from agenda_app.domain.exceptions import DominioError
from agenda_app.presentation.components.dialogs.contacto_form_dialog import (
    ETIQUETAS_SUGERIDAS,
    abrir_formulario_contacto,
)


class ContactosView:
    """Directorio con búsqueda rápida, filtro por etiqueta y mailto:/tel: según SO."""

    def __init__(self, page: ft.Page, contenedor: ContenedorAplicacion) -> None:
        self._page = page
        self._contenedor = contenedor
        self._termino = ""
        self._etiqueta_sel: str | None = None

        self._buscador = ft.TextField(
            label="Buscar contacto (nombre, correo, teléfono, etiqueta)",
            prefix_icon=ft.Icons.SEARCH,
            dense=True,
            on_change=self._on_buscar,
        )
        self._chips_filtro = ft.Row(wrap=True, spacing=6)
        self._lista = ft.ListView(expand=True, spacing=10)

        self._raiz = ft.Column(
            expand=True,
            spacing=10,
            controls=[self._buscador, self._chips_filtro, self._lista],
        )

    @property
    def control(self) -> ft.Control:
        return self._raiz

    def abrir_creacion(self) -> None:
        abrir_formulario_contacto(
            self._page,
            self._contenedor,
            on_guardado=self.refrescar,
        )

    def refrescar(self) -> None:
        self._chips_filtro.controls = [
            ft.Chip(
                label=ft.Text("Todos", size=12),
                selected=self._etiqueta_sel is None,
                on_select=lambda _: self._seleccionar_etiqueta(None),
            )
        ] + [
            ft.Chip(
                label=ft.Text(et, size=12),
                selected=self._etiqueta_sel == et,
                on_select=lambda _, val=et: self._seleccionar_etiqueta(val),
            )
            for et in ETIQUETAS_SUGERIDAS
        ]

        contactos = self._contenedor.servicio_contactos.buscar(
            termino=self._termino,
            etiqueta=self._etiqueta_sel,
        )

        self._lista.controls.clear()
        if not contactos:
            self._lista.controls.append(
                ft.Container(
                    padding=ft.Padding.symmetric(vertical=48),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                        controls=[
                            ft.Icon(
                                ft.Icons.PEOPLE_OUTLINE,
                                size=44,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.Text(
                                "No se encontraron contactos.",
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                    ),
                )
            )
            self._page.update()
            return

        for contacto in contactos:
            self._lista.controls.append(self._tarjeta_contacto(contacto))

        self._page.update()

    def _tarjeta_contacto(self, contacto: Contacto) -> ft.Control:
        puede_correo = contacto.puede_enviar_correo()
        # RN-08: Llamar solo se habilita y muestra en Android (oculto en Windows/Linux)
        puede_llamar = self._contenedor.servicio_contactos.puede_llamar_en_plataforma_actual(
            contacto
        )

        async def _enviar_correo(_: ft.Event, cid: UUID = contacto.id) -> None:
            try:
                await self._contenedor.servicio_contactos.abrir_correo_contacto(cid)
            except DominioError as exc:
                self._page.show_dialog(ft.SnackBar(ft.Text(str(exc))))

        async def _llamar(_: ft.Event, cid: UUID = contacto.id) -> None:
            try:
                await self._contenedor.servicio_contactos.llamar_contacto(cid)
            except DominioError as exc:
                self._page.show_dialog(ft.SnackBar(ft.Text(str(exc))))

        acciones: list[ft.Control] = []
        if puede_correo:
            acciones.append(
                ft.IconButton(
                    icon=ft.Icons.EMAIL_OUTLINED,
                    tooltip=f"Enviar correo ({contacto.correo})",
                    on_click=_enviar_correo,
                )
            )
        if puede_llamar:
            acciones.append(
                ft.IconButton(
                    icon=ft.Icons.CALL_OUTLINED,
                    tooltip=f"Llamar ({contacto.telefono})",
                    on_click=_llamar,
                )
            )
        acciones.extend(
            [
                ft.IconButton(
                    icon=ft.Icons.EDIT_OUTLINED,
                    tooltip="Editar contacto",
                    on_click=lambda _, c=contacto: abrir_formulario_contacto(
                        self._page,
                        self._contenedor,
                        contacto_editar=c,
                        on_guardado=self.refrescar,
                    ),
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_color=ft.Colors.ERROR,
                    tooltip="Eliminar contacto",
                    on_click=lambda _, c=contacto: self._confirmar_eliminar(c),
                ),
            ]
        )

        detalles: list[ft.Control] = []
        if contacto.correo:
            detalles.append(ft.Text(f"Correo: {contacto.correo}", size=12))
        if contacto.telefono:
            detalles.append(ft.Text(f"Teléfono: {contacto.telefono}", size=12))
        if contacto.notas:
            detalles.append(
                ft.Text(contacto.notas, size=12, color=ft.Colors.ON_SURFACE_VARIANT)
            )

        return ft.Container(
            padding=12,
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                spacing=8,
                                expand=True,
                                controls=[
                                    ft.CircleAvatar(
                                        content=ft.Text(contacto.nombre[:1].upper()),
                                        radius=18,
                                    ),
                                    ft.Column(
                                        spacing=2,
                                        expand=True,
                                        controls=[
                                            ft.Text(
                                                contacto.nombre,
                                                size=15,
                                                weight=ft.FontWeight.W_600,
                                            ),
                                            ft.Text(
                                                contacto.etiqueta or "Sin etiqueta",
                                                size=11.5,
                                                color=ft.Colors.PRIMARY,
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            ft.Row(spacing=2, controls=acciones),
                        ],
                    ),
                    *detalles,
                ],
            ),
        )

    def _on_buscar(self, e: ft.Event[ft.TextField]) -> None:
        self._termino = e.control.value or ""
        self.refrescar()

    def _seleccionar_etiqueta(self, etiqueta: str | None) -> None:
        self._etiqueta_sel = etiqueta
        self.refrescar()

    def _confirmar_eliminar(self, contacto: Contacto) -> None:
        def _eliminar(_: ft.Event) -> None:
            self._contenedor.servicio_contactos.eliminar_contacto(contacto.id)
            self._page.pop_dialog()
            self.refrescar()

        self._page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Eliminar contacto"),
                content=ft.Text(
                    f"¿Deseas eliminar a '{contacto.nombre}'? "
                    "Los eventos y tareas vinculados se conservarán desvinculados (RN-13)."
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda _: self._page.pop_dialog()),
                    ft.FilledButton("Eliminar", on_click=_eliminar),
                ],
            )
        )

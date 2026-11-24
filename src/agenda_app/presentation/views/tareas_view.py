"""Vista del Módulo Independiente de Tareas (PROC-04, RN-07, RN-12)."""

from __future__ import annotations

from uuid import UUID

import flet as ft

from agenda_app.container import ContenedorAplicacion
from agenda_app.domain.entities.tarea import Tarea
from agenda_app.domain.enums import (
    EstadoTarea,
    PrioridadTarea,
    TipoOrigenRecordatorio,
)
from agenda_app.presentation.components.dialogs.tarea_form_dialog import (
    abrir_formulario_tarea,
)
from agenda_app.presentation.formatters import (
    etiqueta_estado_tarea,
    formatear_antelacion,
    formatear_fecha_hora,
)
from agenda_app.presentation.theme import color_prioridad, etiqueta_prioridad


class TareasView:
    """Gestiona filtros, lista interactiva y ciclo de vida de Tareas (RN-07, RN-12)."""

    def __init__(self, page: ft.Page, contenedor: ContenedorAplicacion) -> None:
        self._page = page
        self._contenedor = contenedor
        self._filtro_estado: EstadoTarea | None = None
        self._filtro_prioridad: PrioridadTarea | None = None
        self._filtro_cat: UUID | None = None

        self._estado_dd = ft.Dropdown(
            label="Estado",
            width=165,
            dense=True,
            value="",
            options=[ft.DropdownOption(key="", text="Todos")]
            + [
                ft.DropdownOption(key=s.value, text=etiqueta_estado_tarea(s))
                for s in EstadoTarea
            ],
            on_select=self._cambiar_estado,
        )
        self._prioridad_dd = ft.Dropdown(
            label="Prioridad",
            width=155,
            dense=True,
            value="",
            options=[ft.DropdownOption(key="", text="Todas")]
            + [
                ft.DropdownOption(key=p.value, text=etiqueta_prioridad(p))
                for p in PrioridadTarea
            ],
            on_select=self._cambiar_prioridad,
        )
        self._cat_dd = ft.Dropdown(
            label="Categoría",
            width=180,
            dense=True,
            value="",
            on_select=self._cambiar_cat,
        )
        self._lista = ft.ListView(expand=True, spacing=10)

        self._raiz = ft.Column(
            expand=True,
            spacing=12,
            controls=[
                ft.Row(
                    wrap=True,
                    spacing=10,
                    controls=[self._estado_dd, self._prioridad_dd, self._cat_dd],
                ),
                self._lista,
            ],
        )

    @property
    def control(self) -> ft.Control:
        return self._raiz

    def abrir_creacion(self) -> None:
        abrir_formulario_tarea(
            self._page,
            self._contenedor,
            on_guardada=self._tras_cambio,
        )

    def refrescar(self) -> None:
        ajustes = self._contenedor.servicio_ajustes.obtener()
        ahora = self._contenedor.reloj.ahora_utc()

        cats = self._contenedor.servicio_categorias.listar_categorias()
        mapa_cats = {c.id: c for c in cats}
        mapa_contactos = {
            c.id: c for c in self._contenedor.servicio_contactos.buscar()
        }

        self._cat_dd.options = [ft.DropdownOption(key="", text="Todas")] + [
            ft.DropdownOption(key=str(c.id), text=c.nombre) for c in cats
        ]
        self._cat_dd.value = str(self._filtro_cat) if self._filtro_cat else ""

        tareas = self._contenedor.servicio_tareas.listar_tareas(
            estado=self._filtro_estado,
            prioridad=self._filtro_prioridad,
            categoria_id=self._filtro_cat,
        )

        self._lista.controls.clear()
        if not tareas:
            self._lista.controls.append(
                ft.Container(
                    padding=ft.Padding.symmetric(vertical=48),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                        controls=[
                            ft.Icon(
                                ft.Icons.TASK_ALT_OUTLINED,
                                size=44,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.Text(
                                "No hay tareas que coincidan con los filtros.",
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                    ),
                )
            )
            self._page.update()
            return

        for tarea in tareas:
            rec = self._contenedor.repo_recordatorios.obtener_por_item(
                TipoOrigenRecordatorio.TAREA, tarea.id
            )
            vencida = (
                tarea.fecha_limite is not None
                and tarea.fecha_limite < ahora
                and not tarea.esta_completada
            )
            cat = mapa_cats.get(tarea.categoria_id) if tarea.categoria_id else None

            chips: list[ft.Control] = [
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                    border_radius=12,
                    bgcolor=color_prioridad(tarea.prioridad),
                    content=ft.Text(
                        etiqueta_prioridad(tarea.prioridad), size=11, color="#FFFFFF"
                    ),
                ),
                ft.Chip(label=ft.Text(etiqueta_estado_tarea(tarea.estado), size=11)),
            ]
            if cat:
                chips.append(
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                        border_radius=12,
                        bgcolor=cat.color_hex,
                        content=ft.Text(cat.nombre, size=11, color="#FFFFFF"),
                    )
                )
            if rec and rec.esta_activo:
                chips.append(
                    ft.Chip(
                        leading=ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED, size=14),
                        label=ft.Text(
                            formatear_antelacion(rec.antelacion_minutos), size=11
                        ),
                    )
                )
            for cid in tarea.contacto_ids:
                if cid in mapa_contactos:
                    chips.append(
                        ft.Chip(
                            leading=ft.Icon(ft.Icons.PERSON_OUTLINE, size=14),
                            label=ft.Text(mapa_contactos[cid].nombre, size=11),
                        )
                    )

            async def _toggle_completada(
                e: ft.Event[ft.Checkbox], t_id: UUID = tarea.id
            ) -> None:
                if e.control.value:
                    await self._contenedor.servicio_tareas.completar_tarea(t_id)
                else:
                    await self._contenedor.servicio_tareas.reactivar_tarea(t_id)
                self.refrescar()

            cuerpo_col: list[ft.Control] = [
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            expand=True,
                            spacing=6,
                            controls=[
                                ft.Checkbox(
                                    value=tarea.esta_completada,
                                    on_change=_toggle_completada,
                                ),
                                ft.Column(
                                    spacing=2,
                                    expand=True,
                                    controls=[
                                        ft.Text(
                                            tarea.titulo,
                                            size=15,
                                            weight=ft.FontWeight.W_600,
                                            style=(
                                                ft.TextStyle(
                                                    decoration=ft.TextDecoration.LINE_THROUGH
                                                )
                                                if tarea.esta_completada
                                                else None
                                            ),
                                        ),
                                        ft.Text(
                                            (
                                                f"Vence: {formatear_fecha_hora(tarea.fecha_limite, formato_24h=ajustes.formato_24h)}"
                                                if tarea.fecha_limite
                                                else "Sin fecha límite"
                                            ),
                                            size=12,
                                            color=(
                                                ft.Colors.ERROR
                                                if vencida
                                                else ft.Colors.ON_SURFACE_VARIANT
                                            ),
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        ft.Row(
                            spacing=2,
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.EDIT_OUTLINED,
                                    tooltip="Editar tarea",
                                    on_click=lambda _, t=tarea: abrir_formulario_tarea(
                                        self._page,
                                        self._contenedor,
                                        tarea_editar=t,
                                        on_guardada=self._tras_cambio,
                                    ),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    icon_color=ft.Colors.ERROR,
                                    tooltip="Eliminar tarea",
                                    on_click=lambda _, t=tarea: self._confirmar_eliminar(t),
                                ),
                            ],
                        ),
                    ],
                )
            ]

            if tarea.descripcion:
                cuerpo_col.append(ft.Text(tarea.descripcion, size=12.5))
            cuerpo_col.append(ft.Row(wrap=True, spacing=6, controls=chips))

            self._lista.controls.append(
                ft.Container(
                    padding=12,
                    border_radius=12,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                    border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                    content=ft.Column(spacing=6, controls=cuerpo_col),
                )
            )

        self._page.update()

    def _cambiar_estado(self, e: ft.Event[ft.Dropdown]) -> None:
        self._filtro_estado = EstadoTarea(e.control.value) if e.control.value else None
        self.refrescar()

    def _cambiar_prioridad(self, e: ft.Event[ft.Dropdown]) -> None:
        self._filtro_prioridad = (
            PrioridadTarea(e.control.value) if e.control.value else None
        )
        self.refrescar()

    def _cambiar_cat(self, e: ft.Event[ft.Dropdown]) -> None:
        self._filtro_cat = UUID(e.control.value) if e.control.value else None
        self.refrescar()

    def _confirmar_eliminar(self, tarea: Tarea) -> None:
        async def _eliminar(_: ft.Event) -> None:
            await self._contenedor.servicio_tareas.eliminar_tarea(tarea.id)
            self._page.pop_dialog()
            self.refrescar()

        self._page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Eliminar tarea"),
                content=ft.Text(f"¿Deseas eliminar la tarea '{tarea.titulo}'?"),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda _: self._page.pop_dialog()),
                    ft.FilledButton("Eliminar", on_click=_eliminar),
                ],
            )
        )

    async def _tras_cambio(self) -> None:
        self.refrescar()

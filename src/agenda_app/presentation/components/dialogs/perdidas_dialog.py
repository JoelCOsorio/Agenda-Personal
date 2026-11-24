"""Diálogo de Bandeja de Notificaciones Perdidas (RN-05, RN-14)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

import flet as ft

from agenda_app.container import ContenedorAplicacion
from agenda_app.domain.enums import TipoOrigenRecordatorio
from agenda_app.presentation.formatters import formatear_fecha_hora


def abrir_dialogo_perdidas(
    page: ft.Page,
    contenedor: ContenedorAplicacion,
    *,
    on_cambio: Callable[[], Awaitable[None]],
) -> None:
    """Despliega las notificaciones marcadas como PERDIDO con opciones Posponer y Visto."""
    ajustes = contenedor.servicio_ajustes.obtener()
    lista = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, tight=True)

    def _recargar_lista() -> None:
        perdidos = contenedor.repo_recordatorios.obtener_perdidos()
        lista.controls.clear()

        if not perdidos:
            lista.controls.append(
                ft.Container(
                    padding=ft.Padding.symmetric(vertical=20),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=ft.Colors.PRIMARY),
                            ft.Text("No tienes notificaciones perdidas pendientes."),
                        ],
                    ),
                )
            )
            return

        for rec in perdidos:
            titulo = _resolver_titulo(contenedor, rec.tipo_origen, rec.item_id)
            tipo_txt = (
                "Evento" if rec.tipo_origen == TipoOrigenRecordatorio.EVENTO else "Tarea"
            )
            fecha_txt = formatear_fecha_hora(
                rec.fecha_disparo, formato_24h=ajustes.formato_24h
            )

            async def _posponer(
                _: ft.Event, rid: UUID = rec.id
            ) -> None:
                await contenedor.motor.posponer_recordatorio(rid)
                _recargar_lista()
                await on_cambio()
                page.update()

            async def _marcar_vista(
                _: ft.Event, rid: UUID = rec.id
            ) -> None:
                await contenedor.motor.marcar_atendido(rid)
                _recargar_lista()
                await on_cambio()
                page.update()

            lista.controls.append(
                ft.Container(
                    padding=12,
                    border_radius=10,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                    border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                    content=ft.Column(
                        spacing=6,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(
                                        titulo,
                                        weight=ft.FontWeight.W_600,
                                        expand=True,
                                    ),
                                    ft.Chip(label=ft.Text(tipo_txt, size=11)),
                                ],
                            ),
                            ft.Text(
                                f"Debió sonar: {fecha_txt}",
                                size=12,
                                color=ft.Colors.ERROR,
                            ),
                            ft.Row(
                                alignment=ft.MainAxisAlignment.END,
                                spacing=8,
                                controls=[
                                    ft.OutlinedButton(
                                        f"Posponer (+{ajustes.minutos_posponer_defecto}m)",
                                        icon=ft.Icons.SNOOZE,
                                        on_click=_posponer,
                                    ),
                                    ft.FilledButton(
                                        "Marcar vista",
                                        icon=ft.Icons.DONE,
                                        on_click=_marcar_vista,
                                    ),
                                ],
                            ),
                        ],
                    ),
                )
            )

    _recargar_lista()

    dialogo = ft.AlertDialog(
        modal=False,
        title=ft.Row(
            spacing=8,
            controls=[
                ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE, color=ft.Colors.ERROR),
                ft.Text("Notificaciones perdidas"),
            ],
        ),
        content=ft.Container(width=460, height=340, content=lista),
        actions=[
            ft.TextButton("Cerrar", on_click=lambda _: page.pop_dialog()),
        ],
    )
    page.show_dialog(dialogo)


def _resolver_titulo(
    contenedor: ContenedorAplicacion,
    tipo: TipoOrigenRecordatorio,
    item_id: UUID,
) -> str:
    if tipo == TipoOrigenRecordatorio.EVENTO:
        ev = contenedor.servicio_eventos.obtener_evento(item_id)
        return ev.titulo if ev else "Evento de Agenda"
    tar = contenedor.servicio_tareas.obtener_tarea(item_id)
    return tar.titulo if tar else "Tarea Pendiente"

"""Vista Semanal de 7 columnas (RF-05, PROC-02)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import date
from uuid import UUID

import flet as ft

from agenda_app.domain.entities.evento import Evento
from agenda_app.domain.rules.recurrencia import OcurrenciaEvento
from agenda_app.presentation.formatters import (
    DIAS_CORTOS_ES,
    formatear_rango_evento,
    rango_semana,
    utc_a_local,
)


def construir_vista_semana(
    *,
    fecha_seleccionada: date,
    hoy: date,
    primer_dia_semana: int,
    ocurrencias: list[OcurrenciaEvento],
    colores_categoria: dict[UUID, str],
    formato_24h: bool,
    on_seleccionar_dia: Callable[[date], None],
    on_editar: Callable[[Evento], None],
) -> ft.Control:
    dias = rango_semana(fecha_seleccionada, primer_dia_semana)
    por_dia: dict[date, list[OcurrenciaEvento]] = defaultdict(list)
    for oc in ocurrencias:
        por_dia[utc_a_local(oc.inicio).date()].append(oc)

    columnas: list[ft.Control] = []
    for dia in dias:
        es_hoy = dia == hoy
        items = por_dia.get(dia, [])

        tarjetas_dia: list[ft.Control] = []
        for oc in items:
            ev = oc.evento
            color = (
                ev.color_hex
                or (colores_categoria.get(ev.categoria_id) if ev.categoria_id else None)
                or "#3B82F6"
            )
            rango_txt = formatear_rango_evento(
                oc.inicio, oc.fin, todo_el_dia=ev.todo_el_dia, formato_24h=formato_24h
            )
            tarjetas_dia.append(
                ft.Container(
                    padding=8,
                    border_radius=8,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                    border=ft.Border(left=ft.BorderSide(4, color)),
                    on_click=lambda _, e_obj=ev: on_editar(e_obj),
                    content=ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(
                                ev.titulo,
                                size=12.5,
                                weight=ft.FontWeight.W_600,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(rango_txt, size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                        ],
                    ),
                )
            )

        if not tarjetas_dia:
            tarjetas_dia.append(
                ft.Text("Libre", size=11, color=ft.Colors.ON_SURFACE_VARIANT, italic=True)
            )

        columnas.append(
            ft.Container(
                width=165,
                padding=10,
                border_radius=12,
                bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                border=(
                    ft.Border.all(2, ft.Colors.PRIMARY)
                    if es_hoy
                    else ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
                ),
                content=ft.Column(
                    spacing=8,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        ft.Container(
                            on_click=lambda _, d=dia: on_seleccionar_dia(d),
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(
                                        DIAS_CORTOS_ES[dia.weekday()],
                                        weight=ft.FontWeight.W_600,
                                        color=ft.Colors.PRIMARY if es_hoy else None,
                                    ),
                                    ft.Text(
                                        f"{dia.day:02d}/{dia.month:02d}",
                                        size=12,
                                        weight=ft.FontWeight.BOLD if es_hoy else ft.FontWeight.NORMAL,
                                    ),
                                ],
                            ),
                        ),
                        ft.Divider(height=1),
                        *tarjetas_dia,
                    ],
                ),
            )
        )

    return ft.Row(
        expand=True,
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=columnas,
    )

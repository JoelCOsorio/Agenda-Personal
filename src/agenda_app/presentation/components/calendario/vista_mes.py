"""Vista Mensual estilo calendario con panel de detalle del día seleccionado (RF-05)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import date
from uuid import UUID

import flet as ft

from agenda_app.domain.entities.contacto import Contacto
from agenda_app.domain.entities.evento import Evento
from agenda_app.domain.rules.recurrencia import OcurrenciaEvento
from agenda_app.presentation.components.calendario.vista_dia import construir_vista_dia
from agenda_app.presentation.formatters import (
    encabezados_dias_semana,
    generar_cuadricula_mes,
    utc_a_local,
)


def construir_vista_mes(
    *,
    fecha_seleccionada: date,
    hoy: date,
    primer_dia_semana: int,
    ocurrencias: list[OcurrenciaEvento],
    colores_categoria: dict[UUID, str],
    nombres_categoria: dict[UUID, str],
    mapa_contactos: dict[UUID, Contacto],
    formato_24h: bool,
    on_seleccionar_dia: Callable[[date], None],
    on_editar: Callable[[Evento], None],
    on_eliminar: Callable[[Evento], Awaitable[None]],
) -> ft.Control:
    por_dia: dict[date, list[OcurrenciaEvento]] = defaultdict(list)
    for oc in ocurrencias:
        dia_local = utc_a_local(oc.inicio).date()
        por_dia[dia_local].append(oc)

    semanas = generar_cuadricula_mes(
        fecha_seleccionada.year,
        fecha_seleccionada.month,
        primer_dia_semana=primer_dia_semana,
    )
    encabezados = encabezados_dias_semana(primer_dia_semana)

    filas_calendario: list[ft.Control] = [
        ft.Row(
            spacing=4,
            controls=[
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment.CENTER,
                    padding=ft.Padding.symmetric(vertical=6),
                    content=ft.Text(
                        dia_nombre,
                        size=12,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                )
                for dia_nombre in encabezados
            ],
        )
    ]

    for semana in semanas:
        celdas: list[ft.Control] = []
        for dia in semana:
            es_mes_actual = dia.month == fecha_seleccionada.month
            es_hoy = dia == hoy
            es_sel = dia == fecha_seleccionada
            eventos_dia = por_dia.get(dia, [])

            puntos: list[ft.Control] = []
            for oc in eventos_dia[:3]:
                c = (
                    oc.evento.color_hex
                    or (
                        colores_categoria.get(oc.evento.categoria_id)
                        if oc.evento.categoria_id
                        else None
                    )
                    or "#3B82F6"
                )
                puntos.append(
                    ft.Container(width=6, height=6, border_radius=3, bgcolor=c)
                )
            if len(eventos_dia) > 3:
                puntos.append(ft.Text(f"+{len(eventos_dia) - 3}", size=9))

            bgcolor = (
                ft.Colors.PRIMARY_CONTAINER
                if es_sel
                else (
                    ft.Colors.SURFACE_CONTAINER_LOW
                    if es_mes_actual
                    else ft.Colors.TRANSPARENT
                )
            )
            borde = (
                ft.Border.all(2, ft.Colors.PRIMARY)
                if es_hoy
                else ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
            )

            celdas.append(
                ft.Container(
                    expand=True,
                    height=58,
                    padding=4,
                    border_radius=8,
                    bgcolor=bgcolor,
                    border=borde,
                    on_click=lambda _, d=dia: on_seleccionar_dia(d),
                    content=ft.Column(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=2,
                        controls=[
                            ft.Text(
                                str(dia.day),
                                size=13,
                                weight=(
                                    ft.FontWeight.BOLD
                                    if (es_hoy or es_sel)
                                    else ft.FontWeight.NORMAL
                                ),
                                color=(
                                    ft.Colors.ON_PRIMARY_CONTAINER
                                    if es_sel
                                    else (
                                        None
                                        if es_mes_actual
                                        else ft.Colors.ON_SURFACE_VARIANT
                                    )
                                ),
                            ),
                            ft.Row(
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=3,
                                controls=puntos,
                            ),
                        ],
                    ),
                )
            )
        filas_calendario.append(ft.Row(spacing=4, controls=celdas))

    grid_card = ft.Container(
        padding=10,
        border_radius=12,
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        content=ft.Column(spacing=4, controls=filas_calendario),
    )

    detalle_dia = construir_vista_dia(
        fecha=fecha_seleccionada,
        ocurrencias=por_dia.get(fecha_seleccionada, []),
        colores_categoria=colores_categoria,
        nombres_categoria=nombres_categoria,
        mapa_contactos=mapa_contactos,
        formato_24h=formato_24h,
        on_editar=on_editar,
        on_eliminar=on_eliminar,
    )

    return ft.Column(
        expand=True,
        spacing=12,
        controls=[
            grid_card,
            ft.Divider(height=1),
            ft.Container(expand=True, content=detalle_dia),
        ],
    )

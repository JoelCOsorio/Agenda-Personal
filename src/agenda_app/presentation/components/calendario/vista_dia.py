"""Vista Diaria cronológica de eventos (RF-05, PROC-02)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date
from uuid import UUID

import flet as ft

from agenda_app.domain.entities.contacto import Contacto
from agenda_app.domain.entities.evento import Evento
from agenda_app.domain.rules.recurrencia import OcurrenciaEvento
from agenda_app.presentation.formatters import (
    DIAS_LARGOS_ES,
    MESES_ES,
    etiqueta_frecuencia,
    formatear_rango_evento,
)


def construir_vista_dia(
    *,
    fecha: date,
    ocurrencias: list[OcurrenciaEvento],
    colores_categoria: dict[UUID, str],
    nombres_categoria: dict[UUID, str],
    mapa_contactos: dict[UUID, Contacto],
    formato_24h: bool,
    on_editar: Callable[[Evento], None],
    on_eliminar: Callable[[Evento], Awaitable[None]],
) -> ft.Control:
    encabezado = ft.Text(
        f"{DIAS_LARGOS_ES[fecha.weekday()]}, {fecha.day} de {MESES_ES[fecha.month]} de {fecha.year}",
        size=17,
        weight=ft.FontWeight.W_600,
    )

    todo_dia = [o for o in ocurrencias if o.evento.todo_el_dia]
    con_hora = [o for o in ocurrencias if not o.evento.todo_el_dia]

    controles: list[ft.Control] = [encabezado]

    if not ocurrencias:
        controles.append(
            ft.Container(
                padding=ft.Padding.symmetric(vertical=40),
                alignment=ft.Alignment.CENTER,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                    controls=[
                        ft.Icon(
                            ft.Icons.EVENT_AVAILABLE_OUTLINED,
                            size=42,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Text(
                            "No hay eventos programados para este día.",
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    ],
                ),
            )
        )
        return ft.Column(expand=True, spacing=12, controls=controles)

    if todo_dia:
        controles.append(ft.Text("Todo el día", size=12, weight=ft.FontWeight.W_600))
        for oc in todo_dia:
            controles.append(
                _tarjeta_evento(
                    oc,
                    colores_categoria=colores_categoria,
                    nombres_categoria=nombres_categoria,
                    mapa_contactos=mapa_contactos,
                    formato_24h=formato_24h,
                    on_editar=on_editar,
                    on_eliminar=on_eliminar,
                )
            )

    if con_hora:
        controles.append(ft.Text("Horario", size=12, weight=ft.FontWeight.W_600))
        for oc in con_hora:
            controles.append(
                _tarjeta_evento(
                    oc,
                    colores_categoria=colores_categoria,
                    nombres_categoria=nombres_categoria,
                    mapa_contactos=mapa_contactos,
                    formato_24h=formato_24h,
                    on_editar=on_editar,
                    on_eliminar=on_eliminar,
                )
            )

    return ft.ListView(expand=True, spacing=10, controls=controles)


def _tarjeta_evento(
    oc: OcurrenciaEvento,
    *,
    colores_categoria: dict[UUID, str],
    nombres_categoria: dict[UUID, str],
    mapa_contactos: dict[UUID, Contacto],
    formato_24h: bool,
    on_editar: Callable[[Evento], None],
    on_eliminar: Callable[[Evento], Awaitable[None]],
) -> ft.Control:
    ev = oc.evento
    color = (
        ev.color_hex
        or (colores_categoria.get(ev.categoria_id) if ev.categoria_id else None)
        or "#3B82F6"
    )
    rango_txt = formatear_rango_evento(
        oc.inicio, oc.fin, todo_el_dia=ev.todo_el_dia, formato_24h=formato_24h
    )

    etiquetas: list[ft.Control] = []
    if ev.categoria_id and ev.categoria_id in nombres_categoria:
        etiquetas.append(
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                border_radius=12,
                bgcolor=color,
                content=ft.Text(nombres_categoria[ev.categoria_id], size=11, color="#FFFFFF"),
            )
        )
    if ev.recurrencia is not None:
        etiquetas.append(
            ft.Chip(
                label=ft.Text(etiqueta_frecuencia(ev.recurrencia.frecuencia), size=11),
                leading=ft.Icon(ft.Icons.REPEAT, size=14),
            )
        )
    for cid in ev.contacto_ids:
        contacto = mapa_contactos.get(cid)
        if contacto:
            etiquetas.append(
                ft.Chip(
                    label=ft.Text(contacto.nombre, size=11),
                    leading=ft.Icon(ft.Icons.PERSON_OUTLINE, size=14),
                )
            )

    detalles: list[ft.Control] = [
        ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column(
                    spacing=2,
                    expand=True,
                    controls=[
                        ft.Text(ev.titulo, size=15, weight=ft.FontWeight.W_600),
                        ft.Text(rango_txt, size=12, color=ft.Colors.PRIMARY),
                    ],
                ),
                ft.Row(
                    spacing=2,
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.EDIT_OUTLINED,
                            tooltip="Editar evento",
                            on_click=lambda _, e_obj=ev: on_editar(e_obj),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_color=ft.Colors.ERROR,
                            tooltip="Eliminar evento",
                            on_click=lambda _, e_obj=ev: on_eliminar(e_obj),
                        ),
                    ],
                ),
            ],
        )
    ]

    if ev.ubicacion:
        detalles.append(
            ft.Row(
                spacing=4,
                controls=[
                    ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, size=15, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text(ev.ubicacion, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                ],
            )
        )
    if ev.descripcion:
        detalles.append(ft.Text(ev.descripcion, size=12.5))
    if etiquetas:
        detalles.append(ft.Row(wrap=True, spacing=6, controls=etiquetas))

    return ft.Container(
        padding=12,
        border_radius=12,
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        border=ft.Border(
            left=ft.BorderSide(5, color),
            top=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            right=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
        ),
        content=ft.Column(spacing=6, controls=detalles),
    )

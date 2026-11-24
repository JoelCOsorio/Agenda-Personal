"""Vista Anual (12 meses con mapa de densidad de eventos — RF-05)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from datetime import date

import flet as ft

from agenda_app.domain.rules.recurrencia import OcurrenciaEvento
from agenda_app.presentation.formatters import (
    MESES_ES,
    encabezados_dias_semana,
    generar_cuadricula_mes,
    utc_a_local,
)


def construir_vista_anio(
    *,
    anio: int,
    hoy: date,
    primer_dia_semana: int,
    ocurrencias: list[OcurrenciaEvento],
    on_seleccionar_mes: Callable[[int], None],
    on_seleccionar_dia: Callable[[date], None],
) -> ft.Control:
    conteo_por_dia: Counter[date] = Counter(
        utc_a_local(oc.inicio).date() for oc in ocurrencias
    )
    letras_dias = [d[0] for d in encabezados_dias_semana(primer_dia_semana)]

    tarjetas_meses: list[ft.Control] = []
    for mes in range(1, 13):
        semanas = generar_cuadricula_mes(anio, mes, primer_dia_semana=primer_dia_semana)
        total_mes = sum(
            c for d, c in conteo_por_dia.items() if d.year == anio and d.month == mes
        )

        filas: list[ft.Control] = [
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(MESES_ES[mes], size=13, weight=ft.FontWeight.W_600),
                    ft.Text(
                        f"{total_mes} ev." if total_mes else "",
                        size=11,
                        color=ft.Colors.PRIMARY,
                    ),
                ],
            ),
            ft.Row(
                spacing=2,
                controls=[
                    ft.Container(
                        width=24,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text(
                            letra, size=10, color=ft.Colors.ON_SURFACE_VARIANT
                        ),
                    )
                    for letra in letras_dias
                ],
            ),
        ]

        for semana in semanas:
            celdas: list[ft.Control] = []
            for dia in semana:
                en_mes = dia.month == mes
                n = conteo_por_dia.get(dia, 0) if en_mes else 0
                if not en_mes:
                    celdas.append(ft.Container(width=24, height=22))
                    continue

                bgcolor = None
                texto_color = None
                if n >= 2:
                    bgcolor = ft.Colors.PRIMARY
                    texto_color = ft.Colors.ON_PRIMARY
                elif n == 1:
                    bgcolor = ft.Colors.PRIMARY_CONTAINER
                    texto_color = ft.Colors.ON_PRIMARY_CONTAINER

                celdas.append(
                    ft.Container(
                        width=24,
                        height=22,
                        border_radius=5,
                        bgcolor=bgcolor,
                        border=ft.Border.all(1.5, ft.Colors.PRIMARY)
                        if dia == hoy
                        else None,
                        alignment=ft.Alignment.CENTER,
                        on_click=lambda _, d=dia: on_seleccionar_dia(d),
                        content=ft.Text(
                            str(dia.day),
                            size=10,
                            color=texto_color,
                            weight=ft.FontWeight.BOLD if dia == hoy else ft.FontWeight.NORMAL,
                        ),
                    )
                )
            filas.append(ft.Row(spacing=2, controls=celdas))

        tarjetas_meses.append(
            ft.Container(
                width=206,
                padding=10,
                border_radius=12,
                bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                on_click=lambda _, m=mes: on_seleccionar_mes(m),
                content=ft.Column(spacing=4, controls=filas),
            )
        )

    return ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Row(
                wrap=True,
                spacing=12,
                run_spacing=12,
                alignment=ft.MainAxisAlignment.START,
                controls=tarjetas_meses,
            )
        ],
    )

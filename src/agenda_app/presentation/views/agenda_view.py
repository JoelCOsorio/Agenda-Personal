"""Vista principal del Módulo de Agenda (Día, Semana, Mes, Año + Historial — PROC-01/02)."""

from __future__ import annotations

import calendar
from datetime import date, datetime, time, timedelta
from uuid import UUID

import flet as ft

from agenda_app.container import ContenedorAplicacion
from agenda_app.domain.entities.evento import Evento
from agenda_app.domain.enums import VistaAgenda
from agenda_app.presentation.components.calendario.vista_anio import construir_vista_anio
from agenda_app.presentation.components.calendario.vista_dia import construir_vista_dia
from agenda_app.presentation.components.calendario.vista_mes import construir_vista_mes
from agenda_app.presentation.components.calendario.vista_semana import (
    construir_vista_semana,
)
from agenda_app.presentation.components.dialogs.evento_form_dialog import (
    abrir_formulario_evento,
)
from agenda_app.presentation.formatters import (
    MESES_ES,
    combinar_local_a_utc,
    formatear_fecha_hora,
    generar_cuadricula_mes,
    rango_semana,
    utc_a_local,
)


class AgendaView:
    """Controla la navegación temporal, filtros por categoría y las 4 escalas del calendario."""

    def __init__(self, page: ft.Page, contenedor: ContenedorAplicacion) -> None:
        self._page = page
        self._contenedor = contenedor
        ajustes = contenedor.servicio_ajustes.obtener()
        self._vista_actual: VistaAgenda = ajustes.vista_inicial_agenda
        self._fecha_ref: date = utc_a_local(contenedor.reloj.ahora_utc()).date()
        self._filtro_cat: UUID | None = None

        self._selector_vista = ft.SegmentedButton(
            key="agenda_selector_vista",
            selected=[self._vista_actual.value],
            allow_multiple_selection=False,
            segments=[
                ft.Segment(value=VistaAgenda.DIA.value, label=ft.Text("Día")),
                ft.Segment(value=VistaAgenda.SEMANA.value, label=ft.Text("Semana")),
                ft.Segment(value=VistaAgenda.MES.value, label=ft.Text("Mes")),
                ft.Segment(value=VistaAgenda.ANIO.value, label=ft.Text("Año")),
            ],
            on_change=self._cambiar_vista,
        )
        self._titulo_periodo = ft.Text("", size=18, weight=ft.FontWeight.W_600)
        self._filtro_cat_dd = ft.Dropdown(
            label="Categoría",
            width=190,
            dense=True,
            on_select=self._cambiar_filtro_cat,
        )
        self._cuerpo = ft.Container(expand=True)

        self._raiz = ft.Column(
            expand=True,
            spacing=12,
            controls=[
                ft.Row(
                    wrap=True,
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                    controls=[
                        ft.Row(
                            spacing=4,
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.CHEVRON_LEFT,
                                    tooltip="Anterior",
                                    on_click=lambda _: self._desplazar(-1),
                                ),
                                ft.OutlinedButton("Hoy", on_click=lambda _: self._ir_hoy()),
                                ft.IconButton(
                                    icon=ft.Icons.CHEVRON_RIGHT,
                                    tooltip="Siguiente",
                                    on_click=lambda _: self._desplazar(1),
                                ),
                                self._titulo_periodo,
                            ],
                        ),
                        self._selector_vista,
                    ],
                ),
                ft.Row(
                    wrap=True,
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    spacing=8,
                    controls=[
                        self._filtro_cat_dd,
                        ft.OutlinedButton(
                            "Historial",
                            icon=ft.Icons.HISTORY,
                            on_click=lambda _: self._abrir_historial(),
                        ),
                    ],
                ),
                self._cuerpo,
            ],
        )

    @property
    def control(self) -> ft.Control:
        return self._raiz

    def abrir_creacion(self) -> None:
        abrir_formulario_evento(
            self._page,
            self._contenedor,
            fecha_inicial=self._fecha_ref,
            on_guardado=self._tras_guardar,
        )

    def refrescar(self) -> None:
        ajustes = self._contenedor.servicio_ajustes.obtener()
        hoy = utc_a_local(self._contenedor.reloj.ahora_utc()).date()

        cats = self._contenedor.servicio_categorias.listar_categorias()
        colores_cat = {c.id: c.color_hex for c in cats}
        nombres_cat = {c.id: c.nombre for c in cats}
        mapa_contactos = {
            c.id: c for c in self._contenedor.servicio_contactos.buscar()
        }

        self._filtro_cat_dd.options = [ft.DropdownOption(key="", text="Todas")] + [
            ft.DropdownOption(key=str(c.id), text=c.nombre) for c in cats
        ]
        self._filtro_cat_dd.value = str(self._filtro_cat) if self._filtro_cat else ""

        desde_utc, hasta_utc = self._rango_consulta(ajustes.primer_dia_semana)
        ocurrencias = self._contenedor.servicio_eventos.obtener_ocurrencias_vista(
            desde_utc,
            hasta_utc,
            categoria_id=self._filtro_cat,
        )

        self._actualizar_titulo_periodo()

        if self._vista_actual == VistaAgenda.DIA:
            oc_dia = [
                o for o in ocurrencias if utc_a_local(o.inicio).date() == self._fecha_ref
            ]
            self._cuerpo.content = construir_vista_dia(
                fecha=self._fecha_ref,
                ocurrencias=oc_dia,
                colores_categoria=colores_cat,
                nombres_categoria=nombres_cat,
                mapa_contactos=mapa_contactos,
                formato_24h=ajustes.formato_24h,
                on_editar=self._editar_evento,
                on_eliminar=self._eliminar_evento,
            )
        elif self._vista_actual == VistaAgenda.SEMANA:
            self._cuerpo.content = construir_vista_semana(
                fecha_seleccionada=self._fecha_ref,
                hoy=hoy,
                primer_dia_semana=ajustes.primer_dia_semana,
                ocurrencias=ocurrencias,
                colores_categoria=colores_cat,
                formato_24h=ajustes.formato_24h,
                on_seleccionar_dia=self._saltar_a_dia,
                on_editar=self._editar_evento,
            )
        elif self._vista_actual == VistaAgenda.MES:
            self._cuerpo.content = construir_vista_mes(
                fecha_seleccionada=self._fecha_ref,
                hoy=hoy,
                primer_dia_semana=ajustes.primer_dia_semana,
                ocurrencias=ocurrencias,
                colores_categoria=colores_cat,
                nombres_categoria=nombres_cat,
                mapa_contactos=mapa_contactos,
                formato_24h=ajustes.formato_24h,
                on_seleccionar_dia=self._seleccionar_dia_en_mes,
                on_editar=self._editar_evento,
                on_eliminar=self._eliminar_evento,
            )
        else:
            self._cuerpo.content = construir_vista_anio(
                anio=self._fecha_ref.year,
                hoy=hoy,
                primer_dia_semana=ajustes.primer_dia_semana,
                ocurrencias=ocurrencias,
                on_seleccionar_mes=self._saltar_a_mes,
                on_seleccionar_dia=self._saltar_a_dia,
            )

        self._page.update()

    def _rango_consulta(self, primer_dia: int) -> tuple[datetime, datetime]:
        if self._vista_actual == VistaAgenda.DIA:
            return (
                combinar_local_a_utc(self._fecha_ref, time(0, 0)),
                combinar_local_a_utc(self._fecha_ref, time(23, 59, 59)),
            )
        if self._vista_actual == VistaAgenda.SEMANA:
            dias = rango_semana(self._fecha_ref, primer_dia)
            return (
                combinar_local_a_utc(dias[0], time(0, 0)),
                combinar_local_a_utc(dias[-1], time(23, 59, 59)),
            )
        if self._vista_actual == VistaAgenda.MES:
            semanas = generar_cuadricula_mes(
                self._fecha_ref.year, self._fecha_ref.month, primer_dia
            )
            return (
                combinar_local_a_utc(semanas[0][0], time(0, 0)),
                combinar_local_a_utc(semanas[-1][-1], time(23, 59, 59)),
            )
        return (
            combinar_local_a_utc(date(self._fecha_ref.year, 1, 1), time(0, 0)),
            combinar_local_a_utc(date(self._fecha_ref.year, 12, 31), time(23, 59, 59)),
        )

    def _actualizar_titulo_periodo(self) -> None:
        if self._vista_actual == VistaAgenda.ANIO:
            self._titulo_periodo.value = str(self._fecha_ref.year)
        else:
            self._titulo_periodo.value = (
                f"{MESES_ES[self._fecha_ref.month]} {self._fecha_ref.year}"
            )

    def _cambiar_vista(self, e: ft.Event[ft.SegmentedButton]) -> None:
        if e.control.selected:
            self._vista_actual = VistaAgenda(e.control.selected[0])
            self.refrescar()

    def _cambiar_filtro_cat(self, e: ft.Event[ft.Dropdown]) -> None:
        self._filtro_cat = UUID(e.control.value) if e.control.value else None
        self.refrescar()

    def _ir_hoy(self) -> None:
        self._fecha_ref = utc_a_local(self._contenedor.reloj.ahora_utc()).date()
        self.refrescar()

    def _desplazar(self, direccion: int) -> None:
        if self._vista_actual == VistaAgenda.DIA:
            self._fecha_ref += timedelta(days=direccion)
        elif self._vista_actual == VistaAgenda.SEMANA:
            self._fecha_ref += timedelta(weeks=direccion)
        elif self._vista_actual == VistaAgenda.MES:
            mes_idx = self._fecha_ref.month - 1 + direccion
            anio = self._fecha_ref.year + mes_idx // 12
            mes = (mes_idx % 12) + 1
            ultimo = calendar.monthrange(anio, mes)[1]
            self._fecha_ref = date(anio, mes, min(self._fecha_ref.day, ultimo))
        else:
            self._fecha_ref = date(self._fecha_ref.year + direccion, self._fecha_ref.month, 1)
        self.refrescar()

    def _seleccionar_dia_en_mes(self, dia: date) -> None:
        self._fecha_ref = dia
        self.refrescar()

    def _saltar_a_dia(self, dia: date) -> None:
        self._fecha_ref = dia
        self._vista_actual = VistaAgenda.DIA
        self._selector_vista.selected = [VistaAgenda.DIA.value]
        self.refrescar()

    def _saltar_a_mes(self, mes: int) -> None:
        self._fecha_ref = date(self._fecha_ref.year, mes, 1)
        self._vista_actual = VistaAgenda.MES
        self._selector_vista.selected = [VistaAgenda.MES.value]
        self.refrescar()

    def _editar_evento(self, evento: Evento) -> None:
        abrir_formulario_evento(
            self._page,
            self._contenedor,
            evento_editar=evento,
            on_guardado=self._tras_guardar,
        )

    async def _eliminar_evento(self, evento: Evento) -> None:
        async def _confirmar(_: ft.Event) -> None:
            await self._contenedor.servicio_eventos.eliminar_evento(evento.id)
            self._page.pop_dialog()
            self.refrescar()

        dialogo = ft.AlertDialog(
            modal=True,
            title=ft.Text("Eliminar evento"),
            content=ft.Text(
                f"¿Deseas eliminar '{evento.titulo}'? Su recordatorio pendiente también se cancelará."
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: self._page.pop_dialog()),
                ft.FilledButton("Eliminar", on_click=_confirmar),
            ],
        )
        self._page.show_dialog(dialogo)

    def _abrir_historial(self) -> None:
        ajustes = self._contenedor.servicio_ajustes.obtener()
        pasados = self._contenedor.servicio_eventos.obtener_historial()
        controles: list[ft.Control] = []

        if not pasados:
            controles.append(
                ft.Text(
                    "No hay eventos pasados en el historial todavía.",
                    color=ft.Colors.ON_SURFACE_VARIANT,
                )
            )
        else:
            for ev in pasados:
                controles.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.EVENT_NOTE),
                        title=ft.Text(ev.titulo),
                        subtitle=ft.Text(
                            formatear_fecha_hora(
                                ev.fecha_inicio, formato_24h=ajustes.formato_24h
                            )
                        ),
                    )
                )

        dialogo = ft.AlertDialog(
            title=ft.Text("Historial de eventos pasados"),
            content=ft.Container(
                width=460,
                height=360,
                content=ft.ListView(spacing=4, controls=controles),
            ),
            actions=[ft.TextButton("Cerrar", on_click=lambda _: self._page.pop_dialog())],
        )
        self._page.show_dialog(dialogo)

    async def _tras_guardar(self) -> None:
        self.refrescar()

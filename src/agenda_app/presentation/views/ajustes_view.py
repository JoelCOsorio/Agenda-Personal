"""Vista de Configuración / Ajustes en vivo y diagnóstico del SO (PROC-06, RN-14, RF-23/24)."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from agenda_app.container import ContenedorAplicacion
from agenda_app.domain.enums import VistaAgenda
from agenda_app.domain.exceptions import DominioError
from agenda_app.presentation.components.dialogs.categoria_dialog import (
    abrir_gestor_categorias,
)
from agenda_app.presentation.formatters import (
    DIAS_LARGOS_ES,
    OPCIONES_ANTELACION_MIN,
    etiqueta_vista_agenda,
)


class AjustesView:
    """Parametriza notificaciones, calendario, tema claro/oscuro y gestor de categorías."""

    def __init__(
        self,
        page: ft.Page,
        contenedor: ContenedorAplicacion,
        *,
        on_ajustes_actualizados: Callable[[], None],
    ) -> None:
        self._page = page
        self._contenedor = contenedor
        self._on_ajustes_actualizados = on_ajustes_actualizados

        self._tema_oscuro_sw = ft.Switch(
            key="switch_tema_oscuro",
            label="Modo oscuro",
            on_change=self._guardar_switch_tema,
        )
        self._formato_24h_sw = ft.Switch(
            label="Formato de 24 horas",
            on_change=self._guardar_preferencias,
        )
        self._sonido_sw = ft.Switch(
            label="Sonido en notificaciones",
            on_change=self._guardar_preferencias,
        )
        self._perdidas_inicio_sw = ft.Switch(
            label="Mostrar alertas perdidas al iniciar",
            on_change=self._guardar_preferencias,
        )
        self._snooze_field = ft.TextField(
            label="Posponer por defecto (minutos)",
            width=230,
            dense=True,
        )
        self._antelacion_dd = ft.Dropdown(
            label="Recordatorio predeterminado",
            width=260,
            dense=True,
            options=[
                ft.DropdownOption(key=str(v), text=lbl)
                for v, lbl in OPCIONES_ANTELACION_MIN
                if v is not None
            ],
            on_select=self._guardar_preferencias,
        )
        self._primer_dia_dd = ft.Dropdown(
            label="Primer día de la semana",
            width=220,
            dense=True,
            options=[
                ft.DropdownOption(key=str(i + 1), text=nombre)
                for i, nombre in enumerate(DIAS_LARGOS_ES)
            ],
            on_select=self._guardar_preferencias,
        )
        self._vista_inicial_dd = ft.Dropdown(
            label="Vista inicial de Agenda",
            width=220,
            dense=True,
            options=[
                ft.DropdownOption(key=v.value, text=etiqueta_vista_agenda(v))
                for v in VistaAgenda
            ],
            on_select=self._guardar_preferencias,
        )
        self._diag_txt = ft.Text("Consultando capacidades del sistema...", size=12.5)

        self._raiz = ft.ListView(
            expand=True,
            spacing=14,
            controls=[
                self._tarjeta_seccion(
                    "Apariencia y Calendario",
                    ft.Icons.PALETTE_OUTLINED,
                    [
                        self._tema_oscuro_sw,
                        self._formato_24h_sw,
                        ft.Row(
                            wrap=True,
                            spacing=12,
                            controls=[self._primer_dia_dd, self._vista_inicial_dd],
                        ),
                    ],
                ),
                self._tarjeta_seccion(
                    "Notificaciones",
                    ft.Icons.NOTIFICATIONS_OUTLINED,
                    [
                        self._sonido_sw,
                        self._perdidas_inicio_sw,
                        ft.Row(
                            wrap=True,
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                self._snooze_field,
                                ft.FilledTonalButton(
                                    "Aplicar Snooze",
                                    on_click=self._guardar_preferencias,
                                ),
                            ],
                        ),
                        self._antelacion_dd,
                        ft.Divider(height=1),
                        ft.Text("Diagnóstico de Plataforma", weight=ft.FontWeight.W_600, size=13),
                        self._diag_txt,
                        ft.OutlinedButton(
                            "Verificar / Solicitar permisos del SO",
                            icon=ft.Icons.SECURITY_OUTLINED,
                            on_click=self._solicitar_permisos,
                        ),
                    ],
                ),
                self._tarjeta_seccion(
                    "Organización Académica y Personal",
                    ft.Icons.CATEGORY_OUTLINED,
                    [
                        ft.Text(
                            "Administra tus categorías principales (ej. Universidad, Personal) y subcategorías (materias).",
                            size=12.5,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.FilledTonalButton(
                            "Gestionar categorías y subcategorías",
                            icon=ft.Icons.EDIT_ATTRIBUTES_OUTLINED,
                            on_click=lambda _: abrir_gestor_categorias(
                                self._page,
                                self._contenedor,
                                on_cambio=self._on_ajustes_actualizados,
                            ),
                        ),
                    ],
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.END,
                    controls=[
                        ft.OutlinedButton(
                            "Restablecer valores por defecto",
                            icon=ft.Icons.RESTORE,
                            on_click=self._restablecer,
                        )
                    ],
                ),
            ],
        )

    @property
    def control(self) -> ft.Control:
        return self._raiz

    async def refrescar(self) -> None:
        cfg = self._contenedor.servicio_ajustes.obtener()
        self._tema_oscuro_sw.value = cfg.tema_oscuro
        self._formato_24h_sw.value = cfg.formato_24h
        self._sonido_sw.value = cfg.sonido_notificaciones
        self._perdidas_inicio_sw.value = cfg.mostrar_alertas_perdidas_inicio
        self._snooze_field.value = str(cfg.minutos_posponer_defecto)
        self._antelacion_dd.value = str(cfg.antelacion_recordatorio_defecto_min)
        self._primer_dia_dd.value = str(cfg.primer_dia_semana)
        self._vista_inicial_dd.value = cfg.vista_inicial_agenda.value

        caps = await self._contenedor.adaptador.obtener_capacidades()
        self._diag_txt.value = (
            f"Sistema detectado: {caps.plataforma.value} | "
            f"Acciones rápidas: {'Sí' if caps.soporta_acciones_rapidas else 'No soportado en este entorno'} | "
            f"Alarmas exactas: {'Sí' if caps.soporta_alarmas_exactas else 'Inexactas'} | "
            f"Base de datos: {self._contenedor.db.db_path}"
        )
        self._page.update()

    def _guardar_switch_tema(self, _: ft.Event) -> None:
        self._guardar_preferencias(None)

    def _guardar_preferencias(self, _: ft.Event | None) -> None:
        try:
            snooze = int(self._snooze_field.value or "10")
            antelacion = int(self._antelacion_dd.value or "15")
            primer_dia = int(self._primer_dia_dd.value or "1")
            vista_ini = VistaAgenda(self._vista_inicial_dd.value or VistaAgenda.MES.value)

            self._contenedor.servicio_ajustes.actualizar(
                tema_oscuro=bool(self._tema_oscuro_sw.value),
                formato_24h=bool(self._formato_24h_sw.value),
                sonido_notificaciones=bool(self._sonido_sw.value),
                mostrar_alertas_perdidas_inicio=bool(self._perdidas_inicio_sw.value),
                minutos_posponer_defecto=snooze,
                antelacion_recordatorio_defecto_min=antelacion,
                primer_dia_semana=primer_dia,
                vista_inicial_agenda=vista_ini,
            )
            self._on_ajustes_actualizados()
        except (DominioError, ValueError) as exc:
            self._page.show_dialog(ft.SnackBar(ft.Text(f"Error en ajustes: {exc}")))

    async def _solicitar_permisos(self, _: ft.Event) -> None:
        concedido = await self._contenedor.adaptador.solicitar_permisos()
        await self.refrescar()
        msg = "Permisos de notificación activos." if concedido else "Permisos no concedidos por el SO."
        self._page.show_dialog(ft.SnackBar(ft.Text(msg)))

    async def _restablecer(self, _: ft.Event) -> None:
        self._contenedor.servicio_ajustes.restablecer_defaults()
        self._on_ajustes_actualizados()
        await self.refrescar()
        self._page.show_dialog(
            ft.SnackBar(ft.Text("Ajustes restablecidos a valores por defecto."))
        )

    @staticmethod
    def _tarjeta_seccion(
        titulo: str,
        icono: ft.IconData,
        controles: list[ft.Control],
    ) -> ft.Container:
        return ft.Container(
            padding=16,
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(icono, color=ft.Colors.PRIMARY),
                            ft.Text(titulo, size=16, weight=ft.FontWeight.W_600),
                        ],
                    ),
                    *controles,
                ],
            ),
        )

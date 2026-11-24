"""Shell responsivo Material 3: NavigationBar (<760px/Android) y NavigationRail (>=760px)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import flet as ft

BREAKPOINT_ESCRITORIO = 760

DESTINOS: tuple[tuple[str, str, ft.IconData, ft.IconData], ...] = (
    ("agenda", "Agenda", ft.Icons.CALENDAR_MONTH_OUTLINED, ft.Icons.CALENDAR_MONTH),
    ("tareas", "Tareas", ft.Icons.CHECK_CIRCLE_OUTLINE, ft.Icons.CHECK_CIRCLE),
    ("contactos", "Contactos", ft.Icons.CONTACTS_OUTLINED, ft.Icons.CONTACTS),
    ("ajustes", "Ajustes", ft.Icons.SETTINGS_OUTLINED, ft.Icons.SETTINGS),
)

TOOLTIPS_FAB: dict[int, str] = {
    0: "Nuevo evento",
    1: "Nueva tarea",
    2: "Nuevo contacto",
}


class ResponsiveShell:
    """Administra AppBar, NavigationBar/NavigationRail, badge de perdidas y FAB contextual."""

    def __init__(
        self,
        page: ft.Page,
        *,
        on_cambiar_destino: Callable[[int], Awaitable[None]],
        on_abrir_perdidas: Callable[[], Awaitable[None]],
        on_accion_principal: Callable[[int], Awaitable[None]],
    ) -> None:
        self._page = page
        self._on_cambiar_destino = on_cambiar_destino
        self._on_abrir_perdidas = on_abrir_perdidas
        self._on_accion_principal = on_accion_principal
        self._indice_actual = 0
        self._conteo_perdidas = 0

        self._titulo_appbar = ft.Text("Agenda", weight=ft.FontWeight.W_600)
        self._btn_perdidas = ft.IconButton(
            key="btn_perdidas",
            icon=ft.Icons.NOTIFICATIONS_NONE,
            tooltip="Notificaciones perdidas",
            on_click=self._handle_click_perdidas,
        )
        self._contenedor_vista = ft.Container(expand=True, padding=ft.Padding.all(16))

        self._rail = ft.NavigationRail(
            key="nav_rail",
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=84,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=icono,
                    selected_icon=icono_sel,
                    label=etiqueta,
                )
                for _, etiqueta, icono, icono_sel in DESTINOS
            ],
            on_change=self._handle_nav_change,
        )

        self._nav_bar = ft.NavigationBar(
            key="nav_bar",
            selected_index=0,
            destinations=[
                ft.NavigationBarDestination(
                    icon=icono,
                    selected_icon=icono_sel,
                    label=etiqueta,
                )
                for _, etiqueta, icono, icono_sel in DESTINOS
            ],
            on_change=self._handle_nav_change,
        )

        self._fab = ft.FloatingActionButton(
            key="fab_principal",
            icon=ft.Icons.ADD,
            tooltip=TOOLTIPS_FAB[0],
            on_click=self._handle_fab_click,
        )

        self._divisor_rail = ft.VerticalDivider(width=1)
        self._layout_raiz = ft.Row(
            expand=True,
            spacing=0,
            controls=[self._rail, self._divisor_rail, self._contenedor_vista],
        )

        self._page.appbar = ft.AppBar(
            title=self._titulo_appbar,
            center_title=False,
            actions=[self._btn_perdidas],
        )
        self._page.floating_action_button = self._fab
        self._page.on_resize = self._handle_resize

    @property
    def raiz(self) -> ft.Control:
        return ft.SafeArea(expand=True, content=self._layout_raiz)

    @property
    def indice_actual(self) -> int:
        return self._indice_actual

    def montar_vista(self, control: ft.Control, indice: int) -> None:
        self._indice_actual = indice
        self._rail.selected_index = indice
        self._nav_bar.selected_index = indice
        self._titulo_appbar.value = DESTINOS[indice][1]
        self._contenedor_vista.content = control

        # El botón FAB solo aparece en Agenda (0), Tareas (1) y Contactos (2)
        if indice in TOOLTIPS_FAB:
            self._fab.visible = True
            self._fab.tooltip = TOOLTIPS_FAB[indice]
        else:
            self._fab.visible = False

        self.aplicar_modo_responsivo()
        self._page.update()

    def actualizar_conteo_perdidas(self, cantidad: int) -> None:
        self._conteo_perdidas = cantidad
        if cantidad > 0:
            self._btn_perdidas.icon = ft.Icons.NOTIFICATIONS_ACTIVE
            self._btn_perdidas.icon_color = ft.Colors.ERROR
            self._btn_perdidas.badge = ft.Badge(label=str(cantidad))
            self._btn_perdidas.tooltip = f"{cantidad} notificación(es) perdida(s)"
        else:
            self._btn_perdidas.icon = ft.Icons.NOTIFICATIONS_NONE
            self._btn_perdidas.icon_color = None
            self._btn_perdidas.badge = None
            self._btn_perdidas.tooltip = "Sin notificaciones perdidas"
        self._page.update()

    def aplicar_modo_responsivo(self) -> None:
        ancho = self._page.width or 1000
        es_android = self._page.platform in {
            ft.PagePlatform.ANDROID,
            ft.PagePlatform.ANDROID_TV,
        }
        modo_movil = es_android or ancho < BREAKPOINT_ESCRITORIO

        self._rail.visible = not modo_movil
        self._divisor_rail.visible = not modo_movil
        self._page.navigation_bar = self._nav_bar if modo_movil else None

    async def _handle_nav_change(self, e: ft.Event) -> None:
        nuevo = int(e.control.selected_index or 0)
        if nuevo != self._indice_actual:
            await self._on_cambiar_destino(nuevo)

    async def _handle_click_perdidas(self, e: ft.Event[ft.IconButton]) -> None:
        await self._on_abrir_perdidas()

    async def _handle_fab_click(self, e: ft.Event[ft.FloatingActionButton]) -> None:
        await self._on_accion_principal(self._indice_actual)

    def _handle_resize(self, e: ft.Event) -> None:
        self.aplicar_modo_responsivo()
        self._page.update()

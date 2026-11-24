"""Pruebas unitarias rápidas de la capa de Presentación (sin levantar ventana Flutter)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import flet as ft
import pytest

from agenda_app.application.ports.notificaciones import (
    CallbackInteraccion,
    CapacidadesNotificacionSO,
    SolicitudNotificacion,
)
from agenda_app.container import construir_contenedor_aplicacion
from agenda_app.domain.enums import PlataformaSO, VistaAgenda
from agenda_app.presentation.app import AgendaApp


class FakePage:
    def __init__(
        self,
        *,
        width: int = 1024,
        platform: ft.PagePlatform = ft.PagePlatform.LINUX,
    ) -> None:
        self.title = ""
        self.width = width
        self.platform = platform
        self.theme: ft.Theme | None = None
        self.dark_theme: ft.Theme | None = None
        self.theme_mode: ft.ThemeMode | None = None
        self.appbar: ft.AppBar | None = None
        self.navigation_bar: ft.NavigationBar | None = None
        self.floating_action_button: ft.FloatingActionButton | None = None
        self.on_resize = None
        self.on_app_lifecycle_state_change = None
        self.controls: list[ft.Control] = []
        self.dialogs: list[ft.Control] = []
        self.updates = 0

    def add(self, *controls: ft.Control) -> None:
        self.controls.extend(controls)

    def update(self) -> None:
        self.updates += 1

    def show_dialog(self, dialog: ft.Control) -> None:
        self.dialogs.append(dialog)

    def pop_dialog(self) -> ft.Control | None:
        return self.dialogs.pop() if self.dialogs else None


class DummyAdapter:
    async def obtener_capacidades(self) -> CapacidadesNotificacionSO:
        return CapacidadesNotificacionSO(PlataformaSO.LINUX, False, True)

    async def solicitar_permisos(self) -> bool:
        return True

    async def puede_programar_exacto(self) -> bool:
        return True

    async def programar(self, solicitud: SolicitudNotificacion) -> None:
        pass

    async def cancelar(self, id_notificacion_so: int) -> None:
        pass

    async def mostrar_inmediata(self, solicitud: SolicitudNotificacion) -> None:
        pass

    def registrar_callbacks(
        self,
        on_tap: CallbackInteraccion | None = None,
        on_action: CallbackInteraccion | None = None,
    ) -> None:
        pass


@pytest.mark.asyncio
async def test_ui_navegacion_vistas_dialogos_responsividad_y_tema() -> None:
    page = FakePage(width=1080, platform=ft.PagePlatform.LINUX)
    cont = construir_contenedor_aplicacion(
        page_platform=page.platform,
        db_path=":memory:",
        adaptador_personalizado=DummyAdapter(),
    )
    try:
        # Cargar datos reales previos para ejercitar renderizado de tarjetas en todas las vistas
        cat = cont.servicio_categorias.crear_categoria(nombre="Universidad")
        sub = cont.servicio_categorias.crear_subcategoria(
            categoria_id=cat.id, nombre="Software"
        )
        contacto = cont.servicio_contactos.crear_contacto(
            nombre="Prof. López",
            correo="lopez@uni.edu",
            telefono="+52 55 1111 2222",
            etiqueta="Profesor",
        )
        ahora = cont.reloj.ahora_utc()
        await cont.servicio_eventos.crear_evento(
            titulo="Clase UI",
            fecha_inicio=ahora + timedelta(hours=2),
            fecha_fin=ahora + timedelta(hours=3),
            categoria_id=cat.id,
            subcategoria_id=sub.id,
            contacto_ids=[contacto.id],
            recordatorio_antelacion_min=15,
        )
        await cont.servicio_tareas.crear_tarea(
            titulo="Revisar interfaz",
            fecha_limite=ahora + timedelta(hours=8),
            categoria_id=cat.id,
            subcategoria_id=sub.id,
            contacto_ids=[contacto.id],
            recordatorio_antelacion_min=30,
        )

        app = AgendaApp(page, cont)  # type: ignore[arg-type]
        await app.iniciar()

        assert page.title == "Atempo — Agenda Personal"
        assert page.theme_mode == ft.ThemeMode.LIGHT
        assert page.navigation_bar is None  # Escritorio usa NavigationRail

        # Probar las 4 escalas de calendario (Día, Semana, Mes, Año) + Historial
        for vista in VistaAgenda:
            app._agenda_view._vista_actual = vista
            app._agenda_view.refrescar()
        app._agenda_view._abrir_historial()
        assert len(page.dialogs) == 1
        page.pop_dialog()

        # Navegar por Tareas, Contactos y Ajustes
        for idx in (1, 2, 3):
            await app._cambiar_destino(idx)
        assert page.floating_action_button is not None
        assert page.floating_action_button.visible is False  # Oculto en Ajustes

        # Abrir los 3 formularios de creación sin errores
        for idx in (0, 1, 2):
            await app._accion_fab(idx)
            assert len(page.dialogs) == 1
            page.pop_dialog()

        # Probar responsividad Android -> NavigationBar visible
        page.width = 412
        page.platform = ft.PagePlatform.ANDROID
        app._shell.aplicar_modo_responsivo()
        assert page.navigation_bar is not None

        # Probar cambio de tema oscuro en vivo desde Ajustes (RN-14)
        app._ajustes_view._tema_oscuro_sw.value = True
        app._ajustes_view._guardar_switch_tema(None)  # type: ignore[arg-type]
        assert page.theme_mode == ft.ThemeMode.DARK
        assert cont.servicio_ajustes.obtener().tema_oscuro is True
    finally:
        cont.db.cerrar()

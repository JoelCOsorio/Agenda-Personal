"""Orquestador principal de la interfaz Flet 1.x (AgendaApp)."""

from __future__ import annotations

from pathlib import Path

import flet as ft

from agenda_app.container import ContenedorAplicacion, construir_contenedor_aplicacion
from agenda_app.presentation.components.dialogs.perdidas_dialog import (
    abrir_dialogo_perdidas,
)
from agenda_app.presentation.navigation.shell import ResponsiveShell
from agenda_app.presentation.theme import aplicar_tema
from agenda_app.presentation.views.agenda_view import AgendaView
from agenda_app.presentation.views.ajustes_view import AjustesView
from agenda_app.presentation.views.contactos_view import ContactosView
from agenda_app.presentation.views.tareas_view import TareasView


class AgendaApp:
    """Coordina el ciclo de vida de la UI Flet delegando toda lógica a ContenedorAplicacion."""

    def __init__(self, page: ft.Page, contenedor: ContenedorAplicacion) -> None:
        self._page = page
        self._contenedor = contenedor

        self._agenda_view = AgendaView(page, contenedor)
        self._tareas_view = TareasView(page, contenedor)
        self._contactos_view = ContactosView(page, contenedor)
        self._ajustes_view = AjustesView(
            page,
            contenedor,
            on_ajustes_actualizados=self._on_ajustes_actualizados,
        )

        self._shell = ResponsiveShell(
            page,
            on_cambiar_destino=self._cambiar_destino,
            on_abrir_perdidas=self._abrir_bandeja_perdidas,
            on_accion_principal=self._accion_fab,
        )

    async def iniciar(self) -> None:
        self._page.title = "Agenda Personal"
        aplicar_tema(self._page, self._contenedor.servicio_ajustes.obtener())
        self._page.on_app_lifecycle_state_change = self._on_lifecycle_change

        self._page.add(self._shell.raiz)
        await self._cambiar_destino(0)

        # Ejecutar reconciliación de arranque (detección de alertas perdidas RN-05)
        await self._reconciliar_alertas(abrir_si_corresponde=True)

    async def _cambiar_destino(self, indice: int) -> None:
        if indice == 0:
            self._shell.montar_vista(self._agenda_view.control, 0)
            self._agenda_view.refrescar()
        elif indice == 1:
            self._shell.montar_vista(self._tareas_view.control, 1)
            self._tareas_view.refrescar()
        elif indice == 2:
            self._shell.montar_vista(self._contactos_view.control, 2)
            self._contactos_view.refrescar()
        else:
            self._shell.montar_vista(self._ajustes_view.control, 3)
            await self._ajustes_view.refrescar()

    async def _accion_fab(self, indice: int) -> None:
        if indice == 0:
            self._agenda_view.abrir_creacion()
        elif indice == 1:
            self._tareas_view.abrir_creacion()
        elif indice == 2:
            self._contactos_view.abrir_creacion()

    def _on_ajustes_actualizados(self) -> None:
        aplicar_tema(self._page, self._contenedor.servicio_ajustes.obtener())
        if self._shell.indice_actual == 0:
            self._agenda_view.refrescar()
        elif self._shell.indice_actual == 1:
            self._tareas_view.refrescar()
        elif self._shell.indice_actual == 2:
            self._contactos_view.refrescar()
        self._page.update()

    async def _reconciliar_alertas(self, *, abrir_si_corresponde: bool) -> None:
        try:
            resultado = await self._contenedor.reconciliador.reconciliar()
            self._shell.actualizar_conteo_perdidas(len(resultado.total_perdidos_sin_atender))
            if abrir_si_corresponde and resultado.mostrar_aviso_perdidos:
                await self._abrir_bandeja_perdidas()
        except Exception:
            # En entornos sin puente de notificaciones activo no bloquear la UI
            perdidos = self._contenedor.repo_recordatorios.obtener_perdidos()
            self._shell.actualizar_conteo_perdidas(len(perdidos))

    async def _abrir_bandeja_perdidas(self) -> None:
        async def _actualizar_badge() -> None:
            perdidos = self._contenedor.repo_recordatorios.obtener_perdidos()
            self._shell.actualizar_conteo_perdidas(len(perdidos))

        abrir_dialogo_perdidas(
            self._page,
            self._contenedor,
            on_cambio=_actualizar_badge,
        )

    async def _on_lifecycle_change(self, e: ft.AppLifecycleStateChangeEvent) -> None:
        if e.state == ft.AppLifecycleState.RESUME:
            await self._reconciliar_alertas(abrir_si_corresponde=False)


async def run_app(
    page: ft.Page,
    *,
    db_path: Path | str | None = None,
) -> None:
    """Punto de entrada Flet 1.x desacoplado y testable."""
    contenedor = construir_contenedor_aplicacion(
        page_platform=page.platform,
        db_path=db_path,
        url_launcher=ft.UrlLauncher(),
    )
    app = AgendaApp(page, contenedor)
    await app.iniciar()

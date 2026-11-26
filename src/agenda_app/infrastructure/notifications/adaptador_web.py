"""Adaptador de notificaciones para Web (navegador): planificador asyncio + Web Notification API."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from typing import Any

import flet_notifications as ftn

from agenda_app.application.ports.notificaciones import (
    CapacidadesNotificacionSO,
    SolicitudNotificacion,
)
from agenda_app.application.ports.reloj import IReloj
from agenda_app.domain.entities.base import asegurar_utc
from agenda_app.domain.enums import PlataformaSO
from agenda_app.infrastructure.clock import RelojSistemaUTC
from agenda_app.infrastructure.notifications.base_flet import BaseAdaptadorFlet


class AdaptadorNotificacionesWeb(BaseAdaptadorFlet):
    """Gestiona recordatorios en navegador mediante planificador asyncio + Web Notification API.

    En navegadores, flet-notifications.schedule() no está soportado y las acciones rápidas
    nativas no están disponibles fuera de Service Workers push; por ello este adaptador
    programa alertas en memoria mientras la pestaña está abierta y emite notificaciones
    estándar con degradación controlada.
    """

    def __init__(
        self,
        cliente: Any | None = None,
        reloj: IReloj | None = None,
        on_disparada: Callable[[SolicitudNotificacion], Awaitable[None]] | None = None,
    ) -> None:
        super().__init__(cliente=cliente)
        self._reloj: IReloj = reloj if reloj is not None else RelojSistemaUTC()
        self._on_disparada = on_disparada

        self._pendientes: dict[int, SolicitudNotificacion] = {}
        self._evento_cambio: asyncio.Event | None = None
        self._tarea_planificador: asyncio.Task[None] | None = None

    async def obtener_capacidades(self) -> CapacidadesNotificacionSO:
        return CapacidadesNotificacionSO(
            plataforma=PlataformaSO.WEB,
            soporta_programacion_nativa=False,
            soporta_acciones_rapidas=False,
            soporta_alarmas_exactas=True,
            soporta_cancelacion_masiva=True,
        )

    async def solicitar_permisos(self) -> bool:
        try:
            return await super().solicitar_permisos()
        except Exception:
            return False

    async def puede_programar_exacto(self) -> bool:
        return True

    async def programar(self, solicitud: SolicitudNotificacion) -> None:
        self._pendientes[solicitud.id_notificacion_so] = solicitud
        self._asegurar_planificador()
        if self._evento_cambio is not None:
            self._evento_cambio.set()

    async def cancelar(self, id_notificacion_so: int) -> None:
        eliminado = self._pendientes.pop(id_notificacion_so, None)
        if eliminado is not None and self._evento_cambio is not None:
            self._evento_cambio.set()
        with contextlib.suppress(Exception):
            await self._cliente.cancel(id_notificacion_so)

    async def mostrar_inmediata(self, solicitud: SolicitudNotificacion) -> None:
        with contextlib.suppress(Exception):
            await self._cliente.show(
                solicitud.id_notificacion_so,
                title=solicitud.titulo,
                body=solicitud.cuerpo,
                payload=solicitud.payload,
                actions=None,
                options=ftn.NotificationOptions(
                    web=ftn.WebOptions(
                        lang="es",
                        silent=not solicitud.con_sonido,
                    )
                ),
            )

    @property
    def pendientes_en_memoria(self) -> dict[int, SolicitudNotificacion]:
        return dict(self._pendientes)

    async def detener(self) -> None:
        """Detiene limpiamente la tarea asíncrona del planificador en pestaña."""
        if self._tarea_planificador is not None:
            self._tarea_planificador.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._tarea_planificador
            self._tarea_planificador = None

    def _asegurar_planificador(self) -> None:
        if self._evento_cambio is None:
            self._evento_cambio = asyncio.Event()
        if self._tarea_planificador is None or self._tarea_planificador.done():
            self._tarea_planificador = asyncio.create_task(self._bucle_planificador())

    async def _bucle_planificador(self) -> None:
        assert self._evento_cambio is not None
        while True:
            self._evento_cambio.clear()
            if not self._pendientes:
                await self._evento_cambio.wait()
                continue

            proxima = min(
                self._pendientes.values(),
                key=lambda s: asegurar_utc(s.fecha_disparo),
            )
            ahora = asegurar_utc(self._reloj.ahora_utc())
            espera = (asegurar_utc(proxima.fecha_disparo) - ahora).total_seconds()

            if espera > 0:
                try:
                    await asyncio.wait_for(self._evento_cambio.wait(), timeout=espera)
                    continue
                except TimeoutError:
                    pass

            actual = self._pendientes.pop(proxima.id_notificacion_so, None)
            if actual is None:
                continue

            await self.mostrar_inmediata(actual)
            if self._on_disparada is not None:
                await self._on_disparada(actual)

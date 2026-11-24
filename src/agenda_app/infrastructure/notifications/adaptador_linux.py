"""Adaptador de notificaciones para Linux: planificador asyncio + D-Bus / flet-notifications."""

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
from agenda_app.infrastructure.notifications.base_flet import (
    BaseAdaptadorFlet,
    construir_acciones_flet,
)

DetectorAccionesLinux = Callable[[], Awaitable[bool]]


async def _detectar_acciones_dbus_por_defecto() -> bool:
    """Consulta las capacidades D-Bus reales del entorno de escritorio Linux (RN-06)."""
    try:
        from desktop_notifier import Capability, DesktopNotifier

        notifier = DesktopNotifier(app_name="Atempo")
        caps = await notifier.get_capabilities()
        return Capability.BUTTONS in caps
    except Exception:
        return False


class AdaptadorNotificacionesLinux(BaseAdaptadorFlet):
    """Implementa programación local vía asyncio + entrega nativa D-Bus en Linux.

    flet-notifications.schedule() no existe en Linux (lanza NotificationUnsupportedPlatformException),
    por lo que este adaptador nunca invoca schedule() y gestiona el disparo en memoria mientras la app
    está abierta (complementado por linux_worker.py cuando la app está cerrada).
    """

    def __init__(
        self,
        cliente: Any | None = None,
        reloj: IReloj | None = None,
        detector_acciones: DetectorAccionesLinux | None = None,
        on_disparada: Callable[[SolicitudNotificacion], Awaitable[None]] | None = None,
    ) -> None:
        super().__init__(cliente=cliente)
        self._reloj: IReloj = reloj if reloj is not None else RelojSistemaUTC()
        self._detector_acciones = detector_acciones or _detectar_acciones_dbus_por_defecto
        self._on_disparada = on_disparada
        self._soporta_acciones_cache: bool | None = None

        self._pendientes: dict[int, SolicitudNotificacion] = {}
        self._evento_cambio: asyncio.Event | None = None
        self._tarea_planificador: asyncio.Task[None] | None = None

    async def obtener_capacidades(self) -> CapacidadesNotificacionSO:
        if self._soporta_acciones_cache is None:
            self._soporta_acciones_cache = await self._detector_acciones()
        return CapacidadesNotificacionSO(
            plataforma=PlataformaSO.LINUX,
            soporta_programacion_nativa=False,  # Gestionada por planificador asyncio + worker
            soporta_acciones_rapidas=self._soporta_acciones_cache,
            soporta_alarmas_exactas=True,
            soporta_cancelacion_masiva=True,
        )

    async def solicitar_permisos(self) -> bool:
        # En Linux D-Bus no requiere diálogo de permisos en tiempo de ejecución
        return True

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
        caps = await self.obtener_capacidades()
        acciones = construir_acciones_flet(solicitud.acciones) if caps.soporta_acciones_rapidas else None
        await self._cliente.show(
            solicitud.id_notificacion_so,
            title=solicitud.titulo,
            body=solicitud.cuerpo,
            payload=solicitud.payload,
            actions=acciones,
            options=ftn.NotificationOptions(
                linux=ftn.LinuxOptions(
                    urgency=ftn.LinuxUrgency.NORMAL,
                    silent=not solicitud.con_sonido,
                )
            ),
        )

    @property
    def pendientes_en_memoria(self) -> dict[int, SolicitudNotificacion]:
        return dict(self._pendientes)

    async def detener(self) -> None:
        """Detiene limpiamente la tarea asíncrona del planificador."""
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

            # Re-verificar que no haya sido cancelada durante la espera
            actual = self._pendientes.pop(proxima.id_notificacion_so, None)
            if actual is None:
                continue

            await self.mostrar_inmediata(actual)
            if self._on_disparada is not None:
                await self._on_disparada(actual)

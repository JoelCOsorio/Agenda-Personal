"""Pruebas de contrato de adaptadores Android, Windows y Linux ejecutables desde Linux."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import flet_notifications as ftn
import pytest

from agenda_app.application.ports.notificaciones import (
    ACCION_MARCAR_VISTO,
    ACCION_POSPONER,
    AccionNotificacion,
    SolicitudNotificacion,
)
from agenda_app.infrastructure.notifications.adaptador_android import (
    AdaptadorNotificacionesAndroid,
)
from agenda_app.infrastructure.notifications.adaptador_linux import (
    AdaptadorNotificacionesLinux,
)
from agenda_app.infrastructure.notifications.adaptador_windows import (
    AdaptadorNotificacionesWindows,
)


class FakeFletNotificationsClient:
    """Doble de prueba que replica el contrato real de flet_notifications.Notifications."""

    def __init__(
        self,
        *,
        exact_alarms: bool = True,
        fail_exact_once: bool = False,
        forbid_schedule: bool = False,
    ) -> None:
        self.exact_alarms = exact_alarms
        self.fail_exact_once = fail_exact_once
        self.forbid_schedule = forbid_schedule
        self.on_tap: Any = None
        self.on_action: Any = None
        self.scheduled_calls: list[dict[str, Any]] = []
        self.shown_calls: list[dict[str, Any]] = []
        self.canceled_ids: list[int] = []

    async def request_permissions(self) -> bool:
        return True

    async def can_schedule_exact_alarms(self) -> bool:
        return self.exact_alarms

    async def schedule(self, id: int, **kwargs: Any) -> None:
        if self.forbid_schedule:
            raise ftn.NotificationUnsupportedPlatformException("Linux no soporta schedule()")
        if (
            self.fail_exact_once
            and kwargs.get("schedule_mode") == ftn.AndroidScheduleMode.EXACT_ALLOW_WHILE_IDLE
        ):
            self.fail_exact_once = False
            raise ftn.NotificationPermissionException("Permiso exacto revocado")
        self.scheduled_calls.append({"id": id, **kwargs})

    async def show(self, id: int, **kwargs: Any) -> None:
        self.shown_calls.append({"id": id, **kwargs})

    async def cancel(self, id: int, *, tag: str | None = None) -> None:
        self.canceled_ids.append(id)

    async def cancel_all_pending(self) -> None:
        raise AssertionError("cancel_all_pending() no debe invocarse (incompatible con Windows).")


def _solicitud_ejemplo(id_so: int = 7, segundos: float = 60.0) -> SolicitudNotificacion:
    return SolicitudNotificacion(
        id_notificacion_so=id_so,
        titulo="Parcial de Software",
        cuerpo="Empieza pronto",
        fecha_disparo=datetime.now(timezone.utc) + timedelta(seconds=segundos),
        payload='{"rid":"00000000-0000-4000-8000-000000000009","tipo":"EVENTO","item_id":"00000000-0000-4000-8000-000000000010"}',
        con_sonido=True,
        acciones=(
            AccionNotificacion(id=ACCION_POSPONER, titulo="Posponer", abrir_en_primer_plano=True),
            AccionNotificacion(
                id=ACCION_MARCAR_VISTO, titulo="Marcar como visto", abrir_en_primer_plano=False
            ),
        ),
    )


@pytest.mark.asyncio
async def test_contrato_android_exacto_y_degradacion_inexacta() -> None:
    # Caso 1: permiso exacto concedido, pero revocado al programar -> fallback inexacto
    cliente = FakeFletNotificationsClient(exact_alarms=True, fail_exact_once=True)
    adaptador = AdaptadorNotificacionesAndroid(cliente=cliente)

    await adaptador.programar(_solicitud_ejemplo())
    assert len(cliente.scheduled_calls) == 1
    llamada = cliente.scheduled_calls[0]
    assert llamada["schedule_mode"] == ftn.AndroidScheduleMode.INEXACT_ALLOW_WHILE_IDLE
    assert llamada["match_components"] is None
    # Verifica foreground=True en Posponer (clave para que Python reprograme en Android)
    acciones = llamada["actions"]
    assert acciones[0].id == ACCION_POSPONER and acciones[0].foreground is True
    assert acciones[1].id == ACCION_MARCAR_VISTO and acciones[1].foreground is False


@pytest.mark.asyncio
async def test_contrato_windows_one_off_y_cancelacion_individual() -> None:
    cliente = FakeFletNotificationsClient()
    adaptador = AdaptadorNotificacionesWindows(cliente=cliente)

    caps = await adaptador.obtener_capacidades()
    assert caps.soporta_cancelacion_masiva is False
    assert caps.soporta_programacion_nativa is True

    await adaptador.programar(_solicitud_ejemplo(id_so=55))
    assert cliente.scheduled_calls[0]["id"] == 55
    assert cliente.scheduled_calls[0]["match_components"] is None

    await adaptador.cancelar(55)
    assert cliente.canceled_ids == [55]


@pytest.mark.asyncio
async def test_contrato_linux_planificador_asyncio_sin_schedule_y_degradacion() -> None:
    cliente = FakeFletNotificationsClient(forbid_schedule=True)
    disparadas: list[int] = []

    async def _sin_acciones() -> bool:
        return False

    async def _on_disparada(s: SolicitudNotificacion) -> None:
        disparadas.append(s.id_notificacion_so)

    adaptador = AdaptadorNotificacionesLinux(
        cliente=cliente,
        detector_acciones=_sin_acciones,
        on_disparada=_on_disparada,
    )

    try:
        # Programar dos alertas: una se cancela antes, la otra dispara en ~0.08s
        await adaptador.programar(_solicitud_ejemplo(id_so=90, segundos=0.5))
        await adaptador.cancelar(90)
        await adaptador.programar(_solicitud_ejemplo(id_so=91, segundos=0.08))

        await asyncio.sleep(0.25)

        assert disparadas == [91]
        assert len(cliente.shown_calls) == 1
        assert cliente.shown_calls[0]["id"] == 91
        # Sin soporte D-Bus actions -> degradado a actions=None (RN-06)
        assert cliente.shown_calls[0]["actions"] is None
    finally:
        await adaptador.detener()

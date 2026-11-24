"""Puerto del adaptador multiplataforma de notificaciones (DIP, LSP, RN-06)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from uuid import UUID

from agenda_app.domain.enums import PlataformaSO, TipoOrigenRecordatorio

ACCION_POSPONER = "snooze"
ACCION_MARCAR_VISTO = "mark_seen"
ACCION_COMPLETAR_TAREA = "complete_task"


@dataclass(frozen=True)
class AccionNotificacion:
    """Botón de acción rápida adjunto a una notificación nativa."""

    id: str
    titulo: str
    abrir_en_primer_plano: bool = True
    cancelar_al_pulsar: bool = True


@dataclass(frozen=True)
class SolicitudNotificacion:
    """Mensaje agnóstico del SO listo para programar o mostrar inmediatamente."""

    id_notificacion_so: int
    titulo: str
    cuerpo: str
    fecha_disparo: datetime
    payload: str
    con_sonido: bool = True
    acciones: tuple[AccionNotificacion, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EventoInteraccionNotificacion:
    """Evento normalizado cuando el usuario toca la notificación o un botón de acción."""

    payload: str | None
    action_id: str | None = None
    id_notificacion_so: int | None = None


@dataclass(frozen=True)
class CapacidadesNotificacionSO:
    """Capacidades declaradas por el adaptador de la plataforma actual (RN-06)."""

    plataforma: PlataformaSO
    soporta_programacion_nativa: bool
    soporta_acciones_rapidas: bool
    soporta_alarmas_exactas: bool = False
    soporta_cancelacion_masiva: bool = False


@dataclass(frozen=True)
class ContenidoNotificacion:
    """Título y cuerpo actuales de un Evento o Tarea para reconciliación/snooze."""

    titulo: str
    cuerpo: str


CallbackInteraccion = Callable[[EventoInteraccionNotificacion], Awaitable[None]]


class IProveedorContenidoRecordatorio(Protocol):
    """Permite resolver título y descripción actual del Evento/Tarea sin acoplar repositorios."""

    def obtener_contenido(
        self,
        tipo_origen: TipoOrigenRecordatorio,
        item_id: UUID,
    ) -> ContenidoNotificacion | None: ...


class IAdaptadorNotificaciones(Protocol):
    """Contrato común para los adaptadores de Android, Windows, Linux y Fakes."""

    async def obtener_capacidades(self) -> CapacidadesNotificacionSO: ...

    async def solicitar_permisos(self) -> bool: ...

    async def puede_programar_exacto(self) -> bool: ...

    async def programar(self, solicitud: SolicitudNotificacion) -> None: ...

    async def cancelar(self, id_notificacion_so: int) -> None: ...

    async def mostrar_inmediata(self, solicitud: SolicitudNotificacion) -> None: ...

    def registrar_callbacks(
        self,
        on_tap: CallbackInteraccion | None = None,
        on_action: CallbackInteraccion | None = None,
    ) -> None: ...

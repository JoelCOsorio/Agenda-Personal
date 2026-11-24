"""Entidad Recordatorio del Motor Unificado de Notificaciones."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from agenda_app.domain.entities.base import EntidadBase, asegurar_utc
from agenda_app.domain.enums import EstadoRecordatorio, TipoOrigenRecordatorio
from agenda_app.domain.exceptions import RecordatorioInvalidoError

MAX_ANTELACION_MINUTOS = 7 * 24 * 60  # 10,080 minutos (1 semana — RN-03)
MIN_ID_NOTIFICACION_SO = 1
MAX_ID_NOTIFICACION_SO = 2_147_483_647  # int32 con signo requerido por flet-notifications


@dataclass
class Recordatorio(EntidadBase):
    """Recordatorio único asociado de forma exclusiva (XOR) a un Evento o a una Tarea."""

    id_notificacion_so: int = 0
    tipo_origen: TipoOrigenRecordatorio = TipoOrigenRecordatorio.EVENTO
    evento_id: UUID | None = None
    tarea_id: UUID | None = None
    antelacion_minutos: int = 0
    fecha_disparo: datetime = field(default_factory=lambda: datetime.min)
    estado: EstadoRecordatorio = EstadoRecordatorio.PENDIENTE

    def __post_init__(self) -> None:
        super().__post_init__()

        if not (MIN_ID_NOTIFICACION_SO <= self.id_notificacion_so <= MAX_ID_NOTIFICACION_SO):
            raise RecordatorioInvalidoError(
                f"id_notificacion_so debe estar en [{MIN_ID_NOTIFICACION_SO}, {MAX_ID_NOTIFICACION_SO}]."
            )

        if not (0 <= self.antelacion_minutos <= MAX_ANTELACION_MINUTOS):
            raise RecordatorioInvalidoError(
                f"La antelación debe estar entre 0 y {MAX_ANTELACION_MINUTOS} minutos (7 días)."
            )

        if self.tipo_origen == TipoOrigenRecordatorio.EVENTO:
            if self.evento_id is None or self.tarea_id is not None:
                raise RecordatorioInvalidoError(
                    "Un recordatorio de tipo EVENTO requiere evento_id y tarea_id=None (XOR)."
                )
        elif self.tipo_origen == TipoOrigenRecordatorio.TAREA:
            if self.tarea_id is None or self.evento_id is not None:
                raise RecordatorioInvalidoError(
                    "Un recordatorio de tipo TAREA requiere tarea_id y evento_id=None (XOR)."
                )

        self.fecha_disparo = asegurar_utc(self.fecha_disparo)

    @property
    def item_id(self) -> UUID:
        """Devuelve el UUID del evento o tarea propietario."""
        if self.tipo_origen == TipoOrigenRecordatorio.EVENTO and self.evento_id is not None:
            return self.evento_id
        if self.tipo_origen == TipoOrigenRecordatorio.TAREA and self.tarea_id is not None:
            return self.tarea_id
        raise RecordatorioInvalidoError("Recordatorio sin referencia válida.")

    @property
    def esta_activo(self) -> bool:
        return self.estado in {EstadoRecordatorio.PENDIENTE, EstadoRecordatorio.POSPUESTO}

    def marcar_entregado(self, ahora: datetime) -> None:
        self.estado = EstadoRecordatorio.ENTREGADO
        self.tocar_actualizacion(ahora)

    def marcar_perdido(self, ahora: datetime) -> None:
        """Marca el recordatorio como perdido cuando venció sin entregarse (RN-05)."""
        self.estado = EstadoRecordatorio.PERDIDO
        self.tocar_actualizacion(ahora)

    def marcar_atendido(self, ahora: datetime) -> None:
        self.estado = EstadoRecordatorio.ATENDIDO
        self.tocar_actualizacion(ahora)

    def cancelar(self, ahora: datetime) -> None:
        """Cancela el recordatorio al eliminar ítem o completar tarea (RN-02, RN-12)."""
        self.estado = EstadoRecordatorio.CANCELADO
        self.tocar_actualizacion(ahora)

    def posponer(self, nueva_fecha_disparo: datetime, ahora: datetime) -> None:
        """Reprograma el recordatorio por acción rápida Posponer (RN-14)."""
        self.fecha_disparo = asegurar_utc(nueva_fecha_disparo)
        self.estado = EstadoRecordatorio.POSPUESTO
        self.tocar_actualizacion(ahora)

    def reprogramar(
        self,
        nueva_fecha_disparo: datetime,
        nueva_antelacion_minutos: int,
        ahora: datetime,
    ) -> None:
        """Restablece el recordatorio a PENDIENTE tras cambiar fecha/hora o reactivar (RN-02, RN-12)."""
        if not (0 <= nueva_antelacion_minutos <= MAX_ANTELACION_MINUTOS):
            raise RecordatorioInvalidoError(
                f"La antelación debe estar entre 0 y {MAX_ANTELACION_MINUTOS} minutos (7 días)."
            )
        self.antelacion_minutos = nueva_antelacion_minutos
        self.fecha_disparo = asegurar_utc(nueva_fecha_disparo)
        self.estado = EstadoRecordatorio.PENDIENTE
        self.tocar_actualizacion(ahora)

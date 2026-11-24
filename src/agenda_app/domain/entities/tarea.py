"""Entidad Tarea del Módulo Independiente de Tareas (RN-07, RN-12)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from agenda_app.domain.entities.base import EntidadBase, asegurar_utc
from agenda_app.domain.enums import EstadoTarea, PrioridadTarea
from agenda_app.domain.exceptions import ValidacionEntidadError


@dataclass
class Tarea(EntidadBase):
    """Actividad pendiente gestionada en su módulo propio separado del calendario (RN-07)."""

    titulo: str = ""
    descripcion: str | None = None
    fecha_limite: datetime | None = None
    prioridad: PrioridadTarea = PrioridadTarea.MEDIA
    estado: EstadoTarea = EstadoTarea.PENDIENTE
    categoria_id: UUID | None = None
    subcategoria_id: UUID | None = None
    contacto_ids: tuple[UUID, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.titulo = self.titulo.strip()
        if not self.titulo:
            raise ValidacionEntidadError("El título de la tarea es obligatorio.")
        if self.fecha_limite is not None:
            self.fecha_limite = asegurar_utc(self.fecha_limite)
        self.contacto_ids = tuple(dict.fromkeys(self.contacto_ids))

    @property
    def esta_completada(self) -> bool:
        return self.estado == EstadoTarea.COMPLETADA

    def completar(self, ahora: datetime) -> None:
        """Marca la tarea como completada (su recordatorio se cancela en ServicioTareas, RN-12)."""
        self.estado = EstadoTarea.COMPLETADA
        self.tocar_actualizacion(ahora)

    def reactivar(
        self,
        nuevo_estado: EstadoTarea,
        ahora: datetime,
    ) -> None:
        """Reactiva una tarea completada hacia PENDIENTE o EN_PROGRESO (RN-12)."""
        if nuevo_estado == EstadoTarea.COMPLETADA:
            raise ValidacionEntidadError(
                "Para reactivar una tarea el nuevo estado debe ser PENDIENTE o EN_PROGRESO."
            )
        self.estado = nuevo_estado
        self.tocar_actualizacion(ahora)

    def reprogramar(self, nueva_fecha_limite: datetime | None, ahora: datetime) -> None:
        """Modifica la fecha límite de la tarea (RN-02, RN-12)."""
        self.fecha_limite = (
            asegurar_utc(nueva_fecha_limite) if nueva_fecha_limite is not None else None
        )
        self.tocar_actualizacion(ahora)

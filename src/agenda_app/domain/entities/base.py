"""Entidad base abstracta con UUIDv4 y marcas temporales UTC (RN-10)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


def asegurar_utc(valor: datetime) -> datetime:
    """Normaliza un datetime a UTC con zona horaria explícita."""
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def ahora_utc_por_defecto() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class EntidadBase:
    """Superclase común para todas las entidades persistentes (RN-10)."""

    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=ahora_utc_por_defecto)
    updated_at: datetime = field(default_factory=ahora_utc_por_defecto)

    def __post_init__(self) -> None:
        self.created_at = asegurar_utc(self.created_at)
        self.updated_at = asegurar_utc(self.updated_at)

    def tocar_actualizacion(self, ahora: datetime) -> None:
        """Actualiza la marca temporal `updated_at` en UTC."""
        self.updated_at = asegurar_utc(ahora)

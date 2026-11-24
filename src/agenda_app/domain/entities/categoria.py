"""Entidades Categoria y Subcategoria (jerarquía estricta de 2 niveles — RN-09)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from agenda_app.domain.entities.base import EntidadBase
from agenda_app.domain.exceptions import ValidacionEntidadError

_PATRON_COLOR_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def validar_color_hex(color_hex: str | None) -> str | None:
    if color_hex is None:
        return None
    limpio = color_hex.strip()
    if not _PATRON_COLOR_HEX.match(limpio):
        raise ValidacionEntidadError(
            f"El color '{color_hex}' debe tener formato hexadecimal #RRGGBB."
        )
    return limpio


@dataclass
class Categoria(EntidadBase):
    """Categoría principal (Nivel 1, ej. Universidad, Personal, Trabajo)."""

    nombre: str = ""
    color_hex: str = "#3B82F6"
    icono: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self.nombre = self.nombre.strip()
        if not self.nombre:
            raise ValidacionEntidadError("El nombre de la categoría es obligatorio.")
        color_validado = validar_color_hex(self.color_hex)
        assert color_validado is not None
        self.color_hex = color_validado


@dataclass
class Subcategoria(EntidadBase):
    """Subcategoría (Nivel 2 estricto, ej. Materias/Asignaturas — RN-09)."""

    categoria_id: UUID | None = None
    nombre: str = ""
    color_hex: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.categoria_id is None:
            raise ValidacionEntidadError(
                "Toda subcategoría debe pertenecer a una categoría padre."
            )
        self.nombre = self.nombre.strip()
        if not self.nombre:
            raise ValidacionEntidadError("El nombre de la subcategoría es obligatorio.")
        self.color_hex = validar_color_hex(self.color_hex)

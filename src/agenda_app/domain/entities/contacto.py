"""Entidad Contacto con validación de acciones externas según SO (RN-08, RN-13)."""

from __future__ import annotations

from dataclasses import dataclass

from agenda_app.domain.entities.base import EntidadBase
from agenda_app.domain.enums import PlataformaSO
from agenda_app.domain.exceptions import ValidacionEntidadError


@dataclass
class Contacto(EntidadBase):
    """Ficha de contacto personal o académico vinculable a eventos y tareas."""

    nombre: str = ""
    telefono: str | None = None
    correo: str | None = None
    notas: str | None = None
    etiqueta: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self.nombre = self.nombre.strip()
        if not self.nombre:
            raise ValidacionEntidadError("El nombre del contacto es obligatorio.")
        self.telefono = self.telefono.strip() if self.telefono and self.telefono.strip() else None
        self.correo = self.correo.strip() if self.correo and self.correo.strip() else None
        self.etiqueta = self.etiqueta.strip() if self.etiqueta and self.etiqueta.strip() else None

    def puede_enviar_correo(self) -> bool:
        """El envío de correo (mailto:) está disponible en Android, Windows y Linux (RN-08)."""
        return bool(self.correo and "@" in self.correo)

    def puede_llamar(self, plataforma: PlataformaSO) -> bool:
        """La llamada telefónica (tel:) está habilitada únicamente en Android (RN-08)."""
        return plataforma == PlataformaSO.ANDROID and bool(self.telefono)

    def generar_uri_correo(self) -> str | None:
        if not self.puede_enviar_correo():
            return None
        return f"mailto:{self.correo}"

    def generar_uri_llamada(self, plataforma: PlataformaSO) -> str | None:
        if not self.puede_llamar(plataforma):
            return None
        assert self.telefono is not None
        limpio = "".join(ch for ch in self.telefono if ch.isdigit() or ch == "+")
        return f"tel:{limpio}" if limpio else None

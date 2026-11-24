"""Excepciones específicas de la capa de dominio."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID


class DominioError(Exception):
    """Excepción base para infracciones de reglas de negocio."""


class ValidacionEntidadError(DominioError):
    """Se lanza cuando un atributo obligatorio o formato de entidad es inválido."""


class EntidadNoEncontradaError(DominioError):
    """Se lanza cuando no existe la entidad solicitada por identificador."""


class RangoTemporalInvalidoError(DominioError):
    """Se lanza cuando la fecha/hora de fin es anterior a la de inicio (RN-01)."""


class ChoqueEventosError(DominioError):
    """Se lanza cuando existe solapamiento con otro evento (RN-11)."""

    def __init__(
        self,
        mensaje: str,
        *,
        evento_en_conflicto_id: UUID | None = None,
        titulo_conflicto: str = "",
        inicio_conflicto: datetime | None = None,
        fin_conflicto: datetime | None = None,
    ) -> None:
        super().__init__(mensaje)
        self.evento_en_conflicto_id = evento_en_conflicto_id
        self.titulo_conflicto = titulo_conflicto
        self.inicio_conflicto = inicio_conflicto
        self.fin_conflicto = fin_conflicto


class RecordatorioInvalidoError(DominioError):
    """Se lanza cuando un recordatorio infringe RN-03 o sus invariantes de dominio."""


class ConfiguracionInvalidaError(DominioError):
    """Se lanza cuando un parámetro de ConfiguracionSistema está fuera de rango."""


class JerarquiaCategoriaInvalidaError(DominioError):
    """Se lanza cuando una subcategoría no pertenece a la categoría padre indicada (RN-09)."""


class AccionPlataformaNoSoportadaError(DominioError):
    """Se lanza cuando se invoca una acción externa no disponible en el SO actual (RN-08)."""


class PermisoNotificacionError(DominioError):
    """Se lanza cuando el SO no concede permisos necesarios para programar alertas."""

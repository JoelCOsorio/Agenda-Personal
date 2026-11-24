"""Reglas de negocio puras del dominio."""

from agenda_app.domain.rules.recordatorio_rules import (
    MARGEN_SEGURIDAD_SEGUNDOS,
    PayloadRecordatorio,
    ValidadorRecordatorio,
)
from agenda_app.domain.rules.recurrencia import ExpansorRecurrencia, OcurrenciaEvento
from agenda_app.domain.rules.solapamiento import (
    ConflictoEvento,
    DetectorSolapamiento,
    intervalos_se_solapan,
)

__all__ = [
    "ConflictoEvento",
    "DetectorSolapamiento",
    "ExpansorRecurrencia",
    "MARGEN_SEGURIDAD_SEGUNDOS",
    "OcurrenciaEvento",
    "PayloadRecordatorio",
    "ValidadorRecordatorio",
    "intervalos_se_solapan",
]

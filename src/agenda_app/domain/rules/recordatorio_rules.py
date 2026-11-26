"""Reglas puras de validación y serialización de recordatorios (RN-03)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from agenda_app.domain.entities.base import asegurar_utc
from agenda_app.domain.entities.recordatorio import MAX_ANTELACION_MINUTOS, Recordatorio
from agenda_app.domain.enums import TipoOrigenRecordatorio
from agenda_app.domain.exceptions import RecordatorioInvalidoError

MARGEN_SEGURIDAD_SEGUNDOS = 1


@dataclass(frozen=True)
class PayloadRecordatorio:
    """Datos mínimos serializados en el payload nativo de la notificación."""

    recordatorio_id: UUID
    tipo_origen: TipoOrigenRecordatorio
    item_id: UUID


class ValidadorRecordatorio:
    """Aplica validaciones puras de tiempo y disponibilidad de recordatorios (RN-03)."""

    @staticmethod
    def validar_antelacion(antelacion_minutos: int) -> None:
        if antelacion_minutos < 0 or antelacion_minutos > MAX_ANTELACION_MINUTOS:
            raise RecordatorioInvalidoError(
                f"La antelación debe estar entre 0 y {MAX_ANTELACION_MINUTOS} minutos (7 días)."
            )

    @classmethod
    def calcular_y_validar_disparo(
        cls,
        fecha_objetivo: datetime,
        antelacion_minutos: int,
        ahora: datetime,
        margen_segundos: int = MARGEN_SEGURIDAD_SEGUNDOS,
    ) -> datetime:
        """Calcula fecha_disparo en UTC y verifica que sea válida y futura (RN-03)."""
        cls.validar_antelacion(antelacion_minutos)
        objetivo_utc = asegurar_utc(fecha_objetivo)
        ahora_utc = asegurar_utc(ahora)

        fecha_disparo = objetivo_utc - timedelta(minutes=antelacion_minutos)
        umbral_minimo = ahora_utc + timedelta(seconds=margen_segundos)

        if fecha_disparo < umbral_minimo:
            raise RecordatorioInvalidoError(
                "La hora calculada para el recordatorio ya transcurrió. "
                "Reduce la antelación (por ejemplo, 'Al momento de iniciar') o ajusta la fecha y hora."
            )
        return fecha_disparo

    @staticmethod
    def construir_payload(recordatorio: Recordatorio) -> str:
        """Serializa un payload JSON compacto para on_tap y on_action."""
        return json.dumps(
            {
                "rid": str(recordatorio.id),
                "tipo": recordatorio.tipo_origen.value,
                "item_id": str(recordatorio.item_id),
            },
            separators=(",", ":"),
        )

    @staticmethod
    def parsear_payload(payload: str | None) -> PayloadRecordatorio | None:
        """Deserializa el payload devuelto por la API nativa del SO."""
        if not payload:
            return None
        try:
            data = json.loads(payload)
            return PayloadRecordatorio(
                recordatorio_id=UUID(data["rid"]),
                tipo_origen=TipoOrigenRecordatorio(data["tipo"]),
                item_id=UUID(data["item_id"]),
            )
        except (ValueError, KeyError, TypeError):
            return None

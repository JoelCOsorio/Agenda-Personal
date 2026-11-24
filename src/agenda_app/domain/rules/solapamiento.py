"""Validación estricta anti-solapamiento de eventos (RN-11)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from agenda_app.domain.entities.evento import Evento
from agenda_app.domain.rules.recurrencia import ExpansorRecurrencia, OcurrenciaEvento


@dataclass(frozen=True)
class ConflictoEvento:
    """Describe el evento existente y el rango horario que genera el choque (RN-11)."""

    evento_existente: Evento
    inicio_conflicto: datetime
    fin_conflicto: datetime | None


def intervalos_se_solapan(
    inicio_a: datetime,
    fin_a: datetime | None,
    inicio_b: datetime,
    fin_b: datetime | None,
) -> bool:
    """Evalúa solapamiento entre dos eventos con horario definido (incluye puntuales fin=None).

    - Dos rangos [sA, eA) y [sB, eB) chocan si sA < eB y sB < eA (contiguos NO chocan).
    - Dos eventos puntuales (fin=None) chocan si inician exactamente en el mismo instante.
    - Un evento puntual sA choca con un rango [sB, eB) si sB <= sA < eB.
    """
    a_es_puntual = fin_a is None or fin_a == inicio_a
    b_es_puntual = fin_b is None or fin_b == inicio_b

    if a_es_puntual and b_es_puntual:
        return inicio_a == inicio_b
    if a_es_puntual and fin_b is not None:
        return inicio_b <= inicio_a < fin_b
    if b_es_puntual and fin_a is not None:
        return inicio_a <= inicio_b < fin_a
    assert fin_a is not None and fin_b is not None
    return inicio_a < fin_b and inicio_b < fin_a


class DetectorSolapamiento:
    """Detecta colisiones de horario entre un evento candidato y eventos existentes (RN-11).

    Políticas acordadas:
    - Los eventos de 'todo el día' NO bloquean eventos con franja horaria específica.
    - Los eventos sin hora de fin explícita (fecha_fin=None) se evalúan como puntuales.
    - Incluye instancias expandidas de eventos recurrentes.
    """

    @classmethod
    def buscar_conflicto(
        cls,
        candidato: Evento,
        existentes: Sequence[Evento],
        *,
        ventana_recurrencia_dias: int = 365,
    ) -> ConflictoEvento | None:
        if candidato.todo_el_dia:
            return None

        desde, hasta = cls._calcular_ventana(candidato, ventana_recurrencia_dias)
        ocurrencias_candidato = ExpansorRecurrencia.expandir_en_rango(candidato, desde, hasta)
        if not ocurrencias_candidato:
            return None

        for existente in existentes:
            if existente.id == candidato.id or existente.todo_el_dia:
                continue

            ocurrencias_exist = ExpansorRecurrencia.expandir_en_rango(existente, desde, hasta)
            conflicto = cls._buscar_par_en_conflicto(ocurrencias_candidato, ocurrencias_exist)
            if conflicto is not None:
                return conflicto
        return None

    @staticmethod
    def _calcular_ventana(candidato: Evento, ventana_dias: int) -> tuple[datetime, datetime]:
        desde = candidato.fecha_inicio - timedelta(days=1)
        if candidato.recurrencia is None:
            fin_base = candidato.fecha_fin if candidato.fecha_fin is not None else candidato.fecha_inicio
            hasta = fin_base + timedelta(days=1)
        else:
            hasta = candidato.fecha_inicio + timedelta(days=ventana_dias)
        return desde, hasta

    @staticmethod
    def _buscar_par_en_conflicto(
        ocurrencias_a: list[OcurrenciaEvento],
        ocurrencias_b: list[OcurrenciaEvento],
    ) -> ConflictoEvento | None:
        for oc_a in ocurrencias_a:
            for oc_b in ocurrencias_b:
                if intervalos_se_solapan(oc_a.inicio, oc_a.fin, oc_b.inicio, oc_b.fin):
                    return ConflictoEvento(
                        evento_existente=oc_b.evento,
                        inicio_conflicto=oc_b.inicio,
                        fin_conflicto=oc_b.fin,
                    )
        return None

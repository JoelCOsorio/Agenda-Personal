"""Expansión pura de eventos recurrentes (RF-06) sin dependencias externas."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from agenda_app.domain.entities.base import asegurar_utc
from agenda_app.domain.entities.evento import DIAS_SEMANA_VALIDOS, Evento
from agenda_app.domain.enums import TipoFrecuencia

_INDICE_DIA = {codigo: idx for idx, codigo in enumerate(DIAS_SEMANA_VALIDOS)}


@dataclass(frozen=True)
class OcurrenciaEvento:
    """Instancia concreta (puntual o expandida) de un Evento dentro de una vista."""

    evento: Evento
    inicio: datetime
    fin: datetime | None


def _sumar_meses(dt: datetime, meses: int, dia_original: int) -> datetime:
    """Suma meses manteniendo el día original o ajustando al último día válido del mes."""
    total_meses = (dt.year * 12 + (dt.month - 1)) + meses
    nuevo_anio, mes_zero = divmod(total_meses, 12)
    nuevo_mes = mes_zero + 1
    ultimo_dia = calendar.monthrange(nuevo_anio, nuevo_mes)[1]
    return dt.replace(year=nuevo_anio, month=nuevo_mes, day=min(dia_original, ultimo_dia))


class ExpansorRecurrencia:
    """Genera las ocurrencias de un evento dentro de un rango temporal [desde, hasta]."""

    @classmethod
    def expandir_en_rango(
        cls,
        evento: Evento,
        desde: datetime,
        hasta: datetime,
    ) -> list[OcurrenciaEvento]:
        desde_utc = asegurar_utc(desde)
        hasta_utc = asegurar_utc(hasta)
        duracion = (
            (evento.fecha_fin - evento.fecha_inicio)
            if evento.fecha_fin is not None
            else None
        )

        if evento.recurrencia is None:
            fin_ev = evento.fecha_fin if evento.fecha_fin is not None else evento.fecha_inicio
            if evento.fecha_inicio <= hasta_utc and fin_ev >= desde_utc:
                return [OcurrenciaEvento(evento=evento, inicio=evento.fecha_inicio, fin=evento.fecha_fin)]
            return []

        regla = evento.recurrencia
        resultados: list[OcurrenciaEvento] = []
        generadas = 0
        limite_fecha: date | None = regla.fecha_fin_recurrencia
        max_oc = regla.max_ocurrencias

        for inicio_oc in cls._iterar_inicios(evento, hasta_utc):
            if limite_fecha is not None and inicio_oc.date() > limite_fecha:
                break
            generadas += 1
            if max_oc is not None and generadas > max_oc:
                break

            fin_oc = (inicio_oc + duracion) if duracion is not None else None
            corte_fin = fin_oc if fin_oc is not None else inicio_oc

            if inicio_oc > hasta_utc:
                break
            if corte_fin >= desde_utc:
                resultados.append(OcurrenciaEvento(evento=evento, inicio=inicio_oc, fin=fin_oc))

        return resultados

    @classmethod
    def siguiente_ocurrencia(
        cls,
        evento: Evento,
        desde: datetime,
        horizonte_dias: int = 366,
    ) -> OcurrenciaEvento | None:
        """Devuelve la próxima ocurrencia cuyo inicio sea >= desde (para alertas one-off)."""
        desde_utc = asegurar_utc(desde)
        hasta_utc = desde_utc + timedelta(days=horizonte_dias)
        ocurrencias = cls.expandir_en_rango(evento, desde_utc, hasta_utc)
        for oc in ocurrencias:
            if oc.inicio >= desde_utc:
                return oc
        return None

    @staticmethod
    def _iterar_inicios(evento: Evento, hasta_utc: datetime):
        regla = evento.recurrencia
        assert regla is not None
        base = evento.fecha_inicio

        if regla.frecuencia == TipoFrecuencia.DIARIA:
            actual = base
            paso = timedelta(days=regla.intervalo)
            while actual <= hasta_utc:
                yield actual
                actual += paso
            return

        if regla.frecuencia == TipoFrecuencia.SEMANAL:
            dias_objetivo = (
                sorted({_INDICE_DIA[d] for d in regla.dias_semana})
                if regla.dias_semana
                else [base.weekday()]
            )
            lunes_base = base - timedelta(days=base.weekday())
            semana = 0
            while True:
                inicio_semana = lunes_base + timedelta(weeks=semana * regla.intervalo)
                if inicio_semana > hasta_utc + timedelta(days=7):
                    break
                for dia_idx in dias_objetivo:
                    candidato = inicio_semana + timedelta(days=dia_idx)
                    if candidato < base:
                        continue
                    if candidato > hasta_utc:
                        return
                    yield candidato
                semana += 1
            return

        if regla.frecuencia == TipoFrecuencia.MENSUAL:
            paso_n = 0
            dia_orig = base.day
            while True:
                candidato = _sumar_meses(base, paso_n * regla.intervalo, dia_orig)
                if candidato > hasta_utc:
                    break
                yield candidato
                paso_n += 1
            return

        if regla.frecuencia == TipoFrecuencia.ANUAL:
            paso_n = 0
            dia_orig = base.day
            while True:
                candidato = _sumar_meses(base, paso_n * 12 * regla.intervalo, dia_orig)
                if candidato > hasta_utc:
                    break
                yield candidato
                paso_n += 1

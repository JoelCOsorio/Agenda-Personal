"""Pruebas unitarias de expansión de recurrencias (RF-06) y anti-solapamiento (RN-11)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from agenda_app.domain.entities.evento import Evento, ReglaRecurrencia
from agenda_app.domain.enums import TipoFrecuencia
from agenda_app.domain.exceptions import RangoTemporalInvalidoError
from agenda_app.domain.rules.recurrencia import ExpansorRecurrencia
from agenda_app.domain.rules.solapamiento import DetectorSolapamiento


def _dt(anio: int, mes: int, dia: int, hora: int, minuto: int = 0) -> datetime:
    return datetime(anio, mes, dia, hora, minuto, tzinfo=timezone.utc)


def test_evento_rechaza_fecha_fin_anterior_a_inicio_rn01() -> None:
    with pytest.raises(RangoTemporalInvalidoError, match="RN-01"):
        Evento(
            titulo="Inconsistente",
            fecha_inicio=_dt(2026, 11, 24, 12, 0),
            fecha_fin=_dt(2026, 11, 24, 10, 0),
        )


def test_recurrencia_semanal_lu_mi_vi_y_mensual_fin_de_mes() -> None:
    # 2026-11-23 es Lunes
    ev_clases = Evento(
        titulo="Ingeniería de Software",
        fecha_inicio=_dt(2026, 11, 23, 8, 0),
        fecha_fin=_dt(2026, 11, 23, 10, 0),
        recurrencia=ReglaRecurrencia(
            frecuencia=TipoFrecuencia.SEMANAL,
            intervalo=1,
            dias_semana=("LU", "MI", "VI"),
            max_ocurrencias=4,
        ),
    )
    oc = ExpansorRecurrencia.expandir_en_rango(
        ev_clases, _dt(2026, 11, 23, 0, 0), _dt(2026, 12, 10, 0, 0)
    )
    assert [o.inicio.date() for o in oc] == [
        date(2026, 11, 23),  # Lunes
        date(2026, 11, 25),  # Miércoles
        date(2026, 11, 27),  # Viernes
        date(2026, 11, 30),  # Lunes siguiente (tope 4 ocurrencias)
    ]

    # Recurrencia mensual el día 31 -> ajusta a 28 de febrero y regresa a 31 de marzo
    ev_mensual = Evento(
        titulo="Pago mensual",
        fecha_inicio=_dt(2026, 1, 31, 9, 0),
        fecha_fin=_dt(2026, 1, 31, 9, 30),
        recurrencia=ReglaRecurrencia(
            frecuencia=TipoFrecuencia.MENSUAL,
            intervalo=1,
            max_ocurrencias=3,
        ),
    )
    oc_m = ExpansorRecurrencia.expandir_en_rango(
        ev_mensual, _dt(2026, 1, 1, 0, 0), _dt(2026, 5, 1, 0, 0)
    )
    assert [o.inicio.date() for o in oc_m] == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
    ]


def test_solapamiento_estricto_contiguos_puntuales_y_todo_el_dia_rn11() -> None:
    existente = Evento(
        titulo="Clase Cálculo",
        fecha_inicio=_dt(2026, 11, 24, 10, 0),
        fecha_fin=_dt(2026, 11, 24, 12, 0),
    )

    # 1. Contiguo (12:00-13:00) NO choca
    contiguo = Evento(
        titulo="Almuerzo",
        fecha_inicio=_dt(2026, 11, 24, 12, 0),
        fecha_fin=_dt(2026, 11, 24, 13, 0),
    )
    assert DetectorSolapamiento.buscar_conflicto(contiguo, [existente]) is None

    # 2. Solapado parcial (11:30-12:30) SÍ choca
    solapado = Evento(
        titulo="Tutoría",
        fecha_inicio=_dt(2026, 11, 24, 11, 30),
        fecha_fin=_dt(2026, 11, 24, 12, 30),
    )
    conflicto = DetectorSolapamiento.buscar_conflicto(solapado, [existente])
    assert conflicto is not None
    assert conflicto.evento_existente.id == existente.id

    # 3. Evento puntual (fecha_fin=None) dentro del rango [10:00, 12:00) SÍ choca
    puntual_dentro = Evento(
        titulo="Llamada rápida",
        fecha_inicio=_dt(2026, 11, 24, 10, 30),
        fecha_fin=None,
    )
    assert DetectorSolapamiento.buscar_conflicto(puntual_dentro, [existente]) is not None

    # 4. Evento puntual exactamente al término (12:00) NO choca
    puntual_borde = Evento(
        titulo="Check-in",
        fecha_inicio=_dt(2026, 11, 24, 12, 0),
        fecha_fin=None,
    )
    assert DetectorSolapamiento.buscar_conflicto(puntual_borde, [existente]) is None

    # 5. Evento de "Todo el día" NO bloquea ni choca con eventos con horario
    feriado = Evento(
        titulo="Cumpleaños",
        fecha_inicio=_dt(2026, 11, 24, 0, 0),
        todo_el_dia=True,
    )
    assert DetectorSolapamiento.buscar_conflicto(feriado, [existente]) is None
    assert DetectorSolapamiento.buscar_conflicto(existente, [feriado]) is None

    # 6. Editar el mismo evento (mismo UUID) NO choca consigo mismo
    mismo = Evento(
        id=existente.id,
        titulo="Clase Cálculo editada",
        fecha_inicio=_dt(2026, 11, 24, 10, 30),
        fecha_fin=_dt(2026, 11, 24, 11, 30),
    )
    assert DetectorSolapamiento.buscar_conflicto(mismo, [existente]) is None


def test_solapamiento_detecta_choque_con_instancia_futura_de_evento_recurrente() -> None:
    # Clase todos los martes de 10:00 a 12:00 empezando el 2026-11-24
    clase_semanal = Evento(
        titulo="Bases de Datos",
        fecha_inicio=_dt(2026, 11, 24, 10, 0),
        fecha_fin=_dt(2026, 11, 24, 12, 0),
        recurrencia=ReglaRecurrencia(
            frecuencia=TipoFrecuencia.SEMANAL,
            intervalo=1,
            dias_semana=("MA",),
            fecha_fin_recurrencia=date(2026, 12, 31),
        ),
    )

    # Cita puntual dos martes después (2026-12-08 11:00-11:30) debe chocar
    cita = Evento(
        titulo="Dentista",
        fecha_inicio=_dt(2026, 12, 8, 11, 0),
        fecha_fin=_dt(2026, 12, 8, 11, 30),
    )
    conflicto = DetectorSolapamiento.buscar_conflicto(cita, [clase_semanal])
    assert conflicto is not None
    assert conflicto.evento_existente.titulo == "Bases de Datos"
    assert conflicto.inicio_conflicto == _dt(2026, 12, 8, 10, 0)

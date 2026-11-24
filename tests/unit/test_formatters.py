"""Pruebas unitarias de formateadores y utilidades puras de calendario en presentación."""

from __future__ import annotations

from datetime import date, datetime, timezone

from agenda_app.presentation.formatters import (
    encabezados_dias_semana,
    formatear_antelacion,
    formatear_rango_evento,
    generar_cuadricula_mes,
    rango_semana,
)


def test_cuadricula_mensual_y_encabezados_respetan_primer_dia_semana() -> None:
    # Lunes primero (1)
    assert encabezados_dias_semana(1) == ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    semanas_lun = generar_cuadricula_mes(2026, 11, primer_dia_semana=1)
    assert all(len(sem) == 7 for sem in semanas_lun)
    assert semanas_lun[0][0].weekday() == 0  # Lunes

    # Domingo primero (7)
    assert encabezados_dias_semana(7) == ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]
    semanas_dom = generar_cuadricula_mes(2026, 11, primer_dia_semana=7)
    assert semanas_dom[0][0].weekday() == 6  # Domingo


def test_rango_semana_contiene_fecha_referencia() -> None:
    miercoles = date(2026, 11, 25)
    sem_lun = rango_semana(miercoles, primer_dia_semana=1)
    assert len(sem_lun) == 7
    assert sem_lun[0] == date(2026, 11, 23)  # Lunes
    assert sem_lun[-1] == date(2026, 11, 29)  # Domingo

    sem_dom = rango_semana(miercoles, primer_dia_semana=7)
    assert sem_dom[0] == date(2026, 11, 22)  # Domingo
    assert sem_dom[-1] == date(2026, 11, 28)  # Sábado


def test_formatear_antelacion_y_rango_todo_el_dia() -> None:
    assert formatear_antelacion(None) == "Sin recordatorio"
    assert formatear_antelacion(0) == "Al iniciar"
    assert formatear_antelacion(15) == "15 min antes"
    assert formatear_antelacion(60) == "1 hora antes"
    assert formatear_antelacion(1440) == "1 día antes"
    assert formatear_antelacion(10080) == "1 semana antes"

    dt = datetime(2026, 11, 23, 18, 0, tzinfo=timezone.utc)
    assert formatear_rango_evento(dt, None, todo_el_dia=True) == "Todo el día"

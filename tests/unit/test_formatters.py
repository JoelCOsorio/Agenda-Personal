"""Pruebas unitarias de formateadores y utilidades puras de calendario en presentación."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from agenda_app.presentation.formatters import (
    calcular_inicio_por_defecto,
    encabezados_dias_semana,
    evaluar_preview_recordatorio,
    fecha_desde_datepicker,
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


def test_calcular_inicio_por_defecto_respeta_cruce_de_medianoche() -> None:
    tz_mx = timezone(timedelta(hours=-6))
    ahora_noche = datetime(2026, 11, 25, 23, 57, tzinfo=tz_mx)

    # A las 23:57 de hoy, debe saltar al día siguiente 00:00-01:00 (no a hoy 00:00)
    ini, fin = calcular_inicio_por_defecto(date(2026, 11, 25), ahora_noche)
    assert ini == datetime(2026, 11, 26, 0, 0, tzinfo=tz_mx)
    assert fin == datetime(2026, 11, 26, 1, 0, tzinfo=tz_mx)

    # Sin fecha inicial explícita también conserva el salto de medianoche
    ini_none, fin_none = calcular_inicio_por_defecto(None, ahora_noche)
    assert ini_none == datetime(2026, 11, 26, 0, 0, tzinfo=tz_mx)
    assert fin_none == datetime(2026, 11, 26, 1, 0, tzinfo=tz_mx)

    # Para otro día distinto a hoy, sugiere 09:00-10:00 de ese día
    ini_otro, fin_otro = calcular_inicio_por_defecto(date(2026, 11, 28), ahora_noche)
    assert ini_otro == datetime(2026, 11, 28, 9, 0, tzinfo=tz_mx)
    assert fin_otro == datetime(2026, 11, 28, 10, 0, tzinfo=tz_mx)


def test_fecha_desde_datepicker_evita_desfase_utc() -> None:
    # Un DatePicker que devuelve medianoche UTC no debe retroceder al día anterior en UTC-6
    valor_utc = datetime(2026, 11, 26, 0, 0, 0, tzinfo=timezone.utc)
    assert fecha_desde_datepicker(valor_utc) == date(2026, 11, 26)

    valor_naive = datetime(2026, 11, 26, 12, 0, 0)
    assert fecha_desde_datepicker(valor_naive) == date(2026, 11, 26)


def test_evaluar_preview_recordatorio() -> None:
    ahora = datetime(2026, 11, 26, 15, 0, 0, tzinfo=timezone.utc)

    ok_none, msg_none = evaluar_preview_recordatorio(
        objetivo_utc=ahora + timedelta(hours=1),
        antelacion_minutos=None,
        ahora_utc=ahora,
    )
    assert ok_none is True
    assert "No se enviará" in msg_none

    ok_fut, msg_fut = evaluar_preview_recordatorio(
        objetivo_utc=ahora + timedelta(minutes=2),
        antelacion_minutos=0,
        ahora_utc=ahora,
    )
    assert ok_fut is True
    assert msg_fut.startswith("Sonará el:")

    ok_pasado, msg_pasado = evaluar_preview_recordatorio(
        objetivo_utc=ahora + timedelta(minutes=5),
        antelacion_minutos=15,
        ahora_utc=ahora,
    )
    assert ok_pasado is False
    assert "ya transcurrió" in msg_pasado

    ok_max, msg_max = evaluar_preview_recordatorio(
        objetivo_utc=ahora + timedelta(days=10),
        antelacion_minutos=10081,
        ahora_utc=ahora,
    )
    assert ok_max is False
    assert "10,080" in msg_max

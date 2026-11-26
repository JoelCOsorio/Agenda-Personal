"""Pruebas unitarias de reglas puras del dominio de Recordatorio (RN-03, RN-10)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from agenda_app.domain.entities.recordatorio import MAX_ANTELACION_MINUTOS, Recordatorio
from agenda_app.domain.enums import EstadoRecordatorio, TipoOrigenRecordatorio
from agenda_app.domain.exceptions import RecordatorioInvalidoError
from agenda_app.domain.rules.recordatorio_rules import ValidadorRecordatorio

BASE_AHORA = datetime(2026, 11, 23, 18, 0, 0, tzinfo=timezone.utc)


def test_validar_disparo_permite_hasta_7_dias_exactos() -> None:
    objetivo = BASE_AHORA + timedelta(days=8)
    disparo = ValidadorRecordatorio.calcular_y_validar_disparo(
        fecha_objetivo=objetivo,
        antelacion_minutos=MAX_ANTELACION_MINUTOS,  # 10,080 min = 7 días
        ahora=BASE_AHORA,
    )
    assert disparo == BASE_AHORA + timedelta(days=1)


def test_validar_disparo_rechaza_mas_de_7_dias() -> None:
    objetivo = BASE_AHORA + timedelta(days=10)
    with pytest.raises(RecordatorioInvalidoError, match="7 días"):
        ValidadorRecordatorio.calcular_y_validar_disparo(
            fecha_objetivo=objetivo,
            antelacion_minutos=MAX_ANTELACION_MINUTOS + 1,
            ahora=BASE_AHORA,
        )


def test_validar_disparo_rechaza_antelacion_negativa_y_pasado() -> None:
    with pytest.raises(RecordatorioInvalidoError):
        ValidadorRecordatorio.calcular_y_validar_disparo(
            fecha_objetivo=BASE_AHORA + timedelta(hours=1),
            antelacion_minutos=-1,
            ahora=BASE_AHORA,
        )

    # Objetivo en 10 min con antelación de 30 min cae en el pasado
    with pytest.raises(RecordatorioInvalidoError, match="ya transcurrió"):
        ValidadorRecordatorio.calcular_y_validar_disparo(
            fecha_objetivo=BASE_AHORA + timedelta(minutes=10),
            antelacion_minutos=30,
            ahora=BASE_AHORA,
        )


def test_validar_disparo_permite_eventos_cercanos_al_iniciar() -> None:
    # Con margen de 1 segundo, un evento en +2s o +1min con antelación 0 debe aceptarse
    disparo_2s = ValidadorRecordatorio.calcular_y_validar_disparo(
        fecha_objetivo=BASE_AHORA + timedelta(seconds=2),
        antelacion_minutos=0,
        ahora=BASE_AHORA,
    )
    assert disparo_2s == BASE_AHORA + timedelta(seconds=2)

    disparo_1m = ValidadorRecordatorio.calcular_y_validar_disparo(
        fecha_objetivo=BASE_AHORA + timedelta(minutes=1),
        antelacion_minutos=0,
        ahora=BASE_AHORA,
    )
    assert disparo_1m == BASE_AHORA + timedelta(minutes=1)

    # En el mismo instante exacto o en el pasado debe rechazarse
    with pytest.raises(RecordatorioInvalidoError, match="ya transcurrió"):
        ValidadorRecordatorio.calcular_y_validar_disparo(
            fecha_objetivo=BASE_AHORA,
            antelacion_minutos=0,
            ahora=BASE_AHORA,
        )

    with pytest.raises(RecordatorioInvalidoError, match="ya transcurrió"):
        ValidadorRecordatorio.calcular_y_validar_disparo(
            fecha_objetivo=BASE_AHORA - timedelta(seconds=1),
            antelacion_minutos=0,
            ahora=BASE_AHORA,
        )


def test_recordatorio_exige_arco_xor_e_id_so_int32() -> None:
    ev_id = uuid4()
    tar_id = uuid4()

    # Ambos presentes viola XOR
    with pytest.raises(RecordatorioInvalidoError, match="XOR"):
        Recordatorio(
            id_notificacion_so=1,
            tipo_origen=TipoOrigenRecordatorio.EVENTO,
            evento_id=ev_id,
            tarea_id=tar_id,
            antelacion_minutos=15,
            fecha_disparo=BASE_AHORA + timedelta(hours=1),
        )

    # id_notificacion_so fuera de int32
    with pytest.raises(RecordatorioInvalidoError):
        Recordatorio(
            id_notificacion_so=0,
            tipo_origen=TipoOrigenRecordatorio.EVENTO,
            evento_id=ev_id,
            antelacion_minutos=15,
            fecha_disparo=BASE_AHORA + timedelta(hours=1),
        )

    with pytest.raises(RecordatorioInvalidoError):
        Recordatorio(
            id_notificacion_so=2_147_483_648,
            tipo_origen=TipoOrigenRecordatorio.TAREA,
            tarea_id=tar_id,
            antelacion_minutos=15,
            fecha_disparo=BASE_AHORA + timedelta(hours=1),
        )


def test_serializacion_y_deserializacion_payload() -> None:
    tar_id = uuid4()
    rec = Recordatorio(
        id_notificacion_so=42,
        tipo_origen=TipoOrigenRecordatorio.TAREA,
        tarea_id=tar_id,
        antelacion_minutos=30,
        fecha_disparo=BASE_AHORA + timedelta(hours=2),
        estado=EstadoRecordatorio.PENDIENTE,
    )
    raw = ValidadorRecordatorio.construir_payload(rec)
    parsed = ValidadorRecordatorio.parsear_payload(raw)

    assert parsed is not None
    assert parsed.recordatorio_id == rec.id
    assert parsed.tipo_origen == TipoOrigenRecordatorio.TAREA
    assert parsed.item_id == tar_id
    assert ValidadorRecordatorio.parsear_payload("no-es-json") is None

"""Helpers puros de presentación: conversión UTC<->Local, formato 12h/24h y calendarios."""

from __future__ import annotations

import calendar
from datetime import date, datetime, time, timedelta, timezone

from agenda_app.domain.entities.base import asegurar_utc
from agenda_app.domain.enums import EstadoTarea, TipoFrecuencia, VistaAgenda

MESES_ES: tuple[str, ...] = (
    "",
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
)

DIAS_CORTOS_ES: tuple[str, ...] = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")
DIAS_LARGOS_ES: tuple[str, ...] = (
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
)

OPCIONES_ANTELACION_MIN: tuple[tuple[int | None, str], ...] = (
    (None, "Sin recordatorio"),
    (0, "Al momento de iniciar"),
    (10, "10 minutos antes"),
    (15, "15 minutos antes"),
    (30, "30 minutos antes"),
    (60, "1 hora antes"),
    (180, "3 horas antes"),
    (1440, "1 día antes"),
    (2880, "2 días antes"),
    (10080, "1 semana antes (máximo)"),
)


def zona_local():
    return datetime.now().astimezone().tzinfo or timezone.utc


def utc_a_local(dt: datetime) -> datetime:
    """Convierte un datetime UTC del dominio a la hora local del dispositivo."""
    return asegurar_utc(dt).astimezone(zona_local())


def local_a_utc(dt: datetime) -> datetime:
    """Convierte una fecha/hora capturada en hora local hacia UTC para el dominio."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=zona_local())
    return dt.astimezone(timezone.utc)


def combinar_local_a_utc(fecha: date, hora: time) -> datetime:
    return local_a_utc(datetime.combine(fecha, hora))


def formatear_hora(dt: datetime, *, formato_24h: bool = True) -> str:
    local = utc_a_local(dt)
    if formato_24h:
        return local.strftime("%H:%M")
    return local.strftime("%I:%M %p").lstrip("0")


def formatear_fecha(fecha: date) -> str:
    return f"{fecha.day:02d} {MESES_ES[fecha.month][:3]} {fecha.year}"


def formatear_fecha_hora(dt: datetime, *, formato_24h: bool = True) -> str:
    local = utc_a_local(dt)
    return f"{formatear_fecha(local.date())} · {formatear_hora(dt, formato_24h=formato_24h)}"


def formatear_rango_evento(
    inicio: datetime,
    fin: datetime | None,
    *,
    todo_el_dia: bool = False,
    formato_24h: bool = True,
) -> str:
    if todo_el_dia:
        return "Todo el día"
    h_ini = formatear_hora(inicio, formato_24h=formato_24h)
    if fin is None:
        return h_ini
    return f"{h_ini} - {formatear_hora(fin, formato_24h=formato_24h)}"


def formatear_antelacion(minutos: int | None) -> str:
    if minutos is None:
        return "Sin recordatorio"
    if minutos == 0:
        return "Al iniciar"
    if minutos < 60:
        return f"{minutos} min antes"
    if minutos % 1440 == 0:
        dias = minutos // 1440
        if dias == 7:
            return "1 semana antes"
        return f"{dias} día antes" if dias == 1 else f"{dias} días antes"
    if minutos % 60 == 0:
        horas = minutos // 60
        return f"{horas} hora antes" if horas == 1 else f"{horas} horas antes"
    horas, rem = divmod(minutos, 60)
    return f"{horas}h {rem}m antes"


def encabezados_dias_semana(primer_dia_semana: int = 1) -> list[str]:
    """Devuelve encabezados de 7 días rotados según primer_dia_semana (1=Lunes..7=Domingo)."""
    inicio_idx = (primer_dia_semana - 1) % 7
    return [DIAS_CORTOS_ES[(inicio_idx + i) % 7] for i in range(7)]


def generar_cuadricula_mes(
    anio: int,
    mes: int,
    primer_dia_semana: int = 1,
) -> list[list[date]]:
    """Genera semanas de 7 fechas (incluyendo días adyacentes) para el calendario mensual."""
    cal = calendar.Calendar(firstweekday=(primer_dia_semana - 1) % 7)
    return cal.monthdatescalendar(anio, mes)


def rango_semana(fecha_ref: date, primer_dia_semana: int = 1) -> list[date]:
    """Devuelve las 7 fechas de la semana que contiene a fecha_ref."""
    inicio_wd = (primer_dia_semana - 1) % 7
    desplazamiento = (fecha_ref.weekday() - inicio_wd) % 7
    inicio = fecha_ref - timedelta(days=desplazamiento)
    return [inicio + timedelta(days=i) for i in range(7)]


def etiqueta_estado_tarea(estado: EstadoTarea) -> str:
    return {
        EstadoTarea.PENDIENTE: "Pendiente",
        EstadoTarea.EN_PROGRESO: "En progreso",
        EstadoTarea.COMPLETADA: "Completada",
    }[estado]


def etiqueta_frecuencia(frecuencia: TipoFrecuencia | None) -> str:
    if frecuencia is None:
        return "Sin repetición"
    return {
        TipoFrecuencia.DIARIA: "Diaria",
        TipoFrecuencia.SEMANAL: "Semanal",
        TipoFrecuencia.MENSUAL: "Mensual",
        TipoFrecuencia.ANUAL: "Anual",
    }[frecuencia]


def etiqueta_vista_agenda(vista: VistaAgenda) -> str:
    return {
        VistaAgenda.DIA: "Día",
        VistaAgenda.SEMANA: "Semana",
        VistaAgenda.MES: "Mes",
        VistaAgenda.ANIO: "Año",
    }[vista]

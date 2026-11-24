"""Enumeraciones del dominio de Agenda Personal y Académica."""

from enum import Enum


class TipoFrecuencia(str, Enum):
    DIARIA = "DIARIA"
    SEMANAL = "SEMANAL"
    MENSUAL = "MENSUAL"
    ANUAL = "ANUAL"


class PrioridadTarea(str, Enum):
    BAJA = "BAJA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"


class EstadoTarea(str, Enum):
    PENDIENTE = "PENDIENTE"
    EN_PROGRESO = "EN_PROGRESO"
    COMPLETADA = "COMPLETADA"


class EstadoRecordatorio(str, Enum):
    PENDIENTE = "PENDIENTE"
    ENTREGADO = "ENTREGADO"
    PERDIDO = "PERDIDO"
    POSPUESTO = "POSPUESTO"
    CANCELADO = "CANCELADO"
    ATENDIDO = "ATENDIDO"


class TipoOrigenRecordatorio(str, Enum):
    EVENTO = "EVENTO"
    TAREA = "TAREA"


class PlataformaSO(str, Enum):
    ANDROID = "ANDROID"
    WINDOWS = "WINDOWS"
    LINUX = "LINUX"


class VistaAgenda(str, Enum):
    DIA = "DIA"
    SEMANA = "SEMANA"
    MES = "MES"
    ANIO = "ANIO"

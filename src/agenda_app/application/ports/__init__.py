"""Puertos (Protocols) de entrada/salida para Inversión de Dependencias (DIP)."""

from agenda_app.application.ports.notificaciones import (
    ACCION_COMPLETAR_TAREA,
    ACCION_MARCAR_VISTO,
    ACCION_POSPONER,
    AccionNotificacion,
    CapacidadesNotificacionSO,
    ContenidoNotificacion,
    EventoInteraccionNotificacion,
    IAdaptadorNotificaciones,
    IProveedorContenidoRecordatorio,
    SolicitudNotificacion,
)
from agenda_app.application.ports.reloj import IReloj
from agenda_app.application.ports.repositorios import (
    IRepositorioAjustes,
    IRepositorioRecordatorios,
)

__all__ = [
    "ACCION_COMPLETAR_TAREA",
    "ACCION_MARCAR_VISTO",
    "ACCION_POSPONER",
    "AccionNotificacion",
    "CapacidadesNotificacionSO",
    "ContenidoNotificacion",
    "EventoInteraccionNotificacion",
    "IAdaptadorNotificaciones",
    "IProveedorContenidoRecordatorio",
    "IReloj",
    "IRepositorioAjustes",
    "IRepositorioRecordatorios",
    "SolicitudNotificacion",
]

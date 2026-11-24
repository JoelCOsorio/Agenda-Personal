"""Entidades del dominio."""

from agenda_app.domain.entities.base import EntidadBase, asegurar_utc
from agenda_app.domain.entities.categoria import Categoria, Subcategoria
from agenda_app.domain.entities.configuracion import ConfiguracionSistema
from agenda_app.domain.entities.contacto import Contacto
from agenda_app.domain.entities.evento import Evento, RangoHorario, ReglaRecurrencia
from agenda_app.domain.entities.recordatorio import Recordatorio
from agenda_app.domain.entities.tarea import Tarea

__all__ = [
    "Categoria",
    "ConfiguracionSistema",
    "Contacto",
    "EntidadBase",
    "Evento",
    "RangoHorario",
    "Recordatorio",
    "ReglaRecurrencia",
    "Subcategoria",
    "Tarea",
    "asegurar_utc",
]

"""Excepciones específicas de la capa de dominio."""


class DominioError(Exception):
    """Excepción base para infracciones de reglas de negocio."""


class RangoTemporalInvalidoError(DominioError):
    """Se lanza cuando la fecha/hora de fin es anterior a la de inicio (RN-01)."""


class ChoqueEventosError(DominioError):
    """Se lanza cuando existe solapamiento con otro evento (RN-11)."""


class RecordatorioInvalidoError(DominioError):
    """Se lanza cuando un recordatorio infringe RN-03 o sus invariantes de dominio."""


class ConfiguracionInvalidaError(DominioError):
    """Se lanza cuando un parámetro de ConfiguracionSistema está fuera de rango."""


class PermisoNotificacionError(DominioError):
    """Se lanza cuando el SO no concede permisos necesarios para programar alertas."""

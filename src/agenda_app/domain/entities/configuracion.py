"""Entidad singleton ConfiguracionSistema para el módulo de Ajustes (RN-14, RF-23, RF-24)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from agenda_app.domain.entities.base import EntidadBase
from agenda_app.domain.entities.recordatorio import MAX_ANTELACION_MINUTOS
from agenda_app.domain.enums import VistaAgenda
from agenda_app.domain.exceptions import ConfiguracionInvalidaError

CONFIG_SINGLETON_UUID = UUID("00000000-0000-4000-8000-000000000001")
MIN_SNOOZE_MINUTOS = 1
MAX_SNOOZE_MINUTOS = 24 * 60  # 1,440 minutos (24 horas)


@dataclass
class ConfiguracionSistema(EntidadBase):
    """Parámetros globales configurables en Ajustes (RN-14)."""

    id: UUID = field(default=CONFIG_SINGLETON_UUID)
    minutos_posponer_defecto: int = 10
    antelacion_recordatorio_defecto_min: int = 15
    sonido_notificaciones: bool = True
    mostrar_alertas_perdidas_inicio: bool = True
    formato_24h: bool = True
    primer_dia_semana: int = 1  # 1=Lunes .. 7=Domingo
    vista_inicial_agenda: VistaAgenda = VistaAgenda.MES
    tema_oscuro: bool = False

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validar()

    def _validar(self) -> None:
        if not (MIN_SNOOZE_MINUTOS <= self.minutos_posponer_defecto <= MAX_SNOOZE_MINUTOS):
            raise ConfiguracionInvalidaError(
                f"minutos_posponer_defecto debe estar en [{MIN_SNOOZE_MINUTOS}, {MAX_SNOOZE_MINUTOS}]."
            )
        if not (0 <= self.antelacion_recordatorio_defecto_min <= MAX_ANTELACION_MINUTOS):
            raise ConfiguracionInvalidaError(
                f"antelacion_recordatorio_defecto_min debe estar en [0, {MAX_ANTELACION_MINUTOS}]."
            )
        if not (1 <= self.primer_dia_semana <= 7):
            raise ConfiguracionInvalidaError("primer_dia_semana debe estar entre 1 (Lunes) y 7 (Domingo).")

    def restablecer_valores_defecto(self, ahora: datetime) -> None:
        """Restaura valores seguros por defecto (RF-24)."""
        self.minutos_posponer_defecto = 10
        self.antelacion_recordatorio_defecto_min = 15
        self.sonido_notificaciones = True
        self.mostrar_alertas_perdidas_inicio = True
        self.formato_24h = True
        self.primer_dia_semana = 1
        self.vista_inicial_agenda = VistaAgenda.MES
        self.tema_oscuro = False
        self.tocar_actualizacion(ahora)

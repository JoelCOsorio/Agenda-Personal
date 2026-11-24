"""Entidades Evento y ReglaRecurrencia del Módulo de Agenda (RN-01, RN-04, RF-06)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from agenda_app.domain.entities.base import EntidadBase, asegurar_utc
from agenda_app.domain.entities.categoria import validar_color_hex
from agenda_app.domain.enums import TipoFrecuencia
from agenda_app.domain.exceptions import (
    RangoTemporalInvalidoError,
    ValidacionEntidadError,
)

DIAS_SEMANA_VALIDOS = ("LU", "MA", "MI", "JU", "VI", "SA", "DO")


@dataclass(frozen=True)
class RangoHorario:
    """Intervalo temporal inmutable en UTC."""

    inicio: datetime
    fin: datetime | None = None

    def __post_init__(self) -> None:
        ini = asegurar_utc(self.inicio)
        object.__setattr__(self, "inicio", ini)
        if self.fin is not None:
            fin_utc = asegurar_utc(self.fin)
            if fin_utc < ini:
                raise RangoTemporalInvalidoError(
                    "RN-01: La fecha/hora de fin no puede ser anterior a la de inicio."
                )
            object.__setattr__(self, "fin", fin_utc)


@dataclass
class ReglaRecurrencia(EntidadBase):
    """Regla de repetición periódica (0..1 por Evento — RF-06)."""

    evento_id: UUID | None = None
    frecuencia: TipoFrecuencia = TipoFrecuencia.SEMANAL
    intervalo: int = 1
    dias_semana: tuple[str, ...] = field(default_factory=tuple)
    fecha_fin_recurrencia: date | None = None
    max_ocurrencias: int | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.intervalo < 1:
            raise ValidacionEntidadError("El intervalo de recurrencia debe ser >= 1.")
        if self.max_ocurrencias is not None and self.max_ocurrencias < 1:
            raise ValidacionEntidadError("max_ocurrencias debe ser >= 1.")

        dias_norm = tuple(d.strip().upper() for d in self.dias_semana if d.strip())
        for dia in dias_norm:
            if dia not in DIAS_SEMANA_VALIDOS:
                raise ValidacionEntidadError(
                    f"Día de semana inválido '{dia}'. Use {DIAS_SEMANA_VALIDOS}."
                )
        self.dias_semana = dias_norm

    def dias_como_texto(self) -> str | None:
        return ",".join(self.dias_semana) if self.dias_semana else None

    @staticmethod
    def parsear_dias_texto(valor: str | None) -> tuple[str, ...]:
        if not valor:
            return ()
        return tuple(d.strip().upper() for d in valor.split(",") if d.strip())


@dataclass
class Evento(EntidadBase):
    """Evento calendarizado en el Módulo de Agenda (RN-01, RN-04, RN-11)."""

    titulo: str = ""
    fecha_inicio: datetime = field(default_factory=lambda: datetime.min)
    fecha_fin: datetime | None = None
    todo_el_dia: bool = False
    descripcion: str | None = None
    ubicacion: str | None = None
    color_hex: str | None = None
    categoria_id: UUID | None = None
    subcategoria_id: UUID | None = None
    contacto_ids: tuple[UUID, ...] = field(default_factory=tuple)
    recurrencia: ReglaRecurrencia | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self.titulo = self.titulo.strip()
        if not self.titulo:
            raise ValidacionEntidadError("El título del evento es obligatorio.")

        self.fecha_inicio = asegurar_utc(self.fecha_inicio)
        if self.fecha_fin is not None:
            self.fecha_fin = asegurar_utc(self.fecha_fin)
            if not self.todo_el_dia and self.fecha_fin < self.fecha_inicio:
                raise RangoTemporalInvalidoError(
                    "RN-01: La fecha/hora de fin debe ser mayor o igual a la fecha/hora de inicio."
                )

        self.color_hex = validar_color_hex(self.color_hex)
        # Eliminar duplicados preservando orden
        self.contacto_ids = tuple(dict.fromkeys(self.contacto_ids))

        if self.recurrencia is not None and self.recurrencia.evento_id is None:
            self.recurrencia.evento_id = self.id

    def es_pasado(self, referencia: datetime) -> bool:
        """Indica si el evento ya venció respecto a la fecha de referencia (RN-04)."""
        ref_utc = asegurar_utc(referencia)
        corte = self.fecha_fin if self.fecha_fin is not None else self.fecha_inicio
        return corte < ref_utc

    def reprogramar(
        self,
        nuevo_inicio: datetime,
        nuevo_fin: datetime | None,
        ahora: datetime,
    ) -> None:
        inicio_utc = asegurar_utc(nuevo_inicio)
        fin_utc = asegurar_utc(nuevo_fin) if nuevo_fin is not None else None
        if not self.todo_el_dia and fin_utc is not None and fin_utc < inicio_utc:
            raise RangoTemporalInvalidoError(
                "RN-01: La fecha/hora de fin debe ser mayor o igual a la fecha/hora de inicio."
            )
        self.fecha_inicio = inicio_utc
        self.fecha_fin = fin_utc
        self.tocar_actualizacion(ahora)

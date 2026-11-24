"""Puertos segregados de persistencia para todos los módulos del dominio (ISP)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from agenda_app.domain.entities.categoria import Categoria, Subcategoria
from agenda_app.domain.entities.configuracion import ConfiguracionSistema
from agenda_app.domain.entities.contacto import Contacto
from agenda_app.domain.entities.evento import Evento
from agenda_app.domain.entities.recordatorio import Recordatorio
from agenda_app.domain.entities.tarea import Tarea
from agenda_app.domain.enums import (
    EstadoTarea,
    PrioridadTarea,
    TipoOrigenRecordatorio,
)


class IRepositorioRecordatorios(Protocol):
    """Operaciones de persistencia sobre la entidad Recordatorio."""

    def guardar(self, recordatorio: Recordatorio) -> None: ...

    def obtener_por_id(self, recordatorio_id: UUID) -> Recordatorio | None: ...

    def obtener_por_item(
        self,
        tipo_origen: TipoOrigenRecordatorio,
        item_id: UUID,
    ) -> Recordatorio | None: ...

    def obtener_pendientes_vencidos(self, ahora: datetime) -> list[Recordatorio]: ...

    def obtener_pendientes_futuros(
        self,
        ahora: datetime,
        hasta: datetime | None = None,
        limite: int = 200,
    ) -> list[Recordatorio]: ...

    def obtener_perdidos(self) -> list[Recordatorio]: ...

    def siguiente_id_notificacion_so(self) -> int: ...

    def eliminar(self, recordatorio_id: UUID) -> None: ...


class IRepositorioAjustes(Protocol):
    """Operaciones de persistencia sobre el singleton ConfiguracionSistema."""

    def obtener(self) -> ConfiguracionSistema: ...

    def guardar(self, configuracion: ConfiguracionSistema) -> None: ...


class IRepositorioCategorias(Protocol):
    """Operaciones de persistencia sobre Categorias y Subcategorias (RN-09)."""

    def guardar_categoria(self, categoria: Categoria) -> None: ...

    def obtener_categoria(self, categoria_id: UUID) -> Categoria | None: ...

    def listar_categorias(self) -> list[Categoria]: ...

    def eliminar_categoria(self, categoria_id: UUID) -> None: ...

    def guardar_subcategoria(self, subcategoria: Subcategoria) -> None: ...

    def obtener_subcategoria(self, subcategoria_id: UUID) -> Subcategoria | None: ...

    def listar_subcategorias(self, categoria_id: UUID | None = None) -> list[Subcategoria]: ...

    def eliminar_subcategoria(self, subcategoria_id: UUID) -> None: ...

    def subcategoria_pertenece_a(
        self, subcategoria_id: UUID, categoria_id: UUID
    ) -> bool: ...


class IRepositorioContactos(Protocol):
    """Operaciones de persistencia sobre Contactos (RF-17, RN-13)."""

    def guardar(self, contacto: Contacto) -> None: ...

    def obtener_por_id(self, contacto_id: UUID) -> Contacto | None: ...

    def obtener_varios(self, ids: Sequence[UUID]) -> list[Contacto]: ...

    def buscar(
        self,
        termino: str | None = None,
        etiqueta: str | None = None,
    ) -> list[Contacto]: ...

    def eliminar(self, contacto_id: UUID) -> None: ...


class IRepositorioEventos(Protocol):
    """Operaciones de persistencia sobre Eventos, ReglaRecurrencia y vínculos."""

    def guardar(self, evento: Evento) -> None: ...

    def obtener_por_id(self, evento_id: UUID) -> Evento | None: ...

    def listar_candidatos_solapamiento(
        self,
        desde: datetime,
        hasta: datetime,
    ) -> list[Evento]: ...

    def listar_en_rango(
        self,
        desde: datetime,
        hasta: datetime,
        *,
        categoria_id: UUID | None = None,
        subcategoria_id: UUID | None = None,
    ) -> list[Evento]: ...

    def listar_historial(self, antes_de: datetime) -> list[Evento]: ...

    def eliminar(self, evento_id: UUID) -> None: ...


class IRepositorioTareas(Protocol):
    """Operaciones de persistencia sobre Tareas y vínculos con Contactos."""

    def guardar(self, tarea: Tarea) -> None: ...

    def obtener_por_id(self, tarea_id: UUID) -> Tarea | None: ...

    def listar(
        self,
        *,
        estado: EstadoTarea | None = None,
        prioridad: PrioridadTarea | None = None,
        categoria_id: UUID | None = None,
        subcategoria_id: UUID | None = None,
    ) -> list[Tarea]: ...

    def eliminar(self, tarea_id: UUID) -> None: ...

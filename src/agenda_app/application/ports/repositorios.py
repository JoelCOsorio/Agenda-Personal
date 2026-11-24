"""Puertos segregados de persistencia para Recordatorios y Ajustes (ISP)."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from agenda_app.domain.entities.configuracion import ConfiguracionSistema
from agenda_app.domain.entities.recordatorio import Recordatorio
from agenda_app.domain.enums import TipoOrigenRecordatorio


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

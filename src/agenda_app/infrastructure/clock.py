"""Implementación productiva del puerto IReloj en UTC."""

from __future__ import annotations

from datetime import datetime, timezone


class RelojSistemaUTC:
    """Devuelve la hora actual del sistema en UTC."""

    def ahora_utc(self) -> datetime:
        return datetime.now(timezone.utc)

"""Puerto de reloj para permitir pruebas temporales deterministas."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class IReloj(Protocol):
    """Provee la hora actual en UTC."""

    def ahora_utc(self) -> datetime: ...

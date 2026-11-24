"""Puerto para delegar acciones externas al sistema operativo (mailto:, tel: — RN-08)."""

from __future__ import annotations

from typing import Protocol


class ILanzadorAccionesExternas(Protocol):
    """Abstracción para abrir aplicaciones externas según la plataforma actual."""

    def puede_llamar(self) -> bool: ...

    async def abrir_uri(self, uri: str) -> bool: ...

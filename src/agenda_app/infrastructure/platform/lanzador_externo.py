"""Implementación multiplataforma para lanzar apps externas (mailto:, tel: — RN-08)."""

from __future__ import annotations

import asyncio
import webbrowser
from typing import Any

from agenda_app.domain.enums import PlataformaSO


class LanzadorAccionesExternasSO:
    """Delega URIs al SO usando ft.UrlLauncher (si hay página Flet) o webbrowser."""

    def __init__(
        self,
        plataforma: PlataformaSO,
        url_launcher: Any | None = None,
    ) -> None:
        self._plataforma = plataforma
        self._url_launcher = url_launcher

    def puede_llamar(self) -> bool:
        """Las llamadas telefónicas (tel:) solo están habilitadas en Android (RN-08)."""
        return self._plataforma == PlataformaSO.ANDROID

    async def abrir_uri(self, uri: str) -> bool:
        if uri.startswith("tel:") and not self.puede_llamar():
            return False

        if self._url_launcher is not None:
            resultado = self._url_launcher.launch_url(uri)
            if asyncio.iscoroutine(resultado):
                await resultado
            return True

        return bool(webbrowser.open(uri))

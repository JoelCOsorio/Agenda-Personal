"""Worker residente ligero para Linux (D-Bus via desktop-notifier + SQLite WAL).

Permite entregar notificaciones programadas en Linux incluso con la app Flet cerrada,
ejecutándose como servicio de usuario (`systemd --user`).

Uso manual:
    uv run python -m agenda_app.infrastructure.notifications.linux_worker
"""

from __future__ import annotations

import asyncio
import signal
from datetime import timedelta
from pathlib import Path
from uuid import UUID

from agenda_app.application.ports.reloj import IReloj
from agenda_app.domain.entities.recordatorio import Recordatorio
from agenda_app.domain.enums import TipoOrigenRecordatorio
from agenda_app.infrastructure.clock import RelojSistemaUTC
from agenda_app.infrastructure.paths import obtener_ruta_db
from agenda_app.infrastructure.persistence.sqlite.database import SQLiteDatabase
from agenda_app.infrastructure.persistence.sqlite.migrations import aplicar_migraciones
from agenda_app.infrastructure.persistence.sqlite.repo_ajustes import (
    RepositorioAjustesSQLite,
)
from agenda_app.infrastructure.persistence.sqlite.repo_recordatorios import (
    ProveedorContenidoSQLite,
    RepositorioRecordatoriosSQLite,
)

INTERVALO_SONDEO_SEGUNDOS = 10.0


class LinuxNotificationWorker:
    """Servicio de fondo que monitorea SQLite WAL y dispara alertas nativas por D-Bus."""

    def __init__(
        self,
        db_path: Path | str | None = None,
        reloj: IReloj | None = None,
        intervalo_sondeo: float = INTERVALO_SONDEO_SEGUNDOS,
    ) -> None:
        self._db = SQLiteDatabase(obtener_ruta_db(db_path))
        aplicar_migraciones(self._db)
        self._repo_rec = RepositorioRecordatoriosSQLite(self._db)
        self._repo_ajustes = RepositorioAjustesSQLite(self._db)
        self._proveedor = ProveedorContenidoSQLite(self._db)
        self._reloj: IReloj = reloj if reloj is not None else RelojSistemaUTC()
        self._intervalo = intervalo_sondeo
        self._detener_evento = asyncio.Event()

    async def ejecutar(self) -> None:
        from desktop_notifier import Button, Capability, DEFAULT_SOUND, DesktopNotifier, Urgency

        notifier = DesktopNotifier(app_name="Atempo")
        caps = await notifier.get_capabilities()
        soporta_botones = Capability.BUTTONS in caps
        loop = asyncio.get_running_loop()

        while not self._detener_evento.is_set():
            ahora = self._reloj.ahora_utc()
            vencidos = self._repo_rec.obtener_pendientes_vencidos(ahora)
            ajustes = self._repo_ajustes.obtener()

            for rec in vencidos:
                await self._despachar_uno(
                    notifier=notifier,
                    rec=rec,
                    con_sonido=ajustes.sonido_notificaciones,
                    soporta_botones=soporta_botones,
                    button_cls=Button,
                    urgency=Urgency.Normal,
                    default_sound=DEFAULT_SOUND,
                    loop=loop,
                )

            # Calcular espera hasta el siguiente recordatorio futuro o el intervalo de sondeo
            futuros = self._repo_rec.obtener_pendientes_futuros(ahora=ahora, limite=1)
            espera = self._intervalo
            if futuros:
                delta = (futuros[0].fecha_disparo - ahora).total_seconds()
                espera = max(0.2, min(self._intervalo, delta))

            try:
                await asyncio.wait_for(self._detener_evento.wait(), timeout=espera)
            except TimeoutError:
                pass

    def solicitar_detencion(self) -> None:
        self._detener_evento.set()

    async def _despachar_uno(
        self,
        *,
        notifier: object,
        rec: Recordatorio,
        con_sonido: bool,
        soporta_botones: bool,
        button_cls: type,
        urgency: object,
        default_sound: object,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        contenido = self._proveedor.obtener_contenido(rec.tipo_origen, rec.item_id)
        if contenido is not None:
            titulo = contenido.titulo
            cuerpo = contenido.cuerpo or "Tienes una actividad programada."
        else:
            etiqueta = (
                "Evento de Agenda"
                if rec.tipo_origen == TipoOrigenRecordatorio.EVENTO
                else "Tarea Pendiente"
            )
            titulo = f"Recordatorio: {etiqueta}"
            cuerpo = "Tienes una actividad programada."

        rec.marcar_entregado(self._reloj.ahora_utc())
        self._repo_rec.guardar(rec)

        rid = rec.id

        def _posponer() -> None:
            loop.call_soon_threadsafe(self._aplicar_posponer, rid)

        def _marcar_visto() -> None:
            loop.call_soon_threadsafe(self._aplicar_atendido, rid)

        botones = (
            [
                button_cls(title="Posponer", on_pressed=_posponer),
                button_cls(title="Marcar como visto", on_pressed=_marcar_visto),
            ]
            if soporta_botones
            else []
        )

        await notifier.send(  # type: ignore[attr-defined]
            title=titulo,
            message=cuerpo,
            urgency=urgency,
            buttons=botones,
            sound=default_sound if con_sonido else None,
            on_clicked=_marcar_visto,
        )

    def _aplicar_posponer(self, recordatorio_id: UUID) -> None:
        rec = self._repo_rec.obtener_por_id(recordatorio_id)
        if rec is None:
            return
        ahora = self._reloj.ahora_utc()
        minutos = self._repo_ajustes.obtener().minutos_posponer_defecto
        rec.posponer(nueva_fecha_disparo=ahora + timedelta(minutes=minutos), ahora=ahora)
        self._repo_rec.guardar(rec)

    def _aplicar_atendido(self, recordatorio_id: UUID) -> None:
        rec = self._repo_rec.obtener_por_id(recordatorio_id)
        if rec is None:
            return
        rec.marcar_atendido(self._reloj.ahora_utc())
        self._repo_rec.guardar(rec)


def generar_unidad_systemd(ruta_proyecto: Path) -> str:
    """Genera el archivo de servicio de usuario (~/.config/systemd/user/agenda-notificaciones.service)."""
    return f"""[Unit]
Description=Worker de Notificaciones Locales - Agenda Personal
After=graphical-session.target

[Service]
Type=simple
WorkingDirectory={ruta_proyecto}
ExecStart={ruta_proyecto}/.venv/bin/python -m agenda_app.infrastructure.notifications.linux_worker
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
"""


async def _main() -> None:
    worker = LinuxNotificationWorker()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, worker.solicitar_detencion)
    await worker.ejecutar()


if __name__ == "__main__":
    asyncio.run(_main())

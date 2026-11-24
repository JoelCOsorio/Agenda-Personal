"""Composition Root (Inyección de Dependencias) para ensamblar el motor y repositorios."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agenda_app.application.ports.notificaciones import IAdaptadorNotificaciones
from agenda_app.application.ports.reloj import IReloj
from agenda_app.application.services.motor_notificaciones import MotorNotificaciones
from agenda_app.application.services.startup_reconciler import StartupReconciler
from agenda_app.domain.enums import PlataformaSO
from agenda_app.infrastructure.clock import RelojSistemaUTC
from agenda_app.infrastructure.notifications.factory import (
    crear_adaptador_notificaciones,
)
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
from agenda_app.infrastructure.platform.detector_so import detectar_plataforma


@dataclass
class ContenedorNotificaciones:
    """Agrupa las dependencias ya ensambladas del subsistema de notificaciones."""

    plataforma: PlataformaSO
    db: SQLiteDatabase
    reloj: IReloj
    repo_recordatorios: RepositorioRecordatoriosSQLite
    repo_ajustes: RepositorioAjustesSQLite
    adaptador: IAdaptadorNotificaciones
    motor: MotorNotificaciones
    reconciliador: StartupReconciler


def construir_contenedor_notificaciones(
    *,
    page_platform: Any | None = None,
    db_path: Path | str | None = None,
    cliente_flet: Any | None = None,
    reloj: IReloj | None = None,
    adaptador_personalizado: IAdaptadorNotificaciones | None = None,
) -> ContenedorNotificaciones:
    """Ensambla las capas Dominio -> Aplicación -> Infraestructura (DIP)."""
    plataforma = detectar_plataforma(page_platform)
    reloj_activo: IReloj = reloj if reloj is not None else RelojSistemaUTC()

    db = SQLiteDatabase(obtener_ruta_db(db_path))
    aplicar_migraciones(db)

    repo_recordatorios = RepositorioRecordatoriosSQLite(db)
    repo_ajustes = RepositorioAjustesSQLite(db)
    proveedor_contenido = ProveedorContenidoSQLite(db)

    adaptador = (
        adaptador_personalizado
        if adaptador_personalizado is not None
        else crear_adaptador_notificaciones(
            plataforma,
            cliente_flet=cliente_flet,
            reloj=reloj_activo,
        )
    )

    motor = MotorNotificaciones(
        repo_recordatorios=repo_recordatorios,
        repo_ajustes=repo_ajustes,
        adaptador=adaptador,
        reloj=reloj_activo,
        proveedor_contenido=proveedor_contenido,
    )

    reconciliador = StartupReconciler(
        repo_recordatorios=repo_recordatorios,
        repo_ajustes=repo_ajustes,
        motor=motor,
        adaptador=adaptador,
        reloj=reloj_activo,
    )

    return ContenedorNotificaciones(
        plataforma=plataforma,
        db=db,
        reloj=reloj_activo,
        repo_recordatorios=repo_recordatorios,
        repo_ajustes=repo_ajustes,
        adaptador=adaptador,
        motor=motor,
        reconciliador=reconciliador,
    )

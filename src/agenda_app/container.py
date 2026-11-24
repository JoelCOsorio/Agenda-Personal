"""Composition Root (Inyección de Dependencias) para ensamblar toda la aplicación."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from agenda_app.application.ports.acciones_externas import ILanzadorAccionesExternas
from agenda_app.application.ports.notificaciones import IAdaptadorNotificaciones
from agenda_app.application.ports.reloj import IReloj
from agenda_app.application.services.motor_notificaciones import MotorNotificaciones
from agenda_app.application.services.servicio_ajustes import ServicioAjustes
from agenda_app.application.services.servicio_categorias import ServicioCategorias
from agenda_app.application.services.servicio_contactos import ServicioContactos
from agenda_app.application.services.servicio_eventos import ServicioEventos
from agenda_app.application.services.servicio_tareas import ServicioTareas
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
from agenda_app.infrastructure.persistence.sqlite.repo_categorias import (
    RepositorioCategoriasSQLite,
)
from agenda_app.infrastructure.persistence.sqlite.repo_contactos import (
    RepositorioContactosSQLite,
)
from agenda_app.infrastructure.persistence.sqlite.repo_eventos import (
    RepositorioEventosSQLite,
)
from agenda_app.infrastructure.persistence.sqlite.repo_recordatorios import (
    ProveedorContenidoSQLite,
    RepositorioRecordatoriosSQLite,
)
from agenda_app.infrastructure.persistence.sqlite.repo_tareas import (
    RepositorioTareasSQLite,
)
from agenda_app.infrastructure.platform.detector_so import detectar_plataforma
from agenda_app.infrastructure.platform.lanzador_externo import (
    LanzadorAccionesExternasSO,
)


@dataclass
class ContenedorAplicacion:
    """Agrupa todas las dependencias ensambladas de Dominio, Aplicación e Infraestructura."""

    plataforma: PlataformaSO
    db: SQLiteDatabase
    reloj: IReloj
    repo_recordatorios: RepositorioRecordatoriosSQLite
    repo_ajustes: RepositorioAjustesSQLite
    repo_categorias: RepositorioCategoriasSQLite
    repo_contactos: RepositorioContactosSQLite
    repo_eventos: RepositorioEventosSQLite
    repo_tareas: RepositorioTareasSQLite
    adaptador: IAdaptadorNotificaciones
    lanzador_externo: ILanzadorAccionesExternas
    motor: MotorNotificaciones
    reconciliador: StartupReconciler
    servicio_ajustes: ServicioAjustes
    servicio_categorias: ServicioCategorias
    servicio_contactos: ServicioContactos
    servicio_eventos: ServicioEventos
    servicio_tareas: ServicioTareas


# Alias de compatibilidad hacia atrás con poc_notificaciones.py
ContenedorNotificaciones = ContenedorAplicacion


def construir_contenedor_aplicacion(
    *,
    page_platform: Any | None = None,
    db_path: Path | str | None = None,
    cliente_flet: Any | None = None,
    url_launcher: Any | None = None,
    reloj: IReloj | None = None,
    adaptador_personalizado: IAdaptadorNotificaciones | None = None,
    lanzador_personalizado: ILanzadorAccionesExternas | None = None,
) -> ContenedorAplicacion:
    """Ensambla las capas Dominio -> Aplicación -> Infraestructura (DIP)."""
    plataforma = detectar_plataforma(page_platform)
    reloj_activo: IReloj = reloj if reloj is not None else RelojSistemaUTC()

    db = SQLiteDatabase(obtener_ruta_db(db_path))
    aplicar_migraciones(db)

    repo_recordatorios = RepositorioRecordatoriosSQLite(db)
    repo_ajustes = RepositorioAjustesSQLite(db)
    repo_categorias = RepositorioCategoriasSQLite(db)
    repo_contactos = RepositorioContactosSQLite(db)
    repo_eventos = RepositorioEventosSQLite(db)
    repo_tareas = RepositorioTareasSQLite(db)
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
    lanzador = (
        lanzador_personalizado
        if lanzador_personalizado is not None
        else LanzadorAccionesExternasSO(plataforma=plataforma, url_launcher=url_launcher)
    )

    servicio_tareas_ref: list[ServicioTareas] = []

    async def _completar_tarea_desde_notificacion(tarea_id: UUID) -> None:
        if servicio_tareas_ref:
            await servicio_tareas_ref[0].completar_tarea(tarea_id)

    motor = MotorNotificaciones(
        repo_recordatorios=repo_recordatorios,
        repo_ajustes=repo_ajustes,
        adaptador=adaptador,
        reloj=reloj_activo,
        proveedor_contenido=proveedor_contenido,
        on_completar_tarea=_completar_tarea_desde_notificacion,
    )

    reconciliador = StartupReconciler(
        repo_recordatorios=repo_recordatorios,
        repo_ajustes=repo_ajustes,
        repo_eventos=repo_eventos,
        motor=motor,
        adaptador=adaptador,
        reloj=reloj_activo,
    )

    servicio_ajustes = ServicioAjustes(repo_ajustes=repo_ajustes, reloj=reloj_activo)
    servicio_categorias = ServicioCategorias(
        repo_categorias=repo_categorias, reloj=reloj_activo
    )
    servicio_contactos = ServicioContactos(
        repo_contactos=repo_contactos,
        reloj=reloj_activo,
        plataforma=plataforma,
        lanzador=lanzador,
    )
    servicio_eventos = ServicioEventos(
        repo_eventos=repo_eventos,
        repo_categorias=repo_categorias,
        repo_recordatorios=repo_recordatorios,
        motor_notificaciones=motor,
        reloj=reloj_activo,
    )
    servicio_tareas = ServicioTareas(
        repo_tareas=repo_tareas,
        repo_categorias=repo_categorias,
        repo_recordatorios=repo_recordatorios,
        motor_notificaciones=motor,
        reloj=reloj_activo,
    )
    servicio_tareas_ref.append(servicio_tareas)

    return ContenedorAplicacion(
        plataforma=plataforma,
        db=db,
        reloj=reloj_activo,
        repo_recordatorios=repo_recordatorios,
        repo_ajustes=repo_ajustes,
        repo_categorias=repo_categorias,
        repo_contactos=repo_contactos,
        repo_eventos=repo_eventos,
        repo_tareas=repo_tareas,
        adaptador=adaptador,
        lanzador_externo=lanzador,
        motor=motor,
        reconciliador=reconciliador,
        servicio_ajustes=servicio_ajustes,
        servicio_categorias=servicio_categorias,
        servicio_contactos=servicio_contactos,
        servicio_eventos=servicio_eventos,
        servicio_tareas=servicio_tareas,
    )


def construir_contenedor_notificaciones(**kwargs: Any) -> ContenedorAplicacion:
    """Wrapper de compatibilidad hacia atrás con el PoC de notificaciones."""
    return construir_contenedor_aplicacion(**kwargs)

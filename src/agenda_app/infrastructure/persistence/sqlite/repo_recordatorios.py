"""Repositorio SQLite de Recordatorios (implementa IRepositorioRecordatorios)."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from uuid import UUID

from agenda_app.application.ports.notificaciones import ContenidoNotificacion
from agenda_app.domain.entities.base import asegurar_utc
from agenda_app.domain.entities.recordatorio import (
    MAX_ID_NOTIFICACION_SO,
    Recordatorio,
)
from agenda_app.domain.enums import EstadoRecordatorio, TipoOrigenRecordatorio
from agenda_app.infrastructure.persistence.sqlite.database import SQLiteDatabase


def _dt_a_iso(dt: datetime) -> str:
    return asegurar_utc(dt).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _iso_a_dt(valor: str) -> datetime:
    normalizado = valor.replace("Z", "+00:00")
    return asegurar_utc(datetime.fromisoformat(normalizado))


class RepositorioRecordatoriosSQLite:
    """Persistencia SQLite para la entidad Recordatorio."""

    def __init__(self, db: SQLiteDatabase) -> None:
        self._db = db

    def guardar(self, recordatorio: Recordatorio) -> None:
        with self._db.transaccion() as conn:
            conn.execute(
                """
                INSERT INTO recordatorios (
                    id, id_notificacion_so, tipo_origen, evento_id, tarea_id,
                    antelacion_minutos, fecha_disparo, estado, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    id_notificacion_so = excluded.id_notificacion_so,
                    tipo_origen        = excluded.tipo_origen,
                    evento_id          = excluded.evento_id,
                    tarea_id           = excluded.tarea_id,
                    antelacion_minutos = excluded.antelacion_minutos,
                    fecha_disparo      = excluded.fecha_disparo,
                    estado             = excluded.estado,
                    updated_at         = excluded.updated_at
                """,
                (
                    str(recordatorio.id),
                    recordatorio.id_notificacion_so,
                    recordatorio.tipo_origen.value,
                    str(recordatorio.evento_id) if recordatorio.evento_id else None,
                    str(recordatorio.tarea_id) if recordatorio.tarea_id else None,
                    recordatorio.antelacion_minutos,
                    _dt_a_iso(recordatorio.fecha_disparo),
                    recordatorio.estado.value,
                    _dt_a_iso(recordatorio.created_at),
                    _dt_a_iso(recordatorio.updated_at),
                ),
            )

    def obtener_por_id(self, recordatorio_id: UUID) -> Recordatorio | None:
        with self._db.transaccion() as conn:
            row = conn.execute(
                "SELECT * FROM recordatorios WHERE id = ?",
                (str(recordatorio_id),),
            ).fetchone()
            return self._fila_a_entidad(row) if row else None

    def obtener_por_item(
        self,
        tipo_origen: TipoOrigenRecordatorio,
        item_id: UUID,
    ) -> Recordatorio | None:
        columna = "evento_id" if tipo_origen == TipoOrigenRecordatorio.EVENTO else "tarea_id"
        with self._db.transaccion() as conn:
            row = conn.execute(
                f"SELECT * FROM recordatorios WHERE {columna} = ?",
                (str(item_id),),
            ).fetchone()
            return self._fila_a_entidad(row) if row else None

    def obtener_pendientes_vencidos(self, ahora: datetime) -> list[Recordatorio]:
        ahora_iso = _dt_a_iso(ahora)
        with self._db.transaccion() as conn:
            filas = conn.execute(
                """
                SELECT * FROM recordatorios
                WHERE estado IN ('PENDIENTE', 'POSPUESTO')
                  AND fecha_disparo < ?
                ORDER BY fecha_disparo ASC
                """,
                (ahora_iso,),
            ).fetchall()
            return [self._fila_a_entidad(f) for f in filas]

    def obtener_pendientes_futuros(
        self,
        ahora: datetime,
        hasta: datetime | None = None,
        limite: int = 200,
    ) -> list[Recordatorio]:
        ahora_iso = _dt_a_iso(ahora)
        with self._db.transaccion() as conn:
            if hasta is not None:
                filas = conn.execute(
                    """
                    SELECT * FROM recordatorios
                    WHERE estado IN ('PENDIENTE', 'POSPUESTO')
                      AND fecha_disparo >= ?
                      AND fecha_disparo <= ?
                    ORDER BY fecha_disparo ASC
                    LIMIT ?
                    """,
                    (ahora_iso, _dt_a_iso(hasta), limite),
                ).fetchall()
            else:
                filas = conn.execute(
                    """
                    SELECT * FROM recordatorios
                    WHERE estado IN ('PENDIENTE', 'POSPUESTO')
                      AND fecha_disparo >= ?
                    ORDER BY fecha_disparo ASC
                    LIMIT ?
                    """,
                    (ahora_iso, limite),
                ).fetchall()
            return [self._fila_a_entidad(f) for f in filas]

    def obtener_perdidos(self) -> list[Recordatorio]:
        with self._db.transaccion() as conn:
            filas = conn.execute(
                """
                SELECT * FROM recordatorios
                WHERE estado = 'PERDIDO'
                ORDER BY fecha_disparo DESC
                """
            ).fetchall()
            return [self._fila_a_entidad(f) for f in filas]

    def siguiente_id_notificacion_so(self) -> int:
        with self._db.transaccion() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(id_notificacion_so), 0) AS max_id FROM recordatorios"
            ).fetchone()
            siguiente = int(row["max_id"]) + 1
            if siguiente <= MAX_ID_NOTIFICACION_SO:
                return siguiente

            # Fallback de reutilización si alguna vez se alcanza el límite int32
            usados = {
                int(r["id_notificacion_so"])
                for r in conn.execute("SELECT id_notificacion_so FROM recordatorios").fetchall()
            }
            for candidato in range(1, MAX_ID_NOTIFICACION_SO + 1):
                if candidato not in usados:
                    return candidato
            raise RuntimeError("No hay identificadores int32 disponibles para notificaciones.")

    def eliminar(self, recordatorio_id: UUID) -> None:
        with self._db.transaccion() as conn:
            conn.execute("DELETE FROM recordatorios WHERE id = ?", (str(recordatorio_id),))

    @staticmethod
    def _fila_a_entidad(row: sqlite3.Row) -> Recordatorio:
        return Recordatorio(
            id=UUID(row["id"]),
            id_notificacion_so=int(row["id_notificacion_so"]),
            tipo_origen=TipoOrigenRecordatorio(row["tipo_origen"]),
            evento_id=UUID(row["evento_id"]) if row["evento_id"] else None,
            tarea_id=UUID(row["tarea_id"]) if row["tarea_id"] else None,
            antelacion_minutos=int(row["antelacion_minutos"]),
            fecha_disparo=_iso_a_dt(row["fecha_disparo"]),
            estado=EstadoRecordatorio(row["estado"]),
            created_at=_iso_a_dt(row["created_at"]),
            updated_at=_iso_a_dt(row["updated_at"]),
        )


class ProveedorContenidoSQLite:
    """Resuelve título y descripción de un Evento o Tarea directamente desde SQLite."""

    def __init__(self, db: SQLiteDatabase) -> None:
        self._db = db

    def obtener_contenido(
        self,
        tipo_origen: TipoOrigenRecordatorio,
        item_id: UUID,
    ) -> ContenidoNotificacion | None:
        tabla = "eventos" if tipo_origen == TipoOrigenRecordatorio.EVENTO else "tareas"
        with self._db.transaccion() as conn:
            row = conn.execute(
                f"SELECT titulo, descripcion FROM {tabla} WHERE id = ?",
                (str(item_id),),
            ).fetchone()
            if row is None:
                return None
            return ContenidoNotificacion(
                titulo=str(row["titulo"]),
                cuerpo=str(row["descripcion"] or ""),
            )

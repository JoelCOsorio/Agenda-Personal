"""Repositorio SQLite para Tareas y vínculos tarea_contacto (RN-07, RN-12, RN-13)."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from uuid import UUID

from agenda_app.domain.entities.base import asegurar_utc
from agenda_app.domain.entities.tarea import Tarea
from agenda_app.domain.enums import EstadoTarea, PrioridadTarea
from agenda_app.infrastructure.persistence.sqlite.database import SQLiteDatabase


def _dt_a_iso(dt: datetime) -> str:
    return asegurar_utc(dt).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _iso_a_dt(valor: str) -> datetime:
    return asegurar_utc(datetime.fromisoformat(valor.replace("Z", "+00:00")))


class RepositorioTareasSQLite:
    """Persistencia atómica de Tareas y sus contactos vinculados."""

    def __init__(self, db: SQLiteDatabase) -> None:
        self._db = db

    def guardar(self, tarea: Tarea) -> None:
        with self._db.transaccion() as conn:
            conn.execute(
                """
                INSERT INTO tareas (
                    id, titulo, descripcion, fecha_limite, prioridad, estado,
                    categoria_id, subcategoria_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    titulo          = excluded.titulo,
                    descripcion     = excluded.descripcion,
                    fecha_limite    = excluded.fecha_limite,
                    prioridad       = excluded.prioridad,
                    estado          = excluded.estado,
                    categoria_id    = excluded.categoria_id,
                    subcategoria_id = excluded.subcategoria_id,
                    updated_at      = excluded.updated_at
                """,
                (
                    str(tarea.id),
                    tarea.titulo,
                    tarea.descripcion,
                    _dt_a_iso(tarea.fecha_limite) if tarea.fecha_limite is not None else None,
                    tarea.prioridad.value,
                    tarea.estado.value,
                    str(tarea.categoria_id) if tarea.categoria_id else None,
                    str(tarea.subcategoria_id) if tarea.subcategoria_id else None,
                    _dt_a_iso(tarea.created_at),
                    _dt_a_iso(tarea.updated_at),
                ),
            )

            conn.execute("DELETE FROM tarea_contacto WHERE tarea_id = ?", (str(tarea.id),))
            now_iso = _dt_a_iso(tarea.updated_at)
            for cid in tarea.contacto_ids:
                conn.execute(
                    "INSERT INTO tarea_contacto (tarea_id, contacto_id, created_at) VALUES (?, ?, ?)",
                    (str(tarea.id), str(cid), now_iso),
                )

    def obtener_por_id(self, tarea_id: UUID) -> Tarea | None:
        with self._db.transaccion() as conn:
            row = conn.execute(
                "SELECT * FROM tareas WHERE id = ?",
                (str(tarea_id),),
            ).fetchone()
            return self._hidratar_tarea(conn, row) if row else None

    def listar(
        self,
        *,
        estado: EstadoTarea | None = None,
        prioridad: PrioridadTarea | None = None,
        categoria_id: UUID | None = None,
        subcategoria_id: UUID | None = None,
    ) -> list[Tarea]:
        condiciones: list[str] = []
        params: list[str] = []

        if estado is not None:
            condiciones.append("estado = ?")
            params.append(estado.value)
        if prioridad is not None:
            condiciones.append("prioridad = ?")
            params.append(prioridad.value)
        if categoria_id is not None:
            condiciones.append("categoria_id = ?")
            params.append(str(categoria_id))
        if subcategoria_id is not None:
            condiciones.append("subcategoria_id = ?")
            params.append(str(subcategoria_id))

        where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
        with self._db.transaccion() as conn:
            filas = conn.execute(
                f"""
                SELECT * FROM tareas
                {where}
                ORDER BY
                    CASE WHEN fecha_limite IS NULL THEN 1 ELSE 0 END ASC,
                    fecha_limite ASC,
                    created_at DESC
                """,
                params,
            ).fetchall()
            return [self._hidratar_tarea(conn, f) for f in filas]

    def eliminar(self, tarea_id: UUID) -> None:
        with self._db.transaccion() as conn:
            conn.execute("DELETE FROM tareas WHERE id = ?", (str(tarea_id),))

    def _hidratar_tarea(self, conn: sqlite3.Connection, row: sqlite3.Row) -> Tarea:
        tar_id = str(row["id"])
        contactos_rows = conn.execute(
            "SELECT contacto_id FROM tarea_contacto WHERE tarea_id = ? ORDER BY created_at ASC",
            (tar_id,),
        ).fetchall()
        contacto_ids = tuple(UUID(r["contacto_id"]) for r in contactos_rows)

        return Tarea(
            id=UUID(row["id"]),
            titulo=str(row["titulo"]),
            descripcion=row["descripcion"],
            fecha_limite=_iso_a_dt(row["fecha_limite"]) if row["fecha_limite"] else None,
            prioridad=PrioridadTarea(row["prioridad"]),
            estado=EstadoTarea(row["estado"]),
            categoria_id=UUID(row["categoria_id"]) if row["categoria_id"] else None,
            subcategoria_id=UUID(row["subcategoria_id"]) if row["subcategoria_id"] else None,
            contacto_ids=contacto_ids,
            created_at=_iso_a_dt(row["created_at"]),
            updated_at=_iso_a_dt(row["updated_at"]),
        )

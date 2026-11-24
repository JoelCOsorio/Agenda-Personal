"""Repositorio SQLite para Categorias y Subcategorias (RN-09, RN-13)."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from uuid import UUID

from agenda_app.domain.entities.base import asegurar_utc
from agenda_app.domain.entities.categoria import Categoria, Subcategoria
from agenda_app.infrastructure.persistence.sqlite.database import SQLiteDatabase


def _dt_a_iso(dt: datetime) -> str:
    return asegurar_utc(dt).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _iso_a_dt(valor: str) -> datetime:
    return asegurar_utc(datetime.fromisoformat(valor.replace("Z", "+00:00")))


class RepositorioCategoriasSQLite:
    """Persistencia SQLite de categorías (Nivel 1) y subcategorías (Nivel 2)."""

    def __init__(self, db: SQLiteDatabase) -> None:
        self._db = db

    def guardar_categoria(self, categoria: Categoria) -> None:
        with self._db.transaccion() as conn:
            conn.execute(
                """
                INSERT INTO categorias (id, nombre, color_hex, icono, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    nombre     = excluded.nombre,
                    color_hex  = excluded.color_hex,
                    icono      = excluded.icono,
                    updated_at = excluded.updated_at
                """,
                (
                    str(categoria.id),
                    categoria.nombre,
                    categoria.color_hex,
                    categoria.icono,
                    _dt_a_iso(categoria.created_at),
                    _dt_a_iso(categoria.updated_at),
                ),
            )

    def obtener_categoria(self, categoria_id: UUID) -> Categoria | None:
        with self._db.transaccion() as conn:
            row = conn.execute(
                "SELECT * FROM categorias WHERE id = ?",
                (str(categoria_id),),
            ).fetchone()
            return self._fila_a_categoria(row) if row else None

    def listar_categorias(self) -> list[Categoria]:
        with self._db.transaccion() as conn:
            filas = conn.execute(
                "SELECT * FROM categorias ORDER BY lower(nombre) ASC"
            ).fetchall()
            return [self._fila_a_categoria(f) for f in filas]

    def eliminar_categoria(self, categoria_id: UUID) -> None:
        with self._db.transaccion() as conn:
            conn.execute("DELETE FROM categorias WHERE id = ?", (str(categoria_id),))

    def guardar_subcategoria(self, subcategoria: Subcategoria) -> None:
        with self._db.transaccion() as conn:
            conn.execute(
                """
                INSERT INTO subcategorias (id, categoria_id, nombre, color_hex, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    categoria_id = excluded.categoria_id,
                    nombre       = excluded.nombre,
                    color_hex    = excluded.color_hex,
                    updated_at   = excluded.updated_at
                """,
                (
                    str(subcategoria.id),
                    str(subcategoria.categoria_id),
                    subcategoria.nombre,
                    subcategoria.color_hex,
                    _dt_a_iso(subcategoria.created_at),
                    _dt_a_iso(subcategoria.updated_at),
                ),
            )

    def obtener_subcategoria(self, subcategoria_id: UUID) -> Subcategoria | None:
        with self._db.transaccion() as conn:
            row = conn.execute(
                "SELECT * FROM subcategorias WHERE id = ?",
                (str(subcategoria_id),),
            ).fetchone()
            return self._fila_a_subcategoria(row) if row else None

    def listar_subcategorias(self, categoria_id: UUID | None = None) -> list[Subcategoria]:
        with self._db.transaccion() as conn:
            if categoria_id is not None:
                filas = conn.execute(
                    """
                    SELECT * FROM subcategorias
                    WHERE categoria_id = ?
                    ORDER BY lower(nombre) ASC
                    """,
                    (str(categoria_id),),
                ).fetchall()
            else:
                filas = conn.execute(
                    "SELECT * FROM subcategorias ORDER BY lower(nombre) ASC"
                ).fetchall()
            return [self._fila_a_subcategoria(f) for f in filas]

    def eliminar_subcategoria(self, subcategoria_id: UUID) -> None:
        with self._db.transaccion() as conn:
            conn.execute("DELETE FROM subcategorias WHERE id = ?", (str(subcategoria_id),))

    def subcategoria_pertenece_a(
        self, subcategoria_id: UUID, categoria_id: UUID
    ) -> bool:
        with self._db.transaccion() as conn:
            row = conn.execute(
                "SELECT 1 FROM subcategorias WHERE id = ? AND categoria_id = ?",
                (str(subcategoria_id), str(categoria_id)),
            ).fetchone()
            return row is not None

    @staticmethod
    def _fila_a_categoria(row: sqlite3.Row) -> Categoria:
        return Categoria(
            id=UUID(row["id"]),
            nombre=str(row["nombre"]),
            color_hex=str(row["color_hex"]),
            icono=row["icono"],
            created_at=_iso_a_dt(row["created_at"]),
            updated_at=_iso_a_dt(row["updated_at"]),
        )

    @staticmethod
    def _fila_a_subcategoria(row: sqlite3.Row) -> Subcategoria:
        return Subcategoria(
            id=UUID(row["id"]),
            categoria_id=UUID(row["categoria_id"]),
            nombre=str(row["nombre"]),
            color_hex=row["color_hex"],
            created_at=_iso_a_dt(row["created_at"]),
            updated_at=_iso_a_dt(row["updated_at"]),
        )

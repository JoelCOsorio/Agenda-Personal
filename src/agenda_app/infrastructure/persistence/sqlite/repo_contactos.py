"""Repositorio SQLite para Contactos (RF-17, RN-13)."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from agenda_app.domain.entities.base import asegurar_utc
from agenda_app.domain.entities.contacto import Contacto
from agenda_app.infrastructure.persistence.sqlite.database import SQLiteDatabase


def _dt_a_iso(dt: datetime) -> str:
    return asegurar_utc(dt).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _iso_a_dt(valor: str) -> datetime:
    return asegurar_utc(datetime.fromisoformat(valor.replace("Z", "+00:00")))


class RepositorioContactosSQLite:
    """Persistencia SQLite del directorio de contactos."""

    def __init__(self, db: SQLiteDatabase) -> None:
        self._db = db

    def guardar(self, contacto: Contacto) -> None:
        with self._db.transaccion() as conn:
            conn.execute(
                """
                INSERT INTO contactos (
                    id, nombre, telefono, correo, notas, etiqueta, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    nombre     = excluded.nombre,
                    telefono   = excluded.telefono,
                    correo     = excluded.correo,
                    notas      = excluded.notas,
                    etiqueta   = excluded.etiqueta,
                    updated_at = excluded.updated_at
                """,
                (
                    str(contacto.id),
                    contacto.nombre,
                    contacto.telefono,
                    contacto.correo,
                    contacto.notas,
                    contacto.etiqueta,
                    _dt_a_iso(contacto.created_at),
                    _dt_a_iso(contacto.updated_at),
                ),
            )

    def obtener_por_id(self, contacto_id: UUID) -> Contacto | None:
        with self._db.transaccion() as conn:
            row = conn.execute(
                "SELECT * FROM contactos WHERE id = ?",
                (str(contacto_id),),
            ).fetchone()
            return self._fila_a_entidad(row) if row else None

    def obtener_varios(self, ids: Sequence[UUID]) -> list[Contacto]:
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        with self._db.transaccion() as conn:
            filas = conn.execute(
                f"SELECT * FROM contactos WHERE id IN ({placeholders}) ORDER BY lower(nombre) ASC",
                [str(cid) for cid in ids],
            ).fetchall()
            return [self._fila_a_entidad(f) for f in filas]

    def buscar(
        self,
        termino: str | None = None,
        etiqueta: str | None = None,
    ) -> list[Contacto]:
        condiciones: list[str] = []
        params: list[str] = []

        if termino and termino.strip():
            patron = f"%{termino.strip().lower()}%"
            condiciones.append(
                "(lower(nombre) LIKE ? OR lower(COALESCE(correo, '')) LIKE ? "
                "OR lower(COALESCE(telefono, '')) LIKE ? OR lower(COALESCE(etiqueta, '')) LIKE ?)"
            )
            params.extend([patron, patron, patron, patron])

        if etiqueta and etiqueta.strip():
            condiciones.append("lower(COALESCE(etiqueta, '')) = ?")
            params.append(etiqueta.strip().lower())

        where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
        with self._db.transaccion() as conn:
            filas = conn.execute(
                f"SELECT * FROM contactos {where} ORDER BY lower(nombre) ASC",
                params,
            ).fetchall()
            return [self._fila_a_entidad(f) for f in filas]

    def eliminar(self, contacto_id: UUID) -> None:
        """Al borrar un contacto, ON DELETE CASCADE solo elimina vínculos en tablas puente (RN-13)."""
        with self._db.transaccion() as conn:
            conn.execute("DELETE FROM contactos WHERE id = ?", (str(contacto_id),))

    @staticmethod
    def _fila_a_entidad(row: sqlite3.Row) -> Contacto:
        return Contacto(
            id=UUID(row["id"]),
            nombre=str(row["nombre"]),
            telefono=row["telefono"],
            correo=row["correo"],
            notas=row["notas"],
            etiqueta=row["etiqueta"],
            created_at=_iso_a_dt(row["created_at"]),
            updated_at=_iso_a_dt(row["updated_at"]),
        )

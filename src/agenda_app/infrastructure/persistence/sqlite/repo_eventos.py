"""Repositorio SQLite para Eventos, ReglaRecurrencia y vínculos evento_contacto."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from uuid import UUID

from agenda_app.domain.entities.base import asegurar_utc
from agenda_app.domain.entities.evento import Evento, ReglaRecurrencia
from agenda_app.domain.enums import TipoFrecuencia
from agenda_app.infrastructure.persistence.sqlite.database import SQLiteDatabase


def _dt_a_iso(dt: datetime) -> str:
    return asegurar_utc(dt).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _iso_a_dt(valor: str) -> datetime:
    return asegurar_utc(datetime.fromisoformat(valor.replace("Z", "+00:00")))


class RepositorioEventosSQLite:
    """Persiste el agregado Evento de forma atómica (evento + recurrencia + contactos)."""

    def __init__(self, db: SQLiteDatabase) -> None:
        self._db = db

    def guardar(self, evento: Evento) -> None:
        with self._db.transaccion() as conn:
            conn.execute(
                """
                INSERT INTO eventos (
                    id, titulo, descripcion, fecha_inicio, fecha_fin, todo_el_dia,
                    ubicacion, color_hex, categoria_id, subcategoria_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    titulo          = excluded.titulo,
                    descripcion     = excluded.descripcion,
                    fecha_inicio    = excluded.fecha_inicio,
                    fecha_fin       = excluded.fecha_fin,
                    todo_el_dia     = excluded.todo_el_dia,
                    ubicacion       = excluded.ubicacion,
                    color_hex       = excluded.color_hex,
                    categoria_id    = excluded.categoria_id,
                    subcategoria_id = excluded.subcategoria_id,
                    updated_at      = excluded.updated_at
                """,
                (
                    str(evento.id),
                    evento.titulo,
                    evento.descripcion,
                    _dt_a_iso(evento.fecha_inicio),
                    _dt_a_iso(evento.fecha_fin) if evento.fecha_fin is not None else None,
                    int(evento.todo_el_dia),
                    evento.ubicacion,
                    evento.color_hex,
                    str(evento.categoria_id) if evento.categoria_id else None,
                    str(evento.subcategoria_id) if evento.subcategoria_id else None,
                    _dt_a_iso(evento.created_at),
                    _dt_a_iso(evento.updated_at),
                ),
            )

            # Sincronizar ReglaRecurrencia (0..1)
            conn.execute("DELETE FROM reglas_recurrencia WHERE evento_id = ?", (str(evento.id),))
            if evento.recurrencia is not None:
                regla = evento.recurrencia
                conn.execute(
                    """
                    INSERT INTO reglas_recurrencia (
                        id, evento_id, frecuencia, intervalo, dias_semana,
                        fecha_fin_recurrencia, max_ocurrencias, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(regla.id),
                        str(evento.id),
                        regla.frecuencia.value,
                        regla.intervalo,
                        regla.dias_como_texto(),
                        regla.fecha_fin_recurrencia.isoformat()
                        if regla.fecha_fin_recurrencia is not None
                        else None,
                        regla.max_ocurrencias,
                        _dt_a_iso(regla.created_at),
                        _dt_a_iso(regla.updated_at),
                    ),
                )

            # Sincronizar vínculos N:M con contactos
            conn.execute("DELETE FROM evento_contacto WHERE evento_id = ?", (str(evento.id),))
            now_iso = _dt_a_iso(evento.updated_at)
            for cid in evento.contacto_ids:
                conn.execute(
                    "INSERT INTO evento_contacto (evento_id, contacto_id, created_at) VALUES (?, ?, ?)",
                    (str(evento.id), str(cid), now_iso),
                )

    def obtener_por_id(self, evento_id: UUID) -> Evento | None:
        with self._db.transaccion() as conn:
            row = conn.execute(
                "SELECT * FROM eventos WHERE id = ?",
                (str(evento_id),),
            ).fetchone()
            return self._hidratar_evento(conn, row) if row else None

    def listar_candidatos_solapamiento(
        self,
        desde: datetime,
        hasta: datetime,
    ) -> list[Evento]:
        """Devuelve eventos con franja horaria en el rango + todos los eventos recurrentes no todo_el_dia."""
        desde_iso = _dt_a_iso(desde)
        hasta_iso = _dt_a_iso(hasta)
        with self._db.transaccion() as conn:
            filas = conn.execute(
                """
                SELECT DISTINCT e.*
                FROM eventos e
                LEFT JOIN reglas_recurrencia r ON r.evento_id = e.id
                WHERE e.todo_el_dia = 0
                  AND (
                      r.id IS NOT NULL
                      OR (
                          e.fecha_inicio <= ?
                          AND COALESCE(e.fecha_fin, e.fecha_inicio) >= ?
                      )
                  )
                ORDER BY e.fecha_inicio ASC
                """,
                (hasta_iso, desde_iso),
            ).fetchall()
            return [self._hidratar_evento(conn, f) for f in filas]

    def listar_en_rango(
        self,
        desde: datetime,
        hasta: datetime,
        *,
        categoria_id: UUID | None = None,
        subcategoria_id: UUID | None = None,
    ) -> list[Evento]:
        desde_iso = _dt_a_iso(desde)
        hasta_iso = _dt_a_iso(hasta)
        condiciones = [
            "(r.id IS NOT NULL AND e.fecha_inicio <= ?) "
            "OR (r.id IS NULL AND e.fecha_inicio <= ? AND COALESCE(e.fecha_fin, e.fecha_inicio) >= ?)"
        ]
        params: list[str] = [hasta_iso, hasta_iso, desde_iso]

        if categoria_id is not None:
            condiciones.append("e.categoria_id = ?")
            params.append(str(categoria_id))
        if subcategoria_id is not None:
            condiciones.append("e.subcategoria_id = ?")
            params.append(str(subcategoria_id))

        where = " AND ".join(f"({c})" for c in condiciones)
        with self._db.transaccion() as conn:
            filas = conn.execute(
                f"""
                SELECT DISTINCT e.*
                FROM eventos e
                LEFT JOIN reglas_recurrencia r ON r.evento_id = e.id
                WHERE {where}
                ORDER BY e.fecha_inicio ASC
                """,
                params,
            ).fetchall()
            return [self._hidratar_evento(conn, f) for f in filas]

    def listar_historial(self, antes_de: datetime) -> list[Evento]:
        corte_iso = _dt_a_iso(antes_de)
        with self._db.transaccion() as conn:
            filas = conn.execute(
                """
                SELECT * FROM eventos
                WHERE COALESCE(fecha_fin, fecha_inicio) < ?
                ORDER BY fecha_inicio DESC
                """,
                (corte_iso,),
            ).fetchall()
            return [self._hidratar_evento(conn, f) for f in filas]

    def listar_recurrentes(self) -> list[Evento]:
        with self._db.transaccion() as conn:
            filas = conn.execute(
                """
                SELECT e.*
                FROM eventos e
                INNER JOIN reglas_recurrencia r ON r.evento_id = e.id
                ORDER BY e.fecha_inicio ASC
                """
            ).fetchall()
            return [self._hidratar_evento(conn, f) for f in filas]

    def eliminar(self, evento_id: UUID) -> None:
        with self._db.transaccion() as conn:
            conn.execute("DELETE FROM eventos WHERE id = ?", (str(evento_id),))

    def _hidratar_evento(self, conn: sqlite3.Connection, row: sqlite3.Row) -> Evento:
        ev_id = str(row["id"])
        regla_row = conn.execute(
            "SELECT * FROM reglas_recurrencia WHERE evento_id = ?",
            (ev_id,),
        ).fetchone()
        recurrencia = (
            ReglaRecurrencia(
                id=UUID(regla_row["id"]),
                evento_id=UUID(regla_row["evento_id"]),
                frecuencia=TipoFrecuencia(regla_row["frecuencia"]),
                intervalo=int(regla_row["intervalo"]),
                dias_semana=ReglaRecurrencia.parsear_dias_texto(regla_row["dias_semana"]),
                fecha_fin_recurrencia=(
                    date.fromisoformat(regla_row["fecha_fin_recurrencia"])
                    if regla_row["fecha_fin_recurrencia"]
                    else None
                ),
                max_ocurrencias=(
                    int(regla_row["max_ocurrencias"])
                    if regla_row["max_ocurrencias"] is not None
                    else None
                ),
                created_at=_iso_a_dt(regla_row["created_at"]),
                updated_at=_iso_a_dt(regla_row["updated_at"]),
            )
            if regla_row is not None
            else None
        )

        contactos_rows = conn.execute(
            "SELECT contacto_id FROM evento_contacto WHERE evento_id = ? ORDER BY created_at ASC",
            (ev_id,),
        ).fetchall()
        contacto_ids = tuple(UUID(r["contacto_id"]) for r in contactos_rows)

        return Evento(
            id=UUID(row["id"]),
            titulo=str(row["titulo"]),
            descripcion=row["descripcion"],
            fecha_inicio=_iso_a_dt(row["fecha_inicio"]),
            fecha_fin=_iso_a_dt(row["fecha_fin"]) if row["fecha_fin"] else None,
            todo_el_dia=bool(row["todo_el_dia"]),
            ubicacion=row["ubicacion"],
            color_hex=row["color_hex"],
            categoria_id=UUID(row["categoria_id"]) if row["categoria_id"] else None,
            subcategoria_id=UUID(row["subcategoria_id"]) if row["subcategoria_id"] else None,
            contacto_ids=contacto_ids,
            recurrencia=recurrencia,
            created_at=_iso_a_dt(row["created_at"]),
            updated_at=_iso_a_dt(row["updated_at"]),
        )

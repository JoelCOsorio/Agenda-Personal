"""Ejecutor idempotente y versionado de migraciones SQL para SQLite."""

from __future__ import annotations

import re
from pathlib import Path

from agenda_app.infrastructure.persistence.sqlite.database import SQLiteDatabase

SQL_DIR = Path(__file__).parent / "sql"
_PATRON_MIGRACION = re.compile(r"^(\d+)_.*\.sql$")


def aplicar_migraciones(db: SQLiteDatabase, directorio_sql: Path = SQL_DIR) -> list[int]:
    """Aplica en orden los archivos SQL pendientes y registra su versión en schema_migrations."""
    aplicadas: list[int] = []
    archivos: list[tuple[int, Path]] = []

    for ruta in sorted(directorio_sql.glob("*.sql")):
        match = _PATRON_MIGRACION.match(ruta.name)
        if match:
            archivos.append((int(match.group(1)), ruta))

    conn = db.abrir_conexion()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version     INTEGER PRIMARY KEY,
                name        TEXT    NOT NULL,
                applied_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );
            """
        )
        existentes = {
            row["version"]
            for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }

        for version, ruta_sql in sorted(archivos, key=lambda x: x[0]):
            if version in existentes:
                continue
            script = ruta_sql.read_text(encoding="utf-8")
            conn.executescript(script)
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (?, ?)",
                (version, ruta_sql.stem),
            )
            conn.commit()
            aplicadas.append(version)
    finally:
        if db.db_path != ":memory:":
            conn.close()

    return aplicadas

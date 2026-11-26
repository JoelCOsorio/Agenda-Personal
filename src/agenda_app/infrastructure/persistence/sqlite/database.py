"""Gestor de conexiones SQLite 3 con FK estrictas y modo WAL."""

from __future__ import annotations

import sqlite3
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class SQLiteDatabase:
    """Administra conexiones seguras a SQLite 3 (soporta archivos locales, :memory: y WASM)."""

    def __init__(self, db_path: Path | str) -> None:
        self._db_path = str(db_path)
        self._es_memoria = self._db_path == ":memory:"
        self._conn_memoria: sqlite3.Connection | None = None

    @property
    def db_path(self) -> str:
        return self._db_path

    def _configurar_conexion(self, conn: sqlite3.Connection) -> sqlite3.Connection:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        if not self._es_memoria:
            if sys.platform == "emscripten":
                conn.execute("PRAGMA journal_mode = MEMORY;")
            else:
                try:
                    conn.execute("PRAGMA journal_mode = WAL;")
                except sqlite3.OperationalError:
                    conn.execute("PRAGMA journal_mode = DELETE;")
            conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def abrir_conexion(self) -> sqlite3.Connection:
        if self._es_memoria:
            if self._conn_memoria is None:
                self._conn_memoria = self._configurar_conexion(
                    sqlite3.connect(":memory:", check_same_thread=False)
                )
            return self._conn_memoria
        return self._configurar_conexion(
            sqlite3.connect(self._db_path, timeout=5.0, check_same_thread=False)
        )

    @contextmanager
    def transaccion(self) -> Iterator[sqlite3.Connection]:
        """Abre una transacción atómica con commit/rollback automático."""
        conn = self.abrir_conexion()
        try:
            with conn:
                yield conn
        finally:
            if not self._es_memoria:
                conn.close()

    def cerrar(self) -> None:
        if self._conn_memoria is not None:
            self._conn_memoria.close()
            self._conn_memoria = None

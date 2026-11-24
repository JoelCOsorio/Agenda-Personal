"""Repositorio SQLite del singleton ConfiguracionSistema (RN-14, RF-23, RF-24)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from agenda_app.domain.entities.base import asegurar_utc
from agenda_app.domain.entities.configuracion import ConfiguracionSistema
from agenda_app.domain.enums import VistaAgenda
from agenda_app.infrastructure.persistence.sqlite.database import SQLiteDatabase


def _dt_a_iso(dt: datetime) -> str:
    return asegurar_utc(dt).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _iso_a_dt(valor: str) -> datetime:
    return asegurar_utc(datetime.fromisoformat(valor.replace("Z", "+00:00")))


class RepositorioAjustesSQLite:
    """Persistencia SQLite para la fila singleton de configuracion_sistema."""

    def __init__(self, db: SQLiteDatabase) -> None:
        self._db = db

    def obtener(self) -> ConfiguracionSistema:
        with self._db.transaccion() as conn:
            row = conn.execute(
                "SELECT * FROM configuracion_sistema WHERE singleton_key = 1"
            ).fetchone()
            if row is None:
                ahora = datetime.now(timezone.utc)
                defecto = ConfiguracionSistema(created_at=ahora, updated_at=ahora)
                self.guardar(defecto)
                return defecto

            return ConfiguracionSistema(
                id=UUID(row["id"]),
                minutos_posponer_defecto=int(row["minutos_posponer_defecto"]),
                antelacion_recordatorio_defecto_min=int(
                    row["antelacion_recordatorio_defecto_min"]
                ),
                sonido_notificaciones=bool(row["sonido_notificaciones"]),
                mostrar_alertas_perdidas_inicio=bool(
                    row["mostrar_alertas_perdidas_inicio"]
                ),
                formato_24h=bool(row["formato_24h"]),
                primer_dia_semana=int(row["primer_dia_semana"]),
                vista_inicial_agenda=VistaAgenda(row["vista_inicial_agenda"]),
                tema_oscuro=bool(row["tema_oscuro"]),
                created_at=_iso_a_dt(row["created_at"]),
                updated_at=_iso_a_dt(row["updated_at"]),
            )

    def guardar(self, configuracion: ConfiguracionSistema) -> None:
        with self._db.transaccion() as conn:
            conn.execute(
                """
                INSERT INTO configuracion_sistema (
                    singleton_key, id, minutos_posponer_defecto,
                    antelacion_recordatorio_defecto_min, sonido_notificaciones,
                    mostrar_alertas_perdidas_inicio, formato_24h, primer_dia_semana,
                    vista_inicial_agenda, tema_oscuro, created_at, updated_at
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(singleton_key) DO UPDATE SET
                    minutos_posponer_defecto            = excluded.minutos_posponer_defecto,
                    antelacion_recordatorio_defecto_min = excluded.antelacion_recordatorio_defecto_min,
                    sonido_notificaciones               = excluded.sonido_notificaciones,
                    mostrar_alertas_perdidas_inicio     = excluded.mostrar_alertas_perdidas_inicio,
                    formato_24h                         = excluded.formato_24h,
                    primer_dia_semana                   = excluded.primer_dia_semana,
                    vista_inicial_agenda                = excluded.vista_inicial_agenda,
                    tema_oscuro                         = excluded.tema_oscuro,
                    updated_at                          = excluded.updated_at
                """,
                (
                    str(configuracion.id),
                    configuracion.minutos_posponer_defecto,
                    configuracion.antelacion_recordatorio_defecto_min,
                    int(configuracion.sonido_notificaciones),
                    int(configuracion.mostrar_alertas_perdidas_inicio),
                    int(configuracion.formato_24h),
                    configuracion.primer_dia_semana,
                    configuracion.vista_inicial_agenda.value,
                    int(configuracion.tema_oscuro),
                    _dt_a_iso(configuracion.created_at),
                    _dt_a_iso(configuracion.updated_at),
                ),
            )

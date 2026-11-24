"""Servicio de aplicación para Configuración / Ajustes (PROC-06, RF-23, RF-24, RN-14)."""

from __future__ import annotations

from agenda_app.application.ports.reloj import IReloj
from agenda_app.application.ports.repositorios import IRepositorioAjustes
from agenda_app.domain.entities.configuracion import ConfiguracionSistema
from agenda_app.domain.enums import VistaAgenda


class ServicioAjustes:
    """Centraliza lectura, actualización validada y restauración de ConfiguracionSistema."""

    def __init__(
        self,
        repo_ajustes: IRepositorioAjustes,
        reloj: IReloj,
    ) -> None:
        self._repo = repo_ajustes
        self._reloj = reloj

    def obtener(self) -> ConfiguracionSistema:
        return self._repo.obtener()

    def actualizar(
        self,
        *,
        minutos_posponer_defecto: int | None = None,
        antelacion_recordatorio_defecto_min: int | None = None,
        sonido_notificaciones: bool | None = None,
        mostrar_alertas_perdidas_inicio: bool | None = None,
        formato_24h: bool | None = None,
        primer_dia_semana: int | None = None,
        vista_inicial_agenda: VistaAgenda | None = None,
        tema_oscuro: bool | None = None,
    ) -> ConfiguracionSistema:
        actual = self._repo.obtener()
        nueva = ConfiguracionSistema(
            id=actual.id,
            minutos_posponer_defecto=(
                actual.minutos_posponer_defecto
                if minutos_posponer_defecto is None
                else minutos_posponer_defecto
            ),
            antelacion_recordatorio_defecto_min=(
                actual.antelacion_recordatorio_defecto_min
                if antelacion_recordatorio_defecto_min is None
                else antelacion_recordatorio_defecto_min
            ),
            sonido_notificaciones=(
                actual.sonido_notificaciones
                if sonido_notificaciones is None
                else sonido_notificaciones
            ),
            mostrar_alertas_perdidas_inicio=(
                actual.mostrar_alertas_perdidas_inicio
                if mostrar_alertas_perdidas_inicio is None
                else mostrar_alertas_perdidas_inicio
            ),
            formato_24h=actual.formato_24h if formato_24h is None else formato_24h,
            primer_dia_semana=(
                actual.primer_dia_semana
                if primer_dia_semana is None
                else primer_dia_semana
            ),
            vista_inicial_agenda=(
                actual.vista_inicial_agenda
                if vista_inicial_agenda is None
                else vista_inicial_agenda
            ),
            tema_oscuro=actual.tema_oscuro if tema_oscuro is None else tema_oscuro,
            created_at=actual.created_at,
            updated_at=self._reloj.ahora_utc(),
        )
        self._repo.guardar(nueva)
        return nueva

    def restablecer_defaults(self) -> ConfiguracionSistema:
        actual = self._repo.obtener()
        actual.restablecer_valores_defecto(self._reloj.ahora_utc())
        self._repo.guardar(actual)
        return actual

"""Reconciliador de arranque y detección de notificaciones perdidas (RN-05)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from agenda_app.application.ports.notificaciones import IAdaptadorNotificaciones
from agenda_app.application.ports.reloj import IReloj
from agenda_app.application.ports.repositorios import (
    IRepositorioAjustes,
    IRepositorioRecordatorios,
)
from agenda_app.application.services.motor_notificaciones import MotorNotificaciones
from agenda_app.domain.entities.recordatorio import Recordatorio

VENTANA_RECONCILIACION_DIAS = 30
TOPE_ALARMAS_ACTIVAS_SO = 200


@dataclass(frozen=True)
class ResultadoReconciliacion:
    """Resumen devuelto a la capa de presentación tras arrancar o reanudar la app."""

    perdidos_detectados: tuple[Recordatorio, ...]
    total_perdidos_sin_atender: tuple[Recordatorio, ...]
    reprogramados_en_so: int
    alarmas_exactas_disponibles: bool
    mostrar_aviso_perdidos: bool


class StartupReconciler:
    """Protocolo idempotente ejecutado al iniciar la app y en AppLifecycleState.RESUME."""

    def __init__(
        self,
        repo_recordatorios: IRepositorioRecordatorios,
        repo_ajustes: IRepositorioAjustes,
        motor: MotorNotificaciones,
        adaptador: IAdaptadorNotificaciones,
        reloj: IReloj,
        ventana_dias: int = VENTANA_RECONCILIACION_DIAS,
        tope_alarmas: int = TOPE_ALARMAS_ACTIVAS_SO,
    ) -> None:
        self._repo_recordatorios = repo_recordatorios
        self._repo_ajustes = repo_ajustes
        self._motor = motor
        self._adaptador = adaptador
        self._reloj = reloj
        self._ventana_dias = ventana_dias
        self._tope_alarmas = tope_alarmas

    async def reconciliar(self) -> ResultadoReconciliacion:
        """Detecta alertas perdidas (RN-05) y re-sincroniza pendientes futuros con el SO."""
        ahora = self._reloj.ahora_utc()
        ajustes = self._repo_ajustes.obtener()

        # 1. Verificar disponibilidad de alarmas exactas (relevante tras revocación en Android)
        exactas_ok = await self._adaptador.puede_programar_exacto()

        # 2. Detectar recordatorios vencidos que no llegaron a dispararse (RN-05)
        vencidos = self._repo_recordatorios.obtener_pendientes_vencidos(ahora)
        for rec in vencidos:
            rec.marcar_perdido(ahora)
            self._repo_recordatorios.guardar(rec)

        todos_perdidos = self._repo_recordatorios.obtener_perdidos()

        # 3. Reconciliar pendientes futuros dentro de la ventana móvil (protege cuotas OEM)
        limite_hasta = ahora + timedelta(days=self._ventana_dias)
        futuros = self._repo_recordatorios.obtener_pendientes_futuros(
            ahora=ahora,
            hasta=limite_hasta,
            limite=self._tope_alarmas,
        )
        reprogramados = 0
        for rec in futuros:
            await self._motor.reprogramar_en_so_si_activo(rec)
            reprogramados += 1

        return ResultadoReconciliacion(
            perdidos_detectados=tuple(vencidos),
            total_perdidos_sin_atender=tuple(todos_perdidos),
            reprogramados_en_so=reprogramados,
            alarmas_exactas_disponibles=exactas_ok,
            mostrar_aviso_perdidos=ajustes.mostrar_alertas_perdidas_inicio
            and len(todos_perdidos) > 0,
        )

"""Reconciliador de arranque, detección de notificaciones perdidas y avance de recurrencias."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from agenda_app.application.ports.notificaciones import IAdaptadorNotificaciones
from agenda_app.application.ports.reloj import IReloj
from agenda_app.application.ports.repositorios import (
    IRepositorioAjustes,
    IRepositorioEventos,
    IRepositorioRecordatorios,
)
from agenda_app.application.services.motor_notificaciones import MotorNotificaciones
from agenda_app.domain.entities.evento import Evento
from agenda_app.domain.entities.recordatorio import Recordatorio
from agenda_app.domain.enums import EstadoRecordatorio, TipoOrigenRecordatorio
from agenda_app.domain.exceptions import RecordatorioInvalidoError
from agenda_app.domain.rules.recordatorio_rules import ValidadorRecordatorio
from agenda_app.domain.rules.recurrencia import ExpansorRecurrencia

VENTANA_RECONCILIACION_DIAS = 30
TOPE_ALARMAS_ACTIVAS_SO = 200
HORIZONTE_AVANCE_RECURRENCIA_DIAS = 366


@dataclass(frozen=True)
class ResultadoReconciliacion:
    """Resumen devuelto a la capa de presentación tras arrancar o reanudar la app."""

    perdidos_detectados: tuple[Recordatorio, ...]
    total_perdidos_sin_atender: tuple[Recordatorio, ...]
    reprogramados_en_so: int
    alarmas_exactas_disponibles: bool
    mostrar_aviso_perdidos: bool
    recurrencias_avanzadas: int = 0


class StartupReconciler:
    """Protocolo idempotente ejecutado al iniciar la app y en AppLifecycleState.RESUME."""

    def __init__(
        self,
        repo_recordatorios: IRepositorioRecordatorios,
        repo_ajustes: IRepositorioAjustes,
        motor: MotorNotificaciones,
        adaptador: IAdaptadorNotificaciones,
        reloj: IReloj,
        repo_eventos: IRepositorioEventos | None = None,
        ventana_dias: int = VENTANA_RECONCILIACION_DIAS,
        tope_alarmas: int = TOPE_ALARMAS_ACTIVAS_SO,
    ) -> None:
        self._repo_recordatorios = repo_recordatorios
        self._repo_ajustes = repo_ajustes
        self._repo_eventos = repo_eventos
        self._motor = motor
        self._adaptador = adaptador
        self._reloj = reloj
        self._ventana_dias = ventana_dias
        self._tope_alarmas = tope_alarmas

    async def reconciliar(self) -> ResultadoReconciliacion:
        """Detecta perdidas, avanza recordatorios de eventos recurrentes y reconcilia futuros."""
        ahora = self._reloj.ahora_utc()
        ajustes = self._repo_ajustes.obtener()

        # 1. Verificar disponibilidad de alarmas exactas (relevante tras revocación en Android)
        exactas_ok = await self._adaptador.puede_programar_exacto()

        # 2. Detectar recordatorios vencidos que no llegaron a dispararse (RN-05)
        vencidos = self._repo_recordatorios.obtener_pendientes_vencidos(ahora)
        for rec in vencidos:
            rec.marcar_perdido(ahora)
            self._repo_recordatorios.guardar(rec)

        # 3. Avanzar recordatorios de eventos recurrentes cuya alerta anterior ya fue entregada/atendida
        recurrencias_avanzadas = await self._avanzar_recordatorios_recurrentes(ahora)

        todos_perdidos = self._repo_recordatorios.obtener_perdidos()

        # 4. Reconciliar pendientes futuros dentro de la ventana móvil (protege cuotas OEM)
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
            recurrencias_avanzadas=recurrencias_avanzadas,
        )

    async def _avanzar_recordatorios_recurrentes(self, ahora: datetime) -> int:
        if self._repo_eventos is None:
            return 0

        avanzados = 0
        for evento in self._repo_eventos.listar_recurrentes():
            rec = self._repo_recordatorios.obtener_por_item(
                TipoOrigenRecordatorio.EVENTO, evento.id
            )
            if rec is None or rec.estado not in {
                EstadoRecordatorio.ENTREGADO,
                EstadoRecordatorio.ATENDIDO,
            }:
                continue

            objetivo = self._buscar_siguiente_objetivo_valido(
                evento=evento,
                antelacion_minutos=rec.antelacion_minutos,
                ahora=ahora,
            )
            if objetivo is None:
                continue

            await self._motor.programar_o_reprogramar(
                tipo_origen=TipoOrigenRecordatorio.EVENTO,
                item_id=evento.id,
                titulo=evento.titulo,
                cuerpo=evento.descripcion or evento.ubicacion or "Evento programado",
                fecha_objetivo=objetivo,
                antelacion_minutos=rec.antelacion_minutos,
            )
            avanzados += 1
        return avanzados

    @staticmethod
    def _buscar_siguiente_objetivo_valido(
        *,
        evento: Evento,
        antelacion_minutos: int,
        ahora: datetime,
    ) -> datetime | None:
        hasta = ahora + timedelta(days=HORIZONTE_AVANCE_RECURRENCIA_DIAS)
        ocurrencias = ExpansorRecurrencia.expandir_en_rango(evento, ahora, hasta)
        for oc in ocurrencias:
            try:
                ValidadorRecordatorio.calcular_y_validar_disparo(
                    fecha_objetivo=oc.inicio,
                    antelacion_minutos=antelacion_minutos,
                    ahora=ahora,
                )
                return oc.inicio
            except RecordatorioInvalidoError:
                continue
        return None

"""Servicio de aplicación para el Módulo de Agenda / Eventos (PROC-01, PROC-02)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from uuid import UUID

from agenda_app.application.ports.reloj import IReloj
from agenda_app.application.ports.repositorios import (
    IRepositorioCategorias,
    IRepositorioEventos,
    IRepositorioRecordatorios,
)
from agenda_app.application.services.motor_notificaciones import MotorNotificaciones
from agenda_app.domain.entities.evento import Evento, ReglaRecurrencia
from agenda_app.domain.enums import TipoOrigenRecordatorio
from agenda_app.domain.exceptions import (
    ChoqueEventosError,
    EntidadNoEncontradaError,
    JerarquiaCategoriaInvalidaError,
    RecordatorioInvalidoError,
)
from agenda_app.domain.rules.recordatorio_rules import ValidadorRecordatorio
from agenda_app.domain.rules.recurrencia import ExpansorRecurrencia, OcurrenciaEvento
from agenda_app.domain.rules.solapamiento import DetectorSolapamiento


class ServicioEventos:
    """Orquesta CRUD de eventos, validación anti-solapamiento (RN-11) y notificaciones."""

    def __init__(
        self,
        repo_eventos: IRepositorioEventos,
        repo_categorias: IRepositorioCategorias,
        motor_notificaciones: MotorNotificaciones,
        reloj: IReloj,
        repo_recordatorios: IRepositorioRecordatorios | None = None,
    ) -> None:
        self._repo = repo_eventos
        self._repo_categorias = repo_categorias
        self._repo_recordatorios = repo_recordatorios
        self._motor = motor_notificaciones
        self._reloj = reloj

    async def crear_evento(
        self,
        *,
        titulo: str,
        fecha_inicio: datetime,
        fecha_fin: datetime | None = None,
        todo_el_dia: bool = False,
        descripcion: str | None = None,
        ubicacion: str | None = None,
        color_hex: str | None = None,
        categoria_id: UUID | None = None,
        subcategoria_id: UUID | None = None,
        contacto_ids: Sequence[UUID] = (),
        recurrencia: ReglaRecurrencia | None = None,
        recordatorio_antelacion_min: int | None = None,
    ) -> Evento:
        ahora = self._reloj.ahora_utc()
        self._validar_jerarquia(categoria_id, subcategoria_id)

        evento = Evento(
            titulo=titulo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            todo_el_dia=todo_el_dia,
            descripcion=descripcion,
            ubicacion=ubicacion,
            color_hex=color_hex,
            categoria_id=categoria_id,
            subcategoria_id=subcategoria_id,
            contacto_ids=tuple(contacto_ids),
            recurrencia=recurrencia,
            created_at=ahora,
            updated_at=ahora,
        )

        # RN-11: validación estricta contra solapamientos antes de persistir
        self._validar_sin_choque(evento)

        # RN-03: pre-validar recordatorio antes de persistir para mantener atomicidad
        objetivo_notif = self._resolver_objetivo_notificacion(evento, ahora)
        if recordatorio_antelacion_min is not None and objetivo_notif is not None:
            ValidadorRecordatorio.calcular_y_validar_disparo(
                fecha_objetivo=objetivo_notif,
                antelacion_minutos=recordatorio_antelacion_min,
                ahora=ahora,
            )

        self._repo.guardar(evento)

        if recordatorio_antelacion_min is not None and objetivo_notif is not None:
            await self._motor.programar_o_reprogramar(
                tipo_origen=TipoOrigenRecordatorio.EVENTO,
                item_id=evento.id,
                titulo=evento.titulo,
                cuerpo=evento.descripcion or evento.ubicacion or "Evento programado",
                fecha_objetivo=objetivo_notif,
                antelacion_minutos=recordatorio_antelacion_min,
            )
        return evento

    async def editar_evento(
        self,
        evento_id: UUID,
        *,
        titulo: str | None = None,
        fecha_inicio: datetime | None = None,
        fecha_fin: datetime | None = None,
        actualizar_fecha_fin: bool = False,
        todo_el_dia: bool | None = None,
        descripcion: str | None = None,
        ubicacion: str | None = None,
        color_hex: str | None = None,
        categoria_id: UUID | None = None,
        subcategoria_id: UUID | None = None,
        actualizar_clasificacion: bool = False,
        contacto_ids: Sequence[UUID] | None = None,
        recurrencia: ReglaRecurrencia | None = None,
        actualizar_recurrencia: bool = False,
        recordatorio_antelacion_min: int | None = None,
        eliminar_recordatorio: bool = False,
    ) -> Evento:
        actual = self._repo.obtener_por_id(evento_id)
        if actual is None:
            raise EntidadNoEncontradaError(f"Evento {evento_id} no encontrado.")

        ahora = self._reloj.ahora_utc()
        cat_final = categoria_id if actualizar_clasificacion else actual.categoria_id
        sub_final = subcategoria_id if actualizar_clasificacion else actual.subcategoria_id
        self._validar_jerarquia(cat_final, sub_final)

        regla_final = recurrencia if actualizar_recurrencia else actual.recurrencia
        if regla_final is not None:
            regla_final.evento_id = actual.id

        editado = Evento(
            id=actual.id,
            titulo=actual.titulo if titulo is None else titulo,
            fecha_inicio=actual.fecha_inicio if fecha_inicio is None else fecha_inicio,
            fecha_fin=fecha_fin if actualizar_fecha_fin else actual.fecha_fin,
            todo_el_dia=actual.todo_el_dia if todo_el_dia is None else todo_el_dia,
            descripcion=actual.descripcion if descripcion is None else descripcion,
            ubicacion=actual.ubicacion if ubicacion is None else ubicacion,
            color_hex=actual.color_hex if color_hex is None else color_hex,
            categoria_id=cat_final,
            subcategoria_id=sub_final,
            contacto_ids=(
                actual.contacto_ids if contacto_ids is None else tuple(contacto_ids)
            ),
            recurrencia=regla_final,
            created_at=actual.created_at,
            updated_at=ahora,
        )

        self._validar_sin_choque(editado)

        objetivo_notif = self._resolver_objetivo_notificacion(editado, ahora)
        if (
            not eliminar_recordatorio
            and recordatorio_antelacion_min is not None
            and objetivo_notif is not None
        ):
            ValidadorRecordatorio.calcular_y_validar_disparo(
                fecha_objetivo=objetivo_notif,
                antelacion_minutos=recordatorio_antelacion_min,
                ahora=ahora,
            )

        self._repo.guardar(editado)

        if eliminar_recordatorio:
            await self._motor.cancelar_por_item(TipoOrigenRecordatorio.EVENTO, editado.id)
        elif recordatorio_antelacion_min is not None and objetivo_notif is not None:
            await self._motor.programar_o_reprogramar(
                tipo_origen=TipoOrigenRecordatorio.EVENTO,
                item_id=editado.id,
                titulo=editado.titulo,
                cuerpo=editado.descripcion or editado.ubicacion or "Evento programado",
                fecha_objetivo=objetivo_notif,
                antelacion_minutos=recordatorio_antelacion_min,
            )
        elif (
            (fecha_inicio is not None or actualizar_recurrencia)
            and self._repo_recordatorios is not None
            and objetivo_notif is not None
        ):
            rec_previo = self._repo_recordatorios.obtener_por_item(
                TipoOrigenRecordatorio.EVENTO, editado.id
            )
            if rec_previo is not None and rec_previo.esta_activo:
                try:
                    await self._motor.programar_o_reprogramar(
                        tipo_origen=TipoOrigenRecordatorio.EVENTO,
                        item_id=editado.id,
                        titulo=editado.titulo,
                        cuerpo=editado.descripcion or editado.ubicacion or "Evento programado",
                        fecha_objetivo=objetivo_notif,
                        antelacion_minutos=rec_previo.antelacion_minutos,
                    )
                except RecordatorioInvalidoError:
                    await self._motor.cancelar_por_item(TipoOrigenRecordatorio.EVENTO, editado.id)

        return editado

    async def eliminar_evento(self, evento_id: UUID) -> None:
        """Cancela recordatorio asociado (RN-02) y elimina el evento."""
        await self._motor.cancelar_por_item(TipoOrigenRecordatorio.EVENTO, evento_id)
        self._repo.eliminar(evento_id)

    def obtener_evento(self, evento_id: UUID) -> Evento | None:
        return self._repo.obtener_por_id(evento_id)

    def obtener_ocurrencias_vista(
        self,
        desde: datetime,
        hasta: datetime,
        *,
        categoria_id: UUID | None = None,
        subcategoria_id: UUID | None = None,
    ) -> list[OcurrenciaEvento]:
        """Devuelve todas las ocurrencias (puntuales + recurrentes) ordenadas para vistas Día/Semana/Mes/Año."""
        eventos = self._repo.listar_en_rango(
            desde,
            hasta,
            categoria_id=categoria_id,
            subcategoria_id=subcategoria_id,
        )
        ocurrencias: list[OcurrenciaEvento] = []
        for ev in eventos:
            ocurrencias.extend(ExpansorRecurrencia.expandir_en_rango(ev, desde, hasta))
        ocurrencias.sort(key=lambda o: o.inicio)
        return ocurrencias

    def obtener_historial(self) -> list[Evento]:
        """Devuelve los eventos pasados conservados en historial (RN-04)."""
        return self._repo.listar_historial(self._reloj.ahora_utc())

    def _validar_sin_choque(self, candidato: Evento) -> None:
        if candidato.todo_el_dia:
            return
        desde = candidato.fecha_inicio - timedelta(days=1)
        fin_ref = (
            candidato.fecha_fin
            if candidato.fecha_fin is not None
            else candidato.fecha_inicio
        )
        hasta = (
            candidato.fecha_inicio + timedelta(days=366)
            if candidato.recurrencia is not None
            else fin_ref + timedelta(days=1)
        )
        existentes = self._repo.listar_candidatos_solapamiento(desde, hasta)
        conflicto = DetectorSolapamiento.buscar_conflicto(candidato, existentes)
        if conflicto is not None:
            raise ChoqueEventosError(
                f"Choque de horario con el evento '{conflicto.evento_existente.titulo}' "
                f"({conflicto.inicio_conflicto.strftime('%Y-%m-%d %H:%M UTC')}).",
                evento_en_conflicto_id=conflicto.evento_existente.id,
                titulo_conflicto=conflicto.evento_existente.titulo,
                inicio_conflicto=conflicto.inicio_conflicto,
                fin_conflicto=conflicto.fin_conflicto,
            )

    def _validar_jerarquia(
        self,
        categoria_id: UUID | None,
        subcategoria_id: UUID | None,
    ) -> None:
        if subcategoria_id is None:
            return
        if categoria_id is None or not self._repo_categorias.subcategoria_pertenece_a(
            subcategoria_id, categoria_id
        ):
            raise JerarquiaCategoriaInvalidaError(
                "La subcategoría seleccionada no pertenece a la categoría padre."
            )

    @staticmethod
    def _resolver_objetivo_notificacion(evento: Evento, ahora: datetime) -> datetime | None:
        if evento.recurrencia is None:
            return evento.fecha_inicio
        proxima = ExpansorRecurrencia.siguiente_ocurrencia(evento, ahora)
        return proxima.inicio if proxima is not None else None

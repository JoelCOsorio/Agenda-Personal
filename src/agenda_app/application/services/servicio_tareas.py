"""Servicio de aplicación para el Módulo Independiente de Tareas (PROC-04, RN-07, RN-12)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from agenda_app.application.ports.reloj import IReloj
from agenda_app.application.ports.repositorios import (
    IRepositorioCategorias,
    IRepositorioRecordatorios,
    IRepositorioTareas,
)
from agenda_app.application.services.motor_notificaciones import MotorNotificaciones
from agenda_app.domain.entities.tarea import Tarea
from agenda_app.domain.enums import (
    EstadoTarea,
    PrioridadTarea,
    TipoOrigenRecordatorio,
)
from agenda_app.domain.exceptions import (
    EntidadNoEncontradaError,
    JerarquiaCategoriaInvalidaError,
    RecordatorioInvalidoError,
)
from agenda_app.domain.rules.recordatorio_rules import ValidadorRecordatorio


class ServicioTareas:
    """Orquesta CRUD de tareas y su ciclo de vida de recordatorios (RN-02, RN-03, RN-12)."""

    def __init__(
        self,
        repo_tareas: IRepositorioTareas,
        repo_categorias: IRepositorioCategorias,
        repo_recordatorios: IRepositorioRecordatorios,
        motor_notificaciones: MotorNotificaciones,
        reloj: IReloj,
    ) -> None:
        self._repo = repo_tareas
        self._repo_categorias = repo_categorias
        self._repo_recordatorios = repo_recordatorios
        self._motor = motor_notificaciones
        self._reloj = reloj

    async def crear_tarea(
        self,
        *,
        titulo: str,
        descripcion: str | None = None,
        fecha_limite: datetime | None = None,
        prioridad: PrioridadTarea = PrioridadTarea.MEDIA,
        estado: EstadoTarea = EstadoTarea.PENDIENTE,
        categoria_id: UUID | None = None,
        subcategoria_id: UUID | None = None,
        contacto_ids: Sequence[UUID] = (),
        recordatorio_antelacion_min: int | None = None,
    ) -> Tarea:
        ahora = self._reloj.ahora_utc()
        self._validar_jerarquia(categoria_id, subcategoria_id)

        if recordatorio_antelacion_min is not None and estado != EstadoTarea.COMPLETADA:
            if fecha_limite is None:
                raise RecordatorioInvalidoError(
                    "Para programar un recordatorio en una tarea se requiere fecha_limite."
                )
            ValidadorRecordatorio.calcular_y_validar_disparo(
                fecha_objetivo=fecha_limite,
                antelacion_minutos=recordatorio_antelacion_min,
                ahora=ahora,
            )

        tarea = Tarea(
            titulo=titulo,
            descripcion=descripcion,
            fecha_limite=fecha_limite,
            prioridad=prioridad,
            estado=estado,
            categoria_id=categoria_id,
            subcategoria_id=subcategoria_id,
            contacto_ids=tuple(contacto_ids),
            created_at=ahora,
            updated_at=ahora,
        )
        self._repo.guardar(tarea)

        if (
            recordatorio_antelacion_min is not None
            and tarea.fecha_limite is not None
            and not tarea.esta_completada
        ):
            await self._motor.programar_o_reprogramar(
                tipo_origen=TipoOrigenRecordatorio.TAREA,
                item_id=tarea.id,
                titulo=tarea.titulo,
                cuerpo=tarea.descripcion or "Fecha límite de tarea próxima",
                fecha_objetivo=tarea.fecha_limite,
                antelacion_minutos=recordatorio_antelacion_min,
            )
        return tarea

    async def editar_tarea(
        self,
        tarea_id: UUID,
        *,
        titulo: str | None = None,
        descripcion: str | None = None,
        fecha_limite: datetime | None = None,
        actualizar_fecha_limite: bool = False,
        prioridad: PrioridadTarea | None = None,
        estado: EstadoTarea | None = None,
        categoria_id: UUID | None = None,
        subcategoria_id: UUID | None = None,
        actualizar_clasificacion: bool = False,
        contacto_ids: Sequence[UUID] | None = None,
        recordatorio_antelacion_min: int | None = None,
        eliminar_recordatorio: bool = False,
    ) -> Tarea:
        actual = self._repo.obtener_por_id(tarea_id)
        if actual is None:
            raise EntidadNoEncontradaError(f"Tarea {tarea_id} no encontrada.")

        ahora = self._reloj.ahora_utc()
        cat_final = categoria_id if actualizar_clasificacion else actual.categoria_id
        sub_final = subcategoria_id if actualizar_clasificacion else actual.subcategoria_id
        self._validar_jerarquia(cat_final, sub_final)

        fecha_final = fecha_limite if actualizar_fecha_limite else actual.fecha_limite
        estado_final = actual.estado if estado is None else estado

        if (
            not eliminar_recordatorio
            and recordatorio_antelacion_min is not None
            and estado_final != EstadoTarea.COMPLETADA
        ):
            if fecha_final is None:
                raise RecordatorioInvalidoError(
                    "Para programar un recordatorio en una tarea se requiere fecha_limite."
                )
            ValidadorRecordatorio.calcular_y_validar_disparo(
                fecha_objetivo=fecha_final,
                antelacion_minutos=recordatorio_antelacion_min,
                ahora=ahora,
            )

        editada = Tarea(
            id=actual.id,
            titulo=actual.titulo if titulo is None else titulo,
            descripcion=actual.descripcion if descripcion is None else descripcion,
            fecha_limite=fecha_final,
            prioridad=actual.prioridad if prioridad is None else prioridad,
            estado=estado_final,
            categoria_id=cat_final,
            subcategoria_id=sub_final,
            contacto_ids=(
                actual.contacto_ids if contacto_ids is None else tuple(contacto_ids)
            ),
            created_at=actual.created_at,
            updated_at=ahora,
        )
        self._repo.guardar(editada)

        if editada.esta_completada or eliminar_recordatorio or editada.fecha_limite is None:
            await self._motor.cancelar_por_item(TipoOrigenRecordatorio.TAREA, editada.id)
        elif recordatorio_antelacion_min is not None:
            await self._motor.programar_o_reprogramar(
                tipo_origen=TipoOrigenRecordatorio.TAREA,
                item_id=editada.id,
                titulo=editada.titulo,
                cuerpo=editada.descripcion or "Fecha límite de tarea próxima",
                fecha_objetivo=editada.fecha_limite,
                antelacion_minutos=recordatorio_antelacion_min,
            )
        elif actualizar_fecha_limite:
            # Si cambió la fecha límite y ya tenía un recordatorio previo, reestablecerlo (RN-02, RN-12)
            rec_previo = self._repo_recordatorios.obtener_por_item(
                TipoOrigenRecordatorio.TAREA, editada.id
            )
            if rec_previo is not None:
                try:
                    await self._motor.programar_o_reprogramar(
                        tipo_origen=TipoOrigenRecordatorio.TAREA,
                        item_id=editada.id,
                        titulo=editada.titulo,
                        cuerpo=editada.descripcion or "Fecha límite de tarea próxima",
                        fecha_objetivo=editada.fecha_limite,
                        antelacion_minutos=rec_previo.antelacion_minutos,
                    )
                except RecordatorioInvalidoError:
                    await self._motor.cancelar_por_item(TipoOrigenRecordatorio.TAREA, editada.id)

        return editada

    async def completar_tarea(self, tarea_id: UUID) -> Tarea:
        """Marca la tarea como completada y cancela automáticamente su notificación (RN-12)."""
        tarea = self._repo.obtener_por_id(tarea_id)
        if tarea is None:
            raise EntidadNoEncontradaError(f"Tarea {tarea_id} no encontrada.")
        tarea.completar(self._reloj.ahora_utc())
        self._repo.guardar(tarea)
        await self._motor.cancelar_por_item(TipoOrigenRecordatorio.TAREA, tarea.id)
        return tarea

    async def reactivar_tarea(
        self,
        tarea_id: UUID,
        *,
        nuevo_estado: EstadoTarea = EstadoTarea.PENDIENTE,
        nueva_fecha_limite: datetime | None = None,
        antelacion_minutos: int | None = None,
    ) -> Tarea:
        """Reactiva una tarea completada y reestablece su recordatorio si sigue vigente (RN-12)."""
        tarea = self._repo.obtener_por_id(tarea_id)
        if tarea is None:
            raise EntidadNoEncontradaError(f"Tarea {tarea_id} no encontrada.")

        ahora = self._reloj.ahora_utc()
        tarea.reactivar(nuevo_estado, ahora)
        if nueva_fecha_limite is not None:
            tarea.reprogramar(nueva_fecha_limite, ahora)
        self._repo.guardar(tarea)

        if tarea.fecha_limite is not None:
            rec_previo = self._repo_recordatorios.obtener_por_item(
                TipoOrigenRecordatorio.TAREA, tarea.id
            )
            antelacion = (
                antelacion_minutos
                if antelacion_minutos is not None
                else (rec_previo.antelacion_minutos if rec_previo is not None else None)
            )
            if antelacion is not None:
                try:
                    await self._motor.programar_o_reprogramar(
                        tipo_origen=TipoOrigenRecordatorio.TAREA,
                        item_id=tarea.id,
                        titulo=tarea.titulo,
                        cuerpo=tarea.descripcion or "Fecha límite de tarea próxima",
                        fecha_objetivo=tarea.fecha_limite,
                        antelacion_minutos=antelacion,
                    )
                except RecordatorioInvalidoError:
                    # Si la fecha límite ya venció al reactivar, no bloqueamos la reactivación
                    pass

        return tarea

    async def eliminar_tarea(self, tarea_id: UUID) -> None:
        await self._motor.cancelar_por_item(TipoOrigenRecordatorio.TAREA, tarea_id)
        self._repo.eliminar(tarea_id)

    def obtener_tarea(self, tarea_id: UUID) -> Tarea | None:
        return self._repo.obtener_por_id(tarea_id)

    def listar_tareas(
        self,
        *,
        estado: EstadoTarea | None = None,
        prioridad: PrioridadTarea | None = None,
        categoria_id: UUID | None = None,
        subcategoria_id: UUID | None = None,
    ) -> list[Tarea]:
        return self._repo.listar(
            estado=estado,
            prioridad=prioridad,
            categoria_id=categoria_id,
            subcategoria_id=subcategoria_id,
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
                "RN-09: La subcategoría seleccionada no pertenece a la categoría padre."
            )

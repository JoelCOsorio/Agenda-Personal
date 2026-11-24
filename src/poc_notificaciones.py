"""PoC interactivo en Flet 1.x para probar el Motor de Notificaciones en vivo.

Ejecutar con:
    uv run flet run src/poc_notificaciones.py
"""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import flet as ft

from agenda_app.container import construir_contenedor_notificaciones
from agenda_app.domain.entities.recordatorio import Recordatorio
from agenda_app.domain.enums import EstadoRecordatorio, TipoOrigenRecordatorio


async def main(page: ft.Page) -> None:
    page.title = "PoC — Motor Unificado de Notificaciones"
    page.window.width = 760
    page.window.height = 680
    page.padding = 20

    contenedor = construir_contenedor_notificaciones(page_platform=page.platform)
    ultimo_evento_id = uuid4()

    log_view = ft.ListView(expand=True, spacing=6, auto_scroll=True)
    estado_plataforma = ft.Text(weight=ft.FontWeight.BOLD)
    snooze_input = ft.TextField(
        label="Minutos de Posponer (Ajustes RN-14)",
        value=str(contenedor.repo_ajustes.obtener().minutos_posponer_defecto),
        width=260,
    )

    def registrar_log(mensaje: str) -> None:
        ahora = contenedor.reloj.ahora_utc().strftime("%H:%M:%S UTC")
        log_view.controls.append(ft.Text(f"[{ahora}] {mensaje}", size=13))
        page.update()

    async def inicializar() -> None:
        caps = await contenedor.adaptador.obtener_capacidades()
        estado_plataforma.value = (
            f"Plataforma: {caps.plataforma.value} | "
            f"Programación nativa: {caps.soporta_programacion_nativa} | "
            f"Acciones rápidas: {caps.soporta_acciones_rapidas} | "
            f"BD: {contenedor.db.db_path}"
        )
        await contenedor.adaptador.solicitar_permisos()
        resultado = await contenedor.reconciliador.reconciliar()
        registrar_log(
            f"StartupReconciler -> perdidos detectados: {len(resultado.perdidos_detectados)}, "
            f"total perdidos sin atender: {len(resultado.total_perdidos_sin_atender)}, "
            f"reprogramados en SO: {resultado.reprogramados_en_so}"
        )
        page.update()

    def _asegurar_evento_demo(evento_id: str, titulo: str) -> None:
        ahora_iso = contenedor.reloj.ahora_utc().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        with contenedor.db.transaccion() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO eventos (
                    id, titulo, descripcion, fecha_inicio, fecha_fin,
                    todo_el_dia, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    evento_id,
                    titulo,
                    "Evento de prueba generado desde poc_notificaciones.py",
                    ahora_iso,
                    ahora_iso,
                    ahora_iso,
                    ahora_iso,
                ),
            )

    async def programar_en_10s(e: ft.Event[ft.Button]) -> None:
        nonlocal ultimo_evento_id
        ultimo_evento_id = uuid4()
        _asegurar_evento_demo(str(ultimo_evento_id), "Clase de Prueba (PoC)")
        objetivo = contenedor.reloj.ahora_utc() + timedelta(seconds=10)
        rec = await contenedor.motor.programar_o_reprogramar(
            tipo_origen=TipoOrigenRecordatorio.EVENTO,
            item_id=ultimo_evento_id,
            titulo="Clase de Prueba (PoC)",
            cuerpo="Notificación disparada por el Motor Unificado en +10s.",
            fecha_objetivo=objetivo,
            antelacion_minutos=0,
        )
        registrar_log(
            f"Programado id_so={rec.id_notificacion_so} para {rec.fecha_disparo.strftime('%H:%M:%S UTC')}."
        )

    async def cancelar_ultimo(e: ft.Event[ft.Button]) -> None:
        cancelado = await contenedor.motor.cancelar_por_item(
            TipoOrigenRecordatorio.EVENTO,
            ultimo_evento_id,
        )
        registrar_log(
            "Último recordatorio cancelado (RN-02)."
            if cancelado
            else "No había recordatorio activo para el último evento."
        )

    async def simular_perdida(e: ft.Event[ft.Button]) -> None:
        ev_id = uuid4()
        _asegurar_evento_demo(str(ev_id), "Evento Vencido (Simulación Apagado)")
        pasado = contenedor.reloj.ahora_utc() - timedelta(minutes=30)
        rec = Recordatorio(
            id_notificacion_so=contenedor.repo_recordatorios.siguiente_id_notificacion_so(),
            tipo_origen=TipoOrigenRecordatorio.EVENTO,
            evento_id=ev_id,
            antelacion_minutos=15,
            fecha_disparo=pasado,
            estado=EstadoRecordatorio.PENDIENTE,
            created_at=pasado,
            updated_at=pasado,
        )
        contenedor.repo_recordatorios.guardar(rec)
        resultado = await contenedor.reconciliador.reconciliar()
        registrar_log(
            f"Simulación equipo apagado -> detectadas {len(resultado.perdidos_detectados)} "
            f"alertas PERDIDAS (RN-05). Total sin atender: {len(resultado.total_perdidos_sin_atender)}."
        )

    async def guardar_snooze(e: ft.Event[ft.Button]) -> None:
        try:
            minutos = int(snooze_input.value or "10")
            ajustes = contenedor.repo_ajustes.obtener()
            ajustes.minutos_posponer_defecto = minutos
            ajustes.tocar_actualizacion(contenedor.reloj.ahora_utc())
            contenedor.repo_ajustes.guardar(ajustes)
            registrar_log(f"Ajustes guardados: minutos_posponer_defecto = {minutos} min (RN-14).")
        except Exception as exc:
            registrar_log(f"Error en Ajustes: {exc}")

    async def handle_lifecycle(e: ft.AppLifecycleStateChangeEvent) -> None:
        if e.state == ft.AppLifecycleState.RESUME:
            res = await contenedor.reconciliador.reconciliar()
            registrar_log(
                f"RESUME -> perdidas sin atender: {len(res.total_perdidos_sin_atender)}"
            )

    page.on_app_lifecycle_state_change = handle_lifecycle

    page.add(
        ft.Column(
            expand=True,
            spacing=12,
            controls=[
                ft.Text("PoC — Motor Unificado de Notificaciones", size=22, weight=ft.FontWeight.BOLD),
                estado_plataforma,
                ft.Row(
                    wrap=True,
                    spacing=10,
                    controls=[
                        ft.Button("Programar en +10 seg", on_click=programar_en_10s),
                        ft.Button("Cancelar último (RN-02)", on_click=cancelar_ultimo),
                        ft.Button("Simular alerta perdida (RN-05)", on_click=simular_perdida),
                    ],
                ),
                ft.Row(
                    spacing=10,
                    controls=[
                        snooze_input,
                        ft.Button("Guardar Snooze", on_click=guardar_snooze),
                    ],
                ),
                ft.Divider(),
                ft.Text("Registro de eventos:", weight=ft.FontWeight.BOLD),
                ft.Container(
                    expand=True,
                    border=ft.Border.all(1, ft.Colors.OUTLINE),
                    border_radius=8,
                    padding=10,
                    content=log_view,
                ),
            ],
        )
    )

    await inicializar()


if __name__ == "__main__":
    ft.run(main)

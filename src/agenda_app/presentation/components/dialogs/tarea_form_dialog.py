"""Formulario modal para crear y editar Tareas con recordatorio (PROC-04, RN-03, RN-12)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date, datetime, time, timedelta
from uuid import UUID

import flet as ft

from agenda_app.container import ContenedorAplicacion
from agenda_app.domain.entities.tarea import Tarea
from agenda_app.domain.enums import (
    EstadoTarea,
    PrioridadTarea,
    TipoOrigenRecordatorio,
)
from agenda_app.domain.exceptions import DominioError
from agenda_app.presentation.components.dialogs.categoria_dialog import (
    abrir_dialogo_categoria_rapida,
)
from agenda_app.presentation.formatters import (
    OPCIONES_ANTELACION_MIN,
    combinar_local_a_utc,
    etiqueta_estado_tarea,
    formatear_fecha,
    utc_a_local,
)
from agenda_app.presentation.theme import etiqueta_prioridad


def abrir_formulario_tarea(
    page: ft.Page,
    contenedor: ContenedorAplicacion,
    *,
    tarea_editar: Tarea | None = None,
    on_guardada: Callable[[], Awaitable[None]],
) -> None:
    ajustes = contenedor.servicio_ajustes.obtener()
    ahora_local = utc_a_local(contenedor.reloj.ahora_utc())

    if tarea_editar is not None:
        lim_loc = (
            utc_a_local(tarea_editar.fecha_limite)
            if tarea_editar.fecha_limite is not None
            else None
        )
        rec_existente = contenedor.repo_recordatorios.obtener_por_item(
            TipoOrigenRecordatorio.TAREA, tarea_editar.id
        )
    else:
        lim_loc = (ahora_local + timedelta(days=1)).replace(
            hour=18, minute=0, second=0, microsecond=0
        )
        rec_existente = None

    estado_form = {
        "fecha_lim": lim_loc.date() if lim_loc else (ahora_local.date() + timedelta(days=1)),
        "hora_lim": (
            lim_loc.time().replace(second=0, microsecond=0)
            if lim_loc
            else time(18, 0)
        ),
        "contactos_sel": set(tarea_editar.contacto_ids if tarea_editar else ()),
    }

    titulo_field = ft.TextField(
        label="Título *",
        value=tarea_editar.titulo if tarea_editar else "",
        autofocus=True,
    )
    desc_field = ft.TextField(
        label="Descripción",
        value=(tarea_editar.descripcion or "") if tarea_editar else "",
        multiline=True,
        min_lines=2,
        max_lines=3,
    )
    prioridad_dd = ft.Dropdown(
        label="Prioridad",
        value=(tarea_editar.prioridad if tarea_editar else PrioridadTarea.MEDIA).value,
        options=[
            ft.DropdownOption(key=p.value, text=etiqueta_prioridad(p))
            for p in PrioridadTarea
        ],
        expand=True,
    )
    estado_dd = ft.Dropdown(
        label="Estado",
        value=(tarea_editar.estado if tarea_editar else EstadoTarea.PENDIENTE).value,
        options=[
            ft.DropdownOption(key=s.value, text=etiqueta_estado_tarea(s))
            for s in EstadoTarea
        ],
        expand=True,
    )

    con_fecha_sw = ft.Switch(
        label="Definir fecha límite",
        value=(lim_loc is not None) if tarea_editar else True,
    )

    def _fmt_hora(t: time) -> str:
        dt_tmp = datetime.combine(date.today(), t)
        return dt_tmp.strftime("%H:%M") if ajustes.formato_24h else dt_tmp.strftime("%I:%M %p").lstrip("0")

    btn_fecha = ft.OutlinedButton(
        f"Fecha: {formatear_fecha(estado_form['fecha_lim'])}",
        icon=ft.Icons.CALENDAR_TODAY,
    )
    btn_hora = ft.OutlinedButton(
        f"Hora: {_fmt_hora(estado_form['hora_lim'])}",
        icon=ft.Icons.ACCESS_TIME,
    )
    hour_fmt = (
        ft.TimePickerHourFormat.H24
        if ajustes.formato_24h
        else ft.TimePickerHourFormat.H12
    )

    def _pick_fecha(_: ft.Event) -> None:
        def _on_change(e: ft.Event[ft.DatePicker]) -> None:
            if e.control.value:
                estado_form["fecha_lim"] = e.control.value.date()
                btn_fecha.content = f"Fecha: {formatear_fecha(estado_form['fecha_lim'])}"
                page.update()

        page.show_dialog(
            ft.DatePicker(
                first_date=datetime(2020, 1, 1),
                last_date=datetime(2035, 12, 31),
                current_date=datetime.combine(estado_form["fecha_lim"], time(0, 0)),
                on_change=_on_change,
            )
        )

    def _pick_hora(_: ft.Event) -> None:
        def _on_change(e: ft.Event[ft.TimePicker]) -> None:
            if e.control.value:
                estado_form["hora_lim"] = e.control.value.replace(second=0, microsecond=0)
                btn_hora.content = f"Hora: {_fmt_hora(estado_form['hora_lim'])}"
                page.update()

        page.show_dialog(
            ft.TimePicker(
                value=estado_form["hora_lim"],
                hour_format=hour_fmt,
                on_change=_on_change,
            )
        )

    btn_fecha.on_click = _pick_fecha
    btn_hora.on_click = _pick_hora
    fila_fecha = ft.Row(spacing=8, wrap=True, controls=[btn_fecha, btn_hora], visible=bool(con_fecha_sw.value))

    # Categoría y Subcategoría con botón + rápido (RF-22)
    cat_dd = ft.Dropdown(label="Categoría", expand=True)
    sub_dd = ft.Dropdown(label="Subcategoría", expand=True)

    def _cargar_cats(sel_cat: str | None = None, sel_sub: str | None = None) -> None:
        cats = contenedor.servicio_categorias.listar_categorias()
        cat_dd.options = [ft.DropdownOption(key="", text="Sin categoría")] + [
            ft.DropdownOption(key=str(c.id), text=c.nombre) for c in cats
        ]
        if sel_cat is not None:
            cat_dd.value = sel_cat
        _cargar_subs(sel_sub)

    def _cargar_subs(sel_sub: str | None = None) -> None:
        if not cat_dd.value:
            sub_dd.options = [ft.DropdownOption(key="", text="Sin subcategoría")]
            sub_dd.value = ""
            sub_dd.disabled = True
            return
        subs = contenedor.servicio_categorias.listar_subcategorias(UUID(cat_dd.value))
        sub_dd.options = [ft.DropdownOption(key="", text="Sin subcategoría")] + [
            ft.DropdownOption(key=str(s.id), text=s.nombre) for s in subs
        ]
        sub_dd.disabled = False
        sub_dd.value = sel_sub if sel_sub is not None else ""

    cat_dd.on_select = lambda _: (_cargar_subs(""), page.update())
    _cargar_cats(
        sel_cat=str(tarea_editar.categoria_id) if tarea_editar and tarea_editar.categoria_id else "",
        sel_sub=str(tarea_editar.subcategoria_id) if tarea_editar and tarea_editar.subcategoria_id else "",
    )

    btn_add_cat = ft.IconButton(
        icon=ft.Icons.ADD_CIRCLE_OUTLINE,
        tooltip="Crear categoría rápida",
        on_click=lambda _: abrir_dialogo_categoria_rapida(
            page,
            contenedor,
            on_creada=lambda cid, _: (_cargar_cats(str(cid), ""), page.update()),
        ),
    )
    btn_add_sub = ft.IconButton(
        icon=ft.Icons.ADD_CIRCLE_OUTLINE,
        tooltip="Crear subcategoría rápida",
        on_click=lambda _: (
            abrir_dialogo_categoria_rapida(
                page,
                contenedor,
                categoria_padre_id=UUID(cat_dd.value),
                on_creada=lambda cid, sid: (
                    _cargar_cats(str(cid), str(sid) if sid else ""),
                    page.update(),
                ),
            )
            if cat_dd.value
            else None
        ),
    )

    # Recordatorio (RN-03)
    antelacion_ini: int | None = (
        rec_existente.antelacion_minutos
        if rec_existente is not None and rec_existente.esta_activo
        else (None if tarea_editar else ajustes.antelacion_recordatorio_defecto_min)
    )
    presets = {v for v, _ in OPCIONES_ANTELACION_MIN}
    val_dd_rec = (
        "CUSTOM"
        if (antelacion_ini is not None and antelacion_ini not in presets)
        else ("" if antelacion_ini is None else str(antelacion_ini))
    )
    rec_dd = ft.Dropdown(
        label="Recordatorio",
        value=val_dd_rec,
        options=[
            ft.DropdownOption(key="" if v is None else str(v), text=lbl)
            for v, lbl in OPCIONES_ANTELACION_MIN
        ]
        + [ft.DropdownOption(key="CUSTOM", text="Personalizado (minutos)")],
        visible=bool(con_fecha_sw.value),
    )
    rec_custom = ft.TextField(
        label="Minutos antes (0 - 10080)",
        value=str(antelacion_ini or 15),
        visible=bool(con_fecha_sw.value) and val_dd_rec == "CUSTOM",
    )

    def _toggle_fecha(_: ft.Event) -> None:
        activo = bool(con_fecha_sw.value)
        fila_fecha.visible = activo
        rec_dd.visible = activo
        rec_custom.visible = activo and rec_dd.value == "CUSTOM"
        page.update()

    con_fecha_sw.on_change = _toggle_fecha
    rec_dd.on_select = lambda _: (
        setattr(rec_custom, "visible", bool(con_fecha_sw.value) and rec_dd.value == "CUSTOM"),
        page.update(),
    )

    # Contactos vinculados
    todos_contactos = contenedor.servicio_contactos.buscar()
    chips_contactos = ft.Row(
        wrap=True,
        spacing=6,
        controls=[
            ft.Chip(
                label=ft.Text(c.nombre, size=12),
                selected=c.id in estado_form["contactos_sel"],
                on_select=lambda e, cid=c.id: (
                    estado_form["contactos_sel"].add(cid)
                    if e.control.selected
                    else estado_form["contactos_sel"].discard(cid)
                ),
            )
            for c in todos_contactos
        ],
    )

    error_txt = ft.Text("", color=ft.Colors.ERROR, size=12.5, visible=False)

    async def _guardar(_: ft.Event) -> None:
        error_txt.visible = False
        try:
            fecha_lim_utc = (
                combinar_local_a_utc(estado_form["fecha_lim"], estado_form["hora_lim"])
                if con_fecha_sw.value
                else None
            )
            eliminar_rec = (not con_fecha_sw.value) or rec_dd.value == ""
            antelacion_min: int | None = None
            if not eliminar_rec:
                antelacion_min = (
                    int(rec_custom.value or "0")
                    if rec_dd.value == "CUSTOM"
                    else int(rec_dd.value or "0")
                )

            cat_id = UUID(cat_dd.value) if cat_dd.value else None
            sub_id = UUID(sub_dd.value) if sub_dd.value else None

            if tarea_editar is None:
                await contenedor.servicio_tareas.crear_tarea(
                    titulo=titulo_field.value or "",
                    descripcion=desc_field.value or None,
                    fecha_limite=fecha_lim_utc,
                    prioridad=PrioridadTarea(prioridad_dd.value or PrioridadTarea.MEDIA.value),
                    estado=EstadoTarea(estado_dd.value or EstadoTarea.PENDIENTE.value),
                    categoria_id=cat_id,
                    subcategoria_id=sub_id,
                    contacto_ids=list(estado_form["contactos_sel"]),
                    recordatorio_antelacion_min=antelacion_min,
                )
            else:
                await contenedor.servicio_tareas.editar_tarea(
                    tarea_editar.id,
                    titulo=titulo_field.value or "",
                    descripcion=desc_field.value or None,
                    fecha_limite=fecha_lim_utc,
                    actualizar_fecha_limite=True,
                    prioridad=PrioridadTarea(prioridad_dd.value or PrioridadTarea.MEDIA.value),
                    estado=EstadoTarea(estado_dd.value or EstadoTarea.PENDIENTE.value),
                    categoria_id=cat_id,
                    subcategoria_id=sub_id,
                    actualizar_clasificacion=True,
                    contacto_ids=list(estado_form["contactos_sel"]),
                    recordatorio_antelacion_min=antelacion_min,
                    eliminar_recordatorio=eliminar_rec,
                )

            page.pop_dialog()
            await on_guardada()
        except (DominioError, ValueError) as exc:
            error_txt.value = str(exc)
            error_txt.visible = True
            page.update()

    dialogo = ft.AlertDialog(
        modal=True,
        title=ft.Text("Editar tarea" if tarea_editar else "Nueva tarea"),
        content=ft.Container(
            width=460,
            height=480,
            content=ft.Column(
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    error_txt,
                    titulo_field,
                    desc_field,
                    ft.Row(spacing=8, controls=[prioridad_dd, estado_dd]),
                    con_fecha_sw,
                    fila_fecha,
                    ft.Row(spacing=6, controls=[cat_dd, btn_add_cat]),
                    ft.Row(spacing=6, controls=[sub_dd, btn_add_sub]),
                    rec_dd,
                    rec_custom,
                    ft.Text("Contactos vinculados:", size=12, weight=ft.FontWeight.W_600),
                    chips_contactos
                    if todos_contactos
                    else ft.Text(
                        "Sin contactos registrados aún.",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
            ),
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: page.pop_dialog()),
            ft.FilledButton("Guardar", on_click=_guardar),
        ],
    )
    page.show_dialog(dialogo)

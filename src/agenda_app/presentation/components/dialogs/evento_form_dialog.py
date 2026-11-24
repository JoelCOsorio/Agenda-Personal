"""Formulario modal de Evento con validación visual de ChoqueEventosError (RN-11)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date, datetime, time, timedelta
from uuid import UUID

import flet as ft

from agenda_app.container import ContenedorAplicacion
from agenda_app.domain.entities.evento import (
    DIAS_SEMANA_VALIDOS,
    Evento,
    ReglaRecurrencia,
)
from agenda_app.domain.enums import TipoFrecuencia, TipoOrigenRecordatorio
from agenda_app.domain.exceptions import ChoqueEventosError, DominioError
from agenda_app.presentation.components.dialogs.categoria_dialog import (
    abrir_dialogo_categoria_rapida,
)
from agenda_app.presentation.formatters import (
    OPCIONES_ANTELACION_MIN,
    combinar_local_a_utc,
    formatear_fecha,
    formatear_fecha_hora,
    utc_a_local,
)


def abrir_formulario_evento(
    page: ft.Page,
    contenedor: ContenedorAplicacion,
    *,
    evento_editar: Evento | None = None,
    fecha_inicial: date | None = None,
    on_guardado: Callable[[], Awaitable[None]],
) -> None:
    """Abre el diálogo para crear o editar un Evento (PROC-01, RN-01, RN-03, RN-11)."""
    ajustes = contenedor.servicio_ajustes.obtener()
    ahora_local = utc_a_local(contenedor.reloj.ahora_utc())

    if evento_editar is not None:
        ini_loc = utc_a_local(evento_editar.fecha_inicio)
        fin_loc = (
            utc_a_local(evento_editar.fecha_fin)
            if evento_editar.fecha_fin is not None
            else None
        )
        rec_existente = contenedor.repo_recordatorios.obtener_por_item(
            TipoOrigenRecordatorio.EVENTO, evento_editar.id
        )
    else:
        dia_base = fecha_inicial or ahora_local.date()
        hora_sig = (ahora_local + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        ini_loc = datetime.combine(dia_base, hora_sig.time())
        fin_loc = ini_loc + timedelta(hours=1)
        rec_existente = None

    estado = {
        "fecha_inicio": ini_loc.date(),
        "hora_inicio": ini_loc.time().replace(second=0, microsecond=0),
        "fecha_fin": fin_loc.date() if fin_loc else ini_loc.date(),
        "hora_fin": (
            fin_loc.time().replace(second=0, microsecond=0)
            if fin_loc
            else (ini_loc + timedelta(hours=1)).time().replace(second=0, microsecond=0)
        ),
        "dias_semana": set(
            evento_editar.recurrencia.dias_semana
            if evento_editar and evento_editar.recurrencia
            else ()
        ),
        "contactos_sel": set(evento_editar.contacto_ids if evento_editar else ()),
    }

    titulo_field = ft.TextField(
        label="Título *",
        value=evento_editar.titulo if evento_editar else "",
        autofocus=True,
    )
    desc_field = ft.TextField(
        label="Descripción",
        value=(evento_editar.descripcion or "") if evento_editar else "",
        multiline=True,
        min_lines=2,
        max_lines=3,
    )
    ubic_field = ft.TextField(
        label="Ubicación o enlace",
        value=(evento_editar.ubicacion or "") if evento_editar else "",
    )

    todo_el_dia_sw = ft.Switch(
        label="Todo el día",
        value=evento_editar.todo_el_dia if evento_editar else False,
    )
    con_hora_fin_sw = ft.Switch(
        label="Definir hora de fin",
        value=(fin_loc is not None) if evento_editar else True,
    )

    def _fmt_hora(t: time) -> str:
        dt_tmp = datetime.combine(date.today(), t)
        return dt_tmp.strftime("%H:%M") if ajustes.formato_24h else dt_tmp.strftime("%I:%M %p").lstrip("0")

    btn_fecha_ini = ft.OutlinedButton(
        f"Inicio: {formatear_fecha(estado['fecha_inicio'])}",
        icon=ft.Icons.CALENDAR_TODAY,
    )
    btn_hora_ini = ft.OutlinedButton(
        f"Hora: {_fmt_hora(estado['hora_inicio'])}",
        icon=ft.Icons.ACCESS_TIME,
    )
    btn_fecha_fin = ft.OutlinedButton(
        f"Fin: {formatear_fecha(estado['fecha_fin'])}",
        icon=ft.Icons.EVENT,
    )
    btn_hora_fin = ft.OutlinedButton(
        f"Hora: {_fmt_hora(estado['hora_fin'])}",
        icon=ft.Icons.SCHEDULE,
    )

    hour_fmt = (
        ft.TimePickerHourFormat.H24
        if ajustes.formato_24h
        else ft.TimePickerHourFormat.H12
    )

    def _pick_fecha(campo: str, btn: ft.OutlinedButton, prefijo: str) -> None:
        def _on_change(e: ft.Event[ft.DatePicker]) -> None:
            if e.control.value:
                estado[campo] = e.control.value.date()
                if campo == "fecha_inicio" and estado["fecha_fin"] < estado["fecha_inicio"]:
                    estado["fecha_fin"] = estado["fecha_inicio"]
                    btn_fecha_fin.content = f"Fin: {formatear_fecha(estado['fecha_fin'])}"
                btn.content = f"{prefijo}: {formatear_fecha(estado[campo])}"
                page.update()

        picker = ft.DatePicker(
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2035, 12, 31),
            current_date=datetime.combine(estado[campo], time(0, 0)),
            on_change=_on_change,
        )
        page.show_dialog(picker)

    def _pick_hora(campo: str, btn: ft.OutlinedButton) -> None:
        def _on_change(e: ft.Event[ft.TimePicker]) -> None:
            if e.control.value:
                estado[campo] = e.control.value.replace(second=0, microsecond=0)
                btn.content = f"Hora: {_fmt_hora(estado[campo])}"
                page.update()

        picker = ft.TimePicker(
            value=estado[campo],
            hour_format=hour_fmt,
            on_change=_on_change,
        )
        page.show_dialog(picker)

    btn_fecha_ini.on_click = lambda _: _pick_fecha("fecha_inicio", btn_fecha_ini, "Inicio")
    btn_hora_ini.on_click = lambda _: _pick_hora("hora_inicio", btn_hora_ini)
    btn_fecha_fin.on_click = lambda _: _pick_fecha("fecha_fin", btn_fecha_fin, "Fin")
    btn_hora_fin.on_click = lambda _: _pick_hora("hora_fin", btn_hora_fin)

    fila_fin = ft.Row(spacing=8, wrap=True, controls=[btn_fecha_fin, btn_hora_fin])

    def _actualizar_visibilidad_horarios(_: ft.Event | None = None) -> None:
        es_todo = bool(todo_el_dia_sw.value)
        btn_hora_ini.visible = not es_todo
        con_hora_fin_sw.visible = not es_todo
        fila_fin.visible = (not es_todo) and bool(con_hora_fin_sw.value)
        page.update()

    todo_el_dia_sw.on_change = _actualizar_visibilidad_horarios
    con_hora_fin_sw.on_change = _actualizar_visibilidad_horarios
    btn_hora_ini.visible = not todo_el_dia_sw.value
    con_hora_fin_sw.visible = not todo_el_dia_sw.value
    fila_fin.visible = (not todo_el_dia_sw.value) and bool(con_hora_fin_sw.value)

    # Categoría y Subcategoría en cascada con creación rápida en línea (RF-22)
    cat_dd = ft.Dropdown(label="Categoría", expand=True)
    sub_dd = ft.Dropdown(label="Subcategoría", expand=True)

    def _cargar_categorias(sel_cat: str | None = None, sel_sub: str | None = None) -> None:
        cats = contenedor.servicio_categorias.listar_categorias()
        cat_dd.options = [ft.DropdownOption(key="", text="Sin categoría")] + [
            ft.DropdownOption(key=str(c.id), text=c.nombre) for c in cats
        ]
        if sel_cat is not None:
            cat_dd.value = sel_cat
        _cargar_subcategorias(sel_sub)

    def _cargar_subcategorias(sel_sub: str | None = None) -> None:
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

    cat_dd.on_select = lambda _: (_cargar_subcategorias(""), page.update())
    _cargar_categorias(
        sel_cat=str(evento_editar.categoria_id) if evento_editar and evento_editar.categoria_id else "",
        sel_sub=str(evento_editar.subcategoria_id) if evento_editar and evento_editar.subcategoria_id else "",
    )

    btn_add_cat = ft.IconButton(
        icon=ft.Icons.ADD_CIRCLE_OUTLINE,
        tooltip="Crear categoría rápida",
        on_click=lambda _: abrir_dialogo_categoria_rapida(
            page,
            contenedor,
            on_creada=lambda cid, _: (_cargar_categorias(str(cid), ""), page.update()),
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
                    _cargar_categorias(str(cid), str(sid) if sid else ""),
                    page.update(),
                ),
            )
            if cat_dd.value
            else None
        ),
    )

    # Recurrencia (RF-06)
    frec_dd = ft.Dropdown(
        label="Repetición",
        value=(
            evento_editar.recurrencia.frecuencia.value
            if evento_editar and evento_editar.recurrencia
            else ""
        ),
        options=[
            ft.DropdownOption(key="", text="Sin repetición"),
            ft.DropdownOption(key=TipoFrecuencia.DIARIA.value, text="Diaria"),
            ft.DropdownOption(key=TipoFrecuencia.SEMANAL.value, text="Semanal"),
            ft.DropdownOption(key=TipoFrecuencia.MENSUAL.value, text="Mensual"),
            ft.DropdownOption(key=TipoFrecuencia.ANUAL.value, text="Anual"),
        ],
        expand=True,
    )
    intervalo_field = ft.TextField(
        label="Cada N",
        width=90,
        value=str(
            evento_editar.recurrencia.intervalo
            if evento_editar and evento_editar.recurrencia
            else 1
        ),
    )
    chips_dias = ft.Row(wrap=True, spacing=4)

    def _render_chips_dias() -> None:
        chips_dias.controls = [
            ft.Chip(
                label=ft.Text(d, size=11),
                selected=d in estado["dias_semana"],
                on_select=lambda e, dia=d: _toggle_dia(dia, bool(e.control.selected)),
            )
            for d in DIAS_SEMANA_VALIDOS
        ]
        chips_dias.visible = frec_dd.value == TipoFrecuencia.SEMANAL.value
        intervalo_field.visible = bool(frec_dd.value)

    def _toggle_dia(dia: str, seleccionado: bool) -> None:
        if seleccionado:
            estado["dias_semana"].add(dia)
        else:
            estado["dias_semana"].discard(dia)
        page.update()

    frec_dd.on_select = lambda _: (_render_chips_dias(), page.update())
    _render_chips_dias()

    # Recordatorio (0..10080 min, presets + personalizado — RN-03)
    antelacion_inicial: int | None = (
        rec_existente.antelacion_minutos
        if rec_existente is not None and rec_existente.esta_activo
        else (None if evento_editar else ajustes.antelacion_recordatorio_defecto_min)
    )
    presets_vals = {v for v, _ in OPCIONES_ANTELACION_MIN}
    valor_dd_rec = (
        "CUSTOM"
        if (antelacion_inicial is not None and antelacion_inicial not in presets_vals)
        else ("" if antelacion_inicial is None else str(antelacion_inicial))
    )
    rec_dd = ft.Dropdown(
        label="Recordatorio",
        value=valor_dd_rec,
        options=[
            ft.DropdownOption(key="" if v is None else str(v), text=lbl)
            for v, lbl in OPCIONES_ANTELACION_MIN
        ]
        + [ft.DropdownOption(key="CUSTOM", text="Personalizado (minutos)")],
        expand=True,
    )
    rec_custom_field = ft.TextField(
        label="Minutos antes (0 - 10080)",
        value=str(antelacion_inicial or 15),
        visible=valor_dd_rec == "CUSTOM",
    )
    rec_dd.on_select = lambda _: (
        setattr(rec_custom_field, "visible", rec_dd.value == "CUSTOM"),
        page.update(),
    )

    # Contactos vinculados (RF-18)
    todos_contactos = contenedor.servicio_contactos.buscar()
    chips_contactos = ft.Row(
        wrap=True,
        spacing=6,
        controls=[
            ft.Chip(
                label=ft.Text(c.nombre, size=12),
                selected=c.id in estado["contactos_sel"],
                on_select=lambda e, cid=c.id: (
                    estado["contactos_sel"].add(cid)
                    if e.control.selected
                    else estado["contactos_sel"].discard(cid)
                ),
            )
            for c in todos_contactos
        ],
    )

    # Banner de error / aviso de choque de eventos (RN-11)
    texto_alerta = ft.Text("", size=12.5, color=ft.Colors.ON_ERROR_CONTAINER)
    banner_alerta = ft.Container(
        visible=False,
        padding=10,
        border_radius=8,
        bgcolor=ft.Colors.ERROR_CONTAINER,
        content=ft.Row(
            spacing=8,
            controls=[
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.ON_ERROR_CONTAINER),
                ft.Container(expand=True, content=texto_alerta),
            ],
        ),
    )

    async def _guardar(_: ft.Event) -> None:
        banner_alerta.visible = False
        try:
            es_todo = bool(todo_el_dia_sw.value)
            inicio_utc = combinar_local_a_utc(
                estado["fecha_inicio"],
                time(0, 0) if es_todo else estado["hora_inicio"],
            )
            fin_utc = (
                None
                if es_todo or not con_hora_fin_sw.value
                else combinar_local_a_utc(estado["fecha_fin"], estado["hora_fin"])
            )

            regla: ReglaRecurrencia | None = None
            if frec_dd.value:
                regla = ReglaRecurrencia(
                    frecuencia=TipoFrecuencia(frec_dd.value),
                    intervalo=int(intervalo_field.value or "1"),
                    dias_semana=tuple(sorted(estado["dias_semana"]))
                    if frec_dd.value == TipoFrecuencia.SEMANAL.value
                    else (),
                )

            eliminar_rec = rec_dd.value == ""
            antelacion_min: int | None = None
            if rec_dd.value == "CUSTOM":
                antelacion_min = int(rec_custom_field.value or "0")
            elif rec_dd.value:
                antelacion_min = int(rec_dd.value)

            cat_id = UUID(cat_dd.value) if cat_dd.value else None
            sub_id = UUID(sub_dd.value) if sub_dd.value else None

            if evento_editar is None:
                await contenedor.servicio_eventos.crear_evento(
                    titulo=titulo_field.value or "",
                    fecha_inicio=inicio_utc,
                    fecha_fin=fin_utc,
                    todo_el_dia=es_todo,
                    descripcion=desc_field.value or None,
                    ubicacion=ubic_field.value or None,
                    categoria_id=cat_id,
                    subcategoria_id=sub_id,
                    contacto_ids=list(estado["contactos_sel"]),
                    recurrencia=regla,
                    recordatorio_antelacion_min=antelacion_min,
                )
            else:
                await contenedor.servicio_eventos.editar_evento(
                    evento_editar.id,
                    titulo=titulo_field.value or "",
                    fecha_inicio=inicio_utc,
                    fecha_fin=fin_utc,
                    actualizar_fecha_fin=True,
                    todo_el_dia=es_todo,
                    descripcion=desc_field.value or None,
                    ubicacion=ubic_field.value or None,
                    categoria_id=cat_id,
                    subcategoria_id=sub_id,
                    actualizar_clasificacion=True,
                    contacto_ids=list(estado["contactos_sel"]),
                    recurrencia=regla,
                    actualizar_recurrencia=True,
                    recordatorio_antelacion_min=antelacion_min,
                    eliminar_recordatorio=eliminar_rec,
                )

            page.pop_dialog()
            await on_guardado()
        except ChoqueEventosError as choque:
            hora_txt = (
                formatear_fecha_hora(choque.inicio_conflicto, formato_24h=ajustes.formato_24h)
                if choque.inicio_conflicto
                else ""
            )
            texto_alerta.value = (
                f"Choque de eventos: '{choque.titulo_conflicto}' ({hora_txt}). "
                "Ajusta el horario para guardar."
            )
            banner_alerta.visible = True
            page.update()
        except (DominioError, ValueError) as exc:
            texto_alerta.value = str(exc)
            banner_alerta.visible = True
            page.update()

    dialogo = ft.AlertDialog(
        modal=True,
        title=ft.Text("Editar evento" if evento_editar else "Nuevo evento"),
        content=ft.Container(
            width=480,
            height=500,
            content=ft.Column(
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    banner_alerta,
                    titulo_field,
                    todo_el_dia_sw,
                    ft.Row(spacing=8, wrap=True, controls=[btn_fecha_ini, btn_hora_ini]),
                    con_hora_fin_sw,
                    fila_fin,
                    ubic_field,
                    desc_field,
                    ft.Row(spacing=6, controls=[cat_dd, btn_add_cat]),
                    ft.Row(spacing=6, controls=[sub_dd, btn_add_sub]),
                    ft.Row(spacing=8, controls=[frec_dd, intervalo_field]),
                    chips_dias,
                    rec_dd,
                    rec_custom_field,
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

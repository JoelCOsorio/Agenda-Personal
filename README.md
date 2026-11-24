# Agenda Personal y Académica Multiplataforma

Aplicación de gestión personal y académica desarrollada con **Python**, **Flet 1.x (Material 3)** y **SQLite 3 (WAL)**, orientada a **Android, Windows y Linux**, con enfoque en un **Motor Unificado de Notificaciones nativas**.

---

## Características Principales

* **Módulo de Agenda:** CRUD de eventos, eventos de todo el día, eventos recurrentes (diarios, semanales por día `LU..DO`, mensuales y anuales), validación estricta contra choque de horarios, historial de eventos pasados y 4 vistas de calendario (**Día, Semana, Mes y Año**).
* **Motor Unificado de Notificaciones (Agenda y Tareas):**
  * 1 recordatorio por evento o tarea configurable hasta **7 días antes**.
  * Reprogramación automática al editar fechas/horas, cancelación automática al eliminar ítems o completar tareas, y avance automático hacia la siguiente ocurrencia en eventos recurrentes.
  * Detección y bandeja de **notificaciones perdidas** cuando el dispositivo estuvo apagado.
  * Acciones rápidas (*Posponer*, *Marcar como visto*, *Completar tarea*) con degradación elegante según soporte del SO.
  * Adaptadores dedicados para **Android** (`AlarmManager` + `BootReceiver`), **Windows** (*Windows Toast*) y **Linux** (planificador `asyncio` + worker opcional `systemd --user` vía D-Bus).
* **Módulo de Tareas:** Independiente del calendario, con fechas límite, prioridades, estados (*Pendiente, En progreso, Completada*), filtros y recordatorios integrados.
* **Módulo de Contactos:** Directorio con búsqueda rápida, etiquetas, vinculación segura con eventos/tareas (sin borrado en cascada) y acciones externas según plataforma (`mailto:` en los 3 SO y `tel:` exclusivo de Android).
* **Organización y Ajustes:** Categorías y subcategorías (2 niveles) creables en línea, tema Claro/Oscuro en vivo, formato 12h/24h, primer día de la semana, intervalo de *Posponer* y diagnóstico de permisos del SO.

---

## Arquitectura y Documentación

El proyecto sigue **Puertos y Adaptadores (Clean Architecture)** + principios **SOLID**, con `UUIDv4` y marcas temporales UTC preparadas para sincronización futura:

```text
src/agenda_app/
├── domain/          # Entidades, enums, excepciones y reglas puras (cero dependencias)
├── application/     # Puertos (Protocol), servicios y MotorNotificaciones / StartupReconciler
├── infrastructure/  # SQLite WAL, migraciones, adaptadores Android/Windows/Linux y worker D-Bus
├── presentation/    # UI Material 3 en Flet 1.x (NavigationBar móvil / NavigationRail escritorio)
└── container.py     # Composition Root (Inyección de Dependencias)
```

Documentación de ingeniería disponible en `docs/`:
* Propuesta del proyecto: [`docs/propuesta/propuesta_proyecto.md`](docs/propuesta/propuesta_proyecto.md)
* Recolección de datos y entrevistas: [`docs/ing_requerimientos/ingenieria_requerimientos.md`](docs/ing_requerimientos/ingenieria_requerimientos.md)
* Especificación Formal (ERS): [`docs/ing_requerimientos/especificacion_formal_requerimientos.md`](docs/ing_requerimientos/especificacion_formal_requerimientos.md)
* Diseño, Diagrama de Clases y Modelo ER (Mermaid + SVG): [`docs/diseno/diseno_y_modelado_datos.md`](docs/diseno/diseno_y_modelado_datos.md)
* Diseño del Motor de Notificaciones: [`docs/diseno/diseno_motor_notificaciones.md`](docs/diseno/diseno_motor_notificaciones.md)
* Arquitectura Flet y Esquema SQL: [`docs/diseno/arquitectura_flet.md`](docs/diseno/arquitectura_flet.md) · [`docs/diseno/esquema_inicial.sql`](docs/diseno/esquema_inicial.sql)

---

## Instalación y Ejecución (`uv`)

```bash
# 1. Instalar dependencias en .venv
uv sync

# 2. Ejecutar la aplicación en escritorio
uv run flet run
```

---

## Pruebas Automatizadas

```bash
# Ejecutar suite unitaria, de contrato multiplataforma e integración SQLite WAL
uv run pytest tests/unit tests/integration -v

# Smoke test end-to-end con Flutter/Flet
uv run flet test
```

---

## Notificaciones en Segundo Plano en Linux (`systemd --user`)

En Linux, D-Bus no agenda notificaciones a futuro con la app cerrada; para habilitar alertas en segundo plano puedes ejecutar el worker ligero incluido (que comparte el mismo SQLite en modo `WAL`):

```bash
# Ejecución manual
PYTHONPATH=src uv run python -m agenda_app.infrastructure.notifications.linux_worker

# Generar archivo de servicio systemd --user
PYTHONPATH=src uv run python -c "from pathlib import Path; from agenda_app.infrastructure.notifications.linux_worker import generar_unidad_systemd; print(generar_unidad_systemd(Path.cwd()))"
```

---

## Empaquetado por Plataforma

```bash
# Android (APK)
uv run flet build apk -v

# Linux
uv run flet build linux -v

# Windows (ejecutar en entorno Windows)
uv run flet build windows -v
```

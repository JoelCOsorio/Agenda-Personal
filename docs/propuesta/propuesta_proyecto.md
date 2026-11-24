# Propuesta del Proyecto: Agenda Personal y Académica Multiplataforma

**Versión:** 1.2 (Consolidada tras cierre de Elicitación)  
**Tipo de Proyecto:** Personal y Académico  
**Stack Tecnológico Definido:** Python + **Flet**  
**Plataformas Objetivo:** Android, Windows y Linux  
**Fecha:** 23 de noviembre de 2026  

---

## 1. Resumen Ejecutivo y Justificación

En la vida diaria, tanto personal como académica, es común dispersar compromisos, recordatorios, entregas pendientes e información de contacto en distintas aplicaciones que frecuentemente dependen de servicios propietarios en la nube o carecen de integración real con las necesidades del usuario.

Este proyecto propone el diseño y desarrollo en **Flet (Python)** de una aplicación de **Agenda Personal y Académica** enfocada en tres módulos centrales —**Agenda**, **Tareas** y **Contactos**—, apoyados por un **motor unificado de notificaciones locales** y un sistema ágil de **categorías y subcategorías**, operando en **Android, Windows y Linux**. El núcleo diferenciador del proyecto es el tratamiento directo y confiable de las **APIs nativas de notificación** de cada sistema operativo objetivo, garantizando alertas oportunas (incluyendo detección de notificaciones perdidas y acciones rápidas donde el SO lo permita).

---

## 2. Objetivos

### 2.1 Objetivo General
Diseñar y desarrollar con **Flet** una aplicación multiplataforma (Android, Windows y Linux) de gestión personal y académica integrada por los módulos de Agenda, Tareas y Contactos, cuya funcionalidad principal garantice la programación, entrega y recuperación confiable de notificaciones locales mediante las APIs nativas de cada sistema operativo, bajo una arquitectura desacoplada preparada para evolucionar hacia sincronización futura.

### 2.2 Objetivos Específicos
1. **Aplicar Ingeniería de Requerimientos:** Recolectar información directa del usuario, descubrir y formalizar los requerimientos funcionales/no funcionales y establecer las reglas de negocio que rigen los datos y notificaciones.
2. **Construir un Motor Unificado de Notificaciones Multiplataforma:** Integrar las APIs nativas de notificación de **Android**, **Windows** y **Linux** para atender tanto eventos como tareas, soportando rangos amplios de antelación (hasta 1 semana), detección de alertas perdidas cuando el equipo estuvo apagado y acciones rápidas según las capacidades de cada SO.
3. **Desarrollar el Módulo de Agenda:** Implementar la gestión completa de eventos (CRUD, todo el día, recurrencia, historial), vistas temporales (día, semana, mes, año y vista calendario) y vinculación con categorías/subcategorías y contactos.
4. **Desarrollar el Módulo de Tareas:** Proveer un módulo independiente para administrar tareas con fecha límite, prioridad, estado, categoría/subcategoría, contactos vinculados y recordatorios integrados al motor de notificaciones.
5. **Desarrollar el Módulo de Contactos:** Incorporar un directorio con soporte para vinculación con eventos/tareas y acciones externas dependientes de plataforma (gestor de correos en Android/Windows/Linux y app de llamadas exclusivamente en Android).
6. **Garantizar una Arquitectura Desacoplada y Extensible:** Operar inicialmente de forma independiente por dispositivo, pero estructurando capas, repositorios e identificadores únicos para facilitar una futura sincronización multidispositivo sin reescribir la lógica de negocio.

---

## 3. Alcance y Límites del Proyecto

### 3.1 Alcance (Qué SÍ incluye)
* **Módulo de Agenda:**
  * Creación, consulta, modificación y eliminación de eventos (incluyendo eventos de todo el día y eventos recurrentes), con validación estricta contra solapamientos y aviso de choque de horarios.
  * Consulta de eventos futuros y pasados (historial).
  * Visualización en formatos de día, semana, mes y año, incluyendo interfaz estilo calendario.
* **Motor Unificado de Notificaciones (Agenda y Tareas):**
  * Un recordatorio configurable por evento o tarea (hora de inicio/límite, tiempo previo predefinido o personalizado hasta **1 semana antes**, validando disponibilidad temporal).
  * Cancelación automática al eliminar ítems o completar tareas, y reprogramación automática al modificar fechas/horas o reactivar ítems.
  * Detección y despliegue de notificaciones perdidas/vencidas cuando el dispositivo haya estado apagado.
  * Acciones rápidas desde la notificación (ej. posponer con intervalo configurable, marcar como visto) en las plataformas cuya API nativa lo permita.
  * Integración con APIs nativas de notificación para Android, Windows y Linux.
* **Módulo de Tareas (módulo propio independiente del calendario):**
  * Gestión CRUD de tareas con título, descripción, fecha límite, prioridad, estado, categoría/subcategoría y recordatorio.
* **Módulo de Contactos:**
  * Gestión CRUD de contactos (nombre, teléfono, correo, notas, categoría/etiqueta).
  * Vinculación de contactos con eventos y tareas (desvinculación segura sin borrado en cascada).
  * Lanzamiento de aplicaciones externas del SO según plataforma: cliente de correo (`mailto:`) en Android, Windows y Linux; marcador telefónico (`tel:`) únicamente en Android.
* **Organización Transversal (Categorías y Subcategorías):**
  * Creación ágil de categorías principales (ej. *Universidad, Personal, Trabajo*) y subcategorías (ej. materias/asignaturas o áreas específicas).
* **Configuración / Ajustes del Sistema:**
  * Panel de ajustes personalizables para parametrizar comportamientos clave de la aplicación (tiempo de *posponer*, recordatorio predeterminado, formato de fecha/hora, primer día de la semana, tema visual y preferencias de notificación por SO).
* **Persistencia Local Preparada para el Futuro:**
  * Almacenamiento local independiente por dispositivo (*offline-first*), diseñado con bajo acoplamiento para admitir sincronización futura.

### 3.2 Límites (Qué NO incluye en esta versión)
* **Sincronización en tiempo real entre dispositivos:** En esta versión cada instalación (Android, Windows, Linux) opera con su base de datos local independiente (solo se deja preparada la arquitectura para el futuro).
* **Múltiples recordatorios por un mismo ítem:** En esta versión cada evento o tarea admite un único recordatorio activo.
* **Plataformas excluidas:** No se contempla soporte ni empaquetado para **iOS**, **macOS** ni versión **Web**.
* **Multiusuario y colaboración:** Uso estrictamente individual; sin cuentas compartidas ni colaboración en tiempo real.
* **Integración con calendarios de terceros:** Sin sincronización bidireccional con Google Calendar, Outlook ni iCloud.
* **Cliente interno de comunicación:** La aplicación delega correo y llamadas a apps externas del SO; no envía correos ni realiza llamadas internamente, y **no ofrece acción de llamadas en Windows ni Linux**.

---

## 4. Restricciones

### 4.1 Restricción Tecnológica Principal (Obligatoria)
* **Framework obligatorio — Flet (Python):** Por razones de fuerza mayor del proyecto, el desarrollo debe realizarse utilizando **Flet**. Toda la arquitectura de interfaz, persistencia e integración con las APIs del sistema operativo deberá diseñarse alrededor del ecosistema Python/Flet y sus mecanismos de empaquetado (`flet build`).

### 4.2 Restricciones de Plataforma y APIs de Notificación
* **Android (con Flet):**
  * Gestión de permisos `POST_NOTIFICATIONS` (Android 13+), canales de notificación (`NotificationChannel`) y alarmas exactas (`AlarmManager` / `SCHEDULE_EXACT_ALARM`).
  * Restricciones de ejecución en segundo plano (*Doze Mode* y suspensión del runtime de Python cuando la app está cerrada): requerirá evaluar puentes nativos/extensiones de Flet o servicios Android nativos para disparar notificaciones y acciones rápidas de forma confiable con la app cerrada.
* **Windows:**
  * Integración con *Windows Toast Notifications* (WinRT / `AppUserModelID`), que sí soporta acciones rápidas interactivas en notificaciones.
  * Necesidad de ejecución residente en segundo plano (bandeja del sistema o proceso de fondo) para disparar alertas con la ventana cerrada y recuperar notificaciones perdidas al reiniciar.
* **Linux:**
  * Integración con `org.freedesktop.Notifications` vía D-Bus / `libnotify` (donde el soporte de acciones rápidas depende de las capacidades `actions` del demonio de notificaciones del entorno de escritorio: GNOME, KDE, Dunst, etc.).
  * Requerimiento de proceso residente o servicio de usuario (`systemd --user`) para disparar y recuperar alertas locales.
* **Capacidades diferenciadas por SO en Contactos:**
  * Las acciones de llamada telefónica (`tel:`) están restringidas a Android; en Windows y Linux deben ocultarse o deshabilitarse automáticamente según detección de plataforma.

### 4.3 Restricciones Arquitectónicas y Operativas
* **Desacoplamiento obligatorio:** La lógica de dominio debe aislarse de la capa de almacenamiento local y de las implementaciones específicas de notificación por SO (patrón Adaptador / Repositorio) para permitir sincronización futura sin refactorizaciones destructivas.
* **Recurso humano y privacidad:** Desarrollo individual en contexto académico y personal; todos los datos residen localmente bajo control exclusivo del usuario.

---

## 5. Usuarios y Partes Interesadas (Stakeholders)

| Rol | Perfil | Necesidades Principales | Nivel de Interacción |
| :--- | :--- | :--- | :--- |
| **Usuario Final Principal** *(Stakeholder primario / Cliente)* | Estudiante y usuario individual con actividades personales y académicas en Android, Windows y Linux. | Organizar eventos y tareas por categorías/subcategorías, recibir notificaciones confiables (incluso si el equipo estuvo apagado), gestionar contactos vinculados y lanzar apps externas de correo/llamada. | Diario y directo con toda la aplicación. |
| **Evaluador Académico** *(Stakeholder secundario)* | Docente o revisor del proyecto académico. | Evaluar la calidad de la propuesta, el rigor de la ingeniería de requerimientos (elicitación, reglas de negocio) y la solución técnica construida con Flet. | Revisión por hitos y entregables. |

---

## 6. Riesgos Identificados (Actualizados)

| ID | Riesgo | Impacto | Estrategia de Mitigación |
| :--- | :--- | :--- | :--- |
| **R-01** | Limitaciones de **Flet** para programar alarmas exactas, ejecutar código en segundo plano y recibir callbacks de acciones rápidas en Android cuando la app está cerrada. | **Crítico** | Realizar una prueba de concepto (*PoC*) temprana de notificaciones nativas en Android con Flet (evaluando extensiones Flet/Flutter nativas o APIs nativas vía puente) antes de construir toda la UI. |
| **R-02** | Soporte desigual de acciones rápidas en notificaciones entre entornos Linux (ej. entornos sin soporte de botones D-Bus `actions`). | **Medio** | Consultar capacidades del servidor de notificaciones (`GetCapabilities` en D-Bus) y aplicar degradación elegante a notificación estándar cuando no haya soporte. |
| **R-03** | Complejidad de construir 4 vistas de calendario (día, semana, mes, año) manualmente en Flet al no contar con un widget de calendario completo nativo. | **Medio** | Diseñar componentes modulares reutilizables en Flet e implementar las vistas de forma incremental (Mensual + Diaria primero, luego Semanal y Anual). |
| **R-04** | Acoplamiento temprano al almacenamiento local que dificulte agregar sincronización en el futuro. | **Medio** | Aplicar Arquitectura Limpia / Puertos y Adaptadores, identificadores `UUIDv4` y timestamps `updated_at` desde el diseño inicial de base de datos. |

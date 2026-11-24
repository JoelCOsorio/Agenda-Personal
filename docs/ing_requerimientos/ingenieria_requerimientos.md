# Ingeniería de Requerimientos: Recolección de Datos y Descubrimiento Inicial

**Proyecto:** Agenda Personal y Académica Multiplataforma (Flet)  
**Fase Actual:** Elicitación (Recolección de Datos) y Descubrimiento de Requerimientos Iniciales y Reglas de Negocio  
**Estado:** Completada (Rondas 1 y 2 finalizadas y validadas con el usuario)  
**Fecha de cierre:** 23 de noviembre de 2026  

---

## 1. Estrategia de Recolección de Datos (Elicitación)

Para descubrir las necesidades reales, casos borde y reglas de negocio del sistema, se aplicaron dos técnicas complementarias:

1. **Análisis Documental Preliminar:** Revisión de las notas iniciales aportadas por el usuario en [`docs/requerimientos.md`](../requerimientos.md) y la definición de alcance de [`docs/propuesta/propuesta_proyecto.md`](../propuesta/propuesta_proyecto.md).
2. **Entrevista Semi-Estructurada Iterativa (2 Rondas) con el Usuario Final:** Entrevista directa al usuario/stakeholder organizada por bloques temáticos (Plataformas, Agenda y Notificaciones, Tareas, Contactos, Organización Académica, Configuración y Reglas de Negocio).

---

## 2. Registro de Entrevistas

### 2.1 Ronda 1 — Exploración General (23/11/2026)
**Entrevistado:** Usuario Final / Stakeholder Principal  
**Modalidad:** Entrevista escrita semi-estructurada  

| # | Pregunta / Tema | Respuesta del Usuario (Resumen Fiel) | Impacto en Requerimientos / Reglas |
| :--- | :--- | :--- | :--- |
| **P1** | Uso entre dispositivos (Android, Windows, Linux) y sincronización. | Por ahora mantenerlos independientes, pero preparar el escenario a futuro evitando el acoplamiento. | Define arquitectura desacoplada (repositorios, UUIDs, timestamps) sin sincronización activa en v1 (`RNF-01`, `RN-10`). |
| **P2** | Elección del stack tecnológico (Flet vs. Flutter). | Por razones de fuerza mayor, hay que usar **Flet**. | Restricción tecnológica obligatoria (`RNF-02`); eleva criticidad del adaptador de notificaciones nativas en Flet. |
| **P3** | Notificaciones: cantidad, perdidas por apagado y acciones rápidas. | Por ahora solo **1 recordatorio** por ítem, con rango amplio previo (hasta **1 semana**, verificando disponibilidad). Debe mostrarse como **perdida** si el equipo estaba apagado. Sí debe tener **acciones rápidas** si lo permite la API del SO. | Consolida motor unificado de notificaciones (`REQ-NT-01` a `REQ-NT-05`, `RN-03`, `RN-05`, `RN-06`). |
| **P4** | Campos de eventos, recurrencia, todo el día y solapamiento. | Confirma los elementos planteados de ejemplo (campos obligatorios título y fecha/hora inicio; opcionales fin, descripción, ubicación, categoría/color; eventos recurrentes y de todo el día). | Consolida estructura de eventos (`REQ-AG-01` a `REQ-AG-05`). Solapamiento precisado en Ronda 2. |
| **P5** | Módulo de Tareas: atributos, notificaciones y relación con calendario. | Atributos: título, descripción, fecha límite, prioridad, estado, categoría, recordatorio. Sí deben enviar notificaciones usando el **mismo sistema de eventos**. Deben **vivir en su propio módulo** (separadas del calendario). | Consolida módulo de Tareas y reutilización del motor de notificaciones (`REQ-TA-01` a `REQ-TA-04`, `RN-07`). |
| **P6** | Datos a guardar en Contactos. | Confirma los atributos mencionados (nombre, teléfono, correo, notas, categoría/etiqueta como *Profesor, Compañero, Familia, Trabajo*). | Consolida ficha de contacto (`REQ-CO-01`, `REQ-CO-02`). |
| **P7** | Vinculación de contactos y acciones externas (llamar / correo). | Sí debe poder vincularse a eventos/tareas. Debe permitir lanzar apps externas del SO: "llamar" abre la app de llamadas y "correo" abre el gestor de correos, distinguiendo por plataforma (en Linux y Windows no funcionará la llamada). | Agrega vinculación e intents externos condicionados por SO (`REQ-CO-03`, `REQ-CO-04`, `RN-08`). |
| **P8** | Organización académica/personal: categorías vs. materias. | Ambos: categorías y **subcategorías**, y que se puedan crear fácilmente. | Agrega módulo transversal de Categorías y Subcategorías (`REQ-CA-01`, `REQ-CA-02`, `RN-09`). |
| **P9** | Validación de reglas de negocio base (`RN-01` a `RN-04`). | Confirma las 4 reglas propuestas. | `RN-01`, `RN-02`, `RN-03` y `RN-04` confirmadas. |

### 2.2 Ronda 2 — Cierre de Casos Borde y Reglas de Negocio (23/11/2026)

| # | Caso Borde / Tema | Respuesta del Usuario (Resumen Fiel) | Impacto en Requerimientos / Reglas |
| :--- | :--- | :--- | :--- |
| **P10** | Solapamiento de eventos (`RN-11`). | **No puede existir solapamiento de eventos**; debe mostrar un aviso de choque de eventos. | Regla estricta bloqueante con aviso de colisión (`REQ-AG-06`, `RN-11`). |
| **P11** | Completar tareas y reprogramación de horarios (`RN-12`). | Sí, al completar una tarea se cancela el recordatorio. Además, al modificar horas de inicio de un evento o tarea, o volver a reprogramar, se deben **volver a establecer los recordatorios**. | Amplía ciclo de vida de recordatorios (`RN-02`, `RN-12`). |
| **P12** | Eliminación de contactos o categorías vinculadas (`RN-13`). | Sí, se debe desvincular el contacto (sin borrar los eventos/tareas). | Confirma integridad sin borrado en cascada (`RN-13`). |
| **P13** | Intervalo de "Posponer" y personalización (`RN-14`). | Configurable en ajustes; muchas opciones de la aplicación deben poderse configurar desde ajustes. | Descubre el módulo transversal de **Ajustes/Configuración** (`REQ-CF-01`, `REQ-CF-02`, `RN-14`). |

---

## 3. Requerimientos Descubiertos (Línea Base Consolidada)

### 3.1 Módulo de Agenda (Eventos)
| ID | Descripción del Requerimiento | Prioridad | Estado |
| :--- | :--- | :--- | :--- |
| **REQ-AG-01** | El usuario podrá crear, consultar, modificar y eliminar eventos. | Alta | Confirmado |
| **REQ-AG-02** | Un evento registrará como obligatorios título y fecha/hora de inicio, y como opcionales fecha/hora de fin, descripción, ubicación, categoría/subcategoría, color, recordatorio y contactos vinculados. | Alta | Confirmado |
| **REQ-AG-03** | El sistema soportará eventos de **todo el día** y **eventos recurrentes** (repetición periódica para horarios de clase, compromisos periódicos o fechas anuales). | Media-Alta | Confirmado |
| **REQ-AG-04** | El usuario podrá consultar tanto eventos futuros como eventos pasados (historial). | Alta | Confirmado |
| **REQ-AG-05** | El usuario dispondrá de vistas de eventos en formatos de **día, semana, mes y año**, incluyendo una **vista estilo calendario**. | Alta | Confirmado |
| **REQ-AG-06** | El sistema validará colisiones de horario al crear o editar eventos, **impidiendo el solapamiento** y mostrando un **aviso claro de choque de eventos**. | Alta | Confirmado |

### 3.2 Motor Unificado de Notificaciones (Transversal: Agenda y Tareas)
| ID | Descripción del Requerimiento | Prioridad | Estado |
| :--- | :--- | :--- | :--- |
| **REQ-NT-01** | El sistema implementará un único motor de notificaciones reutilizable tanto para **eventos** como para **tareas**. | Crítica | Confirmado |
| **REQ-NT-02** | El usuario podrá configurar **1 recordatorio** por evento o tarea: a la hora exacta, en intervalos previos predefinidos o con un tiempo personalizado de hasta **1 semana (7 días) de antelación**, validando disponibilidad temporal. | Crítica | Confirmado |
| **REQ-NT-03** | El motor interactuará con las APIs nativas de notificación de **Android**, **Windows** y **Linux** mediante adaptadores específicos por plataforma. | Crítica | Confirmado |
| **REQ-NT-04** | Si el dispositivo estuvo apagado o el servicio no pudo disparar una alerta a tiempo, el sistema detectará y mostrará la notificación como **perdida/vencida** al reanudarse. | Alta | Confirmado |
| **REQ-NT-05** | Las notificaciones incluirán **acciones rápidas** (ej. *Posponer* usando el tiempo configurado en ajustes, *Marcar como visto/completado*) siempre que la API del sistema operativo y el entorno actual lo soporten. | Alta | Confirmado |
| **REQ-NT-06** | Ante cambios de fecha/hora, reprogramación o reactivación de un evento o tarea, el motor deberá recalcular y volver a registrar el recordatorio correspondiente en la API del SO; ante eliminación o completado de tarea, deberá cancelarlo. | Crítica | Confirmado |

### 3.3 Módulo de Tareas
| ID | Descripción del Requerimiento | Prioridad | Estado |
| :--- | :--- | :--- | :--- |
| **REQ-TA-01** | El módulo de tareas operará en su propia sección/vista independiente del calendario de la agenda. | Alta | Confirmado |
| **REQ-TA-02** | El usuario podrá crear, consultar, modificar y eliminar tareas. | Alta | Confirmado |
| **REQ-TA-03** | Cada tarea incluirá: título, descripción, fecha límite, prioridad, estado (*Pendiente, En progreso, Completada*), categoría/subcategoría, recordatorio y contactos vinculados (opcionales). | Alta | Confirmado |
| **REQ-TA-04** | Las tareas podrán programar y reprogramar notificaciones haciendo uso del mismo motor unificado de notificaciones (`REQ-NT-01` a `REQ-NT-06`). | Alta | Confirmado |

### 3.4 Módulo de Contactos
| ID | Descripción del Requerimiento | Prioridad | Estado |
| :--- | :--- | :--- | :--- |
| **REQ-CO-01** | El usuario podrá crear, consultar, modificar y eliminar contactos. | Alta | Confirmado |
| **REQ-CO-02** | Cada contacto registrará: nombre, teléfono, correo electrónico, notas y categoría/etiqueta (ej. *Profesor, Compañero, Familia, Trabajo*). | Alta | Confirmado |
| **REQ-CO-03** | El usuario podrá **vincular contactos** a eventos de la agenda y a tareas. | Media-Alta | Confirmado |
| **REQ-CO-04** | Desde el detalle de un contacto, el usuario podrá invocar aplicaciones externas del sistema operativo: **enviar correo** (`mailto:`) en Android, Windows y Linux, y **llamar** (`tel:`) exclusivamente en Android. | Media-Alta | Confirmado |

### 3.5 Módulo Transversal de Categorías y Subcategorías
| ID | Descripción del Requerimiento | Prioridad | Estado |
| :--- | :--- | :--- | :--- |
| **REQ-CA-01** | El sistema permitirá gestionar **categorías principales** (ej. *Universidad, Personal, Trabajo*) y **subcategorías** asociadas (ej. materias/asignaturas específicas o subáreas). | Media-Alta | Confirmado |
| **REQ-CA-02** | La creación de nuevas categorías y subcategorías deberá ser rápida y accesible (incluso desde los formularios de creación de eventos o tareas). | Media | Confirmado |

### 3.6 Módulo Transversal de Configuración / Ajustes
| ID | Descripción del Requerimiento | Prioridad | Estado |
| :--- | :--- | :--- | :--- |
| **REQ-CF-01** | El sistema dispondrá de una sección dedicada de **Ajustes/Configuración** persistente en almacenamiento local. | Media-Alta | Confirmado |
| **REQ-CF-02** | El usuario podrá parametrizar desde Ajustes el comportamiento general del sistema, incluyendo: tiempo de *Posponer* (*snooze*) en notificaciones, antelación predeterminada para nuevos recordatorios, preferencias de alertas perdidas/sonido, formato de hora (12h/24h), primer día de la semana, vista inicial de calendario y tema visual (claro/oscuro). | Media-Alta | Confirmado |

### 3.7 Requerimientos No Funcionales y Arquitectónicos Descubiertos
| ID | Descripción | Estado |
| :--- | :--- | :--- |
| **RNF-01** | **Desacoplamiento para sincronización futura:** Las instancias en Android, Windows y Linux operarán de forma independiente con almacenamiento local, pero el diseño debe desacoplar la lógica de dominio del repositorio de datos y usar identificadores únicos y metadatos temporales para facilitar sincronización futura. | Confirmado |
| **RNF-02** | **Framework obligatorio:** La aplicación se desarrollará sobre **Flet (Python)** con compilación/empaquetado orientado a Android, Windows y Linux. | Confirmado |
| **RNF-03** | **Detección de plataforma y degradación elegante:** El sistema debe detectar el SO en ejecución para habilitar/deshabilitar capacidades dependientes de plataforma (llamadas telefónicas y acciones rápidas en notificaciones) sin generar errores. | Confirmado |

---

## 4. Reglas de Negocio Consolidadas (RN)

Todas las reglas listadas a continuación fueron descubiertas y validadas con el usuario durante las Rondas 1 y 2:

| ID | Nombre | Definición Formal de la Regla de Negocio | Estado |
| :--- | :--- | :--- | :--- |
| **RN-01** | Coherencia temporal del evento | En todo evento con rango horario definido (que no sea de "todo el día"), la fecha/hora de finalización debe ser mayor o igual a la fecha/hora de inicio. | Confirmada |
| **RN-02** | Sincronía total ítem–notificación | Toda modificación de fecha/hora de inicio o límite, reprogramación o cambio en la configuración de recordatorio de un evento o tarea debe **cancelar la alerta previa y volver a establecer la nueva notificación** en la API del SO. Si el ítem se elimina, su notificación pendiente debe cancelarse de inmediato. | Confirmada |
| **RN-03** | Límite y validez temporal del recordatorio | Cada evento o tarea admite como máximo **1 recordatorio activo** en esta versión, configurable desde la hora exacta hasta un máximo de **1 semana (7 días) antes**. El instante resultante de disparo debe ser futuro y validado contra la disponibilidad/restricciones de la API del SO. | Confirmada |
| **RN-04** | Conservación de historial | Los eventos pasados no se eliminan automáticamente al vencer; permanecen consultables en el historial hasta que el usuario los elimine explícitamente. | Confirmada |
| **RN-05** | Gestión de notificaciones perdidas | Toda notificación programada cuya hora haya transcurrido mientras el equipo estaba apagado o el proceso inactivo debe ser detectada al reiniciar/abrir la aplicación y presentada al usuario como **notificación perdida/vencida** hasta que sea atendida. | Confirmada |
| **RN-06** | Degradación elegante de acciones rápidas | Las acciones rápidas dentro de una notificación (ej. *Posponer*, *Marcar como visto*) solo se adjuntan si la API nativa del SO y entorno actual las soportan; en caso contrario, se emite una notificación estándar sin error. | Confirmada |
| **RN-07** | Separación modular Agenda vs. Tareas | Las tareas residen exclusivamente en el Módulo de Tareas y no se mezclan visualmente dentro de las vistas del calendario de la Agenda, aunque comparten el motor de notificaciones, categorías y contactos. | Confirmada |
| **RN-08** | Restricción de acciones externas por plataforma | La acción de abrir el gestor de correo (`mailto:`) estará disponible en **Android, Windows y Linux** siempre que el contacto tenga un correo válido. La acción de abrir la app de llamadas (`tel:`) estará disponible **únicamente en Android** (si el contacto posee teléfono) y permanecerá oculta/deshabilitada en Windows y Linux. | Confirmada |
| **RN-09** | Jerarquía de Categorías y Subcategorías | Una subcategoría siempre pertenece a una categoría padre (estructura de 2 niveles: *Categoría $\rightarrow$ Subcategoría* para mantener creación rápida). Un evento o tarea puede clasificarse en una categoría padre o en una de sus subcategorías. | Confirmada |
| **RN-10** | Preparación para sincronización sin acoplamiento | Toda entidad persistente (evento, tarea, contacto, categoría, subcategoría, recordatorio, ajustes) debe identificarse con un `UUID` único global y mantener marcas temporales (`created_at`, `updated_at`), manteniendo el dominio desacoplado de la interfaz y del motor de almacenamiento local. | Confirmada |
| **RN-11** | Prohibición estricta de solapamiento de eventos | **No puede existir solapamiento entre eventos** en el mismo rango horario (incluyendo instancias de eventos recurrentes). Al intentar crear o reprogramar un evento cuyo intervalo colisione con otro existente, el sistema debe **impedir el guardado** y mostrar un **aviso de choque de eventos** indicando el conflicto. | Confirmada |
| **RN-12** | Ciclo de vida de recordatorios en tareas completadas y reactivadas | Cuando una tarea pasa a estado **Completada**, su recordatorio pendiente debe **cancelarse automáticamente**. Si posteriormente la tarea se reactiva (vuelve a *Pendiente* o *En progreso*) o se reprograma su fecha límite, el sistema debe volver a evaluar y establecer su recordatorio conforme a `RN-03`. | Confirmada |
| **RN-13** | Integridad referencial sin borrado en cascada | Si se elimina un contacto vinculado a eventos o tareas, estos ítems se conservan y simplemente se **desvincula el contacto**. Del mismo modo, si se elimina una categoría o subcategoría en uso, los eventos y tareas asociados se conservan pasando a estado *"Sin categoría"* (o a su categoría padre, según corresponda). | Confirmada |
| **RN-14** | Parametrización centralizada en Ajustes | Los parámetros operativos configurables (intervalo de *Posponer/Snooze*, antelación por defecto de recordatorios, formato horario, preferencias de calendario y notificaciones) deben obtenerse dinámicamente del módulo de Ajustes, contando con valores por defecto seguros al iniciar por primera vez. | Confirmada |

---

## 5. Siguiente Documento (Especificación Formal)

Los resultados de esta fase de recolección y descubrimiento han sido formalizados en:
* **[Especificación Formal de Requerimientos (ERS)](./especificacion_formal_requerimientos.md):** Contiene la descripción formal de procesos (`PROC-01` a `PROC-06`), tablas formales de Requerimientos Funcionales (`RF-01` a `RF-24`), Requerimientos No Funcionales (`RNF-01` a `RNF-10`), Reglas de Negocio (`RN-01` a `RN-14`) y Matriz de Trazabilidad.


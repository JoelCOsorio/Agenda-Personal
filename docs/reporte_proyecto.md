# Documentación: Proyecto Flet

## Atempo — Aplicación Multiplataforma de Agenda Personal y Académica

**Institución:** Universidad Juárez Autónoma de Tabasco  
**División:** División Académica de Ciencias y Tecnologías de la Información (DACYTI)  
**Asignatura:** Desarrollo de Aplicaciones Multiplataforma  
**Alumno:** Joel Cornelio  
**Matrícula:** `[Ingresar matrícula]`  
**Fecha:** 24 de noviembre de 2026  

---

## 1. Introducción

El desarrollo de aplicaciones multiplataforma representa actualmente uno de los retos más relevantes dentro de la ingeniería de software, pues exige diseñar sistemas capaces de operar con una sola base de código en ecosistemas distintos —tanto de escritorio como móviles— sin sacrificar estabilidad, experiencia de usuario ni integración con las capacidades nativas de cada sistema operativo. En el marco de la asignatura **Desarrollo de Aplicaciones Multiplataforma**, el verdadero desafío no consiste únicamente en dibujar una interfaz que se adapte a distintos tamaños de pantalla, sino en resolver las diferencias estructurales entre plataformas como **Android**, **Windows** y **Linux**: permisos en tiempo de ejecución, ejecución en segundo plano, políticas de ahorro de energía, protocolos de notificación del sistema y disponibilidad de funciones propias del dispositivo como la telefonía.

De forma paralela, en el ámbito personal y académico resulta frecuente dispersar clases, entregas, recordatorios y datos de contacto en herramientas separadas que dependen de cuentas en la nube o presentan comportamientos irregulares al sincronizar alertas entre la computadora y el teléfono. Frente a esta necesidad, el presente proyecto documenta el diseño, implementación y empaquetado de **Atempo**, una aplicación multiplataforma de gestión personal y académica desarrollada en **Python** con **Flet** (sobre el motor gráfico de Flutter) y almacenamiento local en **SQLite 3**.

La aplicación integra en un solo entorno los módulos de **Agenda**, **Tareas**, **Contactos**, **Categorías/Subcategorías** y **Ajustes**, articulados alrededor de un **Motor Unificado de Notificaciones** que interactúa con las APIs nativas de Android, Windows y Linux. Su arquitectura desacoplada permite mantener la lógica de negocio y la persistencia completamente aisladas de la interfaz y de los adaptadores de plataforma, demostrando de manera práctica los principios, patrones y herramientas abordados a lo largo de la asignatura.

---

## 2. Objetivos

### 2.1 Objetivo General
Desarrollar, probar y empaquetar una aplicación multiplataforma (Android, Windows y Linux) de agenda personal y académica con Python y Flet que integre la gestión de eventos, tareas y contactos con un sistema confiable de notificaciones locales nativas y almacenamiento autónomo en SQLite.

### 2.2 Objetivos Específicos
1. Aplicar los fundamentos de la asignatura Desarrollo de Aplicaciones Multiplataforma mediante una arquitectura desacoplada en capas (Puertos y Adaptadores y principios SOLID) que aísle la lógica de negocio de la interfaz gráfica y de las APIs particulares de Android, Windows y Linux.
2. Implementar un motor unificado de notificaciones locales capaz de atender eventos y tareas con rangos de antelación configurables de hasta 7 días, detección de alertas perdidas tras apagados, avance automático de recurrencias y degradación controlada de acciones rápidas según el sistema operativo.
3. Implementar la persistencia local en **SQLite 3** (modo WAL y claves foráneas estrictas) empleando identificadores `UUIDv4` y marcas temporales en UTC para garantizar autonomía sin conexión y facilitar una futura sincronización entre dispositivos.
4. Diseñar una interfaz gráfica responsiva basada en Material Design 3 con navegación adaptable (`NavigationRail` en escritorio y `NavigationBar` en Android), cuatro vistas de calendario (día, semana, mes y año) y conmutación en vivo entre modo claro y modo oscuro.
5. Automatizar la ejecución de pruebas unitarias e integración y la compilación de binarios nativos para Android (`.apk`), Linux y Windows mediante flujos de trabajo en GitHub Actions.

---

## 3. Requerimientos

### 3.1 Requerimientos Funcionales

1. **Gestión completa de eventos (Módulo de Agenda):** Permitir crear, consultar, modificar, reprogramar y eliminar eventos especificando título y fecha/hora de inicio obligatorios, así como fecha/hora de fin, indicador de todo el día, descripción, ubicación, clasificación, contactos vinculados y recordatorio.
2. **Eventos recurrentes e historial:** Soportar repetición diaria, semanal (por días específicos `LU` a `DO`), mensual y anual sin duplicar registros manuales, conservando los eventos vencidos en un historial consultable.
3. **Vistas temporales de calendario:** Disponer de vistas en formato de **Día**, **Semana**, **Mes** (estilo calendario interactivo con panel del día seleccionado) y **Año** (mapa de densidad mensual), además de filtros por categoría.
4. **Validación estricta anti-solapamiento:** Impedir el guardado o edición de eventos cuyo rango horario colisione con otro evento existente (incluyendo ocurrencias de eventos recurrentes), mostrando un aviso claro con el evento en conflicto. Los eventos de todo el día no bloquean compromisos con horario específico.
5. **Motor unificado de notificaciones (Agenda y Tareas):** Permitir configurar un recordatorio por evento o tarea desde la hora exacta hasta 7 días antes, validando que el disparo sea futuro. Ante modificaciones o eliminaciones, cancelar y reprogramar automáticamente en el sistema operativo.
6. **Acciones rápidas y recuperación de alertas perdidas:** Adjuntar botones de acción rápida (*Posponer*, *Marcar como visto* y *Completar tarea*) en los sistemas que lo soporten, y detectar al iniciar o reanudar la aplicación cualquier alerta vencida mientras el equipo estuvo apagado, presentándola en una bandeja dedicada.
7. **Gestión de pendientes en módulo independiente (Módulo de Tareas):** Administrar tareas en una sección separada del calendario con título, descripción, fecha límite opcional, prioridad (*Alta, Media, Baja*), estado (*Pendiente, En progreso, Completada*), filtros y sincronización automática del recordatorio al completar o reactivar la tarea.
8. **Directorio de contactos y acciones externas por plataforma (Módulo de Contactos):** Registrar, buscar, filtrar por etiqueta y vincular contactos a eventos y tareas, con apertura externa del gestor de correo (`mailto:`) en las tres plataformas y del marcador telefónico (`tel:`) exclusivamente en Android.
9. **Clasificación en dos niveles (Categorías y Subcategorías):** Crear, gestionar y asignar categorías principales (por ejemplo, *Universidad*, *Personal*, *Trabajo*) y subcategorías (materias o áreas) de forma rápida incluso desde los formularios de eventos y tareas.
10. **Configuración centralizada (Módulo de Ajustes):** Permitir modificar en vivo y persistir el intervalo de posponer (*snooze*), antelación predeterminada, sonido, aviso de alertas perdidas al iniciar, formato horario 12h/24h, primer día de la semana, vista inicial de agenda, tema claro/oscuro y diagnóstico de permisos del sistema operativo.

### 3.2 Requerimientos No Funcionales

1. **Portabilidad multiplataforma:** La aplicación opera nativamente en escritorio (**Linux** y **Windows**) y dispositivos móviles (**Android**) desde una sola base de código en Python y Flet, con compilación nativa mediante `flet build` y adaptación automática de capacidades por sistema operativo.
2. **Persistencia local y autonomía:** Toda la información reside localmente en el archivo `agenda_personal.db` bajo SQLite 3 con `PRAGMA foreign_keys = ON` y modo `WAL`, operando al 100% sin conexión a internet y sin envío de telemetría.
3. **Modularidad y mantenibilidad:** Código organizado en cuatro capas desacopladas (`domain`, `application`, `infrastructure`, `presentation`) con inversión de dependencias mediante `Protocol`, claves `UUIDv4` y marcas UTC preparadas para una futura capa de sincronización.
4. **Confiabilidad y degradación elegante:** SQLite actúa como fuente única de verdad frente a reinicios o revocación de permisos; si un entorno de escritorio Linux no soporta botones D-Bus o si Android revoca alarmas exactas, el sistema degrada sin fallos críticos.
5. **Verificabilidad automatizada:** Las reglas de negocio críticas, los contratos de los adaptadores de Android, Windows y Linux y la integridad de SQLite se verifican mediante una suite automatizada con `pytest` ejecutable sin entorno gráfico.

### 3.3 Reglas de Negocio Principales

1. **Coherencia temporal:** En todo evento con rango horario definido debe cumplirse `fecha_fin >= fecha_inicio`.
2. **Límite de recordatorio:** Cada evento o tarea admite máximo un recordatorio activo con antelación de `0` a `10,080` minutos (7 días) y fecha de disparo futura.
3. **Ciclo de vida en tareas:** Marcar una tarea como completada cancela su notificación pendiente; reactivarla o reprogramar su fecha límite restablece el recordatorio si sigue vigente.
4. **Integridad sin borrado en cascada:** Eliminar un contacto, subcategoría o categoría nunca borra los eventos ni tareas asociados; únicamente desvincula las referencias o reasigna la clasificación a `NULL`.
5. **Discriminación por plataforma en contactos:** La acción `tel:` se habilita únicamente en Android y se oculta y bloquea en Linux y Windows.

---

## 4. Herramientas Tecnológicas Utilizadas

El proyecto hace uso de herramientas modernas orientadas a portabilidad, reproducibilidad del entorno y compilación multiplataforma.

| Componente | Tecnología | Función en el proyecto |
| :--- | :--- | :--- |
| **Lenguaje principal** | Python 3.14 (`>= 3.10`) | Lógica de dominio, servicios de aplicación, tipado estático y orquestación asíncrona. |
| **Framework de UI** | Flet 1.1.3 (Flutter) | Construcción de interfaces reactivas Material Design 3 para Android, Linux y Windows desde una sola base de código. |
| **Notificaciones nativas** | `flet-notifications 1.1.3` y `desktop-notifier 6.2.0` | Programación y entrega nativa en Android (`AlarmManager`) y Windows (*Toast*); planificador `asyncio` y worker residente D-Bus en Linux. |
| **Gestor de base de datos** | SQLite 3 (modo WAL) | Persistencia local autónoma con claves `UUIDv4`, integridad referencial estricta, índices y triggers de validación. |
| **Gestor de dependencias** | `uv` (`pyproject.toml` / `uv.lock`) | Administración reproducible de entornos virtuales y bloqueo exacto de versiones de paquetes. |
| **Empaquetado y CI/CD** | `flet-cli` (`flet build`) y GitHub Actions (`flet-dev/flet-build-action@v1`) | Ejecución continua de pruebas y compilación en la nube de ejecutables para Linux, Windows y APK para Android. |
| **Pruebas automatizadas** | `pytest 9.2` y `pytest-asyncio 1.5` | Verificación unitaria de reglas de negocio, pruebas de contrato multiplataforma e integración real con SQLite. |
| **Control de versiones** | Git y GitHub | Versionado mediante ramas dedicadas por módulo, commits semánticos, integraciones `--no-ff` y publicación de Releases. |

---

## 5. Arquitectura del Sistema y Modelo de Datos

El código está estructurado siguiendo la arquitectura de **Puertos y Adaptadores (Arquitectura Limpia)** y los principios **SOLID**, garantizando que la capa de dominio no dependa de Flet ni de SQLite y que cada sistema operativo se aísle en su propio adaptador.

### 5.1 Organización de Carpetas y Módulos

| Archivo / Directorio | Función principal |
| :--- | :--- |
| `src/main.py` | Punto de entrada mínimo que inicia la aplicación Flet (`ft.run`). |
| `src/agenda_app/container.py` | *Composition Root* que ensambla repositorios, adaptadores según el SO detectado, motor de notificaciones y servicios. |
| `src/agenda_app/domain/` | Entidades (`Evento`, `ReglaRecurrencia`, `Tarea`, `Recordatorio`, `Contacto`, `Categoria`, `Subcategoria`, `ConfiguracionSistema`), enumeraciones, excepciones y reglas puras (`ExpansorRecurrencia`, `DetectorSolapamiento`, `ValidadorRecordatorio`). |
| `src/agenda_app/application/ports/` | Interfaces `Protocol` segregadas para repositorios, reloj, lanzador de URIs externos y adaptador de notificaciones. |
| `src/agenda_app/application/services/` | Casos de uso (`ServicioEventos`, `ServicioTareas`, `ServicioContactos`, `ServicioCategorias`, `ServicioAjustes`, `MotorNotificaciones` y `StartupReconciler`). |
| `src/agenda_app/infrastructure/persistence/sqlite/` | Conexión SQLite en modo WAL, migraciones versionadas (`001_initial.sql`) y los seis repositorios concretos. |
| `src/agenda_app/infrastructure/notifications/` | Adaptadores nativos para Android, Windows y Linux, fábrica por plataforma y servicio residente `linux_worker.py` para `systemd --user`. |
| `src/agenda_app/infrastructure/platform/` | Detector de plataforma y lanzador externo condicionado por SO (`mailto:` multiplataforma y `tel:` exclusivo de Android). |
| `src/agenda_app/presentation/` | Tema Material 3 (claro/oscuro), formateadores `UTC <-> Local`, shell responsivo (`NavigationBar`/`NavigationRail`), vistas de Agenda (Día, Semana, Mes, Año), Tareas, Contactos, Ajustes y diálogos modales. |
| `src/assets/icon.svg` | Ícono vectorial minimalista personalizado de **Atempo** usado por `flet build` para generar los íconos de cada plataforma. |
| `atempo.spec` | Especificación alternativa de empaquetado con PyInstaller para escritorio (Linux/Windows), complementaria al empaquetado oficial `flet build`. |
| `.github/workflows/` | Pipelines de GitHub Actions (`ci.yml` para pruebas en Linux/Windows y `build.yml` para compilación y Releases). |
| `tests/` | Suite automatizada dividida en pruebas unitarias (`tests/unit/`), integración SQLite (`tests/integration/`) y prueba de arranque Flet (`tests/test_main.py`). |

### 5.2 Diagrama de Arquitectura y Capas

#### Sintaxis Mermaid

```mermaid
flowchart TD
    subgraph Pres ["Capa de Presentacion (Flet 1.1 Material 3)"]
        UI["Shell Responsivo + Vistas (Agenda, Tareas, Contactos, Ajustes) + Dialogos"]
    end
    subgraph App ["Capa de Aplicacion"]
        SVC["Servicios de Dominio + MotorNotificaciones + StartupReconciler"]
        PORTS["Puertos Protocol (Repositorios, Notificaciones, Acciones externas, Reloj)"]
    end
    subgraph Dom ["Capa de Dominio (Python Puro)"]
        ENT["Entidades (UUIDv4, UTC), Enumeraciones y Excepciones"]
        RULES["ExpansorRecurrencia, DetectorSolapamiento y ValidadorRecordatorio"]
    end
    subgraph Infra ["Capa de Infraestructura"]
        SQL["SQLiteDatabase WAL + Migraciones + 6 Repositorios"]
        NOTIF["Adaptadores Android, Windows, Linux + Worker D-Bus"]
        PLAT["Detector de SO + Lanzador mailto:/tel:"]
    end

    Pres --> App
    App --> Dom
    App --> PORTS
    Infra -.->|"implementa"| PORTS
    Infra --> Dom
```

#### Sintaxis PlantUML

```plantuml
@startuml
title Arquitectura en Capas — Puertos y Adaptadores (Atempo)
skinparam packageStyle rectangle

package "4. Capa de Presentación (Flet 1.1 — Material 3)" as Pres {
  [Shell Responsivo\nNavigationBar / NavigationRail] as Shell
  [Vistas: Agenda, Tareas, Contactos, Ajustes] as Vistas
  [Diálogos y Formateadores UTC/Local] as Dialogos
}

package "2. Capa de Aplicación" as App {
  [Servicios de Dominio\nEventos, Tareas, Contactos, Categorías, Ajustes] as Svc
  [MotorNotificaciones & StartupReconciler] as Motor
  interface "Puertos (Protocol)\nIRepositorios, IAdaptadorNotificaciones,\nILanzadorAccionesExternas, IReloj" as Ports
}

package "1. Capa de Dominio (Python Puro)" as Dom {
  [Entidades (UUIDv4, UTC)\nEnumeraciones y Excepciones] as Ent
  [Reglas Puras\nExpansorRecurrencia, DetectorSolapamiento,\nValidadorRecordatorio] as Rules
}

package "3. Capa de Infraestructura" as Infra {
  [SQLiteDatabase WAL + 6 Repositorios] as Sqlite
  [Adaptadores SO\nAndroid / Windows / Linux + Worker D-Bus] as NotifSO
  [Detector SO + Lanzador mailto:/tel:] as Plat
}

Pres --> Svc
Pres --> Motor
Svc --> Ent
Svc --> Rules
Motor --> Ent
Motor --> Rules
Svc --> Ports
Motor --> Ports

Sqlite ..|> Ports
NotifSO ..|> Ports
Plat ..|> Ports
Infra --> Ent
@enduml
```

### 5.3 Diagrama de Clases UML del Dominio

La versión vectorial completa se encuentra en [`docs/diseno/diagrama_clases.svg`](./diseno/diagrama_clases.svg).

#### Sintaxis Mermaid

```mermaid
classDiagram
    direction TB

    class EntidadBase {
        <<abstract>>
        +UUID id
        +DateTime created_at
        +DateTime updated_at
        +tocar_actualizacion(ahora: DateTime) void
    }

    class Categoria {
        +str nombre
        +str color_hex
        +str icono
    }

    class Subcategoria {
        +UUID categoria_id
        +str nombre
        +str color_hex
    }

    class Evento {
        +str titulo
        +str descripcion
        +DateTime fecha_inicio
        +DateTime fecha_fin
        +bool todo_el_dia
        +str ubicacion
        +str color_hex
        +UUID categoria_id
        +UUID subcategoria_id
        +es_pasado(referencia: DateTime) bool
        +reprogramar(inicio, fin, ahora) void
    }

    class ReglaRecurrencia {
        +UUID evento_id
        +TipoFrecuencia frecuencia
        +int intervalo
        +tuple dias_semana
        +Date fecha_fin_recurrencia
        +int max_ocurrencias
    }

    class Tarea {
        +str titulo
        +str descripcion
        +DateTime fecha_limite
        +PrioridadTarea prioridad
        +EstadoTarea estado
        +UUID categoria_id
        +UUID subcategoria_id
        +completar(ahora: DateTime) void
        +reactivar(estado: EstadoTarea, ahora: DateTime) void
        +reprogramar(fecha: DateTime, ahora: DateTime) void
    }

    class Recordatorio {
        +int id_notificacion_so
        +TipoOrigenRecordatorio tipo_origen
        +UUID evento_id
        +UUID tarea_id
        +int antelacion_minutos
        +DateTime fecha_disparo
        +EstadoRecordatorio estado
        +marcar_entregado(ahora) void
        +marcar_perdido(ahora) void
        +posponer(nueva_fecha, ahora) void
        +cancelar(ahora) void
    }

    class Contacto {
        +str nombre
        +str telefono
        +str correo
        +str notas
        +str etiqueta
        +puede_enviar_correo() bool
        +puede_llamar(plataforma: PlataformaSO) bool
        +generar_uri_correo() str
        +generar_uri_llamada(plataforma: PlataformaSO) str
    }

    class ConfiguracionSistema {
        <<singleton>>
        +int minutos_posponer_defecto
        +int antelacion_recordatorio_defecto_min
        +bool sonido_notificaciones
        +bool mostrar_alertas_perdidas_inicio
        +bool formato_24h
        +int primer_dia_semana
        +VistaAgenda vista_inicial_agenda
        +bool tema_oscuro
        +restablecer_valores_defecto(ahora) void
    }

    EntidadBase <|-- Categoria
    EntidadBase <|-- Subcategoria
    EntidadBase <|-- Evento
    EntidadBase <|-- ReglaRecurrencia
    EntidadBase <|-- Tarea
    EntidadBase <|-- Recordatorio
    EntidadBase <|-- Contacto
    EntidadBase <|-- ConfiguracionSistema

    Categoria "1" *-- "0..*" Subcategoria : contiene
    Evento "0..*" --> "0..1" Categoria
    Evento "0..*" --> "0..1" Subcategoria
    Tarea "0..*" --> "0..1" Categoria
    Tarea "0..*" --> "0..1" Subcategoria
    Evento "1" *-- "0..1" ReglaRecurrencia
    Evento "0..1" *-- "0..1" Recordatorio : XOR
    Tarea "0..1" *-- "0..1" Recordatorio : XOR
    Evento "0..*" -- "0..*" Contacto : vincula
    Tarea "0..*" -- "0..*" Contacto : vincula
```

#### Sintaxis PlantUML

```plantuml
@startuml
title Diagrama de Clases UML — Modelo de Dominio (Atempo)

abstract class EntidadBase {
  +id : UUID
  +created_at : DateTime
  +updated_at : DateTime
  +tocar_actualizacion(ahora : DateTime) : void
}

class Categoria {
  +nombre : str
  +color_hex : str
  +icono : str?
}

class Subcategoria {
  +categoria_id : UUID
  +nombre : str
  +color_hex : str?
}

class Evento {
  +titulo : str
  +descripcion : str?
  +fecha_inicio : DateTime
  +fecha_fin : DateTime?
  +todo_el_dia : bool
  +ubicacion : str?
  +color_hex : str?
  +categoria_id : UUID?
  +subcategoria_id : UUID?
  +es_pasado(referencia : DateTime) : bool
  +reprogramar(inicio, fin, ahora) : void
}

class ReglaRecurrencia {
  +evento_id : UUID
  +frecuencia : TipoFrecuencia
  +intervalo : int
  +dias_semana : tuple[str]
  +fecha_fin_recurrencia : Date?
  +max_ocurrencias : int?
}

class Tarea {
  +titulo : str
  +descripcion : str?
  +fecha_limite : DateTime?
  +prioridad : PrioridadTarea
  +estado : EstadoTarea
  +categoria_id : UUID?
  +subcategoria_id : UUID?
  +completar(ahora : DateTime) : void
  +reactivar(estado : EstadoTarea, ahora : DateTime) : void
  +reprogramar(fecha : DateTime?, ahora : DateTime) : void
}

class Recordatorio {
  +id_notificacion_so : int
  +tipo_origen : TipoOrigenRecordatorio
  +evento_id : UUID?
  +tarea_id : UUID?
  +antelacion_minutos : int
  +fecha_disparo : DateTime
  +estado : EstadoRecordatorio
  +marcar_entregado(ahora : DateTime) : void
  +marcar_perdido(ahora : DateTime) : void
  +posponer(nueva_fecha : DateTime, ahora : DateTime) : void
  +cancelar(ahora : DateTime) : void
}

class Contacto {
  +nombre : str
  +telefono : str?
  +correo : str?
  +notas : str?
  +etiqueta : str?
  +puede_enviar_correo() : bool
  +puede_llamar(plataforma : PlataformaSO) : bool
  +generar_uri_correo() : str?
  +generar_uri_llamada(plataforma : PlataformaSO) : str?
}

class ConfiguracionSistema <<singleton>> {
  +minutos_posponer_defecto : int
  +antelacion_recordatorio_defecto_min : int
  +sonido_notificaciones : bool
  +mostrar_alertas_perdidas_inicio : bool
  +formato_24h : bool
  +primer_dia_semana : int
  +vista_inicial_agenda : VistaAgenda
  +tema_oscuro : bool
  +restablecer_valores_defecto(ahora : DateTime) : void
}

EntidadBase <|-- Categoria
EntidadBase <|-- Subcategoria
EntidadBase <|-- Evento
EntidadBase <|-- ReglaRecurrencia
EntidadBase <|-- Tarea
EntidadBase <|-- Recordatorio
EntidadBase <|-- Contacto
EntidadBase <|-- ConfiguracionSistema

Categoria "1" *-- "0..*" Subcategoria : contiene
Evento "0..*" --> "0..1" Categoria
Evento "0..*" --> "0..1" Subcategoria
Tarea "0..*" --> "0..1" Categoria
Tarea "0..*" --> "0..1" Subcategoria
Evento "1" *-- "0..1" ReglaRecurrencia : recurrencia
Evento "0..1" *-- "0..1" Recordatorio : {XOR}
Tarea "0..1" *-- "0..1" Recordatorio : {XOR}
Evento "0..*" -- "0..*" Contacto : vincula
Tarea "0..*" -- "0..*" Contacto : vincula
@enduml
```

### 5.4 Modelo Entidad–Relación (SQLite 3)

El diagrama vectorial se encuentra en [`docs/diseno/diagrama_entidad_relacion.svg`](./diseno/diagrama_entidad_relacion.svg) y el script DDL verificado en [`docs/diseno/esquema_inicial.sql`](./diseno/esquema_inicial.sql).

#### Sintaxis Mermaid

```mermaid
erDiagram
    CATEGORIAS ||--o{ SUBCATEGORIAS : "tiene"
    CATEGORIAS ||--o{ EVENTOS : "clasifica"
    SUBCATEGORIAS ||--o{ EVENTOS : "subclasifica"
    CATEGORIAS ||--o{ TAREAS : "clasifica"
    SUBCATEGORIAS ||--o{ TAREAS : "subclasifica"
    EVENTOS ||--o| REGLAS_RECURRENCIA : "posee"
    EVENTOS ||--o| RECORDATORIOS : "programa_xor"
    TAREAS ||--o| RECORDATORIOS : "programa_xor"
    EVENTOS ||--o{ EVENTO_CONTACTO : "vincula"
    CONTACTOS ||--o{ EVENTO_CONTACTO : "participa"
    TAREAS ||--o{ TAREA_CONTACTO : "vincula"
    CONTACTOS ||--o{ TAREA_CONTACTO : "participa"

    CATEGORIAS {
        TEXT id PK
        TEXT nombre
        TEXT color_hex
        TEXT icono
    }
    SUBCATEGORIAS {
        TEXT id PK
        TEXT categoria_id FK
        TEXT nombre
        TEXT color_hex
    }
    EVENTOS {
        TEXT id PK
        TEXT titulo
        TEXT fecha_inicio
        TEXT fecha_fin
        INTEGER todo_el_dia
        TEXT ubicacion
        TEXT categoria_id FK
        TEXT subcategoria_id FK
    }
    REGLAS_RECURRENCIA {
        TEXT id PK
        TEXT evento_id FK
        TEXT frecuencia
        INTEGER intervalo
        TEXT dias_semana
    }
    TAREAS {
        TEXT id PK
        TEXT titulo
        TEXT fecha_limite
        TEXT prioridad
        TEXT estado
        TEXT categoria_id FK
        TEXT subcategoria_id FK
    }
    RECORDATORIOS {
        TEXT id PK
        INTEGER id_notificacion_so UK
        TEXT tipo_origen
        TEXT evento_id FK
        TEXT tarea_id FK
        INTEGER antelacion_minutos
        TEXT fecha_disparo
        TEXT estado
    }
    CONTACTOS {
        TEXT id PK
        TEXT nombre
        TEXT telefono
        TEXT correo
        TEXT etiqueta
    }
    EVENTO_CONTACTO {
        TEXT evento_id PK,FK
        TEXT contacto_id PK,FK
    }
    TAREA_CONTACTO {
        TEXT tarea_id PK,FK
        TEXT contacto_id PK,FK
    }
    CONFIGURACION_SISTEMA {
        INTEGER singleton_key PK
        TEXT id UK
        INTEGER minutos_posponer_defecto
        INTEGER antelacion_recordatorio_defecto_min
        INTEGER formato_24h
        INTEGER primer_dia_semana
        TEXT vista_inicial_agenda
        INTEGER tema_oscuro
    }
```

#### Sintaxis PlantUML

```plantuml
@startuml
title Modelo Entidad-Relación — Esquema SQLite 3 (Atempo)
hide circle
skinparam linetype ortho

entity "CATEGORIAS" as categorias {
  * id : TEXT <<PK>>
  --
  * nombre : TEXT
  * color_hex : TEXT
  icono : TEXT
  * created_at : TEXT
  * updated_at : TEXT
}

entity "SUBCATEGORIAS" as subcategorias {
  * id : TEXT <<PK>>
  --
  * categoria_id : TEXT <<FK>>
  * nombre : TEXT
  color_hex : TEXT
  * created_at : TEXT
  * updated_at : TEXT
}

entity "EVENTOS" as eventos {
  * id : TEXT <<PK>>
  --
  * titulo : TEXT
  descripcion : TEXT
  * fecha_inicio : TEXT
  fecha_fin : TEXT
  * todo_el_dia : INTEGER
  ubicacion : TEXT
  color_hex : TEXT
  categoria_id : TEXT <<FK>>
  subcategoria_id : TEXT <<FK>>
  * created_at : TEXT
  * updated_at : TEXT
}

entity "REGLAS_RECURRENCIA" as recurrencia {
  * id : TEXT <<PK>>
  --
  * evento_id : TEXT <<FK, UK>>
  * frecuencia : TEXT
  * intervalo : INTEGER
  dias_semana : TEXT
  fecha_fin_recurrencia : TEXT
  max_ocurrencias : INTEGER
}

entity "TAREAS" as tareas {
  * id : TEXT <<PK>>
  --
  * titulo : TEXT
  descripcion : TEXT
  fecha_limite : TEXT
  * prioridad : TEXT
  * estado : TEXT
  categoria_id : TEXT <<FK>>
  subcategoria_id : TEXT <<FK>>
  * created_at : TEXT
  * updated_at : TEXT
}

entity "RECORDATORIOS" as recordatorios {
  * id : TEXT <<PK>>
  --
  * id_notificacion_so : INTEGER <<UK>>
  * tipo_origen : TEXT
  evento_id : TEXT <<FK, UK>>
  tarea_id : TEXT <<FK, UK>>
  * antelacion_minutos : INTEGER
  * fecha_disparo : TEXT
  * estado : TEXT
}

entity "CONTACTOS" as contactos {
  * id : TEXT <<PK>>
  --
  * nombre : TEXT
  telefono : TEXT
  correo : TEXT
  notas : TEXT
  etiqueta : TEXT
}

entity "EVENTO_CONTACTO" as ev_con {
  * evento_id : TEXT <<PK, FK>>
  * contacto_id : TEXT <<PK, FK>>
  --
  * created_at : TEXT
}

entity "TAREA_CONTACTO" as tar_con {
  * tarea_id : TEXT <<PK, FK>>
  * contacto_id : TEXT <<PK, FK>>
  --
  * created_at : TEXT
}

entity "CONFIGURACION_SISTEMA" as config {
  * singleton_key : INTEGER <<PK>>
  --
  * id : TEXT <<UK>>
  * minutos_posponer_defecto : INTEGER
  * antelacion_recordatorio_defecto_min : INTEGER
  * sonido_notificaciones : INTEGER
  * mostrar_alertas_perdidas_inicio : INTEGER
  * formato_24h : INTEGER
  * primer_dia_semana : INTEGER
  * vista_inicial_agenda : TEXT
  * tema_oscuro : INTEGER
}

categorias ||--o{ subcategorias : "CASCADE"
categorias |o--o{ eventos : "SET NULL"
subcategorias |o--o{ eventos : "SET NULL"
categorias |o--o{ tareas : "SET NULL"
subcategorias |o--o{ tareas : "SET NULL"
eventos ||--o| recurrencia : "CASCADE"
eventos |o--o| recordatorios : "XOR / CASCADE"
tareas |o--o| recordatorios : "XOR / CASCADE"
eventos ||--o{ ev_con : "CASCADE"
contactos ||--o{ ev_con : "CASCADE"
tareas ||--o{ tar_con : "CASCADE"
contactos ||--o{ tar_con : "CASCADE"
@enduml
```

### 5.5 Estrategia del Motor de Notificaciones y Máquina de Estados

Dado que `flet-notifications` presenta capacidades distintas en cada plataforma, el motor mantiene la tabla `recordatorios` como fuente única de verdad y aplica una estrategia específica detrás de `IAdaptadorNotificaciones`:

* **Android:** emplea `schedule()` con `EXACT_ALLOW_WHILE_IDLE` (degradando automáticamente a `INEXACT_ALLOW_WHILE_IDLE` si el permiso exacto no está concedido), declara `ScheduledNotificationBootReceiver` en `pyproject.toml` para sobrevivir reinicios y configura el botón *Posponer* con `foreground=True` para que el intérprete Python reprograme la nueva alerta.
* **Windows:** programa notificaciones únicas (*one-off*) y realiza cancelaciones individuales por `id_notificacion_so` (`int32`), ya que la API de Windows no admite cancelación masiva de pendientes ni recurrencias nativas.
* **Linux:** al no existir programación diferida en FreeDesktop D-Bus, utiliza un planificador asíncrono `asyncio` mientras la aplicación está abierta y ofrece un proceso ligero opcional (`linux_worker.py`) registrable en `systemd --user` que lee el mismo archivo SQLite en modo WAL y emite notificaciones con botones vía `desktop-notifier`.

#### Máquina de Estados del Recordatorio — Sintaxis Mermaid

```mermaid
stateDiagram-v2
    [*] --> PENDIENTE : Crear o reprogramar
    PENDIENTE --> CANCELADO : Eliminar item / Completar tarea / Editar horario
    PENDIENTE --> ENTREGADO : SO dispara alerta a tiempo
    PENDIENTE --> PERDIDO : Barrido al iniciar detecta vencimiento
    ENTREGADO --> POSPUESTO : Accion rapida Posponer (+Ajustes)
    ENTREGADO --> ATENDIDO : Usuario abre o marca visto
    POSPUESTO --> ENTREGADO : SO dispara alerta diferida
    POSPUESTO --> PERDIDO : Equipo apagado durante snooze
    POSPUESTO --> CANCELADO : Item eliminado o tarea completada
    PERDIDO --> POSPUESTO : Usuario pospone desde bandeja
    PERDIDO --> ATENDIDO : Usuario marca como vista
    CANCELADO --> PENDIENTE : Tarea reactivada o evento reprogramado
    ATENDIDO --> [*]
```

#### Máquina de Estados del Recordatorio — Sintaxis PlantUML

```plantuml
@startuml
title Máquina de Estados del Recordatorio (Motor Unificado)

[*] --> PENDIENTE : Crear o reprogramar
PENDIENTE --> CANCELADO : Eliminar ítem / Completar tarea / Editar horario
PENDIENTE --> ENTREGADO : SO dispara alerta a tiempo
PENDIENTE --> PERDIDO : StartupReconciler detecta vencimiento

ENTREGADO --> POSPUESTO : Acción rápida Posponer (+minutos de Ajustes)
ENTREGADO --> ATENDIDO : Usuario abre o marca visto

POSPUESTO --> ENTREGADO : SO dispara alerta diferida
POSPUESTO --> PERDIDO : Equipo apagado durante snooze
POSPUESTO --> CANCELADO : Ítem eliminado o tarea completada

PERDIDO --> POSPUESTO : Usuario pospone desde bandeja
PERDIDO --> ATENDIDO : Usuario marca como vista

CANCELADO --> PENDIENTE : Tarea reactivada o evento reprogramado
ATENDIDO --> [*]
@enduml
```

---

## 6. Evidencias de Desarrollo y Compilación

En esta sección se documentan las evidencias del entorno de desarrollo, la gestión del repositorio, la ejecución de pruebas y los procesos de compilación local y automatizada en la nube.

### 6.1 Entorno de Desarrollo, Dependencias y Control de Versiones

> **Captura 1 — Entorno de desarrollo y estructura del proyecto:** *Vista del editor (VS Code) mostrando la estructura en capas de `src/agenda_app/` (`domain`, `application`, `infrastructure`, `presentation`) y el archivo `pyproject.toml` con las dependencias y permisos Android.*  
> *(Insertar captura aquí)*

> **Captura 2 — Gestión de entorno reproducible con `uv`:** *Terminal ejecutando `uv sync` y verificando la creación del entorno virtual `.venv` y la resolución de dependencias (`flet`, `flet-notifications`, `desktop-notifier`, `pytest`).*  
> *(Insertar captura aquí)*

> **Captura 3 — Control de versiones en Git y GitHub:** *Terminal mostrando el historial de ramas y merges (`git log --graph --oneline`) junto con la vista del repositorio remoto en GitHub (`JoelCOsorio/Agenda-Personal`).*  
> *(Insertar captura aquí)*

### 6.2 Compilación Local y Automatizada en la Nube (GitHub Actions)

> **Captura 4 — Compilación local en Linux:** *Terminal ejecutando el empaquetado local con `uv run flet build linux -v` (o preparación de dependencias del sistema) y mostrando el binario generado en `build/linux/`.*  
> *(Insertar captura aquí)*

> **Captura 5 — Integración Continua (`ci.yml`) en GitHub Actions:** *Vista de GitHub Actions mostrando la ejecución exitosa del workflow `CI - Pruebas Automatizadas` en paralelo sobre `ubuntu-latest` y `windows-latest`.*  
> *(Insertar captura aquí)*

> **Captura 6 — Compilación multiplataforma en la nube (`build.yml`):** *Resumen del workflow `Build Multiplataforma (Android, Linux, Windows)` en GitHub Actions mostrando en verde la verificación de pruebas y la compilación simultánea de `apk`, `linux` y `windows` con sus artefactos generados.*  
> *(Insertar captura aquí)*

> **Captura 7 — Publicación de Release en GitHub:** *Sección de Releases del repositorio mostrando la etiqueta de versión (`v1.0.0`) con los paquetes compilados adjuntos listos para descargar.*  
> *(Insertar captura aquí)*

---

## 7. Pruebas y Demostración de Funcionalidades

### 7.1 Suite de Pruebas Automatizadas

Para asegurar el cumplimiento de las reglas de negocio antes de empaquetar, se construyó una suite de **25 pruebas automatizadas** que cubren dominio puro, motor de notificaciones, contratos de los adaptadores de Android/Windows/Linux, integración real con SQLite WAL y navegación de vistas UI. Todas se ejecutan con `uv run pytest tests/unit tests/integration -v` (25 pruebas superadas en 0.86 s, 0 advertencias).

> **Captura 8 — Ejecución de pruebas automatizadas:** *Terminal mostrando la salida completa de `uv run pytest tests/unit tests/integration -v` con los 25 casos superados.*  
> *(Insertar captura aquí)*

### 7.2 Ejecución y Demostración de Funcionalidades en Linux (KDE Plasma)

> **Captura 9 — Arranque del ejecutable en Linux y vista mensual de Agenda:** *Terminal lanzando el binario compilado junto a la ventana de Atempo mostrando el `NavigationRail` lateral, la cuadrícula mensual del calendario y el panel de eventos del día.*  
> *(Insertar captura aquí)*

> **Captura 10 — Vistas Día, Semana, Año e Historial:** *Demostración de la conmutación entre las escalas temporales de la agenda (Día, Semana y Año) y el diálogo de Historial de eventos pasados.*  
> *(Insertar captura aquí)*

> **Captura 11 — Creación de evento, recurrencia y categoría rápida en línea:** *Formulario modal de evento configurando repetición semanal, recordatorio y creación rápida de una categoría/subcategoría sin salir del formulario.*  
> *(Insertar captura aquí)*

> **Captura 12 — Validación anti-solapamiento (choque de horarios):** *Formulario de evento mostrando el aviso rojo de choque de horarios al intentar registrar una actividad superpuesta con otra existente.*  
> *(Insertar captura aquí)*

> **Captura 13 — Notificación nativa en KDE Plasma y bandeja de perdidas:** *Notificación emergente nativa en el escritorio Linux con los botones "Posponer" y "Marcar como visto", junto con el diálogo de bandeja de notificaciones perdidas tras simular inactividad.*  
> *(Insertar captura aquí)*

> **Captura 14 — Servicio en segundo plano en Linux (`systemd --user`):** *Terminal mostrando el estado activo de `agenda-notificaciones.service` (`linux_worker.py`) entregando una alerta mientras la ventana principal está cerrada.*  
> *(Insertar captura aquí)*

> **Captura 15 — Módulo independiente de Tareas:** *Vista de Tareas mostrando filtros por estado, prioridad y categoría, tarjetas con insignia de prioridad y recordatorio, y marcado de una tarea como completada.*  
> *(Insertar captura aquí)*

> **Captura 16 — Módulo de Contactos en escritorio:** *Directorio de contactos con búsqueda en tiempo real, etiquetas, botón de correo (`mailto:`) habilitado y verificación de que el botón de llamada no se muestra en Linux.*  
> *(Insertar captura aquí)*

> **Captura 17 — Módulo de Ajustes (Modo Claro vs. Modo Oscuro) y gestor de categorías:** *Comparativa visual del cambio en vivo a modo oscuro, configuración de tiempo de posponer, diagnóstico de plataforma y gestor de categorías/subcategorías.*  
> *(Insertar captura aquí)*

### 7.3 Ejecución y Demostración en Android

> **Captura 18 — Instalación y lanzador en Android:** *Ícono minimalista de Atempo instalado en el dispositivo Android a partir del APK generado en GitHub Actions.*  
> *(Insertar captura aquí)*

> **Captura 19 — Interfaz móvil responsiva (`NavigationBar`):** *Vistas de Agenda y Tareas en pantalla vertical Android mostrando la barra de navegación inferior y el botón flotante contextual.*  
> *(Insertar captura aquí)*

> **Captura 20 — Contactos con llamada nativa en Android:** *Tarjeta de contacto en Android mostrando tanto el botón de correo (`mailto:`) como el botón de llamada (`tel:`) abriendo el marcador telefónico.*  
> *(Insertar captura aquí)*

> **Captura 21 — Notificación nativa y permisos en Android:** *Pantalla de permisos de notificaciones/alarmas exactas en Android y notificación programada entregada con la aplicación cerrada mostrando acciones rápidas.*  
> *(Insertar captura aquí)*

### 7.4 Ejecución y Demostración en Windows

> **Captura 22 — Ejecución del paquete compilado en Windows:** *Ventana de escritorio de Atempo ejecutándose en Windows 10/11 mostrando la interfaz responsiva y la persistencia local.*  
> *(Insertar captura aquí)*

> **Captura 23 — Notificación nativa en Windows (*Windows Toast*):** *Alerta programada apareciendo en el centro de notificaciones de Windows con sus botones de acción.*  
> *(Insertar captura aquí)*

---

## 8. Conclusiones

El desarrollo de **Atempo** dentro de la asignatura **Desarrollo de Aplicaciones Multiplataforma** permitió comprobar en la práctica que construir software verdaderamente multiplataforma implica mucho más que compartir una interfaz gráfica entre distintos sistemas operativos. Si bien Python y Flet facilitan mantener una sola base de código visual basada en Material Design 3 con adaptación responsiva para móvil y escritorio, la integración con servicios nativos del sistema operativo —especialmente el agendado de notificaciones en segundo plano, la gestión de permisos en Android, las restricciones de Windows Toast y el protocolo D-Bus en Linux— obliga a diseñar abstracciones claras desde el inicio.

La adopción de una arquitectura en capas basada en Puertos y Adaptadores y principios SOLID resultó decisiva para controlar esta complejidad. Mantener el dominio completamente libre de dependencias externas permitió validar las reglas críticas del negocio (anti-solapamiento, recurrencias, límites temporales de recordatorios, ciclo de vida de tareas y desvinculación sin cascada) mediante 25 pruebas automatizadas rápidas, además de verificar mediante pruebas de contrato el comportamiento esperado de Android y Windows aun desarrollando principalmente desde Linux.

Asimismo, el uso de SQLite 3 en modo WAL como fuente única de verdad garantizó autonomía sin conexión, privacidad de los datos y concurrencia segura con el servicio residente de Linux, dejando preparados identificadores `UUIDv4` y marcas temporales UTC para incorporar sincronización entre dispositivos en una versión futura. Finalmente, la integración de `uv`, Git con ramas dedicadas y flujos de compilación en la nube con GitHub Actions completó el ciclo de vida profesional del software, desde la especificación de requerimientos hasta la generación automatizada de ejecutables para las tres plataformas objetivo.

---

## 9. Anexos

* **Repositorio del proyecto en GitHub (control de versiones y workflows CI/CD):**  
  `https://github.com/JoelCOsorio/Agenda-Personal.git`
* **Documentación de ingeniería generada en el repositorio:**
  * Propuesta del proyecto: `docs/propuesta/propuesta_proyecto.md`
  * Recolección de datos y entrevistas: `docs/ing_requerimientos/ingenieria_requerimientos.md`
  * Especificación formal de requerimientos (ERS): `docs/ing_requerimientos/especificacion_formal_requerimientos.md`
  * Diseño, diagramas UML/ER y esquema SQL: `docs/diseno/diseno_y_modelado_datos.md`, `docs/diseno/diagrama_clases.svg`, `docs/diseno/diagrama_entidad_relacion.svg`, `docs/diseno/esquema_inicial.sql`
  * Diseño del motor de notificaciones y arquitectura Flet: `docs/diseno/diseno_motor_notificaciones.md`, `docs/diseno/arquitectura_flet.md`

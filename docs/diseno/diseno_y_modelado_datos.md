# Fase de Diseño y Modelado de Datos

**Proyecto:** Agenda Personal y Académica Multiplataforma (Flet)  
**Plataformas Objetivo:** Android, Windows y Linux  
**Versión:** 1.0  
**Fecha:** 23 de noviembre de 2026  
**Documentos Base:**  
* Propuesta del Proyecto: [`docs/propuesta/propuesta_proyecto.md`](../propuesta/propuesta_proyecto.md)  
* Especificación Formal de Requerimientos (ERS): [`docs/ing_requerimientos/especificacion_formal_requerimientos.md`](../ing_requerimientos/especificacion_formal_requerimientos.md)

**Diagramas SVG generados:**  
* Diagrama de Clases UML (Dominio): [`diagrama_clases.svg`](./diagrama_clases.svg)  
* Diagrama Entidad–Relación (Modelo de Datos): [`diagrama_entidad_relacion.svg`](./diagrama_entidad_relacion.svg)

---

## 1. Identificación de Entidades del Dominio

A partir de los procesos (`PROC-01` a `PROC-06`), requerimientos (`RF-01` a `RF-24`, `RNF-01` a `RNF-10`) y reglas de negocio (`RN-01` a `RN-14`), se identifican **9 entidades de dominio/persistencia** (más 1 superclase abstracta base y 6 enumeraciones), todas preparadas con identificadores `UUIDv4` y marcas temporales UTC (`RN-10`) para facilitar sincronización futura sin acoplamiento:

| # | Entidad | Módulo | Propósito Principal | Reglas de Negocio Clave |
| :--- | :--- | :--- | :--- | :--- |
| 0 | **`EntidadBase`** *(Abstracta)* | Transversal | Define `id (UUID)`, `created_at` y `updated_at` heredados por todas las entidades persistentes. | `RN-10`, `RNF-03` |
| 1 | **`Evento`** | Agenda | Representa un compromiso calendarizado con fecha/hora de inicio, fin opcional, indicador de todo el día, ubicación y color. | `RN-01`, `RN-04`, `RN-07`, `RN-11` |
| 2 | **`ReglaRecurrencia`** | Agenda | Define el patrón de repetición periódica (diaria, semanal, mensual o anual) asociado de forma opcional (`0..1`) a un `Evento`. | `RF-06`, `RN-11` |
| 3 | **`Tarea`** | Tareas | Representa una actividad pendiente en módulo propio independiente del calendario, con fecha límite, prioridad y ciclo de vida de estado. | `RN-07`, `RN-12` |
| 4 | **`Recordatorio`** | Notificaciones | Modela la alerta programable única (`0..1`) asociada de forma exclusiva (XOR) a un `Evento` o a una `Tarea`, controlando su estado (`PENDIENTE`, `ENTREGADO`, `PERDIDO`, `POSPUESTO`, `CANCELADO`, `ATENDIDO`). | `RN-02`, `RN-03`, `RN-05`, `RN-06`, `RN-12` |
| 5 | **`Contacto`** | Contactos | Almacena la ficha de personas personales o académicas (nombre, teléfono, correo, notas, etiqueta) y resuelve acciones externas condicionadas por SO. | `RN-08`, `RN-13` |
| 6 | **`Categoria`** | Organización | Nivel 1 de clasificación (ej. *Universidad, Personal, Trabajo*). | `RN-09`, `RN-13` |
| 7 | **`Subcategoria`** | Organización | Nivel 2 de clasificación (ej. *Cálculo, Ingeniería de Software*), siempre subordinada a una `Categoria` padre. | `RN-09`, `RN-13` |
| 8 | **`ConfiguracionSistema`** | Ajustes | Entidad *singleton* persistente con parámetros operativos globales (*snooze*, antelación por defecto, formato 12h/24h, tema, vista inicial, primer día de la semana). | `RF-23`, `RF-24`, `RN-14` |
| 9 | **`EventoContacto` / `TareaContacto`** *(Tablas asociativas)* | Relacional | Materializan las relaciones muchos a muchos (`0..*` $\leftrightarrow$ `0..*`) entre `Contacto` y `Evento`/`Tarea`, garantizando desvinculación segura sin borrado en cascada. | `RF-18`, `RF-19`, `RN-13` |

---

## 2. Matriz de Relaciones y Cardinalidades

| Entidad Origen | Relación | Cardinalidad | Entidad Destino | Tipo UML | Regla de Integridad Referencial |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `Categoria` | agrupa | `1` $\longrightarrow$ `0..*` | `Subcategoria` | Composición | `ON DELETE CASCADE` sobre subcategorías hijas (los eventos/tareas pasan a *"Sin categoría"*). |
| `Evento` | clasificado en | `0..*` $\longrightarrow$ `0..1` | `Categoria` | Asociación | `ON DELETE SET NULL` (`RN-13`). |
| `Evento` | clasificado en | `0..*` $\longrightarrow$ `0..1` | `Subcategoria` | Asociación | `ON DELETE SET NULL` (`RN-13`; conserva `categoria_id` si existe). |
| `Tarea` | clasificada en | `0..*` $\longrightarrow$ `0..1` | `Categoria` | Asociación | `ON DELETE SET NULL` (`RN-13`). |
| `Tarea` | clasificada en | `0..*` $\longrightarrow$ `0..1` | `Subcategoria` | Asociación | `ON DELETE SET NULL` (`RN-13`). |
| `Evento` | posee | `1` $\longrightarrow$ `0..1` | `ReglaRecurrencia` | Composición | `ON DELETE CASCADE` (la regla no existe sin su evento). |
| `Evento` | dispara *(XOR)* | `0..1` $\longrightarrow$ `0..1` | `Recordatorio` | Composición | `ON DELETE CASCADE` + cancelación en SO (`RN-02`, `RN-03`). |
| `Tarea` | dispara *(XOR)* | `0..1` $\longrightarrow$ `0..1` | `Recordatorio` | Composición | `ON DELETE CASCADE` + cancelación en SO (`RN-02`, `RN-03`, `RN-12`). |
| `Evento` | vincula | `0..*` $\longleftrightarrow$ `0..*` | `Contacto` | Asociación N:M | Tabla `evento_contacto`; eliminar un contacto solo elimina el vínculo (`RN-13`). |
| `Tarea` | vincula | `0..*` $\longleftrightarrow$ `0..*` | `Contacto` | Asociación N:M | Tabla `tarea_contacto`; eliminar un contacto solo elimina el vínculo (`RN-13`). |

> **Restricción de Arco Exclusivo (XOR) en `Recordatorio`:** Todo registro de `Recordatorio` debe referenciar exactamente a **un `Evento` o a una `Tarea`**, nunca a ambos ni a ninguno (`(evento_id IS NOT NULL) XOR (tarea_id IS NOT NULL)`), garantizando a su vez unicidad (`UNIQUE`) por ítem para cumplir `RN-03` (máximo 1 recordatorio activo en v1).

---

## 3. Diagrama de Clases UML — Modelo de Dominio (Mermaid)

> Versión gráfica independiente en sintaxis SVG: [`docs/diseno/diagrama_clases.svg`](./diagrama_clases.svg)

```mermaid
classDiagram
    direction TB

    class EntidadBase {
        <<abstract>>
        +UUID id
        +DateTime created_at
        +DateTime updated_at
        +actualizar_marca_temporal() void
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
        +validar_rango_temporal() bool
        +se_solapa_con(otro: Evento) bool
        +es_pasado(referencia: DateTime) bool
        +reprogramar(inicio: DateTime, fin: DateTime) void
    }

    class ReglaRecurrencia {
        +UUID evento_id
        +TipoFrecuencia frecuencia
        +int intervalo
        +str dias_semana
        +Date fecha_fin_recurrencia
        +int max_ocurrencias
        +expandir_ocurrencias(desde: DateTime, hasta: DateTime) List
    }

    class Tarea {
        +str titulo
        +str descripcion
        +DateTime fecha_limite
        +PrioridadTarea prioridad
        +EstadoTarea estado
        +UUID categoria_id
        +UUID subcategoria_id
        +completar() void
        +reactivar(nuevo_estado: EstadoTarea) void
        +reprogramar(nueva_fecha: DateTime) void
    }

    class Recordatorio {
        +TipoOrigenRecordatorio tipo_origen
        +UUID evento_id
        +UUID tarea_id
        +int antelacion_minutos
        +DateTime fecha_disparo
        +EstadoRecordatorio estado
        +int id_notificacion_so
        +calcular_fecha_disparo(objetivo: DateTime) DateTime
        +es_valido_para_programar(ahora: DateTime) bool
        +marcar_perdido() void
        +posponer(minutos_snooze: int) DateTime
        +cancelar() void
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
        +generar_uri_llamada() str
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
        +restablecer_valores_defecto() void
    }

    class TipoFrecuencia {
        <<enumeration>>
        DIARIA
        SEMANAL
        MENSUAL
        ANUAL
    }

    class PrioridadTarea {
        <<enumeration>>
        BAJA
        MEDIA
        ALTA
    }

    class EstadoTarea {
        <<enumeration>>
        PENDIENTE
        EN_PROGRESO
        COMPLETADA
    }

    class EstadoRecordatorio {
        <<enumeration>>
        PENDIENTE
        ENTREGADO
        PERDIDO
        POSPUESTO
        CANCELADO
        ATENDIDO
    }

    class TipoOrigenRecordatorio {
        <<enumeration>>
        EVENTO
        TAREA
    }

    class PlataformaSO {
        <<enumeration>>
        ANDROID
        WINDOWS
        LINUX
    }

    class VistaAgenda {
        <<enumeration>>
        DIA
        SEMANA
        MES
        ANIO
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
    Evento "0..*" --> "0..1" Categoria : pertenece a
    Evento "0..*" --> "0..1" Subcategoria : clasificado en
    Tarea "0..*" --> "0..1" Categoria : pertenece a
    Tarea "0..*" --> "0..1" Subcategoria : clasificada en

    Evento "1" *-- "0..1" ReglaRecurrencia : se repite segun
    Evento "0..1" *-- "0..1" Recordatorio : programa (XOR)
    Tarea "0..1" *-- "0..1" Recordatorio : programa (XOR)

    Evento "0..*" -- "0..*" Contacto : vincula
    Tarea "0..*" -- "0..*" Contacto : vincula

    ReglaRecurrencia ..> TipoFrecuencia : usa
    Tarea ..> PrioridadTarea : usa
    Tarea ..> EstadoTarea : usa
    Recordatorio ..> EstadoRecordatorio : usa
    Recordatorio ..> TipoOrigenRecordatorio : usa
    Contacto ..> PlataformaSO : valida segun
    ConfiguracionSistema ..> VistaAgenda : usa
```

---

## 4. Diagrama de Clases — Capa de Servicios y Adaptadores Multiplataforma (Desacoplamiento `RNF-03`)

Para cumplir con **Flet** (`RNF-01`), las APIs nativas de **Android, Windows y Linux** (`RF-10`, `RF-12`, `RF-20`) y el desacoplamiento preparado para sincronización futura (`RN-10`, `RNF-03`), se definen interfaces (*puertos*) separadas de las implementaciones concretas (*adaptadores*):

```mermaid
classDiagram
    direction TB

    class IAdaptadorNotificaciones {
        <<interface>>
        +soporta_acciones_rapidas() bool
        +verificar_permisos() bool
        +programar(recordatorio: Recordatorio, titulo: str, cuerpo: str, acciones: List) str
        +cancelar(id_notificacion_so: str) void
        +mostrar_inmediata(titulo: str, cuerpo: str) void
    }

    class AdaptadorNotificacionesAndroid {
        +programar(...) str
        +cancelar(id_notificacion_so: str) void
        +soporta_acciones_rapidas() bool
    }

    class AdaptadorNotificacionesWindows {
        +programar(...) str
        +cancelar(id_notificacion_so: str) void
        +soporta_acciones_rapidas() bool
    }

    class AdaptadorNotificacionesLinux {
        +consultar_capacidades_dbus() List
        +programar(...) str
        +cancelar(id_notificacion_so: str) void
        +soporta_acciones_rapidas() bool
    }

    class ILanzadorAccionesExternas {
        <<interface>>
        +puede_llamar() bool
        +abrir_correo(correo: str) bool
        +abrir_llamada(telefono: str) bool
    }

    class IRepositorioAgenda {
        <<interface>>
        +guardar_evento(evento: Evento) void
        +obtener_eventos_rango(inicio: DateTime, fin: DateTime) List
        +eliminar_evento(evento_id: UUID) void
    }

    class RepositorioSQLiteLocal {
        +str ruta_db
        +guardar_evento(evento: Evento) void
        +obtener_eventos_rango(inicio: DateTime, fin: DateTime) List
        +eliminar_evento(evento_id: UUID) void
    }

    class MotorNotificaciones {
        +programar_o_reprogramar(recordatorio: Recordatorio, objetivo: DateTime) void
        +cancelar_por_item(item_id: UUID) void
        +detectar_y_notificar_perdidas() List
        +manejar_accion_posponer(recordatorio_id: UUID) void
    }

    class ServicioEventos {
        +crear_evento(datos) Evento
        +editar_evento(evento_id: UUID, datos) Evento
        +eliminar_evento(evento_id: UUID) void
        +detectar_choque(candidato: Evento) Evento
    }

    IAdaptadorNotificaciones <|.. AdaptadorNotificacionesAndroid
    IAdaptadorNotificaciones <|.. AdaptadorNotificacionesWindows
    IAdaptadorNotificaciones <|.. AdaptadorNotificacionesLinux
    IRepositorioAgenda <|.. RepositorioSQLiteLocal

    ServicioEventos --> IRepositorioAgenda : persiste via
    ServicioEventos --> MotorNotificaciones : sincroniza alertas
    MotorNotificaciones --> IAdaptadorNotificaciones : delega al SO
```

---

## 5. Modelo Entidad–Relación / Modelo de Datos Relacional (Mermaid)

> Versión gráfica independiente en sintaxis SVG: [`docs/diseno/diagrama_entidad_relacion.svg`](./diagrama_entidad_relacion.svg)

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
        TEXT id PK "UUIDv4"
        TEXT nombre "NOT NULL"
        TEXT color_hex
        TEXT icono
        TEXT created_at "UTC ISO-8601"
        TEXT updated_at "UTC ISO-8601"
    }

    SUBCATEGORIAS {
        TEXT id PK "UUIDv4"
        TEXT categoria_id FK "NOT NULL, CASCADE"
        TEXT nombre "NOT NULL"
        TEXT color_hex
        TEXT created_at
        TEXT updated_at
    }

    EVENTOS {
        TEXT id PK "UUIDv4"
        TEXT titulo "NOT NULL"
        TEXT descripcion
        TEXT fecha_inicio "NOT NULL, UTC"
        TEXT fecha_fin "CHECK >= fecha_inicio"
        INTEGER todo_el_dia "BOOLEAN 0/1"
        TEXT ubicacion
        TEXT color_hex
        TEXT categoria_id FK "SET NULL"
        TEXT subcategoria_id FK "SET NULL"
        TEXT created_at
        TEXT updated_at
    }

    REGLAS_RECURRENCIA {
        TEXT id PK "UUIDv4"
        TEXT evento_id FK "UNIQUE, NOT NULL, CASCADE"
        TEXT frecuencia "DIARIA|SEMANAL|MENSUAL|ANUAL"
        INTEGER intervalo "DEFAULT 1"
        TEXT dias_semana "ej. LU,MI,VI"
        TEXT fecha_fin_recurrencia
        INTEGER max_ocurrencias
        TEXT created_at
        TEXT updated_at
    }

    TAREAS {
        TEXT id PK "UUIDv4"
        TEXT titulo "NOT NULL"
        TEXT descripcion
        TEXT fecha_limite "UTC"
        TEXT prioridad "BAJA|MEDIA|ALTA"
        TEXT estado "PENDIENTE|EN_PROGRESO|COMPLETADA"
        TEXT categoria_id FK "SET NULL"
        TEXT subcategoria_id FK "SET NULL"
        TEXT created_at
        TEXT updated_at
    }

    RECORDATORIOS {
        TEXT id PK "UUIDv4"
        TEXT tipo_origen "EVENTO|TAREA"
        TEXT evento_id FK "UNIQUE, CASCADE, XOR"
        TEXT tarea_id FK "UNIQUE, CASCADE, XOR"
        INTEGER antelacion_minutos "CHECK 0..10080"
        TEXT fecha_disparo "NOT NULL, UTC"
        TEXT estado "PENDIENTE|ENTREGADO|PERDIDO|POSPUESTO|CANCELADO|ATENDIDO"
        INTEGER id_notificacion_so "UNIQUE, NOT NULL (int32 flet-notifications)"
        TEXT created_at
        TEXT updated_at
    }

    CONTACTOS {
        TEXT id PK "UUIDv4"
        TEXT nombre "NOT NULL"
        TEXT telefono
        TEXT correo
        TEXT notas
        TEXT etiqueta
        TEXT created_at
        TEXT updated_at
    }

    EVENTO_CONTACTO {
        TEXT evento_id PK,FK "CASCADE"
        TEXT contacto_id PK,FK "CASCADE"
        TEXT created_at
    }

    TAREA_CONTACTO {
        TEXT tarea_id PK,FK "CASCADE"
        TEXT contacto_id PK,FK "CASCADE"
        TEXT created_at
    }

    CONFIGURACION_SISTEMA {
        TEXT id PK "UUIDv4 (Singleton)"
        INTEGER minutos_posponer_defecto "DEFAULT 10"
        INTEGER antelacion_recordatorio_defecto_min "DEFAULT 15"
        INTEGER sonido_notificaciones "BOOLEAN 1"
        INTEGER mostrar_alertas_perdidas_inicio "BOOLEAN 1"
        INTEGER formato_24h "BOOLEAN 1"
        INTEGER primer_dia_semana "1..7"
        TEXT vista_inicial_agenda "DIA|SEMANA|MES|ANIO"
        INTEGER tema_oscuro "BOOLEAN 0"
        TEXT updated_at
    }
```

---

## 6. Diccionario de Restricciones de Integridad en Base de Datos (SQLite)

| Tabla | Restricción / Invariante | Regla Cubierta |
| :--- | :--- | :--- |
| Todas | Clave primaria `id TEXT PRIMARY KEY` (`UUIDv4`) y marcas `created_at`/`updated_at` en formato UTC ISO-8601. | `RN-10`, `RNF-03` |
| `EVENTOS` | `CHECK (todo_el_dia = 1 OR fecha_fin IS NULL OR fecha_fin >= fecha_inicio)` | `RN-01` |
| `EVENTOS` | Índice sobre `(fecha_inicio, fecha_fin)` para acelerar la validación estricta anti-solapamiento (`inicio_A < fin_B AND fin_A > inicio_B`). | `RN-11`, `RNF-07` |
| `RECORDATORIOS` | `CHECK (antelacion_minutos >= 0 AND antelacion_minutos <= 10080)` (máximo 7 días = 10,080 minutos). | `RN-03` |
| `RECORDATORIOS` | `CHECK ((evento_id IS NOT NULL AND tarea_id IS NULL AND tipo_origen = 'EVENTO') OR (tarea_id IS NOT NULL AND evento_id IS NULL AND tipo_origen = 'TAREA'))` (arco exclusivo XOR) + `UNIQUE(evento_id)` y `UNIQUE(tarea_id)`. | `RN-03` |
| `RECORDATORIOS` | Índice sobre `(estado, fecha_disparo)` para el barrido rápido de notificaciones `PENDIENTE` vencidas al iniciar (`PERDIDO`). | `RN-05`, `RNF-04` |
| `EVENTO_CONTACTO` / `TAREA_CONTACTO` | `ON DELETE CASCADE` únicamente en la tabla intermedia: eliminar un contacto borra sus vínculos pero **nunca** elimina los eventos ni tareas asociados. | `RN-13` |
| `EVENTOS` / `TAREAS` | `FOREIGN KEY (categoria_id) ... ON DELETE SET NULL` y `FOREIGN KEY (subcategoria_id) ... ON DELETE SET NULL`. | `RN-13` |
| `SUBCATEGORIAS` | Relación directa `categoria_id NOT NULL` hacia `CATEGORIAS`, impidiendo estructuralmente crear más de 2 niveles de anidamiento. | `RN-09` |

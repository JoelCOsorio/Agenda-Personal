-- =============================================================================
-- Esquema SQL Inicial — Agenda Personal y Académica Multiplataforma
-- Motor: SQLite 3 (con soporte FK estrictas y modo WAL)
-- Versión de esquema: 001 (v1.0)
-- Fecha: 23 de noviembre de 2026
-- Trazabilidad: RF-01..RF-24, RNF-03..RNF-07, RN-01..RN-14
-- =============================================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;

BEGIN TRANSACTION;

-- -----------------------------------------------------------------------------
-- 0. Control de Versiones de Migraciones
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    applied_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- -----------------------------------------------------------------------------
-- 1. CATEGORIAS (Nivel 1 — RN-09, RN-10)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS categorias (
    id          TEXT PRIMARY KEY,                                         -- UUIDv4
    nombre      TEXT NOT NULL CHECK (length(trim(nombre)) > 0),
    color_hex   TEXT NOT NULL DEFAULT '#3B82F6'
                     CHECK (color_hex GLOB '#[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]'),
    icono       TEXT,
    created_at  TEXT NOT NULL,                                            -- UTC ISO-8601
    updated_at  TEXT NOT NULL                                             -- UTC ISO-8601
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_categorias_nombre_nocase
    ON categorias (lower(trim(nombre)));

-- -----------------------------------------------------------------------------
-- 2. SUBCATEGORIAS (Nivel 2 estricto — RN-09, RN-10, RN-13)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subcategorias (
    id            TEXT PRIMARY KEY,                                       -- UUIDv4
    categoria_id  TEXT NOT NULL,
    nombre        TEXT NOT NULL CHECK (length(trim(nombre)) > 0),
    color_hex     TEXT CHECK (
                      color_hex IS NULL OR
                      color_hex GLOB '#[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]'
                  ),
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_subcategorias_categoria
    ON subcategorias (categoria_id);

CREATE UNIQUE INDEX IF NOT EXISTS ux_subcategorias_padre_nombre
    ON subcategorias (categoria_id, lower(trim(nombre)));

-- -----------------------------------------------------------------------------
-- 3. EVENTOS (Módulo de Agenda — RN-01, RN-04, RN-10, RN-11, RN-13)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS eventos (
    id               TEXT    PRIMARY KEY,                                 -- UUIDv4
    titulo           TEXT    NOT NULL CHECK (length(trim(titulo)) > 0),
    descripcion      TEXT,
    fecha_inicio     TEXT    NOT NULL,                                    -- UTC ISO-8601
    fecha_fin        TEXT,                                                -- UTC ISO-8601
    todo_el_dia      INTEGER NOT NULL DEFAULT 0 CHECK (todo_el_dia IN (0, 1)),
    ubicacion        TEXT,
    color_hex        TEXT CHECK (
                         color_hex IS NULL OR
                         color_hex GLOB '#[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]'
                     ),
    categoria_id     TEXT,
    subcategoria_id  TEXT,
    created_at       TEXT    NOT NULL,
    updated_at       TEXT    NOT NULL,

    -- RN-01: Coherencia temporal para eventos con rango horario
    CHECK (todo_el_dia = 1 OR fecha_fin IS NULL OR fecha_fin >= fecha_inicio),

    -- RN-13: Eliminar categoría o subcategoría no borra eventos (pasan a NULL / padre)
    FOREIGN KEY (categoria_id)    REFERENCES categorias(id)    ON DELETE SET NULL,
    FOREIGN KEY (subcategoria_id) REFERENCES subcategorias(id) ON DELETE SET NULL
);

-- Índice para vistas temporales (PROC-02) y validación anti-solapamiento (RN-11)
CREATE INDEX IF NOT EXISTS idx_eventos_rango
    ON eventos (fecha_inicio, fecha_fin);

CREATE INDEX IF NOT EXISTS idx_eventos_categoria
    ON eventos (categoria_id, subcategoria_id);

-- -----------------------------------------------------------------------------
-- 4. REGLAS_RECURRENCIA (0..1 por Evento — RF-06, RN-10, RN-11)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reglas_recurrencia (
    id                     TEXT    PRIMARY KEY,                           -- UUIDv4
    evento_id              TEXT    NOT NULL UNIQUE,
    frecuencia             TEXT    NOT NULL
                                   CHECK (frecuencia IN ('DIARIA', 'SEMANAL', 'MENSUAL', 'ANUAL')),
    intervalo              INTEGER NOT NULL DEFAULT 1 CHECK (intervalo >= 1),
    dias_semana            TEXT,                                          -- Ej.: 'LU,MI,VI'
    fecha_fin_recurrencia  TEXT,                                          -- Fecha límite opcional (ISO-8601)
    max_ocurrencias        INTEGER CHECK (max_ocurrencias IS NULL OR max_ocurrencias >= 1),
    created_at             TEXT    NOT NULL,
    updated_at             TEXT    NOT NULL,
    FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE
);

-- -----------------------------------------------------------------------------
-- 5. TAREAS (Módulo Independiente de Tareas — RF-14..16, RN-07, RN-12, RN-13)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tareas (
    id               TEXT PRIMARY KEY,                                    -- UUIDv4
    titulo           TEXT NOT NULL CHECK (length(trim(titulo)) > 0),
    descripcion      TEXT,
    fecha_limite     TEXT,                                                -- UTC ISO-8601 (opcional)
    prioridad        TEXT NOT NULL DEFAULT 'MEDIA'
                          CHECK (prioridad IN ('BAJA', 'MEDIA', 'ALTA')),
    estado           TEXT NOT NULL DEFAULT 'PENDIENTE'
                          CHECK (estado IN ('PENDIENTE', 'EN_PROGRESO', 'COMPLETADA')),
    categoria_id     TEXT,
    subcategoria_id  TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,

    -- RN-13: Eliminar categoría o subcategoría no borra tareas
    FOREIGN KEY (categoria_id)    REFERENCES categorias(id)    ON DELETE SET NULL,
    FOREIGN KEY (subcategoria_id) REFERENCES subcategorias(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_tareas_estado_fecha
    ON tareas (estado, fecha_limite);

CREATE INDEX IF NOT EXISTS idx_tareas_prioridad
    ON tareas (prioridad);

CREATE INDEX IF NOT EXISTS idx_tareas_categoria
    ON tareas (categoria_id, subcategoria_id);

-- -----------------------------------------------------------------------------
-- 6. RECORDATORIOS (Motor Unificado Agenda+Tareas — RN-02, RN-03, RN-05, RN-12)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS recordatorios (
    id                  TEXT    PRIMARY KEY,                              -- UUIDv4 (dominio / sync)
    id_notificacion_so  INTEGER NOT NULL UNIQUE
                                CHECK (id_notificacion_so >= 1 AND id_notificacion_so <= 2147483647),
    tipo_origen         TEXT    NOT NULL CHECK (tipo_origen IN ('EVENTO', 'TAREA')),
    evento_id           TEXT    UNIQUE,                                   -- Máx. 1 recordatorio por evento (RN-03)
    tarea_id            TEXT    UNIQUE,                                   -- Máx. 1 recordatorio por tarea (RN-03)
    antelacion_minutos  INTEGER NOT NULL DEFAULT 0
                                CHECK (antelacion_minutos >= 0 AND antelacion_minutos <= 10080), -- Máx. 7 días
    fecha_disparo       TEXT    NOT NULL,                                 -- UTC ISO-8601
    estado              TEXT    NOT NULL DEFAULT 'PENDIENTE'
                                CHECK (estado IN (
                                    'PENDIENTE', 'ENTREGADO', 'PERDIDO',
                                    'POSPUESTO', 'CANCELADO', 'ATENDIDO'
                                )),
    created_at          TEXT    NOT NULL,
    updated_at          TEXT    NOT NULL,

    -- Arco exclusivo XOR: pertenece exactamente a un Evento O a una Tarea
    CHECK (
        (tipo_origen = 'EVENTO' AND evento_id IS NOT NULL AND tarea_id IS NULL) OR
        (tipo_origen = 'TAREA'  AND tarea_id  IS NOT NULL AND evento_id IS NULL)
    ),

    -- Al eliminar el evento o la tarea, se elimina su recordatorio (RN-02)
    FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE,
    FOREIGN KEY (tarea_id)  REFERENCES tareas(id)  ON DELETE CASCADE
);

-- Índice crítico para el barrido de alertas vencidas/perdidas (RN-05) y planificador Linux
CREATE INDEX IF NOT EXISTS idx_recordatorios_estado_disparo
    ON recordatorios (estado, fecha_disparo);

-- -----------------------------------------------------------------------------
-- 7. CONTACTOS (Módulo de Contactos — RF-17..20, RN-08, RN-10, RN-13)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS contactos (
    id          TEXT PRIMARY KEY,                                         -- UUIDv4
    nombre      TEXT NOT NULL CHECK (length(trim(nombre)) > 0),
    telefono    TEXT,
    correo      TEXT,
    notas       TEXT,
    etiqueta    TEXT,                                                     -- Ej.: Profesor, Compañero, Familia
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_contactos_nombre
    ON contactos (lower(nombre));

CREATE INDEX IF NOT EXISTS idx_contactos_etiqueta
    ON contactos (etiqueta);

-- -----------------------------------------------------------------------------
-- 8. TABLAS ASOCIATIVAS N:M (Vinculación de Contactos — RF-18, RF-19, RN-13)
--    ON DELETE CASCADE solo elimina el vínculo; nunca elimina eventos ni tareas.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evento_contacto (
    evento_id    TEXT NOT NULL,
    contacto_id  TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    PRIMARY KEY (evento_id, contacto_id),
    FOREIGN KEY (evento_id)   REFERENCES eventos(id)   ON DELETE CASCADE,
    FOREIGN KEY (contacto_id) REFERENCES contactos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_evento_contacto_contacto
    ON evento_contacto (contacto_id);

CREATE TABLE IF NOT EXISTS tarea_contacto (
    tarea_id     TEXT NOT NULL,
    contacto_id  TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    PRIMARY KEY (tarea_id, contacto_id),
    FOREIGN KEY (tarea_id)    REFERENCES tareas(id)    ON DELETE CASCADE,
    FOREIGN KEY (contacto_id) REFERENCES contactos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tarea_contacto_contacto
    ON tarea_contacto (contacto_id);

-- -----------------------------------------------------------------------------
-- 9. CONFIGURACION_SISTEMA (Singleton de Ajustes — RF-23, RF-24, RN-14)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS configuracion_sistema (
    singleton_key                       INTEGER PRIMARY KEY DEFAULT 1 CHECK (singleton_key = 1),
    id                                  TEXT    NOT NULL UNIQUE,          -- UUIDv4 para sync futuro
    minutos_posponer_defecto            INTEGER NOT NULL DEFAULT 10
                                                CHECK (minutos_posponer_defecto >= 1 AND minutos_posponer_defecto <= 1440),
    antelacion_recordatorio_defecto_min INTEGER NOT NULL DEFAULT 15
                                                CHECK (antelacion_recordatorio_defecto_min >= 0 AND antelacion_recordatorio_defecto_min <= 10080),
    sonido_notificaciones               INTEGER NOT NULL DEFAULT 1 CHECK (sonido_notificaciones IN (0, 1)),
    mostrar_alertas_perdidas_inicio     INTEGER NOT NULL DEFAULT 1 CHECK (mostrar_alertas_perdidas_inicio IN (0, 1)),
    formato_24h                         INTEGER NOT NULL DEFAULT 1 CHECK (formato_24h IN (0, 1)),
    primer_dia_semana                   INTEGER NOT NULL DEFAULT 1 CHECK (primer_dia_semana BETWEEN 1 AND 7),
    vista_inicial_agenda                TEXT    NOT NULL DEFAULT 'MES'
                                                CHECK (vista_inicial_agenda IN ('DIA', 'SEMANA', 'MES', 'ANIO')),
    tema_oscuro                         INTEGER NOT NULL DEFAULT 0 CHECK (tema_oscuro IN (0, 1)),
    created_at                          TEXT    NOT NULL,
    updated_at                          TEXT    NOT NULL
);

-- -----------------------------------------------------------------------------
-- 10. TRIGGERS DE COHERENCIA JERÁRQUICA E INTEGRIDAD (RN-09, RN-13)
-- -----------------------------------------------------------------------------
-- Desvincula atómicamente categoría y subcategoría antes de borrar una categoría
-- padre, evitando estados intermedios durante el CASCADE a subcategorias (RN-13).
CREATE TRIGGER IF NOT EXISTS trg_categorias_desvincular_antes_borrar
BEFORE DELETE ON categorias
BEGIN
    UPDATE eventos
       SET categoria_id = NULL,
           subcategoria_id = NULL
     WHERE categoria_id = OLD.id;

    UPDATE tareas
       SET categoria_id = NULL,
           subcategoria_id = NULL
     WHERE categoria_id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_eventos_validar_subcategoria_ins
BEFORE INSERT ON eventos
WHEN NEW.subcategoria_id IS NOT NULL
BEGIN
    SELECT CASE
        WHEN NEW.categoria_id IS NULL OR NOT EXISTS (
            SELECT 1 FROM subcategorias s
            WHERE s.id = NEW.subcategoria_id AND s.categoria_id = NEW.categoria_id
        )
        THEN RAISE(ABORT, 'RN-09: La subcategoria seleccionada no pertenece a la categoria del evento.')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_eventos_validar_subcategoria_upd
BEFORE UPDATE OF categoria_id, subcategoria_id ON eventos
WHEN NEW.subcategoria_id IS NOT NULL
BEGIN
    SELECT CASE
        WHEN NEW.categoria_id IS NULL OR NOT EXISTS (
            SELECT 1 FROM subcategorias s
            WHERE s.id = NEW.subcategoria_id AND s.categoria_id = NEW.categoria_id
        )
        THEN RAISE(ABORT, 'RN-09: La subcategoria seleccionada no pertenece a la categoria del evento.')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_tareas_validar_subcategoria_ins
BEFORE INSERT ON tareas
WHEN NEW.subcategoria_id IS NOT NULL
BEGIN
    SELECT CASE
        WHEN NEW.categoria_id IS NULL OR NOT EXISTS (
            SELECT 1 FROM subcategorias s
            WHERE s.id = NEW.subcategoria_id AND s.categoria_id = NEW.categoria_id
        )
        THEN RAISE(ABORT, 'RN-09: La subcategoria seleccionada no pertenece a la categoria de la tarea.')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_tareas_validar_subcategoria_upd
BEFORE UPDATE OF categoria_id, subcategoria_id ON tareas
WHEN NEW.subcategoria_id IS NOT NULL
BEGIN
    SELECT CASE
        WHEN NEW.categoria_id IS NULL OR NOT EXISTS (
            SELECT 1 FROM subcategorias s
            WHERE s.id = NEW.subcategoria_id AND s.categoria_id = NEW.categoria_id
        )
        THEN RAISE(ABORT, 'RN-09: La subcategoria seleccionada no pertenece a la categoria de la tarea.')
    END;
END;

-- -----------------------------------------------------------------------------
-- 11. SEMILLA INICIAL IDEMPOTENTE (Ajustes por defecto — RF-24)
-- -----------------------------------------------------------------------------
INSERT OR IGNORE INTO configuracion_sistema (
    singleton_key, id, created_at, updated_at
) VALUES (
    1,
    '00000000-0000-4000-8000-000000000001',
    strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
);

INSERT OR IGNORE INTO schema_migrations (version, name)
VALUES (1, '001_initial_schema');

COMMIT;

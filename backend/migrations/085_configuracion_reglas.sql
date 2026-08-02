-- 085_configuracion_reglas.sql
--
-- QUÉ HACE: saca de código a base las reglas que hoy están hardcodeadas o no existen.
--   (a) parametros_empresa        — los escalares (base de días hábiles, cortes, vencimiento).
--   (b) reglas_vacaciones_escala  — la escala de días por antigüedad, que es una LISTA.
--   (c) tipos_ausencia            — + empresa_id nullable + cuenta_ausentismo.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 POR QUÉ DOS TABLAS TIPADAS Y NO UN KV GENÉRICO (clave, valor TEXT)
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- Un KV parece más flexible y es lo contrario: cada lectura vuelve con TEXT y hay que castear
-- en el service, así que el día que alguien guarde "veintidos" en base_dias_habiles el error
-- aparece en el cálculo del ausentismo y no al guardar. Con columnas tipadas el CHECK lo
-- rechaza en el INSERT, que es donde el usuario todavía está mirando la pantalla.
-- Y la escala NO ENTRA en un KV: es una lista de tramos de largo variable.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 empresa_id NULL = FILA GLOBAL. La lectura resuelve COALESCE(mi empresa, global).
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- Sin fila global habría que sembrar una fila por empresa al crearla, y una empresa nueva
-- nacería sin reglas hasta que alguien se acordara. Con la global, toda empresa tiene reglas
-- desde el minuto cero y solo se crea fila propia cuando de verdad difiere.
--
-- El índice único es PARCIAL porque en SQL NULL <> NULL: un `UNIQUE (empresa_id)` común
-- dejaría meter dos, tres o cien filas globales sin quejarse, y la lectura elegiría una al
-- azar. Van dos índices por tabla: uno para las filas con empresa y otro que fuerza que la
-- global sea UNA SOLA — `((empresa_id IS NULL)) WHERE empresa_id IS NULL` indexa la constante
-- TRUE, así que dos filas globales colisionan.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 EL PERÍODO VACACIONAL ES UN CONCEPTO NUEVO — ACÁ SOLO SE GUARDA EL VALOR
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- "Octubre a abril" NO es cuándo se GANAN los días ni cómo se mide la ANTIGÜEDAD: es cuándo
-- se pueden TOMAR. Son tres cosas distintas y el sistema hoy conoce las dos primeras y no la
-- tercera.
--
-- ESTA MIGRACIÓN Y ESTA SESIÓN SOLO PERSISTEN EL VALOR. NO HAY NINGUNA VALIDACIÓN que impida
-- cargar una licencia fuera de esa ventana, ni la va a haber hasta que se defina si BLOQUEA o
-- solo AVISA. Las dos opciones son razonables y tienen consecuencias opuestas sobre los
-- imports históricos (bloquear haría fallar la carga de licencias viejas fuera de ventana).
-- Quien vaya a implementarlo: definir eso PRIMERO.
--
-- Lo mismo vale para la escala, el corte de antigüedad, el primer año y el vencimiento: esta
-- migración los GUARDA y la UI los muestra, pero ningún cálculo los consume todavía. El único
-- valor que se cablea en esta tanda es base_dias_habiles (el "22" del ausentismo).
--
-- NO DESTRUCTIVA salvo por el reemplazo de tipos_ausencia_nombre_key, explicado abajo.
-- Idempotente (IF NOT EXISTS / ON CONFLICT). NO se ejecuta acá (la corre Franco).

BEGIN;

-- ── (a) parametros_empresa ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.parametros_empresa (
    id                          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    -- NULL = fila global (aplica a toda empresa que no tenga la suya). Ver encabezado.
    empresa_id                  UUID        REFERENCES public.empresas(id) ON DELETE CASCADE,

    base_dias_habiles           SMALLINT    NOT NULL DEFAULT 22,
    corte_antiguedad_mes        SMALLINT    NOT NULL DEFAULT 10,
    periodo_vacacional_desde_mes SMALLINT   NOT NULL DEFAULT 10,
    periodo_vacacional_hasta_mes SMALLINT   NOT NULL DEFAULT 4,
    primer_anio_mes_corte       SMALLINT    NOT NULL DEFAULT 7,
    primer_anio_dias            SMALLINT    NOT NULL DEFAULT 5,
    vencimiento_anios           SMALLINT    NOT NULL DEFAULT 4,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Los CHECK son la razón de tipar en vez de usar un KV: rechazan en el INSERT, no en el
    -- cálculo. Un 0 en base_dias_habiles haría división por cero en la tasa de ausentismo.
    CONSTRAINT pe_base_dias_check      CHECK (base_dias_habiles BETWEEN 1 AND 31),
    CONSTRAINT pe_corte_mes_check      CHECK (corte_antiguedad_mes BETWEEN 1 AND 12),
    CONSTRAINT pe_vac_desde_check      CHECK (periodo_vacacional_desde_mes BETWEEN 1 AND 12),
    CONSTRAINT pe_vac_hasta_check      CHECK (periodo_vacacional_hasta_mes BETWEEN 1 AND 12),
    CONSTRAINT pe_primer_anio_mes_check CHECK (primer_anio_mes_corte BETWEEN 1 AND 12),
    CONSTRAINT pe_primer_anio_dias_check CHECK (primer_anio_dias >= 0),
    CONSTRAINT pe_vencimiento_check    CHECK (vencimiento_anios > 0)
);

COMMENT ON TABLE public.parametros_empresa IS
    'Reglas escalares configurables por empresa. empresa_id NULL = fila global; la lectura resuelve COALESCE(fila de mi empresa, fila global). Ver migración 085.';
COMMENT ON COLUMN public.parametros_empresa.base_dias_habiles IS
    'Días hábiles por mes por empleado, denominador de la tasa de ausentismo (R10 y KPI 26). Era la constante _BASE_DIAS_HABILES=22 en services/reportes/_reporte_ausentismo.py.';
COMMENT ON COLUMN public.parametros_empresa.corte_antiguedad_mes IS
    'Mes contra el que se mide la antigüedad para ubicar al empleado en la escala de vacaciones. NINGÚN cálculo lo consume todavía (085).';
COMMENT ON COLUMN public.parametros_empresa.periodo_vacacional_desde_mes IS
    'Mes en que ABRE la ventana para TOMAR vacaciones. NO es cuándo se ganan los días ni cómo se mide la antigüedad — es un concepto nuevo. 085 solo guarda el valor: NO existe validación que impida cargar fuera de ventana, y no la habrá hasta definir si bloquea o solo avisa.';
COMMENT ON COLUMN public.parametros_empresa.periodo_vacacional_hasta_mes IS
    'Mes en que CIERRA la ventana para tomar vacaciones. Puede ser menor que el de apertura: la ventana cruza el año (octubre→abril). Sin validación asociada (ver 085).';
COMMENT ON COLUMN public.parametros_empresa.primer_anio_mes_corte IS
    'En el primer año, mes a partir del cual el ingreso otorga primer_anio_dias en vez del tramo completo de la escala. Sin cálculo asociado todavía (085).';
COMMENT ON COLUMN public.parametros_empresa.vencimiento_anios IS
    'Años que sobreviven los días no tomados antes de vencer. Sin cálculo asociado todavía (085).';

-- Una fila por empresa…
CREATE UNIQUE INDEX IF NOT EXISTS ux_parametros_empresa_por_empresa
    ON public.parametros_empresa (empresa_id) WHERE empresa_id IS NOT NULL;
-- …y UNA SOLA global. Sin este índice, NULL <> NULL deja entrar filas globales duplicadas.
CREATE UNIQUE INDEX IF NOT EXISTS ux_parametros_empresa_global
    ON public.parametros_empresa ((empresa_id IS NULL)) WHERE empresa_id IS NULL;

DROP TRIGGER IF EXISTS trg_parametros_empresa_updated_at ON public.parametros_empresa;
CREATE TRIGGER trg_parametros_empresa_updated_at
    BEFORE UPDATE ON public.parametros_empresa
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.parametros_empresa ENABLE ROW LEVEL SECURITY;

-- Semilla de la fila global con los valores VIGENTES hoy. Los defaults de las columnas ya los
-- repiten, pero la fila tiene que existir: sin ella la lectura no tendría de dónde hacer
-- COALESCE y toda empresa sin fila propia se quedaría sin reglas.
INSERT INTO public.parametros_empresa (empresa_id) VALUES (NULL)
ON CONFLICT DO NOTHING;

-- ── (b) reglas_vacaciones_escala ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.reglas_vacaciones_escala (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    -- NULL = tramo de la escala global. Ver encabezado.
    empresa_id       UUID        REFERENCES public.empresas(id) ON DELETE CASCADE,
    -- Antigüedad MÍNIMA (en años cumplidos) a partir de la cual rige `dias`.
    antiguedad_anios SMALLINT    NOT NULL,
    dias             SMALLINT    NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT rve_antiguedad_check CHECK (antiguedad_anios >= 0 AND antiguedad_anios <= 60),
    CONSTRAINT rve_dias_check       CHECK (dias > 0 AND dias <= 365)
);

COMMENT ON TABLE public.reglas_vacaciones_escala IS
    'Escala de días de vacaciones por antigüedad. Es una LISTA de tramos (por eso no entra en parametros_empresa): se agregan y quitan desde la UI. empresa_id NULL = escala global; una empresa con al menos un tramo propio usa SOLO los suyos, no la unión con la global. Ver migración 085.';
COMMENT ON COLUMN public.reglas_vacaciones_escala.antiguedad_anios IS
    'Años cumplidos a partir de los cuales rige este tramo. El tramo aplicable es el de MAYOR antiguedad_anios que no supere la del empleado. NINGÚN cálculo lo consume todavía (085).';

-- Un tramo por (empresa, antigüedad)…
CREATE UNIQUE INDEX IF NOT EXISTS ux_escala_por_empresa
    ON public.reglas_vacaciones_escala (empresa_id, antiguedad_anios) WHERE empresa_id IS NOT NULL;
-- …y en la global, un tramo por antigüedad. Acá el índice parcial NO es sobre la constante
-- (la escala global son VARIAS filas, a diferencia de parametros_empresa): lo que no puede
-- repetirse es el punto de corte, o dos tramos reclamarían la misma antigüedad.
CREATE UNIQUE INDEX IF NOT EXISTS ux_escala_global
    ON public.reglas_vacaciones_escala (antiguedad_anios) WHERE empresa_id IS NULL;

DROP TRIGGER IF EXISTS trg_reglas_vacaciones_escala_updated_at ON public.reglas_vacaciones_escala;
CREATE TRIGGER trg_reglas_vacaciones_escala_updated_at
    BEFORE UPDATE ON public.reglas_vacaciones_escala
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.reglas_vacaciones_escala ENABLE ROW LEVEL SECURITY;

-- Semilla de la escala global vigente: 14 días desde el ingreso, 21 desde los 5 años,
-- 28 desde los 15.
INSERT INTO public.reglas_vacaciones_escala (empresa_id, antiguedad_anios, dias) VALUES
    (NULL,  0, 14),
    (NULL,  5, 21),
    (NULL, 15, 28)
ON CONFLICT DO NOTHING;

-- ── (c) tipos_ausencia: empresa_id + cuenta_ausentismo ───────────────────────────────────
--
-- empresa_id AHORA y no cuando haga falta: hoy la tabla es un catálogo global y las 4 filas
-- base ya están referenciadas por solicitudes_ausencia.tipo_id. El día que dos empresas
-- quieran vocabularios distintos, agregar la columna después obligaría a crear tipos nuevos y
-- REASIGNAR el tipo_id de las ausencias históricas — una migración de datos sobre filas vivas.
-- Ahora cuestan cuatro líneas y las filas base quedan como globales (empresa_id NULL).

ALTER TABLE public.tipos_ausencia
    ADD COLUMN IF NOT EXISTS empresa_id        UUID REFERENCES public.empresas(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS cuenta_ausentismo BOOLEAN NOT NULL DEFAULT TRUE;

COMMENT ON COLUMN public.tipos_ausencia.empresa_id IS
    'NULL = tipo global, disponible para todas las empresas. Con valor, tipo propio de esa empresa. Ver migración 085.';
COMMENT ON COLUMN public.tipos_ausencia.cuenta_ausentismo IS
    'Si las ausencias de este tipo entran en la tasa de ausentismo. NO reemplaza a solicitudes_ausencia.justificada: son preguntas distintas. `justificada` es un HECHO de la instancia ("¿esta vez trajo certificado?"), esto es una POLÍTICA del tipo ("¿maternidad computa como ausentismo?"). Las cuatro combinaciones son reales, por eso son dos columnas. DEFAULT TRUE = comportamiento idéntico al previo a 085.';

-- 🔴 La UNIQUE global sobre `nombre` deja de servir apenas existe empresa_id: prohibiría que
-- dos empresas tengan cada una su "Licencia especial". Se reemplaza por el mismo par de
-- índices parciales que las tablas de arriba. Es el ÚNICO paso no aditivo de esta migración;
-- no puede perder datos (solo afloja una restricción), pero un rollback exigiría reponerla.
ALTER TABLE public.tipos_ausencia DROP CONSTRAINT IF EXISTS tipos_ausencia_nombre_key;

CREATE UNIQUE INDEX IF NOT EXISTS ux_tipos_ausencia_nombre_por_empresa
    ON public.tipos_ausencia (empresa_id, nombre) WHERE empresa_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_tipos_ausencia_nombre_global
    ON public.tipos_ausencia (nombre) WHERE empresa_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_tipos_ausencia_empresa
    ON public.tipos_ausencia (empresa_id) WHERE empresa_id IS NOT NULL;

COMMIT;

NOTIFY pgrst, 'reload schema';

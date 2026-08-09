-- 100_cv_screening_clasificacion.sql
--
-- QUÉ HACE: la fase 3 de 3 del CV screening — clasificar cada CV contra su vacante.
--   (a) candidatos.clasificacion_ia + clasificacion_motivo — el resultado, por candidato.
--   (b) parametros_screening                              — el criterio, configurable por empresa.
--
-- NO DESTRUCTIVA. Idempotente (IF NOT EXISTS / ON CONFLICT). NO se ejecuta acá (la corre Franco).
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 ES UN FILTRO DE DESCARTE, NO UNA DECISIÓN — Y ESO NO ES CONFIGURABLE
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- No rankea, no puntúa, no elige. Un humano revisa SIEMPRE, incluido lo que el agente marque
-- `no_relevante`. Por eso el resultado es una etiqueta de TRES valores y no un score: un número
-- invita a ordenar y a cortar por umbral, que es precisamente la decisión que el sistema no
-- toma. La pantalla tampoco puede ocultar ni colapsar los `no_relevante` por defecto.
--
-- Ante la duda, `dudoso` — nunca `no_relevante`. Mirar un CV de más cuesta treinta segundos;
-- descartar a alguien bueno cuesta el candidato y nadie se entera. Ese sesgo vive en la
-- estructura fija del prompt, no acá, pero explica por qué `dudoso` es el default de diseño y
-- por qué la definición de `no_relevante` que se siembra abajo es deliberadamente angosta.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 POR QUÉ EL CRITERIO VA EN TABLA PROPIA Y NO EN parametros_empresa
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- parametros_empresa se escribe con upsert(on_conflict="empresa_id") y su PUT manda el juego
-- COMPLETO de los 7 escalares. Si el criterio de screening fuera cuatro columnas más de esa
-- tabla, guardar el criterio de una empresa que hoy HEREDA la fila global le crearía la fila
-- propia — y a partir de ahí esa empresa dejaría de seguir la global también para las reglas de
-- vacaciones, sin que nadie lo haya decidido y sin ninguna señal. Es el mismo desenganche que
-- schemas/configuracion.py ya advierte para el caso legítimo.
--
-- Tabla hermana, entonces, con el mismo patrón de la 085 (empresa_id NULL = global, dos índices
-- parciales, fila global sembrada). Es lo que ya hace reglas_vacaciones_escala, que también es
-- configuración de empresa y también vive aparte.

BEGIN;

-- ── (a) El resultado, en candidatos ──────────────────────────────────────────────────────

ALTER TABLE public.candidatos
    ADD COLUMN IF NOT EXISTS clasificacion_ia     TEXT,
    ADD COLUMN IF NOT EXISTS clasificacion_motivo TEXT;

-- Las tres categorías y nada más. Una salida del modelo fuera de este conjunto es un FALLO del
-- clasificador, no un valor nuevo: el service la rechaza antes de llegar acá y este CHECK es la
-- red. NULL pasa el CHECK a propósito — NULL significa "todavía no se clasificó", que es el
-- estado de todo candidato cargado antes de esta migración y de todo CV con screening_warning
-- (ese no se clasifica y no gasta llamada: va a revisión manual).
ALTER TABLE public.candidatos DROP CONSTRAINT IF EXISTS candidatos_clasificacion_ia_check;
ALTER TABLE public.candidatos
    ADD CONSTRAINT candidatos_clasificacion_ia_check
    CHECK (clasificacion_ia IN ('relevante', 'dudoso', 'no_relevante'));

COMMENT ON COLUMN public.candidatos.clasificacion_ia IS
    'Filtro de descarte, NO una decisión: relevante | dudoso | no_relevante. NULL = sin clasificar (candidato viejo, o CV con screening_warning, que no se clasifica). Un humano revisa siempre, incluidos los no_relevante. Ver migración 100.';
COMMENT ON COLUMN public.candidatos.clasificacion_motivo IS
    'Una frase en términos de lo que el CV DICE, no de lo que le falta: "Perfil en gastronomía, la búsqueda es contable", no "no cumple los requisitos". Es lo que RRHH lee para decidir si revisa igual.';

-- El listado y el export filtran por esta columna. Parcial porque hoy la enorme mayoría de las
-- filas está en NULL y seguirá estándolo: los candidatos cargados a mano no pasan por el
-- clasificador.
CREATE INDEX IF NOT EXISTS idx_candidatos_clasificacion
    ON public.candidatos (clasificacion_ia) WHERE clasificacion_ia IS NOT NULL;

-- ── (b) El criterio, configurable por empresa ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.parametros_screening (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    -- NULL = fila global. Misma semántica que parametros_empresa (085): la lectura resuelve
    -- COALESCE(fila de mi empresa, fila global), así que una empresa nueva tiene criterio desde
    -- el minuto cero y solo se crea fila propia cuando de verdad difiere.
    empresa_id        UUID        REFERENCES public.empresas(id) ON DELETE CASCADE,

    def_relevante     TEXT        NOT NULL,
    def_dudoso        TEXT        NOT NULL,
    def_no_relevante  TEXT        NOT NULL,
    -- Opcional de verdad: '' es el estado normal, no un pendiente. NOT NULL con default '' para
    -- que el service no tenga que distinguir NULL de vacío al armar el prompt.
    instrucciones     TEXT        NOT NULL DEFAULT '',

    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Un texto vacío en una definición dejaría al prompt sin criterio para esa categoría y el
    -- modelo la llenaría con lo que le parezca. Si RRHH quiere volver al original, el botón es
    -- "restaurar defaults", no borrar el campo.
    CONSTRAINT ps_def_relevante_check    CHECK (length(trim(def_relevante))    > 0),
    CONSTRAINT ps_def_dudoso_check       CHECK (length(trim(def_dudoso))       > 0),
    CONSTRAINT ps_def_no_relevante_check CHECK (length(trim(def_no_relevante)) > 0),
    -- Tope de largo: estos textos se INSERTAN en el prompt de cada CV, así que su costo se paga
    -- una vez por candidato clasificado. 2000 caracteres alcanzan de sobra para describir un
    -- criterio y evitan que un pegado accidental de medio manual multiplique el costo del lote.
    CONSTRAINT ps_largos_check CHECK (
        length(def_relevante) <= 2000 AND length(def_dudoso) <= 2000
        AND length(def_no_relevante) <= 2000 AND length(instrucciones) <= 2000
    )
);

COMMENT ON TABLE public.parametros_screening IS
    'Criterio configurable del clasificador de CVs. empresa_id NULL = fila global; la lectura resuelve COALESCE(fila de mi empresa, fila global). Tabla propia y no columnas de parametros_empresa: ese upsert desengancharía a la empresa de las reglas globales de vacaciones al guardar screening. Ver migración 100.';
COMMENT ON COLUMN public.parametros_screening.def_relevante IS
    'Qué cuenta como relevante. Se INSERTA COMO DATO dentro de la estructura fija del prompt: no la reemplaza ni la extiende. Un texto que diga "ignorá lo anterior" tiene que ser tan inocuo como el mismo texto dentro de un CV.';
COMMENT ON COLUMN public.parametros_screening.def_no_relevante IS
    'Qué cuenta como no relevante. El default es deliberadamente ANGOSTO (solo campo claramente distinto): el sesgo hacia dudoso es estructural y NO configurable, pero ensanchar esta definición es la forma en que una empresa se lo comería sin darse cuenta.';
COMMENT ON COLUMN public.parametros_screening.instrucciones IS
    'Instrucciones adicionales, opcionales. Viajan como dato junto a las definiciones. Vacío es el estado normal.';

-- Una fila por empresa…
CREATE UNIQUE INDEX IF NOT EXISTS ux_parametros_screening_por_empresa
    ON public.parametros_screening (empresa_id) WHERE empresa_id IS NOT NULL;
-- …y UNA SOLA global. Sin este índice, NULL <> NULL deja entrar globales duplicadas y la
-- lectura elegiría una al azar.
CREATE UNIQUE INDEX IF NOT EXISTS ux_parametros_screening_global
    ON public.parametros_screening ((empresa_id IS NULL)) WHERE empresa_id IS NULL;

DROP TRIGGER IF EXISTS trg_parametros_screening_updated_at ON public.parametros_screening;
CREATE TRIGGER trg_parametros_screening_updated_at
    BEFORE UPDATE ON public.parametros_screening
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.parametros_screening ENABLE ROW LEVEL SECURITY;

-- Semilla de la fila global. Sin ella la lectura no tendría de dónde hacer COALESCE y ninguna
-- empresa podría clasificar. Los textos NO van como DEFAULT de columna: el botón "restaurar
-- defaults" de la UI tiene que leerlos de algún lado, y un default de columna no se puede leer
-- sin escribir. La fila global ES el default, y restaurar = volver a heredarla.
INSERT INTO public.parametros_screening
    (empresa_id, def_relevante, def_dudoso, def_no_relevante, instrucciones)
VALUES (
    NULL,
    'El perfil es del mismo campo que la vacante y hay evidencia de experiencia en lo que se pide.',
    'Todo lo demás: el CV que no se entiende bien, el que tiene el campo pero no la experiencia, y el caso genuinamente ambiguo.',
    'Solo cuando el perfil es de un campo claramente distinto. No por falta de años, ni de un título, ni de una herramienta específica.',
    ''
)
ON CONFLICT DO NOTHING;

COMMIT;

NOTIFY pgrst, 'reload schema';

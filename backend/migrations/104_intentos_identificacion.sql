-- 104_intentos_identificacion.sql
--
-- QUÉ HACE: tabla NUEVA que registra cada intento de identificación del link público de carga
-- de horas (la quinta ruta pública del sistema, donde alguien escribe un DNI sin autenticarse).
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 POR QUÉ NO VA A `auditoria`
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- `auditoria` es el log de ACCIONES DE NEGOCIO y su columna `usuario_id` apunta a `users`.
-- Acá NO hay usuario: el que escribe el DNI no tiene cuenta —`empleados.user_id` está 0/31— y
-- muchos intentos ni siquiera corresponden a una persona de la empresa. Meterlos ahí llenaría
-- la pantalla `/auditoria` de filas sin autor, rompería la semántica de "quién hizo qué" y
-- ensuciaría los filtros por entidad y por usuario que RRHH usa para otra cosa.
--
-- Son dos logs con propósitos distintos: uno responde "¿quién cambió este registro?" y este
-- responde "¿alguien está probando DNIs?".
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 EL DNI SE GUARDA EN CLARO, Y ES UNA DECISIÓN, NO UN DESCUIDO
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- Se evaluó guardar un SHA-256. NO se hizo, por dos motivos:
--   1. NO PROTEGERÍA NADA. Un DNI son 8 dígitos: 10^8 hashes se precomputan en segundos. Un
--      hash sin salt de un espacio tan chico es reversible, así que sería seguridad de teatro —
--      el mismo argumento por el que este repo descartó hashear el DNI en el lookup.
--   2. DESTRUIRÍA LA UTILIDAD. El propósito de la tabla es que RRHH pueda ver QUÉ se intentó:
--      "este DNI se probó 400 veces" o "esta IP probó 900 DNIs distintos". Con un hash se puede
--      contar, pero no se puede saber a quién están apuntando.
-- Es un LOG DE SEGURIDAD, no un dato de negocio: acceso restringido al rol admin, como
-- `auditoria`. 🚩 PENDIENTE DE PRODUCTO: definir una política de retención/purga. Una tabla
-- que crece sin techo con identificadores de personas ajenas a la empresa no puede quedar así
-- para siempre; hoy no se purga.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- `resultado` DISTINGUE LO QUE LA RESPUESTA HTTP NO PUEDE DISTINGUIR
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- Hacia afuera los cuatro modos de fallo salen por un rechazo ÚNICO —mismo status, mismo code,
-- mismo mensaje— para no darle a nadie un oráculo. Adentro hay que poder separarlos, o el log
-- no sirve para investigar: un pico de `sin_coincidencia` es enumeración, y un pico de `ok`
-- desde una sola IP es otra cosa.
--   ok               → identificó a un empleado
--   sin_coincidencia → ningún empleado con ese DNI
--   inactivo         → existe pero no está activo (baja)
--   sin_clientes     → existe y está activo, pero su empresa no tiene clientes que cargar
--   ambiguo          → el DNI matchea en MÁS DE UNA empresa (ver la nota de abajo)
--   bloqueado        → superó el límite de intentos POR DNI (20/hora). Sale por el MISMO
--                      rechazo que los demás y NO por un 429: un 429 sería un oráculo de
--                      segundo orden — le diría al que pregunta que ese dni se viene
--                      probando, que es justo lo que no hace falta confirmarle.
--
-- ⚠️ `ambiguo` existe porque `empleados` tiene UNIQUE (empresa_id, dni) y NO unique global: el
-- mismo DNI puede estar en dos sociedades del grupo. Hoy los 31 DNIs de producción son
-- distintos, así que es una guarda para el futuro, no un caso vivo.
--
-- SIN `updated_at` a propósito: es append-only. Una fila de log que se pueda editar deja de ser
-- un log. Por eso tampoco lleva trigger, igual que `auditoria`, `adjuntos` y `oauth_states` —
-- y por eso queda fuera del barrido de `test_triggers_updated_at` SOLA, sin declarar nada.
--
-- FKs con ON DELETE SET NULL: si mañana se borra un empleado o una empresa, el intento tiene
-- que sobrevivir. Un log que desaparece cuando se borra el objeto investigado no sirve.
--
-- NO DESTRUCTIVA: solo agrega. Idempotente. NO se ejecuta acá (la corre Franco).

BEGIN;

CREATE TABLE IF NOT EXISTS public.intentos_identificacion (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    dni text NOT NULL,
    resultado text NOT NULL,
    -- Los dos solo se llenan cuando el intento IDENTIFICÓ a alguien. En un fallo no hay a quién
    -- apuntar, y rellenarlos con lo que "se creía" sería inventar.
    empleado_id uuid,
    empresa_id uuid,
    ip text,
    user_agent text,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'intentos_identificacion_pkey') THEN
        ALTER TABLE public.intentos_identificacion
            ADD CONSTRAINT intentos_identificacion_pkey PRIMARY KEY (id);
    END IF;
END $$;

ALTER TABLE public.intentos_identificacion
    DROP CONSTRAINT IF EXISTS intentos_identificacion_resultado_check;
ALTER TABLE public.intentos_identificacion
    ADD CONSTRAINT intentos_identificacion_resultado_check
    CHECK (resultado = ANY (ARRAY['ok'::text, 'sin_coincidencia'::text, 'inactivo'::text,
                                  'sin_clientes'::text, 'ambiguo'::text, 'bloqueado'::text]));

ALTER TABLE public.intentos_identificacion
    DROP CONSTRAINT IF EXISTS intentos_identificacion_empleado_id_fkey;
ALTER TABLE public.intentos_identificacion
    ADD CONSTRAINT intentos_identificacion_empleado_id_fkey
    FOREIGN KEY (empleado_id) REFERENCES public.empleados(id) ON DELETE SET NULL;

ALTER TABLE public.intentos_identificacion
    DROP CONSTRAINT IF EXISTS intentos_identificacion_empresa_id_fkey;
ALTER TABLE public.intentos_identificacion
    ADD CONSTRAINT intentos_identificacion_empresa_id_fkey
    FOREIGN KEY (empresa_id) REFERENCES public.empresas(id) ON DELETE SET NULL;

-- Los tres índices son las tres preguntas que la tabla existe para responder:
--   "¿qué pasó recientemente?"      → created_at
--   "¿cuántas veces se probó ESTE DNI?"  → (dni, created_at)
--   "¿cuántos DNIs probó ESTA IP?"       → (ip, created_at)
CREATE INDEX IF NOT EXISTS idx_intentos_created ON public.intentos_identificacion USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_intentos_dni ON public.intentos_identificacion USING btree (dni, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_intentos_ip ON public.intentos_identificacion USING btree (ip, created_at DESC) WHERE (ip IS NOT NULL);

COMMIT;

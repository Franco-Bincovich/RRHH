-- 080_create_oauth_states.sql
--
-- POR QUÉ:
-- El flujo de autorización OAuth ocurre en DOS requests separados: uno genera la URL de
-- consentimiento del proveedor, y otro —el callback— llega cuando el proveedor redirige el
-- navegador de vuelta. Esta tabla guarda, entre esos dos momentos, un `state`: un nonce de un
-- solo uso que ata el callback a la sesión que efectivamente inició el flujo. Al volver, el
-- callback lo busca acá; si está, vigente y sin usar, la fila dice de qué usuario es y se
-- borra en el acto. La identidad del usuario sale SIEMPRE de esta fila, nunca del query param.
--
-- En serverless los dos requests pueden caer en procesos distintos, así que el state no puede
-- vivir en memoria: tiene que estar en la base para que cualquier instancia lo resuelva.
--
-- MODELO:
--   * state_hash: SHA-256 en hex del nonce crudo. UNIQUE, que además da el índice del lookup
--     (el callback busca exactamente por este valor y por nada más).
--   * user_id: de quién es el flujo en curso. FK a users, ON DELETE CASCADE (si el usuario se
--     va, sus flujos a medio hacer no tienen a quién conectar).
--   * proveedor: para qué integración es. Hoy solo 'google'; existe para que un segundo
--     proveedor no necesite otra tabla ni otra migración.
--   * expires_at: TTL corto (10 minutos, definido en services/_oauth_state.py). El flujo se
--     completa en segundos; el único paso humano es aceptar el consentimiento. Además los
--     authorization codes de Google expiran a los ~10 minutos, así que un TTL mayor no
--     compraría nada: el code ya estaría vencido.
--
-- ⚠️ SHA-256 ACÁ, bcrypt EN refresh_tokens (076) — NO es una inconsistencia:
--   * bcrypt es SALTEADO, o sea NO indexable. En 076 eso se puede pagar porque el refresh
--     token es un JWT que lleva el user_id en `sub`: se acota por usuario y se comparan pocas
--     filas con checkpw. Acá el callback llega SOLO con el state, sin ninguna identidad, así
--     que un esquema salteado obligaría a escanear todos los states pendientes corriendo
--     bcrypt en cada uno — y bcrypt es lento a propósito.
--   * SHA-256 es determinístico: el lookup es una igualdad sobre un índice único.
--   * Sin salt es correcto para este valor concreto: el nonce lo generamos nosotros con 256
--     bits de entropía (secrets.token_urlsafe(32)), así que no hay diccionario ni tabla
--     precomputada que lo alcance. El salt protege secretos de baja entropía; este no lo es.
--   * Lo que sí se conserva de 076: NUNCA se guarda el valor crudo.
--
-- RETENCIÓN (resuelta, no queda pendiente): las filas vencidas las borra
-- services/_oauth_state.generar, que en el mismo write que inserta un state nuevo hace
--     DELETE FROM public.oauth_states WHERE expires_at < now();
-- Se limpia en el camino que genera las filas, así que se autobalancea y no hace falta cron
-- (Vercel no tiene). Es higiene, no corrección: la verificación ya descarta los vencidos
-- mirando expires_at, así que una fila sin borrar no cambia ninguna decisión.
--
-- RLS habilitada sin policies (deny-all; acceso app-level con service_key), mismo criterio que
-- 079/078/066/061. Orden: CREATE TABLE -> PK -> UNIQUE -> FK -> INDEX. Tabla nueva, sin drift.
-- NO se ejecuta acá (la corre Franco).
--
-- 🔴 ORDEN DE DEPLOY: esta migración va ANTES que el código.

BEGIN;

-- ── TABLA ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.oauth_states (
    id         UUID        DEFAULT gen_random_uuid(),
    state_hash TEXT        NOT NULL,
    user_id    UUID        NOT NULL,
    proveedor  TEXT        NOT NULL DEFAULT 'google',
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── PK ──────────────────────────────────────────────────────────────────────

ALTER TABLE public.oauth_states ADD CONSTRAINT oauth_states_pkey PRIMARY KEY (id);

-- ── UNIQUE (además es el índice del lookup del callback) ────────────────────

ALTER TABLE public.oauth_states ADD CONSTRAINT oauth_states_state_hash_key UNIQUE (state_hash);

-- ── FK ──────────────────────────────────────────────────────────────────────

ALTER TABLE public.oauth_states ADD CONSTRAINT oauth_states_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

-- ── ÍNDICE (para la purga oportunista de vencidos) ──────────────────────────

CREATE INDEX IF NOT EXISTS idx_oauth_states_expires_at ON public.oauth_states (expires_at);

-- ── RLS (deny-all; acceso app-level vía service_key) ────────────────────────

ALTER TABLE public.oauth_states ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.oauth_states IS
    'Nonces de un solo uso del flujo de autorización OAuth. Guarda SHA-256, nunca el valor crudo.';
COMMENT ON COLUMN public.oauth_states.state_hash IS
    'SHA-256 hex del nonce. Determinístico a propósito: el callback lo busca por igualdad.';

COMMIT;

NOTIFY pgrst, 'reload schema';

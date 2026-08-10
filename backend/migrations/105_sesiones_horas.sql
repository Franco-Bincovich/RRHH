-- 105_sesiones_horas.sql
--
-- QUÉ HACE: tabla NUEVA que sostiene la identidad ENTRE el paso 1 del link público
-- (identificarse con el DNI) y el paso 2 (cargar horas o una licencia).
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 EL PROBLEMA QUE RESUELVE, Y POR QUÉ NO ALCANZABA NINGUNA ALTERNATIVA MÁS SIMPLE
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- El paso 2 tiene que saber DE QUIÉN son las horas. Las tres formas posibles eran:
--
--   (a) Que el paso 1 devuelva el `empleado_id` y el front lo mande en el paso 2.
--       DESCARTADA, y no por elegancia: es exactamente lo que rompe la condición #3 de las
--       rutas públicas ("la identidad sale de la fila persistida, nunca del request"). Con eso,
--       adivinar un DNI dejaría de ser el TECHO del daño y pasaría a ser el PISO: cualquiera
--       cargaría horas a nombre de cualquiera sin siquiera adivinar un DNI.
--
--   (b) Que el front reenvíe el DNI en cada carga. Funciona y mantiene la identidad server-side,
--       pero deja al paso 2 exactamente igual de débil que el paso 1 —el DNI es enumerable— y
--       además hace viajar un identificador personal en cada request de la sesión.
--
--   (c) ESTA: el paso 1 emite un TOKEN OPACO y el paso 2 lo presenta. La identidad se resuelve
--       contra esta tabla, nunca contra el request.
--
-- 🔴 LO QUE (c) COMPRA, Y ES EL PUNTO DE TODA LA SESIÓN: el paso 2 SÍ cumple las dos condiciones
-- que el paso 1 no puede cumplir. El token es un secreto real de 256 bits (`secrets.token_urlsafe`),
-- se guarda HASHEADO y tiene TTL. O sea: la debilidad de esta feature queda CONFINADA a la
-- identificación; las escrituras quedan detrás de un autenticador de verdad. Un atacante que
-- adivine un DNI ya no puede escribir sin además obtener un token de 256 bits.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- DIFERENCIAS DELIBERADAS CON `oauth_states` (mig 080), que es el molde
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- · NO es de un solo uso. El nonce de OAuth completa UN flujo y se quema; acá una sesión cubre
--   una sesión de trabajo real, donde la persona carga varias entradas del día o de la semana.
--   Quemarlo en la primera carga obligaría a re-tipear el DNI en cada renglón.
-- · TTL de 30 minutos (contra los 10 de OAuth): allá el único paso humano es aceptar un
--   consentimiento; acá la persona está completando un formulario varias veces.
-- · SÍ se guarda hasheado, igual que allá, y por el mismo motivo: contra 256 bits de entropía no
--   hay diccionario ni tabla precomputada, así que un SHA-256 sin salt alcanza. (Es lo contrario
--   del DNI de la mig 104, que se guarda en claro porque 8 dígitos se revierten en segundos.)
--
-- 🔴 FK COMPUESTA `(empleado_id, empresa_id) → empleados(id, empresa_id)`, no dos FKs sueltas.
-- Es la misma que ya usa `solicitudes_ausencia` (`sa_empleado_empresa_fk`). Garantiza EN LA BASE
-- que el par empleado/empresa de una sesión es coherente: sin ella, una fila podría decir
-- "empleado de ACME, empresa DOSUBA" y todo lo que se escriba con esa sesión quedaría imputado a
-- la sociedad equivocada. Es la invariante de la que depende toda la identidad del flujo.
--
-- La purga de vencidas corre en el camino que CREA sesiones, igual que `oauth_states`: se
-- autobalancea sin job periódico. Es higiene, no corrección — la verificación ya descarta por
-- `expires_at`.
--
-- NO DESTRUCTIVA: solo agrega. Idempotente. NO se ejecuta acá (la corre Franco).

BEGIN;

CREATE TABLE IF NOT EXISTS public.sesiones_horas (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    -- SHA-256 del token, NUNCA el token. De la base no sale nada con lo que autenticarse.
    token_hash text NOT NULL,
    empleado_id uuid NOT NULL,
    empresa_id uuid NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'sesiones_horas_pkey') THEN
        ALTER TABLE public.sesiones_horas ADD CONSTRAINT sesiones_horas_pkey PRIMARY KEY (id);
    END IF;
END $$;

-- El lookup del paso 2 entra por acá, y la unicidad es lo que hace que un token identifique a
-- UNA sesión y no a un conjunto.
CREATE UNIQUE INDEX IF NOT EXISTS ux_sesiones_horas_token ON public.sesiones_horas USING btree (token_hash);

-- Ver la nota de la FK compuesta en el encabezado.
ALTER TABLE public.sesiones_horas DROP CONSTRAINT IF EXISTS sesiones_horas_empleado_empresa_fk;
ALTER TABLE public.sesiones_horas
    ADD CONSTRAINT sesiones_horas_empleado_empresa_fk
    FOREIGN KEY (empleado_id, empresa_id) REFERENCES public.empleados(id, empresa_id) ON DELETE CASCADE;

-- Sostiene la purga de vencidas.
CREATE INDEX IF NOT EXISTS idx_sesiones_horas_expira ON public.sesiones_horas USING btree (expires_at);

COMMIT;

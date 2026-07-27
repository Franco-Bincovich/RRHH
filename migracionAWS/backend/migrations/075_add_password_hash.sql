-- 075 — password_hash en users: habilita el auth propio post-Supabase.
--
-- Hoy la credencial NO existe en la base de RRHH: vive en auth.users de Supabase (gotrue),
-- un schema al que el backend solo llega por el SDK. Verificado: `password_hash` tiene CERO
-- ocurrencias en las 74 migraciones y en db/schema.sql. Al salir de Supabase, sin esta
-- columna no hay dónde guardar la contraseña y el login es imposible.
--
-- SIN BACKFILL, A PROPÓSITO: los hashes bcrypt de Supabase no se pueden leer por el SDK, así
-- que no hay nada que migrar. Los usuarios se recrean tras la migración de datos (alta con
-- contraseña temporal + must_change_password=true, que es el flujo que el ABM ya tiene).
-- Por eso la columna es NULLABLE: un perfil sin password_hash no puede loguear
-- (authenticate_user lo rechaza) pero tampoco rompe la migración de las filas existentes.

ALTER TABLE public.users ADD COLUMN password_hash TEXT;

COMMENT ON COLUMN public.users.password_hash IS
    'Hash bcrypt de la contraseña. NULL = usuario sin credencial local (no puede loguear). '
    'Poblado por el ABM de usuarios; nunca se guarda ni loguea la contraseña en claro.';


-- ─────────────────────────────────────────────────────────────────────────────
-- LO SIGUIENTE NO ESTABA EN EL PEDIDO PERO SIN ESTO EL AUTH PROPIO NO ARRANCA.
-- Revisar y decidir antes de correr — están separados del ADD COLUMN a propósito.
-- ─────────────────────────────────────────────────────────────────────────────

-- (1) La FK a auth.users. Hoy existe (db/schema.sql:1040):
--
--     ALTER TABLE public.users ADD CONSTRAINT users_id_fkey
--         FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;
--
-- Mientras viva, TODO INSERT en public.users exige una fila previa en auth.users — o sea,
-- exige Supabase. Es el bloqueo duro del auth propio: con la columna password_hash puesta
-- y esta FK viva, crear un usuario sigue siendo imposible sin gotrue.
--
-- Ese ON DELETE CASCADE además es un mecanismo de negocio VIVO, no un detalle de schema:
-- usuario_service.eliminar_usuario (services/usuario_service.py:145) borra auth.users y
-- confía en el cascade para limpiar public.users. Al dropear la FK, ese DELETE deja de
-- limpiar nada y el service PASA A TENER QUE BORRAR public.users a mano. Dropear esto sin
-- tocar usuario_service deja usuarios huérfanos, sin error visible.
--
-- No se dropea acá porque el orden importa: primero el service nuevo, después la FK.
-- Ver README_AUTH.md ("el punto más delicado").
--
--     ALTER TABLE public.users DROP CONSTRAINT users_id_fkey;

-- (2) El id no se autogenera. public.users.id es `uuid NOT NULL` sin DEFAULT: siempre lo
-- proveyó gotrue (usuario_service.py:79 toma el uid de la respuesta de auth.admin.create_user).
-- Sin Supabase, el INSERT tiene que generar el id — en la base o en la app. Acá, en la base:
--
--     ALTER TABLE public.users ALTER COLUMN id SET DEFAULT gen_random_uuid();
--
-- gen_random_uuid() es built-in desde PG13 (RDS 13+ lo tiene sin extensión).
-- Alternativa: generar el UUID en Python y pasarlo explícito en el INSERT.

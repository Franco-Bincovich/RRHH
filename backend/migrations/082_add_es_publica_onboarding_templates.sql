-- 082_add_es_publica_onboarding_templates.sql
--
-- QUÉ HACE: agrega la visibilidad pública/privada a las plantillas de onboarding.
--
-- POR QUÉ. Las plantillas las crean y guardan los usuarios de RRHH, y hasta ahora todas eran
-- de todos: no había forma de tener un borrador sin que apareciera en la lista de los demás
-- —ni de que se usara como plantilla por defecto para onboardear gente de verdad—.
--
-- 🔴 DEFAULT true, Y NO ES UNA PREFERENCIA ESTÉTICA. Hoy todos ven todas las plantillas: ese
-- es el comportamiento vigente, y una migración no puede cambiarlo por su cuenta. Con DEFAULT
-- false, correr esta migración haría desaparecer en silencio todas las plantillas existentes
-- de la vista de todos menos su autor — y las que tienen `created_by` NULL (todas las
-- anteriores al cableado del autor, commit ef2bb5c) no serían de nadie. Compartir es el
-- estado actual; privado es un opt-out DELIBERADO, de a una plantilla y por decisión de su
-- autor.
--
-- NOT NULL porque no existe la "visibilidad indefinida": una plantilla se ve o no se ve, y un
-- tercer estado obligaría a cada query a decidir qué hacer con él.
--
-- CÓMO SE COMPONE (la regla vive en services/_template_scope.py, no acá):
--     empresa PRIMERO (WHERE de la query) ∩ es_publica OR created_by = yo OR created_by IS NULL
-- `created_by IS NULL` cuenta como pública a propósito: la FK del autor es ON DELETE SET NULL,
-- así que borrar un usuario dejaría sus plantillas privadas SIN DUEÑO, y con un filtro por
-- autor no las vería nadie nunca más. Es la única salida que no deja filas inalcanzables.
--
-- NO DESTRUCTIVA: agrega una columna con default. No toca datos existentes, no cambia lo que
-- ve nadie (default = comportamiento actual) y es segura de correr con la aplicación arriba.
--
-- ⚠️ ORDEN DE DEPLOY: esta migración va ANTES que el código. El código nuevo lee `es_publica`
-- en el SELECT de los dos endpoints de lectura; si sale primero, esas queries piden una
-- columna que no existe y PostgREST responde 400 42703. Al revés no hay problema: la columna
-- con su default es inerte para el código viejo.

ALTER TABLE public.onboarding_templates
    ADD COLUMN IF NOT EXISTS es_publica boolean NOT NULL DEFAULT true;

COMMENT ON COLUMN public.onboarding_templates.es_publica IS
    'true = la ven todos los usuarios de la empresa; false = solo su autor (created_by). Un created_by NULL se trata como pública: la FK es ON DELETE SET NULL y si no, quedaría inalcanzable.';

-- Índice parcial sobre el único corte que la columna habilita: "las privadas". Parcial porque
-- el default es true, así que un índice completo indexaría casi todas las filas para nada.
CREATE INDEX IF NOT EXISTS idx_onboarding_templates_privadas
    ON public.onboarding_templates (empresa_id, created_by) WHERE es_publica = false;

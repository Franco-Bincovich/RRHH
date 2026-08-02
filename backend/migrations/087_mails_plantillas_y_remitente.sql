-- 087_mails_plantillas_y_remitente.sql
--
-- QUÉ HACE: todo lo que el envío de mails por Gmail necesita en la base. Tres piezas, UNA sola
-- migración a propósito: son el mismo cambio funcional y partirlas obligaría a coordinar tres
-- pasos de deploy en vez de uno.
--
--   (a) usuario_integraciones  — + es_remitente_sistema (la casilla del sistema) + scopes.
--   (b) plantillas_mail        — las plantillas que RRHH escribe. TABLA NUEVA.
--   (c) mail_enviado           — qué se mandó, a quién y con qué texto. TABLA NUEVA.
--
-- NO ES DESTRUCTIVA: dos columnas nuevas con default y dos tablas nuevas. No borra ni reescribe
-- ninguna fila existente.
--
-- 🚩 ORDEN RESPECTO DE LA 086: la 086 (empleado_superior_pendiente) TODAVÍA NO SE CORRIÓ.
-- Corre PRIMERO la 086 y después esta. Son independientes entre sí —ninguna toca lo de la
-- otra— pero el orden numérico es el contrato del directorio y saltearlo deja un hueco que la
-- próxima persona va a tener que investigar.
--
-- =====================================================================================
-- (a) LA CASILLA DEL SISTEMA
-- =====================================================================================
-- `usuario_integraciones` es POR USUARIO y no tiene empresa_id. Sin una casilla designada, un
-- mail saldría de la cuenta personal del humano que apretó el botón, y un proceso automático NO
-- TENDRÍA DE QUÉ CUENTA SALIR: no hay user_id que aportar.
--
-- El motivo decisivo, igual, es otro: que el circuito de PRUEBA y el REAL sean el mismo. Con la
-- casilla designada, pasar de la cuenta personal de prueba a la casilla de RRHH es reconectar
-- otra cuenta al mismo usuario técnico — cero código, y lo que se probó es lo que va a
-- producción. Con "sale del que disparó", son dos circuitos distintos y el segundo queda sin
-- probar hasta el día que se usa de verdad.
--
-- 🔴 EL ÍNDICE ES ÚNICO PARCIAL, y es la parte que no se puede simplificar. Un UNIQUE común
-- sobre `es_remitente_sistema` prohibiría tener dos integraciones en `false`, o sea todas menos
-- una. Lo que hay que garantizar es que haya UNA SOLA en `true`, y eso es exactamente un índice
-- único sobre una constante, filtrado por la condición. Mismo patrón que la migración 085 usa
-- para la fila global de parametros_empresa, por el mismo motivo estructural.
--
-- `scopes` guarda los permisos REALMENTE concedidos (el usuario puede destildar en la pantalla
-- de consentimiento). Es lo que permite avisar "esta cuenta no puede enviar, reconectá" ANTES,
-- en vez de un 403 en medio de un envío. NULL = conectada antes de que la columna existiera,
-- que a los efectos es "no sabemos, asumimos que no puede".

ALTER TABLE public.usuario_integraciones
    ADD COLUMN IF NOT EXISTS es_remitente_sistema boolean NOT NULL DEFAULT false;

ALTER TABLE public.usuario_integraciones
    ADD COLUMN IF NOT EXISTS scopes text[];

DROP INDEX IF EXISTS public.uq_integracion_remitente_sistema;
CREATE UNIQUE INDEX uq_integracion_remitente_sistema
    ON public.usuario_integraciones ((es_remitente_sistema))
    WHERE es_remitente_sistema;

COMMENT ON COLUMN public.usuario_integraciones.es_remitente_sistema IS
    'Casilla desde la que salen los mails del sistema. Como máximo UNA en true (índice único parcial). Ver migración 087.';
COMMENT ON COLUMN public.usuario_integraciones.scopes IS
    'Scopes OAuth realmente concedidos. NULL = integración anterior a esta columna; se asume sin permiso de envío.';

-- =====================================================================================
-- (b) PLANTILLAS
-- =====================================================================================
-- 🔴 empresa_id NULLABLE = PLANTILLA GLOBAL. Mismo patrón que la migración 085: la lectura
-- resuelve COALESCE(la de mi empresa, la global). Se pueden sembrar las plantillas base UNA vez
-- y cada empresa pisa solo las que quiera cambiar. Con NOT NULL habría que duplicarlas por
-- empresa desde el día uno — con 1 empresa en producción eso se ve gratis y deja de serlo con
-- la segunda.
--
-- Por qué POR EMPRESA y no global a secas: una plantilla es CONTENIDO (lleva el nombre de la
-- empresa, su tono, su firma), no una categoría del mundo. Es el criterio que separó a
-- onboarding_templates (por empresa, contenido) de tipos_ausencia (global, categoría).
--
-- 🔴 `contexto` ES LA PIEZA CENTRAL DEL DISEÑO. Una variable {{nombre_empleado}} solo tiene
-- sentido si el mail se manda EN CONTEXTO de un empleado. El contexto declara de qué habla la
-- plantilla, y de ahí sale QUÉ VARIABLES puede usar. Es texto y no un FK a un catálogo en base
-- porque el catálogo vive EN CÓDIGO (services/mailer/_variables.py): son claves de programa, no
-- datos que alguien edite, y una tabla de contextos invitaría a agregar uno sin el resolver que
-- lo hace funcionar.
--
-- `cuerpo` es MARKDOWN, no HTML. El HTML lo genera el servidor al enviar. Dejar que el usuario
-- escriba HTML abriría una superficie de inyección hacia el buzón del destinatario, y este repo
-- no tiene ninguna dependencia de sanitización (ni la va a sumar). Con Markdown, el conjunto de
-- HTML posible lo genera nuestro código: la superficie no se acota, desaparece.
--
-- NO SE VERSIONA, a propósito. La pregunta real es "¿qué le llegó a Fulano?", no "¿cómo era la
-- plantilla en marzo?" — y esa la contesta `mail_enviado`, que guarda el texto ya renderizado.
-- Versionar respondería la segunda y para la primera obligaría a reconstruir el render con
-- valores que ya no existen (el empleado cambió de área desde entonces).

CREATE TABLE IF NOT EXISTS public.plantillas_mail (
    id          uuid        NOT NULL DEFAULT gen_random_uuid(),
    empresa_id  uuid        REFERENCES public.empresas(id) ON DELETE CASCADE,
    clave       text        NOT NULL,
    contexto    text        NOT NULL,
    asunto      text        NOT NULL,
    cuerpo      text        NOT NULL,
    activa      boolean     NOT NULL DEFAULT true,
    created_at  timestamp with time zone NOT NULL DEFAULT now(),
    updated_at  timestamp with time zone NOT NULL DEFAULT now()
);

ALTER TABLE public.plantillas_mail DROP CONSTRAINT IF EXISTS plantillas_mail_pkey;
ALTER TABLE public.plantillas_mail ADD CONSTRAINT plantillas_mail_pkey PRIMARY KEY (id);

-- Dos índices únicos parciales por el mismo motivo que en la 085: en SQL NULL <> NULL, así que
-- un UNIQUE(empresa_id, clave) común NO impediría dos globales con la misma clave.
DROP INDEX IF EXISTS public.uq_plantilla_empresa_clave;
CREATE UNIQUE INDEX uq_plantilla_empresa_clave
    ON public.plantillas_mail (empresa_id, clave) WHERE empresa_id IS NOT NULL;

DROP INDEX IF EXISTS public.uq_plantilla_global_clave;
CREATE UNIQUE INDEX uq_plantilla_global_clave
    ON public.plantillas_mail (clave) WHERE empresa_id IS NULL;

COMMENT ON TABLE public.plantillas_mail IS
    'Plantillas de mail editables por RRHH. empresa_id NULL = plantilla global; la lectura resuelve COALESCE(la de mi empresa, la global). El cuerpo es Markdown, NO HTML. Ver migración 087.';

-- =====================================================================================
-- (c) LOG DE ENVÍOS
-- =====================================================================================
-- Tres cosas distintas, y las tres pesan:
--   1. "No me llegó" — sin esto la respuesta es un encogimiento de hombros.
--   2. No mandar dos veces — un reintento tras un timeout duplicaría sin este registro.
--   3. Auditoría — mandar un mail a nombre de la empresa ES una acción, y en este repo toda
--      acción se audita. Sin esto sería la única escritura hacia afuera sin rastro.
--
-- 🔴 `asunto_render` y `cuerpo_render` guardan lo que REALMENTE se mandó. Es lo que reemplaza
-- al versionado de plantillas: contesta la pregunta exacta, sin reconstruir nada.
--
-- ⚠️ ESTA TABLA CONTIENE DATOS PERSONALES POR DEFINICIÓN — nombre, dirección de mail y el cuerpo
-- entero del mensaje. Consecuencias que NO son negociables:
--   · se lee gateada por Seccion.CONFIGURACION, nunca abierta;
--   · NO SE EXPORTA. No hay endpoint de export para esta tabla y no se le agrega uno "por
--     comodidad": un Excel con el texto de todos los mails enviados es exactamente el archivo
--     que no se quiere que circule por WhatsApp.
--   · cuando el volumen moleste, la salida es una política de retención (borrar el cuerpo a los
--     N meses, conservar el resto), no dejar de registrar.
--
-- `empleado_id` es ON DELETE SET NULL y no CASCADE: si el empleado se borra, el hecho de que se
-- le mandó un mail SIGUIÓ PASANDO. Un log que se borra solo no es un log.

CREATE TABLE IF NOT EXISTS public.mail_enviado (
    id              uuid        NOT NULL DEFAULT gen_random_uuid(),
    empresa_id      uuid        REFERENCES public.empresas(id) ON DELETE SET NULL,
    plantilla_clave text,
    contexto        text,
    empleado_id     uuid        REFERENCES public.empleados(id) ON DELETE SET NULL,
    destinatario    text        NOT NULL,
    remitente       text,
    asunto_render   text        NOT NULL,
    cuerpo_render   text        NOT NULL,
    estado          text        NOT NULL DEFAULT 'enviado',
    error           text,
    gmail_message_id text,
    enviado_por     uuid,
    created_at      timestamp with time zone NOT NULL DEFAULT now()
);

ALTER TABLE public.mail_enviado DROP CONSTRAINT IF EXISTS mail_enviado_pkey;
ALTER TABLE public.mail_enviado ADD CONSTRAINT mail_enviado_pkey PRIMARY KEY (id);

ALTER TABLE public.mail_enviado DROP CONSTRAINT IF EXISTS mail_enviado_estado_check;
ALTER TABLE public.mail_enviado ADD CONSTRAINT mail_enviado_estado_check
    CHECK (estado IN ('enviado', 'fallido'));

-- El índice que sostiene la IDEMPOTENCIA: "¿ya le mandé ESTA plantilla a ESTA persona hoy?".
-- No es UNIQUE a propósito — reenviar a mano el mismo mail es legítimo y no se prohíbe desde la
-- base; lo que se hace es DETECTARLO y avisar. Una UNIQUE convertiría un reenvío deliberado en
-- un error de Postgres.
CREATE INDEX IF NOT EXISTS idx_mail_enviado_idempotencia
    ON public.mail_enviado (plantilla_clave, empleado_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mail_enviado_empresa
    ON public.mail_enviado (empresa_id, created_at DESC);

COMMENT ON TABLE public.mail_enviado IS
    'Qué mail se envió, a quién y con qué texto ya renderizado. CONTIENE DATOS PERSONALES: gateado por CONFIGURACION y SIN endpoint de export. Ver migración 087.';

-- 098_candidatos_desde_gmail.sql
--
-- QUÉ HACE: le da a `candidatos` la identidad del CV que entró por mail
-- (`gmail_message_id` + `cv_sha256`), su índice ÚNICO de idempotencia, y agrega `'gmail'` al
-- CHECK de `fuente`.
--
-- NO ES DESTRUCTIVA: agrega dos columnas nullable, un índice y AMPLÍA un CHECK (no lo restringe).
-- Ninguna fila existente deja de cumplirlo. Corre en una transacción.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 🔴 LA CLAVE ES EL HASH DEL CONTENIDO, NO EL `attachmentId` DE GMAIL
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- El candidato obvio para la clave era `(empresa_id, gmail_message_id, attachment_id)`. **No
-- sirve, y es la trampa peor de todas: compila, se lee razonable y no protege nada.** El
-- `attachmentId` está scopeado a UNA lectura del mensaje —la API no garantiza que dos
-- `messages.get` del mismo mail devuelvan el mismo id— así que la segunda corrida traería otro
-- valor, la constraint no chocaría, y se crearía el candidato duplicado. La documentación de
-- Gmail es explícita: hay que guardar el `messageId`, el nombre del archivo y **un hash que uno
-- calcule**, nunca el `attachmentId` como clave de largo plazo.
--
-- `cv_sha256` se calcula sobre los BYTES ya decodificados. Como efecto secundario buscado,
-- también dedupe el mismo CV mandado dos veces en el mismo mail (adjuntar dos veces el archivo
-- es un error de usuario común).
--
-- ⚠️ NO se usó `(empresa_id, cv_sha256)` sin el mensaje: dos personas distintas pueden mandar
-- el MISMO archivo (una plantilla de CV descargada del mismo lugar, un CV reenviado por un
-- referente). Bloquear eso perdería una postulación real. El mensaje acota la unicidad a "este
-- adjunto, de este mail", que es lo que se quiere: reprocesar la casilla no duplica.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 🔴 EL ÚNICO TIENE QUE TOLERAR NULLs, Y EN POSTGRES ESO ES GRATIS — PERO HAY QUE SABERLO
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- Los candidatos cargados A MANO (el formulario de la ficha de la vacante) no tienen ni
-- `gmail_message_id` ni `cv_sha256`: los dos quedan NULL. En Postgres, **un índice único NO
-- considera iguales a dos NULL** (a diferencia de un `UNIQUE NULLS NOT DISTINCT`, que es
-- opcional y NO se usa acá), así que N candidatos manuales conviven sin colisionar entre sí.
-- Igual se agrega el `WHERE ... IS NOT NULL`: hace el índice PARCIAL —más chico y solo sobre
-- las filas que vienen de Gmail— y sobre todo deja escrita la intención, para que nadie lo
-- "corrija" a `NULLS NOT DISTINCT` y rompa el alta manual desde el segundo candidato.
--
-- ⚠️ `empresa_id` va EN la clave aunque el mensaje ya sea único por buzón: la casilla es una
-- sola para todo el sistema, pero un mismo mail podría llegar a resolverse contra vacantes de
-- empresas distintas si algún día hay más de una casilla. Con la empresa adentro, esa puerta
-- queda cerrada sin costo.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- `fuente = 'gmail'`
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- El CHECK actual admite linkedin | referido | web | consultora | espontanea | otra. Sin
-- `'gmail'`, el INSERT del candidato creado desde la casilla **falla con una violación de CHECK**
-- y el CV se pierde. Se REEMPLAZA el constraint (no se puede extender in place); la lista nueva
-- es la vieja MÁS un valor, así que ninguna fila existente puede dejar de cumplirlo.

BEGIN;

-- 1. La identidad del CV que entró por mail. Nullable: los candidatos manuales no la tienen.
ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS gmail_message_id TEXT;
ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS cv_sha256 TEXT;

-- 2. Idempotencia. PARCIAL: solo indexa lo que vino de Gmail (ver la nota de los NULLs).
CREATE UNIQUE INDEX IF NOT EXISTS candidatos_cv_gmail_uq
    ON candidatos (empresa_id, gmail_message_id, cv_sha256)
 WHERE gmail_message_id IS NOT NULL AND cv_sha256 IS NOT NULL;

-- 3. Para listar "los que entraron por esta corrida" sin escanear la tabla.
CREATE INDEX IF NOT EXISTS idx_candidatos_gmail_message
    ON candidatos (gmail_message_id) WHERE gmail_message_id IS NOT NULL;

-- 4. `fuente` acepta 'gmail'. La lista nueva CONTIENE a la vieja: nada existente se invalida.
ALTER TABLE candidatos DROP CONSTRAINT IF EXISTS candidatos_fuente_check;
ALTER TABLE candidatos ADD CONSTRAINT candidatos_fuente_check
    CHECK (fuente::text = ANY (ARRAY['linkedin', 'referido', 'web', 'consultora',
                                     'espontanea', 'otra', 'gmail']::text[]));

COMMIT;

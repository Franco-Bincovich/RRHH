-- 091_triggers_updated_at_faltantes.sql
--
-- QUÉ HACE: crea el trigger `updated_at` de las DOS tablas que nunca lo tuvieron en
-- producción — `usuario_integraciones` (mig 032) y `plantillas_mail` (mig 087).
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- ESTO NO ES DEUDA DE LA MIGRACIÓN A AWS: ES UN BUG VIVO EN SUPABASE HOY
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- Las dos tablas declaran `updated_at timestamptz DEFAULT now()`, así que la columna se
-- POBLA en el alta y después NO SE MUEVE NUNCA. No hay error, no hay warning: el dato dice
-- que la fila no se toca desde que nació. En `usuario_integraciones` eso es exactamente al
-- revés de la verdad — es la tabla del token de Google, que se reescribe en cada refresh.
--
-- Verificado contra el catálogo vivo (3/8/2026): de las cinco tablas con `updated_at` que
-- faltaban en el script de RDS, TRES ya tienen su trigger acá porque sus propias migraciones
-- lo declararon (`vacaciones_pendientes` en la 083, `parametros_empresa` y
-- `reglas_vacaciones_escala` en la 085). Las otras dos no lo declararon. Esta migración
-- cubre SOLO esas dos: correrla no toca las tres que ya están bien.
--
-- ⚠️ ES OTRO ARCHIVO QUE EL 077, Y TIENE QUE SERLO.
-- `migracionAWS/backend/migrations/077_recrear_triggers_updated_at.sql` es el script de la
-- base NUEVA (RDS) y no corre nunca contra Supabase. Las cinco entran allá porque allá se
-- construye todo de cero; acá entran dos porque acá tres ya existen. Un solo archivo para los
-- dos destinos tendría que saber cuál es cuál, y sería el próximo lugar donde se desincronizan.
--
-- La función `public.set_updated_at()` YA EXISTE en producción (la crea la 001 y la usan los
-- otros 39 triggers). No se recrea acá: un `CREATE OR REPLACE` de una función compartida por
-- 39 triggers para agregar dos es riesgo sin beneficio.
--
-- NO DESTRUCTIVA: no borra ni pisa datos, no cambia el schema. Solo agrega comportamiento.
-- ⚠️ NO RETROACTIVA: las filas existentes conservan el `updated_at` congelado que ya tienen.
-- No se hace backfill a propósito — no sabemos cuándo se modificaron de verdad, y escribir
-- `now()` en todas diría que se tocaron hoy, que es una segunda mentira encima de la primera.
-- Desde acá en adelante el dato es correcto; hacia atrás, es desconocido.
-- Idempotente: DROP TRIGGER IF EXISTS + CREATE. Correrla dos veces deja el mismo estado.
-- NO se ejecuta acá (la corre Franco).

BEGIN;

DROP TRIGGER IF EXISTS trg_usuario_integraciones_updated_at ON public.usuario_integraciones;
CREATE TRIGGER trg_usuario_integraciones_updated_at
    BEFORE UPDATE ON public.usuario_integraciones
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_plantillas_mail_updated_at ON public.plantillas_mail;
CREATE TRIGGER trg_plantillas_mail_updated_at
    BEFORE UPDATE ON public.plantillas_mail
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

COMMIT;

-- Verificación: las dos tienen que aparecer.
-- SELECT c.relname, t.tgname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
--  WHERE NOT t.tgisinternal AND c.relname IN ('usuario_integraciones', 'plantillas_mail');

-- 101_clasificacion_origen.sql
--
-- QUÉ HACE: agrega `candidatos.clasificacion_origen` ('modelo' | 'humano'), para que una
-- clasificación corregida a mano no se pueda confundir con una que produjo el clasificador.
--
-- NO DESTRUCTIVA. Idempotente. Va DESPUÉS de la 100 (usa las columnas que aquella crea).
-- NO se ejecuta acá (la corre Franco).
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 POR QUÉ UNA COLUMNA Y NO SOLO EL EVENTO DE AUDITORÍA
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- La corrección manual TAMBIÉN emite un evento (`correccion_clasificacion`, individual, con el
-- veredicto del modelo en `datos_anteriores`). La pregunta es por qué además una columna.
--
-- Dos razones, y las dos son de esas que no se ven hasta que muerden:
--
--   1. **`AuditService.registrar` SE TRAGA TODO ERROR, por diseño** — para no tumbar la
--      operación de negocio. Si el único marcador de "esto lo tocó un humano" fuera el evento,
--      un insert que falla en silencio volvería a mezclar esa corrección con las del modelo, y
--      nadie se enteraría. La columna se escribe en el MISMO UPDATE que la clasificación: no
--      puede divergir de ella.
--   2. **La pregunta se hace SOBRE `candidatos`, no sobre `auditoria`.** "¿Cuántos de los
--      no_relevante los puso el modelo?" es un filtro sobre la tabla de candidatos; resolverlo
--      contra el log de auditoría obligaría a reconstruir el estado actual replayando eventos,
--      que es exactamente lo que un log inmutable NO sirve para hacer barato.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 Y POR QUÉ EL EVENTO IGUAL HACE FALTA: LA COLUMNA PIERDE EL VEREDICTO ORIGINAL
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- La corrección PISA `clasificacion_ia`. Con la columna sola se sabe que un humano intervino,
-- pero no QUÉ había dicho el modelo — y la medición que de verdad importa ("¿en qué dirección
-- se equivoca el filtro?") necesita el par (lo que dijo el modelo, lo que dijo el humano).
-- Ese par vive en `datos_anteriores`/`datos_nuevos` del evento. Son dos preguntas distintas:
-- la columna contesta "¿esta fila es confiable como salida del modelo?" y el evento contesta
-- "¿cuánto y cómo se equivocó?". Ninguna de las dos reemplaza a la otra.
--
-- ⚠️ NULL = no hay clasificación (nunca se corrió, o la corrida falló). El origen solo tiene
-- sentido cuando hay un veredicto: no se siembra un default para las filas viejas porque no
-- hay ninguna clasificación previa a la 100 que etiquetar.

BEGIN;

ALTER TABLE public.candidatos
    ADD COLUMN IF NOT EXISTS clasificacion_origen TEXT;

ALTER TABLE public.candidatos DROP CONSTRAINT IF EXISTS candidatos_clasificacion_origen_check;
ALTER TABLE public.candidatos
    ADD CONSTRAINT candidatos_clasificacion_origen_check
    CHECK (clasificacion_origen IN ('modelo', 'humano'));

COMMENT ON COLUMN public.candidatos.clasificacion_origen IS
    'Quién puso la clasificación vigente: modelo | humano. NULL = no hay clasificación. Existe además del evento de auditoría porque AuditService se traga los errores por diseño y porque la pregunta "cuántos los puso el modelo" es un filtro sobre esta tabla. El veredicto ORIGINAL del modelo, cuando un humano lo pisa, queda en datos_anteriores del evento correccion_clasificacion. Ver migración 101.';

-- Las filas que ya clasificó el modelo antes de esta migración: 'modelo' es el único valor
-- posible para ellas (la corrección manual no existía). Sin este backfill quedarían en NULL y
-- se leerían como "sin clasificar" en cualquier corte por origen.
UPDATE public.candidatos
   SET clasificacion_origen = 'modelo'
 WHERE clasificacion_ia IS NOT NULL AND clasificacion_origen IS NULL;

COMMIT;

NOTIFY pgrst, 'reload schema';

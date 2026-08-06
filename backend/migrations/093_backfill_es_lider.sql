-- 093_backfill_es_lider.sql
--
-- QUÉ HACE: puebla `empleados.es_lider` (booleano) a partir de `empleados.liderazgo` (texto
-- crudo del CSV de nómina) para las filas que ya están cargadas. Son 31: 3 pasan a TRUE, 28 a
-- FALSE (que es el valor que ya tienen, así que en la práctica el UPDATE de FALSE no toca nada).
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- POR QUÉ — la migración 064 dejó esto declarado como trabajo futuro y nadie lo hizo
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- La 064 creó `liderazgo` y escribió, en su propio comentario de cabecera:
--
--     "liderazgo: TEXTO. [...] CONVIVE con la columna booleana existente `es_lider` (060,
--      cableada al checkbox de la UI): esta guarda el texto crudo del CSV; el parser decide
--      cómo poblar `es_lider` a partir de él. No se toca `es_lider`."
--
-- **Ese parser nunca se escribió.** El import cargó el texto y dejó `es_lider` en su DEFAULT
-- FALSE, así que las dos columnas se contradicen. Verificado contra el catálogo vivo (6/8/2026):
--     · `liderazgo` poblado 31/31 — 'SI' en 3, 'NO' en 28.
--     · `es_lider` en false en las 31, **incluidos los 3 líderes**.
--
-- El síntoma no es cosmético: `es_lider` es la columna que leen los 15 consumidores del sistema
-- (el filtro "Liderazgo" del listado, la columna "Es líder" del export, el campo "Líder" de la
-- ficha y —el más caro— `fetchEmpleadosLideres()`, que decide **qué empleados se pueden vincular
-- a un usuario `mandos_medios`**). Con las 31 en false, ese selector devuelve lista vacía.
-- `liderazgo`, en cambio, no lo lee NADIE: ni siquiera atraviesa `EmpleadoResponse`.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- LAS DOS MITADES — esta migración sola no alcanza
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- Esto cierra el hueco HACIA ATRÁS (las filas que ya existen). Lo cierra HACIA ADELANTE
-- `services/_nomina_empleados_transforms.parsear_fila`, que desde ahora deriva `es_lider` en
-- cada import. Hacen falta las dos: sin el backfill, las 31 filas actuales siguen mal hasta que
-- alguien reimporte el archivo completo; sin el parser, el próximo import reabre el hueco para
-- todo empleado nuevo.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 EL CRITERIO DE RECONOCIMIENTO ES EL DEL PARSER, NO UNO PROPIO
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- `services/_nomina_parsers.parse_bool` hace `.strip().upper()` y mapea:
--       'SI' -> true · 'NO' -> false · CUALQUIER OTRA COSA (incluido NULL y '') -> None.
-- Acá se replica tal cual, con `upper(btrim(...))`. Si los dos lados divergen, el backfill y los
-- imports futuros dan resultados distintos sobre el MISMO texto, que es la clase de bug que esta
-- migración viene a cerrar — con otra cara.
-- 🛡️ Hay un test que lo impide: `tests/test_liderazgo_es_lider.py::TestElBackfillYElParserCoinciden`
-- extrae los literales de ESTE archivo con una regex y los pasa por `parse_bool`. Cambiar uno de
-- los dos lados sin el otro rojea.
--
-- Nota sobre el trim: los valores almacenados ya vienen `.strip()`-eados desde Python (`_get` y
-- `limpiar` lo hacen al importar), así que `btrim` es redundante en la práctica. Se deja porque
-- el criterio tiene que ser legible como equivalente al del parser, no porque haga falta.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- QUÉ NO SE TOCA
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- · `liderazgo` NULL  → la fila NO se toca. Escribirle `false` sería el mismo bug con el signo
--   invertido: convertir "no sabemos" en "no es líder".
-- · `liderazgo` con un texto que no es SI/NO (p. ej. 'GERENTE DE ÁREA') → tampoco se toca, por
--   lo mismo. Hoy en producción no hay ninguno; el WHERE lo contempla igual porque la 064 dejó
--   escrito que "el CSV trae variantes más allá de SI/NO".
--   ⚠️ Estas filas quedan en el `false` por default de la 060, que es indistinguible de un
--   'NO' real. Es la limitación conocida y aceptada: el dato para desambiguarlas sigue estando
--   en `liderazgo`, que NO se borra.
-- · `liderazgo` NO SE ELIMINA ni se deja de escribir. Queda como dato crudo del import
--   (decisión de producto): es el único lugar donde sobrevive el texto original.
--
-- 🔴 PISA LA EDICIÓN MANUAL, a propósito: el import de nómina gana sobre lo cargado a mano,
-- mismo criterio que `manager_id`. Hoy no hay nada que pisar (las 31 están en false), pero la
-- regla queda escrita acá porque es la que va a regir cuando alguien tilde el checkbox.
--
-- NO DESTRUCTIVA: no borra filas ni columnas, y no toca ninguna otra columna.
-- IDEMPOTENTE: el `IS DISTINCT FROM` hace que la segunda corrida no actualice ninguna fila.
-- REVERSIBLE de hecho: `liderazgo` conserva el texto, así que el mapeo se puede recalcular.
-- NO se ejecuta acá (la corre Franco contra Supabase y verifica).
--
-- `db/schema.sql` NO CAMBIA: esto toca DATOS, no estructura. `es_lider boolean DEFAULT false`
-- (línea 304) y `liderazgo text` (línea 309) quedan igual que antes. Por lo mismo NO lleva
-- `NOTIFY pgrst, 'reload schema'`: el caché de PostgREST describe el schema, y el schema es
-- idéntico.

BEGIN;

UPDATE public.empleados
   SET es_lider = TRUE
 WHERE upper(btrim(liderazgo)) = 'SI'
   AND es_lider IS DISTINCT FROM TRUE;

UPDATE public.empleados
   SET es_lider = FALSE
 WHERE upper(btrim(liderazgo)) = 'NO'
   AND es_lider IS DISTINCT FROM FALSE;

COMMIT;

-- Verificación. La primera tiene que dar 3 filas en true / 28 en false y ningún desacuerdo;
-- la segunda, 0 filas (las que quedaron sin mapear por traer un texto no reconocido).
-- SELECT es_lider, count(*) FROM public.empleados GROUP BY 1 ORDER BY 1;
-- SELECT id, liderazgo, es_lider FROM public.empleados
--  WHERE liderazgo IS NOT NULL AND upper(btrim(liderazgo)) NOT IN ('SI','NO');

-- 092_seniority_sin_datos_a_null.sql
--
-- QUÉ HACE: las filas con `empleados.seniority = 'SIN DATOS'` pasan a NULL. Son 4.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- POR QUÉ EL LITERAL EXISTE — no lo escribió el sistema
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 'SIN DATOS' viene en el CSV de nómina de RRHH: es cómo ELLOS escriben "no hay dato" en esa
-- celda. Nuestro código nunca lo generó (grep del backend: el string no aparece en ninguna
-- parte), simplemente lo pasó tal cual a la columna porque no estaba en la lista de textos que
-- el import trata como vacíos.
--
-- Esa lista es `backend/services/_nomina_parsers.VACIOS` —la definición ÚNICA de "vacío" del
-- sistema, junto a 'NO APLICA', 'N/A', 'NA', '-' y '--'— y ahora incluye 'SIN DATOS' y
-- 'SIN DATO'. O sea que **los imports futuros ya no lo escriben**: esta migración limpia lo que
-- entró antes de ese cambio, y no vuelve a hacer falta.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- POR QUÉ HACE FALTA SI EL REPORTE YA LO AGRUPA BIEN
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- `services/reportes/_reporte_distribucion._agrupar` importa esa misma lista, así que R4 y el
-- KPI de distribución del dashboard YA cuentan estas 4 filas dentro de "Sin especificar" — sin
-- esta migración el reporte no miente. Lo que sigue mintiendo es la COLUMNA: el export de
-- empleados, la ficha y cualquier filtro futuro leen `seniority` directo, sin pasar por el
-- agrupador, y ahí 'SIN DATOS' se ve como si fuera un nivel de seniority más. Enseñarle a cada
-- superficie a interpretar el literal sería multiplicar el parche; el dato se arregla una vez.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 ORDEN: VA DESPUÉS DEL CÓDIGO. No es una dependencia técnica, es que si no, se deshace.
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- No hay orden OBLIGATORIO: la columna ya es nullable (24 de 31 filas están en NULL hoy), no
-- tiene DEFAULT ni CHECK, y el agrupador nuevo da el mismo resultado con el literal o sin él.
-- Corrida antes del deploy tampoco rompe nada.
--
-- Pero corriéndola antes, el próximo import de nómina —todavía con el código viejo, que no
-- tiene 'SIN DATOS' en VACIOS— vuelve a escribir el literal en esas mismas filas y hay que
-- correrla de nuevo. Con el código desplegado primero, el import ya lo convierte a NULL en la
-- entrada y la limpieza queda firme. Por eso: código, después esto.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- ALCANCE Y SEGURIDAD DEL UPDATE
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- Verificado contra el catálogo vivo (3/8/2026):
--     · 4 filas con `seniority = 'SIN DATOS'` (match exacto), y NINGUNA variante de mayúsculas
--       o espacios — se chequeó `upper(btrim(seniority)) IN ('SIN DATOS','SIN DATO')` y da las
--       mismas 4. Por eso el WHERE es una igualdad literal y no un `upper(btrim(...))`: acotar
--       al valor exacto que existe es lo que hace previsible qué filas toca.
--     · El literal aparece SOLO en esta columna. Se barrieron TODAS las columnas de `empleados`
--       con `to_jsonb(e) ->> columna ILIKE '%sin dato%'` y el único hit es `seniority`.
--     · Distribución completa de `seniority`: 24 NULL · 4 'SIN DATOS' · TRAINEE, EXPERT y
--       SENIOR con 1 cada uno. Después de esto quedan 28 NULL y los 3 valores reales.
--
-- NO DESTRUCTIVA en el sentido de que no borra filas ni columnas, pero SÍ PISA DATOS. Lo que
-- pisa no es información: es la ausencia de información escrita con otras letras. Los 3 valores
-- reales de seniority no los toca ningún camino de este UPDATE.
-- ⚠️ NO ES REVERSIBLE por sí sola: después de correrla no queda forma de distinguir cuáles de
-- las 28 filas en NULL decían 'SIN DATOS' y cuáles ya estaban vacías. Es aceptable porque las
-- dos cosas significan lo mismo — pero si alguna vez hiciera falta esa distinción, el lugar
-- donde vive es el CSV original, no la base.
-- Idempotente: correrla dos veces deja el mismo estado (la segunda no encuentra ninguna).
-- NO se ejecuta acá (la corre Franco).
--
-- `db/schema.sql` NO CAMBIA: esta migración toca DATOS, no estructura. La columna ya está
-- declarada como `seniority text` (línea 300), nullable, sin default ni check — antes y después.
-- Tampoco lleva `NOTIFY pgrst, 'reload schema'`: el caché de PostgREST describe el schema, y el
-- schema es idéntico.

BEGIN;

UPDATE public.empleados
   SET seniority = NULL
 WHERE seniority = 'SIN DATOS';

COMMIT;

-- Verificación: la primera tiene que dar 0 filas, la segunda 28 NULL y 3 con valor real.
-- SELECT count(*) FROM public.empleados WHERE seniority = 'SIN DATOS';
-- SELECT coalesce(seniority,'(null)') AS seniority, count(*)
--   FROM public.empleados GROUP BY 1 ORDER BY 2 DESC;

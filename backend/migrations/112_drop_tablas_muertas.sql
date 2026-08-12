-- 112_drop_tablas_muertas.sql
--
-- QUÉ HACE: dropea las ONCE tablas que quedaron sin código después del bloque J5a.
-- 🔴 DESTRUCTIVA E IRREVERSIBLE. Cierra el bloque J5.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- QUÉ SE VA, Y POR QUÉ
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- GRUPO 1 — las cinco `ev_*`: el motor de evaluaciones que el sistema NUNCA usó.
--   `ev_plantillas`, `ev_criterios`, `ev_ciclos`, `ev_instancias`, `ev_resultados` (migraciones
--   040-044). El sistema iba a EVALUAR: plantillas con criterios, ciclos, una instancia por
--   persona, scoring por criterio. Nunca se usó — las cinco están en 0 filas desde que se
--   crearon. Sus 19 endpoints seguían publicados por HTTP e inalcanzables desde la UI, y uno
--   estaba roto desde hacía meses sin que nadie lo notara (`PUT /plantillas/{id}`: `model_dump`
--   sin `mode="json"` sobre `area_id` rompía el UPDATE). El código se borró en J5a — 17
--   archivos, 1.527 líneas.
--
--   🔴 NO CONFUNDIR CON EL MÓDULO DE EVALUACIONES VIVO, que comparte el prefijo de URL
--   `/api/evaluaciones/*` y ESTÁ EN PRODUCCIÓN CON DATOS. Ese otro son `evaluacion_lotes`,
--   `evaluacion_evaluados`, `evaluacion_resultados` y `evaluacion_equivalencias` (migraciones
--   078-079), tiene 1 lote / 10 evaluados / 307 resultados, y NO SE TOCA acá. La confusión de
--   nombres ya mordió a este repo dos veces (quedó documentada en `tests/test_mappers_
--   ejercitados.py` y `tests/test_mappers_con_datos.py`): antes de tocar cualquier cosa que
--   diga "evaluacion", mirá si el nombre empieza con `ev_` o con `evaluacion_`.
--
-- GRUPO 2 — las seis huérfanas: creadas, nunca cableadas, 0 filas y CERO referencias en código
--   (verificado por grep sobre `routers/`, `services/`, `repositories/`, `schemas/`, `tests/` y
--   todo el front).
--     · `assessment_reportes`    (021) — reportes del assessment; el módulo se apagó por flag.
--     · `configuracion_empresa`  (030) — la configuración real vive en `parametros_empresa`.
--     · `documentos_empleado`    (004) — 🔑 LA REEMPLAZA `adjuntos`, que es su generalización
--        polimórfica: donde ésta tenía `empleado_id` y `tipo`, `adjuntos` tiene `entidad` +
--        `entidad_id` (con resolver para `empleado` ya escrito) y `categoria`, y comparte
--        idénticas `bucket`/`storage_path`/`nombre_archivo`/`mime_type`/`tamano_bytes`/
--        `descripcion`/`estado`/`subido_por`/`created_at`/`empresa_id`. `adjuntos` agrega
--        `es_principal`. No se pierde ninguna capacidad: se pierde una tabla que nunca guardó
--        un archivo.
--     · `notificaciones`         (022) — no se construyó el sistema de notificaciones.
--     · `notificaciones_config`  (023) — ídem.
--     · `sucesion_posiciones`    (015) — sucesión se apagó en el front, y su backend NO usa esta
--        tabla: `sucesion_repo` lee `empleados` y `assessment_resultados`. El único lugar del
--        repo que la nombraba era un mapeo ruta→tabla de un script de smoke que además estaba
--        MAL (decía que `/api/sucesion` depende de ella, y no depende). Se sacó en J5a.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 POR QUÉ VA DESPUÉS DEL DEPLOY DE J5A Y NO ANTES
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- El código que HOY sirve tráfico en producción es el de ANTES de J5a: todavía monta los cuatro
-- routers `ev_*` y —esto es lo que importa— todavía consulta `ev_ciclos` y `ev_instancias`
-- desde DOS superficies que no son de evaluaciones:
--
--   · el Panel de Procesos (`services/procesos_service.py`), que arma los siete procesos en una
--     sola list-comprehension dentro de UN try/except. Una tabla que no existe no deja la fila
--     vacía: levanta `PROCESOS_ERROR` y SE LLEVA EL PANEL ENTERO. Los otros seis procesos, que
--     están perfectos, dejan de verse.
--   · el reporte anual (`services/_reporte_anual_metricas.actividad`), que contaba
--     `ev_instancias` finalizadas y no tiene try/except en ningún escalón: el informe entero
--     deja de generarse.
--
-- O sea: correr esto ANTES del deploy rompe dos pantallas que no tienen nada que ver con
-- evaluaciones. Al revés no pasa nada — el código de J5a ya no nombra ninguna de las once, así
-- que convive sin problema con las tablas todavía presentes. La ventana segura es
--
--     DEPLOY de J5a  →  112 (este archivo)
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 SIN CASCADE, Y ES DELIBERADO
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- Verificado contra el catálogo vivo el 2026-08-11: NO existe ni una sola FK entrante desde una
-- tabla viva hacia ninguna de las once. Tampoco hay vistas, matviews ni funciones que las
-- nombren. Por eso un `DROP TABLE` pelado alcanza, y por eso NO lleva `CASCADE`:
--
--   Sin `CASCADE`, si mañana alguien crea una dependencia que hoy no existe, Postgres RECHAZA
--   el drop y esta migración falla ruidosamente. Con `CASCADE`, la borraría en silencio junto
--   con la tabla. Acá el error es la protección: convierte un desastre silencioso en un rojo.
--
-- El único orden que importa es el de las cinco `ev_*` entre sí, que tienen 5 FK internas:
--     ev_resultados → ev_criterios, ev_instancias
--     ev_criterios  → ev_plantillas
--     ev_instancias → ev_ciclos
--     ev_ciclos     → ev_plantillas
-- Se dropean HIJAS PRIMERO, en el orden de abajo. Las seis huérfanas no tienen FK entre sí y
-- pueden ir en cualquier orden.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- QUÉ SE LLEVA PUESTO (todo cae solo con DROP TABLE — no hay que dropear nada por separado)
-- ─────────────────────────────────────────────────────────────────────────────────────────
--   · 50 índices
--   ·  9 triggers  — 8 `updated_at` + `trg_emp_sucesion` (default de `empresa_id` del retrofit
--                    multiempresa). Producción pasa de 43+9=52 triggers no internos a 35+8=43.
--                    🔑 Los 8 `updated_at` YA SE SACARON de `migracionAWS/.../077` en J5a: ese
--                    script corre después de `schema.sql` en RDS, y `DROP TRIGGER IF EXISTS x
--                    ON tabla` TAMBIÉN falla si la TABLA no existe —el IF EXISTS cubre el
--                    trigger, no la relación—, así que abortaba entero.
--   · 17 policies RLS — las 6 huérfanas las tienen; las cinco `ev_*` tienen RLS activo y CERO
--                    policies (o sea, hoy están cerradas a cal y canto para el rol anónimo).
--   · 66 constraints, 29 de ellas FK (5 internas entre las `ev_*` + 24 salientes hacia
--                    `empresas`, `empleados`, `areas`, `users` y `assessment_resultados`).
--                    Las salientes mueren con su tabla y NO tocan el destino.
--   ·  0 secuencias  — ninguna depende de estas tablas (todas usan `gen_random_uuid()`).
--   ·  0 tipos ENUM  — no hay ningún ENUM en juego, ni exclusivo ni compartido.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- LAS MIGRACIONES 040-044 SE CONSERVAN
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- No se borran, igual que la 102 (que declaraba `clientes.empresa_id`, revertido por la 108/109).
-- Son el HISTORIAL de cómo se llegó hasta acá y explican por qué existieron estas tablas. Quien
-- reconstruya la base no las corre: `db/schema.sql` es la fuente de reconstrucción, y de ahí las
-- once ya salieron. Borrar el historial dejaría el registro incompleto sin ganar nada.
-- Lo mismo vale para 004, 015, 021, 022, 023 y 030, que crearon las seis huérfanas.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════

BEGIN;

-- ── GRUPO 1: las cinco ev_*, HIJAS PRIMERO (respetar este orden) ────────────────────────────

DROP TABLE public.ev_resultados;   -- apunta a ev_criterios y a ev_instancias
DROP TABLE public.ev_instancias;   -- apunta a ev_ciclos
DROP TABLE public.ev_criterios;    -- apunta a ev_plantillas
DROP TABLE public.ev_ciclos;       -- apunta a ev_plantillas
DROP TABLE public.ev_plantillas;   -- la recibían ev_ciclos y ev_criterios

-- ── GRUPO 2: las seis huérfanas (sin FK entre sí — el orden es indistinto) ──────────────────

DROP TABLE public.assessment_reportes;
DROP TABLE public.configuracion_empresa;
DROP TABLE public.documentos_empleado;
DROP TABLE public.notificaciones;
DROP TABLE public.notificaciones_config;
DROP TABLE public.sucesion_posiciones;

COMMIT;


-- ═════════════════════════════════════════════════════════════════════════════════════════
-- VERIFICACIÓN POSTERIOR — correr DESPUÉS del COMMIT, una por una
-- ═════════════════════════════════════════════════════════════════════════════════════════
--
-- ── 1. Las once NO existen. Debe devolver 0 filas. ─────────────────────────────────────────
--
-- SELECT tablename
--   FROM pg_tables
--  WHERE schemaname = 'public'
--    AND tablename IN ('ev_ciclos','ev_criterios','ev_instancias','ev_plantillas',
--                      'ev_resultados','assessment_reportes','configuracion_empresa',
--                      'documentos_empleado','notificaciones','notificaciones_config',
--                      'sucesion_posiciones');
--
--
-- ── 2. 🔴 LA QUE DE VERDAD IMPORTA: las tablas VIVAS que ellas referenciaban siguen ENTERAS.
--
-- Las 24 FK salientes mueren con su tabla y no deberían tocar el destino, pero "no debería" no
-- es una verificación: esta query lo DEMUESTRA con las filas contadas. Los valores esperados son
-- los del 2026-08-11 — si alguno bajó, algo se llevó datos puestos y hay que parar.
--
-- SELECT 'empresas' AS tabla, count(*) AS filas,  2 AS esperado_2026_08_11 FROM empresas
-- UNION ALL SELECT 'empleados',              count(*), 31 FROM empleados
-- UNION ALL SELECT 'areas',                  count(*), 12 FROM areas
-- UNION ALL SELECT 'users',                  count(*),  4 FROM users
-- UNION ALL SELECT 'assessment_resultados',  count(*),  0 FROM assessment_resultados
-- ORDER BY 1;
--
-- Los cinco esperados se leyeron del catálogo el 2026-08-11, ANTES del drop. `assessment_
-- resultados` espera 0 y eso es correcto: nunca tuvo filas — lo que esta query verifica de ella
-- es que la TABLA sobreviva, porque `assessment_reportes` le apuntaba con DOS FK `ON DELETE
-- CASCADE`. Un `count(*)` sobre una tabla borrada no devuelve 0: da error 42P01.
--
--
-- ── 3. Los triggers quedaron en 35 updated_at + 8 trg_emp_* = 43. ──────────────────────────
--
-- SELECT CASE WHEN t.tgname LIKE '%updated_at'  THEN 'updated_at'
--             WHEN t.tgname LIKE 'trg_emp%'     THEN 'trg_emp_*'
--             ELSE 'otro' END AS familia,
--        count(*) AS n
--   FROM pg_trigger t
--   JOIN pg_class c     ON c.oid = t.tgrelid
--   JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'public'
--  WHERE NOT t.tgisinternal
--  GROUP BY 1 ORDER BY 1;
--
-- Esperado exactamente:   trg_emp_*  8   ·   updated_at  35   ·   (ninguna fila 'otro')
--
--
-- ── 4. No quedó ninguna FK colgada apuntando a las once. Debe devolver 0 filas. ────────────
--
-- SELECT con.conname, src.relname AS desde, tgt.relname AS hacia
--   FROM pg_constraint con
--   JOIN pg_class src ON src.oid = con.conrelid
--   JOIN pg_class tgt ON tgt.oid = con.confrelid
--  WHERE con.contype = 'f'
--    AND tgt.relname IN ('ev_ciclos','ev_criterios','ev_instancias','ev_plantillas',
--                        'ev_resultados','assessment_reportes','configuracion_empresa',
--                        'documentos_empleado','notificaciones','notificaciones_config',
--                        'sucesion_posiciones');
--
--
-- ── 5. El total de tablas bajó de 63 a 52. ─────────────────────────────────────────────────
--
-- SELECT count(*) AS tablas FROM pg_tables WHERE schemaname = 'public';   -- esperado: 52

-- 121_intentos_identificacion_preingreso.sql
--
-- QUÉ HACE: UN objeto. `intentos_identificacion_resultado_check` pasa de 6 valores a 7,
-- agregando 'preingreso'. Los seis que ya estaban se conservan textualmente y EN SU ORDEN.
-- No se toca ninguna columna, ningún índice, ningún dato.
--
-- Idempotente (el par DROP IF EXISTS + ADD converge al mismo CHECK cuantas veces corra).
-- NO se ejecuta acá (la corre Franco). Molde: la 120.
--
-- POR QUÉ: el link público de horas rechaza a un preingreso (correcto: todavía no trabaja acá)
-- pero lo registraba como 'inactivo' en el log forense — el dato que le permite a RRHH ver que
-- alguien está probando dnis no distinguía "se fue" de "todavía no entró". Con el estado
-- 'preingreso' vivo desde la 120, esa ambigüedad dejó de ser teórica: un preingreso que prueba
-- el link ANTES de su fecha es un caso normal, no un ataque, y leerlo como "inactivo" manda a
-- RRHH a revisar una baja que no existe.
--
-- 🔴 EL ORDEN DE DEPLOY ACÁ ES OBLIGATORIO Y ES EL INVERSO DEL HABITUAL EN APARIENCIA: PRIMERO
-- esta migración, DESPUÉS el código que escribe 'preingreso'. No es un capricho: el INSERT del
-- log forense está envuelto en un except que se traga todo (`identificacion_repo.
-- registrar_intento` — a propósito, para no reabrir el oráculo de timing del rechazo único), y
-- ESO CONVIERTE EL ORDEN MIGRACIÓN→VALOR EN UNA CONDICIÓN DURA, NO EN UNA RECOMENDACIÓN. Si el
-- código sale antes que esta migración, CADA INTENTO DE UN PREINGRESO SE PIERDE SIN ERROR, SIN
-- LOG Y SIN FILA: el 23514 del CHECK viejo lo atrapa el except, no sube al usuario (que sigue
-- viendo el rechazo único de siempre — el flujo público no se entera de nada) y el único rastro
-- que queda es un `logger.warning` de severidad baja que nadie monitorea en caliente — a fines
-- prácticos, invisible. No hay excepción que alguien note, no hay alerta, no hay fila en
-- `intentos_identificacion`: el caso que esta migración vino a resolver (distinguir "se fue" de
-- "todavía no entró" en el forense) desaparecería en silencio hasta que alguien audite el except.
-- (La regla general de la 090 —"el código que TOLERA primero, la base que PRODUCE después"—
-- no se viola: esta migración no PRODUCE valores, los ACEPTA. Corrida sola es INERTE, igual
-- que la 120: el único que puede escribir 'preingreso' es código que se deploya después.)
--
-- ── VERIFICADO CONTRA `db/schema.sql` (el catálogo de reconstrucción) el 2026-08-19 ─────────
-- El CHECK vigente, tal como está declarado en schema.sql:1277:
--   CHECK ((resultado = ANY (ARRAY['ok'::text, 'sin_coincidencia'::text, 'inactivo'::text,
--                                  'sin_clientes'::text, 'ambiguo'::text, 'bloqueado'::text])))
-- ⚠️ Sin MCP en esta sesión no se contrastó contra el catálogo VIVO. Antes de correrla,
-- verificar con la query del bloque 1 de abajo que el CHECK real coincida con este texto.
--
-- 🔑 NO PUEDE FALLAR POR DATOS: un CHECK que se ENSANCHA acepta todo lo que aceptaba antes
-- (superconjunto estricto). El que falla al revalidar es el que se angosta.
--
-- POR QUÉ EN TRANSACCIÓN, si es un solo objeto: un CHECK no se reemplaza en un paso — entre el
-- DROP y el ADD la columna queda sin defensa, y fuera de transacción una escritura concurrente
-- en esa ventana entra con cualquier valor y hace fallar el ADD al revalidar, dejando la tabla
-- SIN CHECK. Mismo criterio que la 114, la 119 y la 120.

BEGIN;

-- Los seis que ya estaban van PRIMERO y en el orden que tienen hoy. No es cosmético:
-- `pg_get_constraintdef` devuelve el ARRAY en el orden en que se escribió, así que conservarlo
-- hace que el diff contra el CHECK viejo sea exactamente una entrada más al final.

ALTER TABLE public.intentos_identificacion
    DROP CONSTRAINT IF EXISTS intentos_identificacion_resultado_check;

ALTER TABLE public.intentos_identificacion
    ADD CONSTRAINT intentos_identificacion_resultado_check
    CHECK (resultado IN ('ok', 'sin_coincidencia', 'inactivo', 'sin_clientes', 'ambiguo',
                         'bloqueado', 'preingreso'));

COMMIT;


-- ═════════════════════════════════════════════════════════════════════════════════════════
-- VERIFICACIÓN POSTERIOR — correr DESPUÉS, a mano. Nada de esto se ejecuta con la migración.
-- ═════════════════════════════════════════════════════════════════════════════════════════
--
-- 🔴 LOS BLOQUES VAN POR SEPARADO Y NO SE PUEDEN FUSIONAR. El cuarto provoca un error a
-- propósito, y un error aborta la transacción entera: fusionados, todo lo posterior fallaría
-- con "current transaction is aborted" y no se distinguiría el rechazo buscado del daño.
--
--
-- 1. El CHECK quedó con los siete valores, en el orden esperado:
--
--    SELECT pg_get_constraintdef(oid) FROM pg_constraint
--     WHERE conrelid = 'public.intentos_identificacion'::regclass
--       AND conname = 'intentos_identificacion_resultado_check';
--    -- ESPERADO (texto exacto del catálogo):
--    --   CHECK ((resultado = ANY (ARRAY['ok'::text, 'sin_coincidencia'::text,
--    --                                  'inactivo'::text, 'sin_clientes'::text,
--    --                                  'ambiguo'::text, 'bloqueado'::text,
--    --                                  'preingreso'::text])))
--
--
-- 2. Que una fila con resultado='preingreso' ENTRE:
--
--    BEGIN;
--    INSERT INTO public.intentos_identificacion (dni, resultado)
--    VALUES ('00000000', 'preingreso');
--    -- ESPERADO: INSERT 0 1, sin error.
--    ROLLBACK;
--
--
-- 3. Que los SEIS valores viejos sigan entrando — el control de que no se perdió ninguno:
--
--    BEGIN;
--    INSERT INTO public.intentos_identificacion (dni, resultado)
--    SELECT '00000000', v
--      FROM unnest(ARRAY['ok', 'sin_coincidencia', 'inactivo', 'sin_clientes',
--                        'ambiguo', 'bloqueado']) AS v;
--    -- ESPERADO: INSERT 0 6, sin error. Si entra 5 o menos, el CHECK se reescribió mal y se
--    -- perdió un valor que el código YA produce — y como el insert forense traga errores,
--    -- ese motivo dejaría de registrarse SIN síntoma.
--    ROLLBACK;
--
--
-- 4. 🔴 EL QUE IMPORTA — que un valor inventado SIGA REBOTANDO:
--
--    BEGIN;
--    INSERT INTO public.intentos_identificacion (dni, resultado)
--    VALUES ('00000000', 'no_existe');
--    -- ESPERADO: ERROR 23514 check_violation sobre
--    --   "intentos_identificacion_resultado_check".
--    -- Es el único bloque que distingue "el CHECK acepta 'preingreso'" de "no hay CHECK":
--    -- un CHECK que no rechaza nada no es un CHECK.
--    ROLLBACK;
--
--
-- 5. Que no se haya tocado nada más:
--
--    SELECT count(*) FROM pg_constraint
--     WHERE conrelid = 'public.intentos_identificacion'::regclass AND contype = 'c';
--    -- ESPERADO: el mismo número que antes de correr la migración (el DROP se llevó UNO y el
--    -- ADD lo repuso). Los NOT NULL cuentan como CHECK en el catálogo: comparar contra la
--    -- medición previa, no contra un número escrito acá.

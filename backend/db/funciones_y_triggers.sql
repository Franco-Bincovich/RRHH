-- ============================================================================
-- funciones_y_triggers.sql — coherencia de empresa entre un registro y sus referencias
-- ============================================================================
--
-- PASO 3 DE 5 DE LA RECONSTRUCCION. Se corre DESPUES de db/schema.sql:
--   psql -v ON_ERROR_STOP=1 -f db/funciones_y_triggers.sql
-- La secuencia completa esta en docs/handoff-aws/README.md.
--
-- ── DE DONDE SALE ESTE ARCHIVO ───────────────────────────────────────────────
-- 🔴 SE LEYO DEL CATALOGO VIVO DE PRODUCCION (pg_get_functiondef / pg_get_triggerdef,
-- proyecto grmdiwxcvcjorlohpwji, 2026-08-12), NO de las migraciones. Es la misma
-- regla que gobierna a db/schema.sql: produccion driftea y el catalogo no miente.
--
-- 🚨 REEMPLAZA A `backend/migrations/094_recrear_triggers_empresa.sql` EN EL REBUILD.
-- La 094 declara NUEVE triggers; el noveno es `trg_emp_sucesion` sobre
-- `sucesion_posiciones`, una de las once tablas que dropeo la migracion 112. Un replay
-- que use la 094 ABORTA, y no por el trigger: `DROP TRIGGER IF EXISTS x ON tabla` falla
-- igual cuando la que no existe es la TABLA. Es la misma mina que el bloque J5a ya
-- desactivo en la 077 de updated_at, y que a la 094 no se le hizo.
-- La 094 NO se toca: queda como historial de cuando esos objetos se rescataron. El
-- camino de reconstruccion no la mira nunca.
--
-- ── QUE INVARIANTE SOSTIENE ──────────────────────────────────────────────────
-- "Un registro de la empresa A no referencia una fila de la empresa B."
--
-- Una FK garantiza que `empleados.area_id` apunta a un area que EXISTE; no garantiza
-- que esa area sea de la MISMA empresa que el empleado. Sin estos triggers, un INSERT
-- que cruce empresas entra sin error y queda como DATO CORRUPTO SILENCIOSO: el listado
-- de la empresa A muestra un empleado cuya area es de la B.
--
-- La barrera de aplicacion (Fase 2, filtro de empresa en el WHERE) cubre el camino de
-- la API. NO cubre un INSERT por SQL directo, un import mal armado, ni un script de
-- migracion de datos — que es exactamente lo que va a correr durante el cutover.
--
-- 🔴 Y NO HAY RED DEBAJO. De los 12 pares (columna -> tabla padre) que vigilan estos
-- 8 triggers, CERO tienen una FK compuesta que los respalde. Verificado contra el
-- catalogo el 12/8/2026. Y no es que el modelo desconozca el patron: hay 22 FKs
-- compuestas `(x_id, empresa_id) REFERENCES padre(id, empresa_id)` en produccion
-- —costos_nomina, onboarding_*, offboarding_*, inventario_asignaciones,
-- empleado_capacitacion, solicitudes_*, vacaciones_pendientes, sesiones_horas,
-- presupuesto_areas, planes_carrera_hitos— que hacen cumplir lo mismo con una
-- constraint. Estos 12 pares quedaron afuera de ese patron, y el trigger es LO UNICO
-- que los sostiene. Si algun dia se les agrega la FK compuesta, el trigger de ese par
-- pasa a ser redundante y recien ahi se puede sacar.
--
-- Los 12 pares, por tabla:
--   areas                  -> area_padre_id -> areas | responsable_id -> empleados
--   empleados              -> area_id -> areas       | manager_id -> empleados
--   vacantes               -> area_id -> areas
--   onboarding_templates   -> area_id -> areas
--   planes_carrera         -> responsable_id -> empleados
--   assessment_campanas    -> area_id -> areas
--   assessment_links       -> empleado_id -> empleados | candidato_id -> candidatos
--   assessment_resultados  -> empleado_id -> empleados | candidato_id -> candidatos
--
-- ⚠️ `planes_carrera` tiene ADEMAS una FK compuesta, pero sobre `empleado_id`, que es
-- OTRA columna. La que el trigger vigila —`responsable_id`— sigue descubierta.
--
-- ⚠️ Los tres triggers de assessment se conservan aunque el modulo este apagado por
-- `ASSESSMENT_ENABLED`: las tablas existen y el flag se enciende con una variable de
-- entorno. Un rebuild sin ellos dejaria el modulo sin proteccion el dia que se prenda.
--
-- 🔴 CONFLICTO CONOCIDO Y NO RESUELTO — `trg_emp_empleados` SOBRE `manager_id`:
-- este trigger EXIGE que el superior sea de la misma empresa que el empleado, pero la
-- decision de producto del 2/8/2026 dice lo contrario: "un empleado puede tener
-- superior de OTRA empresa del grupo", y sobre esa premisa esta construido
-- `services/_alcance_mandos.py` (el ownership de mandos_medios ignora la empresa) y el
-- import de nomina que escribe `manager_id` (migracion 086, titulada justamente
-- "superior cruzado entre empresas"). Hoy no exploto porque en produccion hay CERO
-- empleados con manager de otra empresa (verificado el 12/8): el dia que se cargue el
-- primero, el UPDATE va a fallar con "Cruce de empresa en empleados.manager_id".
-- SE REPRODUCE TAL CUAL ESTA EN PRODUCCION —este archivo refleja, no decide— pero hay
-- que resolverlo antes del cutover: o se saca ese par del trigger, o se revisa la
-- decision de producto. La 086 no menciona el trigger, asi que el choque nunca se
-- discutio.
--
-- Idempotente: CREATE OR REPLACE + DROP TRIGGER IF EXISTS. Se puede correr de nuevo.
-- ============================================================================

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

-- ── Funcion generica ─────────────────────────────────────────────────────────
-- Recibe pares (columna, tabla_padre) por TG_ARGV. Para cada par, si la columna no es
-- NULL, lee el empresa_id del padre y lo compara con el del registro; si difieren,
-- levanta excepcion. Por eso los 8 triggers comparten UNA sola funcion y se
-- diferencian solo en los argumentos.
--
-- ⚠️ Usa `IS DISTINCT FROM`, no `<>`: con `<>` una comparacion contra NULL daria NULL
-- —que no es TRUE— y el cruce pasaria sin que nadie lo note. Esa eleccion es tambien
-- la razon por la que este patron NO se puede aplicar a tablas con filas globales
-- (`empresa_id IS NULL`), como `tipos_ausencia`: ahi la fila global es legitima y el
-- trigger la rechazaria.

CREATE OR REPLACE FUNCTION public.fn_misma_empresa()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $function$
DECLARE v_col text; v_parent text; v_val uuid; v_emp uuid; i int := 0;
BEGIN
  WHILE i < TG_NARGS LOOP
    v_col := TG_ARGV[i]; v_parent := TG_ARGV[i+1];
    EXECUTE format('SELECT ($1).%I', v_col) INTO v_val USING NEW;
    IF v_val IS NOT NULL THEN
      EXECUTE format('SELECT empresa_id FROM %I WHERE id = $1', v_parent) INTO v_emp USING v_val;
      IF v_emp IS DISTINCT FROM NEW.empresa_id THEN
        RAISE EXCEPTION 'Cruce de empresa en %.%: la referencia % es de empresa %, pero el registro es de empresa %',
          TG_TABLE_NAME, v_col, v_val, v_emp, NEW.empresa_id;
      END IF;
    END IF;
    i := i + 2;
  END LOOP;
  RETURN NEW;
END; $function$;

-- ── Los 8 triggers ───────────────────────────────────────────────────────────
-- El orden de los argumentos importa: son pares (columna, tabla_padre) consecutivos.

DROP TRIGGER IF EXISTS trg_emp_areas ON public.areas;
CREATE TRIGGER trg_emp_areas
    BEFORE INSERT OR UPDATE ON public.areas
    FOR EACH ROW EXECUTE FUNCTION public.fn_misma_empresa('area_padre_id', 'areas', 'responsable_id', 'empleados');

DROP TRIGGER IF EXISTS trg_emp_empleados ON public.empleados;
CREATE TRIGGER trg_emp_empleados
    BEFORE INSERT OR UPDATE ON public.empleados
    FOR EACH ROW EXECUTE FUNCTION public.fn_misma_empresa('area_id', 'areas', 'manager_id', 'empleados');

DROP TRIGGER IF EXISTS trg_emp_vacantes ON public.vacantes;
CREATE TRIGGER trg_emp_vacantes
    BEFORE INSERT OR UPDATE ON public.vacantes
    FOR EACH ROW EXECUTE FUNCTION public.fn_misma_empresa('area_id', 'areas');

DROP TRIGGER IF EXISTS trg_emp_onb_templates ON public.onboarding_templates;
CREATE TRIGGER trg_emp_onb_templates
    BEFORE INSERT OR UPDATE ON public.onboarding_templates
    FOR EACH ROW EXECUTE FUNCTION public.fn_misma_empresa('area_id', 'areas');

DROP TRIGGER IF EXISTS trg_emp_planes_carrera ON public.planes_carrera;
CREATE TRIGGER trg_emp_planes_carrera
    BEFORE INSERT OR UPDATE ON public.planes_carrera
    FOR EACH ROW EXECUTE FUNCTION public.fn_misma_empresa('responsable_id', 'empleados');

DROP TRIGGER IF EXISTS trg_emp_ass_campanas ON public.assessment_campanas;
CREATE TRIGGER trg_emp_ass_campanas
    BEFORE INSERT OR UPDATE ON public.assessment_campanas
    FOR EACH ROW EXECUTE FUNCTION public.fn_misma_empresa('area_id', 'areas');

DROP TRIGGER IF EXISTS trg_emp_ass_links ON public.assessment_links;
CREATE TRIGGER trg_emp_ass_links
    BEFORE INSERT OR UPDATE ON public.assessment_links
    FOR EACH ROW EXECUTE FUNCTION public.fn_misma_empresa('empleado_id', 'empleados', 'candidato_id', 'candidatos');

DROP TRIGGER IF EXISTS trg_emp_ass_resultados ON public.assessment_resultados;
CREATE TRIGGER trg_emp_ass_resultados
    BEFORE INSERT OR UPDATE ON public.assessment_resultados
    FOR EACH ROW EXECUTE FUNCTION public.fn_misma_empresa('empleado_id', 'empleados', 'candidato_id', 'candidatos');

-- ── Verificacion ─────────────────────────────────────────────────────────────
-- Debe devolver 8. Si devuelve menos, alguna tabla no existia al correr este archivo
-- (se corrio antes de schema.sql, o el schema quedo viejo).
--   SELECT count(*) FROM pg_trigger t
--     JOIN pg_proc p ON p.oid = t.tgfoid
--    WHERE p.proname = 'fn_misma_empresa' AND NOT t.tgisinternal;

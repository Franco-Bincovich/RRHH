-- 094_recrear_triggers_empresa.sql
--
-- Recrea la función fn_misma_empresa() + los 9 triggers trg_emp_* que hacen cumplir la
-- coherencia de empresa entre un registro y las filas a las que apunta.
--
-- 🔴 POR QUÉ EXISTE ESTE ARCHIVO: hasta hoy estos 9 triggers y su función EXISTÍAN SOLO EN
-- PRODUCCIÓN. No estaban en db/schema.sql (el snapshot se lee del catálogo y captura tablas,
-- columnas, constraints, índices y defaults, pero 0 funciones y 0 triggers), no estaban en
-- migracionAWS/.../077 (que recrea únicamente los 41 de updated_at) y no estaban en ninguna de
-- las migraciones 001–093: se aplicaron a mano durante el retrofit multiempresa y nunca se
-- versionaron. Un rebuild desde cero —que es exactamente lo que se va a hacer en RDS— los perdía
-- y no había con qué recrearlos. Este script cierra ese agujero.
--
-- QUÉ SE PIERDE SIN ELLOS, y por qué no es cosmético: son la ÚNICA defensa a nivel base contra
-- el cruce de empresas por referencia. Una FK garantiza que `empleados.area_id` apunta a un área
-- que existe; NO garantiza que esa área sea de la MISMA empresa que el empleado. Sin el trigger,
-- un INSERT que cruce empresas entra sin error y queda como dato corrupto silencioso: el listado
-- de la empresa A muestra un empleado cuya área es de la empresa B. La barrera de aplicación
-- (Fase 2) cubre el camino de la API, pero no un INSERT por SQL directo ni un import mal armado.
--
-- CÓMO FUNCIONA: la función es genérica y recibe pares (columna, tabla_padre) por TG_ARGV. Para
-- cada par, si la columna no es NULL, lee el empresa_id del padre y lo compara con el del
-- registro; si difieren, levanta excepción. Por eso los 9 triggers comparten una sola función y
-- se diferencian solo en los argumentos.
--
-- Correr UNA vez contra la base, DESPUÉS de db/schema.sql.
-- Idempotente: CREATE OR REPLACE + DROP TRIGGER IF EXISTS (mismo criterio que la 077).
--
-- Definición extraída 1:1 del catálogo de producción (pg_get_functiondef / pg_get_triggerdef)
-- el 7/8/2026, sobre el proyecto grmdiwxcvcjorlohpwji.

-- ── Función genérica ─────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.fn_misma_empresa()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
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
END; $$;

-- ── Los 9 triggers ───────────────────────────────────────────────────────────
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

DROP TRIGGER IF EXISTS trg_emp_sucesion ON public.sucesion_posiciones;
CREATE TRIGGER trg_emp_sucesion
    BEFORE INSERT OR UPDATE ON public.sucesion_posiciones
    FOR EACH ROW EXECUTE FUNCTION public.fn_misma_empresa('area_id', 'areas', 'titular_id', 'empleados', 'sucesor_primario_id', 'empleados', 'sucesor_secundario_id', 'empleados');

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

-- Verificación (opcional): debe devolver 9.
-- SELECT count(*) FROM pg_trigger t
--   JOIN pg_proc p ON p.oid = t.tgfoid
--   WHERE p.proname = 'fn_misma_empresa' AND NOT t.tgisinternal;

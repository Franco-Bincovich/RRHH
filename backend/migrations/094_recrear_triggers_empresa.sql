-- 094_recrear_triggers_empresa.sql
--
-- Recrea la función fn_misma_empresa() + los 8 triggers trg_emp_* que hacen cumplir la
-- coherencia de empresa entre un registro y las filas a las que apunta.
--
-- ⚠️ ERAN 9 HASTA EL 2026-08-13. Se sacó `trg_emp_sucesion` porque la migración 112 dropeó
-- `sucesion_posiciones` y el bloque hacía abortar el archivo entero (el porqué, donde estaba).
--
-- 🔴 ESTE ARCHIVO YA NO ES EL CAMINO DE RECONSTRUCCIÓN. Lo reemplazó
-- `backend/db/funciones_y_triggers.sql`, que se lee del catálogo vivo y es el paso 3 de 5 del
-- rebuild. Este queda como HISTORIAL de cuándo se rescataron estos objetos; se corrigió —en vez
-- de dejarlo roto— para que correrlo a mano no destruya nada, no para volver a usarlo.
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

-- 📌 ACÁ VIVÍA `trg_emp_sucesion`, SOBRE `sucesion_posiciones`. Se BORRÓ el 2026-08-13 porque esa
-- tabla ya no existe: la dropeó la migración 112. Con el bloque puesto, este archivo ABORTABA
-- entero contra una base reconstruida — y no por el trigger: `DROP TRIGGER IF EXISTS x ON tabla`
-- falla igual cuando la que no existe es la TABLA. El `IF EXISTS` cubre el trigger, no la
-- relación. Es la misma mina que el bloque J5a ya había desactivado en la 077 de `updated_at` y
-- que a este archivo no se le hizo.
-- El trigger borrado sigue en el historial de git; recrearlo no tendría sobre qué correr.

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

-- Verificación (opcional): debe devolver 8.
-- SELECT count(*) FROM pg_trigger t
--   JOIN pg_proc p ON p.oid = t.tgfoid
--   WHERE p.proname = 'fn_misma_empresa' AND NOT t.tgisinternal;

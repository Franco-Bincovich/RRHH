-- 077_recrear_triggers_updated_at.sql
--
-- Recrea la función set_updated_at() + los 35 triggers trg_*_updated_at en la
-- base nueva (RDS). El snapshot db/schema.sql se generó del catálogo y capturó
-- tablas/columnas/constraints/índices/defaults, pero 0 funciones y 0 triggers,
-- así que updated_at se pobla en el alta (por el DEFAULT now()) pero NO se
-- actualizaría en UPDATE — corrupción silenciosa. Este script lo cierra.
--
-- Decisión (ver MIGRACION_A_RDS.md §3 hallazgo 5 y §5): se RECREAN los triggers
-- en RDS, NO se mueve updated_at a la capa de aplicación. Es un solo script SQL
-- y es a prueba de olvidos; dejarlo en la app depende de que nadie se olvide en
-- ninguna de las ~332 queries que se reescriben, y un olvido = dato congelado
-- en silencio.
--
-- Correr UNA vez contra la base limpia, DESPUÉS de db/schema.sql.
-- Idempotente: CREATE OR REPLACE + DROP TRIGGER IF EXISTS.
--
-- Definición y nombres extraídos 1:1 de las migraciones 001–066 (función
-- genérica definida en 001_create_users.sql). NO recrea los triggers de
-- auditoría (dropeados a propósito en 058; la captura hoy es app-level).

-- Función genérica para mantener updated_at; usada por triggers de múltiples tablas.
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- 35 triggers, un trigger por tabla con columna updated_at.
--
-- 🔴 ERAN 43 hasta el 2026-08-11. Se sacaron los 8 que apuntaban a tablas que el bloque J5b
-- dropea (las 5 ev_* + sucesion_posiciones, notificaciones_config y configuracion_empresa).
-- NO alcanzaba con dejarlos: `DROP TRIGGER IF EXISTS x ON tabla` TAMBIÉN falla si la TABLA no
-- existe —el IF EXISTS cubre el trigger, no la relación—, así que este script abortaba entero
-- contra un schema.sql ya limpio. El código de esas tablas se borró en J5a.
-- (horas_proyecto, adjuntos, periodos_cerrados y oauth_states NO llevan: son inmutables / sin
-- updated_at. No hay que declararlos en ningún lado: el barrido DERIVA los candidatos del
-- schema, así que una tabla sin la columna queda afuera sola.)

DROP TRIGGER IF EXISTS trg_users_updated_at ON public.users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_areas_updated_at ON public.areas;
CREATE TRIGGER trg_areas_updated_at
    BEFORE UPDATE ON public.areas
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_empleados_updated_at ON public.empleados;
CREATE TRIGGER trg_empleados_updated_at
    BEFORE UPDATE ON public.empleados
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_vacantes_updated_at ON public.vacantes;
CREATE TRIGGER trg_vacantes_updated_at
    BEFORE UPDATE ON public.vacantes
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_candidatos_updated_at ON public.candidatos;
CREATE TRIGGER trg_candidatos_updated_at
    BEFORE UPDATE ON public.candidatos
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_onboarding_templates_updated_at ON public.onboarding_templates;
CREATE TRIGGER trg_onboarding_templates_updated_at
    BEFORE UPDATE ON public.onboarding_templates
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_onboarding_instancias_updated_at ON public.onboarding_instancias;
CREATE TRIGGER trg_onboarding_instancias_updated_at
    BEFORE UPDATE ON public.onboarding_instancias
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_onboarding_progreso_updated_at ON public.onboarding_progreso;
CREATE TRIGGER trg_onboarding_progreso_updated_at
    BEFORE UPDATE ON public.onboarding_progreso
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_offboarding_instancias_updated_at ON public.offboarding_instancias;
CREATE TRIGGER trg_offboarding_instancias_updated_at
    BEFORE UPDATE ON public.offboarding_instancias
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_offboarding_activos_updated_at ON public.offboarding_activos;
CREATE TRIGGER trg_offboarding_activos_updated_at
    BEFORE UPDATE ON public.offboarding_activos
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_costos_nomina_updated_at ON public.costos_nomina;
CREATE TRIGGER trg_costos_nomina_updated_at
    BEFORE UPDATE ON public.costos_nomina
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_presupuesto_areas_updated_at ON public.presupuesto_areas;
CREATE TRIGGER trg_presupuesto_areas_updated_at
    BEFORE UPDATE ON public.presupuesto_areas
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_planes_carrera_updated_at ON public.planes_carrera;
CREATE TRIGGER trg_planes_carrera_updated_at
    BEFORE UPDATE ON public.planes_carrera
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_planes_carrera_hitos_updated_at ON public.planes_carrera_hitos;
CREATE TRIGGER trg_planes_carrera_hitos_updated_at
    BEFORE UPDATE ON public.planes_carrera_hitos
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_assessment_campanas_updated_at ON public.assessment_campanas;
CREATE TRIGGER trg_assessment_campanas_updated_at
    BEFORE UPDATE ON public.assessment_campanas
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_assessment_resultados_updated_at ON public.assessment_resultados;
CREATE TRIGGER trg_assessment_resultados_updated_at
    BEFORE UPDATE ON public.assessment_resultados
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_empresas_updated_at ON public.empresas;
CREATE TRIGGER trg_empresas_updated_at
    BEFORE UPDATE ON public.empresas
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_sv_updated_at ON public.solicitudes_vacaciones;
CREATE TRIGGER trg_sv_updated_at
    BEFORE UPDATE ON public.solicitudes_vacaciones
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_ta_updated_at ON public.tipos_ausencia;
CREATE TRIGGER trg_ta_updated_at
    BEFORE UPDATE ON public.tipos_ausencia
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_sa_updated_at ON public.solicitudes_ausencia;
CREATE TRIGGER trg_sa_updated_at
    BEFORE UPDATE ON public.solicitudes_ausencia
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_cap_updated_at ON public.capacitaciones;
CREATE TRIGGER trg_cap_updated_at
    BEFORE UPDATE ON public.capacitaciones
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_ec_updated_at ON public.empleado_capacitacion;
CREATE TRIGGER trg_ec_updated_at
    BEFORE UPDATE ON public.empleado_capacitacion
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_inv_items_updated_at ON public.inventario_items;
CREATE TRIGGER trg_inv_items_updated_at
    BEFORE UPDATE ON public.inventario_items
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_inv_asig_updated_at ON public.inventario_asignaciones;
CREATE TRIGGER trg_inv_asig_updated_at
    BEFORE UPDATE ON public.inventario_asignaciones
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_obj_updated_at ON public.objetivos;
CREATE TRIGGER trg_obj_updated_at
    BEFORE UPDATE ON public.objetivos
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_proyectos_updated_at ON public.proyectos;
CREATE TRIGGER trg_proyectos_updated_at
    BEFORE UPDATE ON public.proyectos
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_pa_updated_at ON public.proyecto_asignaciones;
CREATE TRIGGER trg_pa_updated_at
    BEFORE UPDATE ON public.proyecto_asignaciones
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_cesiones_updated_at ON public.cesiones;
CREATE TRIGGER trg_cesiones_updated_at
    BEFORE UPDATE ON public.cesiones
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- Catálogo de clientes (backend/migrations/102_clientes.sql). El trigger va en TRES archivos:
-- la 102 (Supabase), este (RDS) y db/schema.sql (la columna, de la que el barrido deriva el
-- candidato). `test_triggers_updated_at.py` compara schema.sql contra este archivo.
DROP TRIGGER IF EXISTS trg_clientes_updated_at ON public.clientes;
CREATE TRIGGER trg_clientes_updated_at
    BEFORE UPDATE ON public.clientes
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ─────────────────────────────────────────────────────────────────────────────────────────
-- TABLAS QUE NACIERON DESPUÉS DE QUE SE ESCRIBIERA ESTE SCRIPT
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 ESTE BLOQUE ES LA PRUEBA DEL PROBLEMA QUE TIENE ESTE ARCHIVO, no un apéndice.
-- La lista de arriba es HARDCODEADA, así que cada tabla nueva con columna `updated_at` queda
-- afuera sola y el síntoma no es un error: es el `updated_at` congelado en el alta, para
-- siempre, en silencio. Pasó CINCO veces antes de que alguien lo mirara:
--
--   · usuario_integraciones     (mig 032) — nunca tuvo trigger, en ningún lado.
--   · vacaciones_pendientes     (mig 083) — posterior a este script.
--   · parametros_empresa        (mig 085) — ídem.
--   · reglas_vacaciones_escala  (mig 085) — ídem.
--   · plantillas_mail           (mig 087) — ídem.
--   · parametros_screening     (mig 100) — ídem.
--
-- Agregarlas no cierra nada por sí solo: la sexta nacería con el mismo agujero. Lo que lo
-- cierra es `backend/tests/test_triggers_updated_at.py`, que DERIVA la lista de candidatos de
-- db/schema.sql y la compara contra este archivo. Si agregás una tabla con `updated_at` y no
-- tocás esto, el test rojea. NO lo saques ni le bajes los mínimos.
--
-- ⚠️ De las cinco, TRES ya tienen su trigger en Supabase porque sus migraciones (083 y 085) lo
-- declararon; las otras dos (032 y 087) no lo declararon y están congeladas HOY en producción.
-- Eso se arregla aparte, en `backend/migrations/091_triggers_updated_at_faltantes.sql`: este
-- script es el de la base NUEVA y no corre nunca contra Supabase.
-- Los nombres de las tres que ya existen son los MISMOS que en producción, a propósito: así el
-- catálogo de RDS y el de Supabase se pueden diffear sin traducir nada.

DROP TRIGGER IF EXISTS trg_usuario_integraciones_updated_at ON public.usuario_integraciones;
CREATE TRIGGER trg_usuario_integraciones_updated_at
    BEFORE UPDATE ON public.usuario_integraciones
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_vacaciones_pendientes_updated_at ON public.vacaciones_pendientes;
CREATE TRIGGER trg_vacaciones_pendientes_updated_at
    BEFORE UPDATE ON public.vacaciones_pendientes
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_parametros_screening_updated_at ON public.parametros_screening;
CREATE TRIGGER trg_parametros_screening_updated_at
    BEFORE UPDATE ON public.parametros_screening
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_parametros_empresa_updated_at ON public.parametros_empresa;
CREATE TRIGGER trg_parametros_empresa_updated_at
    BEFORE UPDATE ON public.parametros_empresa
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_reglas_vacaciones_escala_updated_at ON public.reglas_vacaciones_escala;
CREATE TRIGGER trg_reglas_vacaciones_escala_updated_at
    BEFORE UPDATE ON public.reglas_vacaciones_escala
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_plantillas_mail_updated_at ON public.plantillas_mail;
CREATE TRIGGER trg_plantillas_mail_updated_at
    BEFORE UPDATE ON public.plantillas_mail
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- Verificación (opcional): debe devolver 35.
-- SELECT count(*) FROM pg_trigger t
--   JOIN pg_proc p ON p.oid = t.tgfoid
--   WHERE p.proname = 'set_updated_at' AND NOT t.tgisinternal;

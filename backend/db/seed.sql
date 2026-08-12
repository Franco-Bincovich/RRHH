-- ============================================================================
-- seed.sql — los catalogos base sin los cuales el sistema arranca roto
-- ============================================================================
--
-- PASO 5 DE 5 DE LA RECONSTRUCCION. Se corre ULTIMO, despues de los triggers:
--   psql -v ON_ERROR_STOP=1 -f db/seed.sql
-- La secuencia completa esta en docs/handoff-aws/README.md.
--
-- ── QUE ES Y QUE NO ES ───────────────────────────────────────────────────────
-- Son CATALOGOS: filas que el CODIGO da por existentes. No son datos de negocio.
--
-- 🔴 LO QUE NO VA ACA, a proposito: `empresas`, `users`, `plantillas_mail`, areas,
-- empleados. Eso es DATO DE NEGOCIO y viaja en el dump de migracion, no en un seed
-- versionado. Un seed que invente una empresa deja la base con una fila que despues
-- nadie sabe si es real.
--
-- 🔑 LAS TRES TABLAS DE ACA LLEVAN `empresa_id = NULL`, QUE NO ES UN DESCUIDO: es la
-- fila GLOBAL. El modelo es "la de mi empresa si existe, si no la global"
-- (`services/configuracion_service.py`), y la global es la que rige para toda empresa
-- que no configuro nada. Por eso este archivo NO depende de que exista ninguna
-- empresa, y se puede correr contra una base recien creada.
--
-- Los valores salieron del CATALOGO VIVO de produccion (proyecto grmdiwxcvcjorlohpwji,
-- 2026-08-12), no de las migraciones.
--
-- ── IDEMPOTENCIA ─────────────────────────────────────────────────────────────
-- `ON CONFLICT DO NOTHING` SIN target, a proposito. Las tres tablas tienen sus
-- indices unicos PARCIALES (`... WHERE empresa_id IS NULL`) y `parametros_empresa`
-- lo tiene ademas POR EXPRESION (`((empresa_id IS NULL))`). Un `ON CONFLICT (col)`
-- exige que Postgres pueda inferir el indice, y con indices parciales hay que repetir
-- el predicado exacto; con uno por expresion, la expresion. Sin target, cualquier
-- violacion de unicidad —de la PK o de esos indices— salta la fila y sigue. Correr
-- este archivo dos veces no duplica nada ni falla.
-- ============================================================================

SET statement_timeout = 0;
SET client_encoding = 'UTF8';

-- ── 1. tipos_ausencia ────────────────────────────────────────────────────────
-- QUE SE ROMPE SIN ESTO: TODO el modulo de ausencias, de entrada.
-- `solicitudes_ausencia.tipo_id` es NOT NULL con FK a esta tabla, asi que con la
-- tabla vacia NO SE PUEDE CREAR NINGUNA AUSENCIA: no hay un solo valor valido que
-- poner. No degrada, no muestra una lista vacia: falla el INSERT.
--
-- 🔴 LOS UUID VAN FIJOS Y NO SE PUEDEN REGENERAR. Dos razones, las dos verificadas:
--   1. `services/_carga_licencia.py:51` tiene HARDCODEADO
--      TIPO_LICENCIA_ID = '9f3b7c2a-1d4e-4a6b-8c5d-0e1f2a3b4c5d'
--      (lo sembro asi la migracion 107). Si el seed genera otro uuid, la carga de
--      licencias del link publico falla con violacion de FK contra un id que no
--      existe — y falla en produccion, no en los tests, porque el fake no tiene FKs.
--   2. Cualquier dump de `solicitudes_ausencia` que se restaure despues trae los
--      `tipo_id` de produccion. Con uuids nuevos, ninguno resuelve.
-- O sea: `gen_random_uuid()` aca seria un bug silencioso de una punta y ruidoso de
-- la otra. Los cinco valores son los de produccion, tal cual.
--
-- Sobre las columnas: `es_base` marca los tipos del sistema (los que no se borran
-- desde la UI). `cuenta_ausentismo` decide si el tipo suma a la tasa del reporte.
-- "Injustificada" va con `activo = false` A PROPOSITO: se desactivo porque mezclaba
-- el eje *calificacion* (justificada o no, que es una columna aparte) con el eje
-- *naturaleza* del tipo. Se siembra igual, desactivada, para no perder el historico
-- de las ausencias que ya la referencian.

INSERT INTO public.tipos_ausencia (id, nombre, es_base, activo, cuenta_ausentismo, empresa_id, padre_id) VALUES
  ('9ae8a905-c0be-403b-8206-b1f4039ec465', 'Enfermedad',    true,  true,  true, NULL, NULL),
  ('9f3b7c2a-1d4e-4a6b-8c5d-0e1f2a3b4c5d', 'Licencia',      true,  true,  true, NULL, NULL),
  ('ec28dbd2-ffa1-47c8-b116-2e3aff840d3b', 'Personal',      true,  true,  true, NULL, NULL),
  ('e67f449a-6b53-479f-afad-e902cfa3d523', 'Otro',          true,  true,  true, NULL, NULL),
  ('da054f82-340d-4ffb-a481-ac7712a5dbb3', 'Injustificada', false, false, true, NULL, NULL)
ON CONFLICT DO NOTHING;

-- ── 2. parametros_empresa (fila global) ──────────────────────────────────────
-- QUE SE ROMPE SIN ESTO, verificado en `services/configuracion_service.py`: el metodo
-- `_global_o_error` levanta AppError("No hay configuracion global cargada. ¿Se corrio
-- la migracion 085?", "CONFIG_GLOBAL_FALTANTE", 500). Falla FUERTE a proposito, en vez
-- de inventar defaults en Python, para que la pantalla no muestre valores que no son
-- los que rigen. A quien golpea:
--   - el REPORTE DE AUSENTISMO: 500, no se genera. `base_dias_habiles()` es el unico
--     de estos parametros que hoy consume un calculo.
--   - el KPI de % ausentismo del DASHBOARD: ahi NO tumba la pantalla, porque el
--     dashboard calcula cada KPI con un `_safe` — esa card sale vacia y el fallo
--     queda listado en `errores`. El resto del dashboard anda.
--   - la pantalla de Configuracion: 500 al abrirla.
--
-- Los valores: base de 22 dias habiles al mes (el divisor de la tasa de ausentismo),
-- periodo vacacional de octubre a abril, corte de antiguedad en octubre, primer anio
-- con corte en julio y 5 dias, vencimiento a los 4 anios.
-- El `id` va con el DEFAULT: nada lo referencia por id.

INSERT INTO public.parametros_empresa
  (empresa_id, base_dias_habiles, corte_antiguedad_mes, periodo_vacacional_desde_mes,
   periodo_vacacional_hasta_mes, primer_anio_mes_corte, primer_anio_dias, vencimiento_anios)
VALUES
  (NULL, 22, 10, 10, 4, 7, 5, 4)
ON CONFLICT DO NOTHING;

-- ── 3. reglas_vacaciones_escala (escala global) ──────────────────────────────
-- ⚠️ QUE SE ROMPE SIN ESTO, dicho sin exagerar: HOY, ningun calculo. `get_escala`
-- devuelve lista vacia sin error, y el encabezado de `configuracion_service.py` dice
-- explicito que la escala "se persiste y se muestra, y nada la aplica todavia" — el
-- unico parametro que un calculo consume es `base_dias_habiles`. Lo que se rompe es
-- la pantalla de Configuracion, que muestra la escala VACIA, y con ella la referencia
-- de cuantos dias corresponden por antiguedad. Quien vaya a configurar la escala de
-- una empresa arranca de cero en vez de arrancar de la global.
-- Se siembra igual porque es un catalogo de negocio real (Ley de Contrato de Trabajo
-- argentina) y porque el dia que el calculo de saldos la use, tiene que estar.
--
-- Semantica de los tramos: se aplica el de MAYOR `antiguedad_anios` que no supere la
-- del empleado. 0-4 anios -> 14 dias | 5-14 -> 21 | 15+ -> 28.

INSERT INTO public.reglas_vacaciones_escala (empresa_id, antiguedad_anios, dias) VALUES
  (NULL,  0, 14),
  (NULL,  5, 21),
  (NULL, 15, 28)
ON CONFLICT DO NOTHING;

-- ── Verificacion ─────────────────────────────────────────────────────────────
-- Los tres conteos tienen que dar 5, 1 y 3.
--   SELECT (SELECT count(*) FROM tipos_ausencia            WHERE empresa_id IS NULL) AS tipos,
--          (SELECT count(*) FROM parametros_empresa        WHERE empresa_id IS NULL) AS parametros,
--          (SELECT count(*) FROM reglas_vacaciones_escala  WHERE empresa_id IS NULL) AS escala;

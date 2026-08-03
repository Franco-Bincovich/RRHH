-- 090_dias_vacaciones_nullable.sql
--
-- ⚠️ NACIÓ NUMERADA 085 Y SE RENUMERÓ A 090. El 085 ya estaba ocupado por
-- `085_configuracion_reglas.sql`, que además YA CORRIÓ en producción — las dos se escribieron
-- el mismo día en sesiones distintas y esta quedó sin commitear. Nada lo detectó: el registro
-- de migraciones de Supabase tiene UNA fila (la 081), o sea que no es un ledger; las
-- migraciones se corren a mano y el único juez es el catálogo.
--
-- QUÉ HACE: `empleados.dias_vacaciones_asignados` pasa de "cupo anual de todos" a
-- OVERRIDE POR EMPLEADO. La columna se vuelve nullable, pierde su DEFAULT, y los
-- valores actuales se backfillean a NULL.
--
--     NULL      → regla general por antigüedad (14 / 21 desde 5 años / 28 desde 15).
--     no NULL   → override permanente para ESA persona, gana sobre la regla.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- POR QUÉ EL BACKFILL A NULL ES SEGURO — y por qué igual lleva un WHERE
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- La columna nació en la 046 con `NOT NULL DEFAULT 14`. Ese 14 nunca fue una decisión sobre
-- ningún empleado: es el default del schema, que Postgres completó en cada alta. Verificado
-- contra el catálogo vivo (30/7/2026, y RE-VERIFICADO el 3/8/2026 ya con la segunda empresa
-- cargada: ahora son 31 empleados y los 31 siguen en 14, así que la premisa aguantó el cambio
-- de padrón que la habría invalidado):
--     · los 31 empleados tienen EXACTAMENTE 14 — no hay un solo valor distinto;
--     · `auditoria` tiene CERO eventos que mencionen la columna, ni en datos_anteriores ni
--       en datos_nuevos: nadie la editó nunca desde la aplicación.
-- O sea que no hay ningún override real que este backfill pueda destruir.
--
-- 🔴 AUN ASÍ EL UPDATE LLEVA `WHERE dias_vacaciones_asignados = 14`, y no es decoración.
-- El argumento de "cero eventos de auditoría" es MÁS DÉBIL DE LO QUE PARECE: los payloads de
-- alta usan listas curadas (`_CAMPOS_EMPLEADO`, 7 campos) y esta columna no está en ninguna,
-- así que un valor escrito por el import de nómina no habría dejado evento aunque hubiera
-- sido deliberado. Hoy el WHERE es equivalente a "todas" (19/19 están en 14), así que no
-- cambia el resultado; lo que cambia es qué pasa si esta migración se corre MÁS TARDE, sobre
-- una base donde alguien ya cargó un override de 21. Sin el WHERE, ese 21 se perdería en
-- silencio. Con el WHERE, sobrevive.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 DROP DEFAULT NO ES OPCIONAL — es la mitad del cambio
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- Volver la columna nullable y dejarle el `DEFAULT 14` no serviría de nada: el write path
-- (`repositories/_empleado_write_repo.guardar`) arma el INSERT con
-- `{k: v for k, v in data.model_dump().items() if v is not None}`, o sea que un alta que no
-- manda el campo simplemente NO lo incluye en el payload — y ahí Postgres aplica el default.
-- Resultado: cada empleado nuevo nacería con un override de 14 que nadie pidió, exactamente
-- el estado del que esta migración viene a salir. El default se va con la NOT NULL.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 ORDEN DE DEPLOY: EL CÓDIGO VA ANTES QUE ESTA MIGRACIÓN
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- Igual que la 084, y por el mismo motivo invertido: acá el peligro no es un SELECT a una
-- columna borrada, es un NULL llegando a un contrato que no lo admite.
-- `schemas/empleado_out.py` declaraba `dias_vacaciones_asignados: int = 14` — NO Optional. Un
-- NULL contra ese tipo levanta ValidationError, que el handler global convierte en 500, y no
-- en el módulo de vacaciones sino en TODA lectura de empleado: el listado, la ficha, el
-- export, el dashboard. Es la misma familia de falla que la 083 describe para `fecha_desde`.
-- Con el código nuevo desplegado (Optional en el schema y nullable en el tipo del front), el
-- NULL es un valor esperado y esta migración no rompe nada.
--
-- NO DESTRUCTIVA en el sentido de que no borra columnas ni filas, pero SÍ pisa datos (el
-- backfill). Ver arriba por qué los datos que pisa no son datos.
-- Idempotente: correrla dos veces deja el mismo estado (la segunda no encuentra ningún 14).
-- NO se ejecuta acá (la corre Franco).

BEGIN;

-- El orden importa: primero se afloja la restricción, después se escribe el NULL.
ALTER TABLE public.empleados
    ALTER COLUMN dias_vacaciones_asignados DROP NOT NULL,
    ALTER COLUMN dias_vacaciones_asignados DROP DEFAULT;

UPDATE public.empleados
   SET dias_vacaciones_asignados = NULL
 WHERE dias_vacaciones_asignados = 14;

COMMENT ON COLUMN public.empleados.dias_vacaciones_asignados IS
    'OVERRIDE PERMANENTE del cupo anual de vacaciones de ESTE empleado. NULL (el caso normal) = se aplica la regla general por antigüedad, que vive en backend/config/reglas_vacaciones.py y NO en la base. Un valor acá gana sobre esa regla y no caduca. Nullable desde la migración 085: antes era NOT NULL DEFAULT 14, y ese 14 no era el cupo de nadie sino el default del schema.';

COMMIT;

NOTIFY pgrst, 'reload schema';

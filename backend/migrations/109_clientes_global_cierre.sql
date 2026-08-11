-- 109_clientes_global_cierre.sql
--
-- QUÉ HACE: borra los CUATRO objetos que quedaban de "el cliente pertenece a una empresa".
-- 🔴 DESTRUCTIVA. Es el único paso irreversible del bloque L.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- QUÉ TERMINA DE REVERTIR
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- La 102 dejó escrito, textual: «`empresa_id` NOT NULL: un cliente es de UNA empresa del grupo.
-- No hay clientes globales — a diferencia de `tipos_ausencia`, donde el catálogo base sí es
-- compartido. Acá dos empresas que le facturen al mismo cliente real son dos filas, porque la
-- relación comercial es de cada sociedad.»
--
-- La 108 sacó la EXIGENCIA (DROP NOT NULL) y puso la unicidad global. Esta saca la COLUMNA y todo
-- lo que colgaba de ella. Después de esto, `clientes` se comporta como `tipos_ausencia`: un
-- catálogo compartido, sin dueño.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 POR QUÉ VA DESPUÉS DEL DEPLOY Y NO ANTES
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- El código que HOY está sirviendo tráfico todavía lee `clientes.empresa_id`: el repo hace
-- `SELECT *` y `ClienteResponse.empresa_id` es obligatorio, y el alta hace
-- `INSERT (empresa_id, nombre)`. Corriendo esto antes del deploy, ese código entra en 500 de dos
-- formas distintas —42703 en el INSERT y `ValidationError` de Pydantic en cada lectura— y el
-- módulo de clientes queda caído hasta que salga el código nuevo.
--
-- Al revés no pasa nada: el código nuevo NO manda ni lee `empresa_id`, así que convive sin
-- problema con la columna todavía presente. Por eso la ventana segura es
--
--     108 (preparación)  →  DEPLOY del código  →  109 (cierre, este archivo)
--
-- y por eso son dos migraciones y no una.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 LA 108 TIENE QUE ESTAR CORRIDA. NO ES UNA RECOMENDACIÓN.
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- Esta migración DROPEA `ux_clientes_nombre_por_empresa`, que hoy es la única unicidad de nombre
-- que tiene la tabla. El reemplazo —`ux_clientes_nombre_global`, sobre `lower(nombre)`— lo crea
-- la 108.
--
-- Si esta corre sin aquella, la tabla queda **SIN NINGUNA UNICIDAD DE NOMBRE**, en silencio: no
-- falla nada, y "Acme" pasa a poder cargarse dos veces. El chequeo del service (`existe_nombre`)
-- sigue devolviendo su 409, pero es una lectura previa al INSERT con una ventana de carrera que
-- solo el índice cierra — o sea que el 99% de las veces parece funcionar. Los reportes de costo
-- por cliente se parten sin que nadie se entere.
--
-- La guarda de abajo lo impide: si el índice global no existe, la migración aborta antes de
-- borrar nada.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- QUÉ NO SE TOCA
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- · `horas_proyecto.cliente_id` y su FK `horas_proyecto_cliente_id_fkey` → INTACTAS. La relación
--   hora→cliente no cambió: lo que se fue es cliente→empresa. Sigue siendo una FK SIN ON DELETE,
--   que es lo que obliga a que la baja de un cliente sea lógica (`activo=false`) y nunca física.
-- · `clientes_pkey` → intacta.
-- · `ux_clientes_nombre_global` (108) → es el que QUEDA. No se toca.
-- · `horas_proyecto.empresa_id` y `empleado_empresa_id` → intactas y NO redundantes: salen del
--   empleado y del proyecto, nunca del cliente. Verificado en el rastreo de L-diagnóstico.

BEGIN;

-- Guarda: sin el índice de la 108, seguir dejaría la tabla sin unicidad de nombre.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = 'clientes'
          AND indexname = 'ux_clientes_nombre_global'
    ) THEN
        RAISE EXCEPTION
            'Falta ux_clientes_nombre_global: corré la migración 108 antes que esta. '
            'Sin ese índice, dropear ux_clientes_nombre_por_empresa deja la tabla sin '
            'ninguna unicidad de nombre.';
    END IF;
END $$;

-- 1) El índice único viejo, sobre (empresa_id, lower(nombre)). Su reemplazo ya está.
DROP INDEX IF EXISTS public.ux_clientes_nombre_por_empresa;

-- 2) El índice de lookup por empresa. Queda sin objeto: nadie filtra por esa columna.
DROP INDEX IF EXISTS public.idx_clientes_empresa;

-- 3) La FK a empresas. Sin ON DELETE, por la decisión de la 102 (borrar una empresa no podía
--    llevarse en silencio los clientes contra los que había horas cargadas).
ALTER TABLE public.clientes DROP CONSTRAINT IF EXISTS clientes_empresa_id_fkey;

-- 4) La columna. Los tres objetos de arriba dependían de ella, así que este DROP los habría
--    borrado igual por cascada implícita; se enumeran uno por uno para que el diff diga QUÉ
--    desaparece y no haya que deducirlo.
ALTER TABLE public.clientes DROP COLUMN IF EXISTS empresa_id;

COMMIT;


-- ═════════════════════════════════════════════════════════════════════════════════════════
-- VERIFICACIÓN POSTERIOR — correr DESPUÉS, a mano. Ninguna de estas escribe.
-- ═════════════════════════════════════════════════════════════════════════════════════════
--
-- 1. La columna NO está, y las otras cinco sí:
--
--    SELECT column_name FROM information_schema.columns
--    WHERE table_schema = 'public' AND table_name = 'clientes'
--    ORDER BY ordinal_position;
--    -- ESPERADO: id, nombre, activo, created_at, updated_at  (5 filas, sin empresa_id)
--
-- 2. Quedó el índice global y NO los dos viejos:
--
--    SELECT indexname FROM pg_indexes
--    WHERE schemaname = 'public' AND tablename = 'clientes' ORDER BY indexname;
--    -- ESPERADO: clientes_pkey, ux_clientes_nombre_global   (2 filas)
--    -- Si aparece ux_clientes_nombre_por_empresa o idx_clientes_empresa, el DROP no corrió.
--
-- 3. La FK a empresas no está (y la PK sí):
--
--    SELECT conname FROM pg_constraint WHERE conrelid = 'public.clientes'::regclass;
--    -- ESPERADO: clientes_pkey  (1 fila, sin clientes_empresa_id_fkey)
--
-- 4. 🔴 LOS TRES CLIENTES SIGUEN AHÍ CON SU NOMBRE. Es lo único que mira el dato y no el
--    schema: un DROP COLUMN no puede perder filas, pero verificarlo cuesta una query y
--    confirma que se corrió contra la base correcta.
--
--    SELECT id, nombre, activo FROM clientes ORDER BY nombre;
--    -- ESPERADO (medido antes de la migración): Berazategui, Escobar, Paysandu — los tres activos.
--
-- 5. 🔴 LA HORA IMPUTADA A PAYSANDU SIGUE APUNTANDO A SU CLIENTE. Es la verificación que
--    importa: `horas_proyecto.cliente_id` es una FK sin ON DELETE, así que si algo hubiera
--    tocado la fila del cliente, esta query devolvería 0 o el nombre en NULL.
--
--    SELECT h.id, h.fecha, h.horas, c.nombre AS cliente
--    FROM horas_proyecto h JOIN clientes c ON c.id = h.cliente_id
--    WHERE c.nombre = 'Paysandu';
--    -- ESPERADO: 1 fila, cliente = 'Paysandu'.
--
-- 6. La unicidad global funciona de verdad (NO dejar esta corrida — hace ROLLBACK):
--
--    BEGIN;
--    INSERT INTO clientes (nombre) VALUES ('paysandu');
--    -- ESPERADO: ERROR 23505 duplicate key value violates unique constraint
--    --           "ux_clientes_nombre_global".  Si entra, la 108 no corrió.
--    ROLLBACK;

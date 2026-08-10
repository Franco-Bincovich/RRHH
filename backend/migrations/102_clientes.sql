-- 102_clientes.sql
--
-- QUÉ HACE: tabla NUEVA `clientes` — el catálogo, por empresa, que RRHH carga y edita, y del
-- que cuelga cada carga de horas del módulo nuevo.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- POR QUÉ UNA TABLA Y NO UNA COLUMNA EN `proyectos`
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- `proyectos` NO participa de este flujo. Sus 8 filas de producción son una copia 1:1 de
-- `empleados.gerencia` —las creó el import de nómina (services/_nomina_proyectos.py), no una
-- persona— así que no son clientes ni proyectos: son centros de imputación. Colgar el cliente
-- de ahí ataría el catálogo nuevo a una tabla que un import reescribe solo.
--
-- El "proyecto" del flujo nuevo es TEXTO LIBRE sobre `horas_proyecto` (ver migración 103), y no
-- tiene ninguna relación con esta tabla ni con `proyectos`.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- DECISIONES DE FORMA
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- · `empresa_id` NOT NULL: un cliente es de UNA empresa del grupo. No hay clientes globales —
--   a diferencia de `tipos_ausencia`, donde el catálogo base sí es compartido. Acá dos empresas
--   que le facturen al mismo cliente real son dos filas, porque la relación comercial es de
--   cada sociedad.
-- · SIN `ON DELETE CASCADE` contra empresas: borrar una empresa no puede llevarse en silencio
--   los clientes contra los que hay horas cargadas. Mismo criterio que `proyectos`.
-- · `activo` en vez de DELETE: la baja es lógica. `horas_proyecto.cliente_id` es una FK sin
--   ON DELETE (migración 103), así que borrar un cliente con horas fallaría — y si no fallara,
--   se llevaría puesto el historial de imputación. Es exactamente el razonamiento de
--   `tipos_ausencia_repo.update`, que por eso tampoco tiene delete.
--
-- 🔴 UNICIDAD CASE-INSENSITIVE, Y NO ES UN LUJO
-- El índice va sobre `(empresa_id, lower(nombre))`, no sobre `(empresa_id, nombre)`. El
-- precedente de lo que pasa sin unicidad está en la tabla de al lado: `proyectos` NO tiene
-- ninguna, y por eso `_nomina_proyectos.py` deduplica con un CACHÉ EN MEMORIA DE PYTHON
-- (`self._cache`, normalizando el nombre a mano) — que no sobrevive a dos procesos concurrentes.
-- Con tres personas de RRHH tipeando a mano, "Acme" y "ACME" son el caso normal, no el borde, y
-- una unicidad sensible a mayúsculas no los ve.
-- ⚠️ Un índice por expresión NO sirve como target de `on_conflict` de PostgREST. No importa acá:
-- clientes se da de alta con INSERT, nunca con upsert.
--
-- 🔴 EL TRIGGER `updated_at` VA EN TRES ARCHIVOS, Y ESTE ES EL PRIMERO
--   1. esta migración          → el trigger en Supabase (producción)
--   2. migracionAWS/.../077    → el trigger en RDS
--   3. backend/db/schema.sql   → la columna, para que el barrido derive el candidato
-- `tests/test_triggers_updated_at.py` compara (3) contra (2) y avisa si falta en la 077.
-- NO cubre (1): ya nacieron sin él `usuario_integraciones` (mig 032) y `plantillas_mail`
-- (mig 087), y hubo que arreglarlas después con la 091. Por eso se declara acá explícitamente.
--
-- La función `public.set_updated_at()` ya existe (la crea la 001, la usan los otros 41
-- triggers). No se recrea: un CREATE OR REPLACE de una función compartida para agregar uno es
-- riesgo sin beneficio.
--
-- NO DESTRUCTIVA: solo agrega. Idempotente: IF NOT EXISTS + DROP IF EXISTS + CREATE.
-- NO se ejecuta acá (la corre Franco).

BEGIN;

CREATE TABLE IF NOT EXISTS public.clientes (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    nombre text NOT NULL,
    activo boolean NOT NULL DEFAULT true,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- 🔴 LA PK SE AGREGA SI FALTA — NO con DROP + ADD, que es el molde de la 086.
-- Acá ese molde NO sirve: la migración 103 crea `horas_proyecto_cliente_id_fkey` apuntando a
-- `clientes(id)`, y una FK DEPENDE de la PK que referencia. Un `DROP CONSTRAINT clientes_pkey`
-- con esa FK ya creada aborta con "cannot drop constraint ... because other objects depend on
-- it", así que re-correr la 102 después de la 103 rompería. En la 086 el mismo patrón es
-- inofensivo solo porque nadie referencia esa tabla.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'clientes_pkey') THEN
        ALTER TABLE public.clientes ADD CONSTRAINT clientes_pkey PRIMARY KEY (id);
    END IF;
END $$;

-- Esta sí puede ir con DROP + ADD: nada depende de una FK saliente.
ALTER TABLE public.clientes DROP CONSTRAINT IF EXISTS clientes_empresa_id_fkey;
ALTER TABLE public.clientes
    ADD CONSTRAINT clientes_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);

-- Ver la nota de unicidad del encabezado.
CREATE UNIQUE INDEX IF NOT EXISTS ux_clientes_nombre_por_empresa
    ON public.clientes USING btree (empresa_id, lower(nombre));

-- El listado del catálogo siempre entra por empresa (o por todas, en modo consolidado).
CREATE INDEX IF NOT EXISTS idx_clientes_empresa ON public.clientes USING btree (empresa_id);

DROP TRIGGER IF EXISTS trg_clientes_updated_at ON public.clientes;
CREATE TRIGGER trg_clientes_updated_at
    BEFORE UPDATE ON public.clientes
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

COMMIT;

-- 095_objetivos_jerarquia.sql
--
-- Subobjetivos: una self-FK `parent_id` sobre la misma tabla `objetivos`.
--
-- POR QUÉ UNA COLUMNA Y NO UNA TABLA APARTE: un subobjetivo tiene título, responsable,
-- prioridad, estado y fecha de entrega — o sea, ES un objetivo. Una tabla aparte duplicaría las
-- 10 columnas y los dos CHECK, y obligaría a un UNION en cada lectura del tablero. Precedente
-- vivo en este mismo repo: `tipos_ausencia.padre_id` (migración 088).
--
-- 🔴 PROFUNDIDAD MÁXIMA 2 (padre → hijo, sin nietos), Y LA GUARDA **NO** ESTÁ ACÁ. Un CHECK de
-- Postgres no puede consultar otra fila, así que "el padre que elijo no puede tener a su vez un
-- padre" es imposible de expresar como constraint de tabla. La guarda vive en
-- `services/_objetivos_jerarquia.py`, exactamente como la de `_tipos_jerarquia.py` para los
-- subtipos de ausencia. **Consecuencia declarada: por SQL directo se puede crear un nieto.** La
-- alternativa sería un trigger, que es la misma lógica en un segundo lugar y en otro lenguaje.
--
-- 🔴 ON DELETE CASCADE, y es una decisión de producto, no una comodidad: un subobjetivo sin
-- padre no significa nada. Sin el cascade, borrar un padre fallaría por violación de FK y la
-- pantalla mostraría un 500 sin explicación; con SET NULL, los hijos quedarían como raíces
-- sueltas que nadie creó y que aparecerían en el tablero como objetivos independientes.
--
-- MIGRACIÓN ADITIVA: no borra ni renombra nada. `parent_id` es NULLABLE, así que la única fila
-- de producción (y cualquier objetivo existente) queda como raíz sin tocarla. Es reversible con
-- un DROP COLUMN mientras el código todavía no la escriba.

ALTER TABLE public.objetivos
    ADD COLUMN IF NOT EXISTS parent_id uuid;

-- La FK va aparte del ADD COLUMN para que el script sea reejecutable: si la columna ya existe
-- pero la constraint no (por un intento a medias), esto la completa igual.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'objetivos_parent_id_fkey'
    ) THEN
        ALTER TABLE public.objetivos
            ADD CONSTRAINT objetivos_parent_id_fkey
            FOREIGN KEY (parent_id) REFERENCES public.objetivos(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Índice sobre parent_id: TODA lectura del tablero agrupa los hijos por su padre, así que este
-- índice se usa en el camino caliente, no en un reporte ocasional. Sin él, armar el árbol es un
-- seq scan por cada padre.
CREATE INDEX IF NOT EXISTS idx_obj_parent ON public.objetivos USING btree (parent_id);

-- 081_add_domicilio_desglosado.sql
--
-- QUÉ HACE: desglosa el domicilio del empleado en seis columnas estructuradas.
--
-- POR QUÉ. `empleados.domicilio` es un único campo de texto libre, así que el domicilio no se
-- puede filtrar ni agregar: no hay forma de responder "cuántos empleados viven en cada
-- provincia" ni de agrupar por localidad. El compromiso con el directorio pide "domicilio
-- completo", y completo significa utilizable, no solo guardado.
--
-- De las seis columnas, tres existen para AGREGAR (provincia, localidad, cp) y tres para que
-- el dato sea una dirección a la que efectivamente se le pueda mandar algo (calle, numero,
-- piso_depto). `cp` es la única clave normalizada: sobrevive a que una persona escriba
-- "CÓRDOBA CAPITAL" y otra "Cordoba Cap.", que con carga manual va a pasar.
--
-- `domicilio` NO SE BORRA. Queda como destino de lo que no encaje en los estructurados y como
-- referencia para completarlos. Al momento de esta migración está 0/19 en producción, así que
-- no hay ningún dato que migrar ni que parsear: las seis columnas nacen en NULL.
--
-- NO DESTRUCTIVA: solo agrega columnas nullable. No toca datos existentes, no reescribe
-- `domicilio`, y es segura de correr con la aplicación arriba.
--
-- ⚠️ `ubicacion` es OTRA COSA y no se toca: sale de la columna "Ubicación Física" del CSV de
-- nómina y es dónde la persona TRABAJA, no dónde vive.
--
-- `domicilio_numero` es TEXT y no un entero a propósito: existen "S/N", "1234 bis", "KM 4".
--
-- La provincia se valida en la capa de aplicación contra las 24 jurisdicciones argentinas
-- (23 provincias + CABA, nombres oficiales del IGN vía apis.datos.gob.ar). NO se agrega un
-- CHECK acá: la lista vive en un solo lugar (backend/schemas/_provincias.py) y duplicarla en
-- la base daría dos fuentes de verdad que se pueden separar en silencio. Tampoco se crea una
-- tabla: son 24 valores que no cambian, y una tabla compraría un join y una migración por
-- nada.

ALTER TABLE public.empleados
    ADD COLUMN IF NOT EXISTS domicilio_calle      text,
    ADD COLUMN IF NOT EXISTS domicilio_numero     text,
    ADD COLUMN IF NOT EXISTS domicilio_piso_depto text,
    ADD COLUMN IF NOT EXISTS domicilio_localidad  text,
    ADD COLUMN IF NOT EXISTS domicilio_provincia  text,
    ADD COLUMN IF NOT EXISTS domicilio_cp         text;

COMMENT ON COLUMN public.empleados.domicilio IS
    'Domicilio en texto libre (legado). Se conserva como destino de lo que no encaja en las columnas domicilio_* y como referencia para completarlas.';
COMMENT ON COLUMN public.empleados.domicilio_numero IS
    'Altura, como texto: admite "S/N", "1234 bis", "KM 4".';
COMMENT ON COLUMN public.empleados.domicilio_provincia IS
    'Una de las 24 jurisdicciones argentinas. Validado en la aplicación (backend/schemas/_provincias.py), no por CHECK.';

-- Índice sobre los dos cortes que la migración vino a habilitar. Parcial: hoy las seis
-- columnas están en NULL, y un índice que indexa 19 NULLs no sirve de nada.
CREATE INDEX IF NOT EXISTS idx_empleados_domicilio_provincia
    ON public.empleados (domicilio_provincia) WHERE domicilio_provincia IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_empleados_domicilio_localidad
    ON public.empleados (domicilio_localidad) WHERE domicilio_localidad IS NOT NULL;

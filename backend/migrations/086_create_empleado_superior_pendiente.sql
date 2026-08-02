-- 086_create_empleado_superior_pendiente.sql
--
-- QUÉ HACE: tabla NUEVA que guarda el nombre del superior que el import de nómina leyó del CSV
-- pero NO pudo resolver a un `manager_id`. Es el insumo del botón "resolver pendientes".
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- POR QUÉ HACE FALTA GUARDARLO
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- El CSV de nómina trae "Apellido Superior" y "Nombre Superior" en las 19 filas, y el import
-- ahora los resuelve a `manager_id` (ver services/_nomina_superiores.py). Pero en el archivo
-- REAL, 5 de los 6 jefes NO ESTÁN CARGADOS como empleados: no hay contra qué matchearlos.
--
-- Sin esta tabla, el nombre del jefe se pierde en cuanto termina el request. La única forma de
-- reintentar sería volver a subir el CSV — y RRHH no necesariamente lo tiene a mano cuando por
-- fin da de alta al jefe que faltaba. Con la tabla, el día que ese jefe existe, un botón
-- resuelve todo lo pendiente contra el estado ACTUAL de `empleados`.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 POR QUÉ UNA TABLA Y NO DOS COLUMNAS EN `empleados`
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- Se evaluaron las dos. Dos columnas (`superior_apellido_csv`, `superior_nombre_csv`) evitan
-- una tabla y un repo más (que en este proyecto es uno más a portar a asyncpg). Pierden en lo
-- que importa: la pregunta que hace el botón es "¿QUÉ QUEDÓ PENDIENTE?".
--
--   · Sobre columnas, esa pregunta es un barrido de `empleados` con un predicado compuesto
--     (`manager_id IS NULL AND superior_apellido_csv IS NOT NULL`), sobre una tabla que crece
--     con cada empleado que NUNCA tuvo un pendiente.
--   · Sobre esta tabla es un SELECT de algo que en estado sano tiene CERO filas.
--
-- Y el estado es transitorio por definición: una fila que DESAPARECE al resolverse modela mejor
-- "pendiente" que dos columnas que quedan en NULL para siempre en el 90% del padrón.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- DECISIONES DE FORMA
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- · PK = empleado_id. Un empleado tiene UN superior: no hay caso de dos pendientes para el
--   mismo. Además hace que el re-import sea un upsert natural (pisa el pendiente anterior con
--   lo que diga el archivo nuevo) en vez de acumular basura.
-- · ON DELETE CASCADE contra empleados: si el empleado se borra, su pendiente no significa nada.
-- · empresa_id es la DEL EMPLEADO, no la del superior — que es justamente lo que no sabemos.
--   Sirve para scopear el listado del botón, no para acotar la búsqueda: el superior puede ser
--   de otra empresa del grupo (decisión de producto 2/8/2026).
-- · `nombre_csv` es NULLABLE: el CSV puede traer solo el apellido.
-- · `motivo` guarda POR QUÉ quedó pendiente (sin candidato / ambiguo / ciclo). Es texto y no un
--   CHECK con enum a propósito: es un mensaje para que un humano de RRHH entienda qué pasó, no
--   un estado sobre el que el código ramifique. Un CHECK obligaría a una migración cada vez que
--   se afine la redacción de un mensaje.
-- · Sin `updated_at`: no hay trigger que mantener (schema.sql no trae los 36 de updated_at, se
--   recrean aparte en la 077) y la fila se pisa entera en cada re-import.
--
-- ⚠️ ES SOLO HACIA ADELANTE. El import de julio ya corrió sin esta tabla: sus superiores no
-- quedaron registrados en ningún lado. Se recuperan re-subiendo ese CSV, no desde la base.

CREATE TABLE IF NOT EXISTS public.empleado_superior_pendiente (
    empleado_id uuid NOT NULL,
    empresa_id uuid NOT NULL,
    apellido_csv text NOT NULL,
    nombre_csv text,
    motivo text NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

ALTER TABLE public.empleado_superior_pendiente
    DROP CONSTRAINT IF EXISTS empleado_superior_pendiente_pkey;
ALTER TABLE public.empleado_superior_pendiente
    ADD CONSTRAINT empleado_superior_pendiente_pkey PRIMARY KEY (empleado_id);

ALTER TABLE public.empleado_superior_pendiente
    DROP CONSTRAINT IF EXISTS empleado_superior_pendiente_empleado_id_fkey;
ALTER TABLE public.empleado_superior_pendiente
    ADD CONSTRAINT empleado_superior_pendiente_empleado_id_fkey
    FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE;

ALTER TABLE public.empleado_superior_pendiente
    DROP CONSTRAINT IF EXISTS empleado_superior_pendiente_empresa_id_fkey;
ALTER TABLE public.empleado_superior_pendiente
    ADD CONSTRAINT empleado_superior_pendiente_empresa_id_fkey
    FOREIGN KEY (empresa_id) REFERENCES empresas(id);

-- El listado del botón se scopea por empresa (el selector del sidebar). Con 0 filas en estado
-- sano el índice no cuesta nada; sin él, el día que haya cientos de pendientes es un seq scan.
CREATE INDEX IF NOT EXISTS idx_esp_empresa ON public.empleado_superior_pendiente (empresa_id);

-- 107_tipo_ausencia_licencia.sql
--
-- QUÉ HACE: siembra el tipo de ausencia "Licencia", que es el que usa la carga del link público.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- POR QUÉ UN TIPO NUEVO Y NO UNO DE LOS CUATRO QUE YA HAY
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- El catálogo tiene Enfermedad, Personal, Otro (activos) e Injustificada (inactivo desde la 088).
-- Los tres activos son MOTIVOS: describen POR QUÉ faltó la persona, y esa es una calificación
-- que RRHH hace mirando la documentación.
--
-- Lo que el empleado carga desde el link no es un motivo: es el HECHO de que ese día no trabajó.
-- Meterlo en "Enfermedad" sería inventar un diagnóstico, y meterlo en "Otro" —el cajón de
-- sastre— haría que el reporte de ausentismo por tipo mezcle las autocargas con todo lo demás
-- que RRHH no supo clasificar. Un tipo propio deja el reporte legible: "Licencia" se lee como
-- "lo declaró la persona y todavía nadie lo revisó".
--
-- `cuenta_ausentismo = true`: la licencia SÍ computa para el ausentismo. Es lo pedido, y además
-- la columna vive en el tipo (mig 088), así que se decide una sola vez acá.
--
-- 🔴 EL ID ES FIJO, Y ESA ES LA DECISIÓN IMPORTANTE DE ESTA MIGRACIÓN.
-- El service necesita referenciar este tipo. Buscarlo POR NOMBRE sería frágil hasta el punto de
-- ser un bug esperando: `tipos_ausencia.nombre` lo edita RRHH desde la pantalla de configuración,
-- así que alguien que lo renombre a "Licencias" rompería la carga pública sin enterarse — y es
-- exactamente el modo de falla que el repo ya documentó para el agrupamiento de subtipos ("el
-- agrupamiento va por ID, no por texto, porque aplanar dejaría el reporte dependiendo de un LIKE
-- sobre un nombre que RRHH edita desde la UI"). Con un UUID fijo, renombrarlo es cosmético.
--
-- ⚠️ El id está DUPLICADO en `services/_carga_licencia.py::TIPO_LICENCIA_ID`. Es un espejo, y no
-- hay forma de evitarlo: un valor sembrado por SQL que el código tiene que nombrar. Lo cubre un
-- test que compara el literal del código contra el de este archivo.
--
-- Va como tipo GLOBAL (`empresa_id NULL`), igual que los otros cuatro base: la carga pública es
-- del sistema, no de una sociedad. `ux_tipos_ausencia_nombre_global` garantiza que no haya otro
-- "Licencia" global.
--
-- NO DESTRUCTIVA: inserta una fila. Idempotente por el ON CONFLICT sobre la PK: correrla dos
-- veces deja el mismo estado y NO pisa un nombre que RRHH haya editado.
-- NO se ejecuta acá (la corre Franco).

BEGIN;

INSERT INTO public.tipos_ausencia (id, nombre, es_base, activo, cuenta_ausentismo, empresa_id)
VALUES ('9f3b7c2a-1d4e-4a6b-8c5d-0e1f2a3b4c5d', 'Licencia', true, true, true, NULL)
ON CONFLICT (id) DO NOTHING;

COMMIT;

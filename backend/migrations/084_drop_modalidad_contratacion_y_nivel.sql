-- 084_drop_modalidad_contratacion_y_nivel.sql
--
-- QUÉ HACE: borra dos columnas de `empleados` que nadie escribe y que duplican a otras dos.
--   · modalidad_contratacion  → el dato real vive en `tipo_contrato`
--   · nivel                   → el dato real vive en `seniority`
--
-- ⚠️ ES LA ÚNICA MIGRACIÓN DESTRUCTIVA DE ESTA TANDA (DROP COLUMN). Ver "por qué es segura ahora".
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 modalidad_contratacion — NO era "otro concepto": era el MISMO que tipo_contrato
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- La columna nació en la migración 060 (legajo ampliado) como campo informativo de ficha. Poco
-- después, la 065 resolvió el mismo problema por otro lado: el CSV de nómina trae el tipo de
-- contrato en una columna llamada "Modalidad Contratacion" con valores libres
-- ("RELACION DE DEPENDENCIA"), y esa 065 decidió —textualmente— mandarlo a `tipo_contrato` y
-- convertirlo a TEXT para que entrara.
--
-- O sea que la 065 consolidó DE HECHO pero no DE DERECHO: dejó `modalidad_contratacion` viva,
-- vacía y sin migrar. El resultado medible en producción antes de esta migración:
--     modalidad_contratacion   0/19   ← ningún camino la escribe
--     tipo_contrato           19/19   "RELACION DE DEPENDENCIA"  ← el import
--
-- Y tuvo una consecuencia visible: el reporte R4 (distribución de plantilla) y el KPI de
-- distribución del dashboard leían `modalidad_contratacion`, así que mostraban
-- "Sin especificar: 19" teniendo el dato cargado en la columna de al lado. Eso se corrige en
-- el mismo commit que esta migración (services/reportes/_reporte_distribucion.py).
--
-- ⚠️ `modalidad_trabajo` NO SE TOCA. Es un concepto DISTINTO —dónde trabaja la persona:
-- presencial/remoto/híbrido, con CHECK cerrado— y no tiene nada que ver con cómo está
-- contratada. Su 19/19 en "presencial" NO es un dato cargado: es el default del schema
-- (`schemas/empleado.py`, `modalidad_trabajo: str = "presencial"`), que Pydantic completa porque
-- el CSV no trae la columna. Queda anotado acá para que nadie lo lea como "todos son
-- presenciales": hoy ese campo no tiene información real, solo su default.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- nivel — residuo puro de seniority
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- `nivel` viene de la migración 003 como VARCHAR(20) con CHECK cerrado a siete literales
-- ('junior','semi_senior','senior','lider','manager','director','c_level'). La 060 agregó
-- `seniority` como TEXTO LIBRE porque los valores del CSV real —"TRAINEE", "SIN DATOS"— no
-- entran en ese CHECK. Desde entonces `nivel` no lo escribe nadie.
--     nivel      0/19    · CHECK incompatible con el dato real
--     seniority  4/19    "SIN DATOS", "TRAINEE"
-- Verificado: CERO referencias en el código (ni en schemas Pydantic, ni en services, ni en el
-- front). El reporte R4 ya leía `seniority`, el campo correcto — a diferencia de modalidad,
-- acá no había nada roto, solo una columna muerta.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- POR QUÉ ES SEGURA AHORA Y NO DESPUÉS
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- Las dos columnas están en 0/19 en producción: no hay UN dato que migrar. Esa es toda la
-- ventana. Cuando entren los 2-5 imports de nómina de 50-120 empleados cada uno, el dato de
-- contratación va a estar en `tipo_contrato` para 250-600 filas, y borrar la columna duplicada
-- dejaría de ser un DROP y pasaría a ser una migración de datos con su propio riesgo.
--
-- 🔴 ORDEN DE DEPLOY: EL CÓDIGO VA ANTES QUE ESTA MIGRACIÓN. Es al revés que una migración
-- aditiva. Si la columna se borra mientras el código viejo sigue arriba, todo SELECT que la
-- pida (el listado de empleados, la ficha, el export) falla con 42703. Con el código nuevo ya
-- desplegado, la columna queda sin lectores y el DROP no rompe nada.
--
-- Idempotente: DROP COLUMN IF EXISTS. NO se ejecuta acá (la corre Franco).

BEGIN;

ALTER TABLE public.empleados
    DROP COLUMN IF EXISTS modalidad_contratacion,
    DROP COLUMN IF EXISTS nivel;

COMMENT ON COLUMN public.empleados.tipo_contrato IS
    'Cómo está contratada la persona (relación de dependencia, monotributo, ...). TEXTO LIBRE desde la migración 065: lo escribe el import de nómina desde la columna "Modalidad Contratacion" del CSV. Absorbió a la ex `modalidad_contratacion`, borrada en la 084.';
COMMENT ON COLUMN public.empleados.modalidad_trabajo IS
    'DÓNDE trabaja: presencial | remoto | hibrido (CHECK cerrado). Concepto DISTINTO de tipo_contrato. El CSV de nómina no lo trae, así que hoy todas las filas tienen el default del schema ("presencial"), que no es un dato cargado.';
COMMENT ON COLUMN public.empleados.seniority IS
    'Seniority en TEXTO LIBRE (migración 060): el CSV trae valores como "TRAINEE" o "SIN DATOS" que no entraban en el CHECK de la ex `nivel`, borrada en la 084.';

COMMIT;

NOTIFY pgrst, 'reload schema';

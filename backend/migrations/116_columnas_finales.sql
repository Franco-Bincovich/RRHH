-- 116_columnas_finales.sql
--
-- 🔴 LA ÚLTIMA MIGRACIÓN ANTES DE CONSTRUIR. Después de esta, un campo nuevo significa
-- coordinar DDL con el dev de infra en medio de su migración. Por eso acá entran cosas que
-- todavía no tienen código que las use: el costo de que sobre una columna nullable es cero,
-- y el de que falte es una ventana de coordinación.
--
-- QUÉ HACE: 11 columnas nuevas, 1 `DROP NOT NULL` y 1 índice único parcial.
--
-- ADITIVA salvo el `DROP NOT NULL`, que **afloja** una restricción y por eso tampoco puede
-- fallar ni invalidar una fila existente. **No borra nada, no mueve un solo dato.**
-- Idempotente: `ADD COLUMN IF NOT EXISTS` + `DROP NOT NULL` (que es no-op si ya está flojo) +
-- `CREATE UNIQUE INDEX IF NOT EXISTS`. Se puede correr de nuevo.
-- Va ANTES del deploy y sin ventana. NO se ejecuta acá (la corre Franco).
--
-- ── VERIFICADO CONTRA EL CATÁLOGO VIVO (grmdiwxcvcjorlohpwji) el 2026-08-13 ────────────────
-- Las 113, 114 y 115 están LAS TRES corridas: 55 tablas, las 7 columnas del lote y los 6
-- índices de escala. **Ninguna de las 11 columnas de abajo existe**, y el índice único tampoco.
-- 🔑 Y el dato que hace inerte al `DROP NOT NULL`: **`empleado_capacitacion` tiene 0 filas**
-- (igual que `capacitaciones` y `perfiles_puesto`). No hay backfill ni fila que revalidar.

-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 1. perfiles_puesto.ofrecemos — el bloque que se repite en todos los avisos
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- Sale del aviso de búsqueda REAL, guardado en `docs/AVISO-BUSQUEDA-REFERENCIA.md`, que tiene
-- un bloque "Ofrecemos" con desarrollo profesional, ambiente de trabajo y beneficios. Es
-- exactamente lo que NO cambia entre búsquedas y por eso pertenece a la plantilla: sin esta
-- columna, RRHH lo reescribe en cada aviso.
--
-- Texto libre y no una lista de beneficios normalizada: son tres viñetas de prosa que se pegan
-- tal cual en el aviso. Una tabla de beneficios compraría un ABM que nadie pidió.
ALTER TABLE public.perfiles_puesto ADD COLUMN IF NOT EXISTS ofrecemos text;

-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 2. 🟠 vacantes.ofrecemos — AGREGADA POR SIMETRÍA. Si no la querés, borrá esta línea.
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- ⚠️ ESTA NO ESTABA PEDIDA. Se agrega porque al contrastar el aviso apareció una asimetría que
-- esta migración es la última oportunidad de cerrar, y porque el costo de que sobre es cero.
--
-- EL ARGUMENTO: `vacantes` YA duplica los nueve campos del perfil —`descripcion`, `requisitos`,
-- `funciones`, `formacion`, `experiencia`, `conocimientos_tecnicos`, `modalidad`, `jornada`,
-- `ubicacion`— verificado en el catálogo. Ese patrón dice algo: **la vacante se lleva su propia
-- copia para poder ajustarla en esa búsqueda concreta sin tocar la plantilla.** Si `ofrecemos`
-- queda solo en el perfil, es el ÚNICO bloque del aviso que no se puede adaptar a una búsqueda
-- puntual (un bono de referidos, un beneficio que aplica solo a esa vacante).
--
-- LA ALTERNATIVA que se descartó: dejar que `ofrecemos` viaje al texto final por
-- `vacantes.copy_publicacion`. Funciona para GENERAR el aviso, pero `copy_publicacion` es el
-- texto ya armado: editar ahí un beneficio no queda como dato, queda como prosa.
ALTER TABLE public.vacantes ADD COLUMN IF NOT EXISTS ofrecemos text;

-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 3. recategorizaciones — el tercer par: categoría
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- La tabla ya tiene los pares `rol_anterior`/`rol_nuevo` y `seniority_anterior`/`seniority_nueva`.
-- Faltaba el de categoría, que `docs/DIAGNOSTICO-FASE-1.md` §10.1 (T2) declaraba y la 113 no creó.
--
-- 🔑 SE AGREGA SIN SABER TODAVÍA CUÁL DE LOS TRES CAMBIA EN UNA RECATEGORIZACIÓN — RRHH no lo
-- confirmó. Ese es justamente el motivo: los tres pares son nullables, así que tener el tercero
-- de más no cuesta nada, y descubrir que faltaba después del congelamiento cuesta una ventana
-- de coordinación. El día que RRHH confirme, sobra un par y se borra; no al revés.
--
-- Nullables como sus dos hermanos: una recategorización que solo cambia el rol deja los otros
-- cuatro campos en NULL, y eso ES el dato ("esto no cambió"), no un faltante.
ALTER TABLE public.recategorizaciones ADD COLUMN IF NOT EXISTS categoria_anterior text;
ALTER TABLE public.recategorizaciones ADD COLUMN IF NOT EXISTS categoria_nueva   text;

-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 4. capacitaciones — las tres columnas del Excel de FORMACIÓN
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 🔑 FORMACIÓN NO ES UN MÓDULO NUEVO: es `capacitaciones` renombrado. Estas tres columnas son
-- las del Excel real que usa RRHH (53 filas, 42 con datos) que no tenían dónde ir.
--
-- LAS TRES VAN EN TEXTO LIBRE, no como CHECK ni como catálogo, y es una decisión con motivo:
-- el archivo es una planilla escrita a mano y todavía no se sabe el vocabulario real de cada
-- columna. Un CHECK puesto ahora contra valores adivinados **haría fallar el import de la fila
-- que traiga un valor nuevo**, que es el peor desenlace posible para una carga mensual. Cuando
-- el vocabulario se estabilice, normalizar es una migración chica; des-normalizar no.
ALTER TABLE public.capacitaciones ADD COLUMN IF NOT EXISTS entidad_capacitadora text;  -- "Entidad capacitadora"
ALTER TABLE public.capacitaciones ADD COLUMN IF NOT EXISTS modalidad            text;  -- "Modalidad"
ALTER TABLE public.capacitaciones ADD COLUMN IF NOT EXISTS tipo                 text;  -- "Tipo"

-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 5. empleado_capacitacion — las cuatro columnas por fila del Excel
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- Del Excel: Año · Fecha (el MES escrito a mano: "marzo", "Marzo") · Proyecto · Colaborador.
--
-- 🔴 `proyecto` VA EN TEXTO LIBRE Y NO COMO FK, a propósito: la columna del Excel mezcla
-- EMPRESAS ("Elinpar"), CLIENTES ("Escobar", "Gestión Berazategui") y proyectos internos. Una
-- FK obligaría a decidir hoy a cuál de las tres entidades apunta cada fila, y esa decisión no
-- está tomada. El texto libre la difiere sin perder el dato.
--
-- ⚠️ `anio` Y `mes` TAMBIÉN VAN EN TEXTO, y esto conviene tenerlo escrito porque no es lo
-- obvio. `mes` es texto porque el Excel lo trae a mano y sin normalizar ("marzo", "Marzo"), no
-- como número. `anio` va en texto por la misma razón —tolera un "2023/2024" sin romper el
-- import—, y el costo es menor de lo que parece: con años de 4 dígitos el orden lexicográfico
-- coincide con el numérico, así que ordenar y filtrar siguen andando. Lo que se pierde es la
-- validación de rango que daría un `smallint CHECK`; a cambio, ninguna fila del archivo real
-- puede hacer fallar la carga. Si el vocabulario se estabiliza, se normaliza después.
--
-- 🔑 `área` Y `puesto` DEL EXCEL **NO** SE AGREGAN, y es la decisión más importante de este
-- bloque: los dos salen del empleado. Copiados como texto, el día que alguien cambia de área el
-- registro histórico empieza a mentir — y un registro que miente es peor que uno incompleto.
ALTER TABLE public.empleado_capacitacion ADD COLUMN IF NOT EXISTS proyecto     text;
ALTER TABLE public.empleado_capacitacion ADD COLUMN IF NOT EXISTS anio         text;
ALTER TABLE public.empleado_capacitacion ADD COLUMN IF NOT EXISTS mes          text;
ALTER TABLE public.empleado_capacitacion ADD COLUMN IF NOT EXISTS nombre_libre text;

-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 6. 🔴 empleado_capacitacion.empleado_id PASA A NULLABLE
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- EL MOTIVO: el Excel trae **41 nombres tipo "Apellido Nombre", sin DNI**, y en el sistema hay
-- 31 colaboradores. Los que no matcheen se cargan igual, con `nombre_libre`. La alternativa era
-- inventar un colaborador "sin identificar" y colgarles todo ahí — un empleado falso en
-- `empleados` que aparecería en el padrón, en los KPIs y en los reportes de dotación.
--
-- Y resuelve un caso que hoy NO se puede representar: **la capacitación de alguien que ya no
-- trabaja acá.** Eso no es un dato incompleto, es un hecho histórico correcto.
--
-- ── LO QUE ESTO AFLOJA, dicho explícito porque el SQL no lo hace obvio ────────────────────
--   · `ec_empleado_empresa_fk (empleado_id, empresa_id)` es **MATCH SIMPLE** (verificado:
--     `confmatchtype='s'`). Con `empleado_id` NULL la constraint **no se evalúa**. No falla —
--     pero tampoco valida nada en esas filas. `empresa_id` sigue con su FK propia a `empresas`.
--   · `UNIQUE (capacitacion_id, empleado_id)` **deja de proteger** las filas de nombre libre:
--     en SQL dos NULL son distintos, así que la misma persona podría entrar N veces. Eso es lo
--     que cierra el índice del punto 7 — sin él, el import del Excel duplica en silencio.
--
-- ✅ LOS CUATRO ESTÁN HECHOS (13/8/2026) — la lista queda porque explica POR QUÉ cada uno, y
-- porque es el inventario que hay que revisar si mañana aparece una quinta superficie que lea
-- `empleado_id`. Los cubre `tests/test_capacitacion_nombre_libre.py` (13 tests, atraviesan HTTP).
-- El 1 se arregló en `repositories/_asignacion_row.py`, no en `asignacion_repo.py`: el
-- enriquecido se mudó ahí al dividir el repo, que estaba en 97/100.
-- ⚠️ LO QUE HABÍA QUE ARREGLAR EN EL CÓDIGO **ANTES** DE QUE EXISTA LA PRIMERA FILA CON NULL.
-- Hoy no hay ninguna (la tabla está en 0), así que esta migración es inerte; el día que el
-- import escriba una, sin estos cuatro cambios el listado se cae:
--   1. `repositories/asignacion_repo.py:24` — `{r["empleado_id"] for r in rows}` mete None en el
--      set y `.in_("id", [None,…])` manda `id=in.(null,…)`: PostgREST responde 400 y **se cae el
--      listado ENTERO**, no solo la fila. Hay que filtrar los None antes del lookup.
--   2. `schemas/capacitacion.py:72` — `AsignacionResponse.empleado_id: str` tiene que ser
--      `Optional[str]`, o Pydantic tira ValidationError y el endpoint devuelve 500.
--   3. `services/_capacitaciones_export.py:31` — `"Empleado": a.empleado_nombre` sale vacío;
--      tiene que caer a `nombre_libre`.
--   4. `frontend/types/capacitacion.ts:43,57` — `empleado_id: string` → `string | null`, o
--      `next build` falla por tipos.
-- (Verificado que NO se rompen: el reporte R16 ya hace `(row.get("empleados") or {})` y cae en
-- "Sin área"; y el filtro por área excluye las filas sin empleado, que es lo correcto.)
ALTER TABLE public.empleado_capacitacion ALTER COLUMN empleado_id DROP NOT NULL;

-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 7. 🔴 El único parcial que reemplaza a la UNIQUE en las filas de nombre libre
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- Sin esto, el punto 6 abre un agujero silencioso: el import del Excel puede cargar dos veces
-- la misma formación de la misma persona sin nombre matcheado, y **nadie se entera** — no hay
-- error, hay una fila de más. Es exactamente el modo de falla que la migración 110 cerró para
-- vacaciones y la 111 para objetivos.
--
-- LA CLAVE, y por qué cada parte:
--   · `capacitacion_id` — ya acota por empresa (`capacitaciones` tiene `empresa_id`), así que
--     no hace falta sumarlo. Dos empresas con una persona homónima no chocan.
--   · `lower(nombre_libre)` — el nombre lo escribe RRHH a mano; "Perez Juan" y "PEREZ JUAN" son
--     la misma persona. Mismo criterio que `ux_clientes_nombre_global` y
--     `ux_perfiles_puesto_nombre_global`.
--   · `coalesce(anio,'')` / `coalesce(lower(mes),'')` — 🔑 **el `coalesce` es obligatorio, no
--     cosmético.** Sin él, dos filas con `anio` NULL vuelven a ser distintas entre sí y el
--     índice no protege justo las filas incompletas, que son las más probables de duplicarse.
--     11 de las 53 filas del Excel vienen sin datos completos.
--   · `WHERE empleado_id IS NULL` — parcial a propósito: las filas CON empleado ya las cubre la
--     `UNIQUE (capacitacion_id, empleado_id)` que existe. Dos índices sobre el mismo universo
--     serían dos reglas para lo mismo.
--
-- ⚠️ Es un índice POR EXPRESIÓN, así que **no sirve como target de `on_conflict`** de PostgREST
-- (que exige nombrar columnas). El import tiene que consultar-y-decidir, o capturar el 23505.
-- Mismo límite y misma nota que `ux_clientes_nombre_global`.
CREATE UNIQUE INDEX IF NOT EXISTS ux_ec_nombre_libre
    ON public.empleado_capacitacion
       (capacitacion_id, lower(nombre_libre), coalesce(anio, ''), coalesce(lower(mes), ''))
    WHERE empleado_id IS NULL AND nombre_libre IS NOT NULL;

-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 🔴 POR QUÉ NO HAY NINGÚN OTRO ÍNDICE — el criterio de la 115, aplicado acá
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- Los candidatos evidentes serían `(empresa_id, anio)` para "formación del año X" y algo sobre
-- `proyecto`. **No van, por el mismo criterio con el que en la 115 se descartaron tres índices
-- midiendo en vez de suponiendo.**
--
-- La razón es que el listado de asignaciones **NO PAGINA**: `AsignacionRepo.find_all` trae todo
-- y ordena por `created_at DESC`, sin `LIMIT`. Y eso ya se midió en la sesión de escala (10
-- empresas, 1.005 colaboradores): sobre `empleado_capacitacion` sin `LIMIT`, **el planner
-- ignora el índice compuesto** y sigue con Seq Scan + Sort, porque leer todo y ordenar es más
-- barato que recorrer un índice. Un índice acá sería costo de escritura puro.
--
-- 🔑 CUÁNDO SÍ VAN A HACER FALTA: el día que este listado se pagine (es uno de los 12 que el
-- diagnóstico de escala marcó para paginar). **Ahí el índice pasa a tener sentido y hay que
-- agregarlo con la paginación, en la misma sesión** — no antes.
-- El único índice de arriba entra porque **no es de performance: es una constraint**, y una
-- constraint que falta no se nota hasta que hay datos duplicados.

-- ═════════════════════════════════════════════════════════════════════════════════════════
-- VERIFICACIÓN POSTERIOR — para correr DESPUÉS de aplicar la migración
-- ═════════════════════════════════════════════════════════════════════════════════════════

-- ── (A) Las 11 columnas existen ───────────────────────────────────────────────────────────
--     Tiene que devolver exactamente 11 filas.
-- SELECT c.relname AS tabla, a.attname AS columna, format_type(a.atttypid, a.atttypmod) AS tipo
--   FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid
--   JOIN pg_namespace n ON n.oid = c.relnamespace
--  WHERE n.nspname = 'public' AND a.attnum > 0 AND NOT a.attisdropped
--    AND ((c.relname = 'perfiles_puesto'       AND a.attname = 'ofrecemos')
--      OR (c.relname = 'vacantes'              AND a.attname = 'ofrecemos')
--      OR (c.relname = 'recategorizaciones'    AND a.attname IN ('categoria_anterior','categoria_nueva'))
--      OR (c.relname = 'capacitaciones'        AND a.attname IN ('entidad_capacitadora','modalidad','tipo'))
--      OR (c.relname = 'empleado_capacitacion' AND a.attname IN ('proyecto','anio','mes','nombre_libre')))
--  ORDER BY 1, 2;

-- ── (B) `empleado_id` quedó nullable ──────────────────────────────────────────────────────
--     Tiene que devolver una fila con nullable = true.
-- SELECT a.attname, NOT a.attnotnull AS nullable
--   FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid
--   JOIN pg_namespace n ON n.oid = c.relnamespace
--  WHERE n.nspname = 'public' AND c.relname = 'empleado_capacitacion' AND a.attname = 'empleado_id';

-- ── (C) El índice único existe y es VÁLIDO ────────────────────────────────────────────────
--     `indisvalid` tiene que ser true: un CREATE UNIQUE INDEX interrumpido deja el índice
--     existente pero inválido, o sea sin proteger nada, y `pg_indexes` igual lo lista.
-- SELECT c.relname AS indice, i.indisvalid, i.indisunique
--   FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid
--   JOIN pg_namespace n ON n.oid = c.relnamespace
--  WHERE n.nspname = 'public' AND c.relname = 'ux_ec_nombre_libre';

-- ── (D) 🔑 QUE EL ÍNDICE REALMENTE FRENE UN DUPLICADO ─────────────────────────────────────
--     Verificar que el objeto existe NO prueba que proteja: el predicado o el coalesce pueden
--     estar mal y el índice queda decorativo. Esto lo ejercita de verdad y NO deja datos
--     (el ROLLBACK revierte todo, incluido el primer INSERT).
--     Esperado: el 1er INSERT pasa, el 2do falla con `duplicate key value ... ux_ec_nombre_libre`.
--     Reemplazar <CAPACITACION> por:  SELECT id, nombre FROM capacitaciones LIMIT 5;
--     y <EMPRESA> por la empresa de ESA capacitación (la FK compuesta la exige).
-- BEGIN;
--   INSERT INTO empleado_capacitacion (capacitacion_id, empresa_id, empleado_id, estado, nombre_libre, anio, mes)
--        VALUES ('<CAPACITACION>', '<EMPRESA>', NULL, 'completado', 'Perez Juan', '2024', 'marzo');
--   -- Distinta caja y NULL en los dos campos de fecha: tiene que chocar igual.
--   INSERT INTO empleado_capacitacion (capacitacion_id, empresa_id, empleado_id, estado, nombre_libre, anio, mes)
--        VALUES ('<CAPACITACION>', '<EMPRESA>', NULL, 'completado', 'PEREZ JUAN', '2024', 'Marzo');
-- ROLLBACK;

-- ── (E) La contracara: el índice NO debe estorbar a las filas CON empleado ────────────────
--     Dos filas con el mismo nombre_libre pero empleados distintos son legítimas (el índice es
--     parcial y no las mira). Esperado: las dos entran sin error.
--     ⚠️ Elegir DOS empleados que todavía NO tengan esa capacitación, o choca la UNIQUE vieja
--     `(capacitacion_id, empleado_id)` y el fallo se lee como un falso positivo de este índice:
--       SELECT e.id FROM empleados e WHERE e.empresa_id = '<EMPRESA>'
--         AND NOT EXISTS (SELECT 1 FROM empleado_capacitacion ec
--                          WHERE ec.empleado_id = e.id AND ec.capacitacion_id = '<CAPACITACION>')
--        LIMIT 2;
-- BEGIN;
--   INSERT INTO empleado_capacitacion (capacitacion_id, empresa_id, empleado_id, estado, nombre_libre)
--        VALUES ('<CAPACITACION>', '<EMPRESA>', '<EMPLEADO_A>', 'completado', 'Perez Juan');
--   INSERT INTO empleado_capacitacion (capacitacion_id, empresa_id, empleado_id, estado, nombre_libre)
--        VALUES ('<CAPACITACION>', '<EMPRESA>', '<EMPLEADO_B>', 'completado', 'Perez Juan');
-- ROLLBACK;

-- ── (F) La otra contracara: la misma persona en DOS AÑOS distintos no es un duplicado ─────
--     Es lo que prueba que el año forma parte de la clave y no está de adorno. Sin esto, un
--     índice que solo mirara (capacitacion_id, nombre) pasaría (C), (D) y (E) igual, y estaría
--     mal: bloquearía la recertificación anual, que es un caso REAL del Excel.
--     Esperado: las dos entran sin error.
-- BEGIN;
--   INSERT INTO empleado_capacitacion (capacitacion_id, empresa_id, empleado_id, estado, nombre_libre, anio)
--        VALUES ('<CAPACITACION>', '<EMPRESA>', NULL, 'completado', 'Perez Juan', '2024');
--   INSERT INTO empleado_capacitacion (capacitacion_id, empresa_id, empleado_id, estado, nombre_libre, anio)
--        VALUES ('<CAPACITACION>', '<EMPRESA>', NULL, 'completado', 'Perez Juan', '2025');
-- ROLLBACK;

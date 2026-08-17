-- 119_objetivo_tipo_y_areas_array.sql
--
-- 🔴 LA ÚLTIMA DEL LOTE ANTES DEL HANDOFF. Después de esta, una columna nueva significa
-- coordinar DDL con el dev de infra en medio de su migración.
--
-- QUÉ HACE: tres objetos, todos sobre `objetivos`.
--   1. `tipo` — columna nueva con CHECK cerrado (`anual` | `operativo`).
--   2. `ux_objetivo_responsable_titulo` — DROP + CREATE con `tipo` como QUINTA columna.
--   3. `areas_involucradas` — `text` → `text[]`, NOT NULL DEFAULT '{}'.
--
-- ⚠️ CONTIENE DOS OBJETOS QUE NO SON ADITIVOS: el `DROP INDEX` (2) y el `ALTER COLUMN ... TYPE`
-- (3). Ninguno de los dos puede perder una fila —un índice no guarda datos, y el cambio de tipo
-- es inerte con el dato que hay— pero los dos cambian algo que ya estaba, y por eso **todo va en
-- UNA transacción**: entre el DROP y el CREATE del índice la tabla queda sin defensa contra el
-- duplicado. Es el mismo criterio con el que la 114 envolvió su propio DROP + CREATE.
--
-- Va ANTES del deploy del módulo de objetivos (feature 2.4). Es seguro correrla con el código
-- viejo desplegado, y no por casualidad — está verificado abajo, en "POR QUÉ VA ANTES".
-- Idempotente. NO se ejecuta acá (la corre Franco).
--
-- ── VERIFICADO CONTRA EL CATÁLOGO VIVO (grmdiwxcvcjorlohpwji) el 2026-08-17 ────────────────
-- · `objetivos` tiene 13 columnas. **`tipo` NO existe.**
-- · `areas_involucradas` es `text`, NULLABLE, sin default.
-- · `periodicidad` es `text NOT NULL DEFAULT ''::text`, sin CHECK (mig 114).
-- · `ux_objetivo_responsable_titulo` es
--     UNIQUE (empresa_id, responsable_id, lower(titulo), lower(periodicidad))  ← 4 expresiones.
-- · CHECKs propios: `objetivos_estado_check` y `objetivos_prioridad_check`. No hay uno de tipo.
-- · Índices: pkey + idx_obj_empresa + idx_obj_responsable + idx_obj_estado + idx_obj_parent +
--   el único. Trigger: `trg_obj_updated_at`.
-- · **La tabla tiene 1 fila** ("búsqueda líder de equipo", `periodicidad = ''`,
--   `areas_involucradas = NULL`, `parent_id = NULL`).
--
-- 🔑 EL DATO QUE HACE INERTE AL PUNTO 3, medido y no supuesto:
--     SELECT count(*) AS total,
--            count(areas_involucradas) AS con_valor,
--            count(*) FILTER (WHERE areas_involucradas IS NOT NULL
--                               AND btrim(areas_involucradas) <> '') AS con_texto
--       FROM objetivos;
--     -- total 1 · con_valor 0 · con_texto 0
-- O sea: **no hay un solo carácter de texto que convertir.** El `USING` de abajo está escrito
-- igual, completo y fiel al formato que el módulo usa, porque este archivo también es el camino
-- de reconstrucción para una base que SÍ pueda tener datos.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- POR QUÉ VA ANTES DEL DEPLOY, y por qué eso NO contradice a la 114
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- La regla (migración 090, escrita en `schemas/empleado_out.py:43-49`) es que el código que
-- TOLERA un valor nuevo tiene que estar desplegado ANTES de que la base lo produzca. Acá el
-- código viejo lo tolera, y está verificado en los tres puntos de contacto:
--
--   · LECTURA — `repositories/_objetivo_row.py::_build` hace
--     `ObjetivoResponse.model_validate({**r, ...})` sobre la fila cruda de un `select("*")`.
--     `ObjetivoResponse` no declara `tipo` ni `areas_involucradas`, y Pydantic v2 ignora los
--     campos de más por default. Las dos columnas viajan y se descartan. Que
--     `areas_involucradas` pase de ser un string a ser una lista tampoco importa: hoy **no lo
--     lee nadie** (grep en `backend/` y `frontend/`: solo aparece en comentarios, en la 114 y en
--     `schema.sql`).
--   · ESCRITURA — `objetivo_repo.save` arma un `payload` EXPLÍCITO con seis claves y ninguna es
--     `tipo`. Los objetivos que se creen entre esta migración y el deploy nacen con el DEFAULT
--     de la columna, `'anual'`, que es exactamente lo mismo que le va a pasar a la fila que ya
--     existe. No hay estado raro que limpiar después.
--   · SEED — `scripts/seed_escala.py:440-452` inserta `objetivos` con una lista de columnas
--     cerrada que no incluye ninguna de las dos. Sigue funcionando sin tocarlo.
--
-- La 114 iba DESPUÉS por un motivo que acá no aplica: tocaba `parametros_empresa`, cuyo PUT de
-- `/configuracion` manda el juego COMPLETO de parámetros y el front viejo habría mostrado una
-- pantalla sin el parámetro recién creado. `objetivos` no tiene esa forma: su update es un PATCH
-- parcial (`model_dump(exclude_none=True)`), así que una columna que el front viejo no conoce ni
-- se pisa ni se ve.

BEGIN;

-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 1. objetivos.tipo — a cuál de las dos vistas pertenece el objetivo
-- ═════════════════════════════════════════════════════════════════════════════════════════
--
-- Cada objetivo pertenece a UNA de las dos vistas y no se comparte: se carga en anuales y vive
-- ahí, se carga en operativos y vive ahí. La vista ANUAL es la que Capital Humano le presenta al
-- directorio y solo muestra objetivos anuales; la OPERATIVA acepta cualquier expresión de
-- tiempo. Se puede cambiar de tipo desde la pantalla — es una columna editable, no una
-- clasificación de nacimiento.
--
-- 🔴 CHECK CERRADO, AL REVÉS QUE `periodicidad`. Las dos columnas son texto y las dos salieron
-- de la misma conversación, así que la asimetría hay que dejarla escrita o alguien la "corrige":
--   · `periodicidad` NO lleva CHECK porque su vocabulario no se puede cerrar — "primer
--     trimestre", "tercera semana de septiembre", una fecha suelta (el porqué completo está en
--     la 114). Un CHECK ahí rechazaría la mitad de lo que se quiere cargar.
--   · `tipo` SÍ lo lleva porque su vocabulario **es** la lista de vistas de la pantalla. Un
--     tercer valor no es un dato que RRHH escriba: es una pantalla que hay que construir. Si el
--     valor puede aparecer sin que nadie programe nada, el CHECK sobra; si no puede, el CHECK es
--     justamente lo que impide que aparezca por un typo del import.
--
-- 🔴 EL DEFAULT DE LA COLUMNA ES 'anual' Y EL DEL IMPORT Y EL ALTA VA A SER 'operativo'.
-- NO SON EL MISMO DEFAULT Y NO SE CONTRADICEN. Son dos preguntas distintas:
--   · El de la BASE contesta "¿qué pasa con las filas que YA existen cuando aparece la columna?".
--     Hay una sola y tiene que quedar como ANUAL, que es lo decidido. Con `DEFAULT 'anual'` el
--     backfill sale gratis: no hace falta un UPDATE, la fila lo toma sola.
--   · El de PRODUCTO contesta "¿en qué vista nace lo que se carga de ahora en adelante?". Ahí la
--     respuesta es OPERATIVO, porque es la vista permisiva: mandar un objetivo cualquiera a la
--     vista que se le muestra al directorio es peor error que al revés.
-- El default de producto vive en el código (`ObjetivoCreate.tipo` y el transform del import), NO
-- acá. Escribir 'operativo' en la base para "que sean iguales" rompería el backfill de la fila
-- que existe, que es lo único que este DEFAULT tiene que resolver.
--
-- ⚠️ Y por eso el default de la columna es un valor de arranque, no una política: apenas el
-- código mande `tipo` explícito en todo INSERT —que es lo que va a hacer—, el DEFAULT deja de
-- usarse. Queda igual porque una columna NOT NULL sin default rompe cualquier INSERT que la
-- omita, incluidos los de `seed_escala.py`.
ALTER TABLE public.objetivos
    ADD COLUMN IF NOT EXISTS tipo text NOT NULL DEFAULT 'anual';

-- El CHECK va aparte del ADD COLUMN, no inline: con `ADD COLUMN IF NOT EXISTS` la segunda
-- corrida saltea la columna Y su CHECK inline, así que un CHECK que hubiera que corregir después
-- quedaría sin aplicar en silencio. Separado, el par DROP IF EXISTS + ADD siempre converge al
-- estado declarado. Es el patrón que la 114 usó para los dos CHECKs de `parametros_empresa`.
-- El nombre sigue a los dos que la tabla ya tiene (`objetivos_estado_check`,
-- `objetivos_prioridad_check`) y a la forma `= ANY (ARRAY[...])` con la que Postgres los guarda.
ALTER TABLE public.objetivos DROP CONSTRAINT IF EXISTS objetivos_tipo_check;
ALTER TABLE public.objetivos ADD CONSTRAINT objetivos_tipo_check
    CHECK (tipo = ANY (ARRAY['anual'::text, 'operativo'::text]));


-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 2. 🔴 TERCERA RECREACIÓN DE ux_objetivo_responsable_titulo (111 → 114 → esta)
-- ═════════════════════════════════════════════════════════════════════════════════════════
--
-- ANTES: (empresa_id, responsable_id, lower(titulo), lower(periodicidad))
-- AHORA: (empresa_id, responsable_id, lower(titulo), lower(periodicidad), tipo)
--
-- 🔴 EL CASO QUE LO OBLIGA, y es el mismo argumento de la 114 con un eje más:
-- **un anual tiene `periodicidad = ''` SIEMPRE** —un anual ya es del año, el campo no aplica— y
-- **un operativo cuyo autor deja el campo vacío también**, porque es opcional. O sea que para
-- ese par de filas la cuarta columna de la clave es igual, y "Cerrar el trimestre" anual y
-- "Cerrar el trimestre" operativo del MISMO responsable colisionan con 23505. Son dos objetivos
-- legítimos y distintos: viven en dos vistas distintas y no se comparten.
-- Es exactamente la falla que la 114 vino a arreglar (una clave más angosta que la identidad
-- real rechaza datos buenos), reaparecida porque la identidad creció otra vez.
--
-- 🔴 `tipo` VA SIN `lower()`, al revés que `titulo` y `periodicidad`. No es una omisión: esos
-- dos son texto que RRHH escribe A MANO, donde "Anual" y "anual" son lo mismo y sin `lower()` el
-- duplicado entra. `tipo` no lo escribe una persona — sale de un CHECK cerrado que solo admite
-- dos literales en minúscula, y el código los manda tal cual. Un `lower()` ahí no podría cambiar
-- ningún resultado, y sería la tercera expresión de un índice que ya tiene dos: costo real
-- (`lower()` es una expresión que Postgres evalúa en cada escritura) a cambio de nada.
--
-- 🟢 NO PUEDE RECHAZAR NINGUNA FILA EXISTENTE. La clave nueva es la vieja MÁS una columna, o sea
-- estrictamente MÁS ancha: todo lo que entraba sigue entrando. Y con una sola fila en la tabla,
-- no hay ni siquiera un par que pudiera colisionar. No hay que deduplicar nada antes.
--
-- ⚠️ EL NOMBRE SE CONSERVA, y esta vez importa más que las dos anteriores: la 111 y la 114 lo
-- citan literalmente en sus queries de verificación posterior, y las dos siguen en el repo como
-- historial. Renombrarlo dejaría dos migraciones apuntando a un objeto inexistente y a alguien
-- corriendo la verificación de la 114 contra una base sana y viendo "0 filas".
--
-- ⚠️ Sigue siendo un índice por expresión, así que NO sirve como target de `on_conflict` de
-- PostgREST. Es lo mismo que ya decían la 111 y la 114 y sigue sin importar: lo que se busca es
-- que el INSERT REBOTE, no un upsert.
-- 🔴 PERO OJO CON LO QUE ESAS DOS AFIRMAN A CONTINUACIÓN. Las dos dicen "el service traduce el
-- 23505 a su propio error". **ESO NO ES CIERTO Y NO LO FUE NUNCA** (verificado el 17/8: grep de
-- `23505` y de "duplicate key" en `backend/` no devuelve una sola línea de código, solo estas
-- migraciones). Hoy `objetivo_repo.save` no envuelve el insert, así que la `APIError` sube hasta
-- `global_error_handler` y el alta manual devuelve **500 INTERNAL_ERROR**; en el import,
-- `confirmar` la atrapa con su `except Exception` y le muestra a RRHH el texto crudo de Postgres.
-- Esta migración NO lo arregla —es código, no DDL— pero lo deja anotado donde se va a leer.
DROP INDEX IF EXISTS public.ux_objetivo_responsable_titulo;

CREATE UNIQUE INDEX IF NOT EXISTS ux_objetivo_responsable_titulo
    ON public.objetivos USING btree (empresa_id, responsable_id, lower(titulo), lower(periodicidad), tipo);


-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 3. 🔴 objetivos.areas_involucradas — text → text[]
-- ═════════════════════════════════════════════════════════════════════════════════════════
--
-- POR QUÉ. Con texto plano el filtro no puede ser honesto, y falla de las dos maneras a la vez:
--   · El desplegable de "valores ya usados" ofrece la CELDA, no el área: si alguien escribió
--     "Sistemas; Legales", eso aparece como UNA opción. El desplegable termina ofreciendo
--     combinaciones y nunca "Legales" a secas.
--   · El filtro por `ILIKE '%Sistemas%'` matchea "Sistemas Corporativos", que es otra área. No
--     hay forma de distinguir un valor de un prefijo dentro de texto libre.
-- Con array las dos se caen solas: el filtro es `.contains()` (`@>`), que compara ELEMENTOS
-- completos, y el desplegable sale del aplanado de todos los arrays — que es literalmente lo que
-- `EmpleadoRolesRepo.get_roles_conocidos` ya hace sobre `empleados.roles`.
--
-- MOLDE: `empleados.roles` (`text[] NOT NULL`, verificado en el catálogo).
--
-- 🔴 PERO **SIN** SU CHECK, y esa es la única diferencia con el molde. `empleados.roles` lleva
-- `empleados_roles_no_vacio CHECK (array_length(roles, 1) >= 1)` porque un empleado sin ningún
-- rol es un legajo incompleto. Acá es al revés: **un objetivo sin áreas compartidas es el caso
-- NORMAL**, no la excepción — los objetivos son del equipo de Capital Humano y lo que esta
-- columna anota son las áreas de OTRAS empresas con las que el objetivo se comparte, que la
-- mayoría de las veces no son ninguna. Copiar el CHECK obligaría a inventar un área para poder
-- guardar un objetivo, que es la constraint que ensucia el dato para poder cargarlo.
--
-- ── NOT NULL DEFAULT '{}' Y NO NULLABLE — la decisión, y por qué NO es la de `periodicidad` ──
-- `periodicidad` es NOT NULL DEFAULT '' por una razón que acá NO aplica: entra en el índice
-- único, y en Postgres los NULL no colisionan entre sí, así que nullable habría desactivado la
-- deduplicación en silencio. `areas_involucradas` no entra en ningún índice único. El motivo es
-- otro y hay que decirlo entero, porque el mismo DDL con distinta justificación es lo que
-- después se "simplifica":
--
--   🔴 CON NULLABLE, "SIN ÁREAS" TENDRÍA DOS REPRESENTACIONES: `NULL` y `'{}'`. Y las dos se
--   van a producir, sin que nadie lo decida: el formulario manda `[]` cuando el usuario no marca
--   nada, y el import manda la columna ausente cuando el Excel no la trae. A partir de ahí,
--   `areas_involucradas IS NULL` y `areas_involucradas = '{}'` son dos filtros distintos para la
--   MISMA pregunta, y el primer "objetivos sin áreas asignadas" que alguien escriba va a
--   devolver la mitad de las filas — sin error y sin aviso. Es la forma de falla que este repo
--   ya tiene documentada con NULL en la 111 y en la 108/109, con otra cara.
--   Con NOT NULL DEFAULT '{}' hay UN solo vacío, y el filtro es uno solo.
--
--   🟢 Y del lado de Python sale gratis: la fila siempre trae una lista, nunca `None`, así que
--   nadie tiene que acordarse del `or []` antes de iterar. (El `or []` de
--   `get_roles_conocidos` sigue siendo correcto ahí y no se toca — `empleados.roles` es otra
--   columna con otra historia.)
--
--   ⚠️ Lo que NO compra: `.contains()` se comporta igual con NULL que con `'{}'` (los dos dejan
--   la fila afuera del resultado, porque `NULL @> ARRAY['x']` es NULL y NULL no es TRUE). Si el
--   argumento fuera el filtrado, nullable alcanzaba. El argumento es el de arriba y solo ese.
--
-- ── EL `USING`, y por qué está escrito completo si la conversión es inerte ─────────────────
-- Con 1 fila en NULL, cualquier `USING` daría el mismo resultado. Se escribe fiel igual porque
-- este archivo se replaya sobre bases que sí pueden tener texto cargado, y porque el formato que
-- habría tenido ese texto no es una suposición: es el que el propio módulo usa para las listas
-- en una celda — `_objetivos_import_transforms._SEPARADORES = (";", ",")`, los dos, "porque el
-- archivo lo escribe una persona".
--   · `NULL` y el texto en blanco caen los dos a `'{}'`. Es una DECISIÓN semántica dentro del
--     DDL, no una tecnicalidad: dice que "sin áreas" y "áreas desconocidas" son lo mismo. Acá lo
--     son —la columna es una anotación opcional, no un dato que pueda faltar— y es lo que hace
--     que después del ALTER no quede un solo NULL y el `SET NOT NULL` no pueda fallar.
--   · `array_remove(..., '')` saca los elementos vacíos que deja un separador colgado
--     ("Sistemas; Legales;" → 2 elementos, no 3). Se usa `array_remove` y no un `SELECT ... FROM
--     unnest(...) WHERE ...` porque **Postgres no admite subqueries en la expresión de `USING`**
--     ("cannot use subquery in transform expression"): tiene que ser una expresión escalar sobre
--     la fila, y ésta lo es.
--   · El `\s*` de los dos lados del separador absorbe el espacio de "Sistemas; Legales". Con
--     `standard_conforming_strings = on` (lo setea `db/schema.sql` y es el default de Supabase)
--     la barra invertida llega literal al motor de regex; no hace falta duplicarla.
--
-- ⚠️ NO HAY UN `UPDATE ... WHERE areas_involucradas IS NULL` ANTES DEL `SET NOT NULL`, y es a
-- propósito. El `USING` ya mapea NULL a `'{}'`, y como los tres pasos van en la MISMA
-- transacción, el estado intermedio "ya es text[] pero todavía es nullable y tiene NULLs" no se
-- puede alcanzar: o entran los tres o no entra ninguno. Un UPDATE ahí sería código que aparenta
-- cubrir un caso que no existe.
--
-- ── IDEMPOTENCIA: el ÚNICO bloque DO del repo, y por qué hace falta ────────────────────────
-- Postgres no tiene `ALTER COLUMN ... TYPE IF ...`, y re-correr el ALTER con la columna ya en
-- `text[]` NO es un no-op: `btrim(text[])` es un error de tipo duro que aborta la transacción
-- entera. Todas las migraciones de este repo declaran ser re-corribles, así que la guarda va
-- explícita. `information_schema.columns.data_type` devuelve `'text'` para text y `'ARRAY'` para
-- text[], que es exactamente la distinción que hace falta.
DO $$
BEGIN
    IF (SELECT data_type
          FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name   = 'objetivos'
           AND column_name  = 'areas_involucradas') = 'text' THEN
        EXECUTE $conv$
            ALTER TABLE public.objetivos
                ALTER COLUMN areas_involucradas TYPE text[]
                USING (
                    CASE
                        WHEN areas_involucradas IS NULL OR btrim(areas_involucradas) = ''
                            THEN ARRAY[]::text[]
                        ELSE array_remove(
                                 regexp_split_to_array(btrim(areas_involucradas), '\s*[;,]\s*'),
                                 '')
                    END
                )
        $conv$;
    END IF;
END
$$;

-- Los dos de abajo SÍ son no-op si ya están puestos, así que van sueltos y no dentro del DO.
ALTER TABLE public.objetivos ALTER COLUMN areas_involucradas SET DEFAULT ARRAY[]::text[];
ALTER TABLE public.objetivos ALTER COLUMN areas_involucradas SET NOT NULL;

-- ESCALA — SIGUE SIN ÍNDICE, y ahora por un motivo distinto al de la 114. Aquella lo justificó
-- diciendo que el filtro sería `ILIKE '%texto%'` y que un btree no sirve para eso (haría falta
-- trigram, y `pg_trgm` no está instalada). **Ese argumento ya no aplica**: con array el filtro es
-- `@>`, y para eso el índice que sirve es un GIN, que no necesita ninguna extensión.
-- No se crea igual, y el motivo es el OTRO que la 114 daba: `objetivos` es el tablero de tareas
-- de un equipo de RRHH de 3 personas. Hoy tiene 1 fila; aun con 10 empresas son cientos, no
-- cientos de miles, y `idx_obj_empresa` ya acota por el eje que toda consulta usa primero. Un
-- GIN sobre cientos de filas es peso muerto que además encarece cada escritura.
-- 🔑 Si algún día crece de verdad, el índice es exactamente éste —anotado para no re-diagnosticarlo:
--     CREATE INDEX idx_obj_areas ON public.objetivos USING gin (areas_involucradas);
-- (Hoy no hay UN SOLO índice GIN en toda la base — verificado en `pg_indexes` el 17/8. Éste
-- sería el primero, así que quien lo cree tiene que medirlo, no copiarlo de un precedente que no
-- existe.)

COMMIT;


-- ═════════════════════════════════════════════════════════════════════════════════════════
-- VERIFICACIÓN POSTERIOR — correr DESPUÉS, a mano. Nada de esto se ejecuta con la migración.
-- ═════════════════════════════════════════════════════════════════════════════════════════
--
-- 1. Las columnas quedaron como se declararon:
--
--    SELECT column_name, data_type, udt_name, is_nullable, column_default
--      FROM information_schema.columns
--     WHERE table_schema = 'public' AND table_name = 'objetivos'
--       AND column_name IN ('tipo', 'periodicidad', 'areas_involucradas')
--     ORDER BY column_name;
--    -- ESPERADO:
--    --   areas_involucradas  ARRAY  _text  NO   ARRAY[]::text[]
--    --   periodicidad        text   text   NO   ''::text        ← sin cambios, es el control
--    --   tipo                text   text   NO   'anual'::text
--
-- 2. El CHECK de tipo existe y dice las dos cosas:
--
--    SELECT conname, pg_get_constraintdef(oid)
--      FROM pg_constraint WHERE conrelid = 'public.objetivos'::regclass AND contype = 'c'
--     ORDER BY conname;
--    -- ESPERADO: los tres — objetivos_estado_check, objetivos_prioridad_check y
--    --           objetivos_tipo_check CHECK ((tipo = ANY (ARRAY['anual'::text, 'operativo'::text])))
--
-- 3. 🔴 EL BACKFILL: la fila que ya existía quedó ANUAL y con el array vacío, no NULL.
--
--    SELECT id, titulo, tipo, periodicidad, areas_involucradas,
--           areas_involucradas IS NULL AS es_null,
--           cardinality(areas_involucradas) AS n
--      FROM objetivos ORDER BY created_at;
--    -- ESPERADO (medido el 2026-08-17): 1 fila, "búsqueda líder de equipo",
--    --   tipo 'anual' · periodicidad '' · areas_involucradas {} · es_null f · n 0
--    -- 🔑 Mirar `es_null`, no solo el valor: en psql un array vacío se imprime `{}` y un NULL se
--    --    imprime vacío, y a simple vista se confunden. Toda la decisión del punto 3 de la
--    --    migración se juega en esa columna.
--
--    SELECT count(*) FROM objetivos WHERE areas_involucradas IS NULL;
--    -- ESPERADO: 0. Si da >0, el SET NOT NULL no corrió y la migración no está completa.
--
-- 4. El índice quedó con las CINCO expresiones y con el nombre de siempre:
--
--    SELECT indexname, indexdef FROM pg_indexes
--     WHERE schemaname = 'public' AND tablename = 'objetivos' ORDER BY indexname;
--    -- ESPERADO: ux_objetivo_responsable_titulo UNIQUE ...
--    --   (empresa_id, responsable_id, lower(titulo), lower(periodicidad), tipo)
--    -- Y los otros cinco intactos: objetivos_pkey, idx_obj_empresa, idx_obj_estado,
--    --   idx_obj_parent, idx_obj_responsable.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 5. 🔴 LA PRUEBA QUE IMPORTA DEL ÍNDICE — LAS DOS MITADES EN EL MISMO BEGIN/ROLLBACK.
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- Sin la segunda mitad esto no prueba nada: un índice DEMASIADO ANCHO (por ejemplo, uno que por
-- error incluyera `id`) pasaría la primera con las manos en los bolsillos y habría dejado de
-- deduplicar por completo. Una clave única se verifica por lo que RECHAZA, no por lo que acepta.
--
-- ⚠️ EL ORDEN NO ES NEGOCIABLE: los dos INSERT que tienen que ENTRAR van primero y el que tiene
-- que FALLAR va último. Cuando un statement falla, Postgres aborta la transacción y todo lo que
-- venga después responde 25P02 ("current transaction is aborted") en vez de ejecutarse — así que
-- con el orden invertido las dos primeras aserciones quedarían sin correr y el bloque parecería
-- pasar. Después del error, ROLLBACK es lo único válido, y es lo que hay que tipear.
--
-- Usa la fila que ya existe para sacar `empresa_id` y `responsable_id` (las dos con FK), así no
-- hay que inventar ids. HACE ROLLBACK — no dejarlo corrido.
--
--    BEGIN;
--
--    -- (a) MITAD UNO — el caso que esta migración vino a habilitar: mismo título, mismo
--    --     responsable, misma periodicidad ('' en los dos, que es el escenario real), y lo
--    --     ÚNICO que los distingue es el tipo. Los dos tienen que entrar.
--    INSERT INTO objetivos (empresa_id, responsable_id, titulo, periodicidad, tipo)
--    SELECT empresa_id, responsable_id, 'Cerrar el trimestre', '', 'anual'   FROM objetivos LIMIT 1;
--    -- ESPERADO: INSERT 0 1
--
--    INSERT INTO objetivos (empresa_id, responsable_id, titulo, periodicidad, tipo)
--    SELECT empresa_id, responsable_id, 'Cerrar el trimestre', '', 'operativo' FROM objetivos
--     WHERE titulo <> 'Cerrar el trimestre' LIMIT 1;
--    -- ESPERADO: INSERT 0 1
--    -- (el WHERE es para no leer la fila que se acaba de insertar y terminar copiándose a sí
--    --  misma el tipo; con LIMIT 1 sin orden, Postgres no garantiza cuál devuelve)
--
--    -- (b) MITAD DOS — la que prueba que el índice SIGUE deduplicando. Dos anuales con el mismo
--    --     título y el mismo responsable son el MISMO objetivo cargado dos veces, y tienen que
--    --     rebotar. El `upper()` prueba de una sola vez la unicidad Y que el lower(titulo) siga
--    --     puesto: si entra, o al índice le falta el lower() o la clave quedó demasiado ancha.
--    INSERT INTO objetivos (empresa_id, responsable_id, titulo, periodicidad, tipo)
--    SELECT empresa_id, responsable_id, upper('Cerrar el trimestre'), '', 'anual' FROM objetivos
--     WHERE titulo <> 'Cerrar el trimestre' LIMIT 1;
--    -- ESPERADO: falla con
--    --   ERROR 23505 duplicate key value violates unique constraint
--    --               "ux_objetivo_responsable_titulo"
--
--    ROLLBACK;
--
-- 6. El contraste de la 114, que NO se pierde con la columna nueva: la misma periodicidad
--    distinta sigue siendo dos objetivos distintos. También hace ROLLBACK.
--
--    BEGIN;
--    INSERT INTO objetivos (empresa_id, responsable_id, titulo, periodicidad, tipo)
--    SELECT empresa_id, responsable_id, 'Revisar headcount', 'mensual',   'operativo' FROM objetivos LIMIT 1;
--    INSERT INTO objetivos (empresa_id, responsable_id, titulo, periodicidad, tipo)
--    SELECT empresa_id, responsable_id, 'Revisar headcount', 'trimestral','operativo' FROM objetivos
--     WHERE titulo <> 'Revisar headcount' LIMIT 1;
--    -- ESPERADO: los DOS entran.
--    ROLLBACK;
--
-- 7. El CHECK de tipo rechaza un tercer valor:
--
--    BEGIN;
--    INSERT INTO objetivos (empresa_id, responsable_id, titulo, tipo)
--    SELECT empresa_id, responsable_id, 'Objetivo con tipo raro', 'semestral' FROM objetivos LIMIT 1;
--    -- ESPERADO: ERROR 23514 new row ... violates check constraint "objetivos_tipo_check"
--    ROLLBACK;
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 8. 🔴 EL ARRAY: que `@>` encuentre el área EXACTA y NO matchee un prefijo.
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- Es la razón entera del punto 3. La aserción que importa es la NEGATIVA: con la columna en
-- texto, `ILIKE '%Sistemas%'` devolvía las dos filas de abajo y el filtro mentía.
-- También hace ROLLBACK.
--
--    BEGIN;
--    INSERT INTO objetivos (empresa_id, responsable_id, titulo, tipo, areas_involucradas)
--    SELECT empresa_id, responsable_id, 'AREATEST prefijo', 'operativo',
--           ARRAY['Sistemas Corporativos'] FROM objetivos LIMIT 1;
--    INSERT INTO objetivos (empresa_id, responsable_id, titulo, tipo, areas_involucradas)
--    SELECT empresa_id, responsable_id, 'AREATEST multiple', 'operativo',
--           ARRAY['Sistemas', 'Legales'] FROM objetivos WHERE titulo NOT LIKE 'AREATEST%' LIMIT 1;
--
--    SELECT titulo FROM objetivos WHERE areas_involucradas @> ARRAY['Sistemas'];
--    -- ESPERADO: SOLO 'AREATEST multiple'. 🔴 Si aparece también 'AREATEST prefijo', el filtro
--    --           está matcheando un prefijo y todo el punto 3 fue al pedo.
--
--    SELECT titulo FROM objetivos WHERE areas_involucradas @> ARRAY['Sistemas Corporativos'];
--    -- ESPERADO: SOLO 'AREATEST prefijo'. El valor exacto sí se encuentra.
--
--    SELECT titulo FROM objetivos WHERE areas_involucradas @> ARRAY['Legales'];
--    -- ESPERADO: SOLO 'AREATEST multiple'. Un elemento que NO es el primero del array también
--    --           se encuentra — `@>` es contención, no comparación posicional.
--
--    SELECT titulo FROM objetivos WHERE areas_involucradas @> ARRAY['Sistemas','Legales'];
--    -- ESPERADO: SOLO 'AREATEST multiple'. Con dos elementos, `@>` pide LOS DOS (es AND, no OR).
--    --           Conviene saberlo antes de cablear un multiselect en la pantalla.
--
--    -- El contraste con lo que había antes, para que quede medido y no argumentado:
--    SELECT titulo FROM objetivos
--     WHERE array_to_string(areas_involucradas, '; ') ILIKE '%Sistemas%';
--    -- ESPERADO: LAS DOS. Esto es lo que devolvía el filtro con la columna en texto.
--
--    ROLLBACK;
--
-- 9. El aplanado que va a alimentar el desplegable de valores usados (mismo patrón que
--    `EmpleadoRolesRepo.get_roles_conocidos` sobre `empleados.roles`):
--
--    SELECT DISTINCT unnest(areas_involucradas) AS area FROM objetivos ORDER BY area;
--    -- ESPERADO hoy: 0 filas (la única fila tiene el array vacío, y `unnest('{}')` no emite
--    --           nada). Lo que importa es que NO tire error y que no aparezca un NULL: eso
--    --           confirma que el SET NOT NULL hizo su trabajo.
--
-- 10. En PostgREST / supabase-py el filtro de (8) se escribe:
--        .contains("areas_involucradas", ["Sistemas"])     →  ?areas_involucradas=cs.{Sistemas}
--     🔴 ANOTADO ACÁ PORQUE NO HAY UN SOLO PRECEDENTE EN EL REPO (verificado el 17/8: cero
--     `.contains(` en `repositories/` y `services/`, y el fake de Supabase de la suite tampoco lo
--     implementa). O sea que el primer test que lo use tiene que agregarlo al fake, o va a pasar
--     en verde sin haber filtrado nada — que es el caso #1 de "un test solo prueba lo que el fake
--     puede desmentir".
--     ⚠️ Y un valor con coma adentro ("Legales, Compliance") rompe la sintaxis `cs.{...}` de
--     PostgREST salvo que se lo comille. Es la razón práctica por la que las áreas se cargan como
--     elementos separados y no como una frase.

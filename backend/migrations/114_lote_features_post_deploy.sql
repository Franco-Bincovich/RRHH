-- 114_lote_features_post_deploy.sql
--
-- QUÉ HACE: la mitad del lote que DEPENDE DEL CÓDIGO NUEVO. Dos parámetros de configuración,
-- dos columnas en `objetivos`, y el reemplazo del índice único de `objetivos`.
--
-- 🔴 VA DESPUÉS DEL DEPLOY. La aditiva pura es la 113 y esa va antes.
--
-- ⚠️ CONTIENE **EL ÚNICO OBJETO DESTRUCTIVO DE TODO EL LOTE**: el `DROP INDEX` de
-- `ux_objetivo_responsable_titulo`, que se recrea acá mismo con una columna más. No se pierde
-- ninguna fila —un índice no guarda datos— pero entre el DROP y el CREATE la tabla queda sin
-- protección de duplicados, y por eso los dos van en la MISMA transacción. Con 1 objetivo en
-- producción la ventana es irrelevante; se escribe igual porque el día que haya 5.000 no lo es.
--
-- Idempotente: ADD COLUMN IF NOT EXISTS + DROP INDEX IF EXISTS + CREATE INDEX IF NOT EXISTS.
-- NO se ejecuta acá (la corre Franco).
-- Verificado contra el catálogo vivo (grmdiwxcvcjorlohpwji) el 2026-08-13.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- POR QUÉ ESTE ARCHIVO VA DESPUÉS Y LA 113 ANTES
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- La regla es la que dejó escrita la migración 090 en `schemas/empleado_out.py:43-49`: el código
-- que TOLERA un valor nuevo tiene que estar desplegado ANTES de que la base lo produzca.
--
--   · `parametros_empresa` — el PUT de `/configuracion` manda el JUEGO COMPLETO de parámetros
--     (anotado en la migración 100). Correr esto antes del deploy dejaría al front viejo
--     guardando sin los dos campos nuevos: no los pisa —PostgREST solo escribe las columnas que
--     recibe— pero tampoco los puede mostrar ni editar, y RRHH vería la pantalla de configuración
--     sin el parámetro que acaba de existir. Es confuso sin ser un bug, y se evita gratis.
--   · `objetivos.periodicidad` — el índice nuevo la referencia, así que el orden interno es
--     COLUMNA → ÍNDICE, obligatoriamente. Y hasta que el código escriba la periodicidad, el
--     índice nuevo se comporta EXACTAMENTE como el viejo (ver la nota del índice).

BEGIN;

-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 1. parametros_empresa — período de prueba y días de aviso de los eventos
-- ═════════════════════════════════════════════════════════════════════════════════════════
--
-- 🔴 DOS COLUMNAS SOBRE LA TABLA QUE YA EXISTE, **NO** UNA TABLA NUEVA NI UNA COLUMNA EN
-- `empresas`. El patrón "fila global + fila por empresa que la pisa" ya está construido acá y
-- verificado en el catálogo:
--   · `parametros_empresa.empresa_id` es NULLABLE;
--   · `ux_parametros_empresa_global` — UNIQUE parcial WHERE empresa_id IS NULL: una sola fila
--     global, imposible tener dos;
--   · `ux_parametros_empresa_por_empresa` — UNIQUE parcial WHERE empresa_id IS NOT NULL: una
--     sola fila por empresa;
--   · en producción hay exactamente UNA fila, la global (empresa_id = NULL, base_dias_habiles 22).
-- O sea que agregar una columna acá HEREDA el override por empresa sin escribir una línea de
-- infraestructura. Es el mismo mecanismo que ya usan `reglas_vacaciones_escala` y
-- `tipos_ausencia`.
--
-- ⚠️ EFECTO DEL `NOT NULL DEFAULT` SOBRE LAS FILAS EXISTENTES: la fila global queda con 90 y 7.
-- Es el valor que se quería, así que el backfill es el default y no hace falta un UPDATE. Si
-- mañana existieran filas por empresa, también nacerían con el default y seguirían pisando a la
-- global solo cuando alguien las edite — que es la semántica correcta.

-- Días del período de prueba. Alimenta el evento "fin de período de prueba" del dashboard, que
-- se calcula como `fecha_ingreso + periodo_prueba_dias`. 90 días es el valor de la LCT argentina
-- para el contrato por tiempo indeterminado; se deja configurable porque la ley cambia y porque
-- el grupo puede tener convenios distintos.
-- ⚠️ NO se modela por tipo de contrato. Si RRHH confirma que una pasantía tiene otro período,
-- eso es otra decisión y otra columna — hoy no hay dato que lo respalde.
ALTER TABLE public.parametros_empresa
    ADD COLUMN IF NOT EXISTS periodo_prueba_dias smallint NOT NULL DEFAULT 90;

-- Días de anticipación con los que el dashboard avisa un evento de la agenda. Es el DEFAULT de
-- la empresa; cada evento puede pisarlo con `eventos_agenda.dias_aviso` (migración 113). Mismo
-- patrón de "regla general + override por fila" que `empleados.dias_vacaciones_asignados` contra
-- la escala por antigüedad.
ALTER TABLE public.parametros_empresa
    ADD COLUMN IF NOT EXISTS dias_aviso_evento smallint NOT NULL DEFAULT 7;

ALTER TABLE public.parametros_empresa DROP CONSTRAINT IF EXISTS parametros_empresa_periodo_prueba_check;
ALTER TABLE public.parametros_empresa ADD CONSTRAINT parametros_empresa_periodo_prueba_check
    CHECK (periodo_prueba_dias > 0 AND periodo_prueba_dias <= 730);

ALTER TABLE public.parametros_empresa DROP CONSTRAINT IF EXISTS parametros_empresa_dias_aviso_check;
ALTER TABLE public.parametros_empresa ADD CONSTRAINT parametros_empresa_dias_aviso_check
    CHECK (dias_aviso_evento >= 0 AND dias_aviso_evento <= 365);

-- SIN índices nuevos, y es deliberado: esta tabla tiene UNA fila global más, como mucho, una por
-- empresa. Con 10 empresas son 11 filas. Los dos índices únicos parciales que ya existen son
-- todo lo que necesita; cualquier otro sería peso muerto.


-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 2. objetivos — periodicidad y áreas involucradas
-- ═════════════════════════════════════════════════════════════════════════════════════════
--
-- 🔴 `periodicidad` ES TEXTO LIBRE, NO UN CHECK CERRADO. Decisión de producto, y el motivo es
-- que el vocabulario no se puede cerrar: la vista anual mira los objetivos anuales, pero la otra
-- vista acepta cualquier expresión que RRHH escriba — "primer trimestre", "tercera semana de
-- septiembre", una fecha suelta. Un CHECK con cinco valores rechazaría la mitad de lo que se
-- quiere cargar, y agrandarlo después del congelamiento es coordinar con infraestructura.
-- Es la misma forma que ya tienen `seniority`, `categoria` y `perfil` en `empleados`: texto libre
-- alimentado por el autocompletado de valores ya usados.
--
-- 🔴 `NOT NULL DEFAULT ''` Y NO NULLABLE, Y ESTO ES LO QUE SOSTIENE EL ÍNDICE DE ABAJO.
-- La migración 111 dejó documentada la trampa exacta al explicar por qué `fecha_entrega` NO
-- entra en la clave única: **en Postgres los NULL no colisionan entre sí**, así que una columna
-- nullable dentro de un índice único hace que el índice DEJE DE DEDUPLICAR EN SILENCIO para toda
-- fila que la tenga vacía — que hoy serían todas. Con NOT NULL DEFAULT '' no hay agujero: el
-- vacío es un valor más y colisiona como cualquier otro.
-- El default es '' y no 'unica' a propósito: con vocabulario abierto, "sin especificar" es
-- literalmente la ausencia de texto, no una categoría inventada que después aparece en el
-- desplegable de valores usados.
ALTER TABLE public.objetivos
    ADD COLUMN IF NOT EXISTS periodicidad text NOT NULL DEFAULT '';

-- Texto libre y filtrable. Un objetivo puede involucrar a varias áreas, y NO es `area_id`: el
-- bloque B de objetivos se canceló a propósito porque `responsable_id` apunta a `users` (el
-- equipo de RRHH), que no tiene área. Esto es una anotación de contexto, no una FK.
ALTER TABLE public.objetivos
    ADD COLUMN IF NOT EXISTS areas_involucradas text;

-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 EL ÚNICO OBJETO DESTRUCTIVO DEL LOTE: reemplazo del índice único
-- ─────────────────────────────────────────────────────────────────────────────────────────
--
-- ANTES: (empresa_id, responsable_id, lower(titulo))
-- AHORA: (empresa_id, responsable_id, lower(titulo), lower(periodicidad))
--
-- POR QUÉ CAMBIA. La migración 111 eligió esa clave porque es lo que identifica una FILA DE LA
-- PLANILLA de import: título + responsable, las dos columnas que el import declara requeridas.
-- Con periodicidad, esa clave pasa a ser DEMASIADO ANGOSTA: "Cerrar el trimestre" mensual y
-- "Cerrar el trimestre" anual del mismo responsable son dos objetivos legítimos y distintos, y
-- con la clave vieja el segundo rebota con 23505 — obligando a RRHH a ensuciar el título para
-- poder cargarlo. Una clave más angosta que la identidad real rechaza datos buenos.
--
-- POR QUÉ `lower(periodicidad)` Y NO `periodicidad` A SECAS. Es texto libre escrito a mano:
-- "Anual" y "anual" son la misma periodicidad. Sin `lower()` el índice las trata como distintas
-- y el duplicado entra. Es el MISMO criterio y el mismo motivo que el `lower(titulo)` que ya
-- estaba, y que `ux_clientes_nombre_global` y `ux_perfiles_puesto_nombre_global`.
-- ⚠️ `lower()` no hace `trim()`: " anual" y "anual" siguen siendo distintas para el índice. Eso
-- lo tiene que normalizar el service al escribir, igual que ya hace `data.titulo.strip()`.
--
-- 🟢 NO PUEDE RECHAZAR NINGUNA FILA EXISTENTE. La clave nueva es la vieja MÁS una columna, o sea
-- estrictamente MÁS ancha: todo lo que entraba sigue entrando. Y como la columna acaba de nacer
-- con '' en todas las filas, hasta que el código escriba periodicidades el índice nuevo se
-- comporta EXACTAMENTE como el viejo. No hay que deduplicar nada antes de correr esto.
--
-- ⚠️ Sigue siendo un índice por expresión, así que NO sirve como target de `on_conflict` de
-- PostgREST. No importa, y es lo mismo que ya decía la 111: lo que se busca es que el INSERT
-- REBOTE, no un upsert — el service traduce el 23505 a su propio error.
DROP INDEX IF EXISTS public.ux_objetivo_responsable_titulo;

CREATE UNIQUE INDEX IF NOT EXISTS ux_objetivo_responsable_titulo
    ON public.objetivos USING btree (empresa_id, responsable_id, lower(titulo), lower(periodicidad));

-- ESCALA — SIN índice para `periodicidad` ni para `areas_involucradas`, y es una decisión, no un
-- olvido:
--   · `objetivos` es el tablero de tareas de un equipo de RRHH de 3 personas, no del padrón. Aun
--     con 10 empresas son cientos de filas, no cientos de miles, y `idx_obj_empresa` ya acota
--     por el eje que toda consulta usa primero.
--   · `areas_involucradas` se filtra por coincidencia parcial (`ILIKE %texto%`), y un btree NO
--     sirve para eso: haría falta un índice trigram, y `pg_trgm` no está instalada. Crear la
--     extensión para una tabla de cientos de filas es peso sin beneficio.
-- Si algún día `objetivos` crece de verdad, el índice que va a hacer falta es
-- `(empresa_id, lower(periodicidad))` — anotado acá para no tener que re-diagnosticarlo.

COMMIT;


-- ═════════════════════════════════════════════════════════════════════════════════════════
-- VERIFICACIÓN POSTERIOR — correr DESPUÉS, a mano.
-- ═════════════════════════════════════════════════════════════════════════════════════════
--
-- 1. Los dos parámetros nuevos, con su default aplicado a la fila global que ya existía:
--
--    SELECT empresa_id, base_dias_habiles, periodo_prueba_dias, dias_aviso_evento
--      FROM parametros_empresa ORDER BY empresa_id NULLS FIRST;
--    -- ESPERADO: 1 fila, empresa_id NULL, base 22, periodo_prueba_dias 90, dias_aviso_evento 7.
--
-- 2. Las dos columnas de objetivos, y que `periodicidad` haya quedado NOT NULL:
--
--    SELECT column_name, data_type, is_nullable, column_default
--      FROM information_schema.columns
--     WHERE table_schema = 'public' AND table_name = 'objetivos'
--       AND column_name IN ('periodicidad','areas_involucradas') ORDER BY 1;
--    -- ESPERADO: areas_involucradas text YES null
--    --           periodicidad       text NO  ''::text
--
--    SELECT count(*) FROM objetivos WHERE periodicidad IS NULL;
--    -- ESPERADO: 0. Si diera otra cosa, el NOT NULL no se aplicó.
--
-- 3. El índice quedó con las CUATRO expresiones:
--
--    SELECT indexdef FROM pg_indexes
--     WHERE schemaname = 'public' AND indexname = 'ux_objetivo_responsable_titulo';
--    -- ESPERADO: UNIQUE ... (empresa_id, responsable_id, lower(titulo), lower(periodicidad))
--
-- 4. La fila que ya existía sigue ahí (un cambio de índice no puede perder datos, pero confirma
--    que se corrió contra la base correcta):
--
--    SELECT id, titulo, periodicidad FROM objetivos ORDER BY created_at;
--    -- ESPERADO (medido el 2026-08-13): 1 fila, "búsqueda líder de equipo", periodicidad ''.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 5. 🔴 LA PRUEBA QUE IMPORTA — que el índice SIGA deduplicando. Hace ROLLBACK.
-- ─────────────────────────────────────────────────────────────────────────────────────────
--
--    BEGIN;
--    INSERT INTO objetivos (empresa_id, responsable_id, titulo, periodicidad)
--    SELECT empresa_id, responsable_id, upper(titulo), periodicidad FROM objetivos LIMIT 1;
--    -- ESPERADO: falla con
--    --   ERROR 23505 duplicate key value violates unique constraint
--    --               "ux_objetivo_responsable_titulo"
--    -- El `upper()` prueba de una sola vez la unicidad Y que el lower(titulo) siga puesto.
--    ROLLBACK;
--
-- 6. 🔴 EL CONTRASTE QUE JUSTIFICA EL CAMBIO — mismo título y mismo responsable, OTRA
--    periodicidad, SÍ tiene que entrar. Esta es la prueba de que el índice no quedó demasiado
--    ancho ni demasiado angosto: sin ella, la clave vieja (tres columnas) pasaría la prueba 5
--    y estaría rechazando el caso legítimo que motivó todo el cambio.
--
--    BEGIN;
--    INSERT INTO objetivos (empresa_id, responsable_id, titulo, periodicidad)
--    SELECT empresa_id, responsable_id, titulo, 'anual' FROM objetivos LIMIT 1;
--    -- ESPERADO: entra sin error.
--    ROLLBACK;
--
-- 7. Y el otro contraste, el que prueba que `lower(periodicidad)` está puesto: la MISMA
--    periodicidad con otras mayúsculas NO tiene que entrar.
--
--    BEGIN;
--    INSERT INTO objetivos (empresa_id, responsable_id, titulo, periodicidad)
--    SELECT empresa_id, responsable_id, titulo, 'anual' FROM objetivos LIMIT 1;
--    INSERT INTO objetivos (empresa_id, responsable_id, titulo, periodicidad)
--    SELECT empresa_id, responsable_id, titulo, 'ANUAL' FROM objetivos LIMIT 1;
--    -- ESPERADO: el PRIMERO entra, el SEGUNDO falla con 23505.
--    -- Si los dos entran, al índice le falta el lower() sobre periodicidad.
--    ROLLBACK;
--
-- 8. El contraste del responsable, heredado de la 111 y que sigue teniendo que valer: el MISMO
--    título para OTRO responsable entra.
--
--    BEGIN;
--    INSERT INTO objetivos (empresa_id, responsable_id, titulo)
--    SELECT o.empresa_id, u.id, o.titulo FROM objetivos o, users u
--     WHERE u.id <> o.responsable_id LIMIT 1;
--    -- ESPERADO: entra sin error.
--    ROLLBACK;
--
-- 9. Los dos CHECK nuevos de parametros_empresa:
--
--    BEGIN;
--    UPDATE parametros_empresa SET periodo_prueba_dias = 0;
--    -- ESPERADO: falla con 23514 "parametros_empresa_periodo_prueba_check"
--    ROLLBACK;
--
--    BEGIN;
--    UPDATE parametros_empresa SET dias_aviso_evento = 400;
--    -- ESPERADO: falla con 23514 "parametros_empresa_dias_aviso_check"
--    ROLLBACK;
--
-- 10. Contraste de la 9: valores válidos entran.
--
--    BEGIN;
--    UPDATE parametros_empresa SET periodo_prueba_dias = 180, dias_aviso_evento = 0;
--    -- ESPERADO: sin error.
--    ROLLBACK;

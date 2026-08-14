-- 117_recategorizacion_categoria.sql
--
-- UNA LÍNEA DE DDL: extiende `recategorizaciones_algo_cambia_check` para que
-- `categoria_nueva` también cuente como "algo cambió".
--
-- 🔴 ES LA ÚLTIMA MIGRACIÓN ANTES DEL HANDOFF. La 116 ya decía eso de sí misma y se equivocó
-- por este agujero: agregó `categoria_anterior`/`categoria_nueva` y **no tocó el CHECK que
-- decide si la fila es válida**. Esta es la corrección de ese olvido, no una feature nueva.
--
-- QUÉ HACE: DROP + ADD de UN constraint. Nada más. No agrega columnas, no toca datos, no crea
-- índices.
--
-- ── EL BUG QUE CIERRA ─────────────────────────────────────────────────────────────────────
-- El CHECK vigente en producción (verificado contra el catálogo, ver abajo) es:
--
--     CHECK (rol_nuevo IS NOT NULL OR seniority_nueva IS NOT NULL)
--
-- La 113 lo escribió cuando la tabla tenía DOS pares de campos, y su comentario lo explicaba
-- bien para ese momento: "ni `rol_nuevo` ni `seniority_nueva` pueden ser NOT NULL por separado
-- (…) pero las dos en NULL es una fila vacía que no dice nada". La 116 sumó el tercer par y
-- dejó el predicado con dos.
--
-- Consecuencia concreta: **una recategorización que solo cambia la categoría la rechaza la
-- base con 23514**, y el mensaje que sale es el nombre del constraint — o sea, un error que
-- para quien lo recibe no tiene ninguna relación con lo que hizo.
--
-- 🔑 Y NO ES UN CASO DE BORDE. Capital Humano definió que la categoría es **el nivel dentro
-- del seniority**, así que "de 3 a 4" es una recategorización legítima y probablemente la MÁS
-- FRECUENTE de las tres: el rol y el seniority cambian de vez en cuando, la categoría sube
-- sola. Sin este cambio, el caso más común del módulo es el único que la base no acepta.
--
-- ── POR QUÉ ES INERTE ─────────────────────────────────────────────────────────────────────
-- El constraint se AFLOJA: pasa de aceptar dos formas a aceptar tres. Un predicado más
-- permisivo **no puede invalidar una fila existente**, así que `ADD CONSTRAINT` no puede
-- fallar por datos. Y además `recategorizaciones` tiene **0 filas** (verificado hoy contra el
-- catálogo vivo), o sea que no hay nada que revalidar en absoluto.
-- Idempotente: `DROP ... IF EXISTS` + `ADD`. Se puede correr de nuevo sin efecto.
-- Va ANTES del deploy del módulo y sin ventana. NO se ejecuta acá (la corre Franco).
--
-- ── VERIFICADO CONTRA EL CATÁLOGO VIVO (grmdiwxcvcjorlohpwji) el 2026-08-14 ───────────────
--   · `recategorizaciones_algo_cambia_check` existe y NO menciona `categoria_nueva`.
--   · `recategorizaciones`: **0 filas**.
--   · 🔑 La **116 ESTÁ CORRIDA ENTERA** — y esto se comprobó mirando los objetos que toca, no
--     contando tablas: las 11 columnas existen, `empleado_capacitacion.empleado_id` quedó
--     nullable, y `ux_ec_nombre_libre` existe. (El encabezado de `db/schema.sql` la declaraba
--     PENDIENTE; se corrigió en la misma sesión que esta migración. Es el cuarto desfasaje de
--     ese encabezado y sale de la misma causa de siempre: verificar por conteo en vez de por
--     objeto.)

-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 1. recategorizaciones_algo_cambia_check — sumar `categoria_nueva`
-- ═════════════════════════════════════════════════════════════════════════════════════════
--
-- 🔴 VA EN UNA TRANSACCIÓN, Y NO ES CEREMONIA. Entre el DROP y el ADD la tabla queda **sin
-- ninguna defensa contra la fila vacía**. Hoy eso es inofensivo (0 filas, sin código que
-- escriba todavía), pero el mismo archivo se puede replayear el día que la tabla tenga datos y
-- tráfico, y ahí esa ventana es real. Es el mismo criterio con el que la 114 hizo su DROP +
-- CREATE de `ux_objetivo_responsable_titulo` dentro de una transacción.
--
-- 🔴 POR QUÉ EL PREDICADO SE ESCRIBE CON `IS NOT NULL` Y NO CON UNA COMPARACIÓN.
-- En Postgres un CHECK **rechaza solo cuando evalúa a FALSE**: si evalúa a NULL (UNKNOWN), la
-- fila PASA. Un predicado escrito como `rol_nuevo <> '' OR ...` daría NULL cuando los tres
-- campos son NULL —que es exactamente el caso que hay que prohibir— y el constraint aceptaría
-- la fila vacía sin que nada lo delate. `IS NOT NULL` nunca devuelve UNKNOWN: siempre es TRUE
-- o FALSE. Por eso la verificación (B) de abajo no es opcional.
--
-- ⚠️ SE CONSERVA EL NOMBRE DEL CONSTRAINT. La verificación de la 113 lo nombra, y el service
-- del módulo va a tener que mapear el 23514 a un mensaje legible usando ese nombre. Cambiarlo
-- obligaría a tocar los dos.
--
-- ⚠️ `categoria_ANTERIOR` NO entra en el predicado, igual que sus dos hermanas: los `*_anterior`
-- los completa el sistema leyendo al empleado y pueden ser NULL legítimamente (nadie tenía
-- categoría cargada antes: hoy son 2/31). Lo que define que la fila diga algo es el valor
-- NUEVO, no el viejo.

BEGIN;

ALTER TABLE public.recategorizaciones
    DROP CONSTRAINT IF EXISTS recategorizaciones_algo_cambia_check;

ALTER TABLE public.recategorizaciones
    ADD CONSTRAINT recategorizaciones_algo_cambia_check
    CHECK (rol_nuevo IS NOT NULL
        OR seniority_nueva IS NOT NULL
        OR categoria_nueva IS NOT NULL);

COMMIT;

-- ═════════════════════════════════════════════════════════════════════════════════════════
-- VERIFICACIÓN POSTERIOR — para correr DESPUÉS de aplicar la migración
-- ═════════════════════════════════════════════════════════════════════════════════════════
--
-- 🔑 (A) sola NO alcanza, y (B) sola tampoco. Un CHECK mal escrito —el caso de la comparación
-- con `<>` explicado arriba, o un `OR TRUE` colado— **acepta la fila de solo categoría Y
-- TAMBIÉN la fila vacía**, así que (A) pasaría y el constraint estaría roto. Las dos van
-- juntas o no prueban nada.

-- ── (A) El constraint quedó con los TRES campos ───────────────────────────────────────────
--     Verificación de FORMA. Tiene que devolver una fila cuyo `def` mencione los tres:
--     rol_nuevo, seniority_nueva y categoria_nueva.
-- SELECT con.conname, pg_get_constraintdef(con.oid) AS def
--   FROM pg_constraint con
--   JOIN pg_class c ON c.oid = con.conrelid
--   JOIN pg_namespace n ON n.oid = c.relnamespace
--  WHERE n.nspname = 'public'
--    AND c.relname = 'recategorizaciones'
--    AND con.conname = 'recategorizaciones_algo_cambia_check';

-- ── (B) 🔑 QUE EL CONSTRAINT REALMENTE HAGA LAS DOS COSAS ─────────────────────────────────
--     Verificación de COMPORTAMIENTO, que es la que importa: leer el `def` prueba que el texto
--     cambió, no que el predicado discrimine. Esto lo ejercita de verdad y NO deja datos (el
--     ROLLBACK revierte todo, incluido el INSERT que sí entra).
--
--     Reemplazar <EMPLEADO> y <EMPRESA> por un par REAL y COHERENTE — la FK es COMPUESTA
--     (`recat_empleado_empresa_fk (empleado_id, empresa_id) -> empleados(id, empresa_id)`),
--     así que un empleado con la empresa de otro falla por la FK y el error se lee como un
--     falso positivo de este CHECK:
--       SELECT id AS empleado, empresa_id AS empresa FROM empleados LIMIT 1;
--
-- BEGIN;
--   -- B.1 — SOLO CATEGORÍA: es lo que esta migración viene a habilitar.
--   --       ESPERADO: entra sin error.
--   INSERT INTO recategorizaciones
--          (empresa_id, empleado_id, fecha_efectiva, motivo, categoria_anterior, categoria_nueva)
--   VALUES ('<EMPRESA>', '<EMPLEADO>', current_date, 'paso de categoria 3 a 4', '3', '4');
--
--   -- B.2 — 🔴 LAS TRES EN NULL: la fila vacía tiene que SEGUIR rechazada.
--   --       Es la mitad que un CHECK mal escrito deja pasar, y la única forma de distinguir
--   --       "se agregó categoria_nueva al predicado" de "se rompió el predicado".
--   --       ESPERADO: falla con
--   --         ERROR 23514 new row violates check constraint "recategorizaciones_algo_cambia_check"
--   INSERT INTO recategorizaciones
--          (empresa_id, empleado_id, fecha_efectiva, motivo)
--   VALUES ('<EMPRESA>', '<EMPLEADO>', current_date, 'prueba sin cambios');
-- ROLLBACK;

-- ── (C) La contracara de B.2: los `*_anterior` NO alcanzan para validar una fila ──────────
--     Una fila que solo trae los valores VIEJOS no dice qué cambió: es tan vacía como B.2.
--     Sin este caso, un predicado escrito por error sobre `categoria_ANTERIOR` pasaría (A),
--     pasaría B.1 y pasaría B.2, y estaría mal.
--     ESPERADO: falla con el mismo 23514.
-- BEGIN;
--   INSERT INTO recategorizaciones
--          (empresa_id, empleado_id, fecha_efectiva, motivo,
--           rol_anterior, seniority_anterior, categoria_anterior)
--   VALUES ('<EMPRESA>', '<EMPLEADO>', current_date, 'solo valores viejos',
--           'ANALISTA', 'SENIOR', '3');
-- ROLLBACK;

-- ── (D) Que las dos formas que YA funcionaban sigan funcionando ───────────────────────────
--     Una migración que afloja un constraint no debería poder romper lo que antes entraba,
--     pero el DROP + ADD reescribe el predicado entero: si alguien lo tipea de nuevo y se come
--     un OR, esto lo caza.
--     ESPERADO: las dos entran sin error.
-- BEGIN;
--   INSERT INTO recategorizaciones (empresa_id, empleado_id, fecha_efectiva, motivo, rol_nuevo)
--   VALUES ('<EMPRESA>', '<EMPLEADO>', current_date, 'cambio de rol', 'ANALISTA FUNCIONAL');
--   INSERT INTO recategorizaciones (empresa_id, empleado_id, fecha_efectiva, motivo, seniority_nueva)
--   VALUES ('<EMPRESA>', '<EMPLEADO>', current_date, 'cambio de seniority', 'SENIOR');
-- ROLLBACK;

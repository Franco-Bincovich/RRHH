-- 097_vacantes_codigo.sql
--
-- QUÉ HACE: `vacantes.codigo` TEXT NOT NULL, formato `VAC-0001`, ÚNICO EN TODO EL SISTEMA.
-- Es el token que RRHH pega en el aviso de LinkedIn ("asunto [VAC-0001]") y con el que el
-- matcher de CVs va a decidir a qué búsqueda pertenece un mail entrante.
--
-- NO ES DESTRUCTIVA: agrega una columna, una secuencia, un índice y un CHECK. No borra ni
-- reescribe ninguna fila existente más allá de completarles el código nuevo.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 🔴 LA UNICIDAD ES GLOBAL, NO POR EMPRESA — y es la decisión que manda sobre el resto
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- El instinto en este repo es `UNIQUE (empresa_id, X)`, porque casi todo cuelga de la empresa.
-- Acá sería un bug: **la casilla que recibe los CVs es UNA SOLA para todo el sistema**. Si
-- DOSUBA y KARSTEC pudieran emitir cada una su `VAC-0001`, un mail con asunto `[VAC-0001]`
-- sería ambiguo y el matcher no tendría con qué desempatar — el remitente es un candidato de
-- afuera, no aporta empresa. Un código ambiguo no falla con un error: manda la postulación a
-- la búsqueda equivocada, en silencio.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 🔴 EL CONTADOR ES UNA SECUENCIA DE POSTGRES EN UN DEFAULT. POR QUÉ, Y CONTRA QUÉ
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- Las tres opciones que había, y por qué gana esta:
--
--   1. **El service lee el máximo y suma uno.** DESCARTADA, y no por elegancia: es una
--      condición de carrera de manual. Dos altas simultáneas leen el mismo máximo, las dos
--      calculan el mismo número y la segunda choca contra el UNIQUE — o, si el UNIQUE no
--      estuviera, las dos quedan con el mismo código y el matcher se rompe para siempre.
--      Con una sola persona cargando vacantes casi nunca se ve; con dos, aparece el día menos
--      pensado y es irreproducible.
--   2. **Un trigger BEFORE INSERT.** Funciona y es igual de atómico, pero agrega una función
--      PL/pgSQL a mantener para algo que un DEFAULT resuelve en una línea. Además este repo ya
--      dropeó sus triggers de lógica de negocio en la migración 058: volver a meter uno iría
--      contra una decisión ya tomada.
--   3. **Secuencia + DEFAULT.** ✅ `nextval()` es atómico y NUNCA devuelve el mismo valor dos
--      veces, ni siquiera bajo concurrencia y sin tomar locks. No hay ventana entre "leer" y
--      "escribir" porque no hay lectura: el valor se reserva al pedirlo.
--
-- Y hay un motivo que decide aparte de la concurrencia: **con el DEFAULT en la base, TODA fila
-- nace con código, venga de donde venga** — del backend, de un INSERT a mano en la consola de
-- Supabase, de un import futuro. Si el código lo pusiera la aplicación, cualquier alta que no
-- pase por ella dejaría una vacante muda que jamás va a poder recibir un CV.
--
-- ⚠️ LA SECUENCIA DEJA HUECOS y está bien. Un INSERT que falla o una transacción que hace
-- rollback consumen el número igual (nextval no se revierte, por diseño: revertirlo exigiría
-- serializar). O sea que puede haber un salto de VAC-0007 a VAC-0009. **El código es un
-- identificador, no un conteo**: nadie va a contar vacantes leyendo el último número, y
-- cerrar los huecos costaría exactamente la condición de carrera que se está evitando.
--
-- ⚠️ EL PADDING ES A 4 DÍGITOS, PERO EL FORMATO ACEPTA MÁS. `lpad(…, 4, '0')` no trunca: en la
-- vacante 10.000 emite `VAC-10000` (5 dígitos) y sigue funcionando. Por eso el CHECK dice
-- `[0-9]{4,}` y no `[0-9]{4}` — con `{4}` exacto, la vacante 10.000 sería rechazada por el
-- CHECK y el alta fallaría sin que nadie entienda por qué.
--
-- ⚠️ EL ÚNICO VA SOBRE `upper(codigo)`, NO SOBRE `codigo`. El lookup del matcher es
-- case-insensitive (un candidato puede escribir `[vac-0001]` en el asunto). Con un UNIQUE
-- sensible a mayúsculas, `VAC-0001` y `vac-0001` podrían coexistir como dos filas distintas y
-- el lookup encontraría DOS — que en `maybe_single()` es un error 500, no un 404. La unicidad
-- tiene que estar definida con el mismo criterio con el que se consulta, o no protege nada.
--
-- ⚠️ AWS/RDS: esto es Postgres estándar (secuencia + DEFAULT + índice funcional). No usa nada
-- propio de Supabase y se recrea igual del otro lado. La secuencia queda OWNED BY la columna,
-- así que un DROP TABLE se la lleva y no queda huérfana.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- BACKFILL
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- Producción tiene **0 vacantes** (verificado contra el catálogo vivo el 8/8/2026), así que el
-- UPDATE no toca ninguna fila. Se escribe igual porque la columna termina NOT NULL: si esta
-- migración se corre alguna vez sobre una base con datos —un entorno de prueba, una restaurada
-- de un backup viejo—, sin el backfill el `SET NOT NULL` falla y la migración queda a medias.
-- El orden add-nullable → backfill → NOT NULL es el que sobrevive a las dos situaciones.

BEGIN;

-- 1. El contador. `nextval` es atómico: es toda la garantía de unicidad bajo concurrencia.
CREATE SEQUENCE IF NOT EXISTS vacantes_codigo_seq AS BIGINT START WITH 1 INCREMENT BY 1;

-- 2. La columna, nullable por ahora (ver BACKFILL).
ALTER TABLE vacantes ADD COLUMN IF NOT EXISTS codigo TEXT;

-- 3. Backfill de las existentes. `ORDER BY created_at, id` para que, si alguna vez corre sobre
--    datos, la vacante más vieja se lleve el número más bajo — sin ORDER BY el reparto lo
--    decide el orden físico de las filas, que no significa nada para quien después los lea.
UPDATE vacantes v
   SET codigo = 'VAC-' || lpad(nextval('vacantes_codigo_seq')::text, 4, '0')
  FROM (SELECT id FROM vacantes WHERE codigo IS NULL ORDER BY created_at, id) AS orden
 WHERE v.id = orden.id;

-- 4. El DEFAULT: toda vacante nueva nace con código, venga del backend o de un INSERT a mano.
ALTER TABLE vacantes
  ALTER COLUMN codigo SET DEFAULT 'VAC-' || lpad(nextval('vacantes_codigo_seq')::text, 4, '0');

-- 5. Recién ahora NOT NULL: sin código, una vacante no puede recibir postulaciones.
ALTER TABLE vacantes ALTER COLUMN codigo SET NOT NULL;

-- 6. La secuencia muere con la columna.
ALTER SEQUENCE vacantes_codigo_seq OWNED BY vacantes.codigo;

-- 7. Unicidad GLOBAL y case-insensitive (ver arriba los dos porqués).
CREATE UNIQUE INDEX IF NOT EXISTS vacantes_codigo_uq ON vacantes (upper(codigo));

-- 8. Forma del código. `{4,}` y no `{4}`: ver la nota del padding.
ALTER TABLE vacantes
  ADD CONSTRAINT vacantes_codigo_formato CHECK (codigo ~ '^VAC-[0-9]{4,}$');

COMMIT;

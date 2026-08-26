-- 122_vacantes_codigo_manual.sql
--
-- QUÉ HACE: el código de la vacante deja de ser `VAC-0001` generado por la base y pasa a ser un
-- campo que ESCRIBE Capital Humano (`ECO-2026`, `LOG-01`, lo que decidan). Esta migración
-- ENSANCHA el CHECK de formato. No toca el índice único, no toca la secuencia, no toca ninguna
-- fila existente.
--
-- NO ES DESTRUCTIVA. Las 5 vacantes de producción (verificado contra el catálogo vivo el
-- 26/8/2026: VAC-0001 .. VAC-0005, todas de la misma empresa, todas con candidatos cargados)
-- pasan el CHECK nuevo sin cambiar: `VAC-0001` es un código válido bajo la forma nueva. Se
-- conservan tal cual A PROPÓSITO — ver abajo.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 🔴 LA UNICIDAD SIGUE SIENDO GLOBAL Y CASE-INSENSITIVE, Y AHORA IMPORTA MÁS QUE ANTES
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- `vacantes_codigo_uq ON vacantes (upper(codigo))` ya existe desde la 097 y NO SE TOCA. El
-- razonamiento de aquella migración se sostiene entero y se refuerza: **la casilla que recibe
-- los CVs es UNA SOLA para todo el sistema**, y quien manda el mail es alguien de afuera que no
-- aporta ninguna empresa. Con unicidad por empresa, `[ECO-2026]` sería ambiguo y el matcher no
-- tendría con qué desempatar — y un código ambiguo no falla con un error: manda la postulación
-- a la búsqueda equivocada, en silencio.
--
-- Lo que CAMBIA es quién puede chocar. Antes el código lo emitía una secuencia y un choque era
-- imposible por construcción; ahora lo tipea una persona, así que el índice pasó de ser una red
-- de seguridad teórica a ser LA garantía. Por eso el backend valida ANTES (para poder decir cuál
-- es la vacante que ya tiene ese código) pero además TRADUCE el error del índice: dos altas
-- simultáneas con el mismo código son una carrera real, y sólo la base la puede resolver.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 🔴 LAS TRES REGLAS DEL FORMATO NUEVO, Y CONTRA QUÉ ESTÁ CADA UNA
-- ═════════════════════════════════════════════════════════════════════════════════════════
--   1. **Sólo `A-Z`, `0-9` y `-` como separador** (`^[A-Z0-9]+(-[A-Z0-9]+)*$`: sin guion al
--      principio, al final, ni dos seguidos). Tres motivos, todos concretos:
--        · El código termina en el ASUNTO DE UN MAIL que tipea un candidato desde el teléfono.
--          Una `Ñ` o una tilde se escriben mal el 30 % de las veces y no hay error visible: el
--          CV cae en revisión manual.
--        · `%` y `_` son COMODINES de `ILIKE`, y `vacante_repo.find_by_codigo` busca con
--          `.ilike("codigo", codigo)`. Un código con `%` haría que el lookup devuelva VARIAS
--          filas, y `maybe_single()` sobre varias filas es un 500, no un 404.
--        · El espacio queda afuera porque el matcher ya trata espacio/punto/guion bajo como
--          separadores tolerados AL LEER; permitirlos también al GUARDAR daría dos códigos
--          distintos (`ECO 26` y `ECO-26`) que se leen igual.
--   2. **Al menos UNA letra.** Un código puramente numérico (`2026`) matchearía cualquier "2026"
--      suelto en un asunto —"CV 2026", "Postulación 2026"— y mandaría el CV a esa búsqueda sin
--      que nada falle. Es la misma clase de decisión que el mínimo de 4 dígitos de la 097: la
--      permisividad llega hasta donde no puede inventar una respuesta distinta.
--   3. **Entre 3 y 30 caracteres.** El piso, por lo mismo que el punto 2: un código de una o dos
--      letras aparece por accidente en cualquier asunto. El techo es para que entre en el asunto
--      junto con el resto del texto y en la columna del listado.
--
-- ⚠️ EL CHECK EXIGE MAYÚSCULAS y la aplicación normaliza antes de escribir
-- (`services/_vacante_codigo.normalizar`). No es cosmética: el índice único es sobre
-- `upper(codigo)`, así que `eco-2026` y `ECO-2026` YA no podían coexistir. Guardar la forma
-- canónica hace que la pantalla, el aviso de LinkedIn y el export digan todos lo mismo, en vez
-- de mostrar la variante que le salió a quien lo cargó primero. Un INSERT a mano en la consola
-- con minúsculas ahora falla explícitamente en vez de crear una fila que se ve distinta.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 🔴 LA SECUENCIA Y EL DEFAULT SE CONSERVAN, Y NO ES INDECISIÓN
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- `codigo` sigue siendo NOT NULL y sigue teniendo el DEFAULT `VAC-` + `nextval`. Ahora la API lo
-- exige en el body (es campo obligatorio del formulario), así que el DEFAULT ya no es el camino
-- normal: es la RED. Una fila que entre por afuera de la aplicación —un INSERT a mano, un import
-- futuro, un backfill— sigue naciendo con un código válido y único en vez de fallar contra el
-- NOT NULL. El argumento de la 097 ("una vacante sin código es una que no puede recibir
-- postulaciones") no cambió; lo único que cambió es quién lo escribe en el caso normal.
--
-- ⚠️ CONSECUENCIA ACEPTADA: si algún día el backend deja de mandar `codigo` por un bug, la fila
-- nace con `VAC-000N` en vez de explotar. Es preferible a la alternativa (una vacante que no se
-- puede crear) y queda visible: el código aparece en la ficha, en el listado y en el export.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- LAS 5 VACANTES EXISTENTES: SE CONSERVAN CON SU `VAC-000N`
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- No se renombran ni se vacían, por tres razones, en orden de peso:
--   1. **Ya están publicadas.** El código es lo que Capital Humano pegó en el aviso; un CV que
--      llegue mañana con `[VAC-0003]` tiene que seguir matcheando. Reescribirlas dejaría a esos
--      mails en revisión manual sin que nadie sepa por qué.
--   2. **Las cinco tienen candidatos** (2 y 3 cada una, verificado el 26/8/2026). Renombrar en
--      masa toca búsquedas vivas.
--   3. **Son válidas bajo la forma nueva.** No hay nada que reparar: `VAC-0001` es exactamente
--      un código de letras, dígitos y guion, con letras, de 8 caracteres.
-- Si Capital Humano quiere renombrarlas, ahora puede: el código es editable desde la ficha de
-- cada búsqueda, de a una y con la misma validación de unicidad.
--
-- ⚠️ AWS/RDS: Postgres estándar (un CHECK). Nada propio de Supabase.

BEGIN;

-- El CHECK viejo sólo admitía `VAC-` + dígitos: con él, `ECO-2026` no se puede guardar.
ALTER TABLE vacantes DROP CONSTRAINT IF EXISTS vacantes_codigo_formato;

ALTER TABLE vacantes
  ADD CONSTRAINT vacantes_codigo_formato CHECK (
    codigo ~ '^[A-Z0-9]+(-[A-Z0-9]+)*$'   -- letras, dígitos y guion como separador
    AND codigo ~ '[A-Z]'                  -- al menos una letra (ver la regla 2)
    AND char_length(codigo) BETWEEN 3 AND 30
  );

COMMIT;

-- VERIFICACIÓN (debe devolver 5 filas, todas `VAC-000N`, y ningún error):
--   SELECT codigo FROM vacantes ORDER BY codigo;

-- 123_vacantes_codigo_texto_natural.sql
--
-- QUÉ HACE: sube el techo de largo del código de vacante de 30 a 60 caracteres. Una línea de
-- efecto; el resto es el porqué.
--
-- NO ES DESTRUCTIVA: ensancha un CHECK. No borra ni reescribe ninguna fila, y todo lo que hoy
-- pasa el CHECK vigente lo sigue pasando (30 ⊂ 60). Las 5 vacantes de producción (`VAC-0001` a
-- `VAC-0005`) no se tocan.
--
-- 🔴 LA 122 YA CORRIÓ. Verificado contra el catálogo vivo el 26/8/2026: el CHECK en producción es
-- el de la 122 (`^[A-Z0-9]+(-[A-Z0-9]+)*$` + al menos una letra + 3..30). Por eso esto es una
-- migración NUEVA y no un retoque de aquélla — una migración que ya corrió es historia.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 🔴 POR QUÉ 30 NO ALCANZA: LO ESCRIBE UNA PERSONA, EN CASTELLANO
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- La 122 puso 30 pensando en códigos tipo `ECO-2026`. Pero el código lo escribe Capital Humano
-- **en texto natural** y la aplicación lo convierte (`services/_vacante_codigo.canonico`):
--
--     "Lider de equipo"                  → LIDER-DE-EQUIPO                  (15)
--     "Ecónomo 2026"                     → ECONOMO-2026                     (12)
--     "Analista de Sistemas Semi Senior" → ANALISTA-DE-SISTEMAS-SEMI-SENIOR (32)  ← ⛔ con 30
--     "Responsable de Administración y Finanzas"
--                                        → RESPONSABLE-DE-ADMINISTRACION-Y-FINANZAS (40)  ← ⛔
--
-- El tercero **no es un ejemplo inventado: es el título de VAC-0002, una de las cinco búsquedas
-- reales que hay cargadas hoy**. Con el techo en 30, esa búsqueda no se podría dar de alta con su
-- propio nombre — que es exactamente el rebote que la feature de texto natural vino a eliminar.
--
-- ⚠️ 60 sigue entrando cómodo en el asunto de un mail y en la columna del listado, que es lo
-- único que este límite protegía. No hay motivo técnico para el número: es el largo a partir del
-- cual un título deja de ser un título y pasa a ser una descripción.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 🔴 PASARSE DEL LARGO RECHAZA, NO RECORTA — Y ESO SE DECIDE EN LA APLICACIÓN, NO ACÁ
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- El CHECK sólo puede rechazar, así que esta decisión no se ve en el SQL; queda escrita acá
-- porque es la que explica por qué el número importa. Recortar en silencio produciría **dos
-- códigos iguales a partir de textos distintos**: "Analista de Sistemas Senior" y "Analista de
-- Sistemas Semi Senior" recortados al mismo largo colapsan, y ahí la segunda búsqueda se
-- rechazaría como duplicada de una que su autor nunca escribió — o peor, el aviso saldría
-- publicado con un código que esa persona no vio nunca. `services/_vacante_codigo.normalizar`
-- rechaza con un mensaje que dice cuántos caracteres sobran.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- LO QUE ESTA MIGRACIÓN NO TOCA, A PROPÓSITO
-- ═════════════════════════════════════════════════════════════════════════════════════════
--   · **El índice `vacantes_codigo_uq ON vacantes (upper(codigo))`** (mig 097). Es LA garantía de
--     que dos búsquedas no compartan código, y con el valor escrito por una persona pasó a ser lo
--     único que resuelve una carrera entre dos altas simultáneas. La unicidad se mide sobre el
--     canónico porque **la columna guarda siempre el canónico**, nunca el texto crudo: por eso
--     "Lider de equipo" y "LIDER DE EQUIPO" chocan, que es lo que se quiere.
--   · **La forma** (`^[A-Z0-9]+(-[A-Z0-9]+)*$`) ni **la regla de al menos una letra**. La
--     conversión no puede producir otra forma, y un código de puros números matchearía cualquier
--     año suelto en el asunto de un mail.
--   · **La secuencia `vacantes_codigo_seq` ni el DEFAULT.** Siguen siendo la red para filas que
--     entren por afuera de la aplicación.
--
-- ⚠️ AWS/RDS: Postgres estándar (un CHECK). Nada propio de Supabase.

BEGIN;

ALTER TABLE vacantes DROP CONSTRAINT IF EXISTS vacantes_codigo_formato;

ALTER TABLE vacantes
  ADD CONSTRAINT vacantes_codigo_formato CHECK (
    codigo ~ '^[A-Z0-9]+(-[A-Z0-9]+)*$'   -- letras, dígitos y guion como separador
    AND codigo ~ '[A-Z]'                  -- al menos una letra
    AND char_length(codigo) BETWEEN 3 AND 60
  );

COMMIT;

-- VERIFICACIÓN (el CHECK tiene que decir 60, y las 5 vacantes seguir ahí):
--   SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'vacantes_codigo_formato';
--   SELECT codigo FROM vacantes ORDER BY codigo;

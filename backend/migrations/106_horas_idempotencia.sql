-- 106_horas_idempotencia.sql
--
-- QUÉ HACE: agrega `horas_proyecto.idempotencia` + índice único parcial. Cierra el DOBLE TAP.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 LA CARRERA DEL TOPE DE 12 HORAS, Y HASTA DÓNDE SE PUEDE CERRAR
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- El tope es "12 horas por día SUMANDO todas las cargas de esa persona ese día". Eso es una
-- restricción sobre la SUMA DE VARIAS FILAS, y ninguna constraint de Postgres puede expresarla:
-- un CHECK solo ve la fila que se inserta.
--
-- La carrera es real: dos envíos simultáneos leen 8 horas cada uno, los dos validan "8+4 ≤ 12"
-- y los dos insertan. Quedan 16 y nada lo atrapa.
--
-- Se separó en DOS problemas, porque tienen respuestas distintas:
--
--   1. EL DOBLE TAP — la misma carga enviada dos veces (doble clic, reintento del navegador,
--      el usuario que no vio la confirmación). Es el caso REALISTA y el que más va a pasar.
--      🟢 ESTE SE CIERRA ACÁ. El cliente genera un identificador por INTENTO de envío y lo
--      manda; el índice único hace que el segundo INSERT no entre. La segunda llamada devuelve
--      la fila que ya se creó, así que para el usuario es idempotente y no un error.
--
--   2. DOS CARGAS DISTINTAS ENVIADAS A LA VEZ (dos pestañas, dos dispositivos). El total puede
--      pasarse de 12.
--      🔴 ESTE QUEDA DECLARADO COMO LÍMITE CONOCIDO, y este es el motivo:
--        · Un TRIGGER lo resolvería, pero los triggers de negocio se DROPEARON repo-wide en la
--          migración 058 y esa es una decisión tomada, no un olvido. Reintroducir uno acá
--          rompería la regla que dice que la captura es app-level.
--        · Una transacción SERIALIZABLE también, pero PostgREST no expone control de
--          transacciones: cada llamada es su propia transacción implícita.
--        · Un contador denormalizado por (empleado, fecha) con compare-and-swap SÍ cerraría la
--          carrera, y se descartó a conciencia: sería un agregado que hay que mantener en
--          sincronía con `horas_proyecto` desde TODOS los caminos —incluido el "editar y
--          borrar" de la vista interna, que todavía no está construido—. Un total que puede
--          driftear del detalle es peor que la carrera: la carrera te da 16 horas visibles y
--          corregibles, el drift te da un número que miente sin que nadie lo note.
--      El daño acotado: el techo se pasa solo con envíos SIMULTÁNEOS de cargas DISTINTAS, el
--      exceso queda VISIBLE en la vista interna (que suma por día) y RRHH lo corrige. No hay
--      pérdida de datos ni escalación de privilegios.
--      🚩 Disparador para revisarlo: el cutover a AWS/asyncpg, donde SÍ hay transacciones
--      reales y esto se cierra con un SELECT ... FOR UPDATE sobre las filas del día.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- POR QUÉ UNA COLUMNA Y NO UNA CLAVE NATURAL
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- Se evaluó un índice único sobre el CONTENIDO (empleado + fecha + horas + cliente + textos).
-- Rechazado: "varias cargas por día" es una decisión de producto explícita —la persona detalla
-- distintas tareas— y dos renglones legítimamente idénticos son posibles (2 h de "Reunión" para
-- el mismo cliente, dos veces en el día). Una clave natural prohibiría eso, o sea rompería una
-- regla de producto para cerrar un bug de infraestructura.
--
-- El índice es PARCIAL (`WHERE idempotencia IS NOT NULL`): el camino viejo
-- (POST /api/proyectos/{id}/horas) no manda el campo y no lo toca ni de casualidad.
--
-- NO DESTRUCTIVA: agrega una columna nullable. Idempotente. NO se ejecuta acá (la corre Franco).

BEGIN;

ALTER TABLE public.horas_proyecto ADD COLUMN IF NOT EXISTS idempotencia text;

CREATE UNIQUE INDEX IF NOT EXISTS ux_hp_idempotencia
    ON public.horas_proyecto USING btree (idempotencia) WHERE (idempotencia IS NOT NULL);

COMMIT;

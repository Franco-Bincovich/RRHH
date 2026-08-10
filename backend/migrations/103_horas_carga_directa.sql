-- 103_horas_carga_directa.sql
--
-- QUÉ HACE: habilita en `horas_proyecto` la carga que NO pasa por una asignación de proyecto.
-- Agrega el cliente, la modalidad del día y el proyecto/tarea como texto libre, y AFLOJA los
-- tres NOT NULL que ataban la tabla al costeo de proyectos.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 POR QUÉ SE AFLOJA LA TABLA EXISTENTE Y NO SE CREA UNA NUEVA
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- `horas_proyecto` nació para costear proyectos: cada fila colgaba de una `proyecto_asignaciones`
-- y congelaba su `valor_hora` en `valor_hora_snapshot`. El flujo nuevo no pasa por ninguna
-- asignación — el empleado elige un CLIENTE, y el proyecto (si lo escribe) es texto.
--
-- Aun así el registro de horas trabajadas es UNO SOLO. Dos tablas obligarían a que todo lector
-- —el costeo, el listado, el export, los KPIs— hiciera UNION de dos formas distintas para
-- responder "cuántas horas trabajó esta persona", y la primera que se olvidara de la segunda
-- tabla daría un número menor sin ningún error. Es el mismo razonamiento por el que
-- `vacaciones_pendientes` SÍ es tabla aparte (mig 083) y acá no: allá un día no tomado no es un
-- hecho del calendario y no comparte ninguna pregunta con las solicitudes; acá las dos cargas
-- responden exactamente la misma pregunta.
--
-- EL CAMINO VIEJO NO SE TOCA. `POST /api/proyectos/{id}/horas` sigue escribiendo los tres
-- campos como siempre. Aflojar un NOT NULL no cambia una sola fila existente ni un solo INSERT
-- que ya mandaba el valor.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 `cliente_id` NACE NULLABLE AUNQUE LA CARGA NUEVA LO EXIJA
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- La obligatoriedad la impone el SERVICE del flujo nuevo, no la base, porque la base tiene DOS
-- escritores con contratos distintos: el camino viejo escribe proyecto+asignación y NO tiene
-- cliente que poner. Un NOT NULL acá rompería ese INSERT — y con 0 filas hoy, el síntoma no
-- sería un backfill fallido sino un endpoint publicado que empieza a dar 500.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 `empleado_id` — COLUMNA QUE EL DISEÑO NO ENUMERÓ Y SIN LA CUAL NO CIERRA
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- Hoy la tabla NO tiene de quién son las horas: se llega al empleado por
-- `asignacion_id -> proyecto_asignaciones.empleado_id`. Si `asignacion_id` puede ser NULL,
-- una carga del flujo nuevo queda SIN DUEÑO, y no hay otra columna de la que deducirlo:
--   · `empleado_empresa_id` dice de qué sociedad es, no quién es.
--   · `cargado_por` es FK a `users`, y los empleados NO tienen cuenta — `empleados.user_id`
--     está en 0/31 y `users` tiene 4 filas (el equipo de RRHH).
-- Sin esta columna no se puede responder "las horas de esta persona esta semana", que es la
-- tabla de solo lectura del propio flujo, ni "el detalle por empleado" de la vista interna.
-- Se agrega NULLABLE: el camino viejo la deja en NULL y sigue resolviendo por la asignación.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- MODALIDAD: VOCABULARIO CERRADO, GUARDADO COMO SLUG
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- Valores en base: 'home_office' | 'on_site'. Las etiquetas que ve el usuario ("Home Office" /
-- "On site") las pone la UI. Es el criterio de TODO vocabulario cerrado del repo
-- (`proyectos.estado` = activo|pausado|cerrado|cancelado, `empleados.modalidad_trabajo` =
-- presencial|hibrido): guardar el texto de pantalla convierte un cambio de redacción en una
-- migración de datos.
-- ⚠️ NO se reusa `empleados.modalidad_trabajo`: esa es del EMPLEADO y su vocabulario
-- (presencial/hibrido) no tiene traducción a un valor de día — "híbrido" no es algo que alguien
-- haya sido un martes. Es del día, y por eso vive acá.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- QUÉ PASA CON EL COSTEO Y CON EL GATE DE BORRADO (verificado, no cambia nada)
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- Las filas del flujo nuevo tienen `proyecto_id IS NULL`, y las dos consultas que miran esta
-- tabla desde el módulo de proyectos las descartan SOLAS:
--   · `_proyectos_enrich.batch_costos` usa `.in_("proyecto_id", ids)` → un NULL nunca matchea
--     un IN, así que no suma al costo de ningún proyecto. Correcto: una hora sin proyecto no
--     tiene contra qué costearse (además de no tener `valor_hora_snapshot`).
--   · `ProyectosRepo.has_horas` usa `.eq("proyecto_id", id)` → ídem: no bloquea el borrado de
--     ningún proyecto. Correcto: no es una hora de ese proyecto.
-- Es la MISMA semántica de "NULL se cae del WHERE" que en la migración 083 era el bug a evitar.
-- Acá es exactamente el comportamiento buscado, y por eso se deja escrito: para que nadie lo
-- "arregle" con un `.or_(proyecto_id.is.null)` creyendo que faltan filas.
--
-- ÍNDICES NUEVOS: los dos son del acceso que este módulo hace todo el tiempo y que ningún
-- índice actual cubre (los 4 de hoy son sobre asignacion, empresa, fecha y proyecto sueltos).
--   · idx_hp_cliente        → "horas por cliente", que es la vista interna entera.
--   · idx_hp_empleado_fecha → "lo que cargó esta persona en este rango", que es la tabla de la
--                             semana y, más adelante, la suma del día del tope de horas.
-- Los dos son PARCIALES (WHERE ... IS NOT NULL): las filas del camino viejo no los tocan.
--
-- NO DESTRUCTIVA: no borra datos, no dropea columnas, no cambia ningún valor existente.
-- Aflojar un NOT NULL es siempre compatible hacia atrás. Idempotente.
-- ⚠️ DEPENDE DE LA 102 (la FK apunta a `clientes`). Correr en orden.
-- NO se ejecuta acá (la corre Franco).

BEGIN;

-- ── Columnas nuevas ──────────────────────────────────────────────────────────────────────
ALTER TABLE public.horas_proyecto ADD COLUMN IF NOT EXISTS cliente_id uuid;
ALTER TABLE public.horas_proyecto ADD COLUMN IF NOT EXISTS empleado_id uuid;
ALTER TABLE public.horas_proyecto ADD COLUMN IF NOT EXISTS modalidad text;
ALTER TABLE public.horas_proyecto ADD COLUMN IF NOT EXISTS proyecto_texto text;
ALTER TABLE public.horas_proyecto ADD COLUMN IF NOT EXISTS tarea_texto text;

-- ── Los tres NOT NULL del costeo por asignación ──────────────────────────────────────────
ALTER TABLE public.horas_proyecto ALTER COLUMN asignacion_id DROP NOT NULL;
ALTER TABLE public.horas_proyecto ALTER COLUMN proyecto_id DROP NOT NULL;
ALTER TABLE public.horas_proyecto ALTER COLUMN valor_hora_snapshot DROP NOT NULL;

-- ── Constraints ──────────────────────────────────────────────────────────────────────────
-- Sin ON DELETE, igual que las otras cinco FKs de la tabla: una hora cargada no se borra
-- porque alguien dé de baja el cliente. La baja del cliente es lógica (clientes.activo).
ALTER TABLE public.horas_proyecto DROP CONSTRAINT IF EXISTS horas_proyecto_cliente_id_fkey;
ALTER TABLE public.horas_proyecto
    ADD CONSTRAINT horas_proyecto_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id);

ALTER TABLE public.horas_proyecto DROP CONSTRAINT IF EXISTS horas_proyecto_empleado_id_fkey;
ALTER TABLE public.horas_proyecto
    ADD CONSTRAINT horas_proyecto_empleado_id_fkey FOREIGN KEY (empleado_id) REFERENCES public.empleados(id);

-- El CHECK acepta NULL a propósito: las filas del camino viejo no tienen modalidad y no la
-- necesitan. La obligatoriedad para la carga nueva la impone el service, igual que el cliente.
ALTER TABLE public.horas_proyecto DROP CONSTRAINT IF EXISTS horas_proyecto_modalidad_check;
ALTER TABLE public.horas_proyecto
    ADD CONSTRAINT horas_proyecto_modalidad_check
    CHECK (modalidad IS NULL OR modalidad = ANY (ARRAY['home_office'::text, 'on_site'::text]));

-- 🔴 LA TABLA TIENE EXACTAMENTE DOS FORMAS DE FILA, Y ESTE CHECK LAS FIJA.
-- Aflojar tres NOT NULL por separado habilita 2^3 combinaciones, y seis de ellas no significan
-- nada. Una en particular es una BOMBA: `proyecto_id` con `valor_hora_snapshot` NULL entra al
-- `.in_("proyecto_id", ids)` de `_proyectos_enrich.batch_costos`, que hace
-- `float(r["valor_hora_snapshot"])` sin guarda → TypeError → 500 en el listado de proyectos.
-- Con este CHECK ese estado no se puede representar, así que el costeo queda seguro POR
-- CONSTRUCCION y no por casualidad. Es preferible a poner un `or 0` en el lector: ese 0
-- convertiría "no se puede costear" en "costó cero", justo al revés del `costo=None` que
-- HoraResponse decide para el mismo caso.
ALTER TABLE public.horas_proyecto DROP CONSTRAINT IF EXISTS horas_proyecto_forma_check;
ALTER TABLE public.horas_proyecto
    ADD CONSTRAINT horas_proyecto_forma_check
    CHECK (
        (asignacion_id IS NULL     AND proyecto_id IS NULL     AND valor_hora_snapshot IS NULL)
     OR (asignacion_id IS NOT NULL AND proyecto_id IS NOT NULL AND valor_hora_snapshot IS NOT NULL)
    );

-- ── Índices ──────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_hp_cliente
    ON public.horas_proyecto USING btree (cliente_id) WHERE (cliente_id IS NOT NULL);

CREATE INDEX IF NOT EXISTS idx_hp_empleado_fecha
    ON public.horas_proyecto USING btree (empleado_id, fecha) WHERE (empleado_id IS NOT NULL);

COMMIT;

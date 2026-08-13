-- 115_indices_escala.sql
--
-- QUÉ HACE: agrega SEIS índices compuestos `(empresa_id, <fecha>)` sobre las tablas cuyos
-- listados paginados hoy hacen que Postgres descarte filas de las otras empresas para armar
-- la página 1. Nada más: no crea tablas, no toca columnas, no mueve un solo dato.
--
-- ADITIVA PURA Y NO DESTRUCTIVA. No dropea ningún índice (el porqué está en el bloque
-- "ÍNDICES VIEJOS" de abajo, que no es un olvido: es una decisión con evidencia).
-- Idempotente: `CREATE INDEX IF NOT EXISTS`. Se puede correr de nuevo sin efecto.
-- Va ANTES del deploy y sin ventana: un índice nuevo no cambia ningún resultado, solo el plan.
-- NO se ejecuta acá (la corre Franco).
--
-- Verificado contra el catálogo vivo (grmdiwxcvcjorlohpwji) el 2026-08-13: **ninguno de los
-- seis existe**, y ninguno de los índices actuales cubre el mismo prefijo de columnas.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 🔴 POR QUÉ UN ÍNDICE COMPUESTO Y NO LOS DOS SUELTOS QUE YA ESTÁN
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- Todas estas tablas YA tienen un índice por `empresa_id` y otro por la fecha, separados. Eso
-- NO resuelve el patrón `WHERE empresa_id = X ORDER BY fecha DESC LIMIT 20`, porque Postgres
-- puede usar UN solo índice por escaneo y ninguno de los dos sirve para las dos mitades:
--
--   · si elige el de FECHA, recorre la tabla entera en orden de fecha y va DESCARTANDO las
--     filas de las otras empresas hasta juntar 20 de la que se pidió;
--   · si elige el de EMPRESA, junta todas las filas de esa empresa y después las ORDENA.
--
-- El planner elige el primero, y ahí está el problema de escala: **la cantidad de filas
-- descartadas crece cada vez que se suma una empresa.** Con 2 empresas descarta la mitad; con
-- 10, nueve décimos. Es el único patrón del sistema que empeora con el número de EMPRESAS y no
-- con el de filas, y por eso entra en el lote que congela el schema.
--
-- MEDIDO (base local de escala: 10 empresas, 1.005 colaboradores, 200.000 eventos de
-- auditoría; detalle en docs/DIAGNOSTICO-ESCALA.md §7.2). Página 1 de la empresa más chica:
--
--                                   filas descartadas   buffers   tiempo
--   auditoria, índices de hoy .....       1.326           1.353    1,53 ms
--   auditoria, con el compuesto ...           0              23    0,096 ms   (16× · 59× buffers)
--
-- Lo que importa no es el 0,1 ms: es que la columna "filas descartadas" es CERO y deja de
-- crecer con el número de empresas.
--
-- ⚠️ LO QUE ESTOS ÍNDICES NO ARREGLAN, también medido: la paginación PROFUNDA. Con
-- `OFFSET 2000` el compuesto no ayuda (11,4 ms con, 9,7 ms sin): un OFFSET es O(offset) con
-- cualquier plan. Si alguien pagina hondo en auditoría, eso se resuelve con paginación por
-- cursor, no con un índice. No es un pendiente de esta migración: es otra cosa.
--
-- ⚠️ Y NO SIRVEN PARA LOS LISTADOS SIN PAGINAR. Se probaron los mismos compuestos en
-- `empleado_capacitacion`, `candidatos` e `inventario_asignaciones`, que ordenan por fecha pero
-- devuelven TODO sin LIMIT: **el planner ni los usa** — sigue haciendo Seq Scan + Sort, porque
-- sin LIMIT leer todo y ordenar es más barato que recorrer un índice. Por eso no están acá:
-- serían costo de escritura puro. A esos módulos los arregla la PAGINACIÓN, y el índice recién
-- tiene sentido el día que la tengan.
--
-- ── CREATE INDEX y no CREATE INDEX CONCURRENTLY, a propósito ──────────────────────────────
-- `CONCURRENTLY` no evita el lock por magia: lo cambia por dos pasadas sobre la tabla y **no
-- puede correr dentro de una transacción**, que es justo como el editor SQL de Supabase manda
-- los statements. Con los volúmenes de producción de hoy (auditoría: 156 filas) el lock de un
-- `CREATE INDEX` normal dura milisegundos. Si alguna de estas tablas llegara a millones de
-- filas antes de correr esto, ahí sí hay que pasar a CONCURRENTLY y correr cada statement suelto.

-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 1. costos_nomina — el más rentable de los seis, y no estaba en la sospecha inicial
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- CONSULTA QUE SIRVE: la nómina de un período, que es la pantalla de Costos y el insumo del
-- reporte de masa salarial.
--   SELECT * FROM costos_nomina WHERE empresa_id = $1 AND anio = $2 AND mes = $3;
--   (repositories/nomina_repo.py)
--
-- GANANCIA MEDIDA: 26,57 ms → 0,57 ms  ·  **47×**, la mayor de las seis.
--
-- POR QUÉ ES LA PEOR HOY: el índice que el planner elige es `idx_costos_nomina_periodo
-- (anio, mes)`, que trae las filas de ESE MES DE TODAS LAS EMPRESAS y después filtra. Con 10
-- empresas y 22.360 filas ya descarta 605 de 1.005 en cada consulta. Escala con el padrón
-- TOTAL del sistema, no con el de la empresa que se está mirando.
CREATE INDEX IF NOT EXISTS idx_costos_nomina_empresa_periodo
    ON public.costos_nomina (empresa_id, anio, mes);

-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 2. auditoria — la tabla que más crece
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- CONSULTA QUE SIRVE: la página 1 de /auditoria, que es como se entra siempre a la pantalla.
--   SELECT * FROM auditoria WHERE empresa_id = $1 ORDER BY created_at DESC LIMIT 20;
--   (repositories/audit_repo.py::listar)
--
-- GANANCIA MEDIDA sobre 200.000 eventos: 1,53 ms → 0,096 ms (**16×**), y de 1.353 buffers a 23.
--
-- ⚠️ NO cubre el caso con filtro de RANGO de fechas: ahí el planner sigue prefiriendo
-- `idx_auditoria_created`, y hace bien (el rango ya acota). Los dos índices tienen su caso —
-- es la razón principal por la que `idx_auditoria_created` NO se dropea.
CREATE INDEX IF NOT EXISTS idx_auditoria_empresa_created
    ON public.auditoria (empresa_id, created_at DESC);

-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 3 y 4. solicitudes_vacaciones y solicitudes_ausencia
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- CONSULTA QUE SIRVE: el listado paginado de cada módulo.
--   SELECT * FROM solicitudes_vacaciones WHERE empresa_id = $1 ORDER BY fecha_desde DESC LIMIT 20;
--   (repositories/vacaciones_repo.py:21 · repositories/ausencias_repo.py:23)
--
-- GANANCIA MEDIDA en vacaciones: 1,42 ms → 0,12 ms  ·  **12×**.
--
-- 🔑 AUSENCIAS VA POR SIMETRÍA, y eso se declara en vez de disimularse: su repo construye la
-- MISMA query con la misma forma (`.eq(empresa_id).order("fecha_desde", desc=True)` + `range`)
-- sobre una tabla del mismo orden de magnitud. Medirla por separado habría dado el mismo
-- número. Lo que NO sería aceptable es la simetría al revés: poner el índice en una y no en la
-- otra deja dos módulos gemelos con planes distintos, y el que quede afuera se descubre recién
-- cuando alguien se queja.
CREATE INDEX IF NOT EXISTS idx_sv_empresa_fecha
    ON public.solicitudes_vacaciones (empresa_id, fecha_desde DESC);

CREATE INDEX IF NOT EXISTS idx_sa_empresa_fecha
    ON public.solicitudes_ausencia (empresa_id, fecha_desde DESC);

-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 5. vacaciones_pendientes — NO estaba en el diagnóstico original; salió de barrer los repos
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- CONSULTA QUE SIRVE: el listado paginado de días pendientes.
--   SELECT * FROM vacaciones_pendientes WHERE empresa_id = $1 ORDER BY periodo DESC LIMIT 20;
--   (repositories/vacaciones_pendientes_repo.py:38)
--
-- GANANCIA MEDIDA: 0,175 ms → 0,061 ms, y el plan pasa a `Index Scan` sobre el compuesto.
--
-- 🔑 ORDENA POR `periodo`, NO POR UNA FECHA. Es el mismo patrón —igualdad por empresa + orden
-- + LIMIT— con otra columna de orden. Entra por eso, no por parecerse en el nombre: lo que
-- define al patrón es la forma de la query, no que la columna se llame `fecha`.
CREATE INDEX IF NOT EXISTS idx_vp_empresa_periodo
    ON public.vacaciones_pendientes (empresa_id, periodo DESC);

-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 6. horas_proyecto — el mismo patrón, pero el eje NO es la empresa
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- CONSULTA QUE SIRVE: las horas de UN proyecto, paginadas.
--   SELECT * FROM horas_proyecto WHERE proyecto_id = $1 ORDER BY fecha DESC LIMIT 20;
--   (repositories/horas_repo.py:34-36)
--
-- GANANCIA MEDIDA: 0,463 ms → 0,100 ms  ·  **4,6×**, con `Index Scan` sobre el compuesto.
--
-- 🔑 ACÁ EL FILTRO ES `proyecto_id` Y NO `empresa_id`, y está bien que así sea: la vista de
-- horas por cliente NO se recorta por empresa (decisión de producto — las horas de un cliente
-- son del cliente). El patrón que este índice ataca es el mismo —igualdad + orden por fecha +
-- LIMIT—; lo que cambia es cuál es la columna de igualdad. Meterle `empresa_id` "por
-- consistencia" daría un índice que esta query no puede usar.
CREATE INDEX IF NOT EXISTS idx_hp_proyecto_fecha
    ON public.horas_proyecto (proyecto_id, fecha DESC);

ANALYZE public.costos_nomina;
ANALYZE public.auditoria;
ANALYZE public.solicitudes_vacaciones;
ANALYZE public.solicitudes_ausencia;
ANALYZE public.vacaciones_pendientes;
ANALYZE public.horas_proyecto;

-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 🔴 ÍNDICES VIEJOS: NO SE DROPEA NINGUNO, Y EL CRITERIO ES ESTE
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- El candidato "obvio" era `idx_costos_nomina_periodo (anio, mes)`, porque el compuesto nuevo
-- lo parecería cubrir. **NO SE DROPEA, y la evidencia lo dice fuerte:** tiene **608 escaneos**
-- en producción, el índice más usado de esa tabla (`pg_stat_user_indexes`, 13/8/2026).
--
-- El motivo es el MODO CONSOLIDADO, que es el default del sidebar: ahí `empresa_id` viaja como
-- NULL y la query sale SIN filtro de empresa —`WHERE anio = $1 AND mes = $2`—. Un índice
-- `(empresa_id, anio, mes)` NO puede servir a esa consulta: le falta la columna que va primero.
-- Los dos índices cubren mitades distintas del mismo módulo.
--
-- 🔑 LA REGLA QUE SALE DE ACÁ, y aplica a cualquier índice futuro de este repo:
--     un índice cuya PRIMERA columna sea la fecha (o el período) sirve al modo CONSOLIDADO;
--     uno cuya primera columna sea `empresa_id` sirve al modo POR EMPRESA.
--     Como los dos modos existen y el consolidado es el default, LOS DOS HACEN FALTA.
-- Vale igual para `idx_auditoria_created`, `idx_hp_fecha` y cualquier `(fecha)` suelto.
--
-- ── Los que SÍ quedan redundantes, y por qué tampoco se dropean HOY ───────────────────────
-- Estos cuatro tienen `empresa_id` como única columna, o sea exactamente el prefijo del
-- compuesto nuevo, así que el compuesto los subsume y podrían borrarse:
--     idx_costos_nomina_empresa · idx_auditoria_empresa · idx_sv_empresa_id · idx_sa_empresa_id
--
-- No se hace en esta migración por tres razones, en orden de peso:
--   1. **Esta migración es aditiva pura**, y esa propiedad es lo que la deja correr antes del
--      deploy sin ventana ni riesgo. Un DROP la convierte en otra cosa.
--   2. **La evidencia para dropear todavía no existe.** Los `idx_scan` de producción salen de
--      una base con 31 empleados y 156 eventos, donde el planner casi no usa índices: son
--      números demasiado chicos para decidir un borrado. El dato que hace falta es el `idx_scan`
--      DESPUÉS de un mes con los índices nuevos y volumen real.
--   3. **El beneficio es chico y el momento es malo.** Lo que se gana es escritura (un índice
--      menos que mantener por INSERT) y unos KB. Hacerlo justo antes de entregarle el repo al
--      dev de infra agrega un modo de falla a cambio de casi nada.
--
-- CUÁNDO REVISARLO: un mes después de que esto esté en producción con datos reales, corriendo
-- la consulta de verificación (E) de abajo. Si los cuatro siguen en ~0 escaneos, ahí sí van a
-- una migración propia de limpieza — y sin apuro, porque un índice de más no rompe nada.


-- ═════════════════════════════════════════════════════════════════════════════════════════
-- VERIFICACIÓN POSTERIOR — para correr DESPUÉS de aplicar la migración
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 🔴 CÓMO SE LEE CADA UNA: tiene que nombrar el índice NUEVO, como `Index Scan using ...` o
-- como `Bitmap Index Scan on ...` (las dos formas cuentan: la segunda es la que elige el
-- planner cuando espera varias filas, y en el caso 1 es la esperada). Lo que NO tiene que
-- aparecer es un nodo `Sort` sobre la columna de orden: eso significa que el índice no se está
-- usando para ordenar, que es la mitad del trabajo que vino a hacer.
--
-- ⚠️ DOS RAZONES POR LAS QUE ESTO PUEDE DAR `Seq Scan` + `Sort` SIN QUE NADA ESTÉ MAL, y las
-- dos hacen que alguien concluya que la migración no sirvió:
--
--   1. **Pocas filas en la tabla.** Con 156 filas en `auditoria`, leerla entera es más barato
--      que abrir un índice y el planner elige bien. No significa que el índice sobre:
--      significa que todavía no hace falta.
--   2. **La empresa elegida tiene pocas filas.** 🔑 Esto pasó al verificar y es la trampa más
--      fácil: con la empresa MÁS CHICA (15 colaboradores), `solicitudes_ausencia` y
--      `vacaciones_pendientes` dieron `Sort`; con la MÁS GRANDE (400), las dos dieron
--      `Index Scan` sobre el índice nuevo. **Elegir una empresa con volumen** — si no, se
--      verifica el caso donde el índice correctamente no aplica.
--
-- Para elegir una con volumen:
--   SELECT e.id, e.nombre, count(p.id) AS dotacion FROM empresas e
--     LEFT JOIN empleados p ON p.empresa_id = e.id GROUP BY e.id, e.nombre ORDER BY 3 DESC;
--
-- Lo que SÍ es concluyente con cualquier volumen: (A) que los seis existan y (D) que ninguno
-- quede inválido. El plan se vuelve concluyente cuando las tablas crezcan. Para ver el efecto
-- hoy está la base local de escala (`scripts/seed_escala.py`), que es donde se midió todo esto.

-- ── (A) Los seis existen ───────────────────────────────────────────────────────────────────
--     Tiene que devolver exactamente 6 filas.
-- SELECT indexname, tablename FROM pg_indexes
--  WHERE schemaname = 'public'
--    AND indexname IN ('idx_costos_nomina_empresa_periodo', 'idx_auditoria_empresa_created',
--                      'idx_sv_empresa_fecha', 'idx_sa_empresa_fecha',
--                      'idx_vp_empresa_periodo', 'idx_hp_proyecto_fecha')
--  ORDER BY tablename;

-- ── (B) Un EXPLAIN por índice, con la consulta que cada uno sirve ──────────────────────────
--     Reemplazar <EMPRESA> por un uuid real:  SELECT id, nombre FROM empresas LIMIT 5;
--     Reemplazar <PROYECTO> por:              SELECT id, nombre FROM proyectos LIMIT 5;
--
-- 1) costos_nomina → espera: Index Scan using idx_costos_nomina_empresa_periodo
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM costos_nomina
--  WHERE empresa_id = '<EMPRESA>' AND anio = 2026 AND mes = 7;
--
-- 2) auditoria → espera: Index Scan using idx_auditoria_empresa_created, SIN nodo Sort
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM auditoria
--  WHERE empresa_id = '<EMPRESA>' ORDER BY created_at DESC LIMIT 20;
--
-- 3) solicitudes_vacaciones → espera: Index Scan using idx_sv_empresa_fecha, SIN Sort
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM solicitudes_vacaciones
--  WHERE empresa_id = '<EMPRESA>' ORDER BY fecha_desde DESC LIMIT 20;
--
-- 4) solicitudes_ausencia → espera: Index Scan using idx_sa_empresa_fecha, SIN Sort
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM solicitudes_ausencia
--  WHERE empresa_id = '<EMPRESA>' ORDER BY fecha_desde DESC LIMIT 20;
--
-- 5) vacaciones_pendientes → espera: Index Scan using idx_vp_empresa_periodo, SIN Sort
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM vacaciones_pendientes
--  WHERE empresa_id = '<EMPRESA>' ORDER BY periodo DESC LIMIT 20;
--
-- 6) horas_proyecto → espera: Index Scan using idx_hp_proyecto_fecha, SIN Sort
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM horas_proyecto
--  WHERE proyecto_id = '<PROYECTO>' ORDER BY fecha DESC LIMIT 20;

-- ── (C) La contracara: el modo CONSOLIDADO sigue usando los índices viejos ─────────────────
--     Es lo que prueba que no sobraban. Espera: Index Scan using idx_costos_nomina_periodo
--     (o Seq Scan con pocos datos), y NUNCA el compuesto nuevo.
-- EXPLAIN (ANALYZE) SELECT * FROM costos_nomina WHERE anio = 2026 AND mes = 7;

-- ── (D) Ninguno quedó inválido ────────────────────────────────────────────────────────────
--     Un CREATE INDEX interrumpido deja el índice `indisvalid = false`: existe, aparece en
--     pg_indexes, y el planner NO lo usa. Tiene que devolver 0 filas.
-- SELECT c.relname AS indice FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid
--  JOIN pg_namespace n ON n.oid = c.relnamespace
--  WHERE n.nspname = 'public' AND NOT i.indisvalid;

-- ── (E) Base para decidir MÁS ADELANTE si los 4 redundantes se dropean ─────────────────────
--     Correr un mes después. Si los `idx_*_empresa*` de una sola columna siguen en ~0 y los
--     compuestos nuevos tienen escaneos, ahí sí se limpian en una migración aparte.
-- SELECT relname AS tabla, indexrelname AS indice, idx_scan AS escaneos,
--        pg_size_pretty(pg_relation_size(indexrelid)) AS tam
--   FROM pg_stat_user_indexes
--  WHERE schemaname = 'public'
--    AND relname IN ('costos_nomina', 'auditoria', 'solicitudes_vacaciones',
--                    'solicitudes_ausencia', 'vacaciones_pendientes', 'horas_proyecto')
--  ORDER BY relname, idx_scan DESC;

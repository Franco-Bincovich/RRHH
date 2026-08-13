-- 113_lote_features_aditivo.sql
--
-- QUÉ HACE: la mitad ADITIVA PURA del lote que congela el schema. Tres tablas nuevas y tres
-- columnas nuevas sobre tablas existentes. **Nada de esto lo ve el código que hoy está en
-- producción**, así que se puede correr ANTES del deploy y sin ventana.
--
-- La otra mitad —lo que depende del código nuevo— va en `114_lote_features_post_deploy.sql`.
-- El porqué del corte, el orden y las alternativas descartadas están en
-- `docs/DIAGNOSTICO-FASE-1.md` §10.
--
-- NO DESTRUCTIVA: no borra nada, no dropea ningún índice, no mueve un solo dato.
-- Idempotente: IF NOT EXISTS + DROP IF EXISTS + CREATE. Se puede correr de nuevo.
-- NO se ejecuta acá (la corre Franco).
-- Verificado contra el catálogo vivo (grmdiwxcvcjorlohpwji) el 2026-08-13: las tres tablas NO
-- existen y ninguna de las tres columnas está declarada.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 🔴 ESCALA: ESTO SE DIMENSIONA PARA ~10 EMPRESAS Y ~1000 COLABORADORES, NO PARA 2 Y 31
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- Una tabla se crea UNA vez; un índice que falta se agrega después, y "después" es coordinar
-- con el dev de infra en medio de su migración. Así que cada índice de abajo está puesto contra
-- una consulta concreta, y cada uno dice cuál. Los que NO están tampoco son un olvido: donde el
-- volumen no lo justifica está escrito que se decidió no ponerlo.
--
-- El patrón que se repite es el ÍNDICE PARCIAL. No es elegancia: en las tres columnas nuevas de
-- fecha la enorme mayoría de las filas va a tener NULL —un padrón de 1000 personas tiene un
-- puñado de ingresos previstos a la vez— y un índice completo indexaría 1000 filas para servir
-- 10. El parcial indexa 10. Es el mismo criterio con el que ya viven
-- `idx_empleados_domicilio_provincia` y `ux_hp_idempotencia`.
--
-- ⚠️ SIN RLS, en las tres tablas nuevas. Es la regla del porteo: en AWS/RDS no va a haber RLS y
-- la seguridad es app-level. Crear políticas acá sería trabajo que hay que deshacer.

BEGIN;

-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 1. perfiles_puesto — el catálogo de plantillas de puesto, GLOBAL AL GRUPO
-- ═════════════════════════════════════════════════════════════════════════════════════════
--
-- 🔴 SIN `empresa_id` Y SIN `area_id`, y las dos ausencias son la decisión de fondo.
--
-- Un perfil de puesto describe QUÉ hace un "Analista de Datos SSR", y eso no cambia según de qué
-- sociedad del grupo cobre la persona. Si llevara `empresa_id`, RRHH tendría que cargar el mismo
-- perfil una vez por empresa y mantenerlo N veces.
--
-- `area_id` es más sutil y es lo que fuerza la mano: `areas.empresa_id` es NOT NULL, así que un
-- área SIEMPRE pertenece a una empresa. Un perfil con `area_id` quedaría atado a esa empresa por
-- transitividad, y encima chocaría con `trg_emp_vacantes`, que rechaza una vacante cuya área sea
-- de otra empresa. Por eso el área NO se copia: se ELIGE al crear la vacante, y el trigger sigue
-- siendo la red que impide el cruce. Ver §1.2 del diagnóstico.
--
-- Molde: `clientes` después de las migraciones 108/109, que es el otro —y único— catálogo global
-- del sistema. De ahí sale también la forma del índice único.
--
-- QUÉ SE EVALUÓ Y SE DESCARTÓ: reusar `vacantes` con una bandera `es_plantilla`. No sirve.
-- `vacantes.empresa_id` es NOT NULL, `codigo` es NOT NULL con secuencia `VAC-####` y CHECK de
-- formato, y `estado`/`prioridad`/`cantidad_puestos`/`fecha_apertura` no significan nada en una
-- plantilla. Peor: el KPI `vacantes_activas` cuenta `estado <> 'cerrada'`, el Panel de Procesos
-- cuenta `vacantes` por estado y la alerta `sin_vacantes` pregunta por existencia — las
-- plantillas se contarían como búsquedas abiertas en TRES lugares.
--
-- 🔴 SIN visibilidad pública/privada, a diferencia de `onboarding_templates.es_publica`.
-- Decisión de producto: simplicidad. Un perfil es material de consulta del equipo entero.

CREATE TABLE IF NOT EXISTS public.perfiles_puesto (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    -- El nombre del perfil ("Analista de Datos SSR"). Es lo que se elige en el selector y lo que
    -- se copia al `titulo` de la vacante.
    nombre text NOT NULL,
    descripcion text,
    -- Los cinco campos descriptivos que hoy se editan en InformacionPuestoSection sobre la
    -- vacante ya creada. Son los que el perfil llena de una.
    funciones text,
    requisitos text,
    formacion text,
    experiencia text,
    conocimientos_tecnicos text,
    -- Los tres con vocabulario cerrado. Los CHECK se copian LITERALMENTE de `vacantes`: si se
    -- reescribieran "parecido", un perfil podría guardar un valor que la vacante rechaza al
    -- copiarlo, y el error saldría recién al crear la búsqueda.
    modalidad character varying(20),
    tipo_contrato character varying(20),
    nivel character varying(20),
    -- Texto libre, igual que en `vacantes`.
    jornada text,
    -- Baja LÓGICA. Un perfil con vacantes creadas a partir de él no se puede borrar sin perder
    -- la trazabilidad de `vacantes.perfil_puesto_id`. Mismo criterio que `clientes` y
    -- `capacitaciones`.
    activo boolean NOT NULL DEFAULT true,
    created_by uuid,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'perfiles_puesto_pkey') THEN
        ALTER TABLE public.perfiles_puesto ADD CONSTRAINT perfiles_puesto_pkey PRIMARY KEY (id);
    END IF;
END $$;

ALTER TABLE public.perfiles_puesto DROP CONSTRAINT IF EXISTS perfiles_puesto_created_by_fkey;
ALTER TABLE public.perfiles_puesto
    ADD CONSTRAINT perfiles_puesto_created_by_fkey FOREIGN KEY (created_by)
    REFERENCES public.users(id) ON DELETE SET NULL;

-- Los tres CHECK, copiados 1:1 de `vacantes` (leídos del catálogo el 2026-08-13).
ALTER TABLE public.perfiles_puesto DROP CONSTRAINT IF EXISTS perfiles_puesto_modalidad_check;
ALTER TABLE public.perfiles_puesto ADD CONSTRAINT perfiles_puesto_modalidad_check
    CHECK (((modalidad)::text = ANY ((ARRAY['presencial'::character varying, 'remoto'::character varying, 'hibrido'::character varying])::text[])));

ALTER TABLE public.perfiles_puesto DROP CONSTRAINT IF EXISTS perfiles_puesto_tipo_contrato_check;
ALTER TABLE public.perfiles_puesto ADD CONSTRAINT perfiles_puesto_tipo_contrato_check
    CHECK (((tipo_contrato)::text = ANY ((ARRAY['efectivo'::character varying, 'plazo_fijo'::character varying, 'contratado'::character varying, 'pasantia'::character varying])::text[])));

ALTER TABLE public.perfiles_puesto DROP CONSTRAINT IF EXISTS perfiles_puesto_nivel_check;
ALTER TABLE public.perfiles_puesto ADD CONSTRAINT perfiles_puesto_nivel_check
    CHECK (((nivel)::text = ANY ((ARRAY['junior'::character varying, 'semi_senior'::character varying, 'senior'::character varying, 'lider'::character varying, 'manager'::character varying, 'director'::character varying, 'c_level'::character varying])::text[])));

-- 🔴 UNICIDAD GLOBAL Y CASE-INSENSITIVE. El nombre lo escribe RRHH a mano: "Analista SSR" y
-- "analista ssr" son el mismo perfil, y sin `lower()` el catálogo junta duplicados que después
-- nadie sabe cuál usar. Es global (no por empresa) porque la tabla lo es. Molde y motivo
-- idénticos a `ux_clientes_nombre_global`.
-- ⚠️ Un índice por expresión NO sirve como target de `on_conflict` de PostgREST. No importa: un
-- perfil se da de alta con INSERT, nunca con upsert.
CREATE UNIQUE INDEX IF NOT EXISTS ux_perfiles_puesto_nombre_global
    ON public.perfiles_puesto USING btree (lower(nombre));

-- ESCALA: el listado por defecto es `WHERE activo ORDER BY nombre`. Parcial sobre los activos,
-- con `nombre` como clave, así sirve al filtro Y al orden sin ordenar en memoria. Con decenas de
-- perfiles Postgres va a preferir el seq scan igual; con cientos usa este. Cuesta nada y el día
-- que haga falta no hay que coordinar nada.
CREATE INDEX IF NOT EXISTS idx_perfiles_puesto_activos
    ON public.perfiles_puesto USING btree (nombre) WHERE activo;

DROP TRIGGER IF EXISTS trg_perfiles_puesto_updated_at ON public.perfiles_puesto;
CREATE TRIGGER trg_perfiles_puesto_updated_at
    BEFORE UPDATE ON public.perfiles_puesto
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 2. recategorizaciones — el histórico de cambios de rol y seniority por empleado
-- ═════════════════════════════════════════════════════════════════════════════════════════
--
-- 🔴 POR QUÉ UNA TABLA SI LA AUDITORÍA YA GUARDA EL DIFF.
-- `payload_update_empleado` difea TODAS las columnas reales del empleado excluyendo solo tres
-- derivadas de joins, así que un cambio de `roles` o de `seniority` YA queda registrado (95
-- eventos `update_empleado` en producción al 2026-08-12). Lo que la auditoría no puede dar, y no
-- por un ajuste:
--   · el MOTIVO — la auditoría registra un hecho técnico ("este campo pasó de X a Y"); el motivo
--     es un dato de negocio que escribe una persona;
--   · la FECHA EFECTIVA — `auditoria.created_at` dice cuándo se CARGÓ, no desde cuándo RIGE. Una
--     recategorización cargada el 12/8 con efecto desde el 1/7 es indistinguible;
--   · el IMPACTO SALARIAL — vive en otra tabla y detrás de otro permiso (`Seccion.COSTOS`); un
--     evento de `empleado` que lleve un sueldo adentro saltea ese gate;
--   · MUTABILIDAD — `auditoria` es inmutable por diseño, y RRHH necesita poder corregir.
-- Y sobre todo: RRHH necesita una PANTALLA con el historial de una persona, no un log filtrado.
--
-- La auditoría NO se reemplaza: la recategorización escribe en `empleados` por el mismo
-- `update_empleado` de siempre y ese evento se sigue emitiendo. Esta tabla es el registro de
-- NEGOCIO; la auditoría, el registro TÉCNICO. Los dos, y ninguno reemplaza al otro.
--
-- QUÉ MÁS SE EVALUÓ Y SE DESCARTÓ:
--   · `costos_nomina` — es una serie MENSUAL con `UNIQUE (empleado_id, anio, mes)`. Una
--     recategorización no ocurre todos los meses y no es un sueldo.
--   · `planes_carrera` — es un plan a FUTURO (`cargo_objetivo`, `fecha_objetivo`, `progreso`),
--     no un hecho consumado. Además está en 0 filas.
--   · `cesiones` — molde estructural correcto (hija de empleado, hecho puntual, auditada) pero
--     otra semántica. Se copia el patrón, no la tabla.

CREATE TABLE IF NOT EXISTS public.recategorizaciones (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    empleado_id uuid NOT NULL,
    -- 🔴 EDITABLE HACIA ATRÁS, a propósito: una recategorización se carga cuando RRHH se entera,
    -- y rige desde antes. Es la columna por la que se ordena el historial y la que distingue
    -- esta tabla de la auditoría.
    fecha_efectiva date NOT NULL,
    -- ANTES y DESPUÉS. Los "anterior" los completa el sistema leyendo al empleado; los "nuevo"
    -- los carga RRHH. `text` y no `text[]`: lo que interesa del historial es de qué rol a qué
    -- rol pasó, no la lista completa. La app decide de dónde lo lee (`empleados.roles[0]`, que
    -- es el rol vigente — `empleados.cargo` está 0/31 y declarado DEPRECADO).
    rol_anterior text,
    rol_nuevo text,
    seniority_anterior text,
    seniority_nueva text,
    -- NOT NULL: es la razón de ser de la tabla. Una recategorización sin motivo no agrega nada
    -- sobre lo que la auditoría ya guarda.
    motivo text NOT NULL,
    -- Opcional. `numeric` sin precisión, igual que `proyectos.presupuesto` y
    -- `vacantes.rango_salarial_min`. Admite negativo (una recategorización puede bajar).
    impacto_salarial numeric,
    registrado_por uuid,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'recategorizaciones_pkey') THEN
        ALTER TABLE public.recategorizaciones ADD CONSTRAINT recategorizaciones_pkey PRIMARY KEY (id);
    END IF;
END $$;

ALTER TABLE public.recategorizaciones DROP CONSTRAINT IF EXISTS recategorizaciones_empresa_id_fkey;
ALTER TABLE public.recategorizaciones
    ADD CONSTRAINT recategorizaciones_empresa_id_fkey FOREIGN KEY (empresa_id)
    REFERENCES public.empresas(id);

-- 🔴 FK COMPUESTA, NO SIMPLE — y es lo que hace que esta tabla NO necesite un trigger
-- `trg_emp_*`. Una FK simple contra `empleados(id)` garantiza que el empleado existe; NO que sea
-- de la misma empresa que la recategorización. La compuesta lo hace cumplir en la base, y se
-- apoya en el índice `empleados_id_empresa_uq`, que ya existe. Es el patrón de las 22 FKs
-- compuestas del modelo (costos_nomina, empleado_capacitacion, solicitudes_*, ...), y
-- `db/funciones_y_triggers.sql` dice explícitamente que donde está la FK compuesta el trigger
-- sobra. Por eso esta tabla NO se agrega a ese archivo.
ALTER TABLE public.recategorizaciones DROP CONSTRAINT IF EXISTS recat_empleado_empresa_fk;
ALTER TABLE public.recategorizaciones
    ADD CONSTRAINT recat_empleado_empresa_fk FOREIGN KEY (empleado_id, empresa_id)
    REFERENCES public.empleados(id, empresa_id);

ALTER TABLE public.recategorizaciones DROP CONSTRAINT IF EXISTS recategorizaciones_registrado_por_fkey;
ALTER TABLE public.recategorizaciones
    ADD CONSTRAINT recategorizaciones_registrado_por_fkey FOREIGN KEY (registrado_por)
    REFERENCES public.users(id) ON DELETE SET NULL;

-- Ni `rol_nuevo` ni `seniority_nueva` pueden ser NOT NULL por separado: una recategorización
-- puede cambiar solo una de las dos. Pero las dos en NULL es una fila vacía que no dice nada, y
-- eso sí se puede prohibir.
ALTER TABLE public.recategorizaciones DROP CONSTRAINT IF EXISTS recategorizaciones_algo_cambia_check;
ALTER TABLE public.recategorizaciones ADD CONSTRAINT recategorizaciones_algo_cambia_check
    CHECK (rol_nuevo IS NOT NULL OR seniority_nueva IS NOT NULL);

-- ESCALA — los dos índices de esta tabla existen por el volumen, no por prolijidad.
-- Con 1000 colaboradores y una o dos recategorizaciones por persona por año, en cinco años esto
-- son 5.000–10.000 filas. Son las dos únicas consultas que el módulo hace:
--
-- (a) EL HISTORIAL DE UNA PERSONA, en su ficha:
--     WHERE empleado_id = ? ORDER BY fecha_efectiva DESC
CREATE INDEX IF NOT EXISTS idx_recat_empleado
    ON public.recategorizaciones USING btree (empleado_id, fecha_efectiva DESC);

-- (b) EL LISTADO DEL MÓDULO, paginado, por empresa:
--     WHERE empresa_id = ? ORDER BY fecha_efectiva DESC LIMIT ? OFFSET ?
-- 🔴 Este es el que la escala hace obligatorio. Sin él, con 10 empresas cada página del listado
-- lee la tabla entera y la ordena en memoria para devolver 20 filas — y el sort completo se paga
-- de nuevo en CADA página. Con el índice, la paginación es un recorrido.
CREATE INDEX IF NOT EXISTS idx_recat_empresa_fecha
    ON public.recategorizaciones USING btree (empresa_id, fecha_efectiva DESC);

-- SIN índice único, a propósito: dos recategorizaciones del mismo empleado el mismo día son
-- legítimas (una corrección de carga). Y no hay import de esta entidad, así que no hay
-- idempotencia que sostener. ⚠️ Si algún día se importa por Excel, hace falta una clave — es
-- exactamente el problema que documentó la migración 111 para objetivos.

DROP TRIGGER IF EXISTS trg_recategorizaciones_updated_at ON public.recategorizaciones;
CREATE TRIGGER trg_recategorizaciones_updated_at
    BEFORE UPDATE ON public.recategorizaciones
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 3. eventos_agenda — los eventos manuales del calendario del dashboard
-- ═════════════════════════════════════════════════════════════════════════════════════════
--
-- QUÉ SE EVALUÓ Y SE DESCARTÓ, antes de crear una tabla más:
--   · `objetivos` — tiene `titulo` + `fecha_entrega`, pero `responsable_id` es NOT NULL (FK a
--     `users`) y arrastra `estado`, `prioridad`, `parent_id` y el índice único de dedup. Un
--     feriado no tiene responsable. Y contaminaría el tablero de objetivos Y el Panel de
--     Procesos, que cuenta esa tabla por estado.
--   · `periodos_cerrados` — es un bloqueo de escritura por módulo. Semántica opuesta.
--   · `onboarding_tareas` — cuelga de un template y de una instancia. No es una agenda.
--
-- `empresa_id` NOT NULL (decisión de producto). El costo asumido: un feriado nacional se carga
-- una vez por empresa. A cambio, el filtro por empresa es un `.eq()` como en todo el resto del
-- sistema, y no un `.or_(empresa_id.is.null, empresa_id.eq.X)` que sería el único de su clase.

CREATE TABLE IF NOT EXISTS public.eventos_agenda (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    nombre text NOT NULL,
    fecha date NOT NULL,
    descripcion text,
    -- Con cuántos días de anticipación avisa. Default 7 (la semana previa que pidió RRHH). El
    -- valor por defecto para eventos nuevos sale de `parametros_empresa.dias_aviso_evento`
    -- (migración 114); esta columna es el OVERRIDE por evento. Mismo patrón que
    -- `empleados.dias_vacaciones_asignados` contra la regla por antigüedad.
    dias_aviso smallint NOT NULL DEFAULT 7,
    -- 🔴 VISIBILIDAD. `true` = lo ve el equipo; `false` = solo quien lo creó. El nombre es
    -- `es_publica` a propósito: es el mismo que `onboarding_templates.es_publica`, que ya
    -- resuelve esto en el repo y tiene su filtro (`with_visibilidad`) escrito.
    es_publica boolean NOT NULL DEFAULT true,
    -- 🔴 ESTADO DE RESUELTA. Un evento NO desaparece por haber pasado de fecha: desaparece
    -- cuando alguien lo marca. Un aviso que se auto-oculta al vencer es justo el que nadie
    -- atendió.
    resuelta boolean NOT NULL DEFAULT false,
    resuelta_at timestamp with time zone,
    resuelta_por uuid,
    -- NOT NULL: un evento privado sin autor no lo puede ver NADIE — sería una fila inalcanzable.
    -- Sin ON DELETE, igual que `objetivos.responsable_id`: borrar un usuario con eventos se
    -- bloquea, que es la postura que el repo ya tomó para las filas que pertenecen a alguien.
    created_by uuid NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'eventos_agenda_pkey') THEN
        ALTER TABLE public.eventos_agenda ADD CONSTRAINT eventos_agenda_pkey PRIMARY KEY (id);
    END IF;
END $$;

ALTER TABLE public.eventos_agenda DROP CONSTRAINT IF EXISTS eventos_agenda_empresa_id_fkey;
ALTER TABLE public.eventos_agenda
    ADD CONSTRAINT eventos_agenda_empresa_id_fkey FOREIGN KEY (empresa_id)
    REFERENCES public.empresas(id);

ALTER TABLE public.eventos_agenda DROP CONSTRAINT IF EXISTS eventos_agenda_created_by_fkey;
ALTER TABLE public.eventos_agenda
    ADD CONSTRAINT eventos_agenda_created_by_fkey FOREIGN KEY (created_by)
    REFERENCES public.users(id);

ALTER TABLE public.eventos_agenda DROP CONSTRAINT IF EXISTS eventos_agenda_resuelta_por_fkey;
ALTER TABLE public.eventos_agenda
    ADD CONSTRAINT eventos_agenda_resuelta_por_fkey FOREIGN KEY (resuelta_por)
    REFERENCES public.users(id) ON DELETE SET NULL;

ALTER TABLE public.eventos_agenda DROP CONSTRAINT IF EXISTS eventos_agenda_dias_aviso_check;
ALTER TABLE public.eventos_agenda ADD CONSTRAINT eventos_agenda_dias_aviso_check
    CHECK (dias_aviso >= 0 AND dias_aviso <= 365);

-- Coherencia: si está resuelta, tiene que decir CUÁNDO. Sin esto, "resuelta" sin fecha deja el
-- panel sin poder explicar por qué un evento dejó de aparecer.
-- ⚠️ El chequeo NO toca `resuelta_por`, que sí puede quedar en NULL: su FK es ON DELETE SET NULL,
-- así que borrar al usuario que resolvió el evento pondría NULL ahí y un CHECK sobre esa columna
-- haría FALLAR ese DELETE.
ALTER TABLE public.eventos_agenda DROP CONSTRAINT IF EXISTS eventos_agenda_resuelta_coherente_check;
ALTER TABLE public.eventos_agenda ADD CONSTRAINT eventos_agenda_resuelta_coherente_check
    CHECK (NOT resuelta OR resuelta_at IS NOT NULL);

-- ESCALA — la consulta caliente es la del dashboard, y corre en CADA carga de pantalla:
--     WHERE empresa_id = ? AND NOT resuelta AND fecha <= current_date + dias_aviso
-- 🔴 PARCIAL SOBRE `NOT resuelta`, y ahí está el punto: los eventos resueltos se acumulan para
-- siempre y el dashboard NO los mira nunca. Con 10 empresas y varios años, el índice completo
-- crecería sin techo mientras la parte útil se mantiene en decenas de filas. El parcial indexa
-- solo lo pendiente.
CREATE INDEX IF NOT EXISTS idx_eventos_agenda_pendientes
    ON public.eventos_agenda USING btree (empresa_id, fecha) WHERE NOT resuelta;

-- ESCALA — el segundo predicado de la visibilidad: `es_publica OR created_by = <yo>`. Los
-- públicos ya entran por el índice de arriba; este sirve la otra mitad. Parcial sobre las
-- privadas, que son la minoría.
CREATE INDEX IF NOT EXISTS idx_eventos_agenda_privados_autor
    ON public.eventos_agenda USING btree (created_by) WHERE NOT es_publica;

DROP TRIGGER IF EXISTS trg_eventos_agenda_updated_at ON public.eventos_agenda;
CREATE TRIGGER trg_eventos_agenda_updated_at
    BEFORE UPDATE ON public.eventos_agenda
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 4. empleados — fechas PREVISTAS de ingreso y de baja
-- ═════════════════════════════════════════════════════════════════════════════════════════
--
-- 🔴 SE AGREGAN DOS COLUMNAS Y **NO SE TOCA EL CHECK DE `empleados.estado`**. Decisión tomada,
-- y el motivo es de radio: `estado` gobierna 17 lugares del backend, de los cuales DOS cuentan
-- de más (`area_repo._counts_by_area` y `sucesion_repo`, los dos con `.neq('estado','baja')` —
-- o sea "todo lo que no es baja es headcount"). Un valor nuevo en el CHECK los rompe en
-- SILENCIO: un preingreso pasaría a contar como dotación sin que nada falle. Con fechas
-- previstas, esos 17 sitios no se enteran y siguen siendo correctos.
--
-- SEMÁNTICA, que es lo que las hace útiles: `fecha_ingreso` es la EFECTIVA (cuándo empieza a
-- trabajar) y ya existe; estas dos son las del TRÁMITE. El trámite arranca el 1/1 y la persona
-- entra el 15/1; o se va el 1/1 y el trámite cierra el 15/1.
--
-- ⚠️ NO duplican a `offboarding_instancias`, que YA tiene `fecha_notificacion` (aviso) y
-- `fecha_ultimo_dia` (último día real). Esa tabla modela el PROCESO de salida; esta columna vive
-- en el legajo para que el listado y el dashboard puedan mirar "quién se va pronto" sin joinear
-- contra el offboarding. Cuál manda cuando las dos existen es decisión de la capa de servicio,
-- no de la base.

ALTER TABLE public.empleados ADD COLUMN IF NOT EXISTS fecha_ingreso_prevista date;
ALTER TABLE public.empleados ADD COLUMN IF NOT EXISTS fecha_baja_prevista date;

-- ESCALA — la consulta del dashboard es "próximos ingresos / próximas bajas de los próximos N
-- días", y corre con el padrón entero detrás:
--     WHERE fecha_ingreso_prevista BETWEEN current_date AND current_date + N
-- 🔴 PARCIALES, y con 1000 colaboradores la diferencia es el punto: en cualquier momento hay un
-- puñado de personas con ingreso previsto y 990 con NULL. Un índice completo indexaría las 1000
-- filas para servir 10, y sin ningún índice el bloque del dashboard escanea el padrón en cada
-- carga, por empresa. Mismo patrón que `idx_empleados_domicilio_provincia`, que ya vive acá.
-- No llevan `empresa_id` adelante a propósito: el predicado parcial ya reduce a decenas de
-- filas, y con `empresa_id` primero el índice dejaría de servir a la vista consolidada.
CREATE INDEX IF NOT EXISTS idx_empleados_ingreso_previsto
    ON public.empleados USING btree (fecha_ingreso_prevista) WHERE (fecha_ingreso_prevista IS NOT NULL);

CREATE INDEX IF NOT EXISTS idx_empleados_baja_prevista
    ON public.empleados USING btree (fecha_baja_prevista) WHERE (fecha_baja_prevista IS NOT NULL);


-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 5. adjuntos — fecha de vencimiento del documento
-- ═════════════════════════════════════════════════════════════════════════════════════════
--
-- Es lo que falta para la alerta "documentos próximos a vencer" del dashboard: hoy `adjuntos`
-- tiene 15 columnas y NINGUNA fecha que no sea `created_at` (verificado en el catálogo).
--
-- ⚠️ LO QUE ESTA COLUMNA **NO** RESUELVE, y hay que decirlo: la alerta solo va a poder avisar de
-- los documentos que alguien cargó CON fecha, nunca de los que FALTAN. Para eso haría falta un
-- catálogo de tipos de documento obligatorios, y hoy `adjuntos.categoria` es texto libre sin
-- CHECK ni tabla (el único adjunto de producción la tiene en NULL). Ese catálogo es una decisión
-- de producto pendiente, no una columna.

ALTER TABLE public.adjuntos ADD COLUMN IF NOT EXISTS fecha_vencimiento date;

-- ESCALA — con 1000 colaboradores y varios documentos por persona, `adjuntos` es de las tablas
-- que más crece. La consulta de la alerta es:
--     WHERE fecha_vencimiento BETWEEN current_date AND current_date + N AND estado = 'activo'
-- 🔴 DOBLEMENTE PARCIAL. La mayoría de los adjuntos (un CV, una foto) no vence nunca, así que
-- `fecha_vencimiento IS NOT NULL` ya recorta casi todo; y `estado = 'activo'` saca los eliminados,
-- que no tienen por qué alertar. El índice queda en el orden de decenas de filas sobre una tabla
-- que va a tener decenas de miles.
-- ⚠️ El predicado `estado = 'activo'` es parte del índice: la query de la alerta TIENE que
-- incluirlo o el planner no lo va a poder usar.
CREATE INDEX IF NOT EXISTS idx_adjuntos_vencimiento
    ON public.adjuntos USING btree (fecha_vencimiento)
    WHERE (fecha_vencimiento IS NOT NULL AND estado = 'activo');


-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 6. vacantes — de qué perfil de puesto salió
-- ═════════════════════════════════════════════════════════════════════════════════════════
--
-- Trazabilidad: sin esta columna no se puede responder "¿cuántas búsquedas salieron de este
-- perfil?", que es la única métrica que justifica mantener el catálogo.
--
-- `ON DELETE SET NULL`: borrar un perfil (si alguna vez se hace físico, hoy la baja es lógica) no
-- puede llevarse la vacante. La vacante ya copió los campos y es independiente — ese es el punto
-- del modelo de COPIA.
--
-- ⚠️ NO lleva trigger `fn_misma_empresa`: `perfiles_puesto` no tiene `empresa_id`, así que no hay
-- cruce de empresa que vigilar. Es la misma situación que `horas_proyecto.cliente_id` después de
-- que la 109 volviera global a `clientes`.

ALTER TABLE public.vacantes ADD COLUMN IF NOT EXISTS perfil_puesto_id uuid;

ALTER TABLE public.vacantes DROP CONSTRAINT IF EXISTS vacantes_perfil_puesto_id_fkey;
ALTER TABLE public.vacantes
    ADD CONSTRAINT vacantes_perfil_puesto_id_fkey FOREIGN KEY (perfil_puesto_id)
    REFERENCES public.perfiles_puesto(id) ON DELETE SET NULL;

-- ESCALA — dos motivos, y el segundo es el que lo vuelve obligatorio:
-- (a) la consulta "vacantes de este perfil": WHERE perfil_puesto_id = ?
-- (b) 🔴 POSTGRES NO INDEXA LAS FK AUTOMÁTICAMENTE. Con `ON DELETE SET NULL`, borrar un perfil
--     obliga a la base a buscar las filas hijas: sin índice, eso es un scan de `vacantes` entera
--     por cada borrado. Con 10 empresas y años de búsquedas, esa tabla no es chica.
-- Parcial: las vacantes anteriores a la feature —y las que se creen a mano— tienen NULL acá.
CREATE INDEX IF NOT EXISTS idx_vacantes_perfil_puesto
    ON public.vacantes USING btree (perfil_puesto_id) WHERE (perfil_puesto_id IS NOT NULL);

COMMIT;


-- ═════════════════════════════════════════════════════════════════════════════════════════
-- VERIFICACIÓN POSTERIOR — correr DESPUÉS, a mano. Nada de esto lo hace la migración.
-- ═════════════════════════════════════════════════════════════════════════════════════════
--
-- 1. Las tres tablas existen y el conteo total subió de 52 a 55:
--
--    SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';
--    -- ESPERADO: 55
--    SELECT table_name FROM information_schema.tables
--     WHERE table_schema = 'public'
--       AND table_name IN ('perfiles_puesto','recategorizaciones','eventos_agenda')
--     ORDER BY 1;
--    -- ESPERADO: las tres.
--
-- 2. Las tres columnas nuevas sobre tablas existentes:
--
--    SELECT table_name, column_name, data_type, is_nullable
--      FROM information_schema.columns
--     WHERE table_schema = 'public'
--       AND (table_name, column_name) IN (
--             ('empleados','fecha_ingreso_prevista'), ('empleados','fecha_baja_prevista'),
--             ('adjuntos','fecha_vencimiento'),       ('vacantes','perfil_puesto_id'))
--     ORDER BY 1, 2;
--    -- ESPERADO: 4 filas, todas is_nullable = YES.
--
-- 3. Los tres triggers `updated_at` nuevos (35 -> 38):
--
--    SELECT count(*) FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid
--     WHERE p.proname = 'set_updated_at' AND NOT t.tgisinternal;
--    -- ESPERADO: 38
--
-- 4. Los 8 índices nuevos:
--
--    SELECT tablename, indexname FROM pg_indexes
--     WHERE schemaname = 'public'
--       AND indexname IN ('ux_perfiles_puesto_nombre_global','idx_perfiles_puesto_activos',
--                         'idx_recat_empleado','idx_recat_empresa_fecha',
--                         'idx_eventos_agenda_pendientes','idx_eventos_agenda_privados_autor',
--                         'idx_empleados_ingreso_previsto','idx_empleados_baja_prevista',
--                         'idx_adjuntos_vencimiento','idx_vacantes_perfil_puesto')
--     ORDER BY 1, 2;
--    -- ESPERADO: 10 filas (8 nuevos + los 2 de empleados).
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 5. 🔴 LA PRUEBA QUE IMPORTA — QUE EL ÍNDICE ÚNICO FUNCIONE. Hace ROLLBACK: no deja nada.
-- ─────────────────────────────────────────────────────────────────────────────────────────
--
--    BEGIN;
--    INSERT INTO perfiles_puesto (nombre) VALUES ('Analista de Datos SSR');
--    INSERT INTO perfiles_puesto (nombre) VALUES ('ANALISTA DE DATOS SSR');
--    -- ESPERADO: el SEGUNDO falla con
--    --   ERROR 23505 duplicate key value violates unique constraint
--    --               "ux_perfiles_puesto_nombre_global"
--    -- El cambio de mayúsculas es a propósito: prueba de una sola vez la unicidad Y que sea
--    -- case-insensitive. Si entra, o el índice no está o le falta el lower().
--    ROLLBACK;
--
-- 6. 🔴 EL CONTRASTE — un nombre DISTINTO SÍ tiene que entrar. Sin esta prueba, un índice
--    demasiado ancho (por ejemplo sobre `lower(nombre)` truncado, o sobre una columna de más)
--    pasaría la prueba 5 y estaría rechazando datos buenos sin que nadie lo note.
--
--    BEGIN;
--    INSERT INTO perfiles_puesto (nombre) VALUES ('Analista de Datos SSR');
--    INSERT INTO perfiles_puesto (nombre) VALUES ('Analista de Datos SR');
--    -- ESPERADO: los dos entran sin error.
--    ROLLBACK;
--
-- 7. La FK COMPUESTA de recategorizaciones rechaza el cruce de empresa. Es la constraint que
--    reemplaza al trigger, así que hay que verla fallar. Usa los datos que ya existen.
--
--    BEGIN;
--    -- Empleado de una empresa, empresa_id de OTRA:
--    INSERT INTO recategorizaciones (empresa_id, empleado_id, fecha_efectiva, rol_nuevo, motivo)
--    SELECT (SELECT id FROM empresas WHERE id <> e.empresa_id LIMIT 1), e.id,
--           current_date, 'Analista SR', 'prueba'
--      FROM empleados e LIMIT 1;
--    -- ESPERADO: falla con
--    --   ERROR 23503 insert or update on table "recategorizaciones" violates foreign key
--    --               constraint "recat_empleado_empresa_fk"
--    ROLLBACK;
--
-- 8. El contraste de la 7: con la empresa CORRECTA sí entra.
--
--    BEGIN;
--    INSERT INTO recategorizaciones (empresa_id, empleado_id, fecha_efectiva, rol_nuevo, motivo)
--    SELECT e.empresa_id, e.id, current_date, 'Analista SR', 'prueba' FROM empleados e LIMIT 1;
--    -- ESPERADO: entra sin error.
--    ROLLBACK;
--
-- 9. El CHECK de "algo tiene que cambiar" en recategorizaciones:
--
--    BEGIN;
--    INSERT INTO recategorizaciones (empresa_id, empleado_id, fecha_efectiva, motivo)
--    SELECT e.empresa_id, e.id, current_date, 'prueba sin cambios' FROM empleados e LIMIT 1;
--    -- ESPERADO: falla con
--    --   ERROR 23514 new row violates check constraint "recategorizaciones_algo_cambia_check"
--    ROLLBACK;
--
-- 10. El CHECK de coherencia de eventos_agenda (resuelta sin fecha):
--
--    BEGIN;
--    INSERT INTO eventos_agenda (empresa_id, nombre, fecha, created_by, resuelta)
--    SELECT (SELECT id FROM empresas LIMIT 1), 'prueba', current_date,
--           (SELECT id FROM users LIMIT 1), true;
--    -- ESPERADO: falla con
--    --   ERROR 23514 new row violates check constraint "eventos_agenda_resuelta_coherente_check"
--    ROLLBACK;
--
-- 11. El contraste de la 10: sin resolver entra, y resuelta CON fecha también.
--
--    BEGIN;
--    INSERT INTO eventos_agenda (empresa_id, nombre, fecha, created_by)
--    SELECT (SELECT id FROM empresas LIMIT 1), 'prueba', current_date, (SELECT id FROM users LIMIT 1);
--    INSERT INTO eventos_agenda (empresa_id, nombre, fecha, created_by, resuelta, resuelta_at)
--    SELECT (SELECT id FROM empresas LIMIT 1), 'prueba 2', current_date,
--           (SELECT id FROM users LIMIT 1), true, now();
--    -- ESPERADO: los dos entran sin error.
--    ROLLBACK;
--
-- 12. Que NO se haya tocado nada de lo que ya estaba. El CHECK de estado sigue con sus 4 valores:
--
--    SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'empleados_estado_check';
--    -- ESPERADO: activo, baja, licencia, suspendido. NI UNO MÁS.
--
--    SELECT count(*) FROM empleados;   -- ESPERADO: el mismo de antes (31 al 2026-08-13)
--    SELECT count(*) FROM vacantes;    -- ESPERADO: el mismo de antes (1)
--    SELECT count(*) FROM adjuntos;    -- ESPERADO: el mismo de antes (1)

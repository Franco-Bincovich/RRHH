-- ============================================================================
-- schema.sql — SNAPSHOT DE RECONSTRUCCION de la base de produccion (RRHH / HR Karstec)
-- ============================================================================
--
-- ESTE ES EL ARTEFACTO DE RECONSTRUCCION AUTORITATIVO.
-- Declara el SCHEMA OBJETIVO, leido del catalogo de Postgres (information_schema / pg_catalog).
-- Incluye TODO: tablas, columnas, defaults, constraints (PK/FK/UNIQUE/CHECK, incluidas las
-- compuestas del modelo multiempresa), e indices.
--
-- ⚠️ "OBJETIVO", NO "ESPEJO": entre que se escribe una migracion y que alguien la corre contra
-- Supabase, este archivo VA POR DELANTE de produccion. Es lo normal y no se documenta caso por
-- caso — el porque, y como averiguar si produccion ya lo tiene, estan en el bloque de abajo.
--
-- POR QUE EXISTE:
-- Las migraciones incrementales de `backend/migrations/` NO reconstruyen la base desde cero
-- de forma confiable: tienen dependencias de orden rotas, operaciones no
-- idempotentes, y parte del modelo multiempresa fue aplicado a mano en produccion
-- (drift) y versionado retroactivamente de forma incompleta. Las migraciones
-- quedan como HISTORIAL de como se llego hasta aca; este schema.sql es la fuente
-- de verdad para RECONSTRUIR.
--
-- COMO SE GENERO: leido del catalogo de la base de produccion via el catalogo de
-- Postgres. Generado: 2026-07-16 (cubre hasta la migracion 074).
--
-- CONTENIDO VERIFICADO CONTRA EL CATALOGO VIVO el 2026-08-07 (proyecto
-- grmdiwxcvcjorlohpwji), ya con las migraciones 075..093 corridas: 58 tablas,
-- 698 columnas, 153 FKs, 103 CHECKs y los 151 indices standalone coincidian
-- EXACTAMENTE, sin fantasmas ni faltantes en ninguna de las dos direcciones.
-- O sea: el archivo se regenero despues del 16/7 y solo la fecha de arriba quedo
-- vieja.
-- 🔄 ESOS NUMEROS SON DEL 7/8 Y YA NO SON LOS DE HOY. Quedan como registro de que la
-- verificacion se hizo, no como descripcion del archivo: ver el bloque de abajo sobre por que
-- ningun numero de este encabezado se puede leer como estado vigente.
--
-- ═════════════════════════════════════════════════════════════════════════════
-- 🔴 ESTE ENCABEZADO YA NO LLEVA LISTA DE MIGRACIONES PENDIENTES. NO LA VUELVAS A ESCRIBIR.
-- ═════════════════════════════════════════════════════════════════════════════
--
-- Hasta el 2026-08-17 este bloque enumeraba "migraciones corridas" y "pendientes de correr".
-- **Se desfaso CINCO veces**, en las dos direcciones, y las cinco por la misma causa: es un dato
-- que cambia cuando alguien corre un script contra Supabase, y este archivo no se entera. Se
-- mantenia a mano y se leia como autoridad.
--
--   1. Decia "va por delante" cuando ya no era cierto: las migraciones se habian corrido y nadie
--      volvio a tocar el archivo.
--   2. Lo mismo con la 112, cuatro dias despues de que corriera.
--   3. Al arreglar (2) se marco "AL DIA, 108..112 todas corridas" verificando SOLO EL CONTEO DE
--      TABLAS (52 = 52). La 109 estaba pendiente: no crea ni borra tablas (borra una columna y
--      tres objetos), asi que era invisible a esa comprobacion.
--   4. La 116 quedo listada como pendiente DESPUES de haberse corrido, por lo mismo: son 11
--      columnas, un DROP NOT NULL y un indice, y "55 = 55" no los ve.
--   5. La 117 y la 118 quedaron listadas como pendientes despues de haberse corrido, y esta vez
--      ni siquiera hubo un conteo de por medio: **se heredo la afirmacion del texto anterior sin
--      verificarla**, en la misma sesion en la que si se verifico objeto por objeto lo de la 119.
--      Es la variante mas facil de repetir — el que edita el bloque toca su parrafo y da por
--      buenos los de al lado.
--
-- 🔴 POR QUE SE SACO Y NO SE "MANTIENE MEJOR". Este archivo es el ARTEFACTO DE RECONSTRUCCION:
-- describe UN SCHEMA. "Que migraciones estan aplicadas" describe OTRA COSA — el estado de un
-- despliegue concreto — que cambia sin que este archivo cambie, y que **no se puede verificar
-- leyendo el archivo**. Dos hechos con ciclos de vida distintos en un mismo documento: el que no
-- se puede chequear desde adentro es el que rota. Un dato que no se puede verificar
-- automaticamente no deberia estar escrito como autoridad, y menos en el archivo del que el dev
-- de infra levanta RDS: si dice que una migracion esta pendiente, la corre de nuevo.
--
-- ⚠️ SE EVALUO Y SE DESCARTO la otra salida: un test que compare este archivo contra el catalogo.
-- Es la correcta, pero **necesita una base en CI y hoy no hay** (la suite corre con un fake de
-- Supabase; ver tests/_postgrest_schema.py, que valida contra ESTE archivo justamente porque no
-- puede consultar la base). Queda anotado con su disparador: **el dia que el pipeline de AWS
-- tenga una base efimera, ese chequeo entra ahi** — es el unico lugar donde puede no mentir.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- COMO SE CONTESTA HOY "¿ESTE ARCHIVO REFLEJA PRODUCCION O VA POR DELANTE?"
-- ─────────────────────────────────────────────────────────────────────────────
-- Se le pregunta al catalogo, que es lo unico que no miente. Tres pasos, en este orden:
--
-- 1. QUE MIGRACIONES HAY. `ls backend/migrations/` — el numero mas alto es el ultimo escrito.
--    Cuales de esas se corrieron NO esta escrito en ningun lado del repo, a proposito (es lo que
--    se acaba de sacar de aca). Lo que si hay es el registro DATADO de cuando se escribio cada
--    una: `docs/BITACORA-CAMBIOS.md`, una entrada por sesion, de la mas reciente a la mas vieja.
--    🔑 Esa bitacora no rota y este bloque si, y la diferencia es de FORMA, no de disciplina: una
--    entrada fechada dice "el 17/8 escribi la 119 y quedo pendiente", y eso sigue siendo verdad
--    para siempre. Un encabezado que dice "pendiente" es falso apenas alguien la corre.
--
-- 2. SI ESA MIGRACION YA CORRIO. **Se mira EL OBJETO QUE TOCA, nunca un conteo.** No hace falta
--    inventar la query: **cada migracion de este repo termina en un bloque "VERIFICACION
--    POSTERIOR" con la consulta exacta y el resultado esperado**, escrito por quien la penso y
--    guardado al lado del DDL que describe. Ese bloque no puede desfasarse del objeto, porque
--    viven en el mismo archivo. Abrir la migracion y correr su bloque es la respuesta.
--    🔴 CONTAR NO ALCANZA, y los casos 3 y 4 de arriba son la prueba: la mayoria de las
--    migraciones no crea ni borra tablas, asi que "N = N" pasa igual con la migracion sin correr.
--
-- 3. 🚨 NO USAR `supabase_migrations.schema_migrations`. Existe, y es una TRAMPA: verificado el
--    17/8, tiene **UNA sola fila** (`081_add_domicilio_desglosado`), porque es el ledger del CLI
--    de Supabase y aca las migraciones se corren a mano desde el SQL editor, que no registra
--    nada. Leerla lleva a concluir que solo corrio la 081 de 119. No es un ledger de este repo.
--    (Las otras dos `schema_migrations` del catalogo, en `auth` y en `realtime`, son internas de
--    Supabase y menos que menos.)
--
-- ─────────────────────────────────────────────────────────────────────────────
-- 🚩 LA REGLA QUE QUEDA, y es la unica
-- ─────────────────────────────────────────────────────────────────────────────
-- Al escribir una migracion nueva se actualiza ESTE ARCHIVO con lo que la migracion declara
-- —columnas, constraints, indices— en la MISMA sesion, igual que la entrada de la bitacora. Eso
-- es todo. **No se anota si esta corrida o no**: este archivo declara el schema OBJETIVO, y que
-- vaya por delante de produccion durante unos dias es lo normal, no una excepcion que haya que
-- documentar cada vez.
-- Corolario: si estas leyendo esto y necesitas saber si produccion ya lo tiene, la respuesta no
-- esta en este archivo — esta en el catalogo, por los tres pasos de arriba.
--
-- ⚠️ Y si igual vas a escribir un estado acá: no toques SOLO tu parrafo. El desfasaje 5 fue
-- exactamente eso.
--
-- COMO USARLO EN UN REBUILD:
--   1. Crear una base vacia.
--   2. psql -v ON_ERROR_STOP=1 -f db/schema.sql
--   3. psql -v ON_ERROR_STOP=1 -f db/funciones_y_triggers.sql
--   4. psql -v ON_ERROR_STOP=1 -f migracionAWS/backend/migrations/077_recrear_triggers_updated_at.sql
--   5. psql -v ON_ERROR_STOP=1 -f db/seed.sql
-- Los cuatro tienen que dar exit 0. La secuencia completa, con el porque de cada
-- paso, esta en docs/handoff-aws/README.md.
-- 🔴 NO correr NINGUNA de las migraciones de `backend/migrations/` encima: son HISTORIAL, no
-- bootstrap. (El rango se escribia aca como "001..112" y quedo viejo dos veces; no lleva numero
-- a proposito — son todas.)
--
-- NOTA: no incluye datos (solo estructura). Los catalogos base van en db/seed.sql.
--
-- ── AUTENTICACION: LO UNICO DE ESTE ARCHIVO QUE NO REFLEJA PRODUCCION ─────────
-- 🔴 SE SACO LA FK `users.id -> auth.users(id) ON DELETE CASCADE` Y SE LE PUSO A
-- `users.id` UN DEFAULT gen_random_uuid(). Era la UNICA referencia a un esquema de
-- Supabase que quedaba, y el UNICO bloqueante del replay: en RDS no existe el
-- schema `auth` y esa linea aborta el script entero.
--
-- 🚨 ESTO NO ES UNA MIGRACION Y NO TOCA SUPABASE. Este archivo es el ARTEFACTO DE
-- RECONSTRUCCION: describe la base que se levanta en RDS, no la que hoy sirve
-- trafico. En produccion la FK sigue existiendo y se queda ahi. Nadie tiene que
-- correr nada contra Supabase por este cambio.
--
-- QUIEN GENERA EL ID, verificado en el codigo (services/_usuario_alta.py:74-90):
-- hoy lo genera SUPABASE AUTH (`supabase_admin.auth.admin.create_user`) y la app lo
-- pasa EXPLICITO en el INSERT (`"id": uid`). O sea que el DEFAULT no cambia el
-- comportamiento actual —el INSERT siempre trae el id, el DEFAULT nunca se usa—;
-- solo habilita el INSERT sin `id`, que es lo que hara falta del otro lado.
--
-- LO QUE SI SE PIERDE CON LA FK, y hay que reponer en la app del destino:
--   - el ON DELETE CASCADE que borraba el perfil al borrar la identidad. En el alta
--     hay un rollback (`_rollback_auth`) que HOY se apoya en ese cascade.
--   - la garantia de que todo `users.id` corresponde a una identidad real.
-- El destino ya tiene su propio auth (migracionAWS: 075 password_hash, 076
-- refresh_tokens), asi que la FK no tendria a que apuntar.
--
-- 🔴 TAMPOCO INCLUYE FUNCIONES NI TRIGGERS: el catalogo se leyo para tablas,
-- columnas, constraints, indices y defaults. Con el lote 113 corrido produccion va
-- a tener 46 triggers no internos y este archivo trae 0. Se recrean aparte, con los
-- pasos 3 y 4 de arriba:
--   - los 38 de updated_at  -> migracionAWS/backend/migrations/077_recrear_triggers_updated_at.sql
--     (35 + los 3 de las tablas nuevas del lote 113)
--   - los 8  trg_emp_*      -> db/funciones_y_triggers.sql
-- ⚠️ NO se usa `backend/migrations/094_recrear_triggers_empresa.sql`. Ese archivo se
-- CORRIGIO el 2026-08-13 —se le saco el noveno trigger, sobre `sucesion_posiciones`,
-- tabla que la 112 dropeo y que hacia abortar el script— pero sigue sin ser el camino
-- de reconstruccion: queda como historial, y el rebuild mira db/funciones_y_triggers.sql.
--
-- ⚠️ NINGUNA de las tres tablas nuevas del lote 113 lleva trigger `trg_emp_*`, y no es
-- un olvido: `perfiles_puesto` no tiene empresa_id (es global), `eventos_agenda` solo
-- referencia a `users` (que no tiene empresa) y `recategorizaciones` usa una FK
-- COMPUESTA contra empleados(id, empresa_id), que hace cumplir lo mismo con una
-- constraint. Es lo que db/funciones_y_triggers.sql declara: donde esta la FK
-- compuesta, el trigger sobra.
-- ============================================================================

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

-- Extension para gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================================
-- SECUENCIAS (las que NO crea un serial/identity)
-- ============================================================================

-- Contador del codigo de vacante (VAC-0001). Va antes de las tablas porque el DEFAULT de
-- vacantes.codigo la referencia. Migracion 097.
CREATE SEQUENCE IF NOT EXISTS public.vacantes_codigo_seq AS BIGINT START WITH 1 INCREMENT BY 1;

-- ============================================================================
-- TABLAS
-- ============================================================================

CREATE TABLE public.adjuntos (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    entidad text NOT NULL,
    entidad_id uuid NOT NULL,
    empresa_id uuid,
    bucket text NOT NULL DEFAULT 'documentos'::text,
    storage_path text NOT NULL,
    nombre_archivo text NOT NULL,
    mime_type text,
    tamano_bytes bigint,
    categoria text,
    descripcion text,
    estado text NOT NULL DEFAULT 'activo'::text,
    subido_por uuid,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    es_principal boolean DEFAULT false,
    -- Migracion 113. Alimenta la alerta "documentos proximos a vencer". NO resuelve "que
    -- documentos FALTAN": para eso haria falta un catalogo de tipos obligatorios, y `categoria`
    -- es texto libre sin CHECK.
    fecha_vencimiento date
);
CREATE TABLE public.areas (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    nombre character varying(100) NOT NULL,
    codigo character varying(20),
    descripcion text,
    area_padre_id uuid,
    responsable_id uuid,
    nivel smallint NOT NULL DEFAULT 1,
    activo boolean NOT NULL DEFAULT true,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    empresa_id uuid NOT NULL
);
CREATE TABLE public.assessment_campanas (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    nombre character varying(150) NOT NULL,
    descripcion text,
    tipo character varying(20) NOT NULL,
    subtipo character varying(50),
    configuracion jsonb NOT NULL DEFAULT '{}'::jsonb,
    estado character varying(20) NOT NULL DEFAULT 'borrador'::character varying,
    fecha_inicio date,
    fecha_fin date,
    created_by uuid,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    area_id uuid,
    posicion_objetivo character varying(200),
    empresa_id uuid NOT NULL
);
CREATE TABLE public.assessment_links (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    campana_id uuid NOT NULL,
    empleado_id uuid,
    candidato_id uuid,
    token character varying(100) NOT NULL DEFAULT encode(gen_random_bytes(32), 'hex'::text),
    email_destino character varying(255) NOT NULL,
    nombre_destino character varying(200),
    estado character varying(20) NOT NULL DEFAULT 'pendiente'::character varying,
    expira_en timestamp with time zone NOT NULL DEFAULT (now() + '7 days'::interval),
    enviado_en timestamp with time zone,
    abierto_en timestamp with time zone,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    empresa_id uuid NOT NULL
);
CREATE TABLE public.assessment_resultados (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    link_id uuid NOT NULL,
    campana_id uuid NOT NULL,
    empleado_id uuid,
    candidato_id uuid,
    respuestas jsonb NOT NULL DEFAULT '{}'::jsonb,
    puntuacion jsonb,
    perfil_resultado jsonb,
    tiempo_total_segundos integer,
    completado_en timestamp with time zone,
    ip_completion inet,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    empresa_id uuid NOT NULL
);
CREATE TABLE public.auditoria (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tabla character varying(100) NOT NULL,
    registro_id uuid NOT NULL,
    accion character varying(10) NOT NULL,
    datos_anteriores jsonb,
    datos_nuevos jsonb,
    usuario_id uuid,
    ip inet,
    user_agent text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    empresa_id uuid,
    entidad character varying(50),
    evento character varying(60)
);
CREATE TABLE public.candidatos (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    vacante_id uuid,
    nombre character varying(100) NOT NULL,
    apellido character varying(100) NOT NULL,
    email character varying(255) NOT NULL,
    telefono character varying(30),
    cv_url text,
    cv_storage_path text,
    linkedin_url text,
    fuente character varying(30),
    etapa character varying(30) NOT NULL DEFAULT 'postulado'::character varying,
    estado character varying(20) NOT NULL DEFAULT 'activo'::character varying,
    notas text,
    puntuacion smallint,
    entrevistador_id uuid,
    fecha_postulacion date NOT NULL DEFAULT CURRENT_DATE,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    cargo_anterior character varying(200),
    empresa_anterior character varying(200),
    score_ia numeric(4,2),
    empresa_id uuid NOT NULL,
    busqueda_congelada text,
    -- Identidad del CV que entro por mail (mig 098). Nullable: los candidatos cargados a mano
    -- no la tienen. La clave de idempotencia es el HASH del contenido y NO el attachmentId de
    -- Gmail, que no es estable entre lecturas del mismo mensaje.
    gmail_message_id text,
    cv_sha256 text,
    -- Texto plano extraido del CV y el POR QUE no se pudo (mig 099). El warning es texto y no un
    -- flag: cada motivo pide una accion distinta (pedir la contrasena, pedirlo en otro formato).
    cv_texto text,
    screening_warning text,
    -- Filtro de descarte del screening (mig 100): relevante | dudoso | no_relevante. NULL = sin
    -- clasificar. NO es una decision: un humano revisa siempre, incluidos los no_relevante.
    clasificacion_ia text,
    clasificacion_motivo text,
    -- Quien puso la clasificacion vigente: modelo | humano (mig 101). NULL = no hay
    -- clasificacion. El veredicto ORIGINAL del modelo, cuando un humano lo pisa, queda en
    -- datos_anteriores del evento correccion_clasificacion.
    clasificacion_origen text
);
CREATE TABLE public.capacitaciones (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    nombre text NOT NULL,
    descripcion text,
    categoria text,
    duracion_horas numeric,
    entidad_capacitadora text,
    modalidad text,
    tipo text,
    obligatoria boolean NOT NULL DEFAULT false,
    activo boolean NOT NULL DEFAULT true,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.cesiones (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empleado_id uuid NOT NULL,
    empresa_id uuid NOT NULL,
    fecha date NOT NULL,
    empresa_cesion text NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);
-- Catalogo GLOBAL de clientes (migracion 102, sin empresa desde la 109). Es de quien depende
-- cada carga de horas del modulo nuevo. NO tiene relacion con `proyectos`: ese flujo no participa.
-- Un cliente NO pertenece a ninguna empresa: se ve, se crea y se da de baja con el selector del
-- sidebar en cualquier modo, y cualquier empleado imputa horas contra cualquiera. Revierte la
-- decision de la 102 ("no hay clientes globales"); se comporta como `tipos_ausencia`.
CREATE TABLE public.clientes (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    nombre text NOT NULL,
    -- La baja es logica: horas_proyecto.cliente_id es una FK sin ON DELETE, asi que borrar un
    -- cliente con horas fallaria. Mismo criterio que tipos_ausencia (que por eso no tiene delete).
    activo boolean NOT NULL DEFAULT true,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.costos_nomina (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empleado_id uuid NOT NULL,
    anio smallint NOT NULL,
    mes smallint NOT NULL,
    salario_bruto numeric(14,2) NOT NULL,
    cargas_sociales numeric(14,2) NOT NULL DEFAULT 0,
    bonos numeric(14,2) NOT NULL DEFAULT 0,
    otros_costos numeric(14,2) NOT NULL DEFAULT 0,
    total numeric(14,2) GENERATED ALWAYS AS (((salario_bruto + cargas_sociales) + bonos) + otros_costos) STORED,
    moneda character(3) NOT NULL DEFAULT 'ARS'::bpchar,
    notas text,
    created_by uuid,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    empresa_id uuid NOT NULL
);
CREATE TABLE public.empleado_capacitacion (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    capacitacion_id uuid NOT NULL,
    empleado_id uuid,
    estado text NOT NULL DEFAULT 'pendiente'::text,
    fecha_asignacion date,
    fecha_limite date,
    fecha_completado date,
    certificado_url text,
    proyecto text,
    anio text,
    mes text,
    nombre_libre text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.empleados (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid,
    legajo character varying(20),
    nombre character varying(100) NOT NULL,
    apellido character varying(100) NOT NULL,
    email_corporativo character varying(255),
    email_personal character varying(255),
    telefono character varying(30),
    fecha_nacimiento date,
    fecha_ingreso date NOT NULL,
    fecha_egreso date,
    area_id uuid,
    cargo character varying(100),
    modalidad_trabajo character varying(20),
    tipo_contrato text,
    estado character varying(20) NOT NULL DEFAULT 'activo'::character varying,
    manager_id uuid,
    foto_url text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    cuil character varying(20),
    potencial character varying(10) NOT NULL DEFAULT 'medio'::character varying,
    desempeno character varying(10) NOT NULL DEFAULT 'medio'::character varying,
    rol character varying(100),
    empresa_id uuid NOT NULL,
    dni character varying(20),
    dias_vacaciones_asignados integer,
    roles text[] NOT NULL,
    tipo_documento text,
    sexo text,
    telefono_alternativo text,
    domicilio text,
    -- Domicilio desglosado (migración 081). `domicilio` de arriba se conserva como texto libre:
    -- es el destino de lo que no encaje acá. `domicilio_numero` es TEXT porque existen "S/N",
    -- "1234 bis", "KM 4". `domicilio_provincia` se valida en la app contra las 24
    -- jurisdicciones (backend/schemas/_provincias.py), no por CHECK: una sola fuente.
    domicilio_calle text,
    domicilio_numero text,
    domicilio_piso_depto text,
    domicilio_localidad text,
    domicilio_provincia text,
    domicilio_cp text,
    estudios text,
    ubicacion text,
    turno text,
    horas_contrato integer,
    -- 🔴 LAS CUATRO SALIERON DEL LEGAJO EL 25/8/2026 (bloque N2) — no se muestran en la ficha,
    -- no se piden en el formulario y no salen en el export. Las columnas se conservan, y el
    -- motivo NO es el mismo para las cuatro. Leerlas como un grupo es el error a evitar:
    --
    --   · `organismo`, `sector`, `perfil` → **0 filas cargadas de 41** (medido contra el catálogo
    --     vivo el 25/8/2026). El import de nómina lee las columnas "Organismo" y "Sector" del CSV
    --     y las DESVÍA a resolver `empresa_id` y `area_id`; nunca escribe estas tres. La ficha
    --     mostraba un guion en campos que el archivo sí traía, resueltos en otro lado y con otro
    --     nombre. Llenarlas habría creado una copia en texto plano y sin FK de lo que ya vive en
    --     `empresas.nombre` y `areas.nombre`: al primer renombre desde /areas, la copia miente y
    --     no hay forma de saber cuál manda. Son candidatas a DROP; nadie las lee.
    --
    --   · `gerencia` → **31 filas de 41, y NO es candidata a DROP**. Dejó de ser un campo del
    --     legajo para ser **la agrupación del organigrama**, y su ÚNICO origen es el archivo de
    --     nómina. Salió del formulario porque Capital Humano pidió que no se cargue ni se edite
    --     a mano, y hay una razón técnica que lo respalda: editar esta columna **no mueve a nadie
    --     en el organigrama**. Ver el párrafo de abajo.
    organismo text,
    -- 🔴 CÓMO FUNCIONA REALMENTE LA AGRUPACIÓN POR GERENCIA, porque la frase corta se malentiende:
    -- **el organigrama NO lee esta columna.** El import (`services/_nomina_proyectos.py`) hace DOS
    -- cosas en la misma pasada con el valor del CSV: escribe acá, y crea/reusa un `proyecto` con
    -- ese nombre y asigna a la persona. El organigrama que se ve es
    -- `organigrama_proyectos_service`, que renderiza `proyectos` + `proyecto_asignaciones`.
    -- Verificado contra producción el 25/8/2026: las 7 gerencias distintas tienen su proyecto
    -- homónimo, con las asignaciones exactas (13/13, 11/11, 3/3 y 1/1 ×4).
    -- ⚠️ CONSECUENCIA, y es el argumento más fuerte para haberla sacado del formulario: la
    -- asignación al proyecto es una FOTO del momento del import. Cambiar esta columna a mano no
    -- reasigna a nadie — era un campo que parecía editable y cuya edición no hacía nada.
    -- 📌 Esta columna es la TRAZA de qué gerencia declaró el archivo; el proyecto es la
    -- materialización. Las dos las escribe el mismo import, así que no pueden divergir.
    gerencia text,
    sector text,
    seniority text,
    perfil text,
    categoria text,
    referido text,
    es_lider boolean DEFAULT false,
    fecha_ingreso_reconocida date,
    equipo text,
    co_sourcing boolean,
    product_owner boolean,
    liderazgo text,
    motivo_baja text,
    -- Migracion 113. Fechas del TRAMITE, distintas de fecha_ingreso/fecha_egreso, que son las
    -- EFECTIVAS. El tramite arranca el 1/1 y la persona entra el 15/1. NO se toco el CHECK de
    -- `estado`: un valor nuevo ahi romperia en silencio los dos conteos que hacen
    -- `.neq(estado,'baja')` (area_repo y sucesion_repo).
    fecha_ingreso_prevista date,
    fecha_baja_prevista date
);
CREATE TABLE public.empresas (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    nombre character varying(200) NOT NULL,
    activa boolean NOT NULL DEFAULT true,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    razon_social character varying(200),
    cuit character varying(13),
    direccion text,
    telefono character varying(30),
    email character varying(255),
    logo_url text
);
CREATE TABLE public.evaluacion_equivalencias (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    apellido_csv text NOT NULL,
    nombre_csv text NOT NULL,
    empleado_id uuid NOT NULL,
    confirmado_por uuid,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.evaluacion_evaluados (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    lote_id uuid NOT NULL,
    empleado_id uuid,
    nota_final numeric,
    perfil text NOT NULL,
    organismo text,
    gerencia text,
    sector text,
    apellido_evaluado text NOT NULL,
    nombre_evaluado text NOT NULL,
    apellido_superior text,
    nombre_superior text,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.evaluacion_lotes (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    periodo text NOT NULL,
    importado_por uuid,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.evaluacion_resultados (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    evaluado_id uuid NOT NULL,
    tipo_evaluador text NOT NULL,
    competencia text NOT NULL,
    orden integer NOT NULL,
    nota numeric NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.horas_proyecto (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    -- 🔴 Los TRES nullables desde la migracion 103. La tabla nacio para costear proyectos via
    -- una asignacion; la carga directa del modulo de horas no pasa por ninguna. El camino viejo
    -- (POST /api/proyectos/{id}/horas) los sigue escribiendo siempre.
    asignacion_id uuid,
    proyecto_id uuid,
    empresa_id uuid NOT NULL,
    empleado_empresa_id uuid NOT NULL,
    fecha date NOT NULL,
    horas numeric(6,2) NOT NULL,
    valor_hora_snapshot numeric(16,2),
    descripcion text,
    cargado_por uuid,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    -- Migracion 103. `cliente_id` es NULLABLE aunque la carga nueva lo exija: la obligatoriedad
    -- la impone el service, porque el camino viejo escribe sin cliente.
    cliente_id uuid,
    -- De quien son las horas cuando NO hay asignacion. Sin esto una carga directa queda sin
    -- dueno: `cargado_por` es FK a users y los empleados no tienen cuenta (empleados.user_id 0/31).
    empleado_id uuid,
    -- Vocabulario cerrado 'home_office' | 'on_site' (CHECK abajo). Es del DIA, no del empleado:
    -- empleados.modalidad_trabajo (presencial|hibrido) es otra cosa y no se reusa.
    modalidad text,
    -- Proyecto y tarea son TEXTO LIBRE y opcionales: no hay tabla de tareas ni cascada, y la
    -- tabla `proyectos` no participa de este flujo.
    proyecto_texto text,
    tarea_texto text,
    -- Migracion 106. Identificador por INTENTO de envio que manda el cliente publico; el indice
    -- unico parcial de abajo es lo que hace que el DOBLE TAP no cree dos filas. El camino viejo
    -- no lo manda (queda NULL) y por eso el indice es parcial.
    idempotencia text
);
-- Log de SEGURIDAD del link publico de carga de horas (migracion 104): un intento por cada DNI
-- escrito en la ruta publica. NO es `auditoria` — ahi hay usuario_id y aca no hay usuario.
-- El DNI se guarda EN CLARO a proposito (8 digitos: un hash seria reversible en segundos y
-- destruiria la utilidad forense). Append-only: SIN updated_at, por eso no lleva trigger.
CREATE TABLE public.intentos_identificacion (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    dni text NOT NULL,
    -- ok | sin_coincidencia | inactivo | sin_clientes | ambiguo | bloqueado. Distingue adentro lo que la
    -- respuesta HTTP NO distingue: hacia afuera los cuatro fallos son un rechazo unico.
    resultado text NOT NULL,
    empleado_id uuid,
    empresa_id uuid,
    ip text,
    user_agent text,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.inventario_asignaciones (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    item_id uuid NOT NULL,
    empleado_id uuid NOT NULL,
    fecha_asignacion date NOT NULL DEFAULT CURRENT_DATE,
    fecha_devolucion date,
    estado_devolucion text,
    notas text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.inventario_items (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    nombre text NOT NULL,
    descripcion text,
    tipo text NOT NULL,
    numero_serie text,
    estado text NOT NULL DEFAULT 'disponible'::text,
    fecha_alta date NOT NULL DEFAULT CURRENT_DATE,
    costo numeric,
    notas text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.oauth_states (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    state_hash text NOT NULL,
    user_id uuid NOT NULL,
    proveedor text NOT NULL DEFAULT 'google'::text,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.objetivo_responsables (
    objetivo_id uuid NOT NULL,
    user_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.objetivos (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    responsable_id uuid NOT NULL,
    parent_id uuid,
    titulo text NOT NULL,
    descripcion text,
    prioridad text NOT NULL DEFAULT 'media'::text,
    estado text NOT NULL DEFAULT 'por_hacer'::text,
    fecha_entrega date,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    -- Migracion 114. TEXTO LIBRE, sin CHECK: la vista anual mira los anuales, pero la otra
    -- acepta cualquier expresion ("primer trimestre", "tercera semana de septiembre"). NOT NULL
    -- DEFAULT '' porque entra en `ux_objetivo_responsable_titulo`, y en Postgres los NULL no
    -- colisionan entre si: nullable ahi haria que el indice deje de deduplicar en silencio.
    periodicidad text NOT NULL DEFAULT ''::text,
    -- Migracion 114, tipo cambiado por la 119. Anotacion de contexto, NO una FK a areas: los
    -- objetivos son del equipo de RRHH (responsable_id -> users) y ese equipo no tiene area. Lo
    -- que se anota son las areas de OTRAS empresas con las que el objetivo se comparte.
    -- 🔄 ARRAY Y NO TEXTO (mig 119) para que el filtro sea honesto: con texto, `ILIKE '%Sistemas%'`
    -- tambien matchea "Sistemas Corporativos" y el desplegable de valores usados ofrece la CELDA
    -- ("Sistemas; Legales") en vez del area. Con array el filtro es `@>` (elementos completos) y
    -- el desplegable sale del aplanado, igual que `empleados.roles`.
    -- NOT NULL DEFAULT '{}' y no nullable: con nullable, "sin areas" tendria DOS representaciones
    -- (NULL y '{}') y las dos se producirian solas — el form manda [] y el import manda la
    -- columna ausente—, asi que `IS NULL` y `= '{}'` serian dos filtros distintos para la misma
    -- pregunta. NO es el motivo de `periodicidad` (esa es NOT NULL porque entra en el indice
    -- unico); aca no entra en ningun indice.
    -- SIN el CHECK de `empleados.roles` (array_length >= 1): un objetivo sin areas compartidas es
    -- el caso NORMAL, no un dato incompleto.
    areas_involucradas text[] NOT NULL DEFAULT ARRAY[]::text[],
    -- Migracion 119. A cual de las dos vistas pertenece el objetivo: la ANUAL es la que Capital
    -- Humano presenta al directorio, la OPERATIVA acepta cualquier expresion de tiempo. Un
    -- objetivo pertenece a UNA y no se comparte; se puede cambiar desde la pantalla.
    -- 🔴 CHECK CERRADO, al reves que `periodicidad`, y la asimetria es a proposito: el vocabulario
    -- de la periodicidad no se puede cerrar (texto libre), y el de `tipo` ES la lista de vistas de
    -- la pantalla — un tercer valor no es un dato que RRHH escriba, es una pantalla que hay que
    -- construir.
    -- 🔴 DEFAULT 'anual' EN LA BASE, pero el default del ALTA y del IMPORT es 'operativo'. No se
    -- contradicen: el de la base resuelve el backfill de las filas que ya existian (la unica tenia
    -- que quedar anual) y vive aca; el de producto resuelve en que vista nace lo nuevo (la
    -- permisiva) y vive en el codigo. Ver la migracion 119.
    tipo text NOT NULL DEFAULT 'anual'::text
);
CREATE TABLE public.offboarding_activos (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    instancia_id uuid NOT NULL,
    tipo_activo character varying(30) NOT NULL,
    descripcion character varying(255),
    numero_serie character varying(100),
    estado character varying(20) NOT NULL DEFAULT 'pendiente'::character varying,
    fecha_devolucion date,
    recibido_por uuid,
    notas character varying(500),
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    empresa_id uuid NOT NULL
);
CREATE TABLE public.offboarding_instancias (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empleado_id uuid NOT NULL,
    motivo_egreso character varying(30) NOT NULL,
    descripcion_motivo text,
    fecha_notificacion date,
    fecha_ultimo_dia date NOT NULL,
    estado character varying(20) NOT NULL DEFAULT 'iniciado'::character varying,
    entrevista_salida boolean NOT NULL DEFAULT false,
    notas_entrevista text,
    created_by uuid,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    empresa_id uuid NOT NULL
);
CREATE TABLE public.onboarding_instancias (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empleado_id uuid NOT NULL,
    template_id uuid NOT NULL,
    fecha_inicio date NOT NULL DEFAULT CURRENT_DATE,
    fecha_fin_esperada date,
    fecha_completada date,
    estado character varying(20) NOT NULL DEFAULT 'pendiente'::character varying,
    created_by uuid,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    empresa_id uuid NOT NULL
);
CREATE TABLE public.onboarding_progreso (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    instancia_id uuid NOT NULL,
    tarea_id uuid NOT NULL,
    estado character varying(20) NOT NULL DEFAULT 'pendiente'::character varying,
    fecha_completada timestamp with time zone,
    completado_por uuid,
    notas text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    empresa_id uuid NOT NULL
);
CREATE TABLE public.onboarding_tareas (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    template_id uuid NOT NULL,
    nombre character varying(200) NOT NULL,
    descripcion text,
    responsable_tipo character varying(20) NOT NULL,
    orden smallint NOT NULL DEFAULT 1,
    dias_limite smallint NOT NULL DEFAULT 1,
    obligatoria boolean NOT NULL DEFAULT true,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    semana smallint NOT NULL DEFAULT 1,
    empresa_id uuid NOT NULL
);
CREATE TABLE public.onboarding_templates (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    nombre character varying(150) NOT NULL,
    descripcion text,
    area_id uuid,
    duracion_dias smallint NOT NULL DEFAULT 30,
    activo boolean NOT NULL DEFAULT true,
    created_by uuid,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    empresa_id uuid NOT NULL,
    es_publica boolean NOT NULL DEFAULT true
);
-- Reglas escalares configurables. empresa_id NULL = fila global; la lectura resuelve
-- COALESCE(fila de mi empresa, fila global). Ver migracion 085.
CREATE TABLE public.parametros_empresa (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid,
    base_dias_habiles smallint NOT NULL DEFAULT 22,
    corte_antiguedad_mes smallint NOT NULL DEFAULT 10,
    periodo_vacacional_desde_mes smallint NOT NULL DEFAULT 10,
    periodo_vacacional_hasta_mes smallint NOT NULL DEFAULT 4,
    primer_anio_mes_corte smallint NOT NULL DEFAULT 7,
    primer_anio_dias smallint NOT NULL DEFAULT 5,
    vencimiento_anios smallint NOT NULL DEFAULT 4,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    -- Migracion 114. Dias del periodo de prueba (LCT: 90). Alimenta el evento "fin de periodo de
    -- prueba" = fecha_ingreso + periodo_prueba_dias. Va ACA y no en `empresas` porque esta tabla
    -- ya tiene el patron fila-global + fila-por-empresa-que-pisa, con sus dos UNIQUE parciales.
    periodo_prueba_dias smallint NOT NULL DEFAULT 90,
    -- Migracion 114. Default de anticipacion del aviso de un evento de agenda. Cada evento puede
    -- pisarlo con `eventos_agenda.dias_aviso`.
    dias_aviso_evento smallint NOT NULL DEFAULT 7
);
-- Criterio configurable del clasificador de CVs (mig 100). Tabla PROPIA y no columnas de
-- parametros_empresa: el upsert de aquella desengancharia a la empresa de las reglas globales
-- de vacaciones al guardar screening. empresa_id NULL = fila global.
CREATE TABLE public.parametros_screening (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid,
    def_relevante text NOT NULL,
    def_dudoso text NOT NULL,
    def_no_relevante text NOT NULL,
    instrucciones text NOT NULL DEFAULT ''::text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.periodos_cerrados (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    modulo text,
    desde date NOT NULL,
    hasta date NOT NULL,
    estado text NOT NULL DEFAULT 'cerrado'::text,
    cerrado_por uuid,
    cerrado_at timestamp with time zone NOT NULL DEFAULT now(),
    reabierto_por uuid,
    reabierto_at timestamp with time zone
);
CREATE TABLE public.planes_carrera (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empleado_id uuid NOT NULL,
    cargo_objetivo character varying(150) NOT NULL,
    descripcion text,
    fecha_inicio date NOT NULL DEFAULT CURRENT_DATE,
    fecha_objetivo date,
    estado character varying(20) NOT NULL DEFAULT 'activo'::character varying,
    progreso smallint NOT NULL DEFAULT 0,
    responsable_id uuid,
    notas text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    empresa_id uuid NOT NULL
);
CREATE TABLE public.planes_carrera_hitos (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    plan_id uuid NOT NULL,
    nombre character varying(200) NOT NULL,
    descripcion text,
    tipo character varying(20) NOT NULL,
    fecha_objetivo date,
    fecha_completada date,
    estado character varying(20) NOT NULL DEFAULT 'pendiente'::character varying,
    evidencia_url text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    empresa_id uuid NOT NULL
);
CREATE TABLE public.presupuesto_areas (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    area_id uuid NOT NULL,
    anio smallint NOT NULL,
    mes smallint,
    tipo_costo character varying(20) NOT NULL,
    monto_presupuestado numeric(16,2) NOT NULL,
    monto_ejecutado numeric(16,2) NOT NULL DEFAULT 0,
    moneda character(3) NOT NULL DEFAULT 'ARS'::bpchar,
    notas text,
    created_by uuid,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    empresa_id uuid NOT NULL
);
CREATE TABLE public.proyecto_asignaciones (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    proyecto_id uuid NOT NULL,
    empleado_id uuid NOT NULL,
    empleado_empresa_id uuid NOT NULL,
    rol text NOT NULL,
    valor_hora numeric(16,2) NOT NULL DEFAULT 0,
    fecha_desde date,
    fecha_hasta date,
    activo boolean NOT NULL DEFAULT true,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.proyectos (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    nombre text NOT NULL,
    descripcion text,
    estado text NOT NULL DEFAULT 'activo'::text,
    fecha_inicio date,
    fecha_fin date,
    presupuesto numeric(16,2) NOT NULL DEFAULT 0,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);
-- Escala de dias de vacaciones por antiguedad: una LISTA de tramos (por eso no vive en
-- parametros_empresa). empresa_id NULL = tramo de la escala global. Ver migracion 085.
CREATE TABLE public.reglas_vacaciones_escala (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid,
    antiguedad_anios smallint NOT NULL,
    dias smallint NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.reportes_generados (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    nombre character varying(200) NOT NULL,
    tipo character varying(50) NOT NULL,
    parametros jsonb,
    datos jsonb NOT NULL DEFAULT '{}'::jsonb,
    generado_por character varying(200) NOT NULL DEFAULT 'Sistema'::character varying,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    empresa_id uuid
);
-- Sesion del link publico de carga de horas (migracion 105). Sostiene la identidad entre el
-- paso 1 (identificarse con el DNI) y el paso 2 (cargar). El token se guarda HASHEADO: contra
-- 256 bits de entropia un SHA-256 sin salt alcanza. Es lo contrario del dni de la 104, que va en
-- claro porque 8 digitos se revierten en segundos. Ver el encabezado de la 105.
CREATE TABLE public.sesiones_horas (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    token_hash text NOT NULL,
    empleado_id uuid NOT NULL,
    empresa_id uuid NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.solicitudes_ausencia (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    empleado_id uuid NOT NULL,
    tipo_id uuid NOT NULL,
    fecha_desde date NOT NULL,
    fecha_hasta date NOT NULL,
    dias integer NOT NULL,
    justificada boolean NOT NULL DEFAULT false,
    motivo text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.solicitudes_vacaciones (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    empleado_id uuid NOT NULL,
    fecha_desde date NOT NULL,
    fecha_hasta date NOT NULL,
    dias integer NOT NULL,
    comentario text,
    cancelada boolean NOT NULL DEFAULT false,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    tipo character varying NOT NULL DEFAULT 'vacaciones'::character varying,
    periodo smallint,
    dias_liquidados integer NOT NULL DEFAULT 0
);

-- Superior que el import de nómina leyó del CSV y NO pudo resolver a manager_id. Estado
-- TRANSITORIO: la fila desaparece cuando el botón "resolver pendientes" la resuelve.
-- El porqué de que sea una tabla y no dos columnas en empleados: migrations/086.
CREATE TABLE public.empleado_superior_pendiente (
    empleado_id uuid NOT NULL,
    empresa_id uuid NOT NULL,
    apellido_csv text NOT NULL,
    nombre_csv text,
    motivo text NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Plantillas de mail editables por RRHH (mig 087). empresa_id NULL = global; la lectura
-- resuelve COALESCE(la de mi empresa, la global). El cuerpo es MARKDOWN, no HTML.
CREATE TABLE public.plantillas_mail (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid,
    clave text NOT NULL,
    contexto text NOT NULL,
    asunto text NOT NULL,
    cuerpo text NOT NULL,
    activa boolean NOT NULL DEFAULT true,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Log de mails enviados (mig 087). Guarda el texto YA RENDERIZADO: es lo que reemplaza al
-- versionado de plantillas. CONTIENE DATOS PERSONALES: gateada y SIN endpoint de export.
CREATE TABLE public.mail_enviado (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid,
    plantilla_clave text,
    contexto text,
    empleado_id uuid,
    destinatario text NOT NULL,
    remitente text,
    asunto_render text NOT NULL,
    cuerpo_render text NOT NULL,
    estado text NOT NULL DEFAULT 'enviado',
    error text,
    gmail_message_id text,
    enviado_por uuid,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Días de un período que NO se tomaron (sin fechas: nadie faltó ningún día). Separada de
-- solicitudes_vacaciones a propósito — ver migrations/083 antes de fusionarlas.
CREATE TABLE public.vacaciones_pendientes (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    empleado_id uuid NOT NULL,
    periodo smallint NOT NULL,
    dias integer NOT NULL,
    dias_liquidados integer NOT NULL DEFAULT 0,
    comentario text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);
-- empresa_id NULL = tipo global (las 4 filas base lo son). cuenta_ausentismo es POLITICA del
-- tipo y NO reemplaza a solicitudes_ausencia.justificada, que es un HECHO de la instancia.
CREATE TABLE public.tipos_ausencia (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    nombre text NOT NULL,
    es_base boolean NOT NULL DEFAULT false,
    activo boolean NOT NULL DEFAULT true,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    empresa_id uuid,
    cuenta_ausentismo boolean NOT NULL DEFAULT true,
    -- Jerarquía de dos niveles (mig 088). NULL = tipo de primer nivel. La profundidad máxima
    -- (2) la garantiza el service, no un CHECK: un CHECK no puede consultar otra fila.
    padre_id uuid
);
-- 🔴 `id` LLEVA DEFAULT gen_random_uuid() Y NO TIENE FK A auth.users. Ver el bloque
-- "AUTENTICACION" del encabezado: en Supabase el id lo genera Supabase Auth y la app lo
-- pasa explicito en el INSERT, asi que el DEFAULT no cambia nada de como se crea un
-- usuario HOY; solo habilita el INSERT sin `id`, que es lo que hace falta en RDS, donde
-- no existe `auth.users` que lo genere.
CREATE TABLE public.users (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    email character varying(255) NOT NULL,
    nombre character varying(100) NOT NULL,
    apellido character varying(100) NOT NULL,
    rol character varying(20) NOT NULL,
    avatar_url text,
    activo boolean NOT NULL DEFAULT true,
    ultimo_acceso timestamp with time zone,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    username character varying(50),
    must_change_password boolean NOT NULL DEFAULT false
);
CREATE TABLE public.usuario_integraciones (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    tipo character varying(50) NOT NULL,
    access_token text,
    refresh_token text,
    token_expiry timestamp with time zone,
    email_cuenta text,
    api_key text,
    activo boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    -- Casilla del sistema (mig 087): como máximo UNA en true, lo garantiza un índice único
    -- parcial. `scopes` = permisos realmente concedidos; NULL = anterior a la columna.
    es_remitente_sistema boolean NOT NULL DEFAULT false,
    scopes text[]
);
CREATE TABLE public.vacantes (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    titulo character varying(150) NOT NULL,
    area_id uuid,
    descripcion text,
    requisitos text,
    modalidad character varying(20),
    tipo_contrato character varying(20),
    nivel character varying(20),
    rango_salarial_min numeric(12,2),
    rango_salarial_max numeric(12,2),
    moneda character(3) NOT NULL DEFAULT 'ARS'::bpchar,
    cantidad_puestos smallint NOT NULL DEFAULT 1,
    estado character varying(20) NOT NULL DEFAULT 'nueva'::character varying,
    prioridad character varying(10) NOT NULL DEFAULT 'media'::character varying,
    fecha_apertura date,
    fecha_cierre date,
    responsable_id uuid,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    linkedin_post_id text,
    linkedin_url text,
    email_contacto text,
    empresa_id uuid NOT NULL,
    copy_publicacion text,
    hashtags text,
    ubicacion text,
    jornada text,
    funciones text,
    formacion text,
    experiencia text,
    conocimientos_tecnicos text,
    ofrecemos text,
    -- Token del aviso de LinkedIn ("asunto [VAC-0001]") y clave del matcher de CVs.
    -- El DEFAULT es lo que garantiza que TODA fila nazca con código, venga del backend o de un
    -- INSERT a mano: nextval es atómico, así que no hay condición de carrera. Ver migración 097.
    codigo text NOT NULL DEFAULT ('VAC-'::text || lpad((nextval('vacantes_codigo_seq'::regclass))::text, 4, '0'::text)),
    -- Migracion 113. De que perfil de puesto salio esta vacante. Solo TRAZABILIDAD: los campos
    -- se COPIAN al crearla y despues son de la vacante. `perfiles_puesto` no tiene empresa_id,
    -- asi que no hay cruce de empresa que vigilar (mismo caso que horas_proyecto.cliente_id
    -- despues de la 109).
    perfil_puesto_id uuid
);

-- ── Las tres tablas del lote 113 (2026-08-13) ────────────────────────────────
-- Se agregan al FINAL y no en orden alfabetico: es la convencion que este archivo ya sigue
-- (empleado_superior_pendiente, plantillas_mail, mail_enviado, tipos_ausencia y vacantes tambien
-- estan fuera de orden, apendeadas cuando nacieron).

-- Catalogo de plantillas de puesto, GLOBAL AL GRUPO.
-- 🔴 SIN empresa_id y SIN area_id. Un perfil describe QUE hace un puesto, y eso no cambia segun
-- de que sociedad cobre la persona. `area_id` ademas lo ataria a una empresa por transitividad
-- (`areas.empresa_id` es NOT NULL) y chocaria con trg_emp_vacantes al copiar. El area se ELIGE
-- al crear la vacante. Molde: `clientes` despues de las migraciones 108/109.
CREATE TABLE public.perfiles_puesto (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    nombre text NOT NULL,
    descripcion text,
    funciones text,
    requisitos text,
    formacion text,
    experiencia text,
    conocimientos_tecnicos text,
    ofrecemos text,
    modalidad character varying(20),
    tipo_contrato character varying(20),
    nivel character varying(20),
    jornada text,
    activo boolean NOT NULL DEFAULT true,
    created_by uuid,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Historico de cambios de rol y seniority por empleado.
-- 🔴 NO duplica a `auditoria`, que ya guarda el diff: lo que aquella NO puede dar es el MOTIVO,
-- la FECHA EFECTIVA (auditoria.created_at dice cuando se cargo, no desde cuando rige), el
-- impacto salarial —que vive detras del gate de COSTOS— ni la posibilidad de corregir, porque
-- `auditoria` es inmutable. Esta es el registro de NEGOCIO; aquella, el TECNICO.
CREATE TABLE public.recategorizaciones (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    empleado_id uuid NOT NULL,
    fecha_efectiva date NOT NULL,
    rol_anterior text,
    rol_nuevo text,
    seniority_anterior text,
    seniority_nueva text,
    categoria_anterior text,
    categoria_nueva text,
    motivo text NOT NULL,
    impacto_salarial numeric,
    registrado_por uuid,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Eventos manuales del calendario del dashboard.
-- `es_publica`: mismo nombre y misma semantica que onboarding_templates.es_publica.
-- `resuelta`: un evento NO desaparece por vencer, desaparece cuando alguien lo marca.
CREATE TABLE public.eventos_agenda (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    nombre text NOT NULL,
    fecha date NOT NULL,
    descripcion text,
    dias_aviso smallint NOT NULL DEFAULT 7,
    es_publica boolean NOT NULL DEFAULT true,
    resuelta boolean NOT NULL DEFAULT false,
    resuelta_at timestamp with time zone,
    resuelta_por uuid,
    created_by uuid NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);


-- ============================================================================
-- CONSTRAINTS (PK -> UNIQUE -> CHECK -> FK)
-- ============================================================================

ALTER TABLE public.adjuntos ADD CONSTRAINT adjuntos_pkey PRIMARY KEY (id);
ALTER TABLE public.areas ADD CONSTRAINT areas_pkey PRIMARY KEY (id);
ALTER TABLE public.assessment_campanas ADD CONSTRAINT assessment_campanas_pkey PRIMARY KEY (id);
ALTER TABLE public.assessment_links ADD CONSTRAINT assessment_links_pkey PRIMARY KEY (id);
ALTER TABLE public.assessment_resultados ADD CONSTRAINT assessment_resultados_pkey PRIMARY KEY (id);
ALTER TABLE public.auditoria ADD CONSTRAINT auditoria_pkey PRIMARY KEY (id);
ALTER TABLE public.candidatos ADD CONSTRAINT candidatos_pkey PRIMARY KEY (id);
ALTER TABLE public.capacitaciones ADD CONSTRAINT capacitaciones_pkey PRIMARY KEY (id);
ALTER TABLE public.cesiones ADD CONSTRAINT cesiones_pkey PRIMARY KEY (id);
ALTER TABLE public.clientes ADD CONSTRAINT clientes_pkey PRIMARY KEY (id);
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_pkey PRIMARY KEY (id);
ALTER TABLE public.empleado_capacitacion ADD CONSTRAINT empleado_capacitacion_pkey PRIMARY KEY (id);
ALTER TABLE public.empleados ADD CONSTRAINT empleados_pkey PRIMARY KEY (id);
ALTER TABLE public.empresas ADD CONSTRAINT empresas_pkey PRIMARY KEY (id);
ALTER TABLE public.evaluacion_equivalencias ADD CONSTRAINT evaluacion_equivalencias_pkey PRIMARY KEY (id);
ALTER TABLE public.evaluacion_evaluados ADD CONSTRAINT evaluacion_evaluados_pkey PRIMARY KEY (id);
ALTER TABLE public.evaluacion_lotes ADD CONSTRAINT evaluacion_lotes_pkey PRIMARY KEY (id);
ALTER TABLE public.evaluacion_resultados ADD CONSTRAINT evaluacion_resultados_pkey PRIMARY KEY (id);
ALTER TABLE public.horas_proyecto ADD CONSTRAINT horas_proyecto_pkey PRIMARY KEY (id);
ALTER TABLE public.intentos_identificacion ADD CONSTRAINT intentos_identificacion_pkey PRIMARY KEY (id);
ALTER TABLE public.inventario_asignaciones ADD CONSTRAINT inventario_asignaciones_pkey PRIMARY KEY (id);
ALTER TABLE public.inventario_items ADD CONSTRAINT inventario_items_pkey PRIMARY KEY (id);
ALTER TABLE public.oauth_states ADD CONSTRAINT oauth_states_pkey PRIMARY KEY (id);
ALTER TABLE public.objetivo_responsables ADD CONSTRAINT objetivo_responsables_pkey PRIMARY KEY (objetivo_id, user_id);
ALTER TABLE public.objetivos ADD CONSTRAINT objetivos_pkey PRIMARY KEY (id);
ALTER TABLE public.offboarding_activos ADD CONSTRAINT offboarding_activos_pkey PRIMARY KEY (id);
ALTER TABLE public.offboarding_instancias ADD CONSTRAINT offboarding_instancias_pkey PRIMARY KEY (id);
ALTER TABLE public.onboarding_instancias ADD CONSTRAINT onboarding_instancias_pkey PRIMARY KEY (id);
ALTER TABLE public.onboarding_progreso ADD CONSTRAINT onboarding_progreso_pkey PRIMARY KEY (id);
ALTER TABLE public.onboarding_tareas ADD CONSTRAINT onboarding_tareas_pkey PRIMARY KEY (id);
ALTER TABLE public.onboarding_templates ADD CONSTRAINT onboarding_templates_pkey PRIMARY KEY (id);
ALTER TABLE public.parametros_empresa ADD CONSTRAINT parametros_empresa_pkey PRIMARY KEY (id);
ALTER TABLE public.parametros_screening ADD CONSTRAINT parametros_screening_pkey PRIMARY KEY (id);
ALTER TABLE public.periodos_cerrados ADD CONSTRAINT periodos_cerrados_pkey PRIMARY KEY (id);
ALTER TABLE public.planes_carrera ADD CONSTRAINT planes_carrera_pkey PRIMARY KEY (id);
ALTER TABLE public.planes_carrera_hitos ADD CONSTRAINT planes_carrera_hitos_pkey PRIMARY KEY (id);
ALTER TABLE public.presupuesto_areas ADD CONSTRAINT presupuesto_areas_pkey PRIMARY KEY (id);
ALTER TABLE public.proyecto_asignaciones ADD CONSTRAINT proyecto_asignaciones_pkey PRIMARY KEY (id);
ALTER TABLE public.proyectos ADD CONSTRAINT proyectos_pkey PRIMARY KEY (id);
ALTER TABLE public.reglas_vacaciones_escala ADD CONSTRAINT reglas_vacaciones_escala_pkey PRIMARY KEY (id);
ALTER TABLE public.reportes_generados ADD CONSTRAINT reportes_generados_pkey PRIMARY KEY (id);
ALTER TABLE public.sesiones_horas ADD CONSTRAINT sesiones_horas_pkey PRIMARY KEY (id);
ALTER TABLE public.solicitudes_ausencia ADD CONSTRAINT solicitudes_ausencia_pkey PRIMARY KEY (id);
ALTER TABLE public.solicitudes_vacaciones ADD CONSTRAINT solicitudes_vacaciones_pkey PRIMARY KEY (id);
ALTER TABLE public.tipos_ausencia ADD CONSTRAINT tipos_ausencia_pkey PRIMARY KEY (id);
ALTER TABLE public.tipos_ausencia ADD CONSTRAINT tipos_ausencia_padre_no_es_si_mismo CHECK (padre_id IS NULL OR padre_id <> id);
ALTER TABLE public.users ADD CONSTRAINT users_pkey PRIMARY KEY (id);
ALTER TABLE public.usuario_integraciones ADD CONSTRAINT usuario_integraciones_pkey PRIMARY KEY (id);
ALTER TABLE public.empleado_superior_pendiente ADD CONSTRAINT empleado_superior_pendiente_pkey PRIMARY KEY (empleado_id);
ALTER TABLE public.plantillas_mail ADD CONSTRAINT plantillas_mail_pkey PRIMARY KEY (id);
ALTER TABLE public.mail_enviado ADD CONSTRAINT mail_enviado_pkey PRIMARY KEY (id);
ALTER TABLE public.mail_enviado ADD CONSTRAINT mail_enviado_estado_check CHECK (estado IN ('enviado', 'fallido'));
ALTER TABLE public.vacaciones_pendientes ADD CONSTRAINT vacaciones_pendientes_pkey PRIMARY KEY (id);
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_pkey PRIMARY KEY (id);
ALTER TABLE public.perfiles_puesto ADD CONSTRAINT perfiles_puesto_pkey PRIMARY KEY (id);
ALTER TABLE public.recategorizaciones ADD CONSTRAINT recategorizaciones_pkey PRIMARY KEY (id);
ALTER TABLE public.eventos_agenda ADD CONSTRAINT eventos_agenda_pkey PRIMARY KEY (id);
ALTER TABLE public.areas ADD CONSTRAINT areas_codigo_key UNIQUE (codigo);
ALTER TABLE public.areas ADD CONSTRAINT areas_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.assessment_campanas ADD CONSTRAINT assessment_campanas_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.assessment_links ADD CONSTRAINT assessment_links_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.assessment_links ADD CONSTRAINT assessment_links_token_key UNIQUE (token);
ALTER TABLE public.assessment_resultados ADD CONSTRAINT assessment_resultados_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.assessment_resultados ADD CONSTRAINT assessment_resultados_link_id_key UNIQUE (link_id);
ALTER TABLE public.candidatos ADD CONSTRAINT candidatos_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.capacitaciones ADD CONSTRAINT capacitaciones_id_empresa_id_key UNIQUE (id, empresa_id);
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_empleado_id_anio_mes_key UNIQUE (empleado_id, anio, mes);
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.empleado_capacitacion ADD CONSTRAINT empleado_capacitacion_capacitacion_id_empleado_id_key UNIQUE (capacitacion_id, empleado_id);
ALTER TABLE public.empleados ADD CONSTRAINT empleados_email_corporativo_key UNIQUE (email_corporativo);
ALTER TABLE public.empleados ADD CONSTRAINT empleados_empresa_dni_uq UNIQUE (empresa_id, dni);
ALTER TABLE public.empleados ADD CONSTRAINT empleados_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.empleados ADD CONSTRAINT empleados_legajo_empresa_key UNIQUE (legajo, empresa_id);
ALTER TABLE public.empresas ADD CONSTRAINT empresas_cuit_uq UNIQUE (cuit);
ALTER TABLE public.empresas ADD CONSTRAINT empresas_nombre_key UNIQUE (nombre);
ALTER TABLE public.evaluacion_equivalencias ADD CONSTRAINT evaluacion_equivalencias_empresa_nombre_key UNIQUE (empresa_id, apellido_csv, nombre_csv);
ALTER TABLE public.evaluacion_evaluados ADD CONSTRAINT evaluacion_evaluados_lote_nombre_key UNIQUE (lote_id, apellido_evaluado, nombre_evaluado);
ALTER TABLE public.evaluacion_lotes ADD CONSTRAINT evaluacion_lotes_empresa_periodo_key UNIQUE (empresa_id, periodo);
ALTER TABLE public.evaluacion_resultados ADD CONSTRAINT evaluacion_resultados_eval_tipo_comp_key UNIQUE (evaluado_id, tipo_evaluador, competencia);
ALTER TABLE public.inventario_items ADD CONSTRAINT inventario_items_id_empresa_id_key UNIQUE (id, empresa_id);
ALTER TABLE public.oauth_states ADD CONSTRAINT oauth_states_state_hash_key UNIQUE (state_hash);
ALTER TABLE public.offboarding_activos ADD CONSTRAINT offboarding_activos_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.offboarding_instancias ADD CONSTRAINT offboarding_instancias_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.onboarding_instancias ADD CONSTRAINT onboarding_instancias_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.onboarding_progreso ADD CONSTRAINT onboarding_progreso_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.onboarding_progreso ADD CONSTRAINT onboarding_progreso_instancia_id_tarea_id_key UNIQUE (instancia_id, tarea_id);
ALTER TABLE public.onboarding_tareas ADD CONSTRAINT onboarding_tareas_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.onboarding_templates ADD CONSTRAINT onboarding_templates_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.planes_carrera ADD CONSTRAINT planes_carrera_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.planes_carrera_hitos ADD CONSTRAINT planes_carrera_hitos_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.presupuesto_areas ADD CONSTRAINT presupuesto_areas_area_id_anio_mes_tipo_costo_key UNIQUE (area_id, anio, mes, tipo_costo);
ALTER TABLE public.presupuesto_areas ADD CONSTRAINT presupuesto_areas_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.proyecto_asignaciones ADD CONSTRAINT uq_proyecto_empleado UNIQUE (proyecto_id, empleado_id);
-- tipos_ausencia_nombre_key (UNIQUE global sobre `nombre`) fue DROPEADA en la migracion 085:
-- con empresa_id nullable prohibia que dos empresas tuvieran cada una su "Licencia especial".
-- La reemplazan los dos indices unicos parciales de la seccion INDICES.
ALTER TABLE public.users ADD CONSTRAINT users_email_key UNIQUE (email);
ALTER TABLE public.users ADD CONSTRAINT users_username_key UNIQUE (username);
ALTER TABLE public.usuario_integraciones ADD CONSTRAINT usuario_integraciones_user_id_tipo_key UNIQUE (user_id, tipo);
-- "N días pendientes del año X" es un hecho único por empleado y período. Da idempotencia al
-- import (ON CONFLICT actualiza en vez de duplicar). empresa_id NO va: empleado_id ya la
-- determina vía vp_empleado_empresa_fk, y sumarla debilitaría la restricción. Ver migración 083.
ALTER TABLE public.vacaciones_pendientes ADD CONSTRAINT vacaciones_pendientes_empleado_periodo_key UNIQUE (empleado_id, periodo);
ALTER TABLE public.adjuntos ADD CONSTRAINT adjuntos_estado_check CHECK ((estado = ANY (ARRAY['activo'::text, 'eliminado'::text])));
ALTER TABLE public.adjuntos ADD CONSTRAINT adjuntos_tamano_bytes_check CHECK ((tamano_bytes > 0));
ALTER TABLE public.areas ADD CONSTRAINT areas_nivel_check CHECK (((nivel >= 1) AND (nivel <= 10)));
ALTER TABLE public.assessment_campanas ADD CONSTRAINT assessment_campanas_estado_check CHECK (((estado)::text = ANY ((ARRAY['borrador'::character varying, 'activa'::character varying, 'cerrada'::character varying, 'archivada'::character varying])::text[])));
ALTER TABLE public.assessment_campanas ADD CONSTRAINT assessment_campanas_tipo_check CHECK (((tipo)::text = ANY ((ARRAY['conductual'::character varying, 'cognitivo'::character varying, 'tecnico'::character varying, 'mixto'::character varying])::text[])));
ALTER TABLE public.assessment_links ADD CONSTRAINT assessment_links_estado_check CHECK (((estado)::text = ANY ((ARRAY['pendiente'::character varying, 'enviado'::character varying, 'abierto'::character varying, 'completado'::character varying, 'expirado'::character varying, 'cancelado'::character varying])::text[])));
ALTER TABLE public.assessment_links ADD CONSTRAINT chk_link_destino_exclusivo CHECK ((NOT ((empleado_id IS NOT NULL) AND (candidato_id IS NOT NULL))));
ALTER TABLE public.assessment_resultados ADD CONSTRAINT assessment_resultados_tiempo_total_segundos_check CHECK ((tiempo_total_segundos > 0));
ALTER TABLE public.auditoria ADD CONSTRAINT auditoria_accion_check CHECK (((accion)::text = ANY ((ARRAY['INSERT'::character varying, 'UPDATE'::character varying, 'DELETE'::character varying])::text[])));
ALTER TABLE public.candidatos ADD CONSTRAINT candidatos_estado_check CHECK (((estado)::text = ANY ((ARRAY['activo'::character varying, 'descartado'::character varying, 'contratado'::character varying, 'en_espera'::character varying])::text[])));
ALTER TABLE public.candidatos ADD CONSTRAINT candidatos_etapa_check CHECK (((etapa)::text = ANY ((ARRAY['postulado'::character varying, 'assessment'::character varying, 'entrevista_rrhh'::character varying, 'entrevista_tecnica'::character varying, 'oferta'::character varying])::text[])));
-- 'gmail' se sumo en la mig 098: sin el, el INSERT del candidato creado desde la casilla falla.
ALTER TABLE public.candidatos ADD CONSTRAINT candidatos_fuente_check CHECK ((fuente::text = ANY (ARRAY['linkedin', 'referido', 'web', 'consultora', 'espontanea', 'otra', 'gmail']::text[])));
ALTER TABLE public.candidatos ADD CONSTRAINT candidatos_puntuacion_check CHECK (((puntuacion >= 1) AND (puntuacion <= 10)));
ALTER TABLE public.candidatos ADD CONSTRAINT candidatos_score_ia_check CHECK (((score_ia >= (0)::numeric) AND (score_ia <= (10)::numeric)));
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_anio_check CHECK (((anio >= 2000) AND (anio <= 2100)));
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_bonos_check CHECK ((bonos >= (0)::numeric));
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_cargas_sociales_check CHECK ((cargas_sociales >= (0)::numeric));
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_mes_check CHECK (((mes >= 1) AND (mes <= 12)));
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_otros_costos_check CHECK ((otros_costos >= (0)::numeric));
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_salario_bruto_check CHECK ((salario_bruto >= (0)::numeric));
ALTER TABLE public.empleado_capacitacion ADD CONSTRAINT empleado_capacitacion_estado_check CHECK ((estado = ANY (ARRAY['pendiente'::text, 'en_curso'::text, 'completado'::text])));
ALTER TABLE public.empleados ADD CONSTRAINT empleados_desempeno_check CHECK (((desempeno)::text = ANY ((ARRAY['alto'::character varying, 'medio'::character varying, 'bajo'::character varying])::text[])));
ALTER TABLE public.empleados ADD CONSTRAINT empleados_estado_check CHECK (((estado)::text = ANY ((ARRAY['activo'::character varying, 'baja'::character varying, 'licencia'::character varying, 'suspendido'::character varying, 'preingreso'::character varying])::text[])));
ALTER TABLE public.empleados ADD CONSTRAINT empleados_modalidad_trabajo_check CHECK (((modalidad_trabajo)::text = ANY ((ARRAY['presencial'::character varying, 'remoto'::character varying, 'hibrido'::character varying])::text[])));
ALTER TABLE public.empleados ADD CONSTRAINT empleados_potencial_check CHECK (((potencial)::text = ANY ((ARRAY['alto'::character varying, 'medio'::character varying, 'bajo'::character varying])::text[])));
ALTER TABLE public.empleados ADD CONSTRAINT empleados_roles_no_vacio CHECK ((array_length(roles, 1) >= 1));
ALTER TABLE public.evaluacion_evaluados ADD CONSTRAINT evaluacion_evaluados_perfil_check CHECK ((perfil = ANY (ARRAY['lider'::text, 'general'::text])));
ALTER TABLE public.evaluacion_resultados ADD CONSTRAINT evaluacion_resultados_tipo_evaluador_check CHECK ((tipo_evaluador = ANY (ARRAY['AUTOEVALUACION'::text, 'AUTOEVALUACION_LIDER'::text, 'SUPERIOR_INMEDIATO'::text, 'PAR'::text, 'COLABORADOR'::text, 'LIBRES'::text])));
ALTER TABLE public.horas_proyecto ADD CONSTRAINT horas_proyecto_horas_check CHECK ((horas > (0)::numeric));
-- Migracion 104. Los cinco desenlaces posibles de un intento de identificacion.
ALTER TABLE public.intentos_identificacion ADD CONSTRAINT intentos_identificacion_resultado_check CHECK ((resultado = ANY (ARRAY['ok'::text, 'sin_coincidencia'::text, 'inactivo'::text, 'sin_clientes'::text, 'ambiguo'::text, 'bloqueado'::text, 'preingreso'::text])));
-- Migracion 103. Acepta NULL a proposito: las filas del camino viejo no llevan modalidad.
ALTER TABLE public.horas_proyecto ADD CONSTRAINT horas_proyecto_modalidad_check CHECK ((modalidad IS NULL OR modalidad = ANY (ARRAY['home_office'::text, 'on_site'::text])));
-- Migracion 103. La tabla tiene EXACTAMENTE DOS formas de fila: o las tres del costeo por
-- asignacion, o ninguna. El estado mixto (proyecto sin snapshot) reventaria batch_costos con un
-- TypeError; asi no se puede representar. Ver el encabezado de la 103.
ALTER TABLE public.horas_proyecto ADD CONSTRAINT horas_proyecto_forma_check CHECK (((asignacion_id IS NULL AND proyecto_id IS NULL AND valor_hora_snapshot IS NULL) OR (asignacion_id IS NOT NULL AND proyecto_id IS NOT NULL AND valor_hora_snapshot IS NOT NULL)));
ALTER TABLE public.inventario_asignaciones ADD CONSTRAINT inventario_asignaciones_estado_devolucion_check CHECK (((estado_devolucion = ANY (ARRAY['ok'::text, 'con_daño'::text])) OR (estado_devolucion IS NULL)));
ALTER TABLE public.inventario_items ADD CONSTRAINT inventario_items_estado_check CHECK ((estado = ANY (ARRAY['disponible'::text, 'asignado'::text, 'en_reparacion'::text, 'baja'::text])));
ALTER TABLE public.objetivos ADD CONSTRAINT objetivos_estado_check CHECK ((estado = ANY (ARRAY['por_hacer'::text, 'haciendo'::text, 'terminado'::text])));
ALTER TABLE public.objetivos ADD CONSTRAINT objetivos_prioridad_check CHECK ((prioridad = ANY (ARRAY['baja'::text, 'media'::text, 'alta'::text])));
-- (mig 119) Las dos vistas del modulo. Cerrado a proposito: el valor lo elige la pantalla, no lo
-- escribe RRHH. Ver el comentario de la columna en el CREATE TABLE.
ALTER TABLE public.objetivos ADD CONSTRAINT objetivos_tipo_check CHECK ((tipo = ANY (ARRAY['anual'::text, 'operativo'::text])));
ALTER TABLE public.offboarding_activos ADD CONSTRAINT offboarding_activos_estado_check CHECK (((estado)::text = ANY ((ARRAY['pendiente'::character varying, 'devuelto'::character varying, 'no_aplica'::character varying, 'perdido'::character varying])::text[])));
ALTER TABLE public.offboarding_activos ADD CONSTRAINT offboarding_activos_tipo_activo_check CHECK (((tipo_activo)::text = ANY ((ARRAY['laptop'::character varying, 'celular'::character varying, 'monitor'::character varying, 'tarjeta_acceso'::character varying, 'licencia_software'::character varying, 'llave'::character varying, 'uniforme'::character varying, 'otro'::character varying])::text[])));
ALTER TABLE public.offboarding_instancias ADD CONSTRAINT offboarding_instancias_estado_check CHECK (((estado)::text = ANY ((ARRAY['iniciado'::character varying, 'en_proceso'::character varying, 'completado'::character varying, 'cancelado'::character varying])::text[])));
ALTER TABLE public.offboarding_instancias ADD CONSTRAINT offboarding_instancias_motivo_egreso_check CHECK (((motivo_egreso)::text = ANY ((ARRAY['renuncia'::character varying, 'despido'::character varying, 'acuerdo_mutuo'::character varying, 'fin_contrato'::character varying, 'jubilacion'::character varying, 'fallecimiento'::character varying, 'otro'::character varying])::text[])));
ALTER TABLE public.onboarding_instancias ADD CONSTRAINT onboarding_instancias_estado_check CHECK (((estado)::text = ANY ((ARRAY['pendiente'::character varying, 'en_progreso'::character varying, 'completado'::character varying, 'cancelado'::character varying])::text[])));
ALTER TABLE public.onboarding_progreso ADD CONSTRAINT onboarding_progreso_estado_check CHECK (((estado)::text = ANY ((ARRAY['pendiente'::character varying, 'en_progreso'::character varying, 'completado'::character varying, 'omitido'::character varying])::text[])));
ALTER TABLE public.onboarding_tareas ADD CONSTRAINT onboarding_tareas_dias_limite_check CHECK ((dias_limite > 0));
ALTER TABLE public.onboarding_tareas ADD CONSTRAINT onboarding_tareas_orden_check CHECK ((orden > 0));
ALTER TABLE public.onboarding_tareas ADD CONSTRAINT onboarding_tareas_responsable_tipo_check CHECK (((responsable_tipo)::text = ANY ((ARRAY['rrhh'::character varying, 'manager'::character varying, 'empleado'::character varying, 'ti'::character varying, 'administracion'::character varying])::text[])));
ALTER TABLE public.onboarding_tareas ADD CONSTRAINT onboarding_tareas_semana_check CHECK (((semana >= 1) AND (semana <= 4)));
ALTER TABLE public.onboarding_templates ADD CONSTRAINT onboarding_templates_duracion_dias_check CHECK ((duracion_dias > 0));
ALTER TABLE public.periodos_cerrados ADD CONSTRAINT periodos_cerrados_check CHECK ((hasta >= desde));
ALTER TABLE public.periodos_cerrados ADD CONSTRAINT periodos_cerrados_estado_check CHECK ((estado = ANY (ARRAY['cerrado'::text, 'abierto'::text])));
ALTER TABLE public.planes_carrera ADD CONSTRAINT planes_carrera_estado_check CHECK (((estado)::text = ANY ((ARRAY['activo'::character varying, 'completado'::character varying, 'pausado'::character varying, 'cancelado'::character varying])::text[])));
ALTER TABLE public.planes_carrera ADD CONSTRAINT planes_carrera_progreso_check CHECK (((progreso >= 0) AND (progreso <= 100)));
ALTER TABLE public.planes_carrera_hitos ADD CONSTRAINT planes_carrera_hitos_estado_check CHECK (((estado)::text = ANY ((ARRAY['pendiente'::character varying, 'en_progreso'::character varying, 'completado'::character varying, 'cancelado'::character varying])::text[])));
ALTER TABLE public.planes_carrera_hitos ADD CONSTRAINT planes_carrera_hitos_tipo_check CHECK (((tipo)::text = ANY ((ARRAY['capacitacion'::character varying, 'certificacion'::character varying, 'proyecto'::character varying, 'mentoring'::character varying, 'rotacion'::character varying, 'otro'::character varying])::text[])));
ALTER TABLE public.presupuesto_areas ADD CONSTRAINT presupuesto_areas_anio_check CHECK (((anio >= 2000) AND (anio <= 2100)));
ALTER TABLE public.presupuesto_areas ADD CONSTRAINT presupuesto_areas_mes_check CHECK (((mes >= 1) AND (mes <= 12)));
ALTER TABLE public.presupuesto_areas ADD CONSTRAINT presupuesto_areas_monto_ejecutado_check CHECK ((monto_ejecutado >= (0)::numeric));
ALTER TABLE public.presupuesto_areas ADD CONSTRAINT presupuesto_areas_monto_presupuestado_check CHECK ((monto_presupuestado >= (0)::numeric));
ALTER TABLE public.presupuesto_areas ADD CONSTRAINT presupuesto_areas_tipo_costo_check CHECK (((tipo_costo)::text = ANY ((ARRAY['nomina'::character varying, 'beneficios'::character varying, 'capacitacion'::character varying, 'reclutamiento'::character varying, 'total'::character varying])::text[])));
ALTER TABLE public.proyectos ADD CONSTRAINT proyectos_estado_check CHECK ((estado = ANY (ARRAY['activo'::text, 'pausado'::text, 'cerrado'::text, 'cancelado'::text])));
ALTER TABLE public.solicitudes_ausencia ADD CONSTRAINT sa_fechas_check CHECK ((fecha_hasta >= fecha_desde));
ALTER TABLE public.solicitudes_ausencia ADD CONSTRAINT solicitudes_ausencia_dias_check CHECK ((dias > 0));
ALTER TABLE public.solicitudes_vacaciones ADD CONSTRAINT solicitudes_vacaciones_dias_check CHECK ((dias > 0));
ALTER TABLE public.solicitudes_vacaciones ADD CONSTRAINT solicitudes_vacaciones_tipo_check CHECK (((tipo)::text = ANY ((ARRAY['vacaciones'::character varying, 'semana_free'::character varying, 'dia_free'::character varying, 'permiso_especial'::character varying])::text[])));
ALTER TABLE public.solicitudes_vacaciones ADD CONSTRAINT sv_dias_liquidados_check CHECK (((dias_liquidados >= 0) AND (dias_liquidados <= dias)));
ALTER TABLE public.solicitudes_vacaciones ADD CONSTRAINT sv_fechas_check CHECK ((fecha_hasta >= fecha_desde));
ALTER TABLE public.solicitudes_vacaciones ADD CONSTRAINT sv_periodo_check CHECK (((periodo IS NULL) OR ((periodo >= 2000) AND (periodo <= 2100))));
ALTER TABLE public.vacaciones_pendientes ADD CONSTRAINT vp_dias_check CHECK ((dias > 0));
ALTER TABLE public.vacaciones_pendientes ADD CONSTRAINT vp_dias_liquidados_check CHECK (((dias_liquidados >= 0) AND (dias_liquidados <= dias)));
ALTER TABLE public.vacaciones_pendientes ADD CONSTRAINT vp_periodo_check CHECK (((periodo >= 2000) AND (periodo <= 2100)));
ALTER TABLE public.users ADD CONSTRAINT users_rol_check CHECK (((rol)::text = ANY ((ARRAY['admin_rrhh'::character varying, 'gerencia_lectura'::character varying, 'mandos_medios'::character varying])::text[])));
ALTER TABLE public.vacantes ADD CONSTRAINT chk_rango_salarial CHECK (((rango_salarial_max IS NULL) OR (rango_salarial_min IS NULL) OR (rango_salarial_max >= rango_salarial_min)));
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_cantidad_puestos_check CHECK ((cantidad_puestos > 0));
-- `{4,}` y no `{4}`: lpad no trunca, la vacante 10.000 emite VAC-10000. Ver migracion 097.
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_codigo_formato CHECK ((codigo ~ '^[A-Z0-9]+(-[A-Z0-9]+)*$'::text) AND (codigo ~ '[A-Z]'::text) AND (char_length(codigo) >= 3) AND (char_length(codigo) <= 30));  -- migracion 122: lo escribe Capital Humano, ya no la secuencia
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_estado_check CHECK (((estado)::text = ANY ((ARRAY['nueva'::character varying, 'en_proceso'::character varying, 'con_candidatos'::character varying, 'cerrada'::character varying])::text[])));
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_modalidad_check CHECK (((modalidad)::text = ANY ((ARRAY['presencial'::character varying, 'remoto'::character varying, 'hibrido'::character varying])::text[])));
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_nivel_check CHECK (((nivel)::text = ANY ((ARRAY['junior'::character varying, 'semi_senior'::character varying, 'senior'::character varying, 'lider'::character varying, 'manager'::character varying, 'director'::character varying, 'c_level'::character varying])::text[])));
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_prioridad_check CHECK (((prioridad)::text = ANY ((ARRAY['baja'::character varying, 'media'::character varying, 'alta'::character varying, 'urgente'::character varying])::text[])));
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_rango_salarial_max_check CHECK ((rango_salarial_max >= (0)::numeric));
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_rango_salarial_min_check CHECK ((rango_salarial_min >= (0)::numeric));
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_tipo_contrato_check CHECK (((tipo_contrato)::text = ANY ((ARRAY['efectivo'::character varying, 'plazo_fijo'::character varying, 'contratado'::character varying, 'pasantia'::character varying])::text[])));
-- Migracion 113. Los tres CHECK de perfiles_puesto son COPIA LITERAL de los de vacantes: si se
-- escribieran "parecido", un perfil podria guardar un valor que la vacante rechaza al copiarlo y
-- el error saldria recien al crear la busqueda.
ALTER TABLE public.perfiles_puesto ADD CONSTRAINT perfiles_puesto_modalidad_check CHECK (((modalidad)::text = ANY ((ARRAY['presencial'::character varying, 'remoto'::character varying, 'hibrido'::character varying])::text[])));
ALTER TABLE public.perfiles_puesto ADD CONSTRAINT perfiles_puesto_nivel_check CHECK (((nivel)::text = ANY ((ARRAY['junior'::character varying, 'semi_senior'::character varying, 'senior'::character varying, 'lider'::character varying, 'manager'::character varying, 'director'::character varying, 'c_level'::character varying])::text[])));
ALTER TABLE public.perfiles_puesto ADD CONSTRAINT perfiles_puesto_tipo_contrato_check CHECK (((tipo_contrato)::text = ANY ((ARRAY['efectivo'::character varying, 'plazo_fijo'::character varying, 'contratado'::character varying, 'pasantia'::character varying])::text[])));
-- Migracion 113. Ni rol_nuevo ni seniority_nueva pueden ser NOT NULL por separado (una
-- recategorizacion puede cambiar solo una), pero las DOS en NULL es una fila que no dice nada.
-- Migracion 117. `categoria_nueva` entra al predicado: la categoria es el NIVEL dentro del
-- seniority, asi que "de 3 a 4" es una recategorizacion legitima -- y la mas frecuente de las
-- tres. La 116 agrego las dos columnas de categoria y no toco este CHECK, con lo cual ese caso
-- rebotaba con 23514. Los `*_anterior` NO entran: lo que define que la fila diga algo es el
-- valor NUEVO. Escrito con `IS NOT NULL` y no con comparaciones porque un CHECK que evalua a
-- NULL PASA, y ahi la fila vacia entraria sin que nada lo delate.
ALTER TABLE public.recategorizaciones ADD CONSTRAINT recategorizaciones_algo_cambia_check CHECK (((rol_nuevo IS NOT NULL) OR (seniority_nueva IS NOT NULL) OR (categoria_nueva IS NOT NULL)));
ALTER TABLE public.eventos_agenda ADD CONSTRAINT eventos_agenda_dias_aviso_check CHECK (((dias_aviso >= 0) AND (dias_aviso <= 365)));
-- Migracion 113. Si esta resuelta, tiene que decir CUANDO. NO toca `resuelta_por`: su FK es
-- ON DELETE SET NULL, y un CHECK sobre esa columna haria FALLAR el borrado de ese usuario.
ALTER TABLE public.eventos_agenda ADD CONSTRAINT eventos_agenda_resuelta_coherente_check CHECK (((NOT resuelta) OR (resuelta_at IS NOT NULL)));
-- Migracion 114.
ALTER TABLE public.parametros_empresa ADD CONSTRAINT parametros_empresa_periodo_prueba_check CHECK (((periodo_prueba_dias > 0) AND (periodo_prueba_dias <= 730)));
ALTER TABLE public.parametros_empresa ADD CONSTRAINT parametros_empresa_dias_aviso_check CHECK (((dias_aviso_evento >= 0) AND (dias_aviso_evento <= 365)));
ALTER TABLE public.parametros_empresa ADD CONSTRAINT pe_base_dias_check CHECK (((base_dias_habiles >= 1) AND (base_dias_habiles <= 31)));
ALTER TABLE public.parametros_empresa ADD CONSTRAINT pe_corte_mes_check CHECK (((corte_antiguedad_mes >= 1) AND (corte_antiguedad_mes <= 12)));
ALTER TABLE public.parametros_empresa ADD CONSTRAINT pe_vac_desde_check CHECK (((periodo_vacacional_desde_mes >= 1) AND (periodo_vacacional_desde_mes <= 12)));
ALTER TABLE public.parametros_empresa ADD CONSTRAINT pe_vac_hasta_check CHECK (((periodo_vacacional_hasta_mes >= 1) AND (periodo_vacacional_hasta_mes <= 12)));
ALTER TABLE public.parametros_empresa ADD CONSTRAINT pe_primer_anio_mes_check CHECK (((primer_anio_mes_corte >= 1) AND (primer_anio_mes_corte <= 12)));
ALTER TABLE public.parametros_empresa ADD CONSTRAINT pe_primer_anio_dias_check CHECK ((primer_anio_dias >= 0));
ALTER TABLE public.parametros_empresa ADD CONSTRAINT pe_vencimiento_check CHECK ((vencimiento_anios > 0));
ALTER TABLE public.parametros_screening ADD CONSTRAINT ps_def_relevante_check CHECK ((length(TRIM(BOTH FROM def_relevante)) > 0));
ALTER TABLE public.parametros_screening ADD CONSTRAINT ps_def_dudoso_check CHECK ((length(TRIM(BOTH FROM def_dudoso)) > 0));
ALTER TABLE public.parametros_screening ADD CONSTRAINT ps_def_no_relevante_check CHECK ((length(TRIM(BOTH FROM def_no_relevante)) > 0));
ALTER TABLE public.parametros_screening ADD CONSTRAINT ps_largos_check CHECK (((length(def_relevante) <= 2000) AND (length(def_dudoso) <= 2000) AND (length(def_no_relevante) <= 2000) AND (length(instrucciones) <= 2000)));
ALTER TABLE public.candidatos ADD CONSTRAINT candidatos_clasificacion_ia_check CHECK ((clasificacion_ia = ANY (ARRAY['relevante'::text, 'dudoso'::text, 'no_relevante'::text])));
ALTER TABLE public.candidatos ADD CONSTRAINT candidatos_clasificacion_origen_check CHECK ((clasificacion_origen = ANY (ARRAY['modelo'::text, 'humano'::text])));
ALTER TABLE public.reglas_vacaciones_escala ADD CONSTRAINT rve_antiguedad_check CHECK (((antiguedad_anios >= 0) AND (antiguedad_anios <= 60)));
ALTER TABLE public.reglas_vacaciones_escala ADD CONSTRAINT rve_dias_check CHECK (((dias > 0) AND (dias <= 365)));
ALTER TABLE public.adjuntos ADD CONSTRAINT adjuntos_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.adjuntos ADD CONSTRAINT adjuntos_subido_por_fkey FOREIGN KEY (subido_por) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.areas ADD CONSTRAINT areas_area_padre_id_fkey FOREIGN KEY (area_padre_id) REFERENCES areas(id) ON DELETE RESTRICT;
ALTER TABLE public.areas ADD CONSTRAINT areas_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.areas ADD CONSTRAINT fk_areas_responsable FOREIGN KEY (responsable_id) REFERENCES empleados(id) ON DELETE SET NULL;
ALTER TABLE public.assessment_campanas ADD CONSTRAINT assessment_campanas_area_id_fkey FOREIGN KEY (area_id) REFERENCES areas(id);
ALTER TABLE public.assessment_campanas ADD CONSTRAINT assessment_campanas_created_by_fkey FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.assessment_campanas ADD CONSTRAINT assessment_campanas_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.assessment_links ADD CONSTRAINT ass_links_campana_emp_fkey FOREIGN KEY (campana_id, empresa_id) REFERENCES assessment_campanas(id, empresa_id) ON DELETE CASCADE;
ALTER TABLE public.assessment_links ADD CONSTRAINT assessment_links_campana_id_fkey FOREIGN KEY (campana_id) REFERENCES assessment_campanas(id) ON DELETE CASCADE;
ALTER TABLE public.assessment_links ADD CONSTRAINT assessment_links_candidato_id_fkey FOREIGN KEY (candidato_id) REFERENCES candidatos(id) ON DELETE SET NULL;
ALTER TABLE public.assessment_links ADD CONSTRAINT assessment_links_empleado_id_fkey FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE SET NULL;
ALTER TABLE public.assessment_links ADD CONSTRAINT assessment_links_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.assessment_resultados ADD CONSTRAINT ass_res_campana_emp_fkey FOREIGN KEY (campana_id, empresa_id) REFERENCES assessment_campanas(id, empresa_id) ON DELETE RESTRICT;
ALTER TABLE public.assessment_resultados ADD CONSTRAINT ass_res_link_emp_fkey FOREIGN KEY (link_id, empresa_id) REFERENCES assessment_links(id, empresa_id) ON DELETE CASCADE;
ALTER TABLE public.assessment_resultados ADD CONSTRAINT assessment_resultados_campana_id_fkey FOREIGN KEY (campana_id) REFERENCES assessment_campanas(id) ON DELETE RESTRICT;
ALTER TABLE public.assessment_resultados ADD CONSTRAINT assessment_resultados_candidato_id_fkey FOREIGN KEY (candidato_id) REFERENCES candidatos(id) ON DELETE SET NULL;
ALTER TABLE public.assessment_resultados ADD CONSTRAINT assessment_resultados_empleado_id_fkey FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE SET NULL;
ALTER TABLE public.assessment_resultados ADD CONSTRAINT assessment_resultados_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.assessment_resultados ADD CONSTRAINT assessment_resultados_link_id_fkey FOREIGN KEY (link_id) REFERENCES assessment_links(id) ON DELETE CASCADE;
ALTER TABLE public.auditoria ADD CONSTRAINT auditoria_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.auditoria ADD CONSTRAINT auditoria_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.candidatos ADD CONSTRAINT candidatos_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.candidatos ADD CONSTRAINT candidatos_entrevistador_id_fkey FOREIGN KEY (entrevistador_id) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.candidatos ADD CONSTRAINT candidatos_vacante_id_fkey FOREIGN KEY (vacante_id) REFERENCES vacantes(id) ON DELETE SET NULL;
ALTER TABLE public.capacitaciones ADD CONSTRAINT capacitaciones_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.cesiones ADD CONSTRAINT cesiones_empleado_id_fkey FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE;
ALTER TABLE public.cesiones ADD CONSTRAINT cesiones_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_created_by_fkey FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_empleado_emp_fkey FOREIGN KEY (empleado_id, empresa_id) REFERENCES empleados(id, empresa_id) ON DELETE RESTRICT;
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_empleado_id_fkey FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE RESTRICT;
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.empleado_capacitacion ADD CONSTRAINT ec_capacitacion_empresa_fk FOREIGN KEY (capacitacion_id, empresa_id) REFERENCES capacitaciones(id, empresa_id);
ALTER TABLE public.empleado_capacitacion ADD CONSTRAINT ec_empleado_empresa_fk FOREIGN KEY (empleado_id, empresa_id) REFERENCES empleados(id, empresa_id);
ALTER TABLE public.empleados ADD CONSTRAINT empleados_area_id_fkey FOREIGN KEY (area_id) REFERENCES areas(id) ON DELETE RESTRICT;
ALTER TABLE public.empleados ADD CONSTRAINT empleados_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.empleados ADD CONSTRAINT empleados_manager_id_fkey FOREIGN KEY (manager_id) REFERENCES empleados(id) ON DELETE SET NULL;
ALTER TABLE public.empleados ADD CONSTRAINT empleados_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.evaluacion_equivalencias ADD CONSTRAINT evaluacion_equivalencias_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.evaluacion_equivalencias ADD CONSTRAINT evaluacion_equivalencias_empleado_id_fkey FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE;
ALTER TABLE public.evaluacion_equivalencias ADD CONSTRAINT evaluacion_equivalencias_confirmado_por_fkey FOREIGN KEY (confirmado_por) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.evaluacion_evaluados ADD CONSTRAINT evaluacion_evaluados_lote_id_fkey FOREIGN KEY (lote_id) REFERENCES evaluacion_lotes(id) ON DELETE CASCADE;
ALTER TABLE public.evaluacion_evaluados ADD CONSTRAINT evaluacion_evaluados_empleado_id_fkey FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE SET NULL;
ALTER TABLE public.evaluacion_lotes ADD CONSTRAINT evaluacion_lotes_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.evaluacion_lotes ADD CONSTRAINT evaluacion_lotes_importado_por_fkey FOREIGN KEY (importado_por) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.evaluacion_resultados ADD CONSTRAINT evaluacion_resultados_evaluado_id_fkey FOREIGN KEY (evaluado_id) REFERENCES evaluacion_evaluados(id) ON DELETE CASCADE;
ALTER TABLE public.horas_proyecto ADD CONSTRAINT horas_proyecto_asignacion_id_fkey FOREIGN KEY (asignacion_id) REFERENCES proyecto_asignaciones(id);
ALTER TABLE public.horas_proyecto ADD CONSTRAINT horas_proyecto_cargado_por_fkey FOREIGN KEY (cargado_por) REFERENCES users(id);
-- Migracion 105. FK COMPUESTA, no dos sueltas: garantiza EN LA BASE que el par empleado/empresa
-- de una sesion es coherente. Sin ella una sesion podria decir "empleado de ACME, empresa DOSUBA"
-- y todo lo escrito con ella quedaria imputado a la sociedad equivocada. Molde: sa_empleado_empresa_fk.
ALTER TABLE public.sesiones_horas ADD CONSTRAINT sesiones_horas_empleado_empresa_fk FOREIGN KEY (empleado_id, empresa_id) REFERENCES empleados(id, empresa_id) ON DELETE CASCADE;
-- Migracion 104. SET NULL: un log que desaparece cuando se borra el objeto investigado no sirve.
ALTER TABLE public.intentos_identificacion ADD CONSTRAINT intentos_identificacion_empleado_id_fkey FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE SET NULL;
ALTER TABLE public.intentos_identificacion ADD CONSTRAINT intentos_identificacion_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE SET NULL;
-- Migracion 103. Las dos SIN ON DELETE, igual que las otras cinco FKs de la tabla.
ALTER TABLE public.horas_proyecto ADD CONSTRAINT horas_proyecto_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES clientes(id);
ALTER TABLE public.horas_proyecto ADD CONSTRAINT horas_proyecto_empleado_id_fkey FOREIGN KEY (empleado_id) REFERENCES empleados(id);
ALTER TABLE public.horas_proyecto ADD CONSTRAINT horas_proyecto_empleado_empresa_id_fkey FOREIGN KEY (empleado_empresa_id) REFERENCES empresas(id);
ALTER TABLE public.horas_proyecto ADD CONSTRAINT horas_proyecto_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.horas_proyecto ADD CONSTRAINT horas_proyecto_proyecto_id_fkey FOREIGN KEY (proyecto_id) REFERENCES proyectos(id);
ALTER TABLE public.inventario_asignaciones ADD CONSTRAINT inv_asig_empleado_empresa_fk FOREIGN KEY (empleado_id, empresa_id) REFERENCES empleados(id, empresa_id);
ALTER TABLE public.inventario_asignaciones ADD CONSTRAINT inv_asig_item_empresa_fk FOREIGN KEY (item_id, empresa_id) REFERENCES inventario_items(id, empresa_id);
ALTER TABLE public.inventario_items ADD CONSTRAINT inventario_items_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.oauth_states ADD CONSTRAINT oauth_states_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE public.objetivo_responsables ADD CONSTRAINT objetivo_responsables_objetivo_id_fkey FOREIGN KEY (objetivo_id) REFERENCES objetivos(id) ON DELETE CASCADE;
ALTER TABLE public.objetivo_responsables ADD CONSTRAINT objetivo_responsables_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE public.objetivos ADD CONSTRAINT objetivos_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.objetivos ADD CONSTRAINT objetivos_responsable_id_fkey FOREIGN KEY (responsable_id) REFERENCES users(id);
ALTER TABLE public.objetivos ADD CONSTRAINT objetivos_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES objetivos(id) ON DELETE CASCADE;
ALTER TABLE public.offboarding_activos ADD CONSTRAINT offb_act_instancia_emp_fkey FOREIGN KEY (instancia_id, empresa_id) REFERENCES offboarding_instancias(id, empresa_id) ON DELETE CASCADE;
ALTER TABLE public.offboarding_activos ADD CONSTRAINT offboarding_activos_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.offboarding_activos ADD CONSTRAINT offboarding_activos_instancia_id_fkey FOREIGN KEY (instancia_id) REFERENCES offboarding_instancias(id) ON DELETE CASCADE;
ALTER TABLE public.offboarding_activos ADD CONSTRAINT offboarding_activos_recibido_por_fkey FOREIGN KEY (recibido_por) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.offboarding_instancias ADD CONSTRAINT offb_inst_empleado_emp_fkey FOREIGN KEY (empleado_id, empresa_id) REFERENCES empleados(id, empresa_id) ON DELETE RESTRICT;
ALTER TABLE public.offboarding_instancias ADD CONSTRAINT offboarding_instancias_created_by_fkey FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.offboarding_instancias ADD CONSTRAINT offboarding_instancias_empleado_id_fkey FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE RESTRICT;
ALTER TABLE public.offboarding_instancias ADD CONSTRAINT offboarding_instancias_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.onboarding_instancias ADD CONSTRAINT onb_inst_empleado_emp_fkey FOREIGN KEY (empleado_id, empresa_id) REFERENCES empleados(id, empresa_id) ON DELETE CASCADE;
ALTER TABLE public.onboarding_instancias ADD CONSTRAINT onb_inst_template_emp_fkey FOREIGN KEY (template_id, empresa_id) REFERENCES onboarding_templates(id, empresa_id) ON DELETE RESTRICT;
ALTER TABLE public.onboarding_instancias ADD CONSTRAINT onboarding_instancias_created_by_fkey FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.onboarding_instancias ADD CONSTRAINT onboarding_instancias_empleado_id_fkey FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE;
ALTER TABLE public.onboarding_instancias ADD CONSTRAINT onboarding_instancias_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.onboarding_instancias ADD CONSTRAINT onboarding_instancias_template_id_fkey FOREIGN KEY (template_id) REFERENCES onboarding_templates(id) ON DELETE RESTRICT;
ALTER TABLE public.onboarding_progreso ADD CONSTRAINT onb_prog_instancia_emp_fkey FOREIGN KEY (instancia_id, empresa_id) REFERENCES onboarding_instancias(id, empresa_id) ON DELETE CASCADE;
ALTER TABLE public.onboarding_progreso ADD CONSTRAINT onb_prog_tarea_emp_fkey FOREIGN KEY (tarea_id, empresa_id) REFERENCES onboarding_tareas(id, empresa_id) ON DELETE CASCADE;
ALTER TABLE public.onboarding_progreso ADD CONSTRAINT onboarding_progreso_completado_por_fkey FOREIGN KEY (completado_por) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.onboarding_progreso ADD CONSTRAINT onboarding_progreso_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.onboarding_progreso ADD CONSTRAINT onboarding_progreso_instancia_id_fkey FOREIGN KEY (instancia_id) REFERENCES onboarding_instancias(id) ON DELETE CASCADE;
ALTER TABLE public.onboarding_progreso ADD CONSTRAINT onboarding_progreso_tarea_id_fkey FOREIGN KEY (tarea_id) REFERENCES onboarding_tareas(id) ON DELETE CASCADE;
ALTER TABLE public.onboarding_tareas ADD CONSTRAINT onb_tareas_template_emp_fkey FOREIGN KEY (template_id, empresa_id) REFERENCES onboarding_templates(id, empresa_id) ON DELETE CASCADE;
ALTER TABLE public.onboarding_tareas ADD CONSTRAINT onboarding_tareas_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.onboarding_tareas ADD CONSTRAINT onboarding_tareas_template_id_fkey FOREIGN KEY (template_id) REFERENCES onboarding_templates(id) ON DELETE CASCADE;
ALTER TABLE public.onboarding_templates ADD CONSTRAINT onboarding_templates_area_id_fkey FOREIGN KEY (area_id) REFERENCES areas(id) ON DELETE SET NULL;
ALTER TABLE public.onboarding_templates ADD CONSTRAINT onboarding_templates_created_by_fkey FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.onboarding_templates ADD CONSTRAINT onboarding_templates_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.periodos_cerrados ADD CONSTRAINT periodos_cerrados_cerrado_por_fkey FOREIGN KEY (cerrado_por) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.periodos_cerrados ADD CONSTRAINT periodos_cerrados_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.periodos_cerrados ADD CONSTRAINT periodos_cerrados_reabierto_por_fkey FOREIGN KEY (reabierto_por) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.planes_carrera ADD CONSTRAINT planes_carrera_empleado_emp_fkey FOREIGN KEY (empleado_id, empresa_id) REFERENCES empleados(id, empresa_id) ON DELETE CASCADE;
ALTER TABLE public.planes_carrera ADD CONSTRAINT planes_carrera_empleado_id_fkey FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE;
ALTER TABLE public.planes_carrera ADD CONSTRAINT planes_carrera_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.planes_carrera ADD CONSTRAINT planes_carrera_responsable_id_fkey FOREIGN KEY (responsable_id) REFERENCES empleados(id) ON DELETE SET NULL;
ALTER TABLE public.planes_carrera_hitos ADD CONSTRAINT pc_hitos_plan_emp_fkey FOREIGN KEY (plan_id, empresa_id) REFERENCES planes_carrera(id, empresa_id) ON DELETE CASCADE;
ALTER TABLE public.planes_carrera_hitos ADD CONSTRAINT planes_carrera_hitos_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.planes_carrera_hitos ADD CONSTRAINT planes_carrera_hitos_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES planes_carrera(id) ON DELETE CASCADE;
ALTER TABLE public.presupuesto_areas ADD CONSTRAINT presupuesto_areas_area_emp_fkey FOREIGN KEY (area_id, empresa_id) REFERENCES areas(id, empresa_id) ON DELETE RESTRICT;
ALTER TABLE public.presupuesto_areas ADD CONSTRAINT presupuesto_areas_area_id_fkey FOREIGN KEY (area_id) REFERENCES areas(id) ON DELETE RESTRICT;
ALTER TABLE public.presupuesto_areas ADD CONSTRAINT presupuesto_areas_created_by_fkey FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.presupuesto_areas ADD CONSTRAINT presupuesto_areas_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.proyecto_asignaciones ADD CONSTRAINT proyecto_asignaciones_empleado_empresa_id_fkey FOREIGN KEY (empleado_empresa_id) REFERENCES empresas(id);
ALTER TABLE public.proyecto_asignaciones ADD CONSTRAINT proyecto_asignaciones_empleado_id_fkey FOREIGN KEY (empleado_id) REFERENCES empleados(id);
ALTER TABLE public.proyecto_asignaciones ADD CONSTRAINT proyecto_asignaciones_proyecto_id_fkey FOREIGN KEY (proyecto_id) REFERENCES proyectos(id);
ALTER TABLE public.proyectos ADD CONSTRAINT proyectos_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.reportes_generados ADD CONSTRAINT reportes_generados_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.solicitudes_ausencia ADD CONSTRAINT sa_empleado_empresa_fk FOREIGN KEY (empleado_id, empresa_id) REFERENCES empleados(id, empresa_id);
ALTER TABLE public.solicitudes_ausencia ADD CONSTRAINT solicitudes_ausencia_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.solicitudes_ausencia ADD CONSTRAINT solicitudes_ausencia_tipo_id_fkey FOREIGN KEY (tipo_id) REFERENCES tipos_ausencia(id);
ALTER TABLE public.tipos_ausencia ADD CONSTRAINT tipos_ausencia_padre_id_fkey FOREIGN KEY (padre_id) REFERENCES tipos_ausencia(id) ON DELETE RESTRICT;
ALTER TABLE public.solicitudes_vacaciones ADD CONSTRAINT solicitudes_vacaciones_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.solicitudes_vacaciones ADD CONSTRAINT sv_empleado_empresa_fk FOREIGN KEY (empleado_id, empresa_id) REFERENCES empleados(id, empresa_id);
ALTER TABLE public.empleado_superior_pendiente ADD CONSTRAINT empleado_superior_pendiente_empleado_id_fkey FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE;
ALTER TABLE public.empleado_superior_pendiente ADD CONSTRAINT empleado_superior_pendiente_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.plantillas_mail ADD CONSTRAINT plantillas_mail_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE;
ALTER TABLE public.mail_enviado ADD CONSTRAINT mail_enviado_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE SET NULL;
ALTER TABLE public.mail_enviado ADD CONSTRAINT mail_enviado_empleado_id_fkey FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE SET NULL;
ALTER TABLE public.vacaciones_pendientes ADD CONSTRAINT vacaciones_pendientes_empleado_id_fkey FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE;
ALTER TABLE public.vacaciones_pendientes ADD CONSTRAINT vacaciones_pendientes_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.vacaciones_pendientes ADD CONSTRAINT vp_empleado_empresa_fk FOREIGN KEY (empleado_id, empresa_id) REFERENCES empleados(id, empresa_id);
-- 🔴 ACA VIVIA LA UNICA REFERENCIA A UN SCHEMA DE SUPABASE, Y SE SACO A PROPOSITO:
--   ALTER TABLE public.users ADD CONSTRAINT users_id_fkey
--     FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;
-- Era el UNICO bloqueante del replay: en RDS no existe el schema `auth`, asi que esa linea
-- aborta el script entero. No se reemplaza por nada — la autenticacion del destino es propia
-- (`migracionAWS/`: 075 password_hash, 076 refresh_tokens), asi que la FK no tiene a que
-- apuntar. Ver el bloque "AUTENTICACION" del encabezado para lo que se pierde con ella.
ALTER TABLE public.usuario_integraciones ADD CONSTRAINT usuario_integraciones_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_area_id_fkey FOREIGN KEY (area_id) REFERENCES areas(id) ON DELETE RESTRICT;
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_responsable_id_fkey FOREIGN KEY (responsable_id) REFERENCES users(id) ON DELETE SET NULL;
-- Migracion 113. ON DELETE SET NULL: borrar un perfil no puede llevarse la vacante, que ya copio
-- los campos y es independiente — ese es el punto del modelo de COPIA.
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_perfil_puesto_id_fkey FOREIGN KEY (perfil_puesto_id) REFERENCES perfiles_puesto(id) ON DELETE SET NULL;
ALTER TABLE public.perfiles_puesto ADD CONSTRAINT perfiles_puesto_created_by_fkey FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.recategorizaciones ADD CONSTRAINT recategorizaciones_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
-- 🔴 FK COMPUESTA, y es lo que hace que esta tabla NO necesite un trigger trg_emp_*. Una FK
-- simple contra empleados(id) garantiza que el empleado existe; NO que sea de la MISMA empresa
-- que la recategorizacion. Se apoya en el indice `empleados_id_empresa_uq`, que ya existe. Es el
-- patron de las 22 FKs compuestas del modelo. Ver db/funciones_y_triggers.sql.
ALTER TABLE public.recategorizaciones ADD CONSTRAINT recat_empleado_empresa_fk FOREIGN KEY (empleado_id, empresa_id) REFERENCES empleados(id, empresa_id);
ALTER TABLE public.recategorizaciones ADD CONSTRAINT recategorizaciones_registrado_por_fkey FOREIGN KEY (registrado_por) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.eventos_agenda ADD CONSTRAINT eventos_agenda_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
-- SIN ON DELETE, igual que objetivos.responsable_id: borrar un usuario con eventos se BLOQUEA.
-- Un evento privado sin autor no lo podria ver nadie — seria una fila inalcanzable.
ALTER TABLE public.eventos_agenda ADD CONSTRAINT eventos_agenda_created_by_fkey FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE public.eventos_agenda ADD CONSTRAINT eventos_agenda_resuelta_por_fkey FOREIGN KEY (resuelta_por) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.parametros_empresa ADD CONSTRAINT parametros_empresa_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE;
ALTER TABLE public.parametros_screening ADD CONSTRAINT parametros_screening_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE;
ALTER TABLE public.reglas_vacaciones_escala ADD CONSTRAINT reglas_vacaciones_escala_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE;
ALTER TABLE public.tipos_ausencia ADD CONSTRAINT tipos_ausencia_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE;


-- ============================================================================
-- INDICES (no derivados de constraints)
-- ============================================================================

CREATE INDEX idx_adjuntos_entidad ON public.adjuntos USING btree (entidad, entidad_id);
CREATE INDEX idx_areas_activo ON public.areas USING btree (activo);
CREATE INDEX idx_areas_empresa ON public.areas USING btree (empresa_id);
CREATE INDEX idx_areas_padre ON public.areas USING btree (area_padre_id);
CREATE INDEX idx_assessment_campanas_empresa ON public.assessment_campanas USING btree (empresa_id);
CREATE INDEX idx_campanas_estado ON public.assessment_campanas USING btree (estado);
CREATE INDEX idx_campanas_tipo ON public.assessment_campanas USING btree (tipo);
CREATE INDEX idx_assessment_links_empresa ON public.assessment_links USING btree (empresa_id);
CREATE INDEX idx_links_campana ON public.assessment_links USING btree (campana_id);
CREATE INDEX idx_links_empleado ON public.assessment_links USING btree (empleado_id);
CREATE INDEX idx_links_estado ON public.assessment_links USING btree (estado);
CREATE INDEX idx_links_token ON public.assessment_links USING btree (token);
CREATE INDEX idx_assessment_resultados_empresa ON public.assessment_resultados USING btree (empresa_id);
CREATE INDEX idx_resultados_campana ON public.assessment_resultados USING btree (campana_id);
CREATE INDEX idx_resultados_candidato ON public.assessment_resultados USING btree (candidato_id);
CREATE INDEX idx_resultados_empleado ON public.assessment_resultados USING btree (empleado_id);
-- ── Indices compuestos (empresa_id, <fecha>) — migracion 115 ─────────────────────────────
-- Los SEIS `..._empresa_<fecha>` / `..._empresa_periodo` de abajo sirven al patron
-- `WHERE empresa_id = $1 ORDER BY <fecha> DESC LIMIT n` de los listados paginados. NO
-- reemplazan a los indices de fecha suelta que estan al lado: esos son los que sirven al MODO
-- CONSOLIDADO, donde la query sale sin filtro de empresa. Los dos modos existen, asi que hacen
-- falta los dos — el porque, con las mediciones, esta en migrations/115_indices_escala.sql.
CREATE INDEX idx_auditoria_created ON public.auditoria USING btree (created_at DESC);
CREATE INDEX idx_auditoria_empresa ON public.auditoria USING btree (empresa_id);
CREATE INDEX idx_auditoria_empresa_created ON public.auditoria USING btree (empresa_id, created_at DESC);
CREATE INDEX idx_auditoria_entidad ON public.auditoria USING btree (entidad, registro_id);
CREATE INDEX idx_auditoria_registro ON public.auditoria USING btree (tabla, registro_id);
CREATE INDEX idx_auditoria_tabla ON public.auditoria USING btree (tabla);
CREATE INDEX idx_auditoria_usuario ON public.auditoria USING btree (usuario_id);
CREATE INDEX idx_candidatos_email ON public.candidatos USING btree (email);
CREATE INDEX idx_candidatos_empresa ON public.candidatos USING btree (empresa_id);
CREATE INDEX idx_candidatos_etapa ON public.candidatos USING btree (etapa);
CREATE INDEX idx_candidatos_vacante ON public.candidatos USING btree (vacante_id);
-- (mig 118) Listado paginado de /candidatos. La `id` final NO es decoracion: sin ella el
-- planner abandona el recorrido ordenado y se lleva las 387 filas de la empresa para devolver
-- 20 (medido). Ver el bloque del tiebreaker en migrations/118_indices_paginacion.sql.
CREATE INDEX idx_candidatos_empresa_created ON public.candidatos USING btree (empresa_id, created_at DESC, id);
CREATE INDEX idx_cap_empresa_id ON public.capacitaciones USING btree (empresa_id);
CREATE INDEX idx_cesiones_empleado ON public.cesiones USING btree (empleado_id);
CREATE INDEX idx_cesiones_empresa ON public.cesiones USING btree (empresa_id);
CREATE INDEX idx_costos_nomina_empleado ON public.costos_nomina USING btree (empleado_id);
CREATE INDEX idx_costos_nomina_empresa ON public.costos_nomina USING btree (empresa_id);
CREATE INDEX idx_costos_nomina_periodo ON public.costos_nomina USING btree (anio, mes);
CREATE INDEX idx_costos_nomina_empresa_periodo ON public.costos_nomina USING btree (empresa_id, anio, mes);
CREATE INDEX idx_ec_capacitacion_id ON public.empleado_capacitacion USING btree (capacitacion_id);
CREATE INDEX idx_ec_empleado_id ON public.empleado_capacitacion USING btree (empleado_id);
CREATE INDEX idx_ec_empresa_id ON public.empleado_capacitacion USING btree (empresa_id);
-- (mig 118) Listado paginado de asignaciones de capacitacion.
CREATE INDEX idx_ec_empresa_created ON public.empleado_capacitacion USING btree (empresa_id, created_at DESC, id);
CREATE INDEX idx_empleados_area ON public.empleados USING btree (area_id);
CREATE INDEX idx_empleados_desempeno ON public.empleados USING btree (desempeno);
CREATE INDEX idx_empleados_domicilio_localidad ON public.empleados USING btree (domicilio_localidad) WHERE (domicilio_localidad IS NOT NULL);
CREATE INDEX idx_empleados_domicilio_provincia ON public.empleados USING btree (domicilio_provincia) WHERE (domicilio_provincia IS NOT NULL);
CREATE INDEX idx_empleados_empresa ON public.empleados USING btree (empresa_id);
CREATE INDEX idx_empleados_estado ON public.empleados USING btree (estado);
CREATE INDEX idx_empleados_manager ON public.empleados USING btree (manager_id);
CREATE INDEX idx_empleados_potencial ON public.empleados USING btree (potencial);
CREATE INDEX idx_empleados_user ON public.empleados USING btree (user_id);
-- (mig 118) 🔴 El listado de /empleados YA paginaba, y hasta este bloque lo hacia SIN ORDER BY
-- (`.range()` pelado en empleado_repo.find_all): paginas no estables. Al agregarle el orden que
-- le faltaba, la query pasa a pedir un orden que ninguna estructura podia darle. El arreglo del
-- bug CREA la necesidad de este indice — por eso viajan juntos.
-- ⚠️ NO lo cubre `empleados_empresa_dni_uq (empresa_id, dni)`: arranca bien pero ordena por DNI.
CREATE INDEX idx_empleados_empresa_apellido ON public.empleados USING btree (empresa_id, apellido, nombre, id);
CREATE INDEX idx_evaluacion_evaluados_empleado ON public.evaluacion_evaluados USING btree (empleado_id);
CREATE INDEX idx_hp_asignacion ON public.horas_proyecto USING btree (asignacion_id);
CREATE INDEX idx_hp_empresa ON public.horas_proyecto USING btree (empresa_id);
CREATE INDEX idx_hp_fecha ON public.horas_proyecto USING btree (fecha);
CREATE INDEX idx_hp_proyecto_fecha ON public.horas_proyecto USING btree (proyecto_id, fecha DESC);
CREATE INDEX idx_hp_proyecto ON public.horas_proyecto USING btree (proyecto_id);
-- Migracion 103. Parciales: las filas del camino viejo (sin cliente ni empleado) no los tocan.
-- idx_hp_cliente sostiene "horas por cliente"; idx_hp_empleado_fecha, "lo que cargo esta
-- persona en este rango" (la tabla de la semana y la suma del dia del tope de horas).
CREATE INDEX idx_hp_cliente ON public.horas_proyecto USING btree (cliente_id) WHERE (cliente_id IS NOT NULL);
CREATE INDEX idx_hp_empleado_fecha ON public.horas_proyecto USING btree (empleado_id, fecha) WHERE (empleado_id IS NOT NULL);
CREATE INDEX idx_inv_asig_empleado ON public.inventario_asignaciones USING btree (empleado_id);
CREATE INDEX idx_inv_asig_empresa ON public.inventario_asignaciones USING btree (empresa_id);
CREATE INDEX idx_inv_asig_item ON public.inventario_asignaciones USING btree (item_id);
-- (mig 118) Listado paginado de asignaciones de inventario. 🔑 PARCIAL, y no es un adorno: el
-- repo NUNCA lista las devueltas (`find_all` arranca con `.is_("fecha_devolucion","null")`
-- fijo). Un indice pleno cargaria las devueltas para descartarlas con un nodo Filter en cada
-- pagina — medido: 4,9x mas lento que el parcial, y la brecha crece sola porque las
-- devoluciones se acumulan para siempre.
-- ⚠️ El historial de un item (`find_historial`, con devueltas y sin empresa) NO lo usa ni puede:
-- lo sigue resolviendo `idx_inv_asig_item`, que por eso queda.
CREATE INDEX idx_inv_asig_empresa_fecha ON public.inventario_asignaciones USING btree (empresa_id, fecha_asignacion DESC, id) WHERE (fecha_devolucion IS NULL);
CREATE UNIQUE INDEX idx_inv_asig_item_activo ON public.inventario_asignaciones USING btree (item_id) WHERE (fecha_devolucion IS NULL);
CREATE INDEX idx_inv_items_empresa ON public.inventario_items USING btree (empresa_id);
CREATE INDEX idx_inv_items_estado ON public.inventario_items USING btree (estado);
-- (mig 118) Listado paginado del catalogo de items. Ordena por `nombre` y no por una fecha,
-- igual que idx_vp_empresa_periodo ordena por `periodo`: lo que define al patron es la FORMA de
-- la query (igualdad por empresa + orden + LIMIT), no que la columna sea temporal.
CREATE INDEX idx_inv_items_empresa_nombre ON public.inventario_items USING btree (empresa_id, nombre, id);
CREATE INDEX idx_obj_empresa ON public.objetivos USING btree (empresa_id);
CREATE INDEX idx_obj_estado ON public.objetivos USING btree (estado);
CREATE INDEX idx_obj_responsable ON public.objetivos USING btree (responsable_id);
CREATE INDEX idx_obj_parent ON public.objetivos USING btree (parent_id);
-- Dedup del import de objetivos (mig 111). La clave natural es lo que identifica una FILA DE LA
-- PLANILLA: las dos columnas que el import declara requeridas, titulo y responsable. NO va el
-- titulo solo —dos responsables pueden tener legitimamente el mismo objetivo— ni `fecha_entrega`,
-- que es NULLABLE y desactivaria el indice en silencio para todo objetivo sin fecha.
-- 🔄 Migracion 114: se le agrego `lower(periodicidad)` como CUARTA expresion. Con la clave de
-- tres, "Cerrar el trimestre" mensual y anual del mismo responsable colisionaban y el segundo
-- rebotaba con 23505 — una clave mas angosta que la identidad real rechaza datos buenos. El
-- `lower()` va por el mismo motivo que el de `titulo`: es texto que RRHH escribe a mano.
-- 🔄 Migracion 119: `tipo` como QUINTA. Mismo argumento, un eje mas — un anual tiene
-- `periodicidad = ''` SIEMPRE (un anual ya es del año) y un operativo con el campo vacio tambien,
-- asi que para ese par la cuarta columna no distingue y "Cerrar el trimestre" anual y operativo
-- del mismo responsable volvian a colisionar. Son dos objetivos legitimos: viven en dos vistas
-- distintas y no se comparten.
-- 🔴 `tipo` va SIN `lower()`, al reves que las otras dos: no lo escribe una persona, sale de un
-- CHECK cerrado de dos literales en minuscula. Un `lower()` ahi no podria cambiar ningun
-- resultado y seria una tercera expresion a evaluar en cada escritura.
-- ⚠️ El NOMBRE se conserva desde la 111: esa migracion y la 114 lo citan literalmente en sus
-- queries de verificacion posterior, y las dos siguen en el repo como historial.
CREATE UNIQUE INDEX ux_objetivo_responsable_titulo ON public.objetivos USING btree (empresa_id, responsable_id, lower(titulo), lower(periodicidad), tipo);
CREATE INDEX idx_obj_resp_user ON public.objetivo_responsables USING btree (user_id);
CREATE INDEX idx_oauth_states_expires_at ON public.oauth_states USING btree (expires_at);
CREATE INDEX idx_offboarding_activos_empresa ON public.offboarding_activos USING btree (empresa_id);
CREATE INDEX idx_offboarding_activos_estado ON public.offboarding_activos USING btree (estado);
CREATE INDEX idx_offboarding_activos_instancia ON public.offboarding_activos USING btree (instancia_id);
CREATE INDEX idx_offboarding_instancias_empleado ON public.offboarding_instancias USING btree (empleado_id);
CREATE INDEX idx_offboarding_instancias_empresa ON public.offboarding_instancias USING btree (empresa_id);
CREATE INDEX idx_offboarding_instancias_estado ON public.offboarding_instancias USING btree (estado);
CREATE INDEX idx_onboarding_instancias_empleado ON public.onboarding_instancias USING btree (empleado_id);
CREATE INDEX idx_onboarding_instancias_empresa ON public.onboarding_instancias USING btree (empresa_id);
CREATE INDEX idx_onboarding_instancias_estado ON public.onboarding_instancias USING btree (estado);
CREATE INDEX idx_onboarding_progreso_empresa ON public.onboarding_progreso USING btree (empresa_id);
CREATE INDEX idx_onboarding_progreso_estado ON public.onboarding_progreso USING btree (estado);
CREATE INDEX idx_onboarding_progreso_instancia ON public.onboarding_progreso USING btree (instancia_id);
CREATE INDEX idx_onboarding_tareas_empresa ON public.onboarding_tareas USING btree (empresa_id);
CREATE INDEX idx_onboarding_tareas_orden ON public.onboarding_tareas USING btree (template_id, orden);
CREATE INDEX idx_onboarding_tareas_template ON public.onboarding_tareas USING btree (template_id);
CREATE INDEX idx_onboarding_templates_activo ON public.onboarding_templates USING btree (activo);
CREATE INDEX idx_onboarding_templates_area ON public.onboarding_templates USING btree (area_id);
CREATE INDEX idx_onboarding_templates_empresa ON public.onboarding_templates USING btree (empresa_id);
CREATE INDEX idx_onboarding_templates_privadas ON public.onboarding_templates USING btree (empresa_id, created_by) WHERE (es_publica = false);
CREATE INDEX idx_periodos_check ON public.periodos_cerrados USING btree (empresa_id, modulo, estado);
CREATE INDEX idx_planes_carrera_empleado ON public.planes_carrera USING btree (empleado_id);
CREATE INDEX idx_planes_carrera_empresa ON public.planes_carrera USING btree (empresa_id);
CREATE INDEX idx_planes_carrera_estado ON public.planes_carrera USING btree (estado);
CREATE INDEX idx_hitos_estado ON public.planes_carrera_hitos USING btree (estado);
CREATE INDEX idx_hitos_plan ON public.planes_carrera_hitos USING btree (plan_id);
CREATE INDEX idx_planes_carrera_hitos_empresa ON public.planes_carrera_hitos USING btree (empresa_id);
CREATE INDEX idx_presupuesto_areas_area ON public.presupuesto_areas USING btree (area_id);
CREATE INDEX idx_presupuesto_areas_empresa ON public.presupuesto_areas USING btree (empresa_id);
CREATE INDEX idx_presupuesto_areas_periodo ON public.presupuesto_areas USING btree (anio, mes);
CREATE INDEX idx_pa_emp_empresa ON public.proyecto_asignaciones USING btree (empleado_empresa_id);
CREATE INDEX idx_pa_empleado ON public.proyecto_asignaciones USING btree (empleado_id);
CREATE INDEX idx_pa_proyecto ON public.proyecto_asignaciones USING btree (proyecto_id);
CREATE INDEX idx_proyectos_empresa ON public.proyectos USING btree (empresa_id);
CREATE INDEX idx_proyectos_estado ON public.proyectos USING btree (estado);
CREATE INDEX idx_reportes_created_at ON public.reportes_generados USING btree (created_at DESC);
CREATE INDEX idx_reportes_generados_empresa ON public.reportes_generados USING btree (empresa_id);
CREATE INDEX idx_sa_empleado_id ON public.solicitudes_ausencia USING btree (empleado_id);
CREATE INDEX idx_sa_empresa_id ON public.solicitudes_ausencia USING btree (empresa_id);
CREATE INDEX idx_sa_empresa_fecha ON public.solicitudes_ausencia USING btree (empresa_id, fecha_desde DESC);
CREATE INDEX idx_solicitudes_vacaciones_empresa_tipo ON public.solicitudes_vacaciones USING btree (empresa_id, tipo);
CREATE INDEX idx_sv_empleado_id ON public.solicitudes_vacaciones USING btree (empleado_id);
CREATE INDEX idx_sv_empresa_id ON public.solicitudes_vacaciones USING btree (empresa_id);
CREATE INDEX idx_sv_empresa_fecha ON public.solicitudes_vacaciones USING btree (empresa_id, fecha_desde DESC);
CREATE INDEX idx_sv_periodo ON public.solicitudes_vacaciones USING btree (empleado_id, periodo) WHERE (periodo IS NOT NULL);
CREATE INDEX idx_vp_empleado ON public.vacaciones_pendientes USING btree (empleado_id);
CREATE INDEX idx_vp_empresa ON public.vacaciones_pendientes USING btree (empresa_id);
CREATE INDEX idx_vp_empresa_periodo ON public.vacaciones_pendientes USING btree (empresa_id, periodo DESC);
CREATE INDEX idx_vacantes_area ON public.vacantes USING btree (area_id);
CREATE INDEX idx_esp_empresa ON public.empleado_superior_pendiente USING btree (empresa_id);
-- Identidad de una ausencia (mig 089) y de una vacacion (mig 110): sostienen la idempotencia del
-- import mensual — `on_conflict` de PostgREST EXIGE una constraint unica. NO prohiben
-- solapamientos parciales, solo el duplicado exacto.
-- ⚠️ Las columnas NO son las mismas: en ausencias el tipo es `tipo_id` (FK a tipos_ausencia); en
-- vacaciones es `tipo` (varchar con CHECK de cuatro valores). Las 8 columnas son NOT NULL, asi
-- que ningun NULL desactiva los indices en silencio.
CREATE UNIQUE INDEX uq_ausencia_empleado_rango_tipo ON public.solicitudes_ausencia USING btree (empleado_id, fecha_desde, fecha_hasta, tipo_id);
CREATE UNIQUE INDEX uq_vacacion_empleado_rango_tipo ON public.solicitudes_vacaciones USING btree (empleado_id, fecha_desde, fecha_hasta, tipo);
CREATE UNIQUE INDEX uq_integracion_remitente_sistema ON public.usuario_integraciones USING btree ((es_remitente_sistema)) WHERE es_remitente_sistema;
-- Codigo de vacante (mig 097): GLOBAL, no por empresa —la casilla que recibe los CVs es una
-- sola—, y sobre upper() porque el lookup del matcher es case-insensitive. Si la unicidad no
-- usara el mismo criterio que la consulta, VAC-0001 y vac-0001 coexistirian y el lookup
-- encontraria DOS filas, que en maybe_single() es un 500.
CREATE UNIQUE INDEX vacantes_codigo_uq ON public.vacantes USING btree (upper(codigo));
-- Idempotencia de la ingesta de CVs (mig 098). PARCIAL: solo indexa lo que vino de Gmail, asi
-- los candidatos manuales —que tienen los dos campos en NULL— conviven sin colisionar.
CREATE UNIQUE INDEX candidatos_cv_gmail_uq ON public.candidatos USING btree (empresa_id, gmail_message_id, cv_sha256) WHERE ((gmail_message_id IS NOT NULL) AND (cv_sha256 IS NOT NULL));
CREATE INDEX idx_candidatos_gmail_message ON public.candidatos USING btree (gmail_message_id) WHERE (gmail_message_id IS NOT NULL);
CREATE UNIQUE INDEX uq_plantilla_empresa_clave ON public.plantillas_mail USING btree (empresa_id, clave) WHERE (empresa_id IS NOT NULL);
CREATE UNIQUE INDEX uq_plantilla_global_clave ON public.plantillas_mail USING btree (clave) WHERE (empresa_id IS NULL);
CREATE INDEX idx_mail_enviado_idempotencia ON public.mail_enviado USING btree (plantilla_clave, empleado_id, created_at DESC);
CREATE INDEX idx_mail_enviado_empresa ON public.mail_enviado USING btree (empresa_id, created_at DESC);
CREATE INDEX idx_vacantes_empresa ON public.vacantes USING btree (empresa_id);
CREATE INDEX idx_vacantes_estado ON public.vacantes USING btree (estado);
CREATE INDEX idx_vacantes_responsable ON public.vacantes USING btree (responsable_id);
-- (mig 118) Listado paginado de /vacantes. Es la tabla mas chica de las seis (200 filas) y aun
-- asi el planner lo elige: no entro por volumen sino porque `vacantes` acumula historico (las
-- cerradas no se borran) y el listado siempre pide las ultimas.
CREATE INDEX idx_vacantes_empresa_created ON public.vacantes USING btree (empresa_id, created_at DESC, id);
-- Migracion 085. Los indices son PARCIALES porque en SQL NULL <> NULL: un UNIQUE comun sobre
-- empresa_id dejaria entrar varias filas globales y la lectura elegiria una al azar.
-- El de parametros_empresa indexa la CONSTANTE (empresa_id IS NULL) = TRUE, asi que solo
-- admite UNA global. El de la escala indexa antiguedad_anios: la escala global son VARIAS
-- filas y lo que no puede repetirse es el punto de corte.
CREATE UNIQUE INDEX ux_parametros_empresa_por_empresa ON public.parametros_empresa USING btree (empresa_id) WHERE (empresa_id IS NOT NULL);
CREATE UNIQUE INDEX ux_parametros_empresa_global ON public.parametros_empresa USING btree (((empresa_id IS NULL))) WHERE (empresa_id IS NULL);
CREATE UNIQUE INDEX ux_parametros_screening_por_empresa ON public.parametros_screening USING btree (empresa_id) WHERE (empresa_id IS NOT NULL);
CREATE UNIQUE INDEX ux_parametros_screening_global ON public.parametros_screening USING btree (((empresa_id IS NULL))) WHERE (empresa_id IS NULL);
CREATE INDEX idx_candidatos_clasificacion ON public.candidatos USING btree (clasificacion_ia) WHERE (clasificacion_ia IS NOT NULL);
CREATE UNIQUE INDEX ux_escala_por_empresa ON public.reglas_vacaciones_escala USING btree (empresa_id, antiguedad_anios) WHERE (empresa_id IS NOT NULL);
CREATE UNIQUE INDEX ux_escala_global ON public.reglas_vacaciones_escala USING btree (antiguedad_anios) WHERE (empresa_id IS NULL);
CREATE UNIQUE INDEX ux_tipos_ausencia_nombre_por_empresa ON public.tipos_ausencia USING btree (empresa_id, nombre) WHERE (empresa_id IS NOT NULL);
CREATE UNIQUE INDEX ux_tipos_ausencia_nombre_global ON public.tipos_ausencia USING btree (nombre) WHERE (empresa_id IS NULL);
CREATE INDEX idx_tipos_ausencia_empresa ON public.tipos_ausencia USING btree (empresa_id) WHERE (empresa_id IS NOT NULL);
CREATE INDEX idx_tipos_ausencia_padre ON public.tipos_ausencia USING btree (padre_id) WHERE (padre_id IS NOT NULL);
-- Migracion 102, reemplazado por el GLOBAL en la 108. Unicidad CASE-INSENSITIVE: con RRHH
-- tipeando a mano, "Acme" y "ACME" son el caso normal. El precedente de lo que pasa sin unicidad
-- es `proyectos`, que no tiene ninguna y por eso deduplica con un cache en memoria de Python
-- (services/_nomina_proyectos.py).
-- 🔴 Desde la 109 el alcance es TODA la tabla, no (empresa, nombre): un cliente no cuelga de
-- ninguna empresa, asi que "Acme" es uno solo para todo el sistema.
-- ⚠️ Un indice por expresion no sirve como target de on_conflict; clientes no se upsertea.
CREATE UNIQUE INDEX ux_clientes_nombre_global ON public.clientes USING btree (lower(nombre));
-- Migracion 104. Las tres preguntas que la tabla existe para responder: que paso recientemente,
-- cuantas veces se probo ESTE dni, y cuantos dnis probo ESTA ip.
-- Migracion 105. La unicidad es lo que hace que un token identifique a UNA sesion.
CREATE UNIQUE INDEX ux_sesiones_horas_token ON public.sesiones_horas USING btree (token_hash);
CREATE INDEX idx_sesiones_horas_expira ON public.sesiones_horas USING btree (expires_at);
-- Migracion 106. Parcial: el camino viejo no manda idempotencia y no lo toca.
CREATE UNIQUE INDEX ux_hp_idempotencia ON public.horas_proyecto USING btree (idempotencia) WHERE (idempotencia IS NOT NULL);
CREATE INDEX idx_intentos_created ON public.intentos_identificacion USING btree (created_at DESC);
CREATE INDEX idx_intentos_dni ON public.intentos_identificacion USING btree (dni, created_at DESC);
CREATE INDEX idx_intentos_ip ON public.intentos_identificacion USING btree (ip, created_at DESC) WHERE (ip IS NOT NULL);

-- ── Migracion 113 (2026-08-13) ───────────────────────────────────────────────
-- 🔴 TODOS ESTOS INDICES ESTAN DIMENSIONADOS PARA ~10 EMPRESAS Y ~1000 COLABORADORES, no para
-- los 2 y 31 de hoy. Una tabla se crea UNA vez; agregar un indice despues del handoff a
-- infraestructura es coordinar. Cada uno dice contra que consulta esta puesto.
-- El patron que se repite es el PARCIAL: en las columnas de fecha nuevas la enorme mayoria de
-- las filas tiene NULL, y un indice completo indexaria 1000 filas para servir 10.

-- Unicidad GLOBAL y case-insensitive del nombre del perfil. Lo escribe RRHH a mano: "Analista
-- SSR" y "analista ssr" son el mismo perfil. Molde: ux_clientes_nombre_global.
CREATE UNIQUE INDEX ux_perfiles_puesto_nombre_global ON public.perfiles_puesto USING btree (lower(nombre));
-- Identidad de una formacion cargada SIN empleado matcheado (mig 116). Reemplaza a
-- `UNIQUE (capacitacion_id, empleado_id)` en esas filas: con empleado_id NULL esa unique
-- deja de proteger (dos NULL son distintos en SQL) y el import del Excel duplicaria en
-- silencio. El coalesce NO es cosmetico: sin el, dos filas sin anio vuelven a ser
-- distintas entre si y el indice no cubre justo las filas incompletas.
CREATE UNIQUE INDEX ux_ec_nombre_libre ON public.empleado_capacitacion USING btree (capacitacion_id, lower(nombre_libre), COALESCE(anio, ''::text), COALESCE(lower(mes), ''::text)) WHERE ((empleado_id IS NULL) AND (nombre_libre IS NOT NULL));
-- Listado por defecto: WHERE activo ORDER BY nombre. Parcial + clave `nombre` = sirve al filtro
-- Y al orden, sin ordenar en memoria.
CREATE INDEX idx_perfiles_puesto_activos ON public.perfiles_puesto USING btree (nombre) WHERE activo;

-- El historial de UNA persona, en su ficha: WHERE empleado_id = ? ORDER BY fecha_efectiva DESC.
CREATE INDEX idx_recat_empleado ON public.recategorizaciones USING btree (empleado_id, fecha_efectiva DESC);
-- 🔴 El listado del modulo, PAGINADO: WHERE empresa_id = ? ORDER BY fecha_efectiva DESC LIMIT.
-- Sin este, con 10 empresas cada pagina lee la tabla entera y la ordena en memoria para devolver
-- 20 filas — y el sort se paga de nuevo en CADA pagina.
CREATE INDEX idx_recat_empresa_fecha ON public.recategorizaciones USING btree (empresa_id, fecha_efectiva DESC);

-- La consulta del dashboard, que corre en cada carga de pantalla:
--   WHERE empresa_id = ? AND NOT resuelta AND fecha <= current_date + dias_aviso
-- 🔴 PARCIAL sobre NOT resuelta: los resueltos se acumulan para siempre y el dashboard no los
-- mira nunca. El indice completo creceria sin techo; este se queda en lo pendiente.
CREATE INDEX idx_eventos_agenda_pendientes ON public.eventos_agenda USING btree (empresa_id, fecha) WHERE (NOT resuelta);
-- El segundo predicado de la visibilidad: `es_publica OR created_by = <yo>`. Los publicos entran
-- por el indice de arriba; este sirve la otra mitad.
CREATE INDEX idx_eventos_agenda_privados_autor ON public.eventos_agenda USING btree (created_by) WHERE (NOT es_publica);

-- "Proximos ingresos / bajas de los proximos N dias". Parciales: en cualquier momento hay un
-- punado de personas con fecha prevista y ~990 con NULL. Sin ellos el bloque del dashboard
-- escanea el padron entero en cada carga. Mismo patron que idx_empleados_domicilio_provincia.
-- Sin `empresa_id` adelante a proposito: el parcial ya reduce a decenas de filas, y con empresa
-- primero el indice dejaria de servir a la vista consolidada.
CREATE INDEX idx_empleados_ingreso_previsto ON public.empleados USING btree (fecha_ingreso_prevista) WHERE (fecha_ingreso_prevista IS NOT NULL);
CREATE INDEX idx_empleados_baja_prevista ON public.empleados USING btree (fecha_baja_prevista) WHERE (fecha_baja_prevista IS NOT NULL);

-- La alerta de documentos por vencer. DOBLEMENTE parcial: la mayoria de los adjuntos (un CV, una
-- foto) no vence nunca, y los eliminados no tienen por que alertar. `adjuntos` es de las tablas
-- que mas crece con 1000 colaboradores.
-- ⚠️ `estado = 'activo'` es parte del indice: la query de la alerta TIENE que incluirlo o el
-- planner no lo va a poder usar.
CREATE INDEX idx_adjuntos_vencimiento ON public.adjuntos USING btree (fecha_vencimiento) WHERE ((fecha_vencimiento IS NOT NULL) AND (estado = 'activo'::text));

-- "Vacantes de este perfil", y sobre todo: 🔴 POSTGRES NO INDEXA LAS FK AUTOMATICAMENTE. Con
-- ON DELETE SET NULL, borrar un perfil obliga a buscar las filas hijas — sin indice eso es un
-- scan de `vacantes` entera por cada borrado.
CREATE INDEX idx_vacantes_perfil_puesto ON public.vacantes USING btree (perfil_puesto_id) WHERE (perfil_puesto_id IS NOT NULL);


-- ============================================================================
-- FIN DEL SNAPSHOT
-- ============================================================================
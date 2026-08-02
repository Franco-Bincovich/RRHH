-- ============================================================================
-- schema.sql — SNAPSHOT DE RECONSTRUCCION de la base de produccion (RRHH / HR Karstec)
-- ============================================================================
--
-- ESTE ES EL ARTEFACTO DE RECONSTRUCCION AUTORITATIVO.
-- Refleja el estado REAL de la base de produccion, leido directamente del catalogo
-- de Postgres (information_schema / pg_catalog). Incluye TODO: tablas, columnas,
-- defaults, constraints (PK/FK/UNIQUE/CHECK, incluidas las compuestas del modelo
-- multiempresa), e indices.
--
-- POR QUE EXISTE:
-- Las 74 migraciones incrementales (001..074) NO reconstruyen la base desde cero
-- de forma confiable: tienen dependencias de orden rotas, operaciones no
-- idempotentes, y parte del modelo multiempresa fue aplicado a mano en produccion
-- (drift) y versionado retroactivamente de forma incompleta. Las migraciones
-- quedan como HISTORIAL de como se llego hasta aca; este schema.sql es la fuente
-- de verdad para RECONSTRUIR.
--
-- COMO SE GENERO: leido del catalogo de la base de produccion via el catalogo de
-- Postgres. Generado: 2026-07-16.
--
-- COMO USARLO EN UN REBUILD:
--   1. Crear una base vacia.
--   2. Correr este schema.sql (crea todo el esquema 'public').
--   3. NO correr las migraciones 001..074 encima (son historial, no bootstrap).
--
-- NOTA: no incluye datos (solo estructura), ni objetos de los esquemas internos de
-- Supabase (auth, storage). La unica referencia externa es users.id -> auth.users(id).
-- ============================================================================

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

-- Extension para gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

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
    es_principal boolean DEFAULT false
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
CREATE TABLE public.assessment_reportes (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    resultado_id uuid NOT NULL,
    tipo_reporte character varying(30) NOT NULL,
    titulo character varying(200) NOT NULL,
    contenido jsonb NOT NULL DEFAULT '{}'::jsonb,
    resumen text,
    generado_por character varying(10) NOT NULL DEFAULT 'ia'::character varying,
    modelo_ia character varying(100),
    url_pdf text,
    storage_path text,
    visible_empleado boolean NOT NULL DEFAULT false,
    created_by uuid,
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
    busqueda_congelada text
);
CREATE TABLE public.capacitaciones (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    nombre text NOT NULL,
    descripcion text,
    categoria text,
    duracion_horas numeric,
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
CREATE TABLE public.configuracion_empresa (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    nombre character varying(200) NOT NULL DEFAULT 'Mi Empresa'::character varying,
    logo_url text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    empresa_id uuid NOT NULL
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
CREATE TABLE public.documentos_empleado (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empleado_id uuid NOT NULL,
    tipo character varying(30) NOT NULL,
    nombre_archivo character varying(255) NOT NULL,
    descripcion character varying(500),
    bucket character varying(50) NOT NULL DEFAULT 'documentos'::character varying,
    storage_path text NOT NULL,
    tamano_bytes bigint,
    mime_type character varying(100),
    estado character varying(20) NOT NULL DEFAULT 'activo'::character varying,
    subido_por uuid,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    empresa_id uuid NOT NULL
);
CREATE TABLE public.empleado_capacitacion (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    capacitacion_id uuid NOT NULL,
    empleado_id uuid NOT NULL,
    estado text NOT NULL DEFAULT 'pendiente'::text,
    fecha_asignacion date,
    fecha_limite date,
    fecha_completado date,
    certificado_url text,
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
    dias_vacaciones_asignados integer NOT NULL DEFAULT 14,
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
    organismo text,
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
    motivo_baja text
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
CREATE TABLE public.ev_ciclos (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    nombre text NOT NULL,
    plantilla_id uuid NOT NULL,
    fecha_inicio date NOT NULL,
    fecha_fin date NOT NULL,
    estado text NOT NULL DEFAULT 'abierto'::text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.ev_criterios (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    plantilla_id uuid NOT NULL,
    nombre text NOT NULL,
    descripcion text,
    peso numeric NOT NULL DEFAULT 1,
    orden integer NOT NULL DEFAULT 1,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.ev_instancias (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    ciclo_id uuid NOT NULL,
    empleado_id uuid NOT NULL,
    evaluador_id uuid,
    estado text NOT NULL DEFAULT 'borrador'::text,
    puntaje_global numeric,
    comentario_general text,
    fecha_evaluacion date,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.ev_plantillas (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    nombre text NOT NULL,
    descripcion text,
    tipo_escala text NOT NULL,
    escala_min integer,
    escala_max integer,
    opciones_cualitativas jsonb,
    activa boolean NOT NULL DEFAULT true,
    area_id uuid,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.ev_resultados (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    instancia_id uuid NOT NULL,
    criterio_id uuid NOT NULL,
    puntaje numeric,
    valor text,
    comentario text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
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
    asignacion_id uuid NOT NULL,
    proyecto_id uuid NOT NULL,
    empresa_id uuid NOT NULL,
    empleado_empresa_id uuid NOT NULL,
    fecha date NOT NULL,
    horas numeric(6,2) NOT NULL,
    valor_hora_snapshot numeric(16,2) NOT NULL,
    descripcion text,
    cargado_por uuid,
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
CREATE TABLE public.notificaciones (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    tipo character varying(30) NOT NULL,
    titulo character varying(200) NOT NULL,
    mensaje text NOT NULL,
    referencia_tipo character varying(50),
    referencia_id uuid,
    leida boolean NOT NULL DEFAULT false,
    leida_en timestamp with time zone,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.notificaciones_config (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    tipo_evento character varying(30) NOT NULL,
    canal character varying(10) NOT NULL,
    activo boolean NOT NULL DEFAULT true,
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
CREATE TABLE public.objetivos (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    empresa_id uuid NOT NULL,
    responsable_id uuid NOT NULL,
    titulo text NOT NULL,
    descripcion text,
    prioridad text NOT NULL DEFAULT 'media'::text,
    estado text NOT NULL DEFAULT 'por_hacer'::text,
    fecha_entrega date,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
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
CREATE TABLE public.sucesion_posiciones (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    cargo character varying(150) NOT NULL,
    area_id uuid,
    titular_id uuid,
    sucesor_primario_id uuid,
    sucesor_secundario_id uuid,
    nivel_preparacion_primario character varying(20),
    nivel_preparacion_secundario character varying(20),
    criticidad character varying(10) NOT NULL DEFAULT 'media'::character varying,
    estado character varying(20) NOT NULL DEFAULT 'activo'::character varying,
    notas text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    empresa_id uuid NOT NULL
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
CREATE TABLE public.users (
    id uuid NOT NULL,
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
    conocimientos_tecnicos text
);


-- ============================================================================
-- CONSTRAINTS (PK -> UNIQUE -> CHECK -> FK)
-- ============================================================================

ALTER TABLE public.adjuntos ADD CONSTRAINT adjuntos_pkey PRIMARY KEY (id);
ALTER TABLE public.areas ADD CONSTRAINT areas_pkey PRIMARY KEY (id);
ALTER TABLE public.assessment_campanas ADD CONSTRAINT assessment_campanas_pkey PRIMARY KEY (id);
ALTER TABLE public.assessment_links ADD CONSTRAINT assessment_links_pkey PRIMARY KEY (id);
ALTER TABLE public.assessment_reportes ADD CONSTRAINT assessment_reportes_pkey PRIMARY KEY (id);
ALTER TABLE public.assessment_resultados ADD CONSTRAINT assessment_resultados_pkey PRIMARY KEY (id);
ALTER TABLE public.auditoria ADD CONSTRAINT auditoria_pkey PRIMARY KEY (id);
ALTER TABLE public.candidatos ADD CONSTRAINT candidatos_pkey PRIMARY KEY (id);
ALTER TABLE public.capacitaciones ADD CONSTRAINT capacitaciones_pkey PRIMARY KEY (id);
ALTER TABLE public.cesiones ADD CONSTRAINT cesiones_pkey PRIMARY KEY (id);
ALTER TABLE public.configuracion_empresa ADD CONSTRAINT configuracion_empresa_pkey PRIMARY KEY (id);
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_pkey PRIMARY KEY (id);
ALTER TABLE public.documentos_empleado ADD CONSTRAINT documentos_empleado_pkey PRIMARY KEY (id);
ALTER TABLE public.empleado_capacitacion ADD CONSTRAINT empleado_capacitacion_pkey PRIMARY KEY (id);
ALTER TABLE public.empleados ADD CONSTRAINT empleados_pkey PRIMARY KEY (id);
ALTER TABLE public.empresas ADD CONSTRAINT empresas_pkey PRIMARY KEY (id);
ALTER TABLE public.ev_ciclos ADD CONSTRAINT ev_ciclos_pkey PRIMARY KEY (id);
ALTER TABLE public.ev_criterios ADD CONSTRAINT ev_criterios_pkey PRIMARY KEY (id);
ALTER TABLE public.ev_instancias ADD CONSTRAINT ev_instancias_pkey PRIMARY KEY (id);
ALTER TABLE public.ev_plantillas ADD CONSTRAINT ev_plantillas_pkey PRIMARY KEY (id);
ALTER TABLE public.ev_resultados ADD CONSTRAINT ev_resultados_pkey PRIMARY KEY (id);
ALTER TABLE public.evaluacion_equivalencias ADD CONSTRAINT evaluacion_equivalencias_pkey PRIMARY KEY (id);
ALTER TABLE public.evaluacion_evaluados ADD CONSTRAINT evaluacion_evaluados_pkey PRIMARY KEY (id);
ALTER TABLE public.evaluacion_lotes ADD CONSTRAINT evaluacion_lotes_pkey PRIMARY KEY (id);
ALTER TABLE public.evaluacion_resultados ADD CONSTRAINT evaluacion_resultados_pkey PRIMARY KEY (id);
ALTER TABLE public.horas_proyecto ADD CONSTRAINT horas_proyecto_pkey PRIMARY KEY (id);
ALTER TABLE public.inventario_asignaciones ADD CONSTRAINT inventario_asignaciones_pkey PRIMARY KEY (id);
ALTER TABLE public.inventario_items ADD CONSTRAINT inventario_items_pkey PRIMARY KEY (id);
ALTER TABLE public.notificaciones ADD CONSTRAINT notificaciones_pkey PRIMARY KEY (id);
ALTER TABLE public.notificaciones_config ADD CONSTRAINT notificaciones_config_pkey PRIMARY KEY (id);
ALTER TABLE public.oauth_states ADD CONSTRAINT oauth_states_pkey PRIMARY KEY (id);
ALTER TABLE public.objetivos ADD CONSTRAINT objetivos_pkey PRIMARY KEY (id);
ALTER TABLE public.offboarding_activos ADD CONSTRAINT offboarding_activos_pkey PRIMARY KEY (id);
ALTER TABLE public.offboarding_instancias ADD CONSTRAINT offboarding_instancias_pkey PRIMARY KEY (id);
ALTER TABLE public.onboarding_instancias ADD CONSTRAINT onboarding_instancias_pkey PRIMARY KEY (id);
ALTER TABLE public.onboarding_progreso ADD CONSTRAINT onboarding_progreso_pkey PRIMARY KEY (id);
ALTER TABLE public.onboarding_tareas ADD CONSTRAINT onboarding_tareas_pkey PRIMARY KEY (id);
ALTER TABLE public.onboarding_templates ADD CONSTRAINT onboarding_templates_pkey PRIMARY KEY (id);
ALTER TABLE public.parametros_empresa ADD CONSTRAINT parametros_empresa_pkey PRIMARY KEY (id);
ALTER TABLE public.periodos_cerrados ADD CONSTRAINT periodos_cerrados_pkey PRIMARY KEY (id);
ALTER TABLE public.planes_carrera ADD CONSTRAINT planes_carrera_pkey PRIMARY KEY (id);
ALTER TABLE public.planes_carrera_hitos ADD CONSTRAINT planes_carrera_hitos_pkey PRIMARY KEY (id);
ALTER TABLE public.presupuesto_areas ADD CONSTRAINT presupuesto_areas_pkey PRIMARY KEY (id);
ALTER TABLE public.proyecto_asignaciones ADD CONSTRAINT proyecto_asignaciones_pkey PRIMARY KEY (id);
ALTER TABLE public.proyectos ADD CONSTRAINT proyectos_pkey PRIMARY KEY (id);
ALTER TABLE public.reglas_vacaciones_escala ADD CONSTRAINT reglas_vacaciones_escala_pkey PRIMARY KEY (id);
ALTER TABLE public.reportes_generados ADD CONSTRAINT reportes_generados_pkey PRIMARY KEY (id);
ALTER TABLE public.solicitudes_ausencia ADD CONSTRAINT solicitudes_ausencia_pkey PRIMARY KEY (id);
ALTER TABLE public.solicitudes_vacaciones ADD CONSTRAINT solicitudes_vacaciones_pkey PRIMARY KEY (id);
ALTER TABLE public.sucesion_posiciones ADD CONSTRAINT sucesion_posiciones_pkey PRIMARY KEY (id);
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
ALTER TABLE public.areas ADD CONSTRAINT areas_codigo_key UNIQUE (codigo);
ALTER TABLE public.areas ADD CONSTRAINT areas_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.assessment_campanas ADD CONSTRAINT assessment_campanas_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.assessment_links ADD CONSTRAINT assessment_links_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.assessment_links ADD CONSTRAINT assessment_links_token_key UNIQUE (token);
ALTER TABLE public.assessment_reportes ADD CONSTRAINT assessment_reportes_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.assessment_resultados ADD CONSTRAINT assessment_resultados_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.assessment_resultados ADD CONSTRAINT assessment_resultados_link_id_key UNIQUE (link_id);
ALTER TABLE public.candidatos ADD CONSTRAINT candidatos_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.capacitaciones ADD CONSTRAINT capacitaciones_id_empresa_id_key UNIQUE (id, empresa_id);
ALTER TABLE public.configuracion_empresa ADD CONSTRAINT configuracion_empresa_empresa_uq UNIQUE (empresa_id);
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_empleado_id_anio_mes_key UNIQUE (empleado_id, anio, mes);
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.documentos_empleado ADD CONSTRAINT documentos_empleado_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.empleado_capacitacion ADD CONSTRAINT empleado_capacitacion_capacitacion_id_empleado_id_key UNIQUE (capacitacion_id, empleado_id);
ALTER TABLE public.empleados ADD CONSTRAINT empleados_email_corporativo_key UNIQUE (email_corporativo);
ALTER TABLE public.empleados ADD CONSTRAINT empleados_empresa_dni_uq UNIQUE (empresa_id, dni);
ALTER TABLE public.empleados ADD CONSTRAINT empleados_id_empresa_uq UNIQUE (id, empresa_id);
ALTER TABLE public.empleados ADD CONSTRAINT empleados_legajo_empresa_key UNIQUE (legajo, empresa_id);
ALTER TABLE public.empresas ADD CONSTRAINT empresas_cuit_uq UNIQUE (cuit);
ALTER TABLE public.empresas ADD CONSTRAINT empresas_nombre_key UNIQUE (nombre);
ALTER TABLE public.ev_ciclos ADD CONSTRAINT ev_ciclos_id_empresa_id_key UNIQUE (id, empresa_id);
ALTER TABLE public.ev_instancias ADD CONSTRAINT ev_instancias_ciclo_id_empleado_id_key UNIQUE (ciclo_id, empleado_id);
ALTER TABLE public.ev_instancias ADD CONSTRAINT ev_instancias_id_empresa_id_key UNIQUE (id, empresa_id);
ALTER TABLE public.ev_plantillas ADD CONSTRAINT ev_plantillas_id_empresa_id_key UNIQUE (id, empresa_id);
ALTER TABLE public.ev_resultados ADD CONSTRAINT ev_resultados_instancia_id_criterio_id_key UNIQUE (instancia_id, criterio_id);
ALTER TABLE public.evaluacion_equivalencias ADD CONSTRAINT evaluacion_equivalencias_empresa_nombre_key UNIQUE (empresa_id, apellido_csv, nombre_csv);
ALTER TABLE public.evaluacion_evaluados ADD CONSTRAINT evaluacion_evaluados_lote_nombre_key UNIQUE (lote_id, apellido_evaluado, nombre_evaluado);
ALTER TABLE public.evaluacion_lotes ADD CONSTRAINT evaluacion_lotes_empresa_periodo_key UNIQUE (empresa_id, periodo);
ALTER TABLE public.evaluacion_resultados ADD CONSTRAINT evaluacion_resultados_eval_tipo_comp_key UNIQUE (evaluado_id, tipo_evaluador, competencia);
ALTER TABLE public.inventario_items ADD CONSTRAINT inventario_items_id_empresa_id_key UNIQUE (id, empresa_id);
ALTER TABLE public.notificaciones_config ADD CONSTRAINT notificaciones_config_user_id_tipo_evento_key UNIQUE (user_id, tipo_evento);
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
ALTER TABLE public.sucesion_posiciones ADD CONSTRAINT sucesion_posiciones_id_empresa_uq UNIQUE (id, empresa_id);
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
ALTER TABLE public.assessment_reportes ADD CONSTRAINT assessment_reportes_generado_por_check CHECK (((generado_por)::text = ANY ((ARRAY['ia'::character varying, 'manual'::character varying])::text[])));
ALTER TABLE public.assessment_reportes ADD CONSTRAINT assessment_reportes_tipo_reporte_check CHECK (((tipo_reporte)::text = ANY ((ARRAY['perfil_conductual'::character varying, 'perfil_cognitivo'::character varying, 'fit_cultural'::character varying, 'plan_desarrollo'::character varying, 'comparativo'::character varying, 'ejecutivo'::character varying])::text[])));
ALTER TABLE public.assessment_resultados ADD CONSTRAINT assessment_resultados_tiempo_total_segundos_check CHECK ((tiempo_total_segundos > 0));
ALTER TABLE public.auditoria ADD CONSTRAINT auditoria_accion_check CHECK (((accion)::text = ANY ((ARRAY['INSERT'::character varying, 'UPDATE'::character varying, 'DELETE'::character varying])::text[])));
ALTER TABLE public.candidatos ADD CONSTRAINT candidatos_estado_check CHECK (((estado)::text = ANY ((ARRAY['activo'::character varying, 'descartado'::character varying, 'contratado'::character varying, 'en_espera'::character varying])::text[])));
ALTER TABLE public.candidatos ADD CONSTRAINT candidatos_etapa_check CHECK (((etapa)::text = ANY ((ARRAY['postulado'::character varying, 'assessment'::character varying, 'entrevista_rrhh'::character varying, 'entrevista_tecnica'::character varying, 'oferta'::character varying])::text[])));
ALTER TABLE public.candidatos ADD CONSTRAINT candidatos_fuente_check CHECK (((fuente)::text = ANY ((ARRAY['linkedin'::character varying, 'referido'::character varying, 'web'::character varying, 'consultora'::character varying, 'espontanea'::character varying, 'otra'::character varying])::text[])));
ALTER TABLE public.candidatos ADD CONSTRAINT candidatos_puntuacion_check CHECK (((puntuacion >= 1) AND (puntuacion <= 10)));
ALTER TABLE public.candidatos ADD CONSTRAINT candidatos_score_ia_check CHECK (((score_ia >= (0)::numeric) AND (score_ia <= (10)::numeric)));
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_anio_check CHECK (((anio >= 2000) AND (anio <= 2100)));
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_bonos_check CHECK ((bonos >= (0)::numeric));
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_cargas_sociales_check CHECK ((cargas_sociales >= (0)::numeric));
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_mes_check CHECK (((mes >= 1) AND (mes <= 12)));
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_otros_costos_check CHECK ((otros_costos >= (0)::numeric));
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_salario_bruto_check CHECK ((salario_bruto >= (0)::numeric));
ALTER TABLE public.documentos_empleado ADD CONSTRAINT documentos_empleado_estado_check CHECK (((estado)::text = ANY ((ARRAY['activo'::character varying, 'archivado'::character varying, 'eliminado'::character varying])::text[])));
ALTER TABLE public.documentos_empleado ADD CONSTRAINT documentos_empleado_tamano_bytes_check CHECK ((tamano_bytes > 0));
ALTER TABLE public.documentos_empleado ADD CONSTRAINT documentos_empleado_tipo_check CHECK (((tipo)::text = ANY ((ARRAY['contrato'::character varying, 'recibo_sueldo'::character varying, 'certificado'::character varying, 'dni'::character varying, 'curriculum'::character varying, 'evaluacion'::character varying, 'otro'::character varying])::text[])));
ALTER TABLE public.empleado_capacitacion ADD CONSTRAINT empleado_capacitacion_estado_check CHECK ((estado = ANY (ARRAY['pendiente'::text, 'en_curso'::text, 'completado'::text])));
ALTER TABLE public.empleados ADD CONSTRAINT empleados_desempeno_check CHECK (((desempeno)::text = ANY ((ARRAY['alto'::character varying, 'medio'::character varying, 'bajo'::character varying])::text[])));
ALTER TABLE public.empleados ADD CONSTRAINT empleados_estado_check CHECK (((estado)::text = ANY ((ARRAY['activo'::character varying, 'baja'::character varying, 'licencia'::character varying, 'suspendido'::character varying])::text[])));
ALTER TABLE public.empleados ADD CONSTRAINT empleados_modalidad_trabajo_check CHECK (((modalidad_trabajo)::text = ANY ((ARRAY['presencial'::character varying, 'remoto'::character varying, 'hibrido'::character varying])::text[])));
ALTER TABLE public.empleados ADD CONSTRAINT empleados_potencial_check CHECK (((potencial)::text = ANY ((ARRAY['alto'::character varying, 'medio'::character varying, 'bajo'::character varying])::text[])));
ALTER TABLE public.empleados ADD CONSTRAINT empleados_roles_no_vacio CHECK ((array_length(roles, 1) >= 1));
ALTER TABLE public.ev_ciclos ADD CONSTRAINT ev_ciclos_estado_check CHECK ((estado = ANY (ARRAY['abierto'::text, 'cerrado'::text])));
ALTER TABLE public.ev_criterios ADD CONSTRAINT ev_criterios_peso_check CHECK ((peso > (0)::numeric));
ALTER TABLE public.ev_instancias ADD CONSTRAINT ev_instancias_estado_check CHECK ((estado = ANY (ARRAY['borrador'::text, 'finalizada'::text])));
ALTER TABLE public.ev_plantillas ADD CONSTRAINT ev_plantillas_tipo_escala_check CHECK ((tipo_escala = ANY (ARRAY['numerica'::text, 'cualitativa'::text])));
ALTER TABLE public.evaluacion_evaluados ADD CONSTRAINT evaluacion_evaluados_perfil_check CHECK ((perfil = ANY (ARRAY['lider'::text, 'general'::text])));
ALTER TABLE public.evaluacion_resultados ADD CONSTRAINT evaluacion_resultados_tipo_evaluador_check CHECK ((tipo_evaluador = ANY (ARRAY['AUTOEVALUACION'::text, 'AUTOEVALUACION_LIDER'::text, 'SUPERIOR_INMEDIATO'::text, 'PAR'::text, 'COLABORADOR'::text, 'LIBRES'::text])));
ALTER TABLE public.horas_proyecto ADD CONSTRAINT horas_proyecto_horas_check CHECK ((horas > (0)::numeric));
ALTER TABLE public.inventario_asignaciones ADD CONSTRAINT inventario_asignaciones_estado_devolucion_check CHECK (((estado_devolucion = ANY (ARRAY['ok'::text, 'con_daño'::text])) OR (estado_devolucion IS NULL)));
ALTER TABLE public.inventario_items ADD CONSTRAINT inventario_items_estado_check CHECK ((estado = ANY (ARRAY['disponible'::text, 'asignado'::text, 'en_reparacion'::text, 'baja'::text])));
ALTER TABLE public.notificaciones ADD CONSTRAINT notificaciones_tipo_check CHECK (((tipo)::text = ANY ((ARRAY['onboarding_tarea'::character varying, 'offboarding_inicio'::character varying, 'assessment_enviado'::character varying, 'assessment_completado'::character varying, 'vacante_nueva'::character varying, 'candidato_nuevo'::character varying, 'documento_vencimiento'::character varying, 'plan_carrera_hito'::character varying, 'sucesion_alerta'::character varying, 'sistema'::character varying, 'otro'::character varying])::text[])));
ALTER TABLE public.notificaciones_config ADD CONSTRAINT notificaciones_config_canal_check CHECK (((canal)::text = ANY ((ARRAY['email'::character varying, 'in_app'::character varying, 'ambos'::character varying, 'ninguno'::character varying])::text[])));
ALTER TABLE public.notificaciones_config ADD CONSTRAINT notificaciones_config_tipo_evento_check CHECK (((tipo_evento)::text = ANY ((ARRAY['onboarding_tarea'::character varying, 'offboarding_inicio'::character varying, 'assessment_enviado'::character varying, 'assessment_completado'::character varying, 'vacante_nueva'::character varying, 'candidato_nuevo'::character varying, 'documento_vencimiento'::character varying, 'plan_carrera_hito'::character varying, 'sucesion_alerta'::character varying, 'sistema'::character varying, 'otro'::character varying])::text[])));
ALTER TABLE public.objetivos ADD CONSTRAINT objetivos_estado_check CHECK ((estado = ANY (ARRAY['por_hacer'::text, 'haciendo'::text, 'terminado'::text])));
ALTER TABLE public.objetivos ADD CONSTRAINT objetivos_prioridad_check CHECK ((prioridad = ANY (ARRAY['baja'::text, 'media'::text, 'alta'::text])));
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
ALTER TABLE public.sucesion_posiciones ADD CONSTRAINT sucesion_posiciones_criticidad_check CHECK (((criticidad)::text = ANY ((ARRAY['baja'::character varying, 'media'::character varying, 'alta'::character varying, 'critica'::character varying])::text[])));
ALTER TABLE public.sucesion_posiciones ADD CONSTRAINT sucesion_posiciones_estado_check CHECK (((estado)::text = ANY ((ARRAY['activo'::character varying, 'en_revision'::character varying, 'cerrado'::character varying])::text[])));
ALTER TABLE public.sucesion_posiciones ADD CONSTRAINT sucesion_posiciones_nivel_preparacion_primario_check CHECK (((nivel_preparacion_primario)::text = ANY ((ARRAY['listo_ya'::character varying, '1_2_anios'::character varying, '3_5_anios'::character varying, 'potencial'::character varying])::text[])));
ALTER TABLE public.sucesion_posiciones ADD CONSTRAINT sucesion_posiciones_nivel_preparacion_secundario_check CHECK (((nivel_preparacion_secundario)::text = ANY ((ARRAY['listo_ya'::character varying, '1_2_anios'::character varying, '3_5_anios'::character varying, 'potencial'::character varying])::text[])));
ALTER TABLE public.users ADD CONSTRAINT users_rol_check CHECK (((rol)::text = ANY ((ARRAY['admin_rrhh'::character varying, 'gerencia_lectura'::character varying, 'mandos_medios'::character varying])::text[])));
ALTER TABLE public.vacantes ADD CONSTRAINT chk_rango_salarial CHECK (((rango_salarial_max IS NULL) OR (rango_salarial_min IS NULL) OR (rango_salarial_max >= rango_salarial_min)));
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_cantidad_puestos_check CHECK ((cantidad_puestos > 0));
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_estado_check CHECK (((estado)::text = ANY ((ARRAY['nueva'::character varying, 'en_proceso'::character varying, 'con_candidatos'::character varying, 'cerrada'::character varying])::text[])));
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_modalidad_check CHECK (((modalidad)::text = ANY ((ARRAY['presencial'::character varying, 'remoto'::character varying, 'hibrido'::character varying])::text[])));
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_nivel_check CHECK (((nivel)::text = ANY ((ARRAY['junior'::character varying, 'semi_senior'::character varying, 'senior'::character varying, 'lider'::character varying, 'manager'::character varying, 'director'::character varying, 'c_level'::character varying])::text[])));
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_prioridad_check CHECK (((prioridad)::text = ANY ((ARRAY['baja'::character varying, 'media'::character varying, 'alta'::character varying, 'urgente'::character varying])::text[])));
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_rango_salarial_max_check CHECK ((rango_salarial_max >= (0)::numeric));
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_rango_salarial_min_check CHECK ((rango_salarial_min >= (0)::numeric));
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_tipo_contrato_check CHECK (((tipo_contrato)::text = ANY ((ARRAY['efectivo'::character varying, 'plazo_fijo'::character varying, 'contratado'::character varying, 'pasantia'::character varying])::text[])));
ALTER TABLE public.parametros_empresa ADD CONSTRAINT pe_base_dias_check CHECK (((base_dias_habiles >= 1) AND (base_dias_habiles <= 31)));
ALTER TABLE public.parametros_empresa ADD CONSTRAINT pe_corte_mes_check CHECK (((corte_antiguedad_mes >= 1) AND (corte_antiguedad_mes <= 12)));
ALTER TABLE public.parametros_empresa ADD CONSTRAINT pe_vac_desde_check CHECK (((periodo_vacacional_desde_mes >= 1) AND (periodo_vacacional_desde_mes <= 12)));
ALTER TABLE public.parametros_empresa ADD CONSTRAINT pe_vac_hasta_check CHECK (((periodo_vacacional_hasta_mes >= 1) AND (periodo_vacacional_hasta_mes <= 12)));
ALTER TABLE public.parametros_empresa ADD CONSTRAINT pe_primer_anio_mes_check CHECK (((primer_anio_mes_corte >= 1) AND (primer_anio_mes_corte <= 12)));
ALTER TABLE public.parametros_empresa ADD CONSTRAINT pe_primer_anio_dias_check CHECK ((primer_anio_dias >= 0));
ALTER TABLE public.parametros_empresa ADD CONSTRAINT pe_vencimiento_check CHECK ((vencimiento_anios > 0));
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
ALTER TABLE public.assessment_reportes ADD CONSTRAINT ass_rep_resultado_emp_fkey FOREIGN KEY (resultado_id, empresa_id) REFERENCES assessment_resultados(id, empresa_id) ON DELETE CASCADE;
ALTER TABLE public.assessment_reportes ADD CONSTRAINT assessment_reportes_created_by_fkey FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.assessment_reportes ADD CONSTRAINT assessment_reportes_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.assessment_reportes ADD CONSTRAINT assessment_reportes_resultado_id_fkey FOREIGN KEY (resultado_id) REFERENCES assessment_resultados(id) ON DELETE CASCADE;
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
ALTER TABLE public.configuracion_empresa ADD CONSTRAINT configuracion_empresa_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE;
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_created_by_fkey FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_empleado_emp_fkey FOREIGN KEY (empleado_id, empresa_id) REFERENCES empleados(id, empresa_id) ON DELETE RESTRICT;
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_empleado_id_fkey FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE RESTRICT;
ALTER TABLE public.costos_nomina ADD CONSTRAINT costos_nomina_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.documentos_empleado ADD CONSTRAINT documentos_empleado_emp_fkey FOREIGN KEY (empleado_id, empresa_id) REFERENCES empleados(id, empresa_id) ON DELETE CASCADE;
ALTER TABLE public.documentos_empleado ADD CONSTRAINT documentos_empleado_empleado_id_fkey FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE;
ALTER TABLE public.documentos_empleado ADD CONSTRAINT documentos_empleado_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.documentos_empleado ADD CONSTRAINT documentos_empleado_subido_por_fkey FOREIGN KEY (subido_por) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.empleado_capacitacion ADD CONSTRAINT ec_capacitacion_empresa_fk FOREIGN KEY (capacitacion_id, empresa_id) REFERENCES capacitaciones(id, empresa_id);
ALTER TABLE public.empleado_capacitacion ADD CONSTRAINT ec_empleado_empresa_fk FOREIGN KEY (empleado_id, empresa_id) REFERENCES empleados(id, empresa_id);
ALTER TABLE public.empleados ADD CONSTRAINT empleados_area_id_fkey FOREIGN KEY (area_id) REFERENCES areas(id) ON DELETE RESTRICT;
ALTER TABLE public.empleados ADD CONSTRAINT empleados_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.empleados ADD CONSTRAINT empleados_manager_id_fkey FOREIGN KEY (manager_id) REFERENCES empleados(id) ON DELETE SET NULL;
ALTER TABLE public.empleados ADD CONSTRAINT empleados_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.ev_ciclos ADD CONSTRAINT ev_ciclo_plantilla_fk FOREIGN KEY (plantilla_id, empresa_id) REFERENCES ev_plantillas(id, empresa_id);
ALTER TABLE public.ev_ciclos ADD CONSTRAINT ev_ciclos_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.ev_criterios ADD CONSTRAINT ev_criterio_plantilla_fk FOREIGN KEY (plantilla_id, empresa_id) REFERENCES ev_plantillas(id, empresa_id);
ALTER TABLE public.ev_criterios ADD CONSTRAINT ev_criterios_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.ev_instancias ADD CONSTRAINT ev_instancia_ciclo_fk FOREIGN KEY (ciclo_id, empresa_id) REFERENCES ev_ciclos(id, empresa_id);
ALTER TABLE public.ev_instancias ADD CONSTRAINT ev_instancia_empleado_fk FOREIGN KEY (empleado_id, empresa_id) REFERENCES empleados(id, empresa_id);
ALTER TABLE public.ev_instancias ADD CONSTRAINT ev_instancias_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.ev_instancias ADD CONSTRAINT ev_instancias_evaluador_id_fkey FOREIGN KEY (evaluador_id) REFERENCES empleados(id);
ALTER TABLE public.ev_plantillas ADD CONSTRAINT ev_plantillas_area_id_fkey FOREIGN KEY (area_id) REFERENCES areas(id);
ALTER TABLE public.ev_plantillas ADD CONSTRAINT ev_plantillas_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.ev_resultados ADD CONSTRAINT ev_resultado_instancia_fk FOREIGN KEY (instancia_id, empresa_id) REFERENCES ev_instancias(id, empresa_id);
ALTER TABLE public.ev_resultados ADD CONSTRAINT ev_resultados_criterio_id_fkey FOREIGN KEY (criterio_id) REFERENCES ev_criterios(id);
ALTER TABLE public.ev_resultados ADD CONSTRAINT ev_resultados_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
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
ALTER TABLE public.horas_proyecto ADD CONSTRAINT horas_proyecto_empleado_empresa_id_fkey FOREIGN KEY (empleado_empresa_id) REFERENCES empresas(id);
ALTER TABLE public.horas_proyecto ADD CONSTRAINT horas_proyecto_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.horas_proyecto ADD CONSTRAINT horas_proyecto_proyecto_id_fkey FOREIGN KEY (proyecto_id) REFERENCES proyectos(id);
ALTER TABLE public.inventario_asignaciones ADD CONSTRAINT inv_asig_empleado_empresa_fk FOREIGN KEY (empleado_id, empresa_id) REFERENCES empleados(id, empresa_id);
ALTER TABLE public.inventario_asignaciones ADD CONSTRAINT inv_asig_item_empresa_fk FOREIGN KEY (item_id, empresa_id) REFERENCES inventario_items(id, empresa_id);
ALTER TABLE public.inventario_items ADD CONSTRAINT inventario_items_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.notificaciones ADD CONSTRAINT notificaciones_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE public.notificaciones_config ADD CONSTRAINT notificaciones_config_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE public.oauth_states ADD CONSTRAINT oauth_states_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE public.objetivos ADD CONSTRAINT objetivos_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE public.objetivos ADD CONSTRAINT objetivos_responsable_id_fkey FOREIGN KEY (responsable_id) REFERENCES users(id);
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
ALTER TABLE public.sucesion_posiciones ADD CONSTRAINT sucesion_posiciones_area_id_fkey FOREIGN KEY (area_id) REFERENCES areas(id) ON DELETE SET NULL;
ALTER TABLE public.sucesion_posiciones ADD CONSTRAINT sucesion_posiciones_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.sucesion_posiciones ADD CONSTRAINT sucesion_posiciones_sucesor_primario_id_fkey FOREIGN KEY (sucesor_primario_id) REFERENCES empleados(id) ON DELETE SET NULL;
ALTER TABLE public.sucesion_posiciones ADD CONSTRAINT sucesion_posiciones_sucesor_secundario_id_fkey FOREIGN KEY (sucesor_secundario_id) REFERENCES empleados(id) ON DELETE SET NULL;
ALTER TABLE public.sucesion_posiciones ADD CONSTRAINT sucesion_posiciones_titular_id_fkey FOREIGN KEY (titular_id) REFERENCES empleados(id) ON DELETE SET NULL;
ALTER TABLE public.users ADD CONSTRAINT users_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public.usuario_integraciones ADD CONSTRAINT usuario_integraciones_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_area_id_fkey FOREIGN KEY (area_id) REFERENCES areas(id) ON DELETE RESTRICT;
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_empresa_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE public.vacantes ADD CONSTRAINT vacantes_responsable_id_fkey FOREIGN KEY (responsable_id) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE public.parametros_empresa ADD CONSTRAINT parametros_empresa_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE;
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
CREATE INDEX idx_assessment_reportes_empresa ON public.assessment_reportes USING btree (empresa_id);
CREATE INDEX idx_reportes_resultado ON public.assessment_reportes USING btree (resultado_id);
CREATE INDEX idx_reportes_tipo ON public.assessment_reportes USING btree (tipo_reporte);
CREATE INDEX idx_assessment_resultados_empresa ON public.assessment_resultados USING btree (empresa_id);
CREATE INDEX idx_resultados_campana ON public.assessment_resultados USING btree (campana_id);
CREATE INDEX idx_resultados_candidato ON public.assessment_resultados USING btree (candidato_id);
CREATE INDEX idx_resultados_empleado ON public.assessment_resultados USING btree (empleado_id);
CREATE INDEX idx_auditoria_created ON public.auditoria USING btree (created_at DESC);
CREATE INDEX idx_auditoria_empresa ON public.auditoria USING btree (empresa_id);
CREATE INDEX idx_auditoria_entidad ON public.auditoria USING btree (entidad, registro_id);
CREATE INDEX idx_auditoria_registro ON public.auditoria USING btree (tabla, registro_id);
CREATE INDEX idx_auditoria_tabla ON public.auditoria USING btree (tabla);
CREATE INDEX idx_auditoria_usuario ON public.auditoria USING btree (usuario_id);
CREATE INDEX idx_candidatos_email ON public.candidatos USING btree (email);
CREATE INDEX idx_candidatos_empresa ON public.candidatos USING btree (empresa_id);
CREATE INDEX idx_candidatos_etapa ON public.candidatos USING btree (etapa);
CREATE INDEX idx_candidatos_vacante ON public.candidatos USING btree (vacante_id);
CREATE INDEX idx_cap_empresa_id ON public.capacitaciones USING btree (empresa_id);
CREATE INDEX idx_cesiones_empleado ON public.cesiones USING btree (empleado_id);
CREATE INDEX idx_cesiones_empresa ON public.cesiones USING btree (empresa_id);
CREATE INDEX idx_costos_nomina_empleado ON public.costos_nomina USING btree (empleado_id);
CREATE INDEX idx_costos_nomina_empresa ON public.costos_nomina USING btree (empresa_id);
CREATE INDEX idx_costos_nomina_periodo ON public.costos_nomina USING btree (anio, mes);
CREATE INDEX idx_documentos_empleado ON public.documentos_empleado USING btree (empleado_id);
CREATE INDEX idx_documentos_empleado_empresa ON public.documentos_empleado USING btree (empresa_id);
CREATE INDEX idx_documentos_estado ON public.documentos_empleado USING btree (estado);
CREATE INDEX idx_documentos_tipo ON public.documentos_empleado USING btree (tipo);
CREATE INDEX idx_ec_capacitacion_id ON public.empleado_capacitacion USING btree (capacitacion_id);
CREATE INDEX idx_ec_empleado_id ON public.empleado_capacitacion USING btree (empleado_id);
CREATE INDEX idx_ec_empresa_id ON public.empleado_capacitacion USING btree (empresa_id);
CREATE INDEX idx_empleados_area ON public.empleados USING btree (area_id);
CREATE INDEX idx_empleados_desempeno ON public.empleados USING btree (desempeno);
CREATE INDEX idx_empleados_domicilio_localidad ON public.empleados USING btree (domicilio_localidad) WHERE (domicilio_localidad IS NOT NULL);
CREATE INDEX idx_empleados_domicilio_provincia ON public.empleados USING btree (domicilio_provincia) WHERE (domicilio_provincia IS NOT NULL);
CREATE INDEX idx_empleados_empresa ON public.empleados USING btree (empresa_id);
CREATE INDEX idx_empleados_estado ON public.empleados USING btree (estado);
CREATE INDEX idx_empleados_manager ON public.empleados USING btree (manager_id);
CREATE INDEX idx_empleados_potencial ON public.empleados USING btree (potencial);
CREATE INDEX idx_empleados_user ON public.empleados USING btree (user_id);
CREATE INDEX idx_evaluacion_evaluados_empleado ON public.evaluacion_evaluados USING btree (empleado_id);
CREATE INDEX idx_evcicp_empresa ON public.ev_ciclos USING btree (empresa_id);
CREATE INDEX idx_evcicp_estado ON public.ev_ciclos USING btree (estado);
CREATE INDEX idx_evcicp_plantilla ON public.ev_ciclos USING btree (plantilla_id);
CREATE INDEX idx_evcrit_empresa ON public.ev_criterios USING btree (empresa_id);
CREATE INDEX idx_evcrit_plantilla ON public.ev_criterios USING btree (plantilla_id);
CREATE INDEX idx_evinst_ciclo ON public.ev_instancias USING btree (ciclo_id);
CREATE INDEX idx_evinst_empleado ON public.ev_instancias USING btree (empleado_id);
CREATE INDEX idx_evinst_empresa ON public.ev_instancias USING btree (empresa_id);
CREATE INDEX idx_evinst_estado ON public.ev_instancias USING btree (estado);
CREATE INDEX idx_evp_activa ON public.ev_plantillas USING btree (activa);
CREATE INDEX idx_evp_area ON public.ev_plantillas USING btree (area_id);
CREATE INDEX idx_evp_empresa ON public.ev_plantillas USING btree (empresa_id);
CREATE INDEX idx_evres_empresa ON public.ev_resultados USING btree (empresa_id);
CREATE INDEX idx_evres_instancia ON public.ev_resultados USING btree (instancia_id);
CREATE INDEX idx_hp_asignacion ON public.horas_proyecto USING btree (asignacion_id);
CREATE INDEX idx_hp_empresa ON public.horas_proyecto USING btree (empresa_id);
CREATE INDEX idx_hp_fecha ON public.horas_proyecto USING btree (fecha);
CREATE INDEX idx_hp_proyecto ON public.horas_proyecto USING btree (proyecto_id);
CREATE INDEX idx_inv_asig_empleado ON public.inventario_asignaciones USING btree (empleado_id);
CREATE INDEX idx_inv_asig_empresa ON public.inventario_asignaciones USING btree (empresa_id);
CREATE INDEX idx_inv_asig_item ON public.inventario_asignaciones USING btree (item_id);
CREATE UNIQUE INDEX idx_inv_asig_item_activo ON public.inventario_asignaciones USING btree (item_id) WHERE (fecha_devolucion IS NULL);
CREATE INDEX idx_inv_items_empresa ON public.inventario_items USING btree (empresa_id);
CREATE INDEX idx_inv_items_estado ON public.inventario_items USING btree (estado);
CREATE INDEX idx_notificaciones_created ON public.notificaciones USING btree (created_at DESC);
CREATE INDEX idx_notificaciones_leida ON public.notificaciones USING btree (user_id, leida);
CREATE INDEX idx_notificaciones_user ON public.notificaciones USING btree (user_id);
CREATE INDEX idx_notif_config_user ON public.notificaciones_config USING btree (user_id);
CREATE INDEX idx_obj_empresa ON public.objetivos USING btree (empresa_id);
CREATE INDEX idx_obj_estado ON public.objetivos USING btree (estado);
CREATE INDEX idx_obj_responsable ON public.objetivos USING btree (responsable_id);
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
CREATE INDEX idx_solicitudes_vacaciones_empresa_tipo ON public.solicitudes_vacaciones USING btree (empresa_id, tipo);
CREATE INDEX idx_sv_empleado_id ON public.solicitudes_vacaciones USING btree (empleado_id);
CREATE INDEX idx_sv_empresa_id ON public.solicitudes_vacaciones USING btree (empresa_id);
CREATE INDEX idx_sv_periodo ON public.solicitudes_vacaciones USING btree (empleado_id, periodo) WHERE (periodo IS NOT NULL);
CREATE INDEX idx_vp_empleado ON public.vacaciones_pendientes USING btree (empleado_id);
CREATE INDEX idx_vp_empresa ON public.vacaciones_pendientes USING btree (empresa_id);
CREATE INDEX idx_sucesion_area ON public.sucesion_posiciones USING btree (area_id);
CREATE INDEX idx_sucesion_criticidad ON public.sucesion_posiciones USING btree (criticidad);
CREATE INDEX idx_sucesion_posiciones_empresa ON public.sucesion_posiciones USING btree (empresa_id);
CREATE INDEX idx_sucesion_titular ON public.sucesion_posiciones USING btree (titular_id);
CREATE INDEX idx_vacantes_area ON public.vacantes USING btree (area_id);
CREATE INDEX idx_esp_empresa ON public.empleado_superior_pendiente USING btree (empresa_id);
CREATE UNIQUE INDEX uq_integracion_remitente_sistema ON public.usuario_integraciones USING btree ((es_remitente_sistema)) WHERE es_remitente_sistema;
CREATE UNIQUE INDEX uq_plantilla_empresa_clave ON public.plantillas_mail USING btree (empresa_id, clave) WHERE (empresa_id IS NOT NULL);
CREATE UNIQUE INDEX uq_plantilla_global_clave ON public.plantillas_mail USING btree (clave) WHERE (empresa_id IS NULL);
CREATE INDEX idx_mail_enviado_idempotencia ON public.mail_enviado USING btree (plantilla_clave, empleado_id, created_at DESC);
CREATE INDEX idx_mail_enviado_empresa ON public.mail_enviado USING btree (empresa_id, created_at DESC);
CREATE INDEX idx_vacantes_empresa ON public.vacantes USING btree (empresa_id);
CREATE INDEX idx_vacantes_estado ON public.vacantes USING btree (estado);
CREATE INDEX idx_vacantes_responsable ON public.vacantes USING btree (responsable_id);
-- Migracion 085. Los indices son PARCIALES porque en SQL NULL <> NULL: un UNIQUE comun sobre
-- empresa_id dejaria entrar varias filas globales y la lectura elegiria una al azar.
-- El de parametros_empresa indexa la CONSTANTE (empresa_id IS NULL) = TRUE, asi que solo
-- admite UNA global. El de la escala indexa antiguedad_anios: la escala global son VARIAS
-- filas y lo que no puede repetirse es el punto de corte.
CREATE UNIQUE INDEX ux_parametros_empresa_por_empresa ON public.parametros_empresa USING btree (empresa_id) WHERE (empresa_id IS NOT NULL);
CREATE UNIQUE INDEX ux_parametros_empresa_global ON public.parametros_empresa USING btree (((empresa_id IS NULL))) WHERE (empresa_id IS NULL);
CREATE UNIQUE INDEX ux_escala_por_empresa ON public.reglas_vacaciones_escala USING btree (empresa_id, antiguedad_anios) WHERE (empresa_id IS NOT NULL);
CREATE UNIQUE INDEX ux_escala_global ON public.reglas_vacaciones_escala USING btree (antiguedad_anios) WHERE (empresa_id IS NULL);
CREATE UNIQUE INDEX ux_tipos_ausencia_nombre_por_empresa ON public.tipos_ausencia USING btree (empresa_id, nombre) WHERE (empresa_id IS NOT NULL);
CREATE UNIQUE INDEX ux_tipos_ausencia_nombre_global ON public.tipos_ausencia USING btree (nombre) WHERE (empresa_id IS NULL);
CREATE INDEX idx_tipos_ausencia_empresa ON public.tipos_ausencia USING btree (empresa_id) WHERE (empresa_id IS NOT NULL);
CREATE INDEX idx_tipos_ausencia_padre ON public.tipos_ausencia USING btree (padre_id) WHERE (padre_id IS NOT NULL);


-- ============================================================================
-- FIN DEL SNAPSHOT
-- ============================================================================
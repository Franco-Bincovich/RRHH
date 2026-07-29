-- 083_vacaciones_periodo_y_pendientes.sql
--
-- QUÉ HACE: separa dos hechos que hoy no se pueden distinguir, y agrega el año devengado.
--   (a) solicitudes_vacaciones: + periodo (año al que corresponde la licencia) + dias_liquidados.
--   (b) tabla NUEVA vacaciones_pendientes: días de un período que NO se tomaron.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- POR QUÉ EL PERÍODO
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- Los archivos históricos de RRHH traen licencias TOMADAS en un año que corresponden a OTRO:
-- del 13/4/2026 al 19/4/2026, período 2025. Hoy el modelo no tiene dónde poner ese dato: las
-- únicas fechas son fecha_desde/fecha_hasta (cuándo se tomó) y created_at (cuándo se cargó).
-- Sin `periodo`, el saldo suma TODO el histórico contra un cupo anual único y da negativo
-- para todos en cuanto se importe la historia completa.
--
-- `periodo` es NULLABLE a propósito: las filas que ya existen en producción no lo tienen y no
-- hay forma de derivarlo (el año de fecha_desde NO es el período — ese es justamente el caso
-- que esta columna vino a representar). Inventarlo con un DEFAULT sería peor que dejarlo NULL:
-- daría un dato falso indistinguible de uno cargado a mano.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 POR QUÉ LOS DÍAS NO TOMADOS VAN EN OTRA TABLA — NO FUSIONAR DESPUÉS "POR SIMPLICIDAD"
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- Un día no tomado no tiene fechas: nadie faltó ningún día. Lo natural parece ser una fila en
-- solicitudes_vacaciones con fecha_desde/fecha_hasta en NULL. Se diagnosticó esa opción sobre
-- el código real y ROMPE 15 LUGARES: 6 con crash y 9 EN SILENCIO.
--
--   Los 6 crashes son recuperables (se ven en el deploy):
--     · schemas/vacaciones.py declara `fecha_desde: date` no-Optional → ValidationError → 500
--       en TODA lectura, apenas exista una fila NULL.
--     · services/_vacaciones_utils.derive_estado compara `today < row.fecha_desde` → TypeError.
--     · repositories: str(None) = "None" viaja como fecha al INSERT.
--     · front: VacacionesTable.formatFecha y MapaVacaciones.parseLocalDate hacen s.split("-").
--
--   Los 9 SILENCIOSOS son el motivo real de esta decisión. Ocho comparten una sola causa:
--   en SQL un predicado sobre NULL da NULL, que NO ES TRUE, así que la fila se cae del WHERE
--   — y como el count viaja en la misma query, se cae también del total. Un filtro no deja
--   pasar las filas sin fecha: LAS ESCONDE, y el total viaja escondido con ellas. El noveno
--   es el reverso: ORDER BY fecha_desde DESC implica NULLS FIRST, así que cuando no las
--   esconde las pone primero, arriba de todo.
--
--   Los dos peores, por consecuencia de negocio:
--     · El reporte de saldos (R11, services/reportes/_reporte_vacaciones.py) filtra por
--       fecha_desde: las filas sin fecha nunca entran en `tomados`, así que el saldo sale
--       INFLADO — le dice a RRHH que el empleado tiene MÁS días de los que tiene.
--     · El bloqueo por período cerrado (services/_periodo_utils.py) retorna sin validar
--       cuando no hay fechas, así que DEJA DE APLICAR.
--
-- Con tablas separadas, fecha_desde y fecha_hasta SIGUEN SIENDO NOT NULL en
-- solicitudes_vacaciones y nada de eso ocurre: los reportes, el mapa, el saldo, el export y
-- los filtros no ven esta tabla nueva y se comportan exactamente igual que antes.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- 🔴 POR QUÉ dias_liquidados ES UN INT Y NO UN BOOL `liquidada`
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- En el archivo real TODAS las filas dicen "Liquidado", incluidas las tomadas, porque las
-- vacaciones siempre se pagan. O sea que "liquidada" NO decide dónde se guarda una fila: lo
-- que separa las dos tablas es SI SE TOMÓ. Por eso el dato existe en las dos.
--
-- Con un bool no se puede representar una liquidación PARCIAL: 10 días pendientes de 2024 de
-- los que se liquidan 5 en marzo y 5 quedan pendientes necesitarían DOS filas del mismo
-- (empleado, período) — que es exactamente lo que la UNIQUE de abajo prohíbe. Con un entero
-- entran en una sola fila y la UNIQUE se sostiene:
--     liquidación total   → dias_liquidados = dias
--     liquidación parcial → dias_liquidados < dias
--     nada liquidado      → dias_liquidados = 0
-- La UI sigue siendo un tilde (tildado → dias_liquidados = dias; destildado → 0). Si RRHH
-- confirma que la liquidación puede ser parcial, el modelo ya lo soporta y solo cambia el
-- input: no hace falta otra migración.
--
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- ALCANCE Y DECISIONES ANOTADAS
-- ─────────────────────────────────────────────────────────────────────────────────────────
-- · Esta tabla es SOLO para tipo='vacaciones'. No lleva columna `tipo` a propósito: solo ese
--   tipo descuenta del saldo (services/_vacaciones_saldo.py), y los pendientes son un concepto
--   de saldo. Si algún día existe "una semana free pendiente", hay que revisar la UNIQUE.
-- · El CÁLCULO DEL SALDO no se toca en esta migración. Depende de si los días no usados se
--   acumulan al año siguiente, que se define con RRHH. Hoy el saldo sigue funcionando igual.
-- · El bloqueo por período cerrado NO aplica a esta tabla. El motivo está escrito en
--   services/vacaciones_pendientes_service.py.
--
-- NO DESTRUCTIVA: agrega columnas nullable / con default y crea una tabla nueva. No toca
-- datos existentes y es segura de correr con la aplicación arriba.
-- Idempotente (IF NOT EXISTS). NO se ejecuta acá (la corre Franco).

BEGIN;

-- ── (a) solicitudes_vacaciones: año devengado + días liquidados ──────────────────────────

ALTER TABLE public.solicitudes_vacaciones
    ADD COLUMN IF NOT EXISTS periodo         SMALLINT,
    ADD COLUMN IF NOT EXISTS dias_liquidados INTEGER NOT NULL DEFAULT 0;

ALTER TABLE public.solicitudes_vacaciones
    DROP CONSTRAINT IF EXISTS sv_periodo_check;
ALTER TABLE public.solicitudes_vacaciones
    ADD CONSTRAINT sv_periodo_check CHECK (periodo IS NULL OR (periodo >= 2000 AND periodo <= 2100));

ALTER TABLE public.solicitudes_vacaciones
    DROP CONSTRAINT IF EXISTS sv_dias_liquidados_check;
ALTER TABLE public.solicitudes_vacaciones
    ADD CONSTRAINT sv_dias_liquidados_check CHECK (dias_liquidados >= 0 AND dias_liquidados <= dias);

COMMENT ON COLUMN public.solicitudes_vacaciones.periodo IS
    'Año al que CORRESPONDE la licencia (devengado), que puede diferir del año de fecha_desde: una licencia tomada en 2026 puede ser del período 2025. NULL en las filas previas a la migración 083 — no se puede derivar de fecha_desde.';
COMMENT ON COLUMN public.solicitudes_vacaciones.dias_liquidados IS
    'Cuántos de los `dias` de esta licencia ya se pagaron. Entero y no bool para admitir liquidación parcial (ver 083).';

CREATE INDEX IF NOT EXISTS idx_sv_periodo
    ON public.solicitudes_vacaciones (empleado_id, periodo) WHERE periodo IS NOT NULL;

-- ── (b) vacaciones_pendientes: días de un período que NO se tomaron ──────────────────────

CREATE TABLE IF NOT EXISTS public.vacaciones_pendientes (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id      UUID        NOT NULL REFERENCES public.empresas(id),
    empleado_id     UUID        NOT NULL REFERENCES public.empleados(id) ON DELETE CASCADE,
    periodo         SMALLINT    NOT NULL,
    dias            INTEGER     NOT NULL,
    dias_liquidados INTEGER     NOT NULL DEFAULT 0,
    comentario      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT vp_periodo_check         CHECK (periodo >= 2000 AND periodo <= 2100),
    CONSTRAINT vp_dias_check            CHECK (dias > 0),
    CONSTRAINT vp_dias_liquidados_check CHECK (dias_liquidados >= 0 AND dias_liquidados <= dias),

    -- FK COMPUESTA contra empleados(id, empresa_id): es lo que hace estructuralmente
    -- imposible que empresa_id driftee de la empresa real del empleado. Mismo patrón que
    -- sv_empleado_empresa_fk en solicitudes_vacaciones y sa_empleado_empresa_fk en ausencias.
    CONSTRAINT vp_empleado_empresa_fk
        FOREIGN KEY (empleado_id, empresa_id) REFERENCES public.empleados(id, empresa_id),

    -- "10 días pendientes del 2024" es UN HECHO ÚNICO por empleado y año. La UNIQUE le da al
    -- import futuro idempotencia gratis (ON CONFLICT → actualiza en vez de duplicar), que es
    -- justo lo que solicitudes_vacaciones NO tiene y por lo que reimportar ahí duplicaría todo.
    -- empresa_id NO va en la UNIQUE: empleado_id ya la determina (empleados.empresa_id es NOT
    -- NULL y la FK compuesta de arriba la fija). Sumarla no agregaría nada y DEBILITARÍA la
    -- restricción — permitiría dos filas si la empresa llegara a driftear.
    CONSTRAINT vacaciones_pendientes_empleado_periodo_key UNIQUE (empleado_id, periodo)
);

COMMENT ON TABLE public.vacaciones_pendientes IS
    'Días de vacaciones de un período que NO se tomaron (no hay fechas: nadie faltó ningún día). Vive aparte de solicitudes_vacaciones a propósito: permitir fecha_desde/fecha_hasta NULL ahí rompe 15 lugares (6 crash, 9 en silencio) porque en SQL un predicado sobre NULL no es TRUE y la fila se cae del WHERE y del count. Ver el encabezado de la migración 083 antes de fusionarlas. Solo aplica a tipo=vacaciones.';
COMMENT ON COLUMN public.vacaciones_pendientes.dias IS
    'Días del período que quedaron sin tomar.';
COMMENT ON COLUMN public.vacaciones_pendientes.dias_liquidados IS
    'Cuántos de esos días ya se pagaron. Entero y no bool para admitir liquidación parcial en UNA fila sin romper la UNIQUE (empleado_id, periodo).';

CREATE INDEX IF NOT EXISTS idx_vp_empleado ON public.vacaciones_pendientes(empleado_id);
CREATE INDEX IF NOT EXISTS idx_vp_empresa  ON public.vacaciones_pendientes(empresa_id);

-- updated_at automático (misma función que empleados/cesiones/proyectos).
DROP TRIGGER IF EXISTS trg_vacaciones_pendientes_updated_at ON public.vacaciones_pendientes;
CREATE TRIGGER trg_vacaciones_pendientes_updated_at
    BEFORE UPDATE ON public.vacaciones_pendientes
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- RLS habilitada SIN policies (deny-all para anon/authenticated). El backend entra con
-- service_key (supabase_admin, bypasea RLS) y el control real es APP-LEVEL vía
-- require_permission(Seccion.VACACIONES). Mismo criterio que 061 (adjuntos) y 066 (cesiones).
ALTER TABLE public.vacaciones_pendientes ENABLE ROW LEVEL SECURITY;

COMMIT;

NOTIFY pgrst, 'reload schema';

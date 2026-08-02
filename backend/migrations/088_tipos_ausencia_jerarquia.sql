-- 088_tipos_ausencia_jerarquia.sql
--
-- QUÉ HACE: le da DOS NIVELES al catálogo de tipos de ausencia, y desactiva "Injustificada".
--   (a) tipos_ausencia + padre_id (self-FK nullable).
--   (b) UPDATE tipos_ausencia SET activo = false WHERE nombre = 'Injustificada'.
--
-- NO ES DESTRUCTIVA: una columna nullable y una baja LÓGICA. No borra ni reescribe ninguna fila.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 🔴 ESTA MIGRACIÓN HAY QUE CORRERLA AHORA, Y EL MOTIVO NO ES TÉCNICO
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- `solicitudes_ausencia` tiene CERO filas en producción (verificado contra el catálogo vivo el
-- 2/8/2026). Hoy esto es un ALTER TABLE y un UPDATE de catálogo sobre 4 filas.
--
-- En cuanto RRHH cargue el histórico de ausencias —que es un pendiente activo, esperando la
-- definición del parser de import— exactamente el mismo cambio pasa a ser una REASIGNACIÓN DE
-- `tipo_id` SOBRE FILAS VIVAS: cada ausencia cargada como "Injustificada" habría que moverla a
-- un tipo real y setearle `justificada = false`, adivinando cuál era el tipo real. Ese dato no
-- existiría en ningún lado.
--
-- La ventana se cierra sola y no vuelve a abrirse.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- (a) POR QUÉ padre_id Y NO APLANAR NI TEXTO LIBRE
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- Los archivos reales de RRHH traen dos niveles: "ENFERMEDAD FAMILIAR → Madre/padre",
-- "FRANCO COMPENSATORIO → Franco compesatorio" (sic — el typo está en el archivo). Se evaluaron
-- tres modelos:
--
--   · APLANAR (un tipo por combinación) es el más barato y rompe el requisito central: "cuántos
--     días de enfermedad familiar" dejaría de ser una consulta y pasaría a ser un
--     `LIKE 'Enfermedad familiar%'` sobre un nombre QUE RRHH EDITA DESDE LA UI. El día que
--     alguien corrija "compesatorio", el agrupamiento se parte en silencio. Un reporte que
--     depende de la ortografía de un campo editable no es un reporte.
--
--   · TEXTO LIBRE (un `subtipo` en la ausencia) es reintroducir `empleados.equipo`, que este
--     repo ya documenta como error — y que este diagnóstico confirmó con datos: 0 de 19
--     poblado. Un campo de texto libre no es flexible: es un campo que nadie puede consultar,
--     agrupar ni validar, y que termina vacío o con cuatro grafías del mismo valor.
--
--   · padre_id hace que el agrupamiento vaya por ID y no por texto. El typo del archivo deja de
--     importar: es el `nombre` de un hijo, y "cuántos días de X" se contesta con
--     COALESCE(padre_id, id).
--
-- Es ADITIVA: `padre_id IS NULL` = tipo de primer nivel, que es exactamente el modelo de hoy.
-- Las 4 filas existentes quedan como padres sin hijos, que es un ESTADO VÁLIDO y no transitorio.
--
-- ⚠️ PROFUNDIDAD MÁXIMA 2 — la guarda NO vive acá. Un CHECK no puede consultar otra fila de la
-- misma tabla (no es inmutable), y un trigger sería la única forma de hacerlo en la base. Se
-- decidió que viva en el service (`_tipos_jerarquia.ensure_padre_valido`), por dos razones: es
-- donde ya vive la guarda equivalente del organigrama (`ensure_no_ciclo_manager`), y así el
-- error le llega al usuario como un AppError legible en vez de un error crudo de Postgres.
-- 🚩 Consecuencia asumida: alguien con acceso directo a la base PUEDE crear un nieto. No es un
-- agujero de seguridad —hace falta ser admin de la base— pero está dicho.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- (b) POR QUÉ SE DESACTIVA "Injustificada"
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- Mezcla DOS EJES que el modelo ya separa, y desde la 085 la mezcla es demostrable:
--
--     naturaleza de la ausencia  → solicitudes_ausencia.tipo_id     (¿por qué faltó?)
--     calificación               → solicitudes_ausencia.justificada (¿está justificada?)
--     impacto en la métrica      → tipos_ausencia.cuenta_ausentismo (¿computa en la tasa?)
--
-- "Injustificada" es un valor del SEGUNDO eje ocupando una fila del PRIMERO. Consecuencias
-- concretas, no teóricas:
--   · una ausencia con tipo='Injustificada' Y justificada=true es representable y NO SIGNIFICA
--     NADA. La base la acepta hoy.
--   · una ausencia por enfermedad sin certificado se puede cargar de DOS formas razonables
--     (tipo=Enfermedad + justificada=false, o tipo=Injustificada) que dan reportes distintos.
--   · `services/reportes/_reporte_ausentismo.py` YA calcula el ausentismo injustificado leyendo
--     `justificada`, NO el tipo. O sea que el eje correcto ya está en uso y este tipo no
--     participa del cálculo: es vocabulario redundante que solo puede contradecirlo.
--
-- 🔴 SE DESACTIVA, NO SE BORRA. `solicitudes_ausencia.tipo_id` es una FK SIN ON DELETE: borrar
-- un tipo en uso falla, y si no fallara se llevaría el historial. Es la misma razón por la que
-- este repo no tiene baja física de tipos (ver tipos_ausencia_service.py). Con 0 ausencias
-- ninguna fila queda huérfana, y el día que existan seguirán mostrando su nombre.
--
-- ⚠️ `es_base` se pone en false ADEMÁS de `activo`. Sin eso, el service lo rechazaría al
-- intentar reactivarlo o editarlo: `TIPO_BASE_NO_DESACTIVABLE` protege a los 4 base, y este
-- deja de ser uno. Dejarlo como base y desactivado sería un estado que la UI no puede revertir.
--
-- 🚩 "Otro" NO se toca en esta migración. Es un anti-tipo (existe para que la carga no se trabe
-- y su efecto real es que la información se pierde ahí adentro), pero sin el catálogo real
-- cargado, sacarlo trabaría la carga. Se desactiva cuando RRHH cargue sus tipos propios.

BEGIN;

-- ── (a) La jerarquía ─────────────────────────────────────────────────────────────────────

ALTER TABLE public.tipos_ausencia
    ADD COLUMN IF NOT EXISTS padre_id uuid;

ALTER TABLE public.tipos_ausencia
    DROP CONSTRAINT IF EXISTS tipos_ausencia_padre_id_fkey;
ALTER TABLE public.tipos_ausencia
    ADD CONSTRAINT tipos_ausencia_padre_id_fkey
    FOREIGN KEY (padre_id) REFERENCES public.tipos_ausencia(id) ON DELETE RESTRICT;

-- ON DELETE RESTRICT y no CASCADE: borrar un padre NO puede llevarse a sus hijos, porque cada
-- hijo puede tener ausencias colgando. Es la misma lógica que hace que no exista baja física.

-- Un tipo no puede ser su propio padre. Es lo ÚNICO del ciclo que un CHECK puede expresar (mira
-- una sola fila); los ciclos de 2+ saltos los detecta `ensure_no_ciclo_manager` en el service.
ALTER TABLE public.tipos_ausencia DROP CONSTRAINT IF EXISTS tipos_ausencia_padre_no_es_si_mismo;
ALTER TABLE public.tipos_ausencia ADD CONSTRAINT tipos_ausencia_padre_no_es_si_mismo
    CHECK (padre_id IS NULL OR padre_id <> id);

CREATE INDEX IF NOT EXISTS idx_tipos_ausencia_padre
    ON public.tipos_ausencia (padre_id) WHERE padre_id IS NOT NULL;

COMMENT ON COLUMN public.tipos_ausencia.padre_id IS
    'Tipo padre. NULL = tipo de primer nivel. Profundidad máxima 2 (la guarda vive en el service, no en un CHECK). Ver migración 088.';

-- ── (b) Injustificada: baja lógica ───────────────────────────────────────────────────────

UPDATE public.tipos_ausencia
   SET activo = false, es_base = false
 WHERE nombre = 'Injustificada' AND empresa_id IS NULL;

COMMIT;

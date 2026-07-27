# Plan de desarrollo — AHORA (Fase actual)
**Proyecto:** HR Karstec (RRHH) · **Para:** Claude Code · **Estado:** fuente de verdad de la fase actual

Este documento cubre lo que construimos **ahora**: el cimiento multiempresa + los módulos que se portan de Nexio. Lo nuevo de cero (proyectos, costeo, permisos, etc.) está en `PLAN_DESARROLLO_DESPUES.md` y **depende de que esta fase esté terminada**.

---

## 0. Contexto y stack

- **Frontend:** Next.js 15 (App Router) + TypeScript + Tailwind + Shadcn/ui. Cliente HTTP en `services/api.ts` (`apiFetch`, JWT desde `localStorage`). Tokens de diseño en `styles/design-system.ts`. Fuente Inter.
- **Backend:** Python 3.11 + FastAPI. Capas `router → service → repository`. Auth por `AuthMiddleware` (deja `request.state.user = {id, rol}`). Cliente `supabase_admin` (service key, **bypassea RLS**). Errores con `AppError {error, message, code}`. Schemas Pydantic `Base → Create → Update → Response → ListResponse`. Routers finos con prefijo `/api/<modulo>`.
- **DB:** Supabase (PostgreSQL). Migraciones SQL numeradas en `migrations/` (historial de cambios, no bootstrap); la reconstrucción de la base se hace desde `backend/db/schema.sql` (ver `backend/db/README.md`). El consolidado `000_run_all.sql` está **deprecado** (guard que aborta). RLS activa con helper `get_current_user_rol()`. Triggers `fn_auditoria()` (auditoría automática) y `set_updated_at()`. Buckets: `documentos`, `cvs`, `avatars`, `reportes`.

## 1. Reglas transversales (aplican a TODO lo nuevo de esta fase)

1. **Multiempresa:** todas las tablas llevan `empresa_id`. (Ver Fase 0.) No existe el concepto de "holding" en la UI.
2. **Un solo operador:** el producto lo usa el equipo de RRHH. **Sin checks de rol** en los endpoints nuevos (el enum `admin_rrhh/management/empleado` existe pero hoy no diferencia nada — no tocarlo, no usarlo). **El empleado no entra nunca al sistema.**
3. **Sin flujos de aprobación:** los registros (vacaciones, ausencias, etc.) son informativos; se cargan directo, sin estado `pendiente→aprobada`.
4. **Estado derivado por fecha** donde aplique (ej. vacaciones: `planificada` si la fecha es futura, `tomada` si ya pasó) — calculado contra hoy, más una columna chica para `cancelada` manual. No es un estado que alguien aprueba.
5. **Auditoría:** enganchar el trigger `fn_auditoria()` a cada tabla nueva. **No** hacer log manual.
6. **Identificador de sección:** cada módulo registra su nombre de ruta estable (`vacaciones`, `ausencias`, etc.) en una lista central. Cuesta cero ahora y deja la capa de permisos (fase Después) como plug-and-play. **No omitir este paso.**
7. **Autorización:** como el backend usa `supabase_admin` (bypassa RLS), las RLS son segunda línea de defensa. En esta fase no hay checks de rol; cualquier usuario autenticado opera.
8. **Patrón de trabajo por módulo:** (1) SQL en Supabase → (2) prompt backend FastAPI → (3) prompt frontend → (4) test. Antes de escribir, leer un router y una página ya existentes (empleados/vacantes) y calcar su patrón.

---

## 2. FASE 0 — Cimiento multiempresa (bloquea todo lo demás)

HR Karstec hoy es **mono-empresa** (no existe tabla `empresas` ni columna `empresa_id`). Hay que volverlo multiempresa **antes** de portar nada.

> **Obra abierta:** esta fase puede romper temporalmente módulos que ya funcionan (empleados, vacantes, costos, onboarding, etc.). Llevar una **lista de lo que se rompe** para dejar todo funcional al cerrar la fase. Lo único que puede quedar pendiente es lo que no está desarrollado en ningún proyecto.

### 2.1 Tabla `empresas` + retrofit
- Crear `empresas (id uuid pk, nombre text, activa bool default true, created_at, updated_at)`.
- Agregar `empresa_id uuid references empresas(id)` a **todas** las tablas de negocio existentes (empleados, areas, vacantes, candidatos, onboarding_*, offboarding_*, costos_nomina, presupuesto_areas, sucesion_*, planes_carrera*, assessment_*, etc.).
- **Migración de datos:** crear la empresa #1 = "HR Karstec" y asignar `empresa_id` de esa empresa a todos los registros existentes.
- Actualizar **cada query** de routers/repositories existentes para filtrar por la empresa activa.
- Las áreas son **por empresa** (distintas aunque compartan nombre).

### 2.2 DNI
- Agregar `dni text unique` a `empleados` (hoy no existe; existe `legajo` y `cuil`).
- La **importación de nómina (Excel/CSV)** debe traer el DNI. Es la llave que después usará el link público de carga de horas.

### 2.3 Selector de empresa + empresa activa
- Selector en el topbar con opción **"Todas las empresas"** + cada empresa individual.
- La **empresa activa** vive en la sesión (header/estado). Todo el backend filtra por ella; "Todas" = sin filtro (vista consolidada).
- Acceso por empresa: dejar preparada una tabla `acceso_empresa (usuario_id, empresa_id, habilitado)` — hoy todos habilitados en todas; la gestión real es de la fase Después (capa de permisos).

---

## 3. FASE 1 — Módulos portados de Nexio

Cada módulo: SQL (con `empresa_id`) → backend → frontend. Vista única de RRHH (no hay "vista empleado"). El código real de referencia está en la extracción de Nexio (`EXTRACCION_NEXIO_PARA_PORTAR.md`).

### 3.1 Vacaciones + Mapa
- Tabla `solicitudes_vacaciones (id, empresa_id, empleado_id, fecha_desde, fecha_hasta, dias, comentario, estado, created_at)`. `estado` = `cancelada` opcional; planificada/tomada se **derivan por fecha**.
- Días = diferencia inclusiva + 1 (ambos extremos cuentan).
- Mapa de vacaciones: calendario que pinta las franjas por empleado (reconstruir por comportamiento; en Nexio no vino completo).
- Export a Excel (portar `lib/export-vacaciones.ts`).

### 3.2 Ausencias
- Tabla `solicitudes_ausencia (id, empresa_id, empleado_id, fecha, motivo, tipo, created_at)`, `tipo IN (enfermedad, personal, otro)`. Clon de vacaciones.

### 3.3 Asistencia
- Tabla `registros_asistencia (id, empresa_id, empleado_id, tipo, fecha, hora_entrada, hora_salida, metodo, created_at)`. Índices por empleado y fecha. Cálculo de horas trabajadas. Export Excel.
- **Fuera de alcance:** check-in automático por WiFi (era de la app mobile de Nexio).

### 3.4 Capacitaciones
- Tablas `capacitaciones` + `empleado_capacitacion` (estado pendiente/en_curso/completado, categorías). Portar tal cual con `empresa_id`.

### 3.5 Evaluaciones de desempeño
- **Tabla nueva `evaluaciones_desempeno`** (NO reutilizar ni tocar `assessment_*`, que es otra cosa en HR Karstec).
- Portar la lógica de scoring de Nexio (criterios, conversión 1-5 ↔ 1-10, ciclo activo en `configuracion_empresa`).

---

## 4. Orden de ejecución (esta fase)

1. Fase 0 completa (empresas + retrofit + DNI + selector). **No portar nada antes de esto.**
2. Vacaciones + Mapa (el de mayor uso diario).
3. Ausencias (clon rápido).
4. Asistencia.
5. Capacitaciones.
6. Evaluaciones de desempeño.

Al cerrar: revisar la lista de "qué se rompió" en el retrofit y dejar todos los módulos existentes funcionales.

---

## 5. Fuera de alcance de esta fase (van en `PLAN_DESARROLLO_DESPUES.md`)
Proyectos · Equipos · Catálogos configurables (seniority/rol/tipos) · Costeo por proyecto · Carga de horas por link público · Presupuesto vs. real · Organigrama unificado por proyecto · Informes por empresa/proyecto · Skills · Días especiales · Balance de vacaciones · Capa de permisos · Links públicos generalizados · Indicadores.

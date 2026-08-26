# Auditoría Funcional — HR Karstec (Sofia)
**Fecha:** 2026-06-02 | **Solo diagnóstico — sin modificaciones al código**

---

## Hallazgo sistémico crítico (leer primero)

El retrofit multiempresa está **arquitectónicamente completo en el código** (los repos tienen filtros por `empresa_id`, los formularios envían `empresa_id`, los routers extraen `empresa_id` del header) pero **ninguna migración SQL añade la columna `empresa_id` a las tablas antiguas**. Las 12 tablas pre-multiempresa siguen sin ese campo en la base de datos.

Tablas viejas sin `empresa_id` en ninguna migración (001–035):

| Tabla | Migración origen |
|-------|-----------------|
| `empleados` | 003 |
| `areas` | 002 |
| `vacantes` | 005 |
| `candidatos` | 006 |
| `onboarding_templates` | 007 |
| `onboarding_instancias` | 009 |
| `offboarding_instancias` | 011 |
| `costos_nomina` | 013 |
| `presupuesto_areas` | 014 |
| `sucesion_posiciones` | 015 |
| `planes_carrera` | 016 |
| `assessment_campanas` | 018 |

Tablas nuevas **con** `empresa_id` (funcionan bien con filtrado multiempresa):
`solicitudes_vacaciones` (036), `solicitudes_ausencia` + `tipos_ausencia` (037), `capacitaciones` (038), `empleado_capacitacion` (039), `ev_plantillas` (040), `ev_criterios` (041), `ev_ciclos` (042), `ev_instancias` (043), `ev_resultados` (044).

**Consecuencia práctica:** cuando el usuario selecciona una empresa específica en el topbar, el frontend envía `X-Empresa-Id: <uuid>` → el backend pasa un `empresa_id` no-nulo a los repos → los repos ejecutan `.eq("empresa_id", str(uuid))` sobre tablas que no tienen esa columna → error de Supabase/PostgreSQL en runtime. Cuando el usuario tiene "Todas las empresas" (empresa_id=null), el filtro no se aplica y la query tiene éxito, pero sin discriminación multiempresa.

---

## Tabla resumen

| # | Funcionalidad | Estado | Corte |
|---|---------------|--------|-------|
| 1 | Login / Logout / Refresh token | ✅ FUNCIONA | — |
| 2 | Selector de empresa (UI) | ✅ FUNCIONA | — |
| 3 | Gestión de empresas — CRUD | ✅ FUNCIONA | — |
| 4 | Toggle activa/inactiva empresa | ✅ FUNCIONA | — |
| 5 | Upload logo empresa | ✅ FUNCIONA | — |
| 6 | Áreas dentro de empresa (EmpresaAreasTab) | ✅ FUNCIONA | — |
| 7 | Áreas — listado global (page Areas) | ⚠️ PARCIAL | Crash si empresa_id ≠ null |
| 8 | Áreas — crear | ⚠️ PARCIAL | Crash si empresa_id ≠ null |
| 9 | Áreas — editar | ⚠️ PARCIAL | Crash si empresa_id ≠ null |
| 10 | Áreas — eliminar | ✅ FUNCIONA | Sin filtro empresa_id en DELETE |
| 11 | Empleados — listar | ⚠️ PARCIAL | Crash si empresa_id ≠ null |
| 12 | Empleados — ver detalle | ⚠️ PARCIAL | Crash si empresa_id ≠ null |
| 13 | Empleados — crear | ❌ ROTO | INSERT falla: columna empresa_id no existe |
| 14 | Empleados — editar | ⚠️ PARCIAL | Crash si empresa_id ≠ null |
| 15 | Empleados — "eliminar" | ⚠️ PARCIAL | Endpoint existe; no hay botón delete en la UI |
| 16 | Importar CSV empleados (preview) | ✅ FUNCIONA | — |
| 17 | Importar CSV empleados (confirmar) | ❌ ROTO | `save()` mete empresa_id en INSERT → crash |
| 18 | Organigrama — ver árbol | ⚠️ PARCIAL | Crash si empresa_id ≠ null (areas no tiene col) |
| 19 | Vacantes — listar | ⚠️ PARCIAL | Crash si empresa_id ≠ null |
| 20 | Vacantes — crear | ⚠️ PARCIAL | No hay empresa_id en tabla; INSERT no la manda |
| 21 | Vacantes — editar | ⚠️ PARCIAL | Sin empresa_id, update funciona |
| 22 | Candidatos — ver pipeline | ⚠️ PARCIAL | Crash si empresa_id ≠ null |
| 23 | Candidatos — crear manualmente | ⚠️ PARCIAL | Sin empresa_id en tabla; funciona si repo no la manda |
| 24 | Candidatos — mover de etapa | ✅ FUNCIONA | `PUT /api/candidatos/{id}/etapa` — sin empresa_id |
| 25 | Vacantes — publicar en LinkedIn (Zernio) | ✅ FUNCIONA | — |
| 26 | Vacantes — revisar emails Gmail | ✅ FUNCIONA | — |
| 27 | Candidatos — crear desde email | ✅ FUNCIONA | — |
| 28 | Onboarding — listar procesos activos | ⚠️ PARCIAL | Crash si empresa_id ≠ null |
| 29 | Onboarding — iniciar proceso | ⚠️ PARCIAL | INSERT en onboarding_instancias con empresa_id → crash |
| 30 | Onboarding — completar tarea | ⚠️ PARCIAL | Depende del instancia_id; si el proceso existe, funciona |
| 31 | Onboarding Templates — listar | ⚠️ PARCIAL | Crash si empresa_id ≠ null (tabla no tiene col) |
| 32 | Onboarding Templates — crear | ⚠️ PARCIAL | INSERT con empresa_id → crash |
| 33 | Onboarding Templates — editar nombre/desc | ✅ FUNCIONA | Update no envía empresa_id |
| 34 | Onboarding Templates — agregar tarea | ✅ FUNCIONA | tabla onboarding_tareas, sin empresa_id |
| 35 | Onboarding Templates — editar tarea | ✅ FUNCIONA | — |
| 36 | Onboarding Templates — eliminar tarea | ✅ FUNCIONA | — |
| 37 | Onboarding Templates — eliminar template | ⚠️ PARCIAL | Funciona si enterprise_id=null; soft-delete |
| 38 | Offboarding — iniciar desde empleado | ⚠️ PARCIAL | Instancia se crea; empleado.estado NUNCA cambia a "baja" |
| 39 | Offboarding — marcar activo devuelto | ✅ FUNCIONA | Sin empresa_id en repo de activos |
| 40 | Offboarding — listar instancias | ⚠️ PARCIAL | Crash si empresa_id ≠ null |
| 41 | Costos — dashboard KPIs | ⚠️ PARCIAL | KPI costos_nomina: crash si empresa ≠ null |
| 42 | Costos — cargar nómina (manual) | ⚠️ PARCIAL | costos_nomina sin empresa_id; upsert falla si col incluida |
| 43 | Costos — importar nómina CSV (preview) | ✅ FUNCIONA | Solo parsea, no toca DB |
| 44 | Costos — importar nómina CSV (confirmar) | ⚠️ PARCIAL | `save_nomina()` podría crashear si pasa empresa_id |
| 45 | Costos — editar entrada nómina | ⚠️ PARCIAL | Mismo problema que cargar nómina |
| 46 | Costos — fijar presupuesto área | ⚠️ PARCIAL | presupuesto_areas sin empresa_id; filtro crashea |
| 47 | Sucesión — mapa de talento (nine-box) | ⚠️ PARCIAL | Crash si empresa_id ≠ null (filtro sobre empleados) |
| 48 | Sucesión — crear plan de carrera | ⚠️ PARCIAL | INSERT en planes_carrera con empresa_id → crash |
| 49 | Sucesión — actualizar readiness | ⚠️ PARCIAL | UPDATE no envía empresa_id; funciona si plan existe |
| 50 | Sucesión — agregar hito | ✅ FUNCIONA | planes_carrera_hitos no tiene filtro empresa |
| 51 | Sucesión — completar hito | ✅ FUNCIONA | — |
| 52 | Sucesión — analizar posición (IA) | ⚠️ PARCIAL | N+1 queries; crashea si empresa_id ≠ null |
| 53 | Assessment — listar campañas | ⚠️ PARCIAL | assessment_campanas sin empresa_id; crash si empresa ≠ null |
| 54 | Assessment — crear campaña | ⚠️ PARCIAL | INSERT con empresa_id → crash |
| 55 | Assessment — generar link (enviar evaluación) | ⚠️ PARCIAL | assessment_links sin empresa_id verificado |
| 56 | Assessment — evaluación pública (token) | ✅ FUNCIONA | Ruta pública, sin filtro empresa, persiste |
| 57 | Assessment — ver resultados | ✅ FUNCIONA | Sin filtro empresa en assessment_resultados |
| 58 | Assessment — descargar reporte PDF | ❌ ROTO | Botón `disabled` en UI; feature no implementada |
| 59 | Vacaciones — listar | ✅ FUNCIONA | Nueva tabla con empresa_id |
| 60 | Vacaciones — crear | ✅ FUNCIONA | — |
| 61 | Vacaciones — cancelar | ✅ FUNCIONA | — |
| 62 | Vacaciones — mapa (vista calendario) | ✅ FUNCIONA | Renderizado client-side desde mismos datos |
| 63 | Vacaciones — exportar CSV | ✅ FUNCIONA | Client-side, sin llamada extra a API |
| 64 | Ausencias — listar | ✅ FUNCIONA | Nueva tabla con empresa_id |
| 65 | Ausencias — crear | ✅ FUNCIONA | — |
| 66 | Ausencias — editar | ✅ FUNCIONA | — |
| 67 | Ausencias — eliminar | ✅ FUNCIONA | — |
| 68 | Ausencias — exportar CSV | ✅ FUNCIONA | Client-side |
| 69 | Ausencias — crear nuevo tipo | ✅ FUNCIONA | tipos_ausencia sin empresa_id (catálogo global) |
| 70 | Capacitaciones — listar catálogo | ✅ FUNCIONA | Nueva tabla con empresa_id |
| 71 | Capacitaciones — crear | ✅ FUNCIONA | — |
| 72 | Capacitaciones — editar | ✅ FUNCIONA | — |
| 73 | Capacitaciones — eliminar (soft si hay asign.) | ✅ FUNCIONA | — |
| 74 | Asignaciones — listar | ✅ FUNCIONA | empresa_id derivado del empleado |
| 75 | Asignaciones — crear | ✅ FUNCIONA | — |
| 76 | Asignaciones — cambiar estado | ✅ FUNCIONA | Auto-fecha cuando pasa a "completado" |
| 77 | Asignaciones — eliminar | ✅ FUNCIONA | — |
| 78 | Asignaciones — subir certificado | ✅ FUNCIONA | Bucket "documentos", signed URL |
| 79 | Evaluaciones — Plantillas CRUD | ✅ FUNCIONA | Nuevas tablas |
| 80 | Evaluaciones — agregar/editar/borrar criterio | ✅ FUNCIONA | — |
| 81 | Evaluaciones — Ciclos CRUD | ✅ FUNCIONA | empresa_id heredado de plantilla |
| 82 | Evaluaciones — cerrar ciclo | ✅ FUNCIONA | — |
| 83 | Evaluaciones — asignar empleados a ciclo | ✅ FUNCIONA | Crea instancias + filas vacías en ev_resultados |
| 84 | Evaluaciones — puntuar criterio | ✅ FUNCIONA | UPDATE ev_resultados |
| 85 | Evaluaciones — finalizar instancia | ✅ FUNCIONA | Calcula puntaje_global ponderado |
| 86 | Evaluaciones — exportar Excel | ✅ FUNCIONA | Client-side con xlsx |
| 87 | Reportes — generar (headcount/rotacion/costos/vacantes/onboarding) | ⚠️ PARCIAL | reporte_generators filtra empleados por empresa_id → crash |
| 88 | Reportes — generar ad-hoc con IA | ⚠️ PARCIAL | Queries de contexto filtran empleados → crash si empresa ≠ null |
| 89 | Reportes — ver historial | ⚠️ PARCIAL | reportes_generados sí tiene empresa_id; debería funcionar |
| 90 | Reportes — exportar PDF/Excel | ✅ FUNCIONA | Usa data ya generada guardada en DB |
| 91 | Dashboard — métricas | ⚠️ PARCIAL | KPI costos y onboarding crashean si empresa ≠ null |
| 92 | Integraciones — Google OAuth (conectar) | ✅ FUNCIONA | — |
| 93 | Integraciones — desconectar Google | ✅ FUNCIONA | — |
| 94 | Integraciones — guardar API key Anthropic | ✅ FUNCIONA | — |
| 95 | Integraciones — guardar API key Zernio | ✅ FUNCIONA | — |
| 96 | Panel IA (AIPanel) — chat HR | ⚠️ PARCIAL | Modelo claude-sonnet-4-20250514 puede ser ID incorrecto |
| 97 | Cerrar sesión | ✅ FUNCIONA | — |

---

## Detalle por módulo

### Auth
**✅ FUNCIONA completo.**
- `POST /api/auth/login` → JWT + refresh cookie → persiste.
- `POST /api/auth/logout` → limpia sesión.
- `POST /api/auth/refresh` → rota token.

---

### Empresas
**✅ FUNCIONA completo.**
- La tabla `empresas` (creada fuera del rango de tablas viejas, con empresa_id propio) funciona correctamente.
- CRUD, toggle activa, upload logo (`POST /api/empresas/{id}/logo` → bucket storage) — todos persistentes.
- `EmpresaAreasTab.tsx` carga las áreas de esa empresa específica — funciona porque hace `fetchAreas(empresaId)` directo.

---

### Áreas (página global)

**⚠️ PARCIAL — crash si empresa_id ≠ null.**

`area_repo.py:52` ejecuta `.eq("empresa_id", empresa_id)` sobre la tabla `areas` que **no tiene la columna** `empresa_id` (migración 002). Cuando el usuario tiene seleccionada una empresa específica, la query falla.

Cuando empresa_id es null (modo "Todas"): la query no filtra y devuelve todas las áreas. Funciona, pero sin segregación.

Ruta: `area_repo.py:52` (filtro), `migrations/002_create_areas.sql` (columna ausente).

---

### Empleados

**❌ CREAR — ROTO.**
`empleado_repo.py:85` → `payload["empresa_id"] = str(empresa_id)` → `supabase_admin.table("empleados").insert(payload)` → PostgreSQL: columna `empresa_id` no existe → error 500. Toda creación de empleado falla.

**⚠️ LISTAR / VER / EDITAR — PARCIAL.**
`empleado_repo.py:52` filtra `empleados` por `empresa_id` → mismo crash cuando empresa ≠ null.

**⚠️ ELIMINAR — sin botón en UI.**
El endpoint `DELETE /api/empleados/{id}` existe en el backend pero no hay botón de eliminar en la tabla de empleados. Endpoint huérfano.

Rutas críticas: `empleado_repo.py:85` (INSERT), `empleado_repo.py:52` (SELECT), `migrations/003_create_empleados.sql` (columna ausente).

---

### Importación CSV Empleados

**✅ PREVIEW — funciona.** Solo parsea el CSV, sin tocar DB.

**❌ CONFIRMAR — ROTO.**
`importacion.py:67,82` llama a `service.update_empleado_por_dni()` y `service.create_empleado()`. El segundo usa `empleado_repo.save()` que intenta insertar `empresa_id` → crash. El primero (`update_por_dni`) actualiza sin empresa_id en el payload, probablemente funciona para actualizaciones; falla para creaciones.

Ruta: `routers/importacion.py:82`, `empleado_repo.py:85`.

---

### Organigrama

**⚠️ PARCIAL — crash si empresa_id ≠ null.**
`organigrama_service.py` delega en `area_repo` que filtra áreas por empresa_id. La tabla `areas` no tiene esa columna. Cuando empresa es null, devuelve todo el árbol sin discriminar.

Ruta: `repositories/area_repo.py:52`.

---

### Vacantes

**⚠️ PARCIAL — listado crash si empresa_id ≠ null.**
`vacante_repo.py` filtra `vacantes` por empresa_id, pero la tabla no tiene esa columna (migración 005). Los datos se muestran sin filtrar en modo "Todas".

**Candidatos — mover etapa: ✅ funciona.**
`PUT /api/candidatos/{id}/etapa` → `candidato_repo.py` actualiza sólo el campo `etapa`, sin empresa_id.

**Candidatos — listar: ⚠️ PARCIAL.**
`candidato_repo.py:32` filtra `candidatos` por empresa_id → tabla sin columna → crash si empresa ≠ null.

Ruta: `repositories/candidato_repo.py:32`, `migrations/006_create_candidatos.sql`.

---

### LinkedIn / Zernio / Gmail (Integraciones vacantes)

**✅ FUNCIONA completo.**
- `publicarLinkedin` → Zernio API real en `services/zernio_service.py:71-77`.
- `fetchEmailsCandidatos` → Gmail real en `services/gmail_service.py:72-114`.
- `crearCandidatoDesdeEmail` → extrae From header, crea candidato en DB.
- URLs frontend vs backend coinciden exactamente: `/emails-candidatos`, `/candidatos-desde-email`.

---

### Onboarding

**⚠️ PARCIAL generalizado.**

- **Listar procesos:** `onboarding_repo.py:52` filtra `onboarding_instancias` por empresa_id → tabla sin columna → crash si empresa ≠ null.
- **Iniciar proceso:** `onboarding_repo.py:83` INSERT en `onboarding_instancias` con empresa_id → crash siempre.
- **Completar tarea:** `PUT /{instancia_id}/tareas/{tarea_id}/completar` → actualiza `onboarding_progreso` (tabla sin empresa_id), pero funciona si la instancia ya existe.

**Templates:**
- **Listar templates:** `onboarding_templates_repo.py` filtra `onboarding_templates` por empresa_id → tabla sin columna → crash si empresa ≠ null.
- **Crear template:** INSERT con empresa_id → crash.
- **Editar nombre/desc:** UPDATE sin empresa_id → funciona.
- **CRUD tareas:** tabla `onboarding_tareas` sin empresa_id pero la operación no envía ese campo → funciona.

Ruta: `repositories/onboarding_repo.py:52,83`, `repositories/onboarding_templates_repo.py`, `migrations/009_create_onboarding_instancias.sql`, `migrations/007_create_onboarding_templates.sql`.

---

### Offboarding

**⚠️ PARCIAL — dos problemas:**

**Problema 1 (crítico de negocio): empleado nunca pasa a "baja".**
`offboarding_repo.py:68-82` crea la instancia y los 4 activos default. **No ejecuta ningún UPDATE sobre `empleados`**. El empleado queda con `estado = "activo"` en la tabla. Si se consulta la lista de empleados activos, el empleado aparece como vigente.

**Problema 2: crash si empresa_id ≠ null.**
`offboarding_repo.py:59` filtra `offboarding_instancias` por empresa_id → tabla sin columna → crash al listar.

**Marcar activo devuelto: ✅ funciona.**
`PUT /api/offboarding/{instancia_id}/activos/{activo_id}` → actualiza `offboarding_activos` → sin empresa_id en el filtro.

Ruta: `repositories/offboarding_repo.py:59,68-82`, `migrations/011_create_offboarding_instancias.sql`.

---

### Costos / Nómina

**⚠️ PARCIAL generalizado.**

- **Dashboard costos:** `costo_repo.py:80` filtra `costos_nomina` por empresa_id → tabla sin columna → crash si empresa ≠ null.
- **Cargar nómina (manual):** `costo_service.py:84` → `costo_repo.save_nomina()` → upsert. Si el payload incluye empresa_id, crash; si no, funciona como mono-empresa.
- **Importar CSV nómina (confirmar):** `importacion_nomina.py:53` llama `repo.save_nomina()` → mismo comportamiento.
- **Presupuesto área:** `presupuesto_repo.py:29` filtra `presupuesto_areas` por empresa_id → tabla sin columna (migración 014) → crash si empresa ≠ null.

Ruta: `repositories/costo_repo.py:80`, `repositories/presupuesto_repo.py:29`, `migrations/013_create_costos_nomina.sql`, `migrations/014_create_presupuesto_areas.sql`.

---

### Sucesión (Nine-Box + Planes de Carrera)

**⚠️ PARCIAL generalizado.**

- **Mapa de talento:** `sucesion_repo.py:49` filtra `empleados` por empresa_id → crash si empresa ≠ null.
- **Crear plan de carrera:** `planes_carrera_repo.py:61` INSERT en `planes_carrera` con empresa_id → crash (tabla sin columna, migración 016).
- **Analizar posición:** `sucesion_repo.py:55` filtra empleados por empresa_id → crash. Además hace N+1 queries individuales por empleado sobre `assessment_resultados` (line 60-62).
- **Readiness, hitos, completar hito:** operan sobre `sucesion_posiciones` y `planes_carrera_hitos` via UPDATE; si el registro ya existe, funcionan.

Ruta: `repositories/sucesion_repo.py:49,55`, `repositories/planes_carrera_repo.py:61`, `migrations/015_create_sucesion_posiciones.sql`, `migrations/016_create_planes_carrera.sql`.

---

### Assessment

**⚠️ PARCIAL — campañas crashean; evaluación pública funciona.**

- **Listar campañas:** `assessment_campanas_repo.py:55` filtra `assessment_campanas` por empresa_id → tabla sin columna (migración 018) → crash si empresa ≠ null.
- **Crear campaña:** INSERT con empresa_id → crash.
- **Evaluación pública (`/evaluacion/[token]`):** ruta pública, no requiere autenticación ni empresa_id. La cadena completa funciona: GET token → muestra preguntas → POST submit → `assessment_service._compute_scores()` calcula puntajes → persiste en `assessment_resultados` → actualiza `ninebox` en empleado. ✅
- **Ver resultados:** `assessment_resultados` no tiene filtro empresa → funciona en modo "Todas".
- **Descargar reporte PDF:** botones con atributo `disabled` en `assessment/[id]/page.tsx:175-180`. Feature declarada en UI, no implementada.

Ruta: `repositories/assessment_campanas_repo.py:55`, `assessment/[id]/page.tsx:175-180`, `migrations/018_create_assessment_campanas.sql`.

---

### Vacaciones ✅
**FUNCIONA completo.** Nueva tabla `solicitudes_vacaciones` (migración 036) con `empresa_id`. CRUD, cancelar, mapa de vacaciones (renderizado client-side), export CSV — todos funcionan de punta a punta.

---

### Ausencias ✅
**FUNCIONA completo.** Nueva tabla `solicitudes_ausencia` (migración 037) con `empresa_id`. CRUD completo, creación de tipos nuevos, export CSV.

---

### Capacitaciones + Asignaciones ✅
**FUNCIONA completo.** Nuevas tablas (038, 039) con `empresa_id`. Soft-delete condicional, upload de certificados a bucket, signed URLs, auto-fecha en completado.

---

### Evaluaciones de Desempeño ✅
**FUNCIONA completo.** Todas las tablas nuevas (040–044) con `empresa_id`. Pipeline completo: Plantillas → Criterios → Ciclos → Instancias → Resultados → Finalización con puntaje ponderado. Export Excel client-side.

---

### Reportes

**⚠️ PARCIAL — generación crashea si empresa ≠ null.**

`reporte_generators.py:45,51,57,62,95` filtra `empleados` por empresa_id → tabla sin columna → crash. Los 5 tipos estándar (headcount, rotación, costos, vacantes, onboarding) fallan.

El reporte ad-hoc con IA (`reporte_adhoc.py:70`) usa `anthropic.Anthropic(api_key=settings.anthropic_api_key)` y llama a `claude-sonnet-4-6` — la integración Anthropic es real. Pero las queries de contexto también filtran `empleados` por empresa_id → crash si empresa ≠ null.

**Historial:** `reportes_generados` tiene `empresa_id` → filtra correctamente.
**Export:** opera sobre el reporte ya guardado → funciona.

Ruta: `services/reporte_generators.py:45,51,57,62,95`, `services/reporte_adhoc.py:40-59`.

---

### Dashboard

**⚠️ PARCIAL.**

- KPIs de empleados activos, ingresos, bajas, vacantes activas: funcionan si empresa_id ≠ null crashea; si es null, devuelve todo sin filtrar.
- KPI costos nómina (`dashboard_service.py:80`): filtro sobre `costos_nomina` sin columna → crash si empresa ≠ null.
- KPI onboardings en curso (`dashboard_service.py:84`): filtro sobre `onboarding_instancias` sin columna → crash si empresa ≠ null.

Ruta: `services/dashboard_service.py:80,84`.

---

### Integraciones (configuración)

**✅ Google OAuth, Anthropic key, Zernio key — todos funcionan.**
- Google: flujo OAuth completo con refresh de tokens.
- Anthropic: key guardada en `usuario_integraciones` (migración 032).
- Zernio: key guardada y usada para publicar en LinkedIn.

---

### Panel IA (AIPanel + app/api/ai)

**⚠️ PARCIAL.**
`frontend/app/api/ai/route.ts:3` usa el modelo `claude-sonnet-4-20250514`. Este ID puede corresponder a un modelo deprecado o con nombre incorrecto. El ID correcto en el stack es `claude-sonnet-4-6`. La ruta existe y está implementada, pero si el ID es inválido, toda llamada al chat de IA del panel retorna error.

Ruta: `frontend/app/api/ai/route.ts:3`.

---

### Endpoints huérfanos (backend sin frontend)

| Endpoint | Archivo | Observación |
|----------|---------|-------------|
| `DELETE /api/empleados/{id}` | `routers/empleados.py:74` | No hay botón delete en la tabla de empleados |
| `GET /api/ausencias/{id}` | `routers/ausencias.py:45` | No hay página de detalle de ausencia |
| `GET /api/vacaciones/{id}` | `routers/vacaciones.py:38` | No hay página de detalle de vacación |
| `GET /api/capacitaciones/{id}` | `routers/capacitaciones.py:32` | No hay página de detalle |

---

## Prioridad de cortes críticos

**P0 — Acción visible sin ningún efecto en DB:**

1. **Crear empleado** — cada intento de alta falla con error de DB. El formulario aparece funcional pero no persiste nunca. `empleado_repo.py:85`.

2. **Confirmar importación CSV de empleados** — ídem para alta masiva. `routers/importacion.py:82`.

3. **Iniciar offboarding desde ficha de empleado** — si logra insertar la instancia (depende de empresa_id), el empleado queda como "activo" para siempre. La acción no tiene efecto observable en el estado del empleado. `offboarding_repo.py:68-82`.

4. **Crear campaña de assessment** — formulario visible en UI, INSERT falla siempre si empresa_id ≠ null. `assessment_campanas_repo.py:55`.

5. **Iniciar proceso de onboarding** — acción central del módulo, INSERT falla. `onboarding_repo.py:83`.

6. **Generar cualquier reporte** — botones de generación en la página de reportes no producen nada útil si empresa_id ≠ null. `reporte_generators.py:45`.

7. **"Descargar Reporte" en Assessment** — botones visibles con `disabled`. Feature no existe. `assessment/[id]/page.tsx:175-180`.

**P1 — Módulos que fallan con empresa seleccionada (degradan todo el flujo):**

8. **Dashboard** — KPIs costos y onboarding dan error → métricas incompletas cuando hay empresa activa.

9. **Listar empleados con empresa activa** — la tabla más usada de la app falla. `empleado_repo.py:52`.

10. **Sucesión / Nine-Box con empresa activa** — el mapa de talento no carga. `sucesion_repo.py:49`.

**P2 — Calidad / comportamiento incorrecto:**

11. **Panel IA** — modelo ID potencialmente incorrecto (`claude-sonnet-4-20250514` vs `claude-sonnet-4-6`). `frontend/app/api/ai/route.ts:3`.

12. **Sucesión — Analizar posición** — N+1 queries en `sucesion_repo.py:60-62`. Para equipos grandes, timeout.

---

*Auditoría realizada exclusivamente sobre el código fuente. Sin ejecutar el servidor ni modificar archivos.*

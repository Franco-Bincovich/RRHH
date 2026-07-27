# CLAUDE.md — RRHH (HR Karstec)

> **Ubicación:** raíz del repo RRHH (`RRHH/`), desde donde se ejecuta `claude`. `backend/`, `frontend/`, `docs/` y `migracionAWS/` cuelgan directo de la raíz — **`RRHH/` es el único repo git (no hay repos anidados), y todas las operaciones git corren desde ahí**.

## Documentos de planificación (leer al inicio)
La dirección del producto y el schema están en estos documentos. **Tienen prioridad sobre la memoria.**
- @docs/MODELO_DATOS.md — **fuente de verdad del schema** (si algo contradice una tabla, manda este doc)
- @docs/PLAN_DESARROLLO_AHORA.md — qué construimos ahora
- @docs/PLAN_DESARROLLO_DESPUES.md — qué construimos después

Documentos de la agencia (convenciones obligatorias): ORDEN-Y-LEGIBILIDAD.md · SEGURIDAD-PENTEST.md · BASES-DE-DESARROLLO.md · UX-UI.md.

---

## Qué es este proyecto
RRHH es el repositorio interno de **HR Karstec**: plataforma de gestión del ciclo de vida del empleado, **multiempresa** (2–5 empresas simultáneas), operada por un equipo de RRHH de 3 personas. Reporting con IA vía Claude Sonnet. **Live en https://www.hrkarstec.site**.

## Stack
- **Backend**: Python 3.11 + FastAPI. Arquitectura por capas **router → service → repository** (NO hay controllers).
- **Frontend**: Next.js 16.2.4 (App Router, Turbopack) + TypeScript + Tailwind v4 + Shadcn/ui.
- **DB**: Supabase (PostgreSQL + Auth + Storage), con RLS. (En el destino AWS/RDS **no habrá RLS** — seguridad app-level.)
- **IA**: Anthropic Claude Sonnet. Modelo vigente: **`claude-sonnet-4-6`** (backend y front). ⚠️ No usar strings con fecha (`claude-sonnet-4-20250514` fue retirado el 15/6/2026 → 404). Usar siempre alias sin fecha.
- **Deploy**: Vercel, **dos proyectos separados** (ver sección Deploy).
- **Auth**: `AuthMiddleware` verifica la firma del JWT de Supabase contra el JWKS público (ES256), fail-closed (cualquier fallo → 401 genérico); expone `user_id`, `rol` y `empresa_id` (header `X-Empresa-Id`) en `request.state`. JWKS cacheado por proceso. Refresh automático + logout real. `GET /health` (sin auth) devuelve `{status, env}`.

## Entornos de desarrollo
- **Windows/PowerShell** (Lenovo) y **Mac** (MacBook Pro). El repo se clona limpio en cada una.
- ⚠️ **Un clon limpio NO trae `.env` ni `node_modules`.** Para verificar local hay que reconstruir los `.env` (valores en el dashboard de Vercel: `sofia-backend` y `sofia-front`) y correr `pip install` / `npm install`. Rutas de los env: `backend/.env`, `frontend/.env.local` (en el front es `.env.local`, no `.env`).
- ⚠️ **En la Mac, `npx tsc` a secas baja el paquete equivocado** (`tsc@2.0.4`, no TypeScript). Usar el binario local: `node_modules/.bin/tsc --noEmit`.
- ⚠️ El `python3` del sistema en la Mac puede tener una versión vieja de `supabase` que rompe el import. Para correr tests, crear venv 3.12 con `requirements.txt` + `requirements-dev.txt`.
- PowerShell: sin `&&` (usar `;`). Paths con paréntesis entre comillas.

---

## 🚀 Deploy (Vercel — DOS proyectos)

**Topología actual (resuelta):**
- **`sofia-front`** — Next.js, Root Directory `frontend`. Dominios: `www.hrkarstec.site`, `hrkarstec.site` (307 → www), `sofia-front-eight.vercel.app`. Auto-deploy por push a `main`.
- **`sofia-backend`** — FastAPI, Root Directory `backend`. Dominio: `sofia-backend-pi.vercel.app`. `backend/vercel.json` propio.
- **`sofia`** (proyecto viejo) — sin dominios propios, deploya al pedo en cada push. Candidato a borrar; se dejó por si el ticket de Vercel lo necesitaba.

**El front pega al backend por `NEXT_PUBLIC_API_URL` (URL absoluta), build-time.** El día del cutover a AWS solo cambia esa variable.

**Variables que el front necesita en `sofia-front`:**
- `NEXT_PUBLIC_API_URL = https://sofia-backend-pi.vercel.app` (sin barra final; build-time).
- `ANTHROPIC_API_KEY` — solo la usa `/api/ai` (chat, hoy oculto). Si falta, esa ruta da 500; no rompe el build. **Hoy no está cargada, por decisión.**

**`ALLOWED_ORIGINS` en `sofia-backend`** debe incluir el dominio del front (`https://www.hrkarstec.site`, `https://sofia-front-eight.vercel.app`), sin barra final, separados por coma. Si falta un origin, el login pasa el preflight `OPTIONS` con 400 (CORS) y falla.

**Minas de deploy ya desactivadas (aprendizajes, no repetir):**
- **Trigger de deploy**: la integración Git del front se había desconectado (deploy congelado desde el 6/5). Reconectada. Un push a `main` ahora dispara solo.
- **`vercel.json` de la raíz**: era config mono-proyecto (`builds` front+back) heredada. Con Root Directory por proyecto quedaba huérfano y rompía el serving del front. **Borrado.**
- **Dos `package-lock.json`**: había un stub vacío en la raíz además del real de `frontend/`. Confundía la inferencia de workspace de Turbopack. **Borrado el de la raíz.**
- **`backend/pyproject.toml`**: `@vercel/python` (uv) lo interpretaba como paquete instalable y abortaba el build. Reemplazado por `backend/ruff.toml` + `backend/pytest.ini`. Las deps reales salen de `backend/requirements.txt`.
- 🔴 **Auto-asignación de dominios / Instant Rollback**: si el dashboard tiene un Instant Rollback activo o la auto-asignación deshabilitada, cada push crea un deployment nuevo que **el dominio no toma** → el dominio sigue sirviendo código viejo. Síntoma típico: arreglás algo, pusheás, y el bug persiste. **Fix: Promote to Production del deployment nuevo.** Verificar SIEMPRE después de un push que el "Production Deployment" muestre el commit nuevo, no uno viejo.

**Verificación post-push (orden obligatorio, por ser dos proyectos):**
1. `sofia-backend` deployó el commit nuevo, READY, dominio apuntando ahí (no uno viejo).
2. `curl.exe -i https://sofia-backend-pi.vercel.app/health` → 200.
3. `sofia-front` deployó, READY.
4. Recién ahí probar la feature en `hrkarstec.site`.
> Si una feature nueva de front tira 404 en una llamada al backend, es que el front salió antes que el backend. Esperar al backend y reprobar, no tocar código.

⚠️ La raíz `/` del front redirige a `/login` (antes era el scaffold de create-next-app). Un usuario con sesión válida que entra a `/` cae en `/dashboard` (guard en `login/page.tsx`). El backend en `/` da 404 de plataforma (no tiene endpoint raíz) — es normal, `/health` es el que responde.

---

## 🎯 FOCO ACTUAL

**Fases 0, 1, 2 y 3 COMPLETAS y en producción.** Fase 0 (blindaje pre-testing) · Fase 1 (reportes + KPIs) · **Fase 2 (barrera de empresa)** · **Fase 3 (deuda estructural)**.

**Lo que sigue:** entregar usuarios a RRHH para testing sobre datos reales · handoff a AWS (`migracionAWS/`) · CV screening. **Fase 4 sigue bloqueada por datos de RRHH.**

### 🔴 EL PROBLEMA #1 NO ES CÓDIGO: RRHH no cargó datos
Verificado en producción (jul 2026): 1 empresa, 19 empleados, y casi todo lo demás vacío:
- `manager_id` 0/19 · `modalidad_contratacion` 0/19 · `seniority` 4/19
- `solicitudes_vacaciones` 0 · `solicitudes_ausencia` 0 · `costos_nomina` 0 · vacantes abiertas 0
- Único campo poblado: `fecha_nacimiento` 19/19 (por eso el KPI de cumpleaños muestra datos).

**Consecuencia:** los reportes y KPIs están correctos pero salen VACÍOS. Antes de entregar a RRHH hay que avisarles explícitamente, o van a abrir pantallas vacías y creer que están rotas. El sistema no muestra valor hasta que carguen datos. Esto NO es deuda técnica — es un bloqueante de adopción.

### Al entregar a testing, decirle a RRHH:
1. Los reportes/KPIs salen vacíos hasta que carguen dotación, vacaciones, ausencias, costos. No están rotos.
2. `manager_id` sin cargar → un usuario `mandos_medios` no ve NADA (su ownership depende de ese campo). Todavía no probar ese rol.
3. Qué se espera que "traten de romper".

### Fases cerradas (no reabrir)
- ✅ **FASE 2 — Barrera de empresa (commits `bd95e98` + `9d7baa7`).** **92/92 endpoints con id de recurso donde aplica** validan empresa, y **13/13 superficies de VACACIONES y AUSENCIAS** componen además el eje de ownership. Quedan **8 endpoints marcados NO APLICA, con razón**: `usuarios` (`DELETE /{user_id}` — los usuarios no cuelgan de una empresa, por decisión de producto), `empresa` (`GET`/`PUT`/`PATCH /{id}/activa`/`POST /{id}/logo` — la empresa *es* el recurso), `assessment` público (`GET`/`POST /evaluacion/{token}` — sin auth, la autorización es el token) e `integraciones` (`DELETE /{tipo}` — scopeado por `user_id`, no por empresa). **La regla permanente está en "Patrón de barrera de empresa" — leerla antes de escribir un endpoint nuevo.**
- ✅ **FASE 3 — Deuda estructural (commits `51832e2` + `a6acaed`).** `fetchEmpleados`/`exportarEmpleados` a objeto de opciones (10 call sites) · `sucesion/page.tsx` 855 → **85** (8 componentes + 2 hooks en `components/features/sucesion/`) · N+1 de sucesión resuelto por batch.
- **FASE 4 — Bloqueada por RRHH:** import Excel de vacaciones/ausencias (esperando archivos); carga real de `manager_id`; import de objetivos (trabado por modelo).

**Pendientes de RRHH (bloqueantes de datos):**
- Cargar datos reales en los módulos (ver arriba).
- Excel reales de vacaciones y ausencias (sin ellos no se define el parser de import).
- Evaluaciones: ¿pueden exportar DNI o legajo? · los 2 líderes sin nota final · qué es "Kolektor".

---

## Estructura (backend)
```
backend/
├── main.py              ← entrada, registro de routers, middleware
├── config/settings.py   ← única fuente de config y env (Settings() se instancia en import)
├── routers/             ← endpoints, sin lógica (límite 80 líneas)
├── services/            ← lógica de negocio (límite 150)
│   ├── _empleado_scope.py     ← barrera de empresa/ownership sobre el empleado target (Fase 2)
│   ├── _adjunto_padres.py     ← resolver de la entidad padre de un adjunto (Fase 2)
│   ├── _empleados_write.py    ← altas/ediciones de empleado, extraído por límite (Fase 2)
│   └── _onboarding_iniciar.py ← alta de onboarding, extraído por límite (Fase 2)
├── repositories/        ← único acceso a DB (límite 100)
├── integrations/        ← wrappers externos (supabase_client, anthropic)
├── schemas/             ← Pydantic in/out
├── utils/               ← permisos.py, errors.py, logger.py
├── db/schema.sql        ← FUENTE DE VERDAD de reconstrucción (47 tablas, 310 constraints, 220 índices)
├── migrations/          ← SQL versionado (backend va por 079; 075–077 viven en migracionAWS/)
├── ruff.toml            ← config de ruff (reemplazó pyproject.toml, por Vercel)
├── pytest.ini           ← config de pytest (asyncio_mode=auto, testpaths=tests)
└── tests/
```

**Env vars obligatorias** (sin default → rompen el import si faltan): `supabase_url`, `supabase_anon_key`, `supabase_service_key`, `jwt_secret`, `anthropic_api_key`, `resend_api_key`. La migración a AWS agrega `database_url`.

**Salud de base:** migraciones 072/073/074 corrigieron drift de producción. `db/schema.sql` es la fuente de reconstrucción (probado en Postgres limpio). `000_run_all.sql` **deprecado con guard que aborta**. ⚠️ `schema.sql` **no incluye los 36 triggers `updated_at`** — se recrean aparte (migración 077 en staging).

---

## Convenciones de código
- Errores: siempre `AppError(message, code, status_code)`.
- Logs: solo eventos de negocio importantes. Sin `print()` / `console.log()` — logger centralizado.
- Config: solo vía `settings`, nunca `os.environ` directo.
- **Límites de líneas (estrictos)**: router 80 · service 150 · repository 100 · componente React 150 · hook 80 · otros 200. Medir SIEMPRE con `.Count` (no `Measure-Object -Line`, subestima).
- Next.js 16: `params` en rutas dinámicas se await (es Promise).
- NO usar `from __future__ import annotations` en routers FastAPI (rompe resolución de anotaciones Pydantic).
- Helpers Supabase en políticas RLS necesitan `SECURITY DEFINER` (evita dependencia circular en login).

## Reglas para Claude Code
1. No modificar archivos fuera del scope de la tarea.
2. Si un archivo supera su límite, **proponer cómo dividirlo antes de escribir**.
3. Cada commit = un cambio coherente (lo hace Franco manualmente, nunca Claude Code).
4. Docstrings en funciones de services e integrations.
5. **Performance, escalabilidad, seguridad y legibilidad gobiernan toda decisión automáticamente** — elegir la opción más segura/escalable/performante sin preguntar, salvo tradeoff funcional real.
6. Diagnóstico read-only primero → revisión → implementación. Nunca asumir nada del código sin leerlo.
7. Una tarea atómica por sesión.
8. Verificar contra los archivos fuente, no contra el auto-reporte de Claude Code.
9. Producción puede driftear de las migraciones — verificar contra el schema vivo (Franco tiene acceso al catálogo por MCP de Supabase; Claude Code no).
10. Commits y push desacoplados: **no hay push a GitHub hasta que Franco lo decida**.
11. Preferir commits por sub-sesión sobre commits por tarea entera.
12. Cortar sub-tareas por módulo cuando hay división de archivos de por medio.
13. Diagnóstico pedido → devolver SOLO diagnóstico (read-only). Implementación pedida → escribir código, no otro diagnóstico.
14. **Cada repo nuevo es un repo más a portar a asyncpg** (hoy son 46). Priorizar wires sobre repos existentes; repo nuevo → moldearlo sobre `migracionAWS/empleado_repo_NEW`.

---

## Modelo de roles funcionales (COMPLETO)
Tres roles en `utils/permisos.py`:
- **admin_rrhh** — lectura + escritura en todo.
- **gerencia_lectura** — lectura en todo, escritura en nada.
- **mandos_medios** — lectura + escritura solo en VACACIONES y AUSENCIAS; sin acceso al resto.
- Rol desconocido / None → **fail-closed**.

Núcleo: `puede(rol, seccion, accion)`, `require_permission(seccion, accion)` (dependency factory → `AppError(..., "FORBIDDEN", 403)`). Enum `Seccion` (26 valores). `MANDOS_MEDIOS_SECCIONES = frozenset({VACACIONES, AUSENCIAS})`. **174 gates `Depends(require_permission(...))` en 43 routers.** Espejo front en `frontend/services/permisos.ts` (riesgo de divergencia manual). Sidebar filtra `NAV_GROUPS` por permiso, AuthGuard gatea por ruta, `useCanWrite` oculta botones de escritura.

**Decisión de producto (NO reabrir):** todo usuario, sin importar rol, accede a TODAS las empresas. No existe "usuario limitado a ciertas empresas".

---

## 🔒 Patrón de barrera de empresa (REGLA PERMANENTE — Fase 2)

**Todo endpoint que reciba un id de recurso de afuera valida que ese recurso sea de la empresa del request.** Sin esto, un UUID ajeno entra igual y la operación se ejecuta sobre él. Es la regla que más fácil se rompe al agregar un módulo: el gate de permisos (`require_permission`) NO alcanza — dice *qué podés hacer*, no *sobre qué fila*.

### Dónde va el filtro
- **Forma A (preferida):** el repo acepta `empresa_id` y el filtro va **en el WHERE de la query**. Una sola ida a la base, imposible de saltear. Es lo que hace `_with_empresa(q, empresa_id)`.
- **Forma B (solo si el repo no lo acepta):** traer la fila y **comparar en el service**. Más caro y más fácil de olvidar; si tocás ese repo, migralo a Forma A.

### El 404 es idéntico, siempre
"No existe" y "es de otra empresa" devuelven el **mismo status, el mismo `code` y el mismo mensaje**. **Nunca un 403.** Un 403 (o un mensaje distinto) confirma que el recurso existe y que es de otro — es un oráculo de enumeración. El literal canónico vive en **`services/_empleados_utils.py::empleado_or_404`** (`"Empleado no encontrado"` / `EMPLEADO_NOT_FOUND` / 404): **no lo dupliques**, delegá, así el mensaje no puede divergir.

### 🚨 El orden de los gates
**La barrera de empresa va ANTES de cualquier chequeo de estado que responda otro código.** Si va después, el otro código delata la existencia del recurso ajeno.
> Caso real: `iniciar_onboarding` chequeaba "ya tiene onboarding activo" antes de la empresa. Un empleado de otra empresa con onboarding activo respondía **409 `ONBOARDING_ALREADY_ACTIVE`** en vez de 404 → confirmaba que existía. Corregido; el porqué está escrito en `services/_onboarding_iniciar.py`.

### `empresa_id=None` no restringe
`None` = vista consolidada ("Todas las empresas", semántica de `get_empresa_id`). **No es un fallo de validación**: cualquier recurso existente pasa. La barrera limita *cuál* recurso podés elegir, no de dónde sale la empresa que se escribe.

### Helpers ya construidos — REUSAR, no reimplementar
- **`services/_empleado_scope.py`**
  - `ensure_empleado_de_empresa(repo, empleado_id, empresa_id)` → barrera de empresa sobre el empleado *target*. Devuelve la fila (no un bool) para que el caller la reuse en vez de consultarla dos veces.
  - `ensure_empleado_visible(repo, ownership_repo, empleado_id, empresa_id, user_id, rol)` → **empresa ∩ ownership**, en ese orden. Los dos fallos dan el mismo 404.
- **`services/_empleados_utils.py::empleado_or_404`** → el literal canónico del 404.
- **`services/_adjunto_padres.py::ensure_padre_de_empresa`** → molde para recursos polimórficos: valida el padre y **devuelve SU `empresa_id`** para etiquetar la hija.

### Ownership ≠ empresa (y solo aplica en dos secciones)
Son **dos ejes independientes que se componen por INTERSECCIÓN** — el ownership nunca reemplaza la empresa.
- **empresa** → frontera multiempresa. Aplica a TODO.
- **ownership** (`services/ownership.py`, `_ownership_filter.py`) → dentro de mi empresa, a qué empleados llego por mi rol. **Solo aplica en `VACACIONES` y `AUSENCIAS`** (`MANDOS_MEDIOS_SECCIONES`). En el resto de las secciones solo llegan `admin_rrhh` y `gerencia_lectura`, para quienes no restringe: **agregarlo ahí es código muerto que aparenta seguridad.** Por eso onboarding usa `ensure_empleado_de_empresa` y no `ensure_empleado_visible`.

### ⚠️ El router pasando `empresa_id` NO prueba nada
Hay que **seguir el parámetro hasta la query**. Un router que recibe `empresa_id` y lo pasa a un service que lo acepta y lo ignora se lee como seguro y no lo es. **Este falso positivo apareció 3 veces en el barrido de Fase 2** (offboarding, horas, onboarding_templates). Auditá de la query hacia arriba, no del router hacia abajo.

### 🚨 Fakes de test que HONRAN `empresa_id`
Un fake cuyo `find_by_id(id, empresa_id)` **acepta el parámetro y lo ignora** da **verde falso**: el test pasa sin validar nada, y es exactamente el bug que se quería cubrir.
- **Todo fake nuevo modela DOS empresas y devuelve `None` cuando `empresa_id` no coincide.**
- Si un fake es **permisivo a propósito** (porque el test cubre otro eje), **tiene que estar declarado en el docstring** del test. Ver `tests/test_assessment_vacantes_scope.py`, que lo dice explícito ("El fake HONRA empresa_id").

### `.single()` vs `maybe_single()`
**Usar `maybe_single()` salvo que la fila esté garantizada.** `.single()` **lanza** con 0 filas en vez de devolver `None` → el `return None` de abajo queda **inalcanzable** y el endpoint da **500 donde el service pretendía 404**. Pasó en `area_repo` y `empresa_repo`; ambos corregidos (el porqué quedó escrito en cada uno). Los `.single()` que sobreviven son legítimos: post-`upsert` (`nomina_repo`) y lookups de auth donde la fila existe por construcción.

---

## Audit log app-level (COMPLETO)
Captura **app-level** (no triggers DB). Tabla `auditoria` (mig 024+058): `id, tabla, registro_id, accion (INSERT|UPDATE|DELETE), datos_anteriores JSONB, datos_nuevos JSONB, usuario_id, ip, user_agent, created_at, empresa_id, entidad, evento`. Inmutable. Triggers DB viejos dropeados en 058.

`AuditService.registrar(...)` keyword-only, síncrono, **traga todo error** (no tumba la operación de negocio). `audit_repo` (insert + listar con filtros/paginación). Payloads canónicos en `services/_audit_payloads*.py`.

✅ **Auditoría de nómina silenciosa — ARREGLADA (Fase 0.1).** Antes `_audit_payloads_rrhh.py` pasaba el literal `"lote_nomina"` en `registro_id` (uuid) → insert fallaba → `AuditService.registrar` tragaba la excepción → evento perdido. Ahora usa `str(uuid4())` por llamada (id de EVENTO, no de recurso — nómina no persiste un lote con id, a diferencia de evaluaciones). Deuda futura: darle a nómina un lote persistido si se quiere trazar un import puntual. **Seguir usando `_audit_payloads_ev.py` como patrón de referencia.**

**UI:** `/auditoria` (admin/gerencia) + `components/ui/Pagination.tsx` (reutilizable). `auditoria.tabla` = `entidad` (espejo 1:1) — legacy, drop futuro sin traducción.

**Regla:** al auditar una importación → **un evento por lote**, nunca fila por fila.

---

## Importación CSV — molde para imports nuevos (COMPLETO)
Dedup por DNI. Dos flujos, ambos gateados `Seccion.IMPORTACION + WRITE` (solo admin_rrhh).

**Flujo 1 — Nómina de empleados** (single-shot, sin preview): `routers/importacion_nomina_empleados.py` → `nomina_empleados_service.py` + `_nomina_empleados_transforms.py`. CSV 27 col, `;`, `latin1`. Idempotente, no aborta ante error de fila, clasifica en 3 grupos.

**Flujo 2 — Nómina de costos** (preview + confirmar): `routers/importacion_nomina.py` → `nomina_csv_service.py::parse_nomina_csv` + `nomina_import_repo.py`. Resuelve DNI→empleado, detecta duplicados por `(anio, mes)`.
> **Este Flujo 2 es el molde de la base de import compartida.** Lo que falta agregar es el **reader XLSX** (hoy `openpyxl` solo se usa para export). Ver playbook Vacaciones/Ausencias.

---

## Evaluaciones de desempeño — resultados importados (COMPLETO, EN PRODUCCIÓN)

**Qué es:** `/evaluaciones` muestra **métricas de resultados calculados afuera**, importados por CSV. **El sistema NO evalúa.**

✅ **Migraciones 078 y 079 CORRIDAS en producción.** Verificado con datos reales: **1 lote (Julio 2026, empresa DOSUBA), 10 evaluados, 307 resultados, 0 equivalencias.**

### El modelo (078/079)
Las tablas `ev_*` no sirven para esto (ver más abajo por qué) y están **vacías en producción**. Las tablas nuevas:
- `evaluacion_lotes` — período, `UNIQUE(empresa_id, periodo)`. Columnas: `id, empresa_id, periodo, importado_por, created_at`.
- `evaluacion_evaluados` — uno por lote×persona, `empleado_id`/`nota_final` NULLABLE, `perfil` (lider|general) + datos crudos del CSV. FK `lote_id → evaluacion_lotes ON DELETE CASCADE`.
- `evaluacion_resultados` — uno por evaluado×tipo×competencia. FK `evaluado_id → evaluacion_evaluados ON DELETE CASCADE`.
- `evaluacion_equivalencias` (079) — texto del CSV = empleado, confirmado a mano. **Cuelga de `empresa_id`, NO de `lote_id` → NO cascadea.** Sobrevive al borrado del lote (mapeo aprendido, se reaplica en el próximo import).

Las hijas **no llevan `empresa_id`** — se alcanza por `lote_id`. **Invariante: el matcheo resuelve el empleado SIEMPRE dentro de la empresa del lote, nunca global.** `competencia` va como texto, no catálogo.

**Por qué no se reusó `ev_*`:** `ev_instancias` tiene `UNIQUE(ciclo_id, empleado_id)` pero el dato real son hasta 6 filas por evaluado (una por tipo de evaluador); `evaluador_id` es FK a persona, el CSV trae un tipo (`AUTOEVALUACION`/`PAR`/…) sin identidad; `puntaje_global` se calcula, acá viene calculado de afuera. UI de `ev_*` borrada; tablas se limpian tras el cutover a AWS.

### El formato (no cambia — nos adaptamos)
Dos CSV `;`, **encoding distinto entre sí** (notas UTF-16, desglose UTF-8), números con espacios adelante. A·Notas finales: 8 col, una fila por evaluado. B·Desglose: 7 de identidad + `TIPO EVALUACION` + 15 competencias. **No traen DNI ni legajo, solo apellido y nombre.** El lector detecta BOM explícito y falla claro si no puede determinar encoding (el decode viejo caía a `latin-1` y decodificaba UTF-16 a basura en silencio).

**Dos perfiles:** líder (14 competencias) y general (9). El perfil se deriva de las 5 competencias exclusivas de líder presentes en el archivo (`VISION ESTRATEGICA`, `ORGANIZACION`, `CONDUCCION EQUIPOS`, `PLANIFICACION`, `COMUNICACION`) — **NO de `es_lider`** (está 0/19).

### Matcheo
Apellido+nombre normalizado (sin acentos), desempatado por superior contra `manager_id`. Estados: `resuelto` · `ambiguo` (revisión humana) · `sin_candidato` (`empleado_id=null`, válido, no error). **Nada de fuzzy por similitud.**
🚨 **`manager_id` está 0/19 en producción** → el desempate no discrimina hoy, todo cae en "resuelto". Degrada bien, se activa cuando carguen jerarquía. **Excede evaluaciones: el ownership de mandos_medios depende de esto.** Colisiones actuales: 0, pero hay 2 apellidos repetidos (unicidad circunstancial).

### Pipeline
`preview` (parsea+resuelve, **no persiste**, avisa si pisa período) → revisión humana → `confirmar` (**no re-parsea**: persiste lo aprobado, pisa el período previo vía `delete_lote`+CASCADE, un evento de auditoría por lote).

✅ **Bug de `confirmar()` — pérdida de datos, ARREGLADO (Fase 0.2).** Antes borraba el lote previo antes de crear el nuevo, sin transacción → un reimport fallido perdía ambos. Ahora el orden es: crear lote nuevo con período TEMPORAL (`"{periodo} ::importando::"`, no choca la UNIQUE) → persistir evaluados+resultados → **verificación POR CONTEO** (`len(guardados)==esperados`; un insert parcial silencioso se detecta acá, no basta "no hubo excepción") → borrar el viejo (único paso destructivo, al final) → renombrar el nuevo al período real. Si algo falla antes del borrado, el viejo queda intacto y el temporal se limpia best-effort. `crear_evaluados`/`crear_resultados` ahora levantan `AppError` si el insert no devuelve todas las filas (antes devolvían `[]` en silencio). La única ventana restante (fallo entre borrar-viejo y renombrar) deja el nuevo completo con nombre temporal → recuperable a mano, logueado a ERROR, no es pérdida.

### Métricas
Agregados en Python puro (`_evaluacion_metricas.py`), no SQL (~300 filas por lote no justifica vistas/RPC). ⚠️ Competencias en DOS tablas separadas (líder/general), cada una con su `n` — **nunca en el mismo ranking** (son 2 evaluaciones distintas, mezclarlas da resultado falso). Excluyen autoevaluaciones. La métrica más valiosa: **brecha de autopercepción** (auto vs promedio de terceros).

### Historial de importaciones (COMPLETO — última entrega)
Tab **"Importaciones"** en `/evaluaciones` con lista de todos los lotes, multi-selección y borrado. Backend + front.

**Backend:**
- `GET /lotes` en modo consolidado (`X-Empresa-Id` ausente/None) devuelve **todos los lotes de todas las empresas**. Enriquecido vía `repositories/_evaluacion_lotes_enrich.py` con `empresa_nombre`, `importado_por_nombre` (null si no hay), `evaluados` (conteo). **Sin N+1**: un lookup batch por dimensión (empresas, users, conteo con GROUP BY), no una query por fila.
- `delete_lote(lote_id, usuario_id)` — **desacoplado de la empresa activa**: valida contra `lote.empresa_id` (autoritativo, ya cargado), no contra el header. El gate WRITE del router (= admin_rrhh) es la única barrera. Audita `baja_lote_evaluaciones` con snapshot (`periodo` + `evaluados`) **antes** del CASCADE (después no se reconstruye).
- `POST /api/evaluaciones/resultados/lotes/eliminar` (bulk) — recibe `{lote_ids}`, devuelve `{eliminados, fallidos:[{id,motivo}]}`, éxito parcial clasificado (patrón `proyectos.asignar_bulk`), no aborta. Un evento de auditoría por baja efectiva.
- El router `evaluaciones_resultados.py` tiene gate READ por default → el DELETE y el bulk necesitan dependency WRITE inline propia.

**Frontend:**
- Tab "Importaciones" (solo `canWrite`). Componentes en `components/features/evaluaciones/`: `HistorialImportaciones.tsx` (orquestador, estados carga/vacío/error/datos) + `HistorialTable.tsx` (presentacional, desktop=tabla / mobile=cards). Hook `useHistorialImportaciones.ts` (carga consolidada + `eliminar(ids)` que normaliza single→DELETE y varios→bulk a un `LotesBulkResult` uniforme).
- **El borrado NO depende del selector de empresa del sidebar.** Usa `fetchLotesHistorial()` que fuerza `X-Empresa-Id: "todas"`. Multi-selección con checkboxes + "seleccionar todo", barra de acción con ≥1 seleccionado, ConfirmDialog destructivo, toast de éxito con conteo y de error listando fallidos.

⚠️ **`EliminarLoteButton.tsx` quedó huérfano** (código muerto, 0 callers) tras mover el borrado al historial. Su vieja guarda `disabled={!empresaActivaId}` era la que trababa el botón cuando el sidebar estaba en "Todas las empresas". Candidato a borrar junto con el dead code.

✅ **Fuga entre empresas — CERRADA (Fase 2, commit `bd95e98`).** Los 7 endpoints del módulo que reciben `lote_id` (incluidos `/metricas`, `/evaluados`, `/export` y `/ficha`) validan por **ownership del lote**: la empresa sale de `lote.empresa_id`, que es autoritativo, no del header. Mismo 404 para "no existe" y "es de otra empresa". Ver "Patrón de barrera de empresa".

### Entrega 2 — descarga de archivos originales (PENDIENTE, feature nueva)
Poder **volver a descargar los CSV originales** de cada importación. Hoy **no se puede**: el import parsea y descarta los bytes (cero `storage.upload`, `evaluacion_lotes` sin columna de ruta). Requiere: (1) guardar los dos CSV en Storage al confirmar (reusar patrón `adjunto_service` / bucket existente), (2) migración con columna(s) de ruta, (3) endpoint de descarga con `create_signed_url`. La infra de Storage ya existe (usada por 5 módulos: adjuntos, cvs, candidatos, certificados, logos).
🚩 **Solo hacia adelante.** El lote Julio 2026 ya existe sin archivos guardados — no se recupera. La descarga funciona solo para importaciones futuras. Confirmar con RRHH que el lote viejo se puede perder.

---

## Reportes y KPIs (COMPLETO — Fase 1, en producción)

Catálogo de reportes descargables (PDF/Excel) + KPIs de dashboard. Construido en 6 sesiones.

### 🔑 PRINCIPIO — Vista vs Acción (evita la confusión recurrente del selector de empresa)
- **El selector de empresa del SIDEBAR es SOLO VISUAL.** Filtra lo que se MIRA (listados, dashboard). NO gobierna acciones.
- **Las ACCIONES reciben la empresa como PARÁMETRO EXPLÍCITO** (del formulario/body), nunca del header `X-Empresa-Id`. Ejemplos: generar un reporte (empresa del form), borrar un lote de evaluaciones (empresa del lote).
- Regla mental: **mirar = sidebar manda · hacer = el form/parámetro manda.**
- Casos concretos: **Reportes = ACCIÓN** → empresa+área salen del form, ignora el sidebar (sin empresa elegida = todas las empresas, consolidado). **Dashboard = VISTA** → respeta el sidebar. Son opuestos a propósito; no contagiar un patrón al otro.

### Reportes construidos (11)
Dotación: headcount, altas/bajas (con listado nominal), distribución por seniority/modalidad/turno (nulos → "Sin especificar"), rotación por motivo.
Vac/aus: listado combinado, ausentismo por área (total + injustificado, tasa sobre 22 días hábiles con nota visible), saldos de vacaciones (asignados − tomados con `cancelada=false`; solo `tipo="vacaciones"` resta saldo; saldo negativo → flag `excedido`, no se oculta).
Costos/otros: masa salarial, presupuesto vs real (desvío + % ejecución), capacitación por área (desde `empleado_capacitacion`, filtra por `fecha_asignacion`), auditoría/trazabilidad (resumen legible, NO vuelca el JSONB crudo, usuario por nombre).

Todos: filtro período + empresa + área (empresa/área del FORM). El área se filtra por join a empleados donde la tabla no tiene `area_id` (costos, rotación, onboarding). `anual_consolidado` no lleva área (transversal por diseño). El motor `build_export` es genérico — producir el dict `datos` y llamarlo.

### KPIs de dashboard (9: 4 previos + 5 nuevos)
Nuevos: ausencias activas hoy, % ausentismo del mes (base 22 días, nota visible), masa salarial + variación vs mes anterior, distribución por seniority/modalidad, cumpleaños/aniversarios del mes. El dashboard RESPETA el sidebar de empresa (es vista).

### Estructura
- `services/reportes/` — un submódulo por familia (`_reporte_dotacion`, `_reporte_costos`, `_reporte_movimientos`, `_reporte_seleccion`, `_reporte_vacaciones`, `_reporte_ausentismo`, `_reporte_capacitacion`, `_reporte_auditoria`) + `reporte_generators.py` como dispatcher/re-export (18 líneas). `_common.py` para lo compartido, evita el ciclo dispatcher↔submódulos.
- `services/_kpi_helpers.py` / `_dashboard_kpis.py` — **cálculos compartidos entre KPIs y reportes** (base 22 días, distribución con "Sin especificar"). Un solo lugar, no duplicar.
- Front: `components/features/reportes/` (catálogo + card + selectores empresa/área) y `components/features/dashboard/` (tarjetas divididas).
- El reporte adhoc con IA (`reporte_adhoc.py`, modelo `claude-sonnet-4-6`) está OCULTO del catálogo (no borrado — patrón AIPanel). El endpoint existe; solo se sacó el punto de entrada del front. Reactivable en una línea.

### 🚨 Dashboard resiliente (fail-safe por KPI)
`dashboard_service` calcula cada KPI/sección con un `_safe`: si UNO falla, los demás se devuelven igual y el fallido queda vacío + marcado en `errores`. NUNCA propaga (antes un KPI roto tiraba 200→500 el dashboard entero). Al agregar un KPI nuevo, respetá este patrón.

### 🔴 APRENDIZAJE CRÍTICO — los tests NO detectan errores de embed de PostgREST
El fake de Supabase de los tests NO replica la resolución de FKs del PostgREST real. Un `select` con embed anidado (`empleados(areas(...))`) puede pasar los 510 tests y explotar en el primer request real con **PGRST201 (300 Multiple Choices)** si la tabla tiene MÁS DE UNA FK al target (ej: `costos_nomina` tiene 2 FKs a `empleados`). **Regla: toda query con embed es un punto ciego de los tests → verificar manualmente en producción después de cada deploy que toque queries con relaciones anidadas.** Fix: nombrar la FK explícita → `empleados!costos_nomina_empleado_id_fkey(...)`. (Hermano del aprendizaje ya conocido de self-join embedding.)

---

## 📋 PLAYBOOK — Filtros + export en Vacaciones y Ausencias (PENDIENTE, bloqueado por Excel de RRHH)

El trabajo hecho en evaluaciones (historial + multi-selección + borrado desacoplado + auditoría) **es el molde** para lo que hay que hacer en Vacaciones y Ausencias cuando lleguen los Excel reales de RRHH. Anotado para no re-diagnosticar.

**Objetivo:** que RRHH obtenga cualquier corte de información con el máximo detalle, sin pedirle nada a desarrollo. En cada módulo: todos los filtros posibles en la UI (empresa, área, empleado, estado, tipo, fechas) + **el export sale siempre con los filtros aplicados** (lo que se ve es lo que sale).

**Estado del terreno (REMEDIDO 27/7/2026 — el filtro de empleado YA ESTÁ, en los dos módulos):**
- ✅ **Vacaciones · filtro empleado**: completo end-to-end — `useFiltrosVacaciones` (hook con `empleadoFiltro` + `campos`) → `vacaciones/page.tsx` → `fetchVacaciones`/`exportarVacaciones` → router (`empleado_id` como `Query`) → `vacaciones_service.get_all/exportar` → repo. Filtros vivos: empresa · área · empleado · estado.
- ✅ **Ausencias · filtro empleado**: también completo (`ausencias_service.get_all` **sí** lo acepta; el doc decía lo contrario). Filtros vivos: empresa · área · empleado · tipo.
- ✅ **Invariante del export cumplida**: los dos endpoints de `exportar` aceptan los mismos `Query` que su `list`.
- ⚠️ **`vacaciones/page.tsx` (148) y `ausencias/page.tsx` (141)** siguen dentro del límite pero con poquísimo margen. Sumar UN filtro más exige extraer la barra a componente propio primero.
- 🔴 **Antes de tocar estos servicios, arreglar los posicionales de `services/vacaciones.ts` / `ausencias.ts`** (ver Deuda técnica): hoy los call sites están bien, pero el próximo filtro que se agregue en el medio desplaza todo en silencio.
- Todo filtro nuevo se **compone POR INTERSECCIÓN con el ownership** (`_ownership_filter.resolver_filtro_empleados`), nunca lo reemplaza.

**Lo que queda pendiente de este playbook es SOLO el import** (bloqueado por los Excel de RRHH), no los filtros.

**Import de vacaciones/ausencias (bloqueado hasta tener los Excel):**
- NO existe camino de import Excel. El único import es CSV (`csv.DictReader`, los dos flujos de nómina). `openpyxl` solo en export.
- Esto NO son "dos features chicas": es **una base de import compartida** (reader XLSX + flujo preview/confirmar genérico, moldeado sobre `nomina_csv_service` Flujo 2) + dos consumidores.
- **Sin los archivos reales de ejemplo no se define el parser.** Pedir a RRHH: Excel de vacaciones y Excel de ausencias.
- Aplicar el patrón de evaluaciones: preview (no persiste) → revisión → confirmar (persiste, audita un evento por lote), y prever el **historial de importaciones con borrado** desde el día 1 (evita el rework que tuvimos en evaluaciones).

**Patrón de éxito parcial** (para el import por filas): clasificar OK / con faltantes / no cargadas, no abortar ante error de fila (como los dos flujos de nómina y el bulk de proyectos/evaluaciones).

---

## Patrón de página de listado (COPIAR para listados nuevos o divisiones)
```
app/(dashboard)/<modulo>/page.tsx        ← orquestador delgado (<150)
  estado page/total + modales + load + handlers CRUD + render
components/features/<modulo>/<Modulo>Table.tsx   ← presentacional (loading/error/empty)
components/features/<modulo>/useFiltros<Modulo>.ts ← estado de filtros + opciones + array de FiltroCampo
```
El hook recibe `onFiltroChange` que la página cablea a `() => setPage(1)` (reset de paginación sin acoplar `page` al hook).

**Precedente de división grande — `components/features/sucesion/` (Fase 3):** `sucesion/page.tsx` pasó de **855 a 85** calcando el corte de `reportes/page.tsx`. Quedó en 8 componentes (`MapaTalentoTab`, `PlanesTab`, `NineBox`, `AnalisisAreaModal`, `NuevoPlanModal`, `PlanDetallePanel`, `NuevoHitoForm`, `HitosList`) + 2 hooks (`useSucesionData`, `usePlanDetalle`) + `_sucesion_ui.ts` para los helpers de presentación. **Copiar este corte para las páginas de 400+ que quedan** (`costos/page.tsx` 618, `vacantes/[id]/page.tsx` 577).

**Paginación:** front manda `page`/`page_size` · usar `Pagination.tsx` (no escribir paginación nueva) · el pager aparece solo si `total > pageSize` · **`page` se resetea a 1 al cambiar cualquier filtro** · **el export NO se pagina.**

**Export estandarizado:** `services/_<modulo>_export.py::construir_filas_export(items)` proyecta columnas legibles sin UUIDs (nombres resueltos, fechas dd/mm/aaaa, booleanos Sí/No). El motor genérico (`services/export/`, `build_export`) NO se toca. Front: `services/api.ts::descargarArchivo` acepta `params?` opcional (filtra vacíos, mergea con `formato`) — usarlo, no duplicar fetch+blob. **Invariante: el endpoint de export acepta los mismos Query que el list.**

**Ownership:** `services/ownership.py` (`ids_empleados_visibles`) y `_ownership_filter.py` (`resolver_filtro_empleados`, ownership ∩ área). **Reusar, no reimplementar.** Todo filtro nuevo se compone por intersección.

**Precedente más rico del repo — Auditoría:** 5 controles UI → 8 params → router con 7 Query → repo aplica todos con `.eq/.gte/.lte` + count exacto. Molde de la `FiltersBar` genérica.

**`components/ui/FiltersBar.tsx`** (52 líneas): presentacional, controlado, 3 tipos (select/search/date), labels visibles. No fetchea, no debouncea, no tiene estado propio. Ahorra ~12 líneas por página (no sirve para destrabar divisiones, sí para consistencia).

---

## Otros módulos (referencia rápida)
- **Vacantes + Candidatos:** `routers/vacantes.py` + `candidatos.py` (+ `_candidato_form.py` público sin auth), `vacante_service.py`, `candidato_service.py`, `cv_service.py`. Integraciones: `zernio_service.py`, `gmail_service.py`. **Vacantes es el patrón canónico de borrado con confirmación** (router DELETE + service con snapshot-antes-de-borrar + `services/vacantes.ts` fetch crudo por el 204 + `EliminarVacanteButton.tsx` + `ConfirmDialog`). Copiar de acá.
- **Cesiones** (mig 066): hija de empleado, en la ficha. Gateada por `Seccion.EMPLEADOS`.
- **Proyectos:** asignación single (`proyecto_asignaciones.py`) + bulk multi-selección (`POST /{id}/asignaciones/bulk`, éxito parcial clasificado). **El área filtra candidatos, NO asigna.** Descartado: asignar área completa en bloque.
- **ABM usuarios:** solo admin_rrhh. `POST /api/usuarios` (alta + contraseña temporal una sola vez, `must_change_password=true`) · `DELETE` (auto-eliminación bloqueada) · `POST /cambiar-password` (self-service). Migración 063. **Para crear usuarios directo en DB** (sin flujo de cambio de contraseña): crear auth user en dashboard Supabase con Auto Confirm, copiar el UUID, INSERT en `public.users` (hay FK `users.id → auth.users(id)`, sin fila en auth.users el INSERT falla). Roles válidos: `admin_rrhh`, `gerencia_lectura`, `mandos_medios`. `must_change_password=false` para saltear el cambio forzado.
- **Ownership mandos_medios:** `services/ownership.py` app-level. "A cargo" = `manager_id`, no área ni `es_lider`. Aplicado en las 13 superficies de Vacaciones y Ausencias (listados, export, escrituras). Falta RLS a nivel DB (en AWS no va — queda app-level definitivo).
- **Adjuntos (polimórficos, cuelgan de `entidad` + `entidad_id`):** la empresa del adjunto sale de la **entidad PADRE, no del header** — aplicación directa del principio Vista vs Acción. `services/_adjunto_padres.py::ensure_padre_de_empresa` valida que el padre exista y sea de tu empresa, y devuelve **su** `empresa_id` para etiquetar la hija (antes se podía colgar un archivo del legajo de un empleado ajeno, y quedaba etiquetado con TU empresa, así que su dueño real ni lo veía). Resolvers para las 5 entidades que el front usa: `empleado`, `vacacion`, `ausencia`, `vacante`, `offboarding`. Los adjuntos con **`empresa_id` NULL (filas legacy) están bloqueados en TODOS los modos**, incluido el consolidado. ⚠️ `entidad_tipo` **`"evaluacion"` queda fail-closed con `ENTIDAD_INVALIDA` (400)**: está mapeado a una Sección pero **no tiene repo resolver** (no se definió a qué apunta: ¿lote?, ¿evaluado?, ¿instancia `ev_*`?) y tiene **0 callers** en backend y front. Definir antes de habilitarlo.

---

## Staging de migración a AWS (`migracionAWS/`)
Carpeta **aislada** para migración de Supabase a **AWS (asyncpg/RDS + S3)**. Código nuevo sin tocar `backend/` en producción. Contiene `*_NEW.py` (auth completo, `postgres_client.py` asyncpg, repos-molde `empleado_repo_NEW`) + migraciones 075 (password_hash), 076 (refresh_tokens), 077 (recrear 36 triggers `updated_at`) + docs (`MIGRACION_A_RDS.md`, `README_AUTH.md`). El otro dev ejecuta la infra.

**Decisiones cerradas:** se recrean los triggers · **NO hay RLS** (seguridad app-level) · no se carga demo data.

**Minas ya desactivadas (para el otro dev):**
- asyncpg devuelve UUID nativos → cast `str()` explícito en mappers.
- FK `users.id → auth.users(id)` bloquea INSERT sin Supabase → dropear + `DEFAULT gen_random_uuid()`.
- El `ON DELETE CASCADE` contra `auth.users` es lógica de negocio viva.
- `passlib` roto (bcrypt 5.0 sacó `__about__`) → usar `import bcrypt` directo.
- `schema.sql` no trae los 36 triggers `updated_at`.
- **Modelo Anthropic**: verificar que ningún string con fecha (`claude-sonnet-4-20250514`, retirado) sobreviva. Usar alias sin fecha (`claude-sonnet-4-6`). El front tenía este bug (chat caído en prod desde el 15/6); ya corregido.

**Contraste con changelog de KarIA Reach (otro proyecto, mismo stack asyncpg/ECS/SSM) — verificado, aplica a RRHH:**
- Secretos en producción → **SSM Parameter Store / Secrets Manager, NUNCA hardcodeado**. URL-encodear caracteres especiales del password en la DSN (evita el bug de secreto truncado que a KarIA le costó días). Ya documentado en `MIGRACION_A_RDS.md` / `settings_ADD.md`. `migracionAWS/` está limpio: sin secretos ni placeholders pegados.
- asyncpg contra RDS: `postgres_client.py` usa `ssl="require"` ✅ y `command_timeout=30` ✅, host desde `database_url` (env, no hardcodeado). **Faltan (decisión de infra, no bug):** timeout de conexión explícito (default 60s cuelga el arranque si RDS es inalcanzable); `verify-full` en vez de `require` (require no verifica CA, abierto a MITM dentro de la VPC); si el DNS de RDS falla, poner IP privada en `database_url`.

---

## ⚠️ Build de producción y estilo de código — LEER ANTES DE TOCAR

### El repo NO está formateado con ruff, pese a su config
`ruff.toml` declara `line-length=100` + `[format]`, pero el código está en **estilo compacto de línea larga** (firmas de una línea >100 chars). Los límites documentados se midieron sobre ese estilo. **Correr `ruff format` reflowea archivos enteros** (en una prueba: `ausencias_service.py` 149→253). **NO correr `ruff format` dentro de una sesión de feature/bugfix.** Adoptar ruff repo-wide es tarea propia con re-medición de límites. ⚠️ Confirmar si `pre-commit` está instalado (los hooks de `.pre-commit-config.yaml` explotarían en el primer commit) — mina para la migración AWS.

### `tsc` en 0 y `next build` verde
`next dev` con Turbopack transpila sin type-check → errores de tipo pasan desapercibidos pero **`next build` falla**. `vitest` ya existe (18 tests) pero cubre solo permisos y query params de empleados, así que para casi todo el front **`tsc` sigue siendo la única red**. **Regla: `node_modules/.bin/tsc --noEmit` tiene que dar 0. Si aparece un error, es tuyo.**

### 🚨 Módulo assessment desactivado — NO convertir el `useState` en `const`
`app/(dashboard)/assessment/[id]/page.tsx` está desactivado a propósito (redirige a `/dashboard`). El gate es `const [moduloActivo] = useState(false)` con el setter descartado. **Tiene que ser `useState`, NO `const`:** TS colapsa un `const` a literal `false`, marca el cuerpo inalcanzable, pierde el narrowing y **`next build` falla**. Hay un comentario explicándolo. No borrarlo, no "simplificar".

---

## Deuda técnica conocida

### Bugs / riesgos activos
- ✅ **Fuga entre empresas — CERRADA (Fase 2).** 92/92 endpoints aplicables con barrera de empresa + 13/13 superficies de vacaciones/ausencias con ownership; 8 endpoints NO APLICA con razón documentada. Ver "Patrón de barrera de empresa" (regla permanente) y FOCO ACTUAL (desglose de los 8).
- ✅ **`confirmar()` de evaluaciones — RESUELTO (Fase 0.2).** Período temporal + verificación por conteo. Ver sección evaluaciones.
- ✅ **Auditoría de nómina silenciosa — RESUELTA (Fase 0.1).** uuid4 de evento. Ver sección audit log.
- ✅ **N+1 de sucesión — RESUELTO (Fase 3, commit `51832e2`).** `get_analisis_posicion` hacía una query de `assessment_resultados` por empleado. Ahora `repositories/sucesion_repo.py::_scores_por_empleado(ids)` trae todo en **UNA** query con `.in_("empleado_id", ids)` y resuelve el "más reciente" en Python: con 200 empleados pasó de **201 requests a 2**. Guarda con la lista vacía (nunca dispara la query sin ids) y no asume orden dentro del `in_`.
- ✅ **`manager_id` — capacidad de edición RESUELTA (Fase 0.3):** se puede asignar/desasignar superior desde la ficha, con anti-ciclos server-side (auto-referencia, ciclo directo/indirecto, tope 50 saltos). ⚠️ PERO **sigue 0/19 poblado** — la capacidad existe, los datos no. Hasta que RRHH cargue jerarquía, `mandos_medios` no ve nada y el desempate de matcheo de evaluaciones no discrimina.
- ✅ **`fetchEmpleados` — RESUELTO (Fase 3).** `fetchEmpleados` y `exportarEmpleados` toman un **objeto de opciones** sobre la interfaz compartida `EmpleadosFiltros`; 10 call sites migrados y auditados uno por uno. Contrato HTTP intacto.
- 🔴 **`services/vacaciones.ts` y `services/ausencias.ts` — MISMA TRAMPA, y peor.** Todos los filtros son `string | undefined` posicionales, y **las hermanas están CORRIDAS una posición entre sí** porque el export lleva `formato` adelante:
  - `fetchVacaciones(empresaId?, areaId?, empleadoId?, estado?, page, pageSize)` vs `exportarVacaciones(formato, empresaId?, areaId?, empleadoId?, estado?)`
  - `fetchAusencias(empresaId?, areaId?, tipoId?, empleadoId?, page, pageSize)` vs `exportarAusencias(formato, empresaId?, areaId?, tipoId?, empleadoId?)`
  Copiar los filtros de una a la otra **desplaza todo un lugar y `tsc` lo acepta** (mismo tipo). Peor: entre módulos las posiciones 3 y 4 **no coinciden** (`empleadoId`/`estado` en vacaciones vs `tipoId`/`empleadoId` en ausencias). Mismo fix que empleados: objeto de opciones con interfaz compartida. **Encaja en el playbook de filtros de Vacaciones/Ausencias — hacerlo ANTES de sumar filtros nuevos, no después.**
- **Filtros duplicados front+back** (patrón recurrente): si un filtro afecta el export, va **server-side, una sola implementación**. Casos: `aplicar_filtro_estado` es espejo de `derive_estado` (merece test que las compare); listado de evaluaciones filtra client-side, exporta server-side (aceptable a ~30 filas, el endpoint ya acepta los filtros).
- **`page_size=100000` en export** — corte silencioso si una empresa lo supera.
- **`middleware/auth.py`** acepta cualquier UUID con formato válido como `X-Empresa-Id` sin verificar que exista. Baja prioridad.
- **`permisos.ts` es espejo manual de `permisos.py`** — riesgo de divergencia.

### Líneas (archivos over-limit, límite front 150 / back según tipo)
> **Remedido contra el código el 27/7/2026.** Ya NO están over-limit: `sucesion/page.tsx` (855 → **85**, Fase 3), `reportes/page.tsx` (era 539) y `reporte_generators.py` (era 249, ambos Fase 1), `empleado_service.py` (143 → **89**) y `ausencias_service.py` (149 → **74**, ambos Fase 2 por extracción).
> ⚠️ `PlantillasTab.tsx` (336), `CiclosTab.tsx` (297) y `EvaluacionesTab.tsx` (286) **ya no existen en el repo** — se fueron con la UI de `ev_*`. Estaban listados acá por arrastre.

**Frontend (38 archivos > 150):** `costos/page.tsx` 618 · `vacantes/[id]/page.tsx` 577 · `onboarding/templates/[id]/page.tsx` 412 · `onboarding/page.tsx` 410 · `configuracion/page.tsx` 390 · `ImportarNominaCSVModal.tsx` 377 · `offboarding/page.tsx` 292 · `onboarding/templates/page.tsx` 290 · `NominaModal.tsx` 287 · `areas/page.tsx` 261 · `evaluacion/[token]/page.tsx` 258 · `VacanteModal.tsx` 251 · `AIPanel.tsx` 249 · `assessment/page.tsx` 233 · `empresas/[id]/page.tsx` 230 + **23 más entre 152 y 226**.
> Dos de los 38 son primitivos generados de **shadcn/ui**, no código nuestro: `components/ui/dropdown-menu.tsx` 268 y `components/ui/dialog.tsx` 160. No cuentan como deuda.

**Backend over-limit:** services `integracion_service` 201 · `_audit_payloads_rrhh` 189 · `reporte_anual` 154. Repos `empleado_repo.py` 174 · `ev_instancias_repo` 146 · `ev_plantillas_repo` 129 · `nomina_repo` 107 · `proyectos_repo` 104. **Routers: ninguno over-limit** (el máximo es 80/80).
> `costo_repo` 135 y `assessment_repo` 130 siguen siendo **legacy con CERO callers** (verificado: el string `costo_repo`/`CostoRepo` no aparece en ningún `.py` fuera del propio archivo; `costo_service` usa `nomina_repo`/`periodo_repo`/`presupuesto_repo`). Candidatos a borrar, junto con `EliminarLoteButton.tsx` (74, 0 callers).

**En/al límite EXACTO (el próximo cambio EXIGE dividir primero):**
- **Services 150/150:** `vacaciones_service.py` · `gmail_service.py` · `costo_service.py` · `assessment_service.py`. A 149: `vacante_service.py` · `usuario_service.py` · `adjunto_service.py`.
- **Repos 100/100:** `onboarding_repo.py` · `evaluacion_repo.py`.
- **Routers 80/80:** `vacantes.py` · `evaluaciones_resultados.py` · `adjuntos.py`. A 79: `objetivos.py` · `inventario_items.py`.

**Cortes ya identificados (para no re-diagnosticar cuando toque dividir):**
- `vacaciones_service.py` → extraer `create` a **`_vacaciones_write.py`**, simétrico con el `_ausencias_write.py` que ya existe (110).
- `gmail_service.py` → extraer el parseo a **`_gmail_parseo.py`**.

### Al margen por decisión (NO tocar)
- **S6 / DROP de `cargo` y `rol`** → no se borra nada (decisión de producto). Fallbacks `roles[0] ?? cargo` quedan.
- **Campo `equipo`** (texto libre): sin tabla `equipos`, "asignar/importar por equipo" no existe.
- **Import de objetivos**: bloqueado por modelo (objetivos cuelgan de `users` vía `responsable_id`, no de empleado).
- **Tablas huérfanas** (`assessment_reportes`, `configuracion_empresa`, `documentos_empleado`, `notificaciones`, `notificaciones_config`, `sucesion_posiciones`): se limpian **después del cutover a AWS** (dropear = migración nueva + regenerar `schema.sql` en plena migración).
- **"Compatibilidad con una posición"** (sucesión): feature nunca construida, no deuda técnica. El ranking es por assessment genérico, sin relación con posición. Cuando RRHH la reclame, definir qué significa compatibilidad antes de improvisar.

### Tests
- **Front: `vitest` configurado y corriendo — `npm test` (= `vitest run`), 18 tests en 2 archivos** (`hooks/useCanWrite.test.ts` 10 · `services/empleados.test.ts` 8). Ya NO es cierto que `tsc` sea la única red, pero la cobertura sigue siendo mínima: **solo permisos y query params de empleados**. Todo lo demás del front sigue sin test.
- Adjuntos: 11 tests unit con `_FakeRepo` + storage monkeypatcheado. **E2E real nunca se ejecutó** (no hay bucket no-productivo; `_BUCKET="documentos"` hardcodeado apunta a prod). Decisión: E2E automatizado en el cutover a AWS/S3.
- Suite backend: **510 passed** (47 archivos de test).
- 🚨 **Los fakes tienen que honrar `empresa_id`** — un fake permisivo da verde falso. Ver la regla completa en "Patrón de barrera de empresa".
- ⚠️ **Los tests con el fake de Supabase NO detectan errores de embed de PostgREST** (resolución de FKs). Toda query con `select` anidado es punto ciego → verificar en producción tras deploy. Ver aprendizaje en sección Reportes.

### En pausa
- **Link público de carga de horas** — mockup HTML aprobado, esperando RRHH.
- **Limpieza general del repo** (código muerto, duplicación): 5–8 sesiones, no urgente. Candidato principal: filtro `empresa` duplicado 8× en 29 repos.

---

## Git
- Operar siempre desde la raíz del repo, `RRHH/`.
- **Commits los hace Franco manualmente** (nunca Claude Code). Commits y push desacoplados: no hay push hasta que Franco lo decida. Preferir commits por sub-sesión.
- Formato convencional (`feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `test:`).
- Solo `main` y `origin/main`. Sin ramas sueltas.
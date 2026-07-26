# CLAUDE.md — Sofia (HR Karstec)

> **Ubicación:** raíz del repo Sofia (`RRHH/Sofia/`), desde donde se ejecuta `claude`. Sofia tiene su propio `.git` dentro del mono-repo RRHH — **todas las operaciones git corren desde `RRHH/Sofia/`, nunca desde `RRHH/`**.

## Documentos de planificación (leer al inicio)
La dirección del producto y el schema están en estos documentos. **Tienen prioridad sobre la memoria.**
- @docs/MODELO_DATOS.md — **fuente de verdad del schema** (si algo contradice una tabla, manda este doc)
- @docs/PLAN_DESARROLLO_AHORA.md — qué construimos ahora
- @docs/PLAN_DESARROLLO_DESPUES.md — qué construimos después

Documentos de la agencia (convenciones obligatorias): ORDEN-Y-LEGIBILIDAD.md · SEGURIDAD-PENTEST.md · BASES-DE-DESARROLLO.md · UX-UI.md.

---

## Qué es este proyecto
Sofia es el repositorio interno de **HR Karstec**: plataforma de gestión del ciclo de vida del empleado, **multiempresa** (2–5 empresas simultáneas), operada por un equipo de RRHH de 3 personas. Reporting con IA vía Claude Sonnet. **Live en https://www.hrkarstec.site**.

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

**Deploy resuelto, evaluaciones en producción.** Lo que sigue en orden:

1. **Segunda usuaria de RRHH** — crear el auth user (dashboard Supabase → Add user → Auto Confirm) + INSERT en `public.users` (rol `admin_rrhh`). Ver "ABM de usuarios".
2. **`manager_id` vacío (0/19)** — avisar a RRHH. Rompe el ownership de `mandos_medios`: hoy ningún mando ve a su gente en vacaciones/ausencias. No depende del deploy.
3. **Reportes y KPIs** — catálogo definido por RRHH (18 reportes + 12 KPIs). Diagnóstico read-only pendiente de correr para mapear qué existe / qué falta. Candidatos a dato faltante ya detectados: rotación por motivo (falta motivo de egreso), saldos de vacaciones (falta días disponibles), cumpleaños/aniversarios (falta fecha nacimiento/ingreso).
4. **Filtros + export en Vacaciones y Ausencias** — bloqueado por los Excel de RRHH. Ver playbook abajo.
5. **Descarga de archivos originales de importaciones** (Entrega 2 de evaluaciones) — feature nueva con migración; ver sección evaluaciones.

**Pendientes de RRHH (bloqueantes de datos):**
- Excel reales de vacaciones y ausencias (sin ellos no se define el parser de import).
- Evaluaciones: ¿pueden exportar DNI o legajo? · los 2 líderes sin nota final · qué es "Kolektor" (empresa del grupo o error de carga).

---

## Estructura (backend)
```
backend/
├── main.py              ← entrada, registro de routers, middleware
├── config/settings.py   ← única fuente de config y env (Settings() se instancia en import)
├── routers/             ← endpoints, sin lógica (límite 80 líneas)
├── services/            ← lógica de negocio (límite 150)
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
14. **Cada repo nuevo es un repo más a portar a asyncpg** (hoy son 43). Priorizar wires sobre repos existentes; repo nuevo → moldearlo sobre `migracionAWS/empleado_repo_NEW`.

---

## Modelo de roles funcionales (COMPLETO)
Tres roles en `utils/permisos.py`:
- **admin_rrhh** — lectura + escritura en todo.
- **gerencia_lectura** — lectura en todo, escritura en nada.
- **mandos_medios** — lectura + escritura solo en VACACIONES y AUSENCIAS; sin acceso al resto.
- Rol desconocido / None → **fail-closed**.

Núcleo: `puede(rol, seccion, accion)`, `require_permission(seccion, accion)` (dependency factory → `AppError(..., "FORBIDDEN", 403)`). Enum `Seccion` (26 valores). `MANDOS_MEDIOS_SECCIONES = frozenset({VACACIONES, AUSENCIAS})`. ~168 gates inline. Espejo front en `frontend/services/permisos.ts` (riesgo de divergencia manual). Sidebar filtra `NAV_GROUPS` por permiso, AuthGuard gatea por ruta, `useCanWrite` oculta botones de escritura.

**Decisión de producto (NO reabrir):** todo usuario, sin importar rol, accede a TODAS las empresas. No existe "usuario limitado a ciertas empresas".

---

## Audit log app-level (COMPLETO)
Captura **app-level** (no triggers DB). Tabla `auditoria` (mig 024+058): `id, tabla, registro_id, accion (INSERT|UPDATE|DELETE), datos_anteriores JSONB, datos_nuevos JSONB, usuario_id, ip, user_agent, created_at, empresa_id, entidad, evento`. Inmutable. Triggers DB viejos dropeados en 058.

`AuditService.registrar(...)` keyword-only, síncrono, **traga todo error** (no tumba la operación de negocio). `audit_repo` (insert + listar con filtros/paginación). Payloads canónicos en `services/_audit_payloads*.py`.

⚠️ **Bug conocido — auditoría de nómina silenciosa:** `_audit_payloads_rrhh.py` pasa el literal `"lote_nomina"` en `registro_id` (columna uuid) → el insert falla y `AuditService.registrar` traga la excepción → el evento se pierde en silencio. **Al copiar patrones de auditoría, copiar `_audit_payloads_ev.py` (correcto), NO el de nómina.** Pendiente de arreglar.

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

🚨 **Bug conocido de `confirmar()` — pérdida de datos, SIN arreglar (tarea aparte, requiere decisión):** el orden es `delete_lote(previo)` (línea :64) **antes** de `crear_lote(nuevo)` (:65), sin transacción (PostgREST = autocommit por request, no hay transacción multi-statement). Un reimport que falle en cualquier punto entre :64 y :74 deja **sin el lote viejo y sin el nuevo** — no es "lote a medias", es pérdida total del ciclo. Puntos de fallo verificados: `guardar_resultados` es insert-por-evaluado (no bulk); `crear_evaluados` devuelve `[]` en silencio si falla (a diferencia de `crear_lote` que levanta AppError) → `KeyError` crudo → 500 con lote ya creado y 0 evaluados. **Fix propuesto (no aplicado): invertir orden (crear nuevo antes de borrar viejo) + que `crear_evaluados` levante AppError como su hermano.** El botón de eliminar importación mitiga (permite borrar un lote incompleto y reimportar limpio).

### Métricas
Agregados en Python puro (`_evaluacion_metricas.py`), no SQL (~300 filas por lote no justifica vistas/RPC). ⚠️ Competencias en DOS tablas separadas (líder/general), cada una con su `n` — **nunca en el mismo ranking** (son 2 evaluaciones distintas, mezclarlas da resultado falso). Excluyen autoevaluaciones. La métrica más valiosa: **brecha de autopercepción** (auto vs promedio de terceros).

### Historial de importaciones (COMPLETO — última entrega)
Tab **"Importaciones"** en `/evaluaciones` con lista de todos los lotes, multi-selección y borrado. Backend + front, suite en **254 tests**.

**Backend:**
- `GET /lotes` en modo consolidado (`X-Empresa-Id` ausente/None) devuelve **todos los lotes de todas las empresas**. Enriquecido vía `repositories/_evaluacion_lotes_enrich.py` con `empresa_nombre`, `importado_por_nombre` (null si no hay), `evaluados` (conteo). **Sin N+1**: un lookup batch por dimensión (empresas, users, conteo con GROUP BY), no una query por fila.
- `delete_lote(lote_id, usuario_id)` — **desacoplado de la empresa activa**: valida contra `lote.empresa_id` (autoritativo, ya cargado), no contra el header. El gate WRITE del router (= admin_rrhh) es la única barrera. Audita `baja_lote_evaluaciones` con snapshot (`periodo` + `evaluados`) **antes** del CASCADE (después no se reconstruye).
- `POST /api/evaluaciones/resultados/lotes/eliminar` (bulk) — recibe `{lote_ids}`, devuelve `{eliminados, fallidos:[{id,motivo}]}`, éxito parcial clasificado (patrón `proyectos.asignar_bulk`), no aborta. Un evento de auditoría por baja efectiva.
- El router `evaluaciones_resultados.py` tiene gate READ por default → el DELETE y el bulk necesitan dependency WRITE inline propia.

**Frontend:**
- Tab "Importaciones" (solo `canWrite`). Componentes en `components/features/evaluaciones/`: `HistorialImportaciones.tsx` (orquestador, estados carga/vacío/error/datos) + `HistorialTable.tsx` (presentacional, desktop=tabla / mobile=cards). Hook `useHistorialImportaciones.ts` (carga consolidada + `eliminar(ids)` que normaliza single→DELETE y varios→bulk a un `LotesBulkResult` uniforme).
- **El borrado NO depende del selector de empresa del sidebar.** Usa `fetchLotesHistorial()` que fuerza `X-Empresa-Id: "todas"`. Multi-selección con checkboxes + "seleccionar todo", barra de acción con ≥1 seleccionado, ConfirmDialog destructivo, toast de éxito con conteo y de error listando fallidos.

⚠️ **`EliminarLoteButton.tsx` quedó huérfano** (código muerto, 0 callers) tras mover el borrado al historial. Su vieja guarda `disabled={!empresaActivaId}` era la que trababa el botón cuando el sidebar estaba en "Todas las empresas". Candidato a borrar junto con el dead code.

🔴 **FUGA ENTRE EMPRESAS — preexistente, pendiente de seguridad con prioridad:** los endpoints `GET /metricas`, `/evaluados`, `/export` y `/ficha` de evaluaciones **no validan empresa** — reciben `lote_id` crudo y nunca comparan contra la empresa del usuario. Con el UUID de un lote ajeno, cualquier admin_rrhh lee/exporta evaluados de otra empresa. No explotable hoy (una sola empresa cargada), se vuelve real con la segunda. El DELETE nuevo sí valida (contra `lote.empresa_id`), no hereda el agujero. **Arreglar antes de que entre la segunda empresa.**

### Entrega 2 — descarga de archivos originales (PENDIENTE, feature nueva)
Poder **volver a descargar los CSV originales** de cada importación. Hoy **no se puede**: el import parsea y descarta los bytes (cero `storage.upload`, `evaluacion_lotes` sin columna de ruta). Requiere: (1) guardar los dos CSV en Storage al confirmar (reusar patrón `adjunto_service` / bucket existente), (2) migración con columna(s) de ruta, (3) endpoint de descarga con `create_signed_url`. La infra de Storage ya existe (usada por 5 módulos: adjuntos, cvs, candidatos, certificados, logos).
🚩 **Solo hacia adelante.** El lote Julio 2026 ya existe sin archivos guardados — no se recupera. La descarga funciona solo para importaciones futuras. Confirmar con RRHH que el lote viejo se puede perder.

---

## 📋 PLAYBOOK — Filtros + export en Vacaciones y Ausencias (PENDIENTE, bloqueado por Excel de RRHH)

El trabajo hecho en evaluaciones (historial + multi-selección + borrado desacoplado + auditoría) **es el molde** para lo que hay que hacer en Vacaciones y Ausencias cuando lleguen los Excel reales de RRHH. Anotado para no re-diagnosticar.

**Objetivo:** que RRHH obtenga cualquier corte de información con el máximo detalle, sin pedirle nada a desarrollo. En cada módulo: todos los filtros posibles en la UI (empresa, área, empleado, estado, tipo, fechas) + **el export sale siempre con los filtros aplicados** (lo que se ve es lo que sale).

**Estado del terreno (ya relevado):**
- **Vacaciones · filtro empleado**: service+repo+helper+export **ya lo soportan**; falta exponerlo en el list router y agregar el control en el front. Solo WIRE.
- **Ausencias · filtro empleado**: **no existe en ninguna capa** (`ausencias_service.get_all` no lo acepta) → hay que construir la cadena completa service+router+front. (El export de ausencias sí se corrigió antes.)
- ⚠️ **`vacaciones/page.tsx` (148) y `ausencias/page.tsx` (141)** están dentro del límite pero con poco margen — sumar filtros exige extraer la barra de filtros a componente propio primero (reutilizable en los demás módulos). Seguir el patrón de página de listado (abajo).
- Todo filtro nuevo se **compone POR INTERSECCIÓN con el ownership** (`_ownership_filter.resolver_filtro_empleados`), nunca lo reemplaza.

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
- **Ownership mandos_medios:** `services/ownership.py` app-level. "A cargo" = `manager_id`, no área ni `es_lider`. Aplicado en Vacaciones y Ausencias (listados, export, 5 escrituras). Falta RLS a nivel DB (en AWS no va — queda app-level definitivo).

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

**Contraste con changelog de KarIA Reach (otro proyecto, mismo stack asyncpg/ECS/SSM) — verificado, aplica a Sofia:**
- Secretos en producción → **SSM Parameter Store / Secrets Manager, NUNCA hardcodeado**. URL-encodear caracteres especiales del password en la DSN (evita el bug de secreto truncado que a KarIA le costó días). Ya documentado en `MIGRACION_A_RDS.md` / `settings_ADD.md`. `migracionAWS/` está limpio: sin secretos ni placeholders pegados.
- asyncpg contra RDS: `postgres_client.py` usa `ssl="require"` ✅ y `command_timeout=30` ✅, host desde `database_url` (env, no hardcodeado). **Faltan (decisión de infra, no bug):** timeout de conexión explícito (default 60s cuelga el arranque si RDS es inalcanzable); `verify-full` en vez de `require` (require no verifica CA, abierto a MITM dentro de la VPC); si el DNS de RDS falla, poner IP privada en `database_url`.

---

## ⚠️ Build de producción y estilo de código — LEER ANTES DE TOCAR

### El repo NO está formateado con ruff, pese a su config
`ruff.toml` declara `line-length=100` + `[format]`, pero el código está en **estilo compacto de línea larga** (firmas de una línea >100 chars). Los límites documentados se midieron sobre ese estilo. **Correr `ruff format` reflowea archivos enteros** (en una prueba: `ausencias_service.py` 149→253). **NO correr `ruff format` dentro de una sesión de feature/bugfix.** Adoptar ruff repo-wide es tarea propia con re-medición de límites. ⚠️ Confirmar si `pre-commit` está instalado (los hooks de `.pre-commit-config.yaml` explotarían en el primer commit) — mina para la migración AWS.

### `tsc` en 0 y `next build` verde
`next dev` con Turbopack transpila sin type-check → errores de tipo pasan desapercibidos pero **`next build` falla**. Sin tests de front, `tsc` es la única red. **Regla: `node_modules/.bin/tsc --noEmit` tiene que dar 0. Si aparece un error, es tuyo.**

### 🚨 Módulo assessment desactivado — NO convertir el `useState` en `const`
`app/(dashboard)/assessment/[id]/page.tsx` está desactivado a propósito (redirige a `/dashboard`). El gate es `const [moduloActivo] = useState(false)` con el setter descartado. **Tiene que ser `useState`, NO `const`:** TS colapsa un `const` a literal `false`, marca el cuerpo inalcanzable, pierde el narrowing y **`next build` falla**. Hay un comentario explicándolo. No borrarlo, no "simplificar".

---

## Deuda técnica conocida

### Bugs / riesgos activos
- 🔴 **Fuga entre empresas** en `/metricas`, `/evaluados`, `/export`, `/ficha` de evaluaciones (ver sección evaluaciones). Prioridad antes de la 2ª empresa.
- 🚨 **`confirmar()` de evaluaciones** — pérdida total del lote si un reimport falla (ver sección evaluaciones). Fix propuesto, sin aplicar.
- 🚨 **Auditoría de nómina silenciosa** — `"lote_nomina"` string donde va un UUID → evento perdido. Copiar `_audit_payloads_ev.py`, no el de nómina.
- **`manager_id` 0/19** — rompe ownership de mandos_medios y desempate de matcheo. Avisar a RRHH.
- **`fetchEmpleados` — 4 opcionales posicionales del mismo tipo** (`string|undefined`). Agregar uno rompe callers en silencio (`tsc` no lo detecta, intercambiar dos `string|undefined` no es error de tipos). Fix real: objeto de opciones (toca 9 call sites). Mientras: al tocar la firma, tabla manual de callers.
- **Filtros duplicados front+back** (patrón recurrente): si un filtro afecta el export, va **server-side, una sola implementación**. Casos: `aplicar_filtro_estado` es espejo de `derive_estado` (merece test que las compare); listado de evaluaciones filtra client-side, exporta server-side (aceptable a ~30 filas, el endpoint ya acepta los filtros).
- **`page_size=100000` en export** — corte silencioso si una empresa lo supera.
- **`middleware/auth.py`** acepta cualquier UUID con formato válido como `X-Empresa-Id` sin verificar que exista. Baja prioridad.
- **`permisos.ts` es espejo manual de `permisos.py`** — riesgo de divergencia.

### Líneas (archivos over-limit, límite front 150 / back según tipo)
**Frontend:** `sucesion/page.tsx` 855 · `costos/page.tsx` 618 · `vacantes/[id]/page.tsx` 577 · `reportes/page.tsx` 539 · `onboarding/templates/[id]/page.tsx` 412 · `onboarding/page.tsx` 410 · `configuracion/page.tsx` 390 · `ImportarNominaCSVModal.tsx` 377 · `PlantillasTab.tsx` 336 · `CiclosTab.tsx` 297 · `offboarding/page.tsx` 292 · `NominaModal.tsx` 287 · `EvaluacionesTab.tsx` 286 · `areas/page.tsx` 261 · `AsignacionesTab.tsx` 211 · `assessment/[id]/page.tsx` 192 + ~26 más entre 152–268.
**Backend:** `reporte_generators` 249 · `integracion_service` 201 · `_audit_payloads_rrhh` 186 · `empleado_repo.py` 174 · `reporte_anual` 154 · `ev_instancias_repo` 146 · `nomina_repo` 107 · `proyectos_repo` 104. (`costo_repo` 135 y `assessment_repo` 130 son **legacy sin callers** — candidatos a borrar, junto con `EliminarLoteButton.tsx`.)
**Cerca del límite (el próximo cambio exige dividir primero):** `costo_service.py` 150 · `vacaciones_service.py` 142 · `empleado_service.py` 141 · routers `inventario_items.py`/`ausencias.py` 79 (margen 1) · `objetivos.py` 79 · `vacaciones.py` 75.

### Al margen por decisión (NO tocar)
- **S6 / DROP de `cargo` y `rol`** → no se borra nada (decisión de producto). Fallbacks `roles[0] ?? cargo` quedan.
- **Campo `equipo`** (texto libre): sin tabla `equipos`, "asignar/importar por equipo" no existe.
- **Import de objetivos**: bloqueado por modelo (objetivos cuelgan de `users` vía `responsable_id`, no de empleado).
- **Tablas huérfanas** (`assessment_reportes`, `configuracion_empresa`, `documentos_empleado`, `notificaciones`, `notificaciones_config`, `sucesion_posiciones`): se limpian **después del cutover a AWS** (dropear = migración nueva + regenerar `schema.sql` en plena migración).
- **"Compatibilidad con una posición"** (sucesión): feature nunca construida, no deuda técnica. El ranking es por assessment genérico, sin relación con posición. Cuando RRHH la reclame, definir qué significa compatibilidad antes de improvisar.

### Tests
- Front: **0 tests** en todo el repo. `tsc` es la única red.
- Adjuntos: 11 tests unit con `_FakeRepo` + storage monkeypatcheado. **E2E real nunca se ejecutó** (no hay bucket no-productivo; `_BUCKET="documentos"` hardcodeado apunta a prod). Decisión: E2E automatizado en el cutover a AWS/S3.
- Suite backend: **254 passed**.

### En pausa
- **Link público de carga de horas** — mockup HTML aprobado, esperando RRHH.
- **Limpieza general del repo** (código muerto, duplicación): 5–8 sesiones, no urgente. Candidato principal: filtro `empresa` duplicado 8× en 29 repos.

---

## Git
- Operar siempre desde `RRHH/Sofia/`.
- **Commits los hace Franco manualmente** (nunca Claude Code). Commits y push desacoplados: no hay push hasta que Franco lo decida. Preferir commits por sub-sesión.
- Formato convencional (`feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `test:`).
- Solo `main` y `origin/main`. Sin ramas sueltas.
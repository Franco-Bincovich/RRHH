# CLAUDE.md — RRHH (HR Karstec)

> **Ubicación:** raíz del repo RRHH (`RRHH/`), desde donde se ejecuta `claude`. `backend/`, `frontend/`, `docs/` y `migracionAWS/` cuelgan directo de la raíz — **`RRHH/` es el único repo git (no hay repos anidados), y todas las operaciones git corren desde ahí**.

## Documentos (leer al inicio) — jerarquía y qué responde cada uno

**Fuente de verdad del SCHEMA, en este orden:**
1. **El catálogo vivo de producción** (proyecto Supabase `grmdiwxcvcjorlohpwji`, "HR Karstec"). Producción driftea; el catálogo no miente.
2. **`backend/db/schema.sql`** — fuente de reconstrucción, y lo que `tests/_postgrest_schema.py` valida contra las queries. Hoy coincide con producción en tablas y constraints.
3. 🔴 **`docs/MODELO_DATOS.md` SE BORRÓ el 2/8/2026 — no lo busques ni lo recrees.** Se declaraba "fuente de verdad única del schema" y describía **13 tablas que no existen** (`equipos`, `empleado_proyecto`, `presupuesto_proyecto`, `seniorities`, `roles`, `skills`, `acceso_empresa`…) y **6 columnas inventadas solo en `horas_proyecto`**. **La única fuente de verdad del schema es `backend/db/schema.sql`**, que se lee del catálogo de Postgres y tiene un validador automático (`tests/_postgrest_schema.py`). Un segundo documento que lo describa en prosa vuelve a divergir: por eso no se reemplazó por nada.

**Fuente de verdad del TRABAJO — hay CINCO planes en `docs/` y solo el primero manda:**
1. 🟢 **`docs/PLAN-6-SEPTIEMBRE.md`** (12/8/2026) — **EL VIGENTE.** Entrega el 20/9, objetivo interno 6/9. Fases 0 a 4, las cinco features nuevas, las cuatro reglas de "construir pensando en el porteo" y las dependencias externas con fecha de vencimiento. Es el que manda para "qué se hace ahora".
2. **`docs/ORDEN-SESIONES-CODIGO.md`** (11/8) — el tablero de bloques **A–L**: qué se cerró, qué quedó pendiente, qué bloquea RRHH. Sigue siendo el mejor inventario de pendientes concretos; **ya no es el plan**.
3. **`docs/PLAN-DE-TRABAJO.md`** (5/8) — superseded. Declara en su encabezado que reemplaza al siguiente.
4. **`docs/Plan de trabajo`** (v2, 27/7 — el archivo no tiene extensión) — superseded por el anterior.
5. **`PLAN_DESARROLLO_AHORA.md` / `PLAN_DESARROLLO_DESPUES.md`** — registro histórico, ver abajo.
> 🔴 **Cinco planes es exactamente el modo de falla que este archivo documenta.** Ninguno se borra —cada uno es el registro de una etapa— pero **la jerarquía se lee acá y en ningún otro lado**. Si vas a escribir un plan nuevo, actualizá esta lista en la misma sesión.

- ⚠️ **`PLAN_DESARROLLO_AHORA.md` y `PLAN_DESARROLLO_DESPUES.md` quedaron OBSOLETOS como plan.** AHORA describe una Fase 0 multiempresa que se completó hace meses y reglas que ya no rigen ("sin checks de rol", "sin flujos de aprobación", auditoría por trigger `fn_auditoria()` — los triggers se dropearon en la migración 058). DESPUÉS describe features que en su mayoría no se van a construir en ese orden. **No borrarlos: siguen siendo el registro de la intención original de producto** (proyectos, costeo por hora, link público, capa de permisos por sección). Leerlos como contexto histórico, nunca como instrucción.

**Estado y trazabilidad:**
- **`docs/ESTADO-VS-COMPROMISO.md`** — contraste ítem por ítem entre lo comprometido con el directorio (junio 2026) y lo que el código + el catálogo realmente hacen. Estados HECHO / PARCIAL / NO EXISTE / DISTINTO / BLOQUEADO, con evidencia `archivo:línea`. **Responde "¿esto existe de verdad?"**
- **`docs/BITACORA-CAMBIOS.md`** — log por sesión, del más reciente al más viejo, de **qué cambió y qué tiene que hacer infraestructura al respecto**. Para el dev que monta AWS. **Regla: la entrada se escribe en la MISMA sesión que el cambio.** Responde "¿qué se rompió/condicionó desde la última vez que miré?"
- **`docs/MATRIZ-FILTROS.md`** — inventario de qué filtro existe en cada módulo y en cuál de las cuatro capas (repo → service → router → UI), y si el export lo acepta. **Se actualiza al cerrar cada tanda del bloque B.** Responde "¿qué corte de información puede sacar RRHH sin pedirnos nada?"

Documentos de la agencia (convenciones obligatorias): `docs/ORDEN-Y-LEGIBILIDAD.md` · `docs/SEGURIDAD-PENTEST.md` · `docs/BASES-DE-DESARROLLO.md` · `docs/UX-UI.md`.

**`docs/handoff-aws/`** — carpeta única de la migración a AWS (creada el 12/8/2026). Adentro: el
material que dejó el dev de infra tras migrar tres proyectos (`COMPARATIVA_VERCEL_SUPABASE_VS_AWS.md`,
`PATRONES_CODIGO_AWS.md`, `README-DEV.md`) y el `README.md` que explica cómo se usa.
🔴 **Esos tres son CONTEXTO de decisiones ya tomadas, NO instrucciones a ejecutar.** Su checklist
de 50 ítems no se corre, y **no se hace refactor preventivo para parecerse a sus patrones**: el
código existente del proyecto manda. Lo que sí sale de ahí son las cuatro reglas de porteo que
adoptó `PLAN-6-SEPTIEMBRE.md` (IDs `UUID`, un solo lugar para serializar, buckets centralizados,
nada de RLS en tablas nuevas).

> ✅ **Duplicación resuelta — TODA la doc vive en `docs/`, sin excepciones.** `Plan de trabajo`, `ORDEN-Y-LEGIBILIDAD.md` y `UX-UI.md` estaban tracked **dos veces** (raíz y `docs/`). Los dos `.md` eran idénticos; **`Plan de trabajo` NO**: el de la raíz era la v1 (153 líneas) y el de `docs/` la v2 (282), y nada indicaba cuál mandaba. **Se borraron las tres copias de la raíz.** La v1 queda en el historial de git (`1c5dd30`, última forma en `e9df215`). En la raíz solo quedan `CLAUDE.md` y `AUDITORIA_FUNCIONAL.md`.
> **Regla: un documento nuevo va en `docs/`. Si tenés que elegir entre dos copias, ya es tarde.**

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
- **Rate limiting**: slowapi con franjas por riesgo + baseline global por middleware. Ver "Hardening (Bloque A)".

## Entornos de desarrollo
- **Windows/PowerShell** (Lenovo) y **Mac** (MacBook Pro). El repo se clona limpio en cada una.
- ⚠️ **Un clon limpio NO trae `.env` ni `node_modules`.** Para verificar local hay que reconstruir los `.env` (valores en el dashboard de Vercel: `sofia-backend` y `sofia-front`) y correr `pip install` / `npm install`. Rutas de los env: `backend/.env`, `frontend/.env.local` (en el front es `.env.local`, no `.env`).
- ⚠️ **En la Mac, `npx tsc` a secas baja el paquete equivocado** (`tsc@2.0.4`, no TypeScript). Usar el binario local: `node_modules/.bin/tsc --noEmit`.
- ⚠️ El `python3` del sistema en la Mac puede tener una versión vieja de `supabase` que rompe el import. Para correr tests, crear venv 3.12 con `requirements.txt` + `requirements-dev.txt`.
- ⚠️ **En Windows el venv usable es `backend/venv/`** (`backend/.venv/` es un resto de la Mac, tiene `bin/` y no `Scripts/`). Si `venv` fue creado sin `requirements-dev.txt`, la suite falla con **33 errores que NO son del código**: sin `pytest-asyncio` los tests async "no están soportados nativamente" y sin `python-docx` revientan los de export. **Instalar los dos requirements antes de creer un rojo.**
- ⚠️ **Al correr mutation checks, `__pycache__` puede quedar viciado**: el arnés escribe y restaura el archivo tan rápido que Python reusa el bytecode mutado. **Si un fallo no se explica leyendo el código, borrar `__pycache__` y reintentar antes de diagnosticar nada.**
- PowerShell: sin `&&` (usar `;`). Paths con paréntesis o corchetes entre comillas, y **`Get-Content -LiteralPath`** — sin `-LiteralPath`, las rutas con `[id]` se interpretan como glob y el archivo "no existe" (subestima cualquier conteo de líneas del front).

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

**Variables nuevas del Bloque A en `sofia-backend`** (las dos tienen default seguro, pero conviene declararlas explícitas):
- **`TRUSTED_PROXY_HOPS`** (default `1`) — cuántas capas de proxy CONFIABLES hay delante. Define qué entrada de `X-Forwarded-For` es la IP real. `1` = Vercel · `0` = local sin proxy · AWS: `1` con ALB solo, `2` con CloudFront adelante. 🔴 **Un valor de más colapsa TODO el tráfico en un solo contador y deja al equipo entero afuera.**
- **`RATE_LIMIT_STORAGE_URI`** (default `memory://`) — store de los contadores. `memory://` es **por proceso**: en serverless cada cold start arranca en cero y con N instancias vivas el límite efectivo es N×. El enchufe para `redis://...` está puesto; conectarlo es decisión de infraestructura.
- **`ASSESSMENT_ENABLED`** (default `false`) — ver "Módulos desactivados".

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

⚠️ La raíz `/` del front redirige a `/login`. Un usuario con sesión válida que entra a `/` cae en `/dashboard` (guard en `login/page.tsx`). El backend en `/` da 404 de plataforma (no tiene endpoint raíz) — es normal, `/health` es el que responde.

---

## 🎯 FOCO ACTUAL

🔴 **EL PLAN VIGENTE ES `docs/PLAN-6-SEPTIEMBRE.md`** (12/8/2026). Entrega comprometida **20 de
septiembre**, objetivo interno **6 de septiembre** para dejarle dos semanas de colchón al dev de
infra. Los otros tres documentos de plan quedaron atrás y **cada uno declara a quién supersede**:
`ORDEN-SESIONES-CODIGO.md` (11/8, bloques A–L) → `PLAN-DE-TRABAJO.md` (5/8) → `Plan de trabajo`
(v2, 27/7). Ninguno se borra; todos son registro. **Para "qué se hace ahora" manda el primero.**
⚠️ El plan del 6/9 describe la Fase 0 y el congelamiento del 21/8 como TRABAJO FUTURO — ya
ocurrieron. Esta sección se reescribió el 19/8/2026 con el estado real; el documento en sí no
se tocó (es de Franco).

**🟢 EL BLOQUE A (backend de seguridad/estado) ESTÁ CERRADO.** Sesiones A2 a A6 más A3.3, todas
sobre `main`, sin frontend:

- **A2/A3** — el estado `preingreso`: CHECK ensanchado (mig 120), 18 lecturas de `empleados.estado`
  auditadas y correctas gratis, `POST /api/empleados/{id}/activar` (guardas: es preingreso · la
  fecha de ingreso ya ocurrió), `POST /api/offboarding/{id}/efectivizar` con guarda de
  preingreso (quien nunca entró no figura como baja del mes).
- **A3.3** — cierra el bloque: import de nómina ya NO da de baja a un preingreso (lo saltea y
  reporta) · el link público distingue en el forense "se fue" de "todavía no entró" (mig 121,
  **escrita, no corrida**) · este documento, remedido.
- **A4.2** — el puente candidato→empleado: `POST /api/candidatos/{id}/contratar` (candidato en
  oferta → legajo en `preingreso`, cinco guardas).
- **A5 / A5.1 / A5.2** — módulo de Formación (ex-Capacitaciones): renombre de texto visible, las
  7 columnas del Excel de formación cableadas de punta a punta, e import completo por Excel
  (`POST /api/importacion/formacion/preview` y `/confirmar`) con matcheo de personas, traducción
  de estado y duplicados reportados en vez de romper.
- **A6** — el panel "Requiere tu atención" del dashboard: `GET /api/dashboard/atencion` (alertas
  calculadas + manuales de agenda, en una sola respuesta) y `POST /api/dashboard/atencion/resolver`.

**🔴 TODO LO ANTERIOR TIENE BACKEND CON TESTS VERDES Y CERO BOTÓN EN EL FRONT.** El bloque B
(frontend) todavía no arrancó. La lista completa de qué necesita UI, qué archivos están al
límite de línea y qué decisiones de producto quedaron abiertas está en
`docs/DEUDA-TECNICA.md`, sección **"Cierre del bloque A (19/8/2026)"** — es el punto de partida
del bloque B, léela antes de escribir el primer componente.

> 🔴 **LO PRIMERO QUE EL BLOQUE B TIENE QUE SABER — EL TABLERO DE OBJETIVOS SE CONSTRUYE CONTRA EL
> WRAPPER PAGINADO, AUNQUE EL BACKEND HOY DEVUELVA TODO.**
> `ObjetivoListResponse` **ya** tiene la forma final `{items, total, page, page_size,
> total_pages}`; lo único provisorio es que hoy `total == len(items)` porque `objetivo_repo`
> todavía trae el árbol entero (es la única lista del sistema que no pagina — ver *Deuda*).
> **Qué significa en la práctica, sin excepción:** el front lee **`total`** para los contadores
> del encabezado, monta **`Pagination`**, y **NUNCA asume que le llegó el conjunto completo** —
> ni `items.length` como total, ni `.reduce()` sobre `items` para un agregado, ni contar o
> filtrar en el cliente lo que el backend ya sabe contar.
> **Por qué ahora y no cuando se pagine:** escrito contra el wrapper, el día que el backend
> pagine **el front no cambia una sola línea**. Escrito contra "me llega todo", hay que rehacer
> contadores, filtros y agregados — y ese día ya es septiembre. Es el bug que `HorasTab` ya pagó
> una vez: decía "9 h" con 400 h cargadas, porque sumaba con `.reduce()` sobre la página en lugar
> de leer el total del backend. El contrato está escrito también en `schemas/objetivo.py`, al pie
> de `ObjetivoListResponse`.

**Bloques previos, completos, con commits en `main`** (sin cambios desde la última medición):
Fases 0–3 (blindaje, reportes+KPIs, barrera de empresa, deuda estructural) · Bloques B
(filtros/exports) · C (compromisos del directorio, salvo C6 sin alcance) · D–L (agosto: mails,
CV screening, exports en 25 módulos, clientes globales, desmontaje de `ev_*`). El bloque B DE
OBJETIVOS se canceló (decisión de producto, ver más abajo).

### 🔴 EL PROBLEMA #1 NO ES CÓDIGO: RRHH no cargó datos
Verificado contra el catálogo vivo (**12/8/2026**): **2 empresas, 31 empleados** (19 + 12), y casi todo lo demás vacío:
- `manager_id` **11/31** · `seniority` 3/31 · `horas_contrato` **0/31**
- `solicitudes_vacaciones` 0 · `solicitudes_ausencia` 0 · **`costos_nomina` 0**
- Apenas arrancados: `vacantes` 1 · `objetivos` 1 · `candidatos` 3 · **`clientes` 4 · `horas_proyecto` 1**
- Poblado: `fecha_nacimiento` 31/31 (por eso el KPI de cumpleaños muestra datos) · `areas` 12 · `auditoria` 156 filas · el lote de evaluaciones (10 evaluados, 307 resultados).

> 🟢 **`manager_id` DEJÓ DE ESTAR EN CERO** (0/19 → 11/31). Es el cambio más importante de este
> bloque y desbloquea dos cosas que estaban declaradas como no probables: el rol
> **`mandos_medios`** ahora tiene a quién ver (su ownership cuelga de ese campo), y el
> **desempate por superior** del matcheo de evaluaciones empieza a discriminar de verdad. Los
> 20 restantes siguen sin cargar, así que probar mandos_medios exige elegir un usuario que sea
> manager de alguien.
>
> 🔴 **`horas_contrato` 0/31 es el nuevo cero que importa:** toda licencia cargada por el link
> público se calcula con la jornada asumida de 8 h y sale marcada `horas_por_dia_estimadas`.

**Consecuencia:** los reportes y KPIs están correctos pero salen VACÍOS. Antes de entregar a RRHH hay que avisarles explícitamente, o van a abrir pantallas vacías y creer que están rotas. Esto NO es deuda técnica — es un bloqueante de adopción.

> ⚠️ **`costos_nomina` en 0 tiene un efecto colateral que no es obvio:** el **historial salarial** (C1) muestra la serie de esa tabla, así que hoy sale vacío para todos. La feature está entera; el dato no existe.

### Al entregar a testing, decirle a RRHH:
1. Los reportes/KPIs salen vacíos hasta que carguen dotación, vacaciones, ausencias, costos. No están rotos.
2. `manager_id` **11/31** → `mandos_medios` YA se puede probar, pero solo con un usuario que sea manager de alguien; los otros 20 empleados siguen sin superior y un manager vacío no ve nada.
3. Los filtros nuevos (área, proyecto, empleado, rango de fechas) están vivos, pero con 31 empleados y un proyecto que concentra 13, **casi todo filtro devuelve casi todo**. No es un filtro roto: es el reparto real de la gente.
4. **El link público de horas necesita al menos un cliente cargado EN EL SISTEMA** (hay 4, verificado el 12/8/2026): con CERO clientes la identificación por DNI rechaza al padrón entero, y por rechazo único el empleado no ve la diferencia con "tu DNI no existe". 🔴 **El gate es de SISTEMA, no por empresa** (bloque L): antes bastaba con que la sociedad de esa persona no tuviera clientes propios para dejarla afuera con el sistema lleno.
5. Qué se espera que "traten de romper".

### Fases cerradas (no reabrir)
- ✅ **FASE 2 — Barrera de empresa (commits `bd95e98` + `9d7baa7`).** **92/92 endpoints con id de recurso donde aplica** validaban empresa, y **13/13 superficies de VACACIONES y AUSENCIAS** componían además el eje de ownership. 8 endpoints quedaron marcados NO APLICA con razón: `usuarios` (`DELETE /{user_id}` — los usuarios no cuelgan de una empresa, por decisión de producto), `empresa` (`GET`/`PUT`/`PATCH /{id}/activa`/`POST /{id}/logo` — la empresa *es* el recurso), `assessment` público (`GET`/`POST /evaluacion/{token}` — sin auth, la autorización es el token) e `integraciones` (`DELETE /{tipo}` — scopeado por `user_id`, no por empresa). **Los 2 de assessment ya ni se montan** (Bloque A1). **La regla permanente está en "Patrón de barrera de empresa" — leerla antes de escribir un endpoint nuevo, y aplicarla a los endpoints que se agregaron después del barrido.**
- ✅ **FASE 3 — Deuda estructural (commits `51832e2` + `a6acaed`).** `fetchEmpleados`/`exportarEmpleados` a objeto de opciones (10 call sites) · `sucesion/page.tsx` 855 → 85 (8 componentes + 2 hooks) · N+1 de sucesión resuelto por batch.

**Pendientes de RRHH (bloqueantes de datos):**
- Cargar datos reales en los módulos (ver arriba).
- Excel reales de vacaciones y ausencias (sin ellos no se define el parser de import — **es lo ÚNICO que queda del playbook de vacaciones/ausencias; los filtros ya están**).
- Un **segundo lote de evaluaciones** (sin él, las estadísticas cross-lote del Bloque D no son verificables).
- Evaluaciones: ¿pueden exportar DNI o legajo? · los 2 líderes sin nota final · qué es "Kolektor".

---

## 🚨 REGLA TRANSVERSAL — *Un test solo prueba lo que el fake puede desmentir*

**Es el patrón que más veces se repitió en este repo, y el que más caro sale: el test está en verde y el código está roto.** No falla la lógica del test — falla que el fake **no modela la única diferencia que importaba**, así que el modo de falla que se quería cubrir *no puede aparecer*.

### La pregunta obligatoria antes de dar un test por bueno
> **¿Qué tendría que ser distinto en el fake para que este test pueda fallar?**
>
> Si la respuesta es "nada" o no sale sola, el test no está probando lo que su nombre dice. Escribir la respuesta **en el docstring del test**.

### Las cinco veces que pasó (todas reales, todas en este repo)

| # | El fake… | Lo que quedó sin probar | Dónde está escrito |
|---|---|---|---|
| 1 | acepta `empresa_id` y **lo ignora** | la barrera de empresa entera — exactamente el bug que el test venía a cubrir | "Patrón de barrera de empresa" |
| 2 | devuelve **la MISMA forma** para `find_by_id` y para `update` (misma factory) | la asimetría con-joins / sin-joins que generó el **diff fantasma de auditoría** (93 eventos falsos) | `tests/test_audit_diff_derivados.py` |
| 3 | **ordena en Python** | el `.order(..., desc=True)` real: sacárselo dejaba todo en verde | `tests/test_historial_salarial.py::TestElOrdenLoPoneLaQuery` |
| 4 | renderiza con `renderToStaticMarkup`, que **no ejecuta `useEffect`** | un test de "sin permiso no pide datos" pasaba **con el guard borrado** | `components/features/empleados/ficha/HistorialSalarialSection.test.tsx` |
| 5 | usa una **clave de ruta que dejó de existir** al mudarse el endpoint | la aserción quedó **vacua** (`assert not _limites(...)` sobre una clave inexistente) y seguía en verde | `tests/test_rate_limit.py::test_los_dos_pendientes_siguen_sin_decorador` |

### Las reglas que salen de ahí (todas obligatorias)
- **Todo fake nuevo modela DOS empresas** y devuelve `None` cuando `empresa_id` no coincide. Un fake permisivo a propósito **se declara en el docstring** (ver `tests/test_assessment_vacantes_scope.py`).
- **Todo fake de un repo con lecturas enriquecidas modela la asimetría**: `find_by_id` devuelve la fila CON los campos de join, la escritura la devuelve SIN ellos.
- **Todo fake de escritura construye la respuesta A PARTIR de lo que recibe**, nunca devuelve un objeto prefabricado — si no, el test afirma algo sobre su propia constante (ver `tests/test_domicilio_desglosado.py`, que lo explica en el encabezado).
- **Lo que tiene que viajar EN LA QUERY se testea un escalón más abajo**, falseando el cliente de Supabase y capturando los `.order()/.eq()/.in_()` — no el repo. Moldes: `TestElOrdenLoPoneLaQuery` y `TestElWhereDelRepoLlevaLaEmpresa` (`test_offboarding_entrevista.py`).
- **Un test que cierra un pendiente no se BORRA de la lista de pendientes: se MUEVE** al test que verifica lo contrario. Borrarlo deja la aserción restante sin nada que mirar.
- **Todo barrido automático lleva su guarda de mínimo** (`assert len(...) >= N`). Sin ella, si la derivación se rompe el barrido devuelve 0 elementos y **todo pasa sin haber comparado nada**. Ver los cuatro barridos estructurales de abajo.

---

## 🔒 Hardening (Bloque A) — rate limiting, empresas, OAuth

### `utils/rate_limit.py` — el limiter único de la app
Vive en `utils/`, no en un router (antes el `Limiter` estaba en `routers/auth.py` y `main.py` lo importaba de ahí — un router configurando la app).

- **`client_ip(request)`** — key_func propia. `X-Forwarded-For` se construye de izquierda a derecha: las entradas de la **derecha** las escribió nuestra infraestructura y son confiables; las de la izquierda las pudo inventar el cliente. Con N proxies confiables la IP real es `hops[-N]` (`settings.trusted_proxy_hops`). Si el header trae menos saltos de los declarados, cae a la IP de la conexión. **NO usar `slowapi.util.get_ipaddr`**: busca `"X_FORWARDED_FOR"` con guiones bajos, que no es un header HTTP válido, así que esa rama nunca corre y siempre devuelve `request.client.host`, en silencio.
- **Baseline por middleware** — `SlowAPIMiddleware` aplica `default_limits = ["300/minute"]` a **todo endpoint sin decorador propio**, sin tocar un solo router. Un endpoint decorado **ignora** el baseline (`override_defaults=True` es el default de `limiter.limit`): el decorador reemplaza, no se suma.
- **Franjas por riesgo** (de más restrictiva a menos): público sin auth 10/min (5/min el submit de assessment) · login 5/min, refresh 20/min, cambiar-password 10/hora · **import 10/hora compartido** (`scope="import"`, **9 endpoints** medidos el 19/8/2026: los 2 de cada uno de objetivos/formación/nómina-empleados/nómina-costos + el 1 de evaluaciones) · **export 100/hora POR USUARIO compartido** (`scope="export"`, vía el decorador único `limite_export` de `utils/rate_limit.py` — **28 endpoints** decorados con `@limite_export`, uno por router; reemplazó un "30/hora por IP" que agotaba los 30 en minutos con 10 empresas y modo consolidado) · `POST /reportes/generar` 20/hora (llama a Claude, cada request cuesta plata) · `/health` **exento**.
  > ⚠️ **No hay una franja "export 30/hora" separada de `limite_export`**: son el mismo mecanismo. Una sesión anterior (A5.1) leyó el `@limite_export` de `capacitaciones.py` como "otra cosa" porque no encontró el literal `scope="export"` repetido en cada router — está centralizado en `utils/rate_limit.py:105`, no repetido.
- **Handler 429 propio** — `rate_limit_handler` arma el body con `global_error_handler`, el mismo que produce todos los errores de la app, así el 429 no puede divergir del contrato `{error, message, code}` que el front espera. Agrega `Retry-After`; si no se puede calcular, sale sin el header (perder un header es aceptable, convertir el 429 en 500 no).

> 🚨 **`headers_enabled=False` es A PROPÓSITO, no un olvido — no lo "corrijas".**
> Con `headers_enabled=True`, **slowapi 0.1.9 rompe el camino de ÉXITO** de todo endpoint decorado: tras un request OK intenta inyectar los headers en `kwargs.get("response")`, que es `None` salvo que el endpoint declare un parámetro `response: Response`. Con `None` levanta `"parameter 'response' must be an instance of starlette.responses.Response"`, que el handler global convierte en **500**. O sea: **cada endpoint limitado devolvería 500 al responder BIEN.** Evitarlo exigiría agregar `response: Response` a todas las firmas decoradas. El único header que importa —`Retry-After`— lo calcula el handler. Está documentado también dentro del archivo.

> ⚠️ **Dos límites reales de esta implementación, para no venderla de más:** (1) el store es por proceso (ver `RATE_LIMIT_STORAGE_URI`); (2) la key es la IP y depende de `TRUSTED_PROXY_HOPS`.
> ⚠️ **Tres exports quedaron fuera de la franja y corren bajo el baseline**: `objetivos.py` e `inventario_items.py` (79 líneas cada uno). Sumarles el decorador los pasaba del límite de 80 del router. **Cuando se dividan, agregarles `shared_limit("30/hour", scope="export")`** — hay un test que lo recuerda.

### `utils/empresas_cache.py` — validación de `X-Empresa-Id`
Antes el middleware solo validaba el **formato**: un UUID sintácticamente correcto de una empresa inexistente entraba igual, viajaba aguas abajo y llegaba a columnas con FK a `empresas` —`auditoria.empresa_id` entre ellas— haciendo fallar el INSERT del evento, **que `AuditService` se traga por diseño**: la operación de negocio se completaba y el registro de auditoría desaparecía sin rastro.

Ahora `_resolver_empresa_id` consulta un **caché por proceso** del set de ids (molde: el `PyJWKClient` del propio middleware). TTL 300 s · **el constructor no toca la base** (primera carga perezosa, para no penalizar el cold start en serverless) · **refresco ante un miss** con ventana de gracia de 10 s (un miss es justamente "quizás es una empresa recién creada"; sin ese refresco quedaría invisible hasta 5 minutos). Guarda **todas** las empresas, activas e inactivas: la pregunta es "¿es una empresa real?", no "¿está habilitada?".

> 🚨 **ES FAIL-OPEN, y no es un descuido — no lo "corrijas".**
> Si el caché no se puede cargar, **se ACEPTA el header**. Suena al revés y lo es solo en apariencia: **descartar el header ENSANCHA**, porque `empresa_id=None` significa "todas las empresas" (vista consolidada). La opción conservadora ante un blip de base es aceptar; descartar cambiaría en silencio la vista de todo el mundo al consolidado. Y no hay riesgo de acceso: el consolidado ya está autorizado para todos los roles (decisión de producto cerrada).
>
> **Esto es HARDENING, no la barrera de seguridad.** La barrera es la de Fase 2 (filtro en el WHERE) y **no depende de esto en absoluto**.

Un id inexistente se **descarta en silencio**, sin status propio: un 400 no compraría seguridad y agregaría el oráculo de enumeración de empresas que la Fase 2 cerró. Se loguea a WARNING.

### `oauth_states` (mig 080) + `services/_oauth_state.py` + `_google_oauth.py`
Antes el `state` del callback de Google **era el `user_id`**: estable, adivinable, no validado server-side, y el callback está en `PUBLIC_ROUTES`. No cumplía ninguna función anti-CSRF.

Ahora es un **nonce de un solo uso**: `secrets.token_urlsafe(32)` (256 bits), se persiste **hasheado** (SHA-256 sin salt — contra 256 bits de entropía no hay diccionario ni tabla precomputada), TTL 10 minutos. **La identidad del usuario sale de la fila persistida, nunca del query param del callback.** Tabla `oauth_states (id, state_hash, user_id, proveedor, expires_at, created_at)`, con `proveedor` para que una segunda integración OAuth no necesite otra tabla.

> 🔴 **El DELETE ES la verificación, no un select-then-delete.** `OAuthStateRepo.consumir` hace `delete().eq(state_hash).eq(proveedor)` y devuelve la fila borrada. Así el uso único es **atómico**: si dos callbacks llegan a la vez con el mismo valor, la base le entrega la fila a uno solo y el otro recibe `None`. Un `select` seguido de un `delete` deja esa ventana abierta.

**RECHAZO ÚNICO:** los cuatro motivos por los que un state puede no servir —ausente, desconocido, vencido, ya usado— salen por el **mismo** `AppError` (`OAUTH_STATE_INVALIDO`, 400), mismo mensaje. Mismo criterio que la barrera de empresa. El WARNING que se loguea tampoco incluye el valor recibido.

La purga de vencidos corre en el camino que **crea** states (el que genera las filas), así se autobalancea sin job periódico. Es higiene, no corrección: la verificación ya descarta por `expires_at`.

---

## Estructura (backend)
```
backend/
├── main.py              ← entrada + middleware (71 líneas; el registro se fue a registro_routers.py)
├── registro_routers.py  ← registrar(app): 77 app.include_router() (75 incondicionales + 2
│                          gateados por flag: assessment_enabled, horas_publico_enabled). Es
│                          FUNCIÓN, no módulo con efectos: los flags se leen AL LLAMARLA, así un
│                          test puede encenderlos y re-registrar. 🔴 197/200 líneas — el próximo
│                          router NUEVO exige dividirlo primero (ver "Líneas" más abajo).
├── config/settings.py   ← única fuente de config y env (Settings() se instancia en import)
├── routers/             ← 81 archivos (límite 80 líneas cada uno)
├── services/            ← 231 archivos de lógica de negocio (257 con submódulos: export/ 8,
│                          mailer/ 6, reportes/ 12) (límite 150)
│   ├── _empleado_scope.py     ← barrera de empresa/ownership sobre el empleado target (Fase 2)
│   ├── _adjunto_padres.py     ← resolver de la entidad padre de un adjunto (Fase 2)
│   ├── _empleados_write.py    ← altas/ediciones de empleado, extraído por límite
│   ├── _onboarding_iniciar.py ← alta de onboarding, extraído por límite
│   ├── _vacaciones_write.py   ← create de vacaciones, simétrico con _ausencias_write (B4)
│   ├── _costos_write.py       ← write path de costos, extraído por límite
│   ├── _limite_export.py      ← LIMITE_FILAS_EXPORT + verificar_limite_export (B7)
│   ├── _oauth_state.py        ← nonces del flujo OAuth, sin nada de Google (A4)
│   ├── _google_oauth.py       ← lo específico de Google (A4)
│   ├── _offboarding_entrevista.py ← entrevista de salida (C3)
│   ├── _alcance_mandos.py     ← 🔴 LA ÚNICA excepción a la barrera de empresa (ownership cruzado)
│   ├── _import_csv.py, _import_encoding.py ← lector de CSV único de los 3 imports
│   ├── _tipos_jerarquia.py    ← guarda de profundidad de los subtipos de ausencia (mig 088)
│   ├── _nomina_superiores.py, _superiores_matcher.py ← 2ª pasada del import (mig 086)
│   ├── _usuario_alta.py       ← alta de usuario, extraída por límite
│   ├── _reporte_anual_metricas.py, _audit_payloads_offboarding.py ← extraídos por límite
│   ├── cliente_service.py     ← ABM del catálogo GLOBAL de clientes; la baja es LÓGICA (activo=False)
│   ├── identificacion_service.py ← paso 1 del link público: DNI → sesión. Rechazo ÚNICO + piso de tiempo
│   ├── _sesion_horas.py       ← el token opaco que lleva la identidad del paso 1 al 2
│   ├── carga_horas_service.py, _carga_reglas.py, _carga_licencia.py ← la carga: tope 12 h, ventana 30 días, licencia
│   ├── _semana_publica.py     ← "lo que cargaste esta semana" (lunes a domingo, la decide el backend)
│   ├── horas_cliente_service.py, _horas_cliente_agrupacion.py ← la vista interna por cliente
│   ├── mailer/                ← punto de salida ÚNICO de mails; expone solo enviar_mail
│   ├── export/                ← punto de salida ÚNICO de exports; expone build_export
│   └── reportes/              ← un submódulo por familia + _common.py
├── repositories/        ← 111 archivos, único acceso a DB (límite 100, satélites incluidos)
│   ├── cliente_repo.py        ← catálogo GLOBAL (sin empresa); `existe_nombre` compara TODO el catálogo en Python, NO con .ilike()
│   ├── _hora_row.py           ← mapper de horas_proyecto con lookups por lote (anti-N+1)
│   ├── identificacion_repo.py, sesion_horas_repo.py ← DNI → empleado · nonces de sesión del link público
│   ├── _horas_vista_repo.py, _semana_publica_repo.py ← la vista interna · la semana del empleado
│   ├── _scope_filtros.py      ← "qué empleados caen bajo área/proyecto" (B3/B4, era _area_scope.py)
│   ├── _rango_fechas.py       ← filtro por período con semántica de SOLAPAMIENTO (B5)
│   ├── _empleado_write_repo.py, _empleado_row.py, _nomina_row.py, _offboarding_row.py
│   ├── _onboarding_templates_{row,filtros,write}.py ← SELECT+mappers · visibilidad · payloads
│   └── oauth_state_repo.py    ← crear · consumir · purgar_vencidos (A4)
├── integrations/        ← wrappers externos (supabase_client, anthropic)
│   └── storage.py       ← 🔴 PUNTO DE CONTACTO ÚNICO con Storage. Los 3 buckets y las 4
│                          operaciones. API neutral al proveedor: afuera no se ve `from_()`
│                          ni `signedURL`. Al pasar a S3 se toca ESTE archivo y ninguno más.
├── schemas/             ← Pydantic in/out (+ empleado_out.py y _provincias.py)
├── utils/               ← permisos.py, errors.py, logger.py, rate_limit.py, empresas_cache.py
├── db/schema.sql        ← FUENTE DE RECONSTRUCCIÓN (55 tablas — CREATE TABLE contados el
│                          19/8/2026; FKs/índices no remedidos esta sesión)
├── migrations/          ← 121 archivos SQL (075–077 viven en migracionAWS/)
├── ruff.toml            ← config de ruff (reemplazó pyproject.toml, por Vercel)
├── pytest.ini           ← config de pytest (asyncio_mode=auto, testpaths=tests)
└── tests/               ← 211 archivos .py: 192 `test_*.py` + 19 helpers `_*.py` (exentos del
                            límite de 200 los primeros, NO los segundos — ver "Líneas")
```

**Env vars obligatorias** (sin default → rompen el import si faltan): `supabase_url`, `supabase_anon_key`, `supabase_service_key`, `jwt_secret`, `anthropic_api_key`, `resend_api_key`. Con default: `assessment_enabled`, **`horas_publico_enabled`** (`false` — enciende el link público de carga de horas), `trusted_proxy_hops`, `rate_limit_storage_uri`, `supabase_timeout` (30 s), Google OAuth, `frontend_url`, `allowed_origins`. La migración a AWS agrega `database_url`.

**Migraciones y salud de base.** 121 archivos SQL. La última ESCRITA es **121**
(`intentos_identificacion_preingreso`, A3.3) — **NO corrida a la fecha de este documento**, la
corre Franco. La última CORRIDA en producción sigue siendo la **120** (`empleados_estado_preingreso`,
17/8/2026: agrega `'preingreso'` al CHECK de `empleados.estado`). ⚠️ **Sin MCP de Supabase en
las últimas sesiones, este párrafo NO está reverificado contra el catálogo VIVO** desde el
12/8/2026 (112, `drop_tablas_muertas`, 52 tablas en ese momento) — lo que sigue es una
proyección a partir de qué migraciones se ESCRIBIERON después y su propio texto dice si
requieren correrse antes de la siguiente para no fallar. Migraciones 113–121 escritas y (según
sus propios encabezados) pensadas para correr en orden antes del congelamiento de schema:
**113** (perfiles_puesto, recategorizaciones, eventos_agenda, +3 tablas → 55) · 114 (post-deploy
del lote 113) · 115 (índices de escala) · 116 (11 columnas finales + `empleado_id` nullable en
`empleado_capacitacion`) · 117 (categoria en recategorizaciones) · 118 (índices de paginación) ·
119 (objetivo.tipo + areas array) · 120 (estado preingreso) · **121 (preingreso en el forense
del link público — escrita en A3.3, no corrida)**. `db/schema.sql` (el documento de
reconstrucción, no producción) ya refleja 113–121 completas, incluida la 121.
> ⚠️ **La 109 estuvo pendiente y este documento lo afirmó al revés durante unas horas.** Decía "108–112 todas corridas" tras verificar **solo el conteo de tablas** (52 = 52), y la 109 no crea ni borra tablas —borra una columna y tres objetos—, así que era invisible a esa comprobación. **Contar tablas no alcanza para decir que `schema.sql` refleja producción: hay que mirar el objeto que la migración toca.** Es el tercer desfasaje del encabezado de `schema.sql`; la regla que sale de los tres está escrita ahí. Las 072/073/074 corrigieron drift. **Destructivas: la 084** (`DROP COLUMN modalidad_contratacion` y `nivel`), **la 109** (drop de `clientes.empresa_id`) **y la 112** (drop de 11 tablas). `000_run_all.sql` **deprecado con guard que aborta**. Detalle de reconstrucción desde cero en **`docs/DEPLOY.md`**.

**Contraste schema.sql ↔ catálogo vivo (reverificado el 12/8/2026, ya con la 112 corrida):**

| | `db/schema.sql` | Producción | |
|---|---|---|---|
| Tablas | 52 | 52 | ✅ |
| FKs | 133 declaradas | 134 | ✅ la de más es `users.id → auth.users(id)`, que `schema.sql` no declara a propósito (es la mina de la migración a RDS) |
| Índices | 141 standalone declarados | 235 en `pg_indexes` | ✅ la diferencia son los índices que Postgres crea solo por PK/UNIQUE |
| Triggers `updated_at` | **0** | **35** | 🔴 `schema.sql` NO los trae — se recrean aparte (mig 077, en `migracionAWS/`) |

> ⚠️ **No compares "constraints" contra el catálogo con un solo número.** Acá vivía una fila que decía `364 = 364`; el catálogo cuenta cada `NOT NULL` como CHECK (hoy da 705 en total), así que ese número no era comparable con nada que se lea del archivo. La fila de FKs sí lo es, y es la que quedó.
>
> ✅ **J5b CORRIÓ (11/8/2026) — esto ya no es futuro.** En producción hay **43 triggers** no internos: **35** de `updated_at` + **8** `trg_emp_*` (defaults de `empresa_id` del retrofit multiempresa). `trg_emp_sucesion` se fue con `sucesion_posiciones`. La excepción con vencimiento (`tests/test_triggers_updated_at.py::_PENDIENTES_DE_DROP_J5B`) **se cerró y se borró**: el barrido volvió a ser igualdad estricta 35 = 35 en las dos direcciones.

---

## Convenciones de código
- Errores: siempre `AppError(message, code, status_code)`.
- Logs: solo eventos de negocio importantes. Sin `print()` / `console.log()` — logger centralizado.
- Config: solo vía `settings`, nunca `os.environ` directo.
- **Límites de líneas (estrictos)**: router 80 · service 150 · repository 100 · componente React 150 · hook 80 · otros 200. Medir SIEMPRE con `.Count` y **`-LiteralPath`** (no `Measure-Object -Line`, subestima; sin `-LiteralPath` los paths con `[id]` no se leen).
- 🔴 **LOS ARCHIVOS `tests/test_*.py` ESTÁN EXENTOS DEL LÍMITE DE 200 — declarado el 18/8/2026.**
  **El dato: de los 204 archivos de `backend/tests/`, 117 están sobre 200. Mediana 233, máximo
  1169 (`test_objetivos.py`).** La regla nunca rigió ahí, y escribirla como si rigiera obligaba a
  cada sesión a decidir sola si arrastraba una deuda de 117 archivos que nadie había declarado —
  y en la práctica la ignoraba. Una regla que se saltea sistemáticamente le quita autoridad a las
  que sí se cumplen (el backend está en CERO archivos de producción over-limit, y eso vale porque
  se sostiene).
  **El criterio que SÍ aplica: un archivo de test cubre UN módulo. Cuando cubre tres, se parte
  por módulo — no por líneas.** Un archivo de 600 líneas sobre un solo módulo está bien; uno de
  180 que toca tres está mal aunque entre. Señales de partir, todas independientes del conteo:
  cubre módulos distintos · mezcla ejes (lo que el código HACE, lo que RECHAZA, cómo se lo
  INVOCA) · el padrón y los fakes crecen más que las aserciones. Molde: los cuatro archivos del
  puente candidato→empleado. ⚠️ **Los helpers `tests/_*.py` NO están exentos**: son código de
  apoyo, no aserciones, y mantienen sus 200. Detalle completo en `docs/ORDEN-Y-LEGIBILIDAD.md` §2.
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
9. Producción puede driftear de las migraciones — **verificar contra el catálogo vivo**. Si la sesión tiene MCP de Supabase habilitado, usarlo; si no, pedírselo a Franco.
10. Commits y push desacoplados: **no hay push a GitHub hasta que Franco lo decida**.
11. Preferir commits por sub-sesión sobre commits por tarea entera.
12. Cortar sub-tareas por módulo cuando hay división de archivos de por medio.
13. Diagnóstico pedido → devolver SOLO diagnóstico (read-only). Implementación pedida → escribir código, no otro diagnóstico.
14. **Cada repo nuevo es un repo más a portar a asyncpg** (hoy son **69** archivos en `repositories/`). Priorizar wires sobre repos existentes; repo nuevo → moldearlo sobre `migracionAWS/empleado_repo_NEW`.
15. **Toda sesión que cambia algo escribe su entrada en `docs/BITACORA-CAMBIOS.md` ANTES de terminar.** Si la sesión termina sin su entrada, la sesión no terminó.

---

## Modelo de roles funcionales (COMPLETO)
Tres roles en `utils/permisos.py`:
- **admin_rrhh** — lectura + escritura en todo.
- **gerencia_lectura** — lectura en todo, escritura en nada.
- **mandos_medios** — lectura + escritura solo en VACACIONES y AUSENCIAS; sin acceso al resto.
- Rol desconocido / None → **fail-closed**.

Núcleo: `puede(rol, seccion, accion)`, `require_permission(seccion, accion)` (dependency factory → `AppError(..., "FORBIDDEN", 403)`). Enum `Seccion` (28 valores). `MANDOS_MEDIOS_SECCIONES = frozenset({VACACIONES, AUSENCIAS})`. **204 gates `Depends(require_permission(...))` en 61 routers.** *(Recontado el 12/8/2026.)* Espejo front en `frontend/services/permisos.ts`, **hoy verificado por `tests/test_espejo_permisos.py`** (secciones, acciones, roles y `MANDOS_MEDIOS_SECCIONES`, con guarda de mínimo). Sidebar filtra `NAV_GROUPS` por permiso, AuthGuard gatea por ruta, `useCanWrite` oculta botones de escritura.

✅ **La divergencia sidebar ↔ guard de ruta ya NO es manual-y-a-ciegas:** `components/layout/nav-config.test.ts` compara `NAV_GROUPS` entero contra `seccionDeRuta` de `permisos.ts`, con guarda de mínimo. Un ítem nuevo del menú sin su mapeo de ruta (o al revés) rompe el test. **Lo que sigue siendo espejo manual es `permisos.ts` ↔ `permisos.py`** — eso no tiene test.

**Decisión de producto (NO reabrir):** todo usuario, sin importar rol, accede a TODAS las empresas. No existe "usuario limitado a ciertas empresas".

---

## 🔒 Patrón de barrera de empresa (REGLA PERMANENTE — Fase 2)

**Todo endpoint que reciba un id de recurso de afuera valida que ese recurso sea de la empresa del request.** Sin esto, un UUID ajeno entra igual y la operación se ejecuta sobre él. Es la regla que más fácil se rompe al agregar un módulo: el gate de permisos (`require_permission`) NO alcanza — dice *qué podés hacer*, no *sobre qué fila*.

### Dónde va el filtro
- **Forma A (preferida):** el repo acepta `empresa_id` y el filtro va **en el WHERE de la query**. Una sola ida a la base, imposible de saltear. Es lo que hace `_with_empresa(q, empresa_id)`.
- **Forma B (solo si el repo no lo acepta):** traer la fila y **comparar en el service**. Más caro y más fácil de olvidar; si tocás ese repo, migralo a Forma A.

### El 404 es idéntico, siempre
"No existe" y "es de otra empresa" devuelven el **mismo status, el mismo `code` y el mismo mensaje**. **Nunca un 403.** Un 403 (o un mensaje distinto) confirma que el recurso existe y que es de otro — es un oráculo de enumeración. El literal canónico vive en **`services/_empleados_utils.py::empleado_or_404`** (`"Empleado no encontrado"` / `EMPLEADO_NOT_FOUND` / 404): **no lo dupliques**, delegá, así el mensaje no puede divergir.
> Mismo criterio en `_oauth_state.consumir` (los cuatro motivos de rechazo salen por un `AppError` único) y en `_resolver_empresa_id` (un `X-Empresa-Id` inexistente se descarta en silencio, sin status propio).

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

### 🔴 LA ÚNICA EXCEPCIÓN A ESTA REGLA — `services/_alcance_mandos.py`

**Decisión de producto (2/8/2026): un empleado puede tener superior de OTRA empresa del grupo, y
para `mandos_medios` el `manager_id` REEMPLAZA al filtro de empresa** — en lectura Y en escritura.
Lo justifica que el `manager_id` es un vínculo más fuerte que la empresa: la empresa dice de qué
sociedad cobra alguien, el `manager_id` dice quién responde ante quién, que es la pregunta que el
ownership contesta.

**Está concentrada en UN módulo con nombre propio para que se lea como excepción y no como patrón
a copiar.** `empresa_efectiva(empresa_id, rol)` devuelve `None` para `mandos_medios`; y **la misma
función que suelta la empresa verifica la invariante de la que eso depende**, fail-closed: para
`mandos_medios` el ownership NUNCA puede resolver a "sin restricción". Antes, un fallo ahí quedaba
contenido por el `.eq("empresa_id")`; sin ese filtro, `(None, False)` significaría **la tabla
entera de todas las empresas**. Soltar la empresa y chequear la invariante viven juntas por eso.

⚠️ **NO toca `_ownership_filter.py`** (del que dependen 13 endpoints) ni su contrato de tupla
`(ids, vacio)`: la intersección nunca ocurrió ahí adentro, ocurre en el WHERE como dos predicados
independientes, y `ids_subordinados` ya era ciego a la empresa. Alcanzó con no pasarle el
`empresa_id` al repo.

### Ownership ≠ empresa (y solo aplica en dos secciones)
Son **dos ejes independientes que se componen por INTERSECCIÓN** — el ownership nunca reemplaza la empresa.
- **empresa** → frontera multiempresa. Aplica a TODO.
- **ownership** (`services/ownership.py`, `_ownership_filter.py`) → dentro de mi empresa, a qué empleados llego por mi rol. **Solo aplica en `VACACIONES` y `AUSENCIAS`** (`MANDOS_MEDIOS_SECCIONES`). En el resto de las secciones solo llegan `admin_rrhh` y `gerencia_lectura`, para quienes no restringe: **agregarlo ahí es código muerto que aparenta seguridad.** Por eso onboarding usa `ensure_empleado_de_empresa` y no `ensure_empleado_visible`.
- **Todo filtro nuevo se compone con ownership por INTERSECCIÓN** (`_ownership_filter.resolver_filtro_empleados`), nunca lo reemplaza. Un filtro que lo esquive con un `.eq()` propio no da error: devuelve datos de empleados que ese rol no debería ver.

### ⚠️ El router pasando `empresa_id` NO prueba nada
Hay que **seguir el parámetro hasta la query**. Un router que recibe `empresa_id` y lo pasa a un service que lo acepta y lo ignora se lee como seguro y no lo es. **Este falso positivo apareció 3 veces en el barrido de Fase 2** (offboarding, horas, onboarding_templates). Auditá de la query hacia arriba, no del router hacia abajo.

### 🚨 Fakes de test que HONRAN `empresa_id`
Un fake cuyo `find_by_id(id, empresa_id)` **acepta el parámetro y lo ignora** da **verde falso**: el test pasa sin validar nada, y es exactamente el bug que se quería cubrir. Es el caso #1 de "Un test solo prueba lo que el fake puede desmentir" — leer esa sección entera.

### `.single()` vs `maybe_single()`
**Usar `maybe_single()` salvo que la fila esté garantizada.** `.single()` **lanza** con 0 filas en vez de devolver `None` → el `return None` de abajo queda **inalcanzable** y el endpoint da **500 donde el service pretendía 404**. Pasó en `area_repo` y `empresa_repo`; ambos corregidos. Los `.single()` que sobreviven son legítimos: post-`upsert` (`nomina_repo`) y lookups de auth donde la fila existe por construcción.

---

## Audit log app-level (COMPLETO)
Captura **app-level** (no triggers DB). Tabla `auditoria` (mig 024+058): `id, tabla, registro_id, accion (INSERT|UPDATE|DELETE), datos_anteriores JSONB, datos_nuevos JSONB, usuario_id, ip, user_agent, created_at, empresa_id, entidad, evento`. Inmutable. Triggers DB viejos dropeados en 058.

`AuditService.registrar(...)` keyword-only, síncrono, **traga todo error** (no tumba la operación de negocio). `audit_repo` (insert + listar con filtros/paginación). Payloads canónicos en `services/_audit_payloads*.py` (`_audit_payloads.py` · `_rrhh` · `_costos` · `_usuarios` · `_ev` · `_cesion`).

### 🔴 REGLA — UN DIFF NUNCA REGISTRA CAMPOS DERIVADOS DE JOINS

Durante meses, **cada edición de un empleado grabó un cambio que no ocurrió**: `area_nombre: "SALUD" → null`, `empresa_nombre: "..." → null`. **93 de 113 eventos de producción eran exactamente eso y nada más**, y la pantalla se lo afirmaba al usuario sobre empleados reales.

**La causa:** el diff comparaba los `*Response` completos. `prior` sale de un `SELECT` **con joins** (nombres resueltos) y `nuevo` de un `UPDATE ... RETURNING` **sin joins** (nombres en `null`). Los campos derivados —`area_nombre`, `empresa_nombre`, `empleado_nombre`, `manager_nombre`, `tipo_nombre`— no son datos del registro: son resultado de **cómo se lo leyó**. Tampoco van los **calculados** (p. ej. el `estado` de una vacación, que sale de las fechas: cambia solo con el paso del tiempo y se leería como una edición que nadie hizo).

> ✅ **Verificado en producción (28/7/2026): los 94 eventos con el fantasma están todos fechados el 14/7, ninguno posterior al fix.** No se están generando nuevos. Los viejos quedan: `auditoria` es inmutable por diseño.

### 🚨 POR QUÉ SE EXCLUYE (`sin_derivados`) EN VEZ DE ENUMERAR — la parte que hay que entender

Un **alta** o una **baja** FOTOGRAFÍAN un estado, y ahí una lista curada (`_CAMPOS_X`) alcanza: se elige qué vale la pena guardar. Un **UPDATE** responde otra pregunta —*¿qué cambió?*— y ahí **una lista curada MIENTE POR OMISIÓN**: si alguien edita un campo que no está en la lista, el log dice que no pasó nada.

Concreto: `_CAMPOS_EMPLEADO` cubre **7** campos, y `empleados` tiene **29 columnas más editables** (`manager_id`, `dni`, `email_corporativo`, `fecha_ingreso`…). Enumerar habría dejado de registrar esas ediciones **en silencio** — que en un log de auditoría es **peor** que el fantasma que el cambio vino a sacar.

**Por eso los diffs usan `sin_derivados(obj, DERIVADOS)`: una columna nueva queda auditada sola, y lo único que hay que declarar es lo que NO es una columna.** `sin_derivados` vive en `_audit_payloads.py` y **se IMPORTA** desde los módulos hermanos (a diferencia de `_subset`, que se duplica): define qué entra en un diff, y dos copias que se separen darían dos criterios distintos sobre lo mismo.

✅ **Auditoría de nómina silenciosa — ARREGLADA (Fase 0.1).** `_audit_payloads_rrhh.py` pasaba el literal `"lote_nomina"` en `registro_id` (uuid) → el insert fallaba → `AuditService.registrar` tragaba la excepción → evento perdido. Ahora usa `str(uuid4())` por llamada (id de EVENTO, no de recurso).

**UI:** `/auditoria` (admin/gerencia) + `components/ui/Pagination.tsx`. El detalle **resuelve los nombres al renderizar** (commits `5e8f44c` + `3ad82a4`): el diff guarda `area_id`, la pantalla muestra el área. `auditoria.tabla` = `entidad` (espejo 1:1) — legacy, drop futuro sin traducción.

**Regla:** al auditar una importación → **un evento por lote**, nunca fila por fila.

---

## Importación CSV — molde para imports nuevos (COMPLETO)
Dedup por DNI. Dos flujos, ambos gateados `Seccion.IMPORTACION + WRITE` (solo admin_rrhh) y ambos bajo la franja de rate limit `scope="import"` (10/hora compartido).

**Flujo 1 — Nómina de empleados** (single-shot, sin preview): `routers/importacion_nomina_empleados.py` → `nomina_empleados_service.py` + `_nomina_empleados_transforms.py`. CSV 27 col, `;`, `latin1`. Idempotente, no aborta ante error de fila, clasifica en 3 grupos.

**Flujo 2 — Nómina de costos** (preview + confirmar): `routers/importacion_nomina.py` → `nomina_csv_service.py::parse_nomina_csv` + `nomina_import_repo.py`. Resuelve DNI→empleado, detecta duplicados por `(anio, mes)`.
> **Este Flujo 2 es el molde de la base de import compartida.**
> ✅ **La auditoría que este documento le marcaba como faltante ESTÁ**: la emite `services/nomina_import_service.py`, UN evento por lote (ver "Resueltos" abajo).
> ⚠️ **El reader XLSX ya existe** — `services/_import_excel.py`, escrito para el import de objetivos del bloque H—, **pero este flujo sigue siendo solo CSV**: nadie los cableó. Enchufarlo es lo que queda de la "base de import compartida".

---

## 🔎 Filtros y exports (Bloque B) — REGLAS PERMANENTES

**El requisito de fondo:** que RRHH llegue a **cualquier corte de información sin pedirle nada a desarrollo**. El inventario capa por capa está en **`docs/MATRIZ-FILTROS.md`** — actualizarlo al cerrar cada tanda.

### Las cuatro invariantes del bloque
1. **Si el filtro afecta al export, va SERVER-SIDE — una sola implementación.** Filtrar en el cliente y también en el backend son dos copias de la misma regla que divergen sin avisar. Y el export no ve el array del cliente: si el filtro vive solo ahí, **el archivo sale con más filas de las que se ven en pantalla**.
2. **El endpoint de export acepta los MISMOS Query que el list.** (Con dos excepciones legítimas, abajo.)
3. **Todo filtro se compone con ownership por INTERSECCIÓN**, nunca lo reemplaza.
4. **`page` se resetea a 1 al cambiar cualquier filtro.** El hook NO conoce `page`: recibe `onFiltroChange` y la página lo cablea a `() => setPage(1)`.

### Backend — helpers compartidos (REUSAR, no reimplementar)
- **`repositories/_scope_filtros.py`** (era `_area_scope.py`) — resuelve "qué empleados caen bajo un filtro de área o de proyecto", con lookups batch, nunca uno por fila. **Existe como módulo aparte porque la decisión de acotar o no por empresa DIFIERE entre funciones:**
  - `empleados_de_area(area_id, empresa_id=None)` — acotar por empresa es correcto cuando la entidad y sus empleados pertenecen a UNA empresa (capacitaciones, inventario).
  - `proyecto_ids_con_area(area_id)` y `empleados_de_proyecto(proyecto_id)` — **NO acotan por empresa, a propósito**: un proyecto de la empresa A puede tener gente de la B (el modelo lo soporta, por eso `proyecto_asignaciones` lleva `empleado_empresa_id`). Agregar ese `.eq` "por consistencia" dejaría el conjunto vacío y el filtro devolvería **cero** sin ningún error.
  - **Definiciones de producto que hay que conocer antes de tocarlas:** "proyectos del área X" = proyectos donde trabaja al menos alguien de X (`proyectos` no tiene columna de área) · cuenta asignaciones **activas e inactivas** · un proyecto sin nadie asignado **no aparece bajo ninguna área** (es la definición, no un bug) · **no hay ventana temporal** en el filtro por proyecto (las 19 asignaciones de producción tienen `fecha_desde`/`fecha_hasta` en NULL, así que la regla con ventana devolvería lo mismo y nadie podría probarla). **Disparador para revisarlo: que empiecen a cargarse esas fechas.**
- **`repositories/_rango_fechas.py::aplicar_rango(q, desde, hasta)`** — vacaciones y ausencias. 🔴 **Semántica de SOLAPAMIENTO, no de contención:** "las vacaciones de marzo" incluye una licencia del 25/2 al 5/3. Con contención esa fila desaparecería del listado **y del total**, que es peor: un reporte de ausentismo del mes dejaría afuera justo los casos que cruzan el borde. Y es la **misma** semántica que `services/_periodo_utils._solapa` usa para decidir si una solicitud cae en un período cerrado — dos definiciones de "pertenece a este período" en el mismo módulo sería un bug esperando. Rangos abiertos salen gratis (las dos mitades del predicado son independientes). ⚠️ Un rango invertido **no se rechaza**: lo tiene que impedir la UI con `min`/`max`, no el repo adivinando la intención.

### Frontend — el molde
- **`components/features/shared/filtros.ts`** — el molde del hook `useFiltros<Modulo>` (sacado de AuditFilters, el precedente más rico) + `etiquetaArea` (en modo consolidado sufija con el nombre de la empresa: las áreas son POR empresa y dos empresas pueden tener una "Sistemas" cada una) + `setFiltro` (normaliza `""` y `[]` a `undefined` en UN lugar) + `filtrosActivos`.
  - **a.** Un objeto de filtros **tipado** por módulo, que viaja entero de la UI al service. **Nunca posicionales.**
  - **b.** El **MISMO tipo** lo consumen el listado y el export, y los dos arman sus query params con la **MISMA** función de traducción. Es lo que hace **estructuralmente imposible** que un filtro quede en uno solo de los dos.
- **`components/ui/FiltersBar.tsx`** (128 líneas) — presentacional, controlado, sin estado ni fetch ni debounce. **5 tipos:** `select` · `search` · `date` · **`daterange`** (emite un objeto) · **`multiselect`** (checkboxes, *no* `<select multiple>`: el nativo exige ctrl/cmd+click, que es justo lo que un usuario no descubre solo). Si algún filtro llega a decenas de opciones, eso pide un combobox con búsqueda — control distinto, no un ajuste de este.
- Hooks vivos: `useFiltrosEmpleados` · `useFiltrosVacaciones` · `useFiltrosAusencias` · `useFiltrosProyectos` · `useFiltrosAsignacionesCap` · `useFiltrosAsignacionesInv` · `useFiltrosEvaluadosResultados`.

### Superficie de filtros hoy (verificada por introspección de `app.routes`, 12/8/2026)

**26 endpoints con parámetro `formato`** (= exports), inventario del 12/8/2026 — **no
reverificado en detalle esta sesión, pero el conteo de `@limite_export` mide 28 el 19/8**
(formación/import sumó un router de import que NO exporta, así que la diferencia no es 1:1;
antes de confiar en el "26" para una tarea puntual, remedir por introspección de `app.routes`
como indica el propio método de abajo). **18 aceptan además filtros propios**; los
otros 8 exportan el listado entero (empresas, equipo, offboarding, onboarding, onboarding/
templates, períodos, usuarios y el export de un reporte por id). Los que llevan filtros:

| Módulo | Filtros del listado = del export |
|---|---|
| empleados | area · proyecto · estado · es_lider · search · sin_manager |
| vacaciones | area · proyecto · empleado · estado · **fecha_desde/hasta** |
| ausencias | area · proyecto · empleado · tipo · **fecha_desde/hasta** |
| auditoría | entidad · evento · usuario · registro · fecha_desde/hasta |
| capacitaciones (asignaciones) | area · capacitación · empleado · estado |
| inventario (asignaciones / ítems) | area · empleado / estado |
| objetivos | estado · prioridad · responsable |
| evaluaciones (evaluados de un lote) | perfil · sector · con_nota · **proyecto** |
| costos/nómina | anio · mes |
| proyectos (listado) | area · estado |
| **clientes** | incluir_inactivos (🔴 **no hay filtro de empresa**: el catálogo es global) |
| **horas por cliente** | anio · mes — 🔴 **obligatorios**, no opcionales: sin período la consulta sería la tabla entera |
| vacaciones pendientes | area · empleado · proyecto |
| capacitaciones (catálogo) | solo_activos |
| vacantes / candidatos | estado / clasificación · sin_vacante |
| áreas | empresa |

### 🔴 DOS TESTS ESTRUCTURALES — son REGLA PERMANENTE, no tests de una feature

Los dos **barren la superficie entera automáticamente**, así que **cualquier export nuevo queda cubierto sin tocar el test**. Los dos llevan **guarda contra el falso verde**.

**1. `tests/test_paridad_list_export.py` — invariante list ↔ export.**
Las rutas salen de **`app.routes`** (introspección de FastAPI), no de una lista escrita a mano. Verifica en las dos direcciones: que el export acepte todo lo que el listado filtra (si no, **el archivo trae más filas de las que se ven en pantalla**, sin error y sin aviso), y que el export no tenga filtros propios (serían inalcanzables desde la UI). Las **dos únicas** diferencias legítimas: `formato` (solo export — es cómo sale el archivo, no un filtro) y `page`/`page_size` (solo listado — **el export NO se pagina, por diseño**).
- **Si un par difiere con motivo legítimo se declara en `_EXPORTS_SIN_LISTADO` CON su razón — nunca se saca el módulo del barrido.** Hoy hay 1: `/api/reportes/{reporte_id}/exportar` (exporta un reporte ya generado por id, no un listado).
- Guardas: `>= 8` exports y `>= 8` pares detectados · ningún export huérfano sin excepción declarada · **ninguna excepción que apunte a una ruta borrada** (una excepción muerta es ruido que oculta el próximo caso).

**2. `tests/test_limite_export.py::TestTodosLosExportsChequean` — barrido del límite de export.**
Barre los **20 services con export** y verifica que cada uno (a) importe `verificar_limite_export` y (b) **lo invoque en el cuerpo de `exportar`** (importarlo no alcanza — se comprueba con `inspect.getsource`). Sin él, el próximo export nace sin control y nadie se entera hasta que un usuario recibe un archivo incompleto.
- Excepciones declaradas con razón: `reporte_export_service` (reporte puntual por id) y `reportes/_reporte_auditoria` (acotado a un mes por construcción, conserva un truncado **declarado** con nota en el archivo).
- Guarda: `assert len(EXPORTS) >= 20` (medido el 19/8/2026; entraron `perfil_puesto_service` y `recategorizacion_service`). ⚠️ **`EXPORTS` sigue siendo una lista a mano** (a diferencia del barrido de paridad, que descubre por `app.routes`): un export nuevo entra al barrido solo si alguien lo agrega. Pasarlo a introspección es el ítem **K2** de `docs/ORDEN-SESIONES-CODIGO.md`.

> Hay un **tercero, en el front**: `components/layout/nav-config.test.ts` compara `NAV_GROUPS` contra `seccionDeRuta` de `permisos.ts`, también con guarda de mínimo (`>= 20` ítems). Cubre al próximo módulo que se agregue al sidebar.

### `LIMITE_FILAS_EXPORT = 20000` — y por qué (`services/_limite_export.py`)

Antes cada export pedía `page_size=100000` y armaba el archivo con lo que entrara: un pedido más grande salía **incompleto y sin ninguna señal**. Ahora un pedido que lo supera devuelve **422 `EXPORT_DEMASIADAS_FILAS`** con un mensaje para alguien de RRHH (dice cuántas filas dio la consulta, cuál es el máximo, y que use los filtros).

> 🔴 **ERA 5.000 HASTA EL 13/8/2026 Y HOY SON 20.000. Este documento afirmó "5.000" hasta el
> 19/8 — seis días de más.** El archivo tiene el detalle medido; acá va lo que hay que saber.
> **El techo real de un export no son las filas sino el TIEMPO, pero cuál de los techos corta
> también estaba mal.** Se decía que era el timeout httpx de 30 s del cliente de Supabase.
> Medido sobre 27.597 filas de auditoría: traer las filas **4,2 s**, CSV **4,1 s**, Excel
> **39-53 s**, PDF **126 s**. O sea **la base aporta el 8% y el 92% es construir el archivo**:
> ese timeout no llega a dispararse nunca. El que rige es **el de la función de Vercel, 300 s**.
> **De dónde sale el 20.000:** de la tasa real de eventos (0,174 por empleado por día, medida en
> producción), proyectada a 1.005 colaboradores → ~16.000 por trimestre. El **5.000 anterior no
> alcanzaba ni para UN MES** a esa escala, y auditoría —el módulo del que RRHH exporta histórico—
> era el único que a escala no se podía exportar nunca. Ese es el bug que el cambio cerró.
> ⚠️ **Lo que 20.000 NO cubre, y hay que decirlo: el AÑO entero** (~64.000 eventos, que en PDF
> pasan los 300 s). Un export anual **no se arregla subiendo el número**: pide export asíncrono o
> paginado por trimestre desde la UI. Sigue anotado como deuda.
> ⚠️ **El formato pesa más que las filas: 31× entre CSV y PDF** sobre el mismo conjunto. El
> límite es uno solo para los tres y está calibrado para que entre el más lento.

Es **constante de módulo, NO variable de entorno**: subirlo exige revisar los techos de tiempo, y eso es una decisión, no configuración.

⚠️ **Alcance real, para no venderlo de más.** En los exports **paginados** el total llega por `count="exact"` y solo se traen las filas del tope: ahí el control actúa **antes** de cargar nada grande. **Hoy son ocho**: empleados, vacaciones, ausencias, auditoría y —desde la sesión 2 de paginación (14/8/2026)— capacitaciones/asignaciones, inventario/ítems, inventario/asignaciones y proyectos.
> 🔴 **EL ÚNICO QUE TODAVÍA NO PAGINA ES `objetivos`** (este documento decía "cuatro" hasta el 19/8: el catálogo de formación, inventario ítems, inventario asignaciones y objetivos — los tres primeros ya salieron). Su repo no expone un conteo, así que el chequeo corre sobre la lista ya traída. **Y tiene una vuelta propia que hay que resolver al paginarlo:** el archivo trae padres E hijos, así que el tope se cuenta sobre el árbol **aplanado** (`_objetivos_arbol.contar_con_hijos`), no sobre las raíces que `find_all` devuelve — un `count="exact"` sobre la tabla contaría las dos cosas mezcladas. Está anotado en `schemas/objetivo.py`, al lado del campo.

---

## Evaluaciones de desempeño — resultados importados (COMPLETO, EN PRODUCCIÓN)

**Qué es:** `/evaluaciones` muestra **métricas de resultados calculados afuera**, importados por CSV. **El sistema NO evalúa.**

✅ **Migraciones 078 y 079 CORRIDAS en producción.** Verificado contra el catálogo (28/7/2026): **1 lote (Julio 2026, empresa DOSUBA), 10 evaluados, 307 resultados, 0 equivalencias.**

### El modelo (078/079)
Las tablas `ev_*` no sirven para esto y están **vacías en producción**. Las nuevas:
- `evaluacion_lotes` — período, `UNIQUE(empresa_id, periodo)`. Columnas: `id, empresa_id, periodo, importado_por, created_at`.
- `evaluacion_evaluados` — uno por lote×persona, `empleado_id`/`nota_final` NULLABLE, `perfil` (lider|general) + datos crudos del CSV. FK `lote_id → evaluacion_lotes ON DELETE CASCADE`.
- `evaluacion_resultados` — uno por evaluado×tipo×competencia. FK `evaluado_id → evaluacion_evaluados ON DELETE CASCADE`.
- `evaluacion_equivalencias` (079) — texto del CSV = empleado, confirmado a mano. **Cuelga de `empresa_id`, NO de `lote_id` → NO cascadea.** Sobrevive al borrado del lote (mapeo aprendido, se reaplica en el próximo import).

Las hijas **no llevan `empresa_id`** — se alcanza por `lote_id`. **Invariante: el matcheo resuelve el empleado SIEMPRE dentro de la empresa del lote, nunca global.** `competencia` va como texto, no catálogo.

**Por qué no se reusó `ev_*`:** `ev_instancias` tenía `UNIQUE(ciclo_id, empleado_id)` pero el dato real son hasta 6 filas por evaluado (una por tipo de evaluador); `evaluador_id` era FK a persona, y el CSV trae un tipo (`AUTOEVALUACION`/`PAR`/…) sin identidad; `puntaje_global` se calculaba, acá viene calculado de afuera. ✅ **El módulo `ev_*` ya no existe: código borrado en J5a (17 archivos, 19 endpoints) y las 5 tablas dropeadas por la migración 112 en J5b.** Queda como explicación de por qué este módulo nació aparte.

### El formato (no cambia — nos adaptamos)
Dos CSV `;`, **encoding distinto entre sí** (notas UTF-16, desglose UTF-8), números con espacios adelante. A·Notas finales: 8 col, una fila por evaluado. B·Desglose: 7 de identidad + `TIPO EVALUACION` + 15 competencias. **No traen DNI ni legajo, solo apellido y nombre.** El lector detecta BOM explícito y falla claro si no puede determinar encoding (el decode viejo caía a `latin-1` y decodificaba UTF-16 a basura en silencio).

**Dos perfiles:** líder (14 competencias) y general (9). El perfil se deriva de las 5 competencias exclusivas de líder presentes en el archivo (`VISION ESTRATEGICA`, `ORGANIZACION`, `CONDUCCION EQUIPOS`, `PLANIFICACION`, `COMUNICACION`) — **NO de `es_lider`** (está 0/19).

### Matcheo
Apellido+nombre normalizado (sin acentos), desempatado por superior contra `manager_id`. Estados: `resuelto` · `ambiguo` (revisión humana) · `sin_candidato` (`empleado_id=null`, válido, no error). **Nada de fuzzy por similitud.**
🚨 **`manager_id` está 0/19 en producción** → el desempate no discrimina hoy, todo cae en "resuelto". Degrada bien, se activa cuando carguen jerarquía. **Excede evaluaciones: el ownership de mandos_medios depende de esto.**

### Pipeline
`preview` (parsea+resuelve, **no persiste**, avisa si pisa período) → revisión humana → `confirmar` (**no re-parsea**: persiste lo aprobado, pisa el período previo vía `delete_lote`+CASCADE, un evento de auditoría por lote).

✅ **Bug de `confirmar()` — pérdida de datos, ARREGLADO (Fase 0.2).** El orden ahora es: crear lote nuevo con período TEMPORAL (`"{periodo} ::importando::"`, no choca la UNIQUE) → persistir evaluados+resultados → **verificación POR CONTEO** (`len(guardados)==esperados`; un insert parcial silencioso se detecta acá — no basta "no hubo excepción") → borrar el viejo (único paso destructivo, al final) → renombrar el nuevo al período real. Si algo falla antes del borrado, el viejo queda intacto. `crear_evaluados`/`crear_resultados` levantan `AppError` si el insert no devuelve todas las filas. La única ventana restante (fallo entre borrar-viejo y renombrar) deja el nuevo completo con nombre temporal → recuperable a mano, logueado a ERROR, no es pérdida.

### Métricas
Agregados en Python puro (`_evaluacion_metricas.py`), no SQL (~300 filas por lote no justifica vistas/RPC). ⚠️ Competencias en DOS tablas separadas (líder/general), cada una con su `n` — **nunca en el mismo ranking** (son 2 evaluaciones distintas, mezclarlas da resultado falso). Excluyen autoevaluaciones. La métrica más valiosa: **brecha de autopercepción** (auto vs promedio de terceros).

### Historial de importaciones (COMPLETO)
Tab **"Importaciones"** en `/evaluaciones` con lista de todos los lotes, multi-selección y borrado.

**Backend:** `GET /lotes` en modo consolidado devuelve **todos los lotes de todas las empresas**, enriquecido vía `repositories/_evaluacion_lotes_enrich.py` (empresa, usuario, conteo) **sin N+1** (un lookup batch por dimensión) · `delete_lote(lote_id, usuario_id)` **desacoplado de la empresa activa**: valida contra `lote.empresa_id` (autoritativo), no contra el header; audita con snapshot **antes** del CASCADE · `POST /api/evaluaciones/resultados/lotes/eliminar` (bulk) con éxito parcial clasificado (patrón `proyectos.asignar_bulk`), un evento de auditoría por baja efectiva · el router tiene gate READ por default, así que el DELETE y el bulk llevan dependency WRITE inline propia.

**Frontend:** Tab solo `canWrite`. `HistorialImportaciones.tsx` (orquestador) + `HistorialTable.tsx` (presentacional) + `useHistorialImportaciones.ts`. **El borrado NO depende del selector de empresa del sidebar**: usa `fetchLotesHistorial()` que fuerza `X-Empresa-Id: "todas"`.

✅ **`EliminarLoteButton.tsx` se BORRÓ el 2/8/2026** (74 líneas, 0 callers verificados en todo el front). El borrado real de un lote lo hace `HistorialImportaciones`.

✅ **Fuga entre empresas — CERRADA (Fase 2, commit `bd95e98`).** Los 7 endpoints del módulo que reciben `lote_id` validan por **ownership del lote**: la empresa sale de `lote.empresa_id`, no del header.

### Entrega 2 — descarga de archivos originales (PENDIENTE — es el D2 del Plan)
Hoy **no se puede**: el import parsea y descarta los bytes (cero `storage.upload`, `evaluacion_lotes` sin columna de ruta). Requiere: (1) guardar los CSV en Storage al confirmar, (2) migración con columna(s) de ruta, (3) endpoint con `create_signed_url`. La infra de Storage ya existe (5 módulos la usan).
🚩 **Solo hacia adelante.** El lote de Julio 2026 ya existe sin archivos — no se recupera.
⚠️ **Definir antes si Storage queda en Supabase o pasa a S3**, o se hace dos veces.

---

## Reportes y KPIs (Fase 1 — completo, PERO leer el aprendizaje crítico)

Catálogo de reportes descargables (PDF/Excel) + KPIs de dashboard. **14 reportes en el catálogo del front**: los 11 de Fase 1 (headcount, altas/bajas, distribución, rotación, listado vac/aus, ausentismo, saldos de vacaciones, costos, presupuesto, capacitación, auditoría) + `vacantes`, `onboarding` y `anual_consolidado`, que ya existían.

### 🔴 "COMPLETO Y EN PRODUCCIÓN" NO QUERÍA DECIR "FUNCIONABA"
**Seis de los once reportes de Fase 1 se entregaron como completos y NUNCA funcionaron en producción.** Pedían columnas que no existen (`motivo` por `motivo_egreso`, `progreso` en una tabla que no la tiene) o embeds ambiguos que PostgREST rechaza con **PGRST201**. **Los 799 tests pasaban**, porque el fake de Supabase implementa `select(*a, **k)` **ignorando el argumento**: acepta cualquier spec, exista o no la columna. Los tests no mentían sobre la lógica; **no miraban los nombres**. Corregido en el Bloque C.

### 🛡️ `tests/_postgrest_schema.py` — lo que cierra la clase de bug
Arreglar las siete instancias no cerraba nada: el próximo reporte nacía con el mismo agujero. Lo que la cierra es este validador, que **lee `db/schema.sql` y valida un spec como lo haría PostgREST**, detectando las dos fallas vistas:
- **columna inexistente** → PostgREST responde 400 42703.
- **embed sin FK nombrada** → 300 **PGRST201**, cuando hay MÁS DE UNA relación entre las dos tablas. Es la traicionera: `areas(nombre)` desde `empleados` se lee perfecto y es ambiguo, porque además de `empleados.area_id → areas` existe `areas.responsable_id → empleados`. **Basta con que alguien agregue una FK para que un embed que venía andando se vuelva ambiguo**, y el único síntoma sea un reporte en blanco. Fix: nombrar la FK → `empleados!costos_nomina_empleado_id_fkey(...)`.

**`tests/test_reportes_columnas.py`** ejecuta **cada generador contra ese validador**, y **cada uno corre DOS veces, con y sin `area_id`** — no es redundancia: el filtro de área arma joins `!inner` y embeds distintos con f-strings, así que una sola pasada deja la mitad de las queries sin mirar (el bug de ausentismo vivía justo ahí).

**Lo que `_postgrest_schema` NO valida:** tipos, filtros, RLS ni existencia de filas. Solo nombres y relaciones — que es lo que el fake no puede ver.
> ⚠️ **Sigue habiendo punto ciego** para queries construidas fuera de los generadores barridos. **Toda query con `select` anidado que no pase por `test_reportes_columnas.py` hay que verificarla en producción tras el deploy.**

### 🔑 PRINCIPIO — Vista vs Acción (evita la confusión recurrente del selector de empresa)
- **El selector de empresa del SIDEBAR es SOLO VISUAL.** Filtra lo que se MIRA (listados, dashboard). NO gobierna acciones.
- **Las ACCIONES reciben la empresa como PARÁMETRO EXPLÍCITO** (del formulario/body), nunca del header `X-Empresa-Id`. Ejemplos: generar un reporte (empresa del form), borrar un lote de evaluaciones (empresa del lote), colgar un adjunto (empresa de la entidad padre).
- Regla mental: **mirar = sidebar manda · hacer = el form/parámetro manda.**
- **Reportes = ACCIÓN** → empresa+área salen del form, ignora el sidebar. **Dashboard = VISTA** → respeta el sidebar. Son opuestos a propósito; no contagiar un patrón al otro.
- ✅ **La violación que este documento marcaba en `services/_costos_write.py` está CERRADA** (6/8/2026). Los dos caminos de escritura auditan con la empresa de la ENTIDAD: `nomina.empresa_id` (línea 48) y `presupuesto.empresa_id` (línea 86), con el porqué escrito en el docstring del módulo. El `empresa_id` del header se recibe y se declara explícitamente como "solo VISTA".

### Detalle de los reportes
Dotación: headcount, altas/bajas (con listado nominal), distribución por seniority/modalidad/turno (nulos → "Sin especificar"), rotación por motivo.
Vac/aus: listado combinado, ausentismo por área (total + injustificado, tasa sobre la base de días hábiles configurada —migración 085—, con nota visible que dice el valor usado), saldos de vacaciones (asignados − tomados con `cancelada=false`; solo `tipo="vacaciones"` resta saldo; saldo negativo → flag `excedido`, no se oculta).
Costos/otros: masa salarial, presupuesto vs real (desvío + % ejecución), capacitación por área, auditoría/trazabilidad (resumen legible, NO vuelca el JSONB crudo).

Todos: filtro período + empresa + área (empresa/área del FORM). El área se filtra por join a empleados donde la tabla no tiene `area_id`. `anual_consolidado` no lleva área (transversal por diseño). El motor `build_export` es genérico.

### KPIs de dashboard (9)
Ausencias activas hoy, % ausentismo del mes (base de días hábiles configurable, nota visible con el valor usado), masa salarial + variación vs mes anterior, distribución por seniority/modalidad, cumpleaños/aniversarios del mes, y los 4 previos. El dashboard RESPETA el sidebar de empresa (es vista).

### Estructura
- `services/reportes/` — un submódulo por familia (`_reporte_dotacion` 124, `_reporte_costos` 128, `_reporte_vacaciones` 125, `_reporte_seleccion` 96, `_reporte_ausentismo` 82, `_reporte_movimientos` 63, `_reporte_auditoria` 60, `_reporte_capacitacion` 58, `_reporte_distribucion` 49) + `reporte_generators.py` como dispatcher/re-export (**27 líneas**) + `_common.py` (evita el ciclo dispatcher↔submódulos).
- `services/_kpi_helpers.py` / `_dashboard_kpis.py` — **cálculos compartidos entre KPIs y reportes** (base de días hábiles, que desde la mig 085 sale de `parametros_empresa`; distribución con "Sin especificar"). Un solo lugar, no duplicar.
- Front: `components/features/reportes/` (catálogo + card + selectores) y `components/features/dashboard/`. `reportes/page.tsx` quedó en **35 líneas**.
- El reporte adhoc con IA (`reporte_adhoc.py`, `claude-sonnet-4-6`) está OCULTO del catálogo (no borrado — patrón AIPanel). Reactivable en una línea. Su endpoint lleva rate limit propio (20/hora): cada request cuesta plata.

### 🚨 Dashboard resiliente (fail-safe por KPI)
`dashboard_service` calcula cada KPI/sección con un `_safe`: si UNO falla, los demás se devuelven igual y el fallido queda vacío + marcado en `errores`. NUNCA propaga. Al agregar un KPI nuevo, respetá este patrón.

---

## Otros módulos (referencia rápida)
- **Carga de horas (migraciones 102–107, TODAS CORRIDAS).** Dos superficies sobre `horas_proyecto`.
  - **Link público `/horas`** (front fuera de `(dashboard)`, sin AuthGuard) — el empleado se
    identifica **solo con DNI** (decisión de producto cerrada) y carga horas o una licencia.
    🔴 **Apagado por `HORAS_PUBLICO_ENABLED` (default `false`), y el flag gatea DOS piezas**: el
    router no se monta **y** las rutas salen de `PUBLIC_ROUTES`. Gatear las dos es lo que hace que
    se comporten como una ruta inexistente; solo desmontar el router cambiaría el 401 por un 404 y
    esa diferencia delataría al módulo. Encendido son **5 rutas públicas nuevas** (4 + las 4 base = 9).
  - **La identidad entre pasos NO es el DNI**: el paso 1 devuelve un **token opaco de 256 bits**
    persistido hasheado en `sesiones_horas`, TTL 30 min. Así los pasos 2+ se autentican con algo
    que el cliente no puede adivinar, y la debilidad del DNI queda confinada al paso 1 — que
    además tiene rate limit por IP **y** por DNI, rechazo único con piso de tiempo, y log de
    intentos en `intentos_identificacion` (**DNI en claro**: 8 dígitos hasheados se revierten en
    segundos y perder el valor forense no compra nada).
  - **Reglas de carga:** tope **12 h/día**, ventana de **30 días** hacia atrás, `cliente_id`
    obligatorio, `proyecto`/`tarea` texto libre. El doble-tap está cerrado por `idempotencia` +
    índice único parcial; la carrera entre cargas concurrentes distintas es **límite conocido
    declarado** (sin triggers ni transacciones vía PostgREST). La licencia sin `horas_contrato`
    asume 8 h y lo **avisa** en la respuesta.
  - **Vista interna "Horas por cliente"** (`/horas-por-cliente`, gate `Seccion.PROYECTOS`) —
    agrupa por cliente y empleado con período obligatorio, exporta y **borra**. Editar una carga
    NO está: revocaría la irreversibilidad, es decisión de producto, no una feature faltante.
  - **Catálogo GLOBAL de clientes** (`/clientes`, gate `Seccion.CLIENTES`) — ABM con **baja
    lógica**. 🔴 **Un cliente NO pertenece a ninguna empresa** (bloque L, migraciones 108/109):
    se ve y se edita con el sidebar en cualquier modo, y el nombre es único en TODO el sistema
    (`ux_clientes_nombre_global`, case-insensitive). Revierte lo declarado en `102_clientes.sql`.
  - **Hoy hay 4 clientes cargados** (12/8/2026), y `horas_proyecto` tiene **1 fila**. Con CERO
    clientes, el gate de identificación —que es de SISTEMA, no por empresa— rechaza al padrón entero.
  - 🔴 **Las horas de un cliente son del cliente**: la vista "Horas por cliente" NO se recorta por
    empresa en ninguna de sus cuatro superficies (listado, export, detalle, baja). El reparto por
    sociedad se muestra desglosado adentro de cada cliente, y la pantalla avisa que el selector
    del sidebar no manda ahí.
- **Vacantes + Candidatos:** `routers/vacantes.py` + `candidatos.py` (+ `_candidato_form.py` público sin auth), `vacante_service.py`, `candidato_service.py`, `cv_service.py`. Integraciones: `zernio_service.py`, `gmail_service.py` (**recepción** de mails de candidatos, 122 líneas). **Vacantes es el patrón canónico de borrado con confirmación** (router DELETE + service con snapshot-antes-de-borrar + fetch crudo por el 204 + `EliminarVacanteButton.tsx` + `ConfirmDialog`). Copiar de acá.
- **Historial salarial (C1):** `costo_service.get_historial_salarial`. 🔑 **La serie de `costos_nomina` ES el historial** — no hace falta el log de cambios: la tabla tiene `UNIQUE (empleado_id, anio, mes)`, o sea una fila por mes. Con auditoría, el caso más común —sueldos importados por CSV y nunca editados a mano— daría **historial vacío teniendo los sueldos cargados**. **DOS barreras, las dos necesarias y distintas:** la de SECCIÓN (`Seccion.COSTOS + READ`, la aplica el router: quién puede ver sueldos) y la de EMPRESA (se aplica en el service, sobre el EMPLEADO objetivo — el `empresa_id` del repo sale del header y no valida a qué empleado apuntás). El front no renderiza la sección sin permiso de costos: una sección que aparece y falla es peor que una que no aparece.
- **Entrevista de salida (C3):** `services/_offboarding_entrevista.py`. Las columnas `entrevista_salida` y `notas_entrevista` existían en DB y estaban **muertas**; ahora se escriben y se leen.
- **Domicilio desglosado (C4, mig 081):** 6 columnas nuevas en `empleados` (`domicilio_calle`, `_numero`, `_piso_depto`, `_localidad`, `_provincia`, `_cp`). **Se conserva el `domicilio` crudo** además de las estructuradas, porque el import de nómina lo trae como texto libre. **`provincia` es una lista cerrada servida por endpoint** (`schemas/_provincias.py` + `routers/empleados_catalogos.py`): el front no la hardcodea.
- **Cesiones** (mig 066): hija de empleado, en la ficha. Gateada por `Seccion.EMPLEADOS`.
- **Mails con plantillas editables (mig 087):** `services/mailer/` es el **punto de salida único**
  — `__init__.py` exporta solo `enviar_mail`; `engine`, `_gmail`, `_markdown`, `_render` y
  `_variables` son internos y **un test estructural verifica que nadie de afuera los importe**
  (molde: `services/export/`). Tres decisiones cerradas: (a) sale de una **casilla del sistema**
  designada, no de la cuenta del que aprieta el botón —un proceso automático no tiene `user_id` que
  aportar, y así el circuito de prueba y el real son el MISMO—; (b) RRHH escribe **Markdown, no
  HTML**: el HTML que llega al buzón lo genera nuestro código, así la superficie de inyección no se
  acota, desaparece (el repo no tiene ninguna dependencia de sanitización); (c) las variables son
  **allowlist, jamás "todo menos"** — con "todo menos", cada columna nueva de `empleados` se
  volvería variable de mail sin que nadie lo decida. Fuera con motivo: sueldo, documento, fecha de
  nacimiento, domicilio, contacto personal y `potencial`/`desempeno`. El envío masivo usa el
  **presupuesto de tiempo** de `_lote_mails.py`. Ver `docs/DECISIONES.md`.
- **Subtipos de ausencia (mig 088):** self-FK `padre_id` en `tipos_ausencia`, **profundidad máxima
  2**. El agrupamiento de reportes va por ID, no por texto: aplanar habría dejado "cuántos días de
  enfermedad familiar" dependiendo de un `LIKE` sobre un nombre **que RRHH edita desde la UI**.
  🔑 **`cuenta_ausentismo` vive en el HIJO**, no en el padre ni en los dos: dentro de "Licencia"
  puede haber subtipos que computan y otros que no. El padre conserva la columna solo como valor
  por defecto al crear un hijo — ahorro de tipeo, **no herencia**. ⚠️ El CHECK no puede consultar
  otra fila, así que **la guarda contra un nieto vive en `services/_tipos_jerarquia.py`**: por SQL
  directo se puede crear. "Injustificada" se **desactivó** (mezclaba el eje *calificación* con el
  eje *naturaleza*, y `_reporte_ausentismo` ya leía `justificada`, no el tipo).
- **Lector de CSV único** (`services/_import_csv.py` + `_import_encoding.py`): los tres imports
  (nómina de empleados, nómina de costos, evaluaciones) leen por acá. 🔴 **Detecta UTF-16 ANTES de
  caer a latin-1**, que es el bug que cerró: los routers hacían `except → latin-1` y **latin-1
  NUNCA falla**, así que un CSV en UTF-16 entraba como `'ÿþA\x00p\x00e\x00l…'` y el import se
  completaba con nombres ilegibles. `utf-8-sig` primero: `str.strip()` NO saca el BOM (no es
  whitespace), así que un CSV de Excel reportaba "falta la columna Apellido" con Apellido presente.
  ⚠️ **`permitir_latin1` es una política POR FLUJO, no un descuido**: evaluaciones prefiere fallar,
  nómina tiene que aceptar latin-1 porque es el formato real de RRHH. **La duplicación real era la
  DETECCIÓN; la política difiere.** El vocabulario de columnas del archivo de novedades **NO se
  escribió**: RRHH no mandó la estructura definitiva.
- **Superior desde el import de nómina (mig 086):** el superior se resuelve en una **SEGUNDA
  PASADA**, no dentro del loop — el jefe puede estar en una fila posterior (en el archivo real está
  en la fila 11 con 13 subordinados, 10 de ellos procesados antes), y resolver fila por fila daría
  **un resultado que depende del orden del Excel**. Lo que no matchea va a
  `empleado_superior_pendiente` para revisión humana. No se reusó `ResolutorIdentidad` de
  evaluaciones: ahí el desempate ES el superior, y acá el superior es la incógnita — sería circular.
- **Vacaciones pendientes (mig 083):** tabla **propia**, no filas de `solicitudes_vacaciones` con
  fechas en NULL. Esa opción rompía **15 lugares, 9 EN SILENCIO**: un predicado sobre NULL da NULL,
  que no es TRUE, así que la fila se cae del WHERE — y como el count viaja en la misma query, **se
  cae también del total**. Un día no tomado no tiene fechas porque nadie faltó ningún día: es un
  saldo, no un hecho del calendario.
- **Unicidad de ausencias (mig 089, ✅ CORRIDA — verificado 10/8/2026):** índice único
  `(empleado_id, fecha_desde, fecha_hasta, tipo_id)`. Sostiene la idempotencia del import mensual
  (`on_conflict` de PostgREST **exige** una constraint única). **NO prohíbe solapamientos
  parciales**, solo el duplicado exacto. Se corrió con la tabla en 0 filas, que era la ventana
  para hacerlo sin riesgo: con histórico cargado, un duplicado real habría hecho fallar el
  `CREATE UNIQUE INDEX` y habría que deduplicar a mano.
- **Proyectos:** asignación single (`proyecto_asignaciones.py`) + bulk multi-selección
  (`POST /{id}/asignaciones/bulk`) + **alta de un ÁREA ENTERA** (`POST /{id}/asignaciones/area`).
  Los tres comparten la clasificación en **tres grupos**: `asignados` · `ya_asignados` · `errores`
  (un duplicado NO es un error: es idempotencia — asignando un área lo normal es que la mitad ya esté).
  ⚠️ **El área ASIGNA, además de filtrar.** La línea que decía *"el área filtra candidatos, NO
  asigna"* se corrigió el 2/8/2026: **nunca fue una decisión**. Era un comentario del modal que
  describía lo implementado, la doc lo copió y al escribirlo en mayúsculas lo volvió norma.
  🔴 **Es una FOTO, no un vínculo vivo**: se resuelven los empleados del área EN ESE MOMENTO. Un
  alta posterior en el área no entra sola, y sacar a alguien del área no le borra la asignación —
  que podría tener horas, y ahí choca con `ASIGNACION_CON_HORAS` (409). *Eso* sí es una decisión.
  🔴 **La barrera va en DOS pasos** (`services/_asignaciones_bulk.asignar_area`): el ÁREA se valida
  contra el header (`ensure_area_valida` → 404) y los EMPLEADOS se resuelven **sin** filtro de
  empresa. Pasarle el `empresa_id` a `empleados_de_area` "porque falta" devolvería lista vacía y un
  200 mudo — el patrón de filtro que falla en silencio. Está escrito en el código; leerlo antes.
- **ABM usuarios:** solo admin_rrhh. `POST /api/usuarios` (alta + contraseña temporal una sola vez, `must_change_password=true`) · `DELETE` (auto-eliminación bloqueada) · `POST /cambiar-password` (self-service, 10/hora). Migración 063. **Para crear usuarios directo en DB:** crear auth user en dashboard Supabase con Auto Confirm, copiar el UUID, INSERT en `public.users` (hay FK `users.id → auth.users(id)`). Roles: `admin_rrhh`, `gerencia_lectura`, `mandos_medios`.
- **Ownership mandos_medios:** `services/ownership.py` app-level. "A cargo" = `manager_id`, no área ni `es_lider`. Aplicado en las 13 superficies de Vacaciones y Ausencias. Falta RLS a nivel DB (en AWS no va — queda app-level definitivo).
- **Adjuntos (polimórficos, `entidad` + `entidad_id`):** la empresa del adjunto sale de la **entidad PADRE, no del header** — aplicación directa de Vista vs Acción. `services/_adjunto_padres.py::ensure_padre_de_empresa` valida el padre y devuelve **su** `empresa_id` para etiquetar la hija. Resolvers para las 5 entidades que el front usa: `empleado`, `vacacion`, `ausencia`, `vacante`, `offboarding`. Los adjuntos con **`empresa_id` NULL (filas legacy) están bloqueados en TODOS los modos**, incluido el consolidado. ⚠️ `entidad_tipo` **`"evaluacion"` queda fail-closed con `ENTIDAD_INVALIDA` (400)**: está mapeado a una Sección pero **no tiene repo resolver** (no se definió a qué apunta) y tiene **0 callers**. Definir antes de habilitarlo.

---

## Staging de migración a AWS (`migracionAWS/`)
Carpeta **aislada** para migración de Supabase a **AWS (asyncpg/RDS + S3)**. Código nuevo sin tocar `backend/` en producción. Contiene `*_NEW.py` (auth completo, `postgres_client.py` asyncpg, repos-molde `empleado_repo_NEW`, `empleado_lookup_repo_NEW`, `token_repo_NEW`) + migraciones 075 (password_hash), 076 (refresh_tokens), 077 (recrear 35 triggers `updated_at`) + docs (`MIGRACION_A_RDS.md`, `README_AUTH.md`, `settings_ADD.md`). El otro dev ejecuta la infra.

**Decisiones cerradas:** se recrean los triggers · **NO hay RLS** (seguridad app-level) · no se carga demo data.

**Minas ya desactivadas (para el otro dev):**
- asyncpg devuelve UUID nativos → cast `str()` explícito en mappers.
- FK `users.id → auth.users(id)` bloquea INSERT sin Supabase → dropear + `DEFAULT gen_random_uuid()`.
- El `ON DELETE CASCADE` contra `auth.users` es lógica de negocio viva.
- `passlib` roto (bcrypt 5.0 sacó `__about__`) → usar `import bcrypt` directo.
- `schema.sql` no trae los 43 triggers `updated_at` (35 tras J5b — ver la tabla de arriba).
- **Modelo Anthropic**: que ningún string con fecha (`claude-sonnet-4-20250514`, retirado) sobreviva. Alias sin fecha (`claude-sonnet-4-6`).
- **Nuevo del Bloque A:** las tres env vars (`ASSESSMENT_ENABLED`, `TRUSTED_PROXY_HOPS`, `RATE_LIMIT_STORAGE_URI`) tienen que existir del otro lado. `TRUSTED_PROXY_HOPS` **cambia de valor en AWS** (1 con ALB solo, 2 con CloudFront adelante) — un valor de más deja al equipo entero fuera con 429. Y `RATE_LIMIT_STORAGE_URI=redis://...` es la única forma de que los límites sean reales con más de un proceso.
- **Nuevo del Bloque A:** la tabla `oauth_states` (mig 080) tiene que estar antes de que el flujo de Google funcione.

**Contraste con changelog de KarIA Reach (otro proyecto, mismo stack asyncpg/ECS/SSM) — verificado, aplica a RRHH:**
- Secretos en producción → **SSM Parameter Store / Secrets Manager, NUNCA hardcodeado**. URL-encodear caracteres especiales del password en la DSN. `migracionAWS/` está limpio: sin secretos ni placeholders pegados.
- asyncpg contra RDS: `postgres_client.py` usa `ssl="require"` ✅ y `command_timeout=30` ✅, host desde `database_url`. **Faltan (decisión de infra, no bug):** timeout de conexión explícito (default 60s cuelga el arranque si RDS es inalcanzable); `verify-full` en vez de `require`; si el DNS de RDS falla, poner IP privada en `database_url`.

---

## ⚠️ Build de producción y estilo de código — LEER ANTES DE TOCAR

### El repo NO está formateado con ruff, pese a su config
`ruff.toml` declara `line-length=100` + `[format]`, pero el código está en **estilo compacto de línea larga**. Los límites documentados se midieron sobre ese estilo. **Correr `ruff format` reflowea archivos enteros** (en una prueba: `ausencias_service.py` 149→253). **NO correr `ruff format` dentro de una sesión de feature/bugfix.** Adoptar ruff repo-wide es tarea propia con re-medición de límites. ⚠️ Confirmar si `pre-commit` está instalado — mina para la migración AWS.

### 🔴 LA VERIFICACIÓN DEL FRONT SON TRES COMANDOS, NO DOS

```
node_modules/.bin/tsc --noEmit     # 0 errores
npm test                           # vitest, todo verde
npm run build                      # "Compiled successfully"
```

**Los tres, siempre, y `npm run build` NO es opcional ni redundante con `tsc`.** El motivo está
medido, no supuesto: en la tanda de selects del 19/8/2026 se agregó un `import` en un archivo que
no tenía ninguno y quedó **arriba del `"use client"`**. Eso rompe el build de Turbopack
(*"The `use client` directive must be placed before other expressions"*, `PeriodoSelectors.tsx`) y
**`tsc` no dice una palabra**: es una regla de Next, no del sistema de tipos. Con dos de tres, el
rojo aparecía en el deploy de Vercel y no en la sesión que lo causó. Los tres miran cosas
distintas: `tsc` los tipos, `vitest` el comportamiento, `build` **las reglas de Next y la
compilación real de Tailwind/Turbopack** — directivas mal ubicadas, imports de servidor en
cliente, CSS que no resuelve.

`next dev` con Turbopack transpila sin type-check → un error de tipo pasa desapercibido en
desarrollo pero **`next build` falla**. `vitest` cubre 746 tests en 63 archivos, pero **la mayor
parte del front sigue sin test**: `tsc` sigue siendo la red principal. **Si aparece un error en
cualquiera de los tres, es tuyo.**

> ⚠️ **`npm run build` deja basura que rompe el `tsc` siguiente, en esta Mac.** Después de cada
> build aparecen duplicados de `.next/types/routes.d.ts`, `cache-life.d.ts` y `validator.ts` (los
> crea el sync de la carpeta, no Next), y como `tsconfig.json` incluye `.next/types/**/*.ts`, el
> `tsc` siguiente da **3 errores TS6200/TS2428/TS2300 que no son del código**.
> 🔴 **El sufijo NO es siempre `" 2"`: va subiendo** — apareció como `routes.d 2.ts` y en el build
> siguiente como `routes.d 3.ts`. Limpiar con el número fijo deja el problema vivo. El comando es
> `find .next -name "* [0-9].*" -delete`. Por eso conviene **correr el build ÚLTIMO**, o limpiar
> antes de creer un rojo de `tsc` que apunte a `.next/`.
> ⚠️ vitest corre con `environment: "node"` y **sin jsdom**: los tests de componentes usan `renderToStaticMarkup` y verifican el **markup**, no la interacción — y **no ejecutan `useEffect`**. Ver el caso #4 de "Un test solo prueba lo que el fake puede desmentir".

### 🚨 Módulos desactivados (assessment, sucesión y el link público de horas)

Hay **tres módulos apagados a propósito**. En los tres el código está **entero**: se sacó el punto de entrada, no se borró nada.

> 🔴 **El tercero es distinto de los otros dos y no hay que confundirlos.** Assessment y sucesión
> están apagados porque **no se usan**; el link público de horas está apagado porque **todavía no
> se encendió**: es código nuevo, completo y verde, esperando `HORAS_PUBLICO_ENABLED=true` en
> `sofia-backend` y que RRHH cargue un cliente. Su mecánica de apagado copia la de assessment
> (router desmontado **+** rutas fuera de `PUBLIC_ROUTES`, las dos con el mismo flag), y está
> descrita en *Otros módulos → Carga de horas*.

#### 1. Assessment — apagado en el FRONT **y en el BACKEND**
- **Backend (Bloque A1):** `settings.assessment_enabled: bool = False`. **Dos puntos leen el flag:**
  - `main.py:135` — el router **no se monta**. Toda la superficie del módulo (incluidas sus **2 rutas públicas sin auth**) deja de existir para FastAPI y devuelve el **404 de plataforma, idéntico a cualquier ruta inexistente** — nunca un 403 ni un mensaje que confirme que el módulo está ahí.
  - `middleware/auth.py:64` — `_is_public` gatea el regex de las rutas públicas con el mismo flag. **Gatear las dos cosas es lo que hace que se comporten como una ruta cualquiera**: si solo se desmontara el router, dejarlas saltear el auth cambiaría el 401 por un 404, y esa diferencia contra el resto de las rutas desconocidas delataría que están contempladas de forma especial.
  - ⚠️ Ahí vivía además `_ASSESSMENT_FE_RE = r"^/assessment/[^/]+$"`, **borrado a propósito**: era un bypass de auth que no matcheaba nada (el backend monta assessment en `/api/assessment`).
  - Los **rate limits de las rutas públicas quedan puestos aunque el flag esté en `false`**, para que encenderlo no reabra el agujero.
  - **PARA REACTIVARLO: `ASSESSMENT_ENABLED=true` en el entorno. Nada más — cero cambios de código.** `tests/test_assessment_modulo_flag.py` cubre las tres piezas.
- **Front:** `app/(dashboard)/assessment/[id]/page.tsx` → `const [moduloActivo] = useState(false)` con el setter descartado; redirige a `/dashboard`.

#### 2. Sucesión — apagado por decisión de producto, solo en el front. **Dos flags, uno por archivo:**
- `components/layout/nav-config.ts` → `const SUCESION_ACTIVA: boolean = false`. El ítem no se borró: quedó como `SUCESION_ITEM` y el grupo "Incorporación" lo incluye con `...(SUCESION_ACTIVA ? [SUCESION_ITEM] : [])`.
- `app/(dashboard)/sucesion/page.tsx` → `const [moduloActivo] = useState(false)` + `router.replace("/dashboard")`.
- **Cómo revertir: dos líneas, una por archivo. Hacen falta las dos** — solo la primera devuelve el ítem al sidebar pero la página sigue redirigiendo.

#### 🚨 LA REGLA QUE UNE A LOS DOS — el flag del front NUNCA es un `const` con literal
> TS colapsa `const x = false` al tipo literal `false`. En un componente eso marca el cuerpo inalcanzable, pierde el narrowing y **`next build` falla**. En un módulo de datos, la rama `true` del ternario deja de type-checkear, así que **reactivar el módulo rompería el build en vez de funcionar**. Por eso el flag es `useState(false)` en las páginas y **`: boolean` anotado explícito** en la config. **No "simplificar" ninguno de los dos.** Hay comentarios en cada archivo.
> (En el backend el problema no existe: `assessment_enabled` es un campo de `Settings`, tipado `bool` por Pydantic, y se lee en runtime.)

⚠️ **Por qué el contenido de sucesión vive en un `SucesionContenido` aparte** y no en el cuerpo del componente, como sí hace assessment: acá la carga de datos está en **hooks** (`useSucesionData`), no en un `useEffect` que se pueda gatear. Los hooks corren aunque el módulo esté apagado, así que sin esa separación la pantalla desactivada **dispara 3 llamadas al backend antes de redirigir**. **Si apagás otro módulo, fijate primero dónde vive su fetch**: en un `useEffect` alcanza un componente; en hooks, hace falta separar.

**Lo que queda vivo a propósito:** las rutas siguen **navegables a mano** y redirigen (no están borradas del router). Por eso **`services/permisos.ts:96` conserva `{ ruta: "/sucesion", seccion: "sucesion" }`: la ruta existe, así que el AuthGuard tiene que seguir protegiéndola.** Sacarlo dejaría una ruta viva sin gate. Lo mismo con `assessment` en `permisos.ts:55`.

**Intactos en sucesión:** todo el backend (endpoints, `Seccion.SUCESION`, tests), los 11 archivos de `components/features/sucesion/`, `services/sucesion.ts` y `types/sucesion`.

---

## Deuda técnica conocida

### 🔴 Bugs / riesgos ACTIVOS

- 🔴 **`migrations/094_recrear_triggers_empresa.sql` quedó desincronizada de la 112, y eso ROMPE EL REBUILD.** Declara **9** triggers `trg_emp_*`; el noveno es `trg_emp_sucesion` **sobre `sucesion_posiciones`, tabla que la 112 dropeó**. Producción tiene **8** (contado el 12/8). Un replay de `schema.sql` (52 tablas) seguido de la 094 **aborta**: `DROP TRIGGER IF EXISTS x ON tabla` falla igual si la que no existe es la TABLA. **Es la misma mina que J5a ya desactivó en la 077** y a la 094 no se le hizo. Fix: sacar las líneas 82-85 y el comentario de verificación que dice "debe devolver 9".
  > 🔑 **Y no es un archivo prescindible:** `fn_misma_empresa()` y sus triggers son la **única** defensa a nivel base contra el cruce de empresas por referencia, y **no están en `schema.sql`** (que no trae funciones ni triggers). De los 12 pares (columna → tabla padre) que vigilan, **cero tienen FK compuesta que los respalde** — verificado contra el catálogo el 12/8, y eso que el modelo usa ese patrón en otras 22 FKs.

- **Los 3 eventos de auditoría mal etiquetados que ya están en la tabla.** `alta_adjunto` y `baja_adjunto` (los dos sobre una **vacante**, que sí tiene empresa) y `baja_candidato` quedaron con `empresa_id NULL`. Son datos viejos: `auditoria` es inmutable, no se corrigen. Los otros 6 NULL son legítimos (`alta_usuario` ×3 y `cambio_password` ×3 — los usuarios no cuelgan de una empresa). Con **dos** empresas cargadas, un desajuste header-vs-entidad recién ahora empieza a ser distinguible.
  > ✅ **El bug que los produjo está cerrado** (`_costos_write.py`, ver Vista vs Acción). Esta entrada queda porque las filas siguen ahí.
- **`objetivos.responsable_id` es FK a `users`, no a `empleados`** (verificado en el catálogo). ⚠️ **Y es una DECISIÓN, no deuda: el bloque B de objetivos se canceló a propósito** — los objetivos son tablero del equipo de RRHH, no de los 31 empleados, y los operadores de RRHH no tienen área. Consecuencia asumida: **no hay filtro por área en objetivos**, y hay que explicárselo al directorio (estaba comprometido).
- **Filtro por provincia/localidad — pendiente hasta que haya domicilios cargados.** Las 6 columnas existen (mig 081) y `provincia` ya es una lista cerrada servida por endpoint, así que el filtro es barato; hoy no tendría nada que filtrar.
- **Filtros duplicados front+back** (patrón recurrente): si un filtro afecta el export, va **server-side, una sola implementación**. Casos abiertos: `aplicar_filtro_estado` es espejo de `derive_estado` (merece un test que las compare); el listado de evaluaciones filtra client-side y exporta server-side (aceptable a ~30 filas, el endpoint ya acepta los filtros).
- **`permisos.ts` es espejo manual de `permisos.py`** — riesgo de divergencia. (La divergencia sidebar↔guard **sí** tiene test; esta no.)
- **`_postgrest_schema` cubre los generadores de reportes, no todo el repo** — toda query con `select` anidado fuera de ese barrido sigue siendo punto ciego. Verificar en producción tras el deploy.

### ✅ Resueltos (verificados uno por uno — NO reabrir)
- ✅ **El import de costos ya audita — RESUELTO (E1).** Emite **UN evento por lote** (`importacion_costos`, entidad `nomina`) desde `services/nomina_import_service.py`. El `confirmar` era el único de los tres imports **sin capa de service** (router → repo directo, con el armado de filas y el conteo en el handler): se creó el service y el router bajó de 70 a **57** líneas.
  > ⚠️ **Corrección de lo que decía esta misma entrada: el molde NO era `payload_carga_nomina`.** Ese payload es de **UNA FILA** —recibe un `NominaResponse` individual y difea contra el `prior`—, así que copiarlo habría dado **un evento por fila**, exactamente lo que la regla propia del repo prohíbe. Su único caller es la carga manual (`_costos_write.py:48`) y ahí está bien. El molde real era **`payload_importacion_nomina`** (`services/_audit_payloads_import.py`), que ya resolvía lo que este caso comparte: **`costos_nomina` no persiste un lote con id propio**, así que el `registro_id` es un `uuid4()` de **EVENTO**, no de recurso. Evaluaciones tampoco servía de molde para eso: ahí el lote **sí** es una fila real con id.
  > 🔴 **`empresa_id` VA SETEADA acá, al revés que en el hermano de empleados.** Ese lote crea gente en varias empresas (las deriva del archivo) y por eso va con `None`; este recibe una empresa explícita en el body. Copiarle el `None` habría dejado el evento fuera del filtro por empresa de `/auditoria`.
  > 🔴 **Lo que el evento NO dice, a propósito: no lleva `importados`/`actualizados`.** El upsert de PostgREST devuelve las filas resultantes pero **no distingue INSERT de UPDATE**; esa distinción solo existe en el `es_actualizacion` del body, que se calculó en el preview y **volvió por la red** (el cliente lo puede alterar). El evento cuenta **`filas_persistidas` desde el retorno del repo** —el único dato autoritativo, que el router descartaba— más `filas_enviadas` y un `parcial` derivado. La respuesta HTTP sí conserva el desglose: **la pantalla dice más que el log, y el log dice solo lo que puede sostener.**
- ✅ **Fuga entre empresas — CERRADA (Fase 2).** Ver "Patrón de barrera de empresa".
- ✅ **`confirmar()` de evaluaciones — RESUELTO (Fase 0.2).** Período temporal + verificación por conteo.
- ✅ **Auditoría de nómina silenciosa — RESUELTA (Fase 0.1).** uuid4 de evento.
- ✅ **N+1 de sucesión — RESUELTO (Fase 3, `51832e2`).** Con 200 empleados: de 201 requests a 2.
- ✅ **Diff fantasma de auditoría — RESUELTO (Bloque C).** `sin_derivados`. Ver "Audit log".
- ✅ **6 de 11 reportes rotos en producción — RESUELTO (Bloque C).** + `tests/_postgrest_schema.py` para que no vuelva.
- ✅ **`fetchEmpleados` posicional — RESUELTO (Fase 3).** Objeto de opciones sobre `EmpleadosFiltros`.
- ✅ **`page_size=100000` en export — RESUELTO (B7).** `LIMITE_FILAS_EXPORT = 20000` (era 5.000; se subió el 13/8/2026 con medición, ver arriba) + aviso 422. **En el código ya no queda ningún `100000`** (solo referencias en docs y en demo data SQL).
- ✅ **`middleware/auth.py` aceptaba cualquier UUID como `X-Empresa-Id` — RESUELTO (A3).** `utils/empresas_cache.py`.
- ✅ **Posicionales de `services/vacaciones.ts` y `ausencias.ts` — RESUELTO (B2).** Los cuatro (`fetchVacaciones`, `exportarVacaciones`, `fetchAusencias`, `exportarAusencias`) toman `filtros: VacacionesFiltros/AusenciasFiltros`, y listado y export comparten el traductor `queryVacaciones`/`queryAusencias`. **Ya no hay filtros posicionales corridos entre hermanas.** (`page`/`pageSize` siguen posicionales en los `fetch*`, lo cual es correcto: el export no se pagina.)
- ✅ **`state` de OAuth adivinable — RESUELTO (A4).** Nonce de un solo uso.
- ✅ **Assessment expuesto sin auth — RESUELTO (A1).** Router desmontado + regex gateada.

### Líneas — **REMEDIDO contra el código el 12/8/2026**

> 🟢 **BACKEND: CERO archivos sobre su límite.** Se sostiene desde el 2/8, remedido hoy archivo
> por archivo. Los 7 originales se cerraron ese día: 2 se **borraron** (`costo_repo`,
> `assessment_repo` — ver "Código muerto") y 5 se **partieron** (`_onboarding_templates_row`
> 159→87 · `_audit_payloads` 167→119 · `ev_instancias_repo` 146→98 · `ev_plantillas_repo`
> 129→93 · `reporte_anual` 154→112), más `usuario_service` 149→77 y `ev_instancias_service`
> 149→113 que estaban en el techo. *(Los cuatro `ev_*` de esa lista ya no existen: J5a los borró.
> Quedan escritos porque el aprendizaje de abajo salió de ellos.)*

> 🔴 **UN SATÉLITE NO TIENE LÍMITE PROPIO DE 200 POR VIVIR EN `repositories/`.** Dos archivos
> `_row` tenían escrito "acá el límite es 200" y uno llegó a **159**. Un `_*.py` dentro de
> `repositories/` **es un repositorio y su límite es 100**; dentro de `services/`, 150. Partir un
> archivo para respetar un límite es correcto; redefinir el límite del archivo nuevo, no.

**Backend — nadie over-limit. A 99-100 (el próximo cambio EXIGE dividir primero), remedido el 12/8:**
- ⚠️ **`repositories/nomina_repo.py` 99/100** — llegó ahí en la sesión 0.6. El comentario del `str()` se condensó a una línea justamente para no pasarlo.
- **Services 150/150:** `assessment_service.py` · `_clasificador_prompt.py` · `_vacaciones_write.py`.
- **Repos 100/100:** `area_repo` · `candidato_repo` · `inventario_asignaciones_repo` · `objetivo_repo` · `planes_carrera_repo` · `vacante_repo`.
- **Routers 80/80:** `adjuntos.py` · `candidatos.py`.
> ⚠️ **Esta lista se mueve todas las semanas: es una FOTO, no un inventario estable.** La forma de reconstruirla es medir, no leerla — `Get-ChildItem ... | ForEach-Object { (Get-Content -LiteralPath $_.FullName).Count }` sobre `routers/`, `services/` y `repositories/`. La versión anterior nombraba `evaluacion_repo`, `nomina_repo`, `vacantes.py` y `vacaciones.py`, que desde entonces bajaron o subieron.
> ⚠️ **`gmail_service.py` ya NO está en el techo** (150 → **122**): el manejo del token se fue a `_google_token.py`, compartido con el envío. Quedó solo con la recepción de mails de candidatos.

**Frontend — 28 archivos > 150** (sin contar `.test.*`; **26 propios**, los otros 2 son primitivos de shadcn), y **2 hooks > 80**. Remedido el 12/8:
`costos/page.tsx` **624** · `vacantes/[id]/page.tsx` **451** · `onboarding/page.tsx` 413 ·
`ImportarNominaCSVModal.tsx` 377 · `offboarding/page.tsx` 311 · `NominaModal.tsx` 287 ·
`evaluacion/[token]/page.tsx` 258 · `VacanteModal.tsx` 251 · `AIPanel.tsx` 249 ·
`assessment/page.tsx` 233 · `empresas/[id]/page.tsx` 230 · `EmpresaModal.tsx` 226 ·
`CampanaModal.tsx` 208 · `EmpresaAreasTab.tsx` 206 · `vacantes/page.tsx` 178 · +11 más entre 152 y 201.
- **Hooks sobre 80:** `useFiltrosVacaciones.ts` **95** · `useFiltrosAsignacionesCap.ts` **89** (los dos viven en `components/features/`, no en `hooks/`). Molde para cortarlos: `useOpcionesAusencias` (partir la carga de opciones del estado del filtro).
- ⬜ **No cuentan como deuda:** `dropdown-menu.tsx` 268 y `dialog.tsx` **221** son primitivos generados de shadcn/ui.
- ✅ Ya cortados: `configuracion/page.tsx` (390 → **81**) · `onboarding/templates/[id]/page.tsx` (412 → **136**) · `onboarding/templates/page.tsx` (290 → **120**) · **`areas/page.tsx` (261 → 128)**.
> Los dos objetivos grandes siguen siendo `costos/page.tsx` (624) y `vacantes/[id]/page.tsx` (577) — copiar el corte de `components/features/sucesion/` (855 → 85).

**Cortes ya identificados (para no re-diagnosticar):**
- `objetivos.py` e `inventario_items.py` (79) → al dividirlos, **agregarles `shared_limit("30/hour", scope="export")`**; hay un test que lo recuerda.
- `evaluacion_repo.py` (100) y su router → los pide el Bloque D1 (estadísticas cross-lote).

### 🔴 Código muerto — el criterio es CALLERS REALES, no visibilidad en la UI

**"Está oculto en la UI" ≠ "está muerto".** En el relevamiento del 2/8, de 5 sospechosos **3
estaban vivos**, y la lista vieja de este archivo fue lo que indujo el error. La verificación es
siempre la misma y no se salta: grep del nombre del módulo Y de su clase en `services/`,
`routers/`, `repositories/`, `tests/` y `main.py`.

**Ya borrado el 2/8/2026 (0 callers, verificado uno por uno):** `repositories/costo_repo.py` ·
`repositories/assessment_repo.py` · `components/features/evaluaciones/EliminarLoteButton.tsx`.
`costo_service` usa `nomina_repo`/`periodo_repo`/`presupuesto_repo`, no `costo_repo`.
> Los 8 casos parametrizados que `test_selects_repos` tenía sobre esos dos repos desaparecieron
> con ellos: es esperado, el barrido descubre por introspección.

🔴 **LO QUE NO ESTÁ MUERTO Y NO SE BORRA, aunque no se vea en la UI:**

| Qué | Por qué |
|---|---|
| **Assessment** (services, schemas, tests) | Apagado por FLAG (`ASSESSMENT_ENABLED`), no muerto. Encenderlo es una variable de entorno y cero código. Solo `assessment_repo` estaba huérfano, y ya se borró. |
| **Sucesión** (todo el backend, y los 11 componentes del front) | Apagado por dos flags en el front. El backend está intacto y montado. |

> ✅ **`ev_*` YA NO ESTÁ EN ESTA TABLA: se borró entero en el bloque J5 (11/8/2026).** Acá decía
> *"los 3 routers están MONTADOS, borrarlos rompe endpoints publicados"*, y era cierto hasta ese
> día. Lo que lo destrabó fue medir qué había del otro lado de esos endpoints: **19 rutas
> publicadas por HTTP e inalcanzables desde la UI**, una de ellas rota hacía meses sin que nadie
> lo notara. **J5a** borró el código (17 archivos, 1.527 líneas) y **J5b** dropeó las tablas
> (migración 112). 🔴 **No confundir con el módulo de evaluaciones VIVO**, que comparte el prefijo
> de URL `/api/evaluaciones/*` y tiene datos en producción: ése es `evaluacion_*`, no `ev_*`.

✅ **Las 6 tablas huérfanas TAMBIÉN se dropearon** (`assessment_reportes`, `configuracion_empresa`,
`documentos_empleado`, `notificaciones`, `notificaciones_config`, `sucesion_posiciones`), en la
misma migración 112 y por el mismo motivo: 0 filas y cero referencias en código. Acá decía que se
limpiaban "después del cutover a AWS"; se adelantó **a propósito**, porque el `schema.sql` que el
dev de infra levanta en RDS no tiene por qué traerlas. **Producción: 63 → 52 tablas** (verificado
contra el catálogo el 12/8/2026).

### Al margen por decisión (NO tocar)
- **S6 / DROP de `cargo` y `rol`** → no se borra nada (decisión de producto). Fallbacks `roles[0] ?? cargo` quedan.
- **Campo `equipo`** (texto libre): sin tabla `equipos`, "asignar/importar por equipo" no existe.
- **"Compatibilidad con una posición"** (sucesión): feature nunca construida, no deuda técnica. El ranking es por assessment genérico. Cuando RRHH la reclame, definir qué significa compatibilidad antes de improvisar.

### Tests
- **Backend: 4004 passed** en **192 archivos `test_*.py`** (+ **19 helpers** `tests/_*.py`, que no son tests — 211 archivos `.py` en total dentro de `tests/`). `pytest -q` desde `backend/` con `venv`. *(Remedido el 19/8/2026, al cerrar A3.3 / el bloque A.)*
  > 📌 **La secuencia, para que un número no parezca una caída inexplicada:** 3280 (11/8) → 3229 (J5a) → 3228 (J5b) → 3234 (fix ASCII) → 3915 (A4.2) → 3934 (A5.1) → 3980 (A5.2/A6) → **4004** (A3.3). Sube porque se agrega código con tests, no al revés — si algún día baja, es porque se borró código, como el único caso de arriba.
- **Front: `npm test` (= `vitest run`) — 746 tests en 63 archivos, verdes.** *(Windows verificado el 19/8/2026; la Mac quedó verificada por última vez el 12/8 con 647. Sin sesión de frontend desde A6, este número no se movió.)* **La cobertura sigue siendo parcial** — `tsc` sigue haciendo falta. No listar los archivos acá: se desactualiza en una sesión. `npm test` los enumera.
  > ✅ **Los 3 rojos que daba en Windows están arreglados (12/8).** `barridoFront.test.ts` armaba los paths con `path.join` (separador `\`) y filtraba con un `/` literal, así que descubría **0 exports** y las guardas de mínimo lo cazaban. **Verde en la Mac, rojo en la Lenovo, sin que cambiara el código auditado.** Ahora los paths se normalizan en `archivosDe`, el único lugar donde nacen. 🔑 **La regla que deja: un barrido que recorre el árbol filtra por `e.name` o normaliza el separador — nunca compara un tramo de path con `/` literal.** Los barridos del backend ya lo hacen bien (`Path.parts` / `.stem` / `.as_posix()`), y los otros tres del front filtran por nombre de archivo.
- **Son 21 barridos estructurales conocidos** (16 backend + 5 front), renumerados el 19/8/2026 —
  la lista anterior tenía dos numeraciones distintas conviviendo (1–11 y 12–15 fuera de orden) y
  le faltaban 3 barridos que ya existían. **Cada uno cubre automáticamente lo que se agregue
  después, y todos llevan guarda de mínimo** (`assert len(...) >= N`), sin la cual una
  extracción rota devolvería 0 elementos y pasaría en el vacío:
  1. `tests/test_paridad_list_export.py` — el export acepta los mismos Query que el listado.
  2. `tests/test_limite_export.py::TestTodosLosExportsChequean` — todo export llama a `verificar_limite_export`.
  3. `tests/test_selects_repos.py` — **todo** `select` con embed del repo, validado con AST contra `db/schema.sql`. Descubrimiento por introspección, nunca una lista.
  4. `tests/test_espejo_permisos.py` — `frontend/services/permisos.ts` contra `utils/permisos.py`: secciones, acciones, roles y `MANDOS_MEDIOS_SECCIONES`.
  5. `tests/test_callers_huerfanos.py` — símbolos de `services/`+`repositories/` que nadie llama, y endpoints montados que el front nunca pide.
  6. `tests/test_mappers_ejercitados.py` · 7. `tests/test_contrato_repos.py` · 8. `tests/test_auditoria_coherente.py` · 9. `tests/test_nombres_definidos.py` · 10. `tests/test_triggers_updated_at.py`.
  11. **`tests/test_acceso_a_datos.py`** — **solo `repositories/` habla con la base.** Barre por AST todas las capas que no son repos y rojea ante un `.table()`/`.rpc()` no declarado. 🔑 Las excepciones son **4 FAMILIAS** (`reporte`, `dashboard`, `organigrama`, `procesos`), no 19 archivos, y **un test impide que pasen de 5**: una lista larga es la que nadie mira (K2/K7). Guarda de mínimo ≥250 archivos + contracara. El inventario de las 58 declaradas vive en `docs/handoff-aws/ACCESO-A-DATOS.md`.
  12. **`tests/test_storage_punto_unico.py`** — ningún service ni repo nombra un bucket ni llama al SDK de Storage: todo pasa por `integrations/storage.py`. **Por AST, no por texto**, porque varios docstrings dicen "bucket privado 'documentos'" y un grep los marcaría — hay un quinto test que fija que la prosa NO cuenta. Guarda de mínimo ≥150 archivos.
  13. **`tests/test_columnas_candidatos.py`** (A4.1) — toda columna de `candidatos` está EXPUESTA o DECLARADA con razón, en las dos direcciones (código→base Y base→código). El primero de su clase: los otros barridos de columnas viajan código→base y no ven una columna que el `select("*")` trae y nadie usa.
  14. **`tests/test_columnas_capacitaciones.py`** (A5.1) — mismo patrón, generalizado a 2 tablas (`capacitaciones`, `empleado_capacitacion`) con el concepto extra de `DERIVADOS` (campos resueltos por join, no columnas). El patrón cubre 3 tablas / 4 de los ~30 archivos con `select("*")` — quedan ~26 sin barrido.
  15. **`tests/test_estado_preingreso_lecturas.py`** (A2/A3) — toda COMPARACIÓN contra `empleados.estado` en el código, declarada con su criterio (grupo A "¿está activo hoy?", plantilla, alta, baja).
  16. **`tests/test_estado_preingreso_escrituras.py`** (A2/A3.3) — hermano del anterior: toda ESCRITURA de `empleados.estado`. Los SEIS caminos (alta, PUT, activar, efectivizar, nómina, contratar) con sus guardas o la ausencia declarada.
  17. **`frontend/components/layout/nav-config.test.ts`** — `NAV_GROUPS` contra `seccionDeRuta`.
  18. **`frontend/services/barridoFront.test.ts`** — exports de `services/` que ningún componente importa, en dos buckets (huérfano / solo-tests), con excepciones declaradas con razón y verificadas en las dos direcciones.
  19. **`frontend/app/contrasteTokens.test.ts`** — ratio WCAG de los **10 pares** fondo/texto de la paleta, **en LOS DOS TEMAS** (`:root` y `.dark`), parseando hex y oklch del archivo real. 🔴 **Desde el 19/8/2026 lee `app/paleta.css`, no `globals.css`**: los dos bloques de tokens se mudaron a un archivo propio cuando la paleta de `docs/SISTEMA-DE-DISENO.md` pasó a `globals.css` del límite de 200 líneas, y `globals.css` quedó con el cableado (`@theme inline`, capa base, print) importándolo. Vigila que la paleta siga siendo legible: la regla de `option` de `globals.css` no elige colores, los toma prestados de `--popover`/`--popover-foreground`, así que un ajuste de paleta puede volver el popup ilegible **sin tocar la regla**. Ancla la fórmula con valores literales antes de medir nada (blanco/negro = 21:1 por hex y por oklch) y **rechaza** los colores con canal alfa en vez de medirlos ignorándolo. ⚠️ **Hasta el 19/8 parseaba SOLO el bloque `.dark`**, y ese medio barrido escondía que `--muted/--muted-foreground` daba 4.34:1 en claro. `BRECHAS_DECLARADAS` quedó **vacío**: la paleta nueva cerró las tres brechas que había (`--primary` y `--sidebar-primary` en oscuro, 3.68:1 → 7.97:1; `--muted` en claro, 4.34:1 → 5.24:1). El mecanismo sigue, para la próxima.
  20. **`frontend/components/ui/barridoSelect.test.ts`** — **ningún `<select>` nativo fuera de `components/ui/select.tsx`**. Nació el 19/8/2026 junto con el primitivo, al migrar los **81 `<select>` de 53 archivos** que vivían vestidos con **29 constantes de estilo copiadas entre archivos** (`SELECT_CLASS` declarada en 14 archivos con **10 valores distintos**, `SEL` en 9 con 3, `SELECT_CLS` en 3 con 3, más 17 con la clase inline). Migrar sin barrido no cierra nada: el próximo `<select>` nativo entra en el próximo PR. Tres aserciones: no hay nativos fuera del primitivo · la única excepción declarada sigue teniendo uno (excepción muerta = rojo) · todo archivo que pinta `<Select>` lo importa de `@/components/ui/select` (un `Select` local esquivaría la primera). Guardas de mínimo ≥300 archivos barridos y ≥40 consumidores. 🔑 **Enmascara los comentarios antes de buscar**: hay 6 lugares que mencionan `<select>` en prosa para explicar por qué ahí NO se usó uno, y un barrido por texto plano empujaría a borrar justo esas explicaciones. Excluye los `.test.*` — sin eso se marca a sí mismo.
  21. **`frontend/components/ui/dialog.test.tsx`** (bloque *"Barrido: la altura y el scroll del modal los decide el primitivo"*) — **ningún `<DialogContent>` declara `max-h-*` ni `overflow-*`**. 🔴 Nació el 19/8/2026 **dando vuelta el test que estaba en su lugar**, que verificaba lo contrario: *"los 15 modales que ya traían `max-h-[90vh] overflow-y-auto` siguen andando"*, o sea que el className del consumidor le GANARA al del primitivo. Era cierto y era el bug: **20 modales pisaban el `max-h-[calc(100dvh-2rem)]` del popup con `90vh`** —y `vh` en mobile cuenta la barra de direcciones, que es exactamente lo que el `dvh` del primitivo evita—, y ponían `overflow-y-auto` sobre el POPUP en vez del cuerpo, con lo que el título y los botones se iban con el scroll. Un test que protege una regresión es peor que no tenerlo. Lee los archivos reales (un modal nuevo entra solo), con guarda de mínimo ≥15. **Lo encontró él y no un grep**: el 20º usaba `max-h-[80vh]`.
  > ⚠️ **Esta lista es una FOTO, compilada por grep del marcador "BARRIDO ESTRUCTURAL" + memoria
  > de sesión, no una re-auditoría exhaustiva de cada archivo.** Puede faltar alguno con un
  > docstring que no use ese marcador literal. La forma de reconstruirla de cero, si hace falta:
  > `grep -ril "BARRIDO ESTRUCTURAL" backend/tests/` + revisar a mano los que no usan ese texto
  > (`test_paridad_list_export.py`, `test_limite_export.py`, `test_triggers_updated_at.py` no lo
  > usan literal y hay que buscarlos por su propósito).

> 🔴 **POR QUÉ HICIERON FALTA DOS BARRIDOS DE CÓDIGO MUERTO Y NO ALCANZA UNO.** El #5 empareja
> *(path, método)* contra los **literales de path escritos en el front**; el #12 mira **quién
> importa a quién**. Son ejes distintos y cada uno ve lo que el otro no puede: un wrapper muerto
> le sigue "dando caller" a su endpoint en el #5 —`fetchCliente` estuvo cinco sesiones sin caller
> y el barrido verde, tapada por `updateCliente`/`deleteCliente`, que escriben el mismo literal
> con otro método—, y el #12 no sabe nada de rutas del backend. Al encenderse, el #12 encontró en
> el acto que **`POST /api/costos/presupuesto` y la asignación single a un proyecto solo los
> escribe una función sin caller**: dos features publicadas e inalcanzables desde la UI.
> ⚠️ Y por eso **un comentario del front NO cita una ruta entre backticks**: el escáner del #5 no
> distingue un comentario de un template literal, así que escribirla vuelve a tapar el endpoint.
- Adjuntos: 11 tests unit con `_FakeRepo` + storage monkeypatcheado. **E2E real nunca se ejecutó** (`_BUCKET="documentos"` hardcodeado apunta a prod). Decisión: E2E automatizado en el cutover a AWS/S3.
- 🚨 **Antes de dar un test por bueno, contestar: ¿qué tendría que ser distinto en el fake para que pueda fallar?** Ver la sección "Un test solo prueba lo que el fake puede desmentir".

### En pausa
- ✅ **Link público de carga de horas (E4) — YA NO ESTÁ EN PAUSA: SE CONSTRUYÓ ENTERO.** Esta línea
  decía *"Bloqueado: requiere la reunión de definición"* y quedó así hasta el 10/8/2026, seis
  sesiones después de que el módulo empezara. Ver **"Carga de horas"** en *Otros módulos*. Lo único que
  falta para que funcione en producción no es código: `HORAS_PUBLICO_ENABLED=true` en
  `sofia-backend` y **al menos un cliente cargado**.
- **Limpieza general del repo** (Bloque G): lo que queda es el filtro `empresa` duplicado 8× entre repos y el presupuesto de tiempo duplicado entre `_nomina_lote` y `_lote_mails`. **El dead code y los duplicados de la raíz YA SE BORRARON** (2/8/2026). No urgente.

---

## Git
- Operar siempre desde la raíz del repo, `RRHH/`.
- **Commits los hace Franco manualmente** (nunca Claude Code). Commits y push desacoplados: no hay push hasta que Franco lo decida. Preferir commits por sub-sesión.
- Formato convencional (`feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `test:`).
- Solo `main` y `origin/main`. Sin ramas sueltas.

---

## 🔴 POR QUÉ ESTE ARCHIVO SE PUDRE, Y LA PROPUESTA PARA QUE DEJE DE HACERLO

Este documento se leyó al empezar cada sesión desde A2 hasta A6 y ninguna lo corrigió — no por
descuido puntual, sino porque **actualizarlo compite con la tarea real de la sesión y siempre
pierde**: nadie abre un CLAUDE.md de 1000+ líneas a mitad de un bugfix para remedir 15 conteos
que no tienen que ver con lo que está arreglando. El resultado, siete sesiones después, fue esta
misma corrección: siete números falsos, tres de ellos contradictorios entre sí (la cantidad de
archivos de test aparecía de tres formas distintas en el mismo archivo).

**La propuesta — una sola cosa, sin depender de que alguien se acuerde:**

Un **barrido estructural que compare los números que este documento AFIRMA contra los que el
repo TIENE**, en el mismo espíritu que los otros 19: `tests/test_claude_md_no_miente.py`
(exento del límite de 200 por vivir en `tests/`, como el resto de los `test_*.py`). Parsea este
archivo buscando un puñado de patrones ya estables ("N archivos SQL en `migrations/`", "N
archivos en `routers/`", "Backend: N passed", el número del CHECK de `empleados.estado`) con una
tabla de regex→medición real (`len(Path("migrations").glob("*.sql"))`, un conteo de rutas,
etc.), y **rojea si divergen más de un margen razonable** (la suite de tests, por ejemplo, va a
moverse SIEMPRE que se agregue un test — el barrido no puede exigir igualdad exacta ahí, solo
que el número no esté a cientos de distancia).

Por qué esto y no otra cosa:
- **No depende de memoria ni de disciplina** — es lo que ya funciona para los otros 19 barridos:
  el CI (o `pytest -q` local) lo hace fallar solo, no hace falta que nadie se acuerde de mirar.
- **Es barato de mantener**: el barrido no necesita saber SI un número es correcto, solo que
  coincida con lo medible — la corrección del texto la sigue haciendo una sesión humana (o de
  Claude), el barrido solo avisa que hace falta.
- **No exige actualizar CLAUDE.md en cada sesión** (eso es lo que ya falló siete veces): exige
  que la PRÓXIMA sesión que toque algo medido por el barrido no pueda cerrar en verde sin
  corregir el número, que es un incentivo que sí funciona en este repo — es literalmente el
  patrón que sostiene los otros 19.
- **No se construye acá.** Es la propuesta, no la implementación: decidir qué números vale la
  pena anclar (no todos: "31 empleados" es dato de producción y no se ancla, como pidió esta
  sesión) es una decisión de una tanda propia, con el archivo completo por delante.

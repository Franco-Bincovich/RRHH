# CLAUDE.md — RRHH (HR Karstec)

> **Ubicación:** raíz del repo RRHH (`RRHH/`), desde donde se ejecuta `claude`. `backend/`, `frontend/`, `docs/` y `migracionAWS/` cuelgan directo de la raíz — **`RRHH/` es el único repo git (no hay repos anidados), y todas las operaciones git corren desde ahí**.

## Documentos (leer al inicio) — jerarquía y qué responde cada uno

**Fuente de verdad del SCHEMA, en este orden:**
1. **El catálogo vivo de producción** (proyecto Supabase `grmdiwxcvcjorlohpwji`, "HR Karstec"). Producción driftea; el catálogo no miente.
2. **`backend/db/schema.sql`** — fuente de reconstrucción, y lo que `tests/_postgrest_schema.py` valida contra las queries. Hoy coincide con producción en tablas y constraints.
3. ⚠️ **`docs/MODELO_DATOS.md` — DESACTUALIZADO, ya NO es "la fuente de verdad única".** Describe tablas que no existen con esa forma (p. ej. `horas_proyecto` con `costo_hora_snapshot`/`fecha_carga`/`origen`, que la tabla real no tiene) y catálogos (`seniorities`, `roles`, `equipos`, `tipos_licencia`, `motivos_baja`) que nunca se crearon. Sirve como **intención de diseño**, no como descripción del schema. Ante contradicción **gana el catálogo vivo**.

**Fuente de verdad del TRABAJO:**
- **`docs/Plan de trabajo`** (v2, 27/7/2026 — el archivo no tiene extensión) — **supersede a `PLAN_DESARROLLO_AHORA.md` y `PLAN_DESARROLLO_DESPUES.md`**. 7 bloques (A–G), decisiones cerradas, pedidos a RRHH. Es el que manda para "qué se hace ahora".
- ⚠️ **`PLAN_DESARROLLO_AHORA.md` y `PLAN_DESARROLLO_DESPUES.md` quedaron OBSOLETOS como plan.** AHORA describe una Fase 0 multiempresa que se completó hace meses y reglas que ya no rigen ("sin checks de rol", "sin flujos de aprobación", auditoría por trigger `fn_auditoria()` — los triggers se dropearon en la migración 058). DESPUÉS describe features que en su mayoría no se van a construir en ese orden. **No borrarlos: siguen siendo el registro de la intención original de producto** (proyectos, costeo por hora, link público, capa de permisos por sección). Leerlos como contexto histórico, nunca como instrucción.

**Estado y trazabilidad:**
- **`docs/ESTADO-VS-COMPROMISO.md`** — contraste ítem por ítem entre lo comprometido con el directorio (junio 2026) y lo que el código + el catálogo realmente hacen. Estados HECHO / PARCIAL / NO EXISTE / DISTINTO / BLOQUEADO, con evidencia `archivo:línea`. **Responde "¿esto existe de verdad?"**
- **`docs/BITACORA-CAMBIOS.md`** — log por sesión, del más reciente al más viejo, de **qué cambió y qué tiene que hacer infraestructura al respecto**. Para el dev que monta AWS. **Regla: la entrada se escribe en la MISMA sesión que el cambio.** Responde "¿qué se rompió/condicionó desde la última vez que miré?"
- **`docs/MATRIZ-FILTROS.md`** — inventario de qué filtro existe en cada módulo y en cuál de las cuatro capas (repo → service → router → UI), y si el export lo acepta. **Se actualiza al cerrar cada tanda del bloque B.** Responde "¿qué corte de información puede sacar RRHH sin pedirnos nada?"

Documentos de la agencia (convenciones obligatorias): `docs/ORDEN-Y-LEGIBILIDAD.md` · `docs/SEGURIDAD-PENTEST.md` · `docs/BASES-DE-DESARROLLO.md` · `docs/UX-UI.md`.

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

**Fases 0–3 y Bloques A, B y C COMPLETOS** (los tres bloques del `Plan de trabajo` v2 con commits en `main`, working tree limpio).

- **Fase 0** (blindaje pre-testing) · **Fase 1** (reportes + KPIs) · **Fase 2** (barrera de empresa) · **Fase 3** (deuda estructural).
- **BLOQUE A — Seguridad.** A1 assessment apagado también en backend · A2 rate limiting por franjas · A3 validación de `X-Empresa-Id` contra empresas reales · A4 nonce OAuth de un solo uso. Ver "Hardening (Bloque A)".
- **BLOQUE B — Filtros y exports.** B1 matriz · B2 fundación · B3 filtro por área · B4 filtro por proyecto · B5/B6 filtros expuestos y rango de fechas · B7 límite de export con aviso. Ver "Filtros y exports (Bloque B)".
- **BLOQUE C — Compromisos del directorio.** C1 historial salarial · C2 exports de nómina y auditoría · C3 entrevista de salida · C4 domicilio desglosado (mig 081) · C5 Áreas al sidebar. **C6 (plantillas públicas/privadas) NO está hecho** — sigue sin alcance definido (§4.3 del Plan).

**Lo que sigue:** entregar usuarios a RRHH para testing sobre datos reales · **BLOQUE D** (evaluaciones cross-lote, bloqueado por tener 1 solo lote) · **BLOQUE E** (CV screening) · handoff a AWS (`migracionAWS/`).

### 🔴 EL PROBLEMA #1 NO ES CÓDIGO: RRHH no cargó datos
Verificado contra el catálogo vivo (28/7/2026): **1 empresa, 19 empleados**, y casi todo lo demás vacío:
- `manager_id` 0/19 · `modalidad_contratacion` 0/19 · `seniority` 4/19
- `solicitudes_vacaciones` 0 · `solicitudes_ausencia` 0 · `costos_nomina` 0 · `vacantes` 0 · `objetivos` 0
- Poblado: `fecha_nacimiento` 19/19 (por eso el KPI de cumpleaños muestra datos) · `auditoria` 133 filas · el lote de evaluaciones (10 evaluados, 307 resultados).

**Consecuencia:** los reportes y KPIs están correctos pero salen VACÍOS. Antes de entregar a RRHH hay que avisarles explícitamente, o van a abrir pantallas vacías y creer que están rotas. Esto NO es deuda técnica — es un bloqueante de adopción.

> ⚠️ **`costos_nomina` en 0 tiene un efecto colateral que no es obvio:** el **historial salarial** (C1) muestra la serie de esa tabla, así que hoy sale vacío para todos. La feature está entera; el dato no existe.

### Al entregar a testing, decirle a RRHH:
1. Los reportes/KPIs salen vacíos hasta que carguen dotación, vacaciones, ausencias, costos. No están rotos.
2. `manager_id` sin cargar → un usuario `mandos_medios` no ve NADA (su ownership depende de ese campo). Todavía no probar ese rol.
3. Los filtros nuevos (área, proyecto, empleado, rango de fechas) están vivos, pero con 19 empleados y un proyecto que concentra 13, **casi todo filtro devuelve casi todo**. No es un filtro roto: es el reparto real de la gente.
4. Qué se espera que "traten de romper".

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
- **Franjas por riesgo** (de más restrictiva a menos): público sin auth 10/min (5/min el submit de assessment) · login 5/min, refresh 20/min, cambiar-password 10/hora · **import 10/hora compartido** (`scope="import"`, 5 endpoints) · **export 30/hora compartido** (`scope="export"`) · `POST /reportes/generar` 20/hora (llama a Claude, cada request cuesta plata) · `/health` **exento**.
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
├── main.py              ← entrada, registro de routers, middleware (163 líneas)
├── config/settings.py   ← única fuente de config y env (Settings() se instancia en import)
├── routers/             ← 48 endpoints, sin lógica (límite 80 líneas)
├── services/            ← 113 archivos de lógica de negocio (límite 150)
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
│   └── reportes/              ← un submódulo por familia + _common.py
├── repositories/        ← 54 archivos, único acceso a DB (límite 100)
│   ├── _scope_filtros.py      ← "qué empleados caen bajo área/proyecto" (B3/B4, era _area_scope.py)
│   ├── _rango_fechas.py       ← filtro por período con semántica de SOLAPAMIENTO (B5)
│   ├── _empleado_write_repo.py, _empleado_row.py, _nomina_row.py, _offboarding_row.py
│   └── oauth_state_repo.py    ← crear · consumir · purgar_vencidos (A4)
├── integrations/        ← wrappers externos (supabase_client, anthropic)
├── schemas/             ← Pydantic in/out (+ empleado_out.py y _provincias.py)
├── utils/               ← permisos.py, errors.py, logger.py, rate_limit.py, empresas_cache.py
├── db/schema.sql        ← FUENTE DE RECONSTRUCCIÓN (52 tablas, 331 constraints, 132 CREATE INDEX)
├── migrations/          ← 79 archivos SQL; backend va por 081 (075–077 viven en migracionAWS/)
├── ruff.toml            ← config de ruff (reemplazó pyproject.toml, por Vercel)
├── pytest.ini           ← config de pytest (asyncio_mode=auto, testpaths=tests)
└── tests/               ← 61 archivos test_*.py + _postgrest_schema.py (helper)
```

**Env vars obligatorias** (sin default → rompen el import si faltan): `supabase_url`, `supabase_anon_key`, `supabase_service_key`, `jwt_secret`, `anthropic_api_key`, `resend_api_key`. Con default: `assessment_enabled`, `trusted_proxy_hops`, `rate_limit_storage_uri`, `supabase_timeout` (30 s), Google OAuth, `frontend_url`, `allowed_origins`. La migración a AWS agrega `database_url`.

**Migraciones y salud de base.** La última del backend es **081** (`add_domicilio_desglosado`); **080 y 081 están CORRIDAS en producción** (verificado contra el catálogo: `oauth_states` existe, `empleados` tiene los 6 `domicilio_*`). Las 072/073/074 corrigieron drift. `000_run_all.sql` **deprecado con guard que aborta**.

**Contraste schema.sql ↔ catálogo vivo (28/7/2026):**

| | `db/schema.sql` | Producción | |
|---|---|---|---|
| Tablas | 52 | 52 | ✅ |
| Constraints | 331 | 331 | ✅ |
| Índices | 132 `CREATE INDEX` | 234 `pg_indexes` | ✅ la diferencia son los índices que Postgres crea solo por PK/UNIQUE |
| Triggers `updated_at` | **0** | **36** | 🔴 `schema.sql` NO los trae — se recrean aparte (mig 077, en `migracionAWS/`) |

> En producción hay **45 triggers** no internos: los 36 de `updated_at` + 9 `trg_emp_*` (defaults de `empresa_id` del retrofit multiempresa).

---

## Convenciones de código
- Errores: siempre `AppError(message, code, status_code)`.
- Logs: solo eventos de negocio importantes. Sin `print()` / `console.log()` — logger centralizado.
- Config: solo vía `settings`, nunca `os.environ` directo.
- **Límites de líneas (estrictos)**: router 80 · service 150 · repository 100 · componente React 150 · hook 80 · otros 200. Medir SIEMPRE con `.Count` y **`-LiteralPath`** (no `Measure-Object -Line`, subestima; sin `-LiteralPath` los paths con `[id]` no se leen).
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
14. **Cada repo nuevo es un repo más a portar a asyncpg** (hoy son **54**). Priorizar wires sobre repos existentes; repo nuevo → moldearlo sobre `migracionAWS/empleado_repo_NEW`.
15. **Toda sesión que cambia algo escribe su entrada en `docs/BITACORA-CAMBIOS.md` ANTES de terminar.** Si la sesión termina sin su entrada, la sesión no terminó.

---

## Modelo de roles funcionales (COMPLETO)
Tres roles en `utils/permisos.py`:
- **admin_rrhh** — lectura + escritura en todo.
- **gerencia_lectura** — lectura en todo, escritura en nada.
- **mandos_medios** — lectura + escritura solo en VACACIONES y AUSENCIAS; sin acceso al resto.
- Rol desconocido / None → **fail-closed**.

Núcleo: `puede(rol, seccion, accion)`, `require_permission(seccion, accion)` (dependency factory → `AppError(..., "FORBIDDEN", 403)`). Enum `Seccion` (26 valores). `MANDOS_MEDIOS_SECCIONES = frozenset({VACACIONES, AUSENCIAS})`. **180 gates `Depends(require_permission(...))` en 45 routers.** Espejo front en `frontend/services/permisos.ts`. Sidebar filtra `NAV_GROUPS` por permiso, AuthGuard gatea por ruta, `useCanWrite` oculta botones de escritura.

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
> **Este Flujo 2 es el molde de la base de import compartida.** Lo que falta agregar es el **reader XLSX** (hoy `openpyxl` solo se usa para export).
> 🔴 **Y le falta la auditoría**: `routers/importacion_nomina.py:62` hace el `batch_upsert_nomina` y **no registra ningún evento** — contra la regla propia de "un evento por lote". Ver Deuda técnica.

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

### Superficie de filtros hoy (12 exports, verificada por introspección de `app.routes`)

| Módulo | Filtros del listado = del export |
|---|---|
| empleados | area · proyecto · estado · es_lider · search |
| vacaciones | area · proyecto · empleado · estado · **fecha_desde/hasta** |
| ausencias | area · proyecto · empleado · tipo · **fecha_desde/hasta** |
| auditoría | entidad · evento · usuario · registro · fecha_desde/hasta |
| capacitaciones (asignaciones) | area · capacitación · empleado · estado |
| inventario (asignaciones / ítems) | area · empleado / estado |
| objetivos | estado · prioridad · responsable |
| evaluaciones (evaluados de un lote) | perfil · sector · con_nota · **proyecto** |
| costos/nómina | anio · mes |
| ev_instancias | ciclo · estado |
| proyectos (listado) | area · estado |

### 🔴 DOS TESTS ESTRUCTURALES — son REGLA PERMANENTE, no tests de una feature

Los dos **barren la superficie entera automáticamente**, así que **cualquier export nuevo queda cubierto sin tocar el test**. Los dos llevan **guarda contra el falso verde**.

**1. `tests/test_paridad_list_export.py` — invariante list ↔ export.**
Las rutas salen de **`app.routes`** (introspección de FastAPI), no de una lista escrita a mano. Verifica en las dos direcciones: que el export acepte todo lo que el listado filtra (si no, **el archivo trae más filas de las que se ven en pantalla**, sin error y sin aviso), y que el export no tenga filtros propios (serían inalcanzables desde la UI). Las **dos únicas** diferencias legítimas: `formato` (solo export — es cómo sale el archivo, no un filtro) y `page`/`page_size` (solo listado — **el export NO se pagina, por diseño**).
- **Si un par difiere con motivo legítimo se declara en `_EXPORTS_SIN_LISTADO` CON su razón — nunca se saca el módulo del barrido.** Hoy hay 1: `/api/reportes/{reporte_id}/exportar` (exporta un reporte ya generado por id, no un listado).
- Guardas: `>= 8` exports y `>= 8` pares detectados · ningún export huérfano sin excepción declarada · **ninguna excepción que apunte a una ruta borrada** (una excepción muerta es ruido que oculta el próximo caso).

**2. `tests/test_limite_export.py::TestTodosLosExportsChequean` — barrido del límite de export.**
Barre los **11 services con export** y verifica que cada uno (a) importe `verificar_limite_export` y (b) **lo invoque en el cuerpo de `exportar`** (importarlo no alcanza — se comprueba con `inspect.getsource`). Sin él, el próximo export nace sin control y nadie se entera hasta que un usuario recibe un archivo incompleto.
- Excepciones declaradas con razón: `reporte_export_service` (reporte puntual por id) y `reportes/_reporte_auditoria` (acotado a un mes por construcción, conserva un truncado **declarado** con nota en el archivo).
- Guarda: `assert len(EXPORTS) >= 11`.

> Hay un **tercero, en el front**: `components/layout/nav-config.test.ts` compara `NAV_GROUPS` contra `seccionDeRuta` de `permisos.ts`, también con guarda de mínimo (`>= 20` ítems). Cubre al próximo módulo que se agregue al sidebar.

### `LIMITE_FILAS_EXPORT = 5000` — y por qué (`services/_limite_export.py`)

Antes cada export pedía `page_size=100000` y armaba el archivo con lo que entrara: un pedido más grande salía **incompleto y sin ninguna señal**. Ahora un pedido que lo supera devuelve **422 `EXPORT_DEMASIADAS_FILAS`** con un mensaje para alguien de RRHH (dice cuántas filas dio la consulta, cuál es el máximo, y que use los filtros).

> 🔴 **POR QUÉ 5.000 Y NO 100.000: el techo real de un export NO son las filas, es el TIEMPO — y el 100.000 nunca se alcanzaba.**
> · **30 s** — timeout httpx del cliente de Supabase (`settings.supabase_timeout`). Es el más bajo y el que corta primero.
> · **~8 s** — `statement_timeout` del rol `authenticator` con el que PostgREST se conecta.
> · **120 s** — `statement_timeout` de la instancia. Nunca llega a regir.
> · el límite de Vercel, que además puede no ser el declarado.
> 5.000 es 250× el padrón actual y queda cómodo debajo de todos. **Un número alto "por las dudas" reproduce el mismo bug con otra cara: en vez de un archivo truncado, un timeout sin mensaje.**

Es **constante de módulo, NO variable de entorno**: subirlo exige revisar los techos de tiempo, y eso es una decisión, no configuración.

⚠️ **Alcance real, para no venderlo de más.** En los exports **paginados** (empleados, vacaciones, ausencias, auditoría) el total llega por `count="exact"` y el control actúa **antes** de cargar nada grande. En los **cinco que no paginan** (capacitaciones, inventario ítems, inventario asignaciones, objetivos, ev_instancias) el repo no expone un conteo, así que el chequeo corre sobre la lista ya traída — igual que antes: no hay regresión, pero un volumen que muera por timeout muere antes de llegar acá. Cerrarlo del todo pide un `contar()` por repo: tanda propia.

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

**Por qué no se reusó `ev_*`:** `ev_instancias` tiene `UNIQUE(ciclo_id, empleado_id)` pero el dato real son hasta 6 filas por evaluado (una por tipo de evaluador); `evaluador_id` es FK a persona, el CSV trae un tipo (`AUTOEVALUACION`/`PAR`/…) sin identidad; `puntaje_global` se calcula, acá viene calculado de afuera. UI de `ev_*` borrada; tablas se limpian tras el cutover a AWS.

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

⚠️ **`EliminarLoteButton.tsx` (74 líneas) sigue huérfano** — 0 callers, verificado. Candidato a borrar con el resto del dead code.

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
- 🔴 **Este principio HOY ESTÁ VIOLADO en un lugar**: `services/_costos_write.py:80` audita con la empresa del **header** en vez de la de la entidad afectada. Ver Deuda técnica.

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
- **Vacantes + Candidatos:** `routers/vacantes.py` + `candidatos.py` (+ `_candidato_form.py` público sin auth), `vacante_service.py`, `candidato_service.py`, `cv_service.py`. Integraciones: `zernio_service.py`, `gmail_service.py`. **Vacantes es el patrón canónico de borrado con confirmación** (router DELETE + service con snapshot-antes-de-borrar + fetch crudo por el 204 + `EliminarVacanteButton.tsx` + `ConfirmDialog`). Copiar de acá.
- **Historial salarial (C1):** `costo_service.get_historial_salarial`. 🔑 **La serie de `costos_nomina` ES el historial** — no hace falta el log de cambios: la tabla tiene `UNIQUE (empleado_id, anio, mes)`, o sea una fila por mes. Con auditoría, el caso más común —sueldos importados por CSV y nunca editados a mano— daría **historial vacío teniendo los sueldos cargados**. **DOS barreras, las dos necesarias y distintas:** la de SECCIÓN (`Seccion.COSTOS + READ`, la aplica el router: quién puede ver sueldos) y la de EMPRESA (se aplica en el service, sobre el EMPLEADO objetivo — el `empresa_id` del repo sale del header y no valida a qué empleado apuntás). El front no renderiza la sección sin permiso de costos: una sección que aparece y falla es peor que una que no aparece.
- **Entrevista de salida (C3):** `services/_offboarding_entrevista.py`. Las columnas `entrevista_salida` y `notas_entrevista` existían en DB y estaban **muertas**; ahora se escriben y se leen.
- **Domicilio desglosado (C4, mig 081):** 6 columnas nuevas en `empleados` (`domicilio_calle`, `_numero`, `_piso_depto`, `_localidad`, `_provincia`, `_cp`). **Se conserva el `domicilio` crudo** además de las estructuradas, porque el import de nómina lo trae como texto libre. **`provincia` es una lista cerrada servida por endpoint** (`schemas/_provincias.py` + `routers/empleados_catalogos.py`): el front no la hardcodea.
- **Cesiones** (mig 066): hija de empleado, en la ficha. Gateada por `Seccion.EMPLEADOS`.
- **Proyectos:** asignación single (`proyecto_asignaciones.py`) + bulk multi-selección (`POST /{id}/asignaciones/bulk`, éxito parcial clasificado). **El área filtra candidatos, NO asigna.**
- **ABM usuarios:** solo admin_rrhh. `POST /api/usuarios` (alta + contraseña temporal una sola vez, `must_change_password=true`) · `DELETE` (auto-eliminación bloqueada) · `POST /cambiar-password` (self-service, 10/hora). Migración 063. **Para crear usuarios directo en DB:** crear auth user en dashboard Supabase con Auto Confirm, copiar el UUID, INSERT en `public.users` (hay FK `users.id → auth.users(id)`). Roles: `admin_rrhh`, `gerencia_lectura`, `mandos_medios`.
- **Ownership mandos_medios:** `services/ownership.py` app-level. "A cargo" = `manager_id`, no área ni `es_lider`. Aplicado en las 13 superficies de Vacaciones y Ausencias. Falta RLS a nivel DB (en AWS no va — queda app-level definitivo).
- **Adjuntos (polimórficos, `entidad` + `entidad_id`):** la empresa del adjunto sale de la **entidad PADRE, no del header** — aplicación directa de Vista vs Acción. `services/_adjunto_padres.py::ensure_padre_de_empresa` valida el padre y devuelve **su** `empresa_id` para etiquetar la hija. Resolvers para las 5 entidades que el front usa: `empleado`, `vacacion`, `ausencia`, `vacante`, `offboarding`. Los adjuntos con **`empresa_id` NULL (filas legacy) están bloqueados en TODOS los modos**, incluido el consolidado. ⚠️ `entidad_tipo` **`"evaluacion"` queda fail-closed con `ENTIDAD_INVALIDA` (400)**: está mapeado a una Sección pero **no tiene repo resolver** (no se definió a qué apunta) y tiene **0 callers**. Definir antes de habilitarlo.

---

## Staging de migración a AWS (`migracionAWS/`)
Carpeta **aislada** para migración de Supabase a **AWS (asyncpg/RDS + S3)**. Código nuevo sin tocar `backend/` en producción. Contiene `*_NEW.py` (auth completo, `postgres_client.py` asyncpg, repos-molde `empleado_repo_NEW`, `empleado_lookup_repo_NEW`, `token_repo_NEW`) + migraciones 075 (password_hash), 076 (refresh_tokens), 077 (recrear 36 triggers `updated_at`) + docs (`MIGRACION_A_RDS.md`, `README_AUTH.md`, `settings_ADD.md`). El otro dev ejecuta la infra.

**Decisiones cerradas:** se recrean los triggers · **NO hay RLS** (seguridad app-level) · no se carga demo data.

**Minas ya desactivadas (para el otro dev):**
- asyncpg devuelve UUID nativos → cast `str()` explícito en mappers.
- FK `users.id → auth.users(id)` bloquea INSERT sin Supabase → dropear + `DEFAULT gen_random_uuid()`.
- El `ON DELETE CASCADE` contra `auth.users` es lógica de negocio viva.
- `passlib` roto (bcrypt 5.0 sacó `__about__`) → usar `import bcrypt` directo.
- `schema.sql` no trae los 36 triggers `updated_at`.
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

### `tsc` en 0 y `next build` verde
`next dev` con Turbopack transpila sin type-check → errores de tipo pasan desapercibidos pero **`next build` falla**. `vitest` cubre hoy 143 tests en 10 archivos, pero **la mayor parte del front sigue sin test**: `tsc` sigue siendo la red principal. **Regla: `node_modules/.bin/tsc --noEmit` tiene que dar 0. Si aparece un error, es tuyo.**
> ⚠️ vitest corre con `environment: "node"` y **sin jsdom**: los tests de componentes usan `renderToStaticMarkup` y verifican el **markup**, no la interacción — y **no ejecutan `useEffect`**. Ver el caso #4 de "Un test solo prueba lo que el fake puede desmentir".

### 🚨 Módulos desactivados (assessment y sucesión)

Hay **dos módulos apagados a propósito**. En los dos el código está **entero**: se sacó el punto de entrada, no se borró nada.

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

- **El import de costos no audita nada.** `routers/importacion_nomina.py:62` hace el `batch_upsert_nomina` y no registra ningún evento — **contra la regla propia de "un evento por lote"**. El Flujo 1 (nómina de empleados) sí audita. Un import de costos hoy es invisible en `/auditoria`. Barato de cerrar: un `payload_carga_nomina` de lote, igual que evaluaciones.
- **`_costos_write.py:80` audita con la empresa del HEADER, no con la de la entidad afectada.** El presupuesto hereda su `empresa_id` del área, pero el evento se etiqueta con `X-Empresa-Id` — que en modo consolidado es `None`. **Viola Vista vs Acción** (auditar es una ACCIÓN: la empresa sale de la entidad).
  > ⚠️ **Corrección respecto de cómo estaba anotado:** en producción hay **cero** eventos `set_presupuesto` y **cero** `carga_nomina`, así que esta línea todavía **no etiquetó mal nada**. Los **9 eventos con `empresa_id NULL`** que sí existen son otros: `alta_usuario` ×3 y `cambio_password` ×3 (legítimos — los usuarios no cuelgan de una empresa, es la decisión de producto documentada) y **3 que sí están mal etiquetados**: `alta_adjunto`, `baja_adjunto` (los dos sobre una **vacante**, que sí tiene empresa) y `baja_candidato`. Con **una sola empresa** en producción un desajuste header-vs-entidad no se puede distinguir todavía; **se va a volver visible el día que exista la segunda.** Cerrar el patrón antes de eso.
- **`objetivos.responsable_id` es FK a `users`, no a `empleados`** (verificado en el catálogo). Bloquea el filtro por área y el import de objetivos: un objetivo no se puede colgar de un empleado ni ubicar en un área. **Con 0 filas la migración es trivial; con datos cargados es cara.** 🚩 **Hacerlo AHORA o asumir el costo después.** (Es el §4.1 del Plan: falta definir el alcance del rediseño.)
- **Filtro por provincia/localidad — pendiente hasta que haya domicilios cargados.** Las 6 columnas existen (mig 081) y `provincia` ya es una lista cerrada servida por endpoint, así que el filtro es barato; hoy no tendría nada que filtrar.
- **Filtros duplicados front+back** (patrón recurrente): si un filtro afecta el export, va **server-side, una sola implementación**. Casos abiertos: `aplicar_filtro_estado` es espejo de `derive_estado` (merece un test que las compare); el listado de evaluaciones filtra client-side y exporta server-side (aceptable a ~30 filas, el endpoint ya acepta los filtros).
- **`permisos.ts` es espejo manual de `permisos.py`** — riesgo de divergencia. (La divergencia sidebar↔guard **sí** tiene test; esta no.)
- **`_postgrest_schema` cubre los generadores de reportes, no todo el repo** — toda query con `select` anidado fuera de ese barrido sigue siendo punto ciego. Verificar en producción tras el deploy.

### ✅ Resueltos (verificados uno por uno — NO reabrir)
- ✅ **Fuga entre empresas — CERRADA (Fase 2).** Ver "Patrón de barrera de empresa".
- ✅ **`confirmar()` de evaluaciones — RESUELTO (Fase 0.2).** Período temporal + verificación por conteo.
- ✅ **Auditoría de nómina silenciosa — RESUELTA (Fase 0.1).** uuid4 de evento.
- ✅ **N+1 de sucesión — RESUELTO (Fase 3, `51832e2`).** Con 200 empleados: de 201 requests a 2.
- ✅ **Diff fantasma de auditoría — RESUELTO (Bloque C).** `sin_derivados`. Ver "Audit log".
- ✅ **6 de 11 reportes rotos en producción — RESUELTO (Bloque C).** + `tests/_postgrest_schema.py` para que no vuelva.
- ✅ **`fetchEmpleados` posicional — RESUELTO (Fase 3).** Objeto de opciones sobre `EmpleadosFiltros`.
- ✅ **`page_size=100000` en export — RESUELTO (B7).** `LIMITE_FILAS_EXPORT = 5000` + aviso 422. **En el código ya no queda ningún `100000`** (solo referencias en docs y en demo data SQL).
- ✅ **`middleware/auth.py` aceptaba cualquier UUID como `X-Empresa-Id` — RESUELTO (A3).** `utils/empresas_cache.py`.
- ✅ **Posicionales de `services/vacaciones.ts` y `ausencias.ts` — RESUELTO (B2).** Los cuatro (`fetchVacaciones`, `exportarVacaciones`, `fetchAusencias`, `exportarAusencias`) toman `filtros: VacacionesFiltros/AusenciasFiltros`, y listado y export comparten el traductor `queryVacaciones`/`queryAusencias`. **Ya no hay filtros posicionales corridos entre hermanas.** (`page`/`pageSize` siguen posicionales en los `fetch*`, lo cual es correcto: el export no se pagina.)
- ✅ **`state` de OAuth adivinable — RESUELTO (A4).** Nonce de un solo uso.
- ✅ **Assessment expuesto sin auth — RESUELTO (A1).** Router desmontado + regex gateada.

### Líneas — **REMEDIDO contra el código el 28/7/2026** (`-LiteralPath`, `.Count`)

> **Hubo ~15 divisiones esta semana.** Ya NO están over-limit: `empleado_repo.py` (174 → **98**) · `integracion_service.py` (201 → **110**) · `_audit_payloads_rrhh.py` (189 → **149**) · `nomina_repo.py` (107 → **98**) · `offboarding_repo.py` (**87**) · `costo_service.py` (150 → **141**) · `vacaciones_service.py` (150 → **116**) · `proyectos_repo.py` (104 → **74**) · `routers/evaluaciones_resultados.py` (80 → **69**) · `routers/costos.py` (**76**) · `routers/vacaciones.py` (**72**) · `reportes/page.tsx` (539 → **35**) · `proyectos/page.tsx` y `empleados/[id]/page.tsx` (ya no superan 150).

**Frontend — 38 archivos > 150** (sin contar los `.test.*`):
`costos/page.tsx` **624** · `vacantes/[id]/page.tsx` **577** · `onboarding/templates/[id]/page.tsx` 412 · `onboarding/page.tsx` 410 · `configuracion/page.tsx` 390 · `ImportarNominaCSVModal.tsx` 377 · `offboarding/page.tsx` 307 · `onboarding/templates/page.tsx` 290 · `NominaModal.tsx` 287 · `areas/page.tsx` 261 · `evaluacion/[token]/page.tsx` 258 · `VacanteModal.tsx` 251 · `AIPanel.tsx` 249 · `assessment/page.tsx` 233 · `empresas/[id]/page.tsx` 230 · `EmpresaModal.tsx` 226 · `vacantes/page.tsx` 217 · `CampanaModal.tsx` 208 · `AreaModal.tsx` 207 · `EmpresaAreasTab.tsx` 206 · `empresas/page.tsx` 204 · `login/page.tsx` 201 · `NineBox.tsx` 198 · `auditLabels.ts` 198 · `AsignacionModal.tsx` 192 · `CapacitacionModal.tsx` 192 · `assessment/[id]/page.tsx` 192 · `OnboardingChecklist.tsx` 186 · `CandidatoModal.tsx` 181 · `empleados/modal/_constants.ts` 175 · `ArbolProyecto.tsx` 170 · `ItemModal.tsx` 161 · `ObjetivoModal.tsx` 156 · `CatalogoTab.tsx` 153 · `MapaVacaciones.tsx` 152 · `ItemsTab.tsx` 152.
> Dos de los 38 son primitivos generados de **shadcn/ui**, no código nuestro: `dropdown-menu.tsx` 268 y `dialog.tsx` 160. **No cuentan como deuda.** Los dos objetivos grandes siguen siendo `costos/page.tsx` (624) y `vacantes/[id]/page.tsx` (577) — copiar el corte de `components/features/sucesion/`.

**Backend over-limit:**
- **Services (>150):** `_audit_payloads.py` **167** · `reporte_anual.py` **154**.
- **Repos (>100):** `ev_instancias_repo.py` **146** · `costo_repo.py` **135** · `assessment_repo.py` **130** · `ev_plantillas_repo.py` **129**.
- **Routers: ninguno over-limit** (el máximo es 80/80).
> `costo_repo` (135) y `assessment_repo` (130) siguen siendo **legacy con CERO callers** — verificado: solo aparecen en su propio archivo, en `db/schema.sql` y en un comentario de `test_assessment_vacantes_scope.py` que dice explícitamente que son el código muerto. `costo_service` usa `nomina_repo`/`periodo_repo`/`presupuesto_repo`. Candidatos a borrar, junto con `EliminarLoteButton.tsx` (74, 0 callers).

**En/al límite EXACTO (el próximo cambio EXIGE dividir primero):**
- **Services 150/150:** `gmail_service.py` · `assessment_service.py`. **A 149:** `_audit_payloads_rrhh.py` · `vacante_service.py` · `usuario_service.py` · `adjunto_service.py` · `ev_instancias_service.py` · `offboarding_service.py`.
- **Repos 100/100:** `vacaciones_repo.py` · `onboarding_repo.py` · `evaluacion_repo.py` · `inventario_asignaciones_repo.py`. **A 99:** `objetivo_repo.py` · `planes_carrera_repo.py`.
- **Routers 80/80:** `vacantes.py` · `adjuntos.py`. **A 79:** `objetivos.py` · `inventario_items.py` · `asignaciones_capacitacion.py`.

**Cortes ya identificados (para no re-diagnosticar):**
- `gmail_service.py` → extraer el parseo a **`_gmail_parseo.py`** (va con el Bloque E1).
- `objetivos.py` e `inventario_items.py` (79) → al dividirlos, **agregarles `shared_limit("30/hour", scope="export")`**; hay un test que lo recuerda.
- `evaluacion_repo.py` (100) y su router → los pide el Bloque D1 (estadísticas cross-lote).
- ✅ Ya hecho: `vacaciones_service.py` → `_vacaciones_write.py` (77), simétrico con `_ausencias_write.py` (110).

### Al margen por decisión (NO tocar)
- **S6 / DROP de `cargo` y `rol`** → no se borra nada (decisión de producto). Fallbacks `roles[0] ?? cargo` quedan.
- **Campo `equipo`** (texto libre): sin tabla `equipos`, "asignar/importar por equipo" no existe.
- **Tablas huérfanas** (`assessment_reportes`, `configuracion_empresa`, `documentos_empleado`, `notificaciones`, `notificaciones_config`, `sucesion_posiciones`): se limpian **después del cutover a AWS**.
- **"Compatibilidad con una posición"** (sucesión): feature nunca construida, no deuda técnica. El ranking es por assessment genérico. Cuando RRHH la reclame, definir qué significa compatibilidad antes de improvisar.

### Tests
- **Backend: 975 passed** en **61 archivos `test_*.py`** (+ `tests/_postgrest_schema.py`, que es helper, no test). `pytest -q` desde `backend/` con `venv`.
- **Front: `npm test` (= `vitest run`) — 143 tests en 10 archivos**: `services/filtros-export.test.ts` 31 · `components/layout/nav-config.test.ts` 25 · `components/features/auditoria/auditLabels.test.ts` 18 · `components/ui/FiltersBar.test.tsx` 18 · `components/features/shared/filtros.test.ts` 12 · `hooks/useCanWrite.test.ts` 10 · `components/features/empleados/ficha/_domicilio.test.ts` 9 · `services/empleados.test.ts` 8 · `HistorialSalarialSection.test.tsx` 7 · `components/features/export/ExportMenu.test.ts` 5. **La cobertura sigue siendo parcial** — `tsc` sigue haciendo falta.
- **Los tres barridos estructurales** (paridad list↔export, límite de export, nav↔permisos) cubren automáticamente lo que se agregue. **Todos llevan guarda de mínimo.**
- Adjuntos: 11 tests unit con `_FakeRepo` + storage monkeypatcheado. **E2E real nunca se ejecutó** (`_BUCKET="documentos"` hardcodeado apunta a prod). Decisión: E2E automatizado en el cutover a AWS/S3.
- 🚨 **Antes de dar un test por bueno, contestar: ¿qué tendría que ser distinto en el fake para que pueda fallar?** Ver la sección "Un test solo prueba lo que el fake puede desmentir".

### En pausa
- **Link público de carga de horas** (E4) — mockup HTML aprobado. Bloqueado: requiere la reunión de definición.
- **Limpieza general del repo** (Bloque G): dead code (`costo_repo`, `assessment_repo`, `EliminarLoteButton.tsx`), los tres duplicados de la raíz, y el filtro `empresa` duplicado 8× entre repos. No urgente.

---

## Git
- Operar siempre desde la raíz del repo, `RRHH/`.
- **Commits los hace Franco manualmente** (nunca Claude Code). Commits y push desacoplados: no hay push hasta que Franco lo decida. Preferir commits por sub-sesión.
- Formato convencional (`feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `test:`).
- Solo `main` y `origin/main`. Sin ramas sueltas.

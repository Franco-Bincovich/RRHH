# SMOKE-TEST — test de humo profundo del backend

> **Qué es:** un script que le pega a **toda la superficie HTTP del backend real**, enumerando las
> rutas desde `app.routes`, y clasifica cada endpoint en ROTO / SOSPECHOSO / NO PROBADO / OK.
> **Read-only.** Vive en `backend/scripts/smoke_test.py` y se corre cuantas veces se quiera.

## Por qué existe

La suite tiene **1117 tests** y **no detectó** los 6 reportes rotos, el listado de plantillas de
onboarding roto, ni el KPI que leía una columna vacía. No es que los tests estuvieran mal escritos:
es estructural. El fake de Supabase implementa `select(*a, **k)` **ignorando el argumento**, así que
acepta cualquier spec de columnas —exista o no la columna— y no replica la resolución de FKs de
PostgREST. Un `areas(nombre)` ambiguo que PostgREST rechaza con **PGRST201**, el fake lo acepta.

`tests/_postgrest_schema.py` cerró parte del agujero validando los generadores de reportes contra
`db/schema.sql`. Lo que queda afuera es toda query que no pase por ese barrido — y la única forma de
encontrar esa familia de bugs es **pegarle al PostgREST real**. Eso es esto.

**RRHH está por empezar a testear sobre datos reales. Esto tiene que correr antes.**

---

## 1. Cómo correrlo

```bash
cd backend

# Solo lo que no necesita token: barrido de 401 + rutas públicas. Corre siempre.
./venv/bin/python scripts/smoke_test.py --sin-auth

# Completo, con los GET autenticados
export SMOKE_TOKEN="eyJhbGci..."
./venv/bin/python scripts/smoke_test.py \
    --conteos scripts/conteos_produccion.json \
    --salida ../docs/SMOKE-TEST-RESULTADOS.md
```

| Flag | Para qué |
|---|---|
| `--base URL` | backend a probar. Default: `https://sofia-backend-pi.vercel.app` |
| `--conteos ARCHIVO` | JSON `{tabla: filas}` — sin esto, un endpoint vacío es SOSPECHOSO y no ROTO |
| `--salida ARCHIVO` | escribe el reporte markdown |
| `--sin-auth` | omite los GET autenticados; no pide token |

Sale con **código 1** si hay algún ROTO, así que sirve como gate en un pipeline.

### Cómo obtener el token

El JWT lo firma Supabase con **ES256** y el middleware lo valida contra el JWKS público, así que
**no se puede generar a mano ni con el `JWT_SECRET`**. Tiene que ser un login real. Dos formas:

**A. Desde el navegador (la más rápida).** Entrá a https://www.hrkarstec.site, logueate, abrí la
consola del navegador y pegá:

```js
JSON.parse(localStorage.getItem("sb-grmdiwxcvcjorlohpwji-auth-token")).access_token
```

**B. Por API,** con las credenciales de un usuario `admin_rrhh`:

```bash
curl -s -X POST https://sofia-backend-pi.vercel.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"...","password":"..."}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])"
```

⚠️ **El token dura ~1 hora.** Si vence a mitad de la corrida los endpoints empiezan a dar 401 y el
reporte se llena de ROTO falsos. El script chequea el token **antes** de empezar y aborta con un
mensaje claro si no sirve, pero no puede detectar un vencimiento a mitad de camino: si ves muchos
401 seguidos, sacá un token nuevo y volvé a correr.

### Regenerar los conteos

`scripts/conteos_produccion.json` es una **foto** de cuántas filas tiene cada tabla. Es lo que
permite distinguir "vacío porque no hay datos" de "vacío porque está roto".

🔴 **Hay que regenerarlo cuando RRHH cargue datos.** Un conteo viejo que dice `0` convierte un
endpoint roto en OK — es el falso verde que este script existe para evitar. El SQL está en el
encabezado del propio archivo; se corre contra el proyecto Supabase `grmdiwxcvcjorlohpwji`.

---

## 2. Qué cubre, y cómo

| # | Cobertura | Cómo |
|---|---|---|
| 1 | **Enumeración completa** | `app.routes` por introspección. **Nunca una lista escrita a mano**: un endpoint nuevo queda cubierto solo. Guarda `MINIMO_RUTAS = 150`: si la enumeración se rompe, el script **aborta** en vez de reportar verde sobre nada |
| 2 | **Todos los GET** | status + tiempo + cuántos elementos devolvió |
| 3 | **Endpoints de detalle** | resuelve un **id real** del listado correspondiente y después pega al detalle. Es lo que hace profundo al test: los `/{id}` son los que nunca se prueban, y donde viven los embeds de PostgREST. Sin filas → **NO PROBADO**, nunca OK |
| 4 | **Modo consolidado** | cada GET **dos veces**: con `X-Empresa-Id` y sin él. Son dos caminos de código (`empresa_id=None` no restringe) y el consolidado casi nunca se ejercita |
| 5 | **Reportes** | los 14 del catálogo, con y sin filtro de área. El filtro cambia la query — ahí vivía el bug de ausentismo |
| 6 | **Exports** | que devuelvan un archivo y no un error; se registra tamaño y content-type |
| 7 | **Auth en runtime** | **cada** endpoint sin token → 401. Distinto del barrido estático de Fase 2: verifica el comportamiento real. Y las públicas declaradas: que sigan alcanzables, y que **solo** esas lo sean |
| 8 | **Tiempos** | por endpoint. Primera medición real de performance del repo |

### La clasificación

| | Significa |
|---|---|
| 🔴 **ROTO** | 5xx · 4xx inesperado · **vacío teniendo filas en la base** · sin token devolvió algo distinto de 401 |
| ⚠️ **SOSPECHOSO** | más de 3 s · vacío sin poder confirmar si es normal |
| ⬜ **NO PROBADO** | no se pudo ejercitar, **con el motivo** |
| ✅ **OK** | respondió lo esperado |

🔴 **La distinción NO PROBADO vs OK es lo que hace honesto al reporte.** Un endpoint de detalle sin
una sola fila para resolver el id **no está OK**: está sin ejercitar. Marcarlo verde es cómo un
reporte de humo se convierte en un papel que nadie puede usar.

### 🔴 Cero escrituras

Se corre contra **producción, con datos reales**. El script **solo emite GET**. Las 107 rutas de
escritura se tocan **únicamente** en el barrido de auth y **sin token**: el `AuthMiddleware` responde
401 **antes de enrutar**, así que ningún handler llega a ejecutarse y nada puede persistir. Es la
única excepción, está acotada a `_smoke_barridos.barrer_auth` y documentada ahí.

---

## 3. Resultados de la última corrida

_Corrida autenticada: 2026-07-30 · base `https://sofia-backend-pi.vercel.app` · 199 rutas · empresa activa DOSUBA_

**🔴 4 ROTO · ⚠️ 2 SOSPECHOSO · ⬜ 62 NO PROBADO · ✅ 290 OK** (358 verificaciones sobre 199 rutas)

La tabla completa por módulo está en **`docs/SMOKE-TEST-RESULTADOS.md`**, que el script regenera.

### 🔴 Hallazgos — 2 endpoints, 4 verificaciones

#### 1. `GET /api/vacaciones-pendientes` → 500 · **la migración 083 no corrió y el código sí está deployado**

Verificado contra el catálogo: `vacaciones_pendientes` **no existe** y `solicitudes_vacaciones` **no
tiene `periodo` ni `dias_liquidados`**. El código que las usa está en producción (HEAD `98cb9a0`).

🔴 **Es la violación exacta del orden de deploy que la bitácora advirtió**, y el listado de
pendientes es el síntoma menor. El grave no aparece en este reporte porque el smoke no escribe:
`_vacaciones_write_repo.guardar` incluye `periodo` y `dias_liquidados` en el INSERT, así que
**registrar una vacación tiene que estar fallando en producción ahora mismo**. Es certeza del
código más el catálogo, no una hipótesis — pero no se puede confirmar sin un POST, y esto es
read-only sobre datos reales.

**Arreglo: correr `backend/migrations/083_vacaciones_periodo_y_pendientes.sql`.** Nada de código.

> El listado de vacaciones **sí** funciona (`GET /api/vacaciones` dio 200): `find_all` hace
> `select("*")` sin nombrar las columnas nuevas, y el schema las tiene con default. Por eso la
> rotura pasa desapercibida hasta que alguien intenta cargar una.

#### 2. `GET /api/sucesion/planes` → 500 · **nombre de constraint inexistente en un embed**

`repositories/planes_carrera_repo.py:16` pide el embed
`planes_carrera_hitos!planes_carrera_hitos_plan_emp_fkey(estado)`, pero **esa constraint no existe**:
la real se llama **`pc_hitos_plan_emp_fkey`** (verificado en `pg_constraint`). PostgREST no la
resuelve y el endpoint revienta.

🔴 **Es exactamente la familia de bugs que motivó este script**, y la razón por la que 1117 tests no
lo vieron: el fake de Supabase acepta cualquier spec de `select`. Es el mismo error de los 6
reportes rotos, en un módulo que `tests/_postgrest_schema.py` no barre (solo cubre los generadores
de reportes). Preexistente, no de esta semana.

**Arreglo: `planes_carrera_hitos_plan_emp_fkey` → `pc_hitos_plan_emp_fkey`.** Una palabra.
Y conviene extender el barrido de `_postgrest_schema` más allá de los reportes.

### ⚠️ Sospechosos — 1 endpoint

`GET /api/integraciones/google/auth` → **503 `GOOGLE_NOT_CONFIGURED`**. No es un crash: es la app
diciendo que Google OAuth no tiene credenciales en producción (coherente con
`usuario_integraciones` = 0 filas). Bloquea el CV screening del Bloque E. **No hay nada que
arreglar en el código** — es configuración que falta.

### ⬜ Los 62 NO PROBADO, por qué

| Motivo | Cuántos |
|---|---|
| **Sin filas para resolver un id real** — todo lo que cuelga de las tablas vacías (vacaciones, ausencias, costos, capacitaciones, inventario, objetivos, onboarding, offboarding, candidatos) | 34 |
| **Requiere query params que el smoke no provee** — `/api/adjuntos` pide `entidad`+`entidad_id`, `/api/costos/nomina` pide `anio`+`mes`, `/api/sucesion/analisis` pide `area_id`, etc. | 20 |
| **429: el barrido agotó su propia franja de rate limit** (ver Limitaciones) | 5 |
| **La plataforma no enruta el path** — `/docs`, `/docs/oauth2-redirect`, `/openapi.json` | 3 |

🔴 **Ninguno de esos 62 está OK.** Los 34 del primer grupo se cubren solos cuando RRHH cargue
datos; los 20 del segundo piden enseñarle al script qué params mandar, y son la mejora más
valiosa que le queda.

### ✅ Lo que sí quedó verificado

- **Las 196 rutas publicadas devuelven 401 sin token.** Ni un endpoint desprotegido en 199 rutas.
- **Los 14 reportes responden 200, con y sin filtro de área.** Es la zona donde aparecieron 6
  rotos la semana pasada: **hoy están sanos**, y el filtro de área —que arma joins e embeds
  distintos— no rompe ninguno.
- **El modo consolidado (sin `X-Empresa-Id`) funciona en todos los GET probados.** Ese camino
  (`empresa_id=None` no restringe) casi nunca se ejercita y no dio una sola diferencia de status.
- **Los exports devuelven archivo.** En una corrida previa de esta sesión, **22 de 24** llamadas a
  export retornaron un archivo con su content-type correcto; las 2 restantes cayeron por rate
  limit, no por error.
- **Los endpoints de detalle con datos** (empleados, empresas, áreas, proyectos, cesiones,
  evaluaciones) responden 200 con el id resuelto del listado.

### Falsos positivos que la corrida produjo, y qué se corrigió en el script

Los anoto porque un reporte con ruido se deja de leer:

| Se reportaba | Era | Corrección |
|---|---|---|
| 14 endpoints ROTO por **422** | Falta un query param **requerido** que el script no manda | 422 → NO PROBADO, listando qué params pide |
| `/api/integraciones/google/auth` ROTO por **503** | Condición de negocio manejada (`GOOGLE_NOT_CONFIGURED`) | 5xx **con** el contrato `{error,message,code}` y un code propio → SOSPECHOSO; solo `INTERNAL_ERROR` o un 5xx sin contrato es ROTO |
| `/api/vacaciones/exportar` ROTO por **429** | El propio barrido agotó la franja de export | 429 → NO PROBADO |
| `/docs`, `/openapi.json` ROTO por **404** | La plataforma no los enruta | NO PROBADO |
| `/api/integraciones/google/callback` "DESPROTEGIDO" | Está **declarada pública** | La lista de públicas se **importa** de `middleware.auth.PUBLIC_ROUTES` |

## 4. Los tiempos

Primera medición real de performance del repo, **con base de datos incluida** (corrida autenticada).

**Todo respondió por debajo de 0,7 s. Ningún endpoint pasó de 3 s** — ni de 1 s, de hecho. Eso vale
para el presupuesto del import: la latencia por request contra este backend es de **~0,2–0,7 s**, y
el import de nómina hace 2–8 consultas por fila, no requests HTTP.

⚠️ **Con 19 empleados y casi todas las tablas vacías.** Estos números son el piso, no una
proyección: los endpoints que hoy devuelven listas vacías no están pagando ningún costo de datos.
Hay que volver a medir cuando RRHH cargue.

Dato aparte: **el primer request tras inactividad tardó 5,2 s** (cold start de la función
serverless). No aparece en la tabla porque fue un `/health` previo al barrido, pero es lo que va a
sentir el primer usuario de la mañana.

## Los 10 más lentos

| # | Endpoint | Tiempo | Veredicto |
|---|---|---|---|
| 1 | `GET /api/dashboard [empresa]` | **0.67s** | ✅ |
| 2 | `GET /api/procesos [consolidado]` | **0.63s** | ✅ |
| 3 | `GET /api/procesos [empresa]` | **0.61s** | ✅ |
| 4 | `GET /api/dashboard [consolidado]` | **0.57s** | ✅ |
| 5 | `GET /api/integraciones/google/callback` | **0.52s** | ✅ |
| 6 | `GET /api/adjuntos` | **0.48s** | ✅ |
| 7 | `GET /api/empleados/{id} [consolidado]` | **0.41s** | ✅ |
| 8 | `GET /api/integraciones/google/callback [empresa]` | **0.39s** | ✅ |
| 9 | `GET /api/organigrama/proyectos [empresa]` | **0.34s** | ✅ |
| 10 | `GET /api/organigrama/proyectos [consolidado]` | **0.33s** | ✅ |

---

## 5. Qué NO cubre, y por qué

| No cubre | Por qué |
|---|---|
| **Escrituras** (107 rutas: POST/PUT/PATCH/DELETE) | Corre contra producción con datos reales. Ninguna se ejercita más allá del 401 sin token. Probar que rechazan input inválido exigiría llegar al handler, y un bug en la validación escribiría de verdad |
| **Roles `mandos_medios` y `gerencia_lectura`** | 🔴 **No se pueden probar hoy: los 4 usuarios de producción son `admin_rrhh`.** Así que todo el modelo de permisos se ejercita desde el rol más amplio y **las restricciones de los otros dos quedan sin verificar en runtime**. Peor para `mandos_medios`: su ownership depende de `manager_id` (0/19) y de `empleados.user_id` (0/19), así que incluso creando el usuario vería 0 filas y no se sabría si es el gate o la falta de datos |
| **Los módulos apagados** | `assessment` no se monta (`ASSESSMENT_ENABLED=false`), así que sus rutas no están en `app.routes` y no se enumeran. `sucesión` sí está montada en el backend (solo el front la esconde) y **sí** se prueba |
| **El contenido de los reportes** | Verifica que un reporte responda 200 y traiga datos, no que los números sean correctos. Un reporte que devuelve totales equivocados pasa como OK |
| **Endpoints de detalle sin datos** | Con 0 filas no hay id real que probar → NO PROBADO. Hoy afecta a todo lo que cuelga de las tablas vacías (vacaciones, ausencias, costos, capacitaciones, inventario, objetivos, onboarding, offboarding). **Van a quedar cubiertos solos cuando RRHH cargue datos y se vuelva a correr** |
| **El front** | Solo backend. Un endpoint que responde 200 con una forma que el front no sabe leer pasa como OK |
| **Concurrencia y carga** | Un request a la vez, secuencial |
| **Endpoints con query params requeridos** | 20 quedan NO PROBADO porque el script no sabe qué mandarles (`entidad`+`entidad_id`, `anio`+`mes`, `area_id`…). Es la mejora más valiosa que le queda al script |
| **Dos corridas en la misma hora** | 🔴 Los exports comparten una franja de **30/hora** (`scope="export"`) y el barrido consume 24 por corrida. La segunda corrida dentro de la misma hora hace 429 en los exports y los reporta NO PROBADO. **Si necesitás verificar exports, corré una vez y esperá la hora** |
| **Escrituras rotas** | El smoke no escribe, así que **no puede detectar una escritura rota**. El caso vivo lo prueba: el 500 de `/api/vacaciones-pendientes` es el síntoma menor de la 083 sin correr; que registrar una vacación esté roto se deduce del código, no se observa |

---

## Archivos

| Archivo | Qué es |
|---|---|
| `backend/scripts/smoke_test.py` | CLI + orquestación + reporte markdown |
| `backend/scripts/_smoke_barridos.py` | los tres barridos (auth, públicas, GET). Todo lo que emite requests |
| `backend/scripts/_smoke_rutas.py` | enumeración, guarda de mínimo, resolución de ids, mapa endpoint→tabla |
| `backend/scripts/_smoke_reporte.py` | clasificación de veredictos y salida |
| `backend/scripts/conteos_produccion.json` | foto de filas por tabla — **regenerar cuando haya datos** |

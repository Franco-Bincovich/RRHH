# Bitácora de cambios — impacto en infraestructura

**Qué es:** un log corrido de cada sesión de trabajo, ordenado de más reciente a más antiguo,
que declara **qué cambió y qué tiene que hacer infraestructura al respecto**. No es un
historial de features ni un resumen de commits: es la lista de cosas que rompen, condicionan
o requieren acción del lado del deploy.

**Para quién:** el dev que está montando la infraestructura en AWS en paralelo. La idea es
que se entere de todo lo que le afecta **sin tener que leer los commits ni el código**.

**No reemplaza a [`CHANGELOG.md`](CHANGELOG.md)**, que es por versión y orientado al producto.
Este documento es por sesión y orientado al impacto operativo. Los dos conviven.

## Regla de actualización

> **La entrada se escribe en la MISMA sesión que el cambio, nunca después.**

Una bitácora que se completa "cuando haya tiempo" es una bitácora que miente: el otro dev la
lee creyendo que está al día y deploya contra información vieja. Si una sesión termina sin su
entrada, la sesión no terminó.

## Formato

```
## AAAA-MM-DD · <título corto> · commit <hash>
**Qué cambió:** 2-4 líneas en prosa.
**Impacto en infraestructura:** "Ninguno." o la lista de los puntos afectados.
```

**Puntos que SIEMPRE hay que revisar y declarar si aplican** (si ninguno aplica, va "Ninguno."):

- **Migraciones** nuevas — número, qué hacen, si son destructivas, si requieren orden
- **Variables de entorno** nuevas, renombradas, o con valor distinto en producción
- **Dependencias** nuevas o versiones fijadas (`requirements.txt` / `package.json`)
- **Buckets de Storage** nuevos, o cambio de uso de uno existente
- **Endpoints nuevos**, marcando en especial los **PÚBLICOS** (sin auth)
- **Procesos que NO corren en serverless** — jobs periódicos, tareas de fondo, operaciones
  que superen 60s
- **Cambios en el modelo de autenticación** o en los claims del token
- **Dependencias de una URL o dominio concreto** — CORS, callbacks OAuth, webhooks

---

## 2026-07-27 · Filtro por área en proyectos e inventario · commits `<pendiente>` ×3

**Qué cambió:** los dos módulos pasaron a poder acotarse por área, y proyectos ganó además el
filtro de empresa que le faltaba en la UI. En inventario el área se resuelve a empleados y
acota las asignaciones vigentes. En proyectos la semántica es distinta y está documentada en
`repositories/_area_scope.py`: un proyecto no tiene área, así que el filtro devuelve los que
tienen **al menos un empleado asignado** de esa área. Antes se dividieron tres archivos que
estaban en su límite o pasados.

**Impacto en infraestructura:** Ninguno.

*(Sin migraciones, sin variables de entorno, sin dependencias, sin buckets, sin endpoints
nuevos ni removidos —`area_id` es un query param opcional más—, sin cambios en el modelo de
auth ni en los claims del token. Un cliente que no mande el filtro recibe exactamente lo de
antes.)*

> **Nota de consultas, no acción:** el filtro de proyectos agrega **dos queries batch fijas**
> (`empleados` por área, `proyecto_asignaciones` por esos empleados) que **no escalan con la
> cantidad de proyectos** — hay un test que fija el conteo en 2 incluso con 200 asignaciones.
> Cuando haya volumen, las columnas candidatas a índice son `empleados.area_id` y
> `proyecto_asignaciones.empleado_id`. No hace falta anticiparlo.

---

## 2026-07-27 · Exponer filtros que el backend ya aceptaba · commits `<pendiente>` ×2

**Qué cambió:** tres filtros que el backend aplicaba desde antes pasaron a tener control en la
pantalla: **liderazgo** en empleados, **empleado** y **capacitación** en asignaciones de
capacitación, y **empleado** en asignaciones de inventario. No se tocó ni una línea de backend:
lo único que faltaba era el punto de entrada y que el wrapper del front los mandara también al
export. Antes, `capacitaciones/AsignacionesTab.tsx` se dividió (211 → 87 + una tabla
presentacional de 122).

**Impacto en infraestructura:** Ninguno.

*(Cambios de frontend salvo por los tests. Sin migraciones, sin variables de entorno, sin
dependencias, sin buckets, sin endpoints nuevos ni removidos —los tres filtros ya existían como
query params—, sin cambios en el modelo de auth ni en los claims del token.)*

> **Nota de expectativas, no de infraestructura:** los tres filtros funcionan pero hoy **no
> tienen datos que cortar**. En producción: 0 capacitaciones, 0 asignaciones de capacitación,
> 0 asignaciones de inventario, y los 19 empleados con `es_lider = false` (o sea que "Solo
> líderes" devuelve 0). La capacidad quedó entregada; el valor aparece cuando RRHH cargue
> datos. **Si alguien prueba estas pantallas y las ve vacías, no están rotas** — es el mismo
> bloqueante de adopción que ya está documentado.

---

## 2026-07-27 · Filtro por rango de fechas en vacaciones y ausencias · commits `<pendiente>` ×2

**Qué cambió:** los dos módulos de uso diario pasaron a poder acotarse por período, que era la
ausencia más grande del inventario de filtros. Params `fecha_desde` y `fecha_hasta`, end-to-end
repo → service → router → UI, en el listado y en el export. La semántica es **solapamiento**:
una solicitud que empieza antes del rango pero lo cruza entra — la misma regla que ya usaba el
bloqueo por período cerrado, ahora en un helper compartido (`repositories/_rango_fechas.py`).
Antes, `routers/vacaciones.py` se dividió: las lecturas por empleado (saldo e histórico) se
mudaron a `routers/vacaciones_empleado.py`.

**Impacto en infraestructura:** Ninguno.

*(Sin migraciones, sin variables de entorno, sin dependencias, sin buckets, sin cambios en el
modelo de auth ni en los claims del token, sin dependencias de URL. Los filtros son query params
opcionales: un cliente que no los mande recibe exactamente lo de antes.)*

> **Dos notas para quien mire rutas o consultas, no acción:**
> - **No hay endpoints nuevos.** `GET /api/vacaciones/saldo/{id}` y
>   `GET /api/vacaciones/empleado/{id}` siguen en la misma ruta y con el mismo comportamiento:
>   solo se movieron de archivo. Se montan **antes** que el router principal porque `/{id}`
>   matchearía primero — si alguna vez se reordenan los `include_router` de `main.py`, esas dos
>   rutas dejan de resolver.
> - **El filtro es server-side y se traduce a dos comparaciones de fecha indexables**
>   (`fecha_hasta >= desde`, `fecha_desde <= hasta`) sobre `solicitudes_vacaciones` y
>   `solicitudes_ausencia`. Hoy esas tablas están vacías en producción, así que no hay nada que
>   medir; **cuando se carguen datos, esas dos columnas son las candidatas a índice** si el
>   listado se pone lento. No hace falta anticiparlo.

---

## 2026-07-27 · B2 — fundación del sistema de filtros · commits `<pendiente>` ×3

**Qué cambió:** la base de las tandas de filtros (B3–B6), sin entregar todavía ningún filtro
nuevo al usuario. (1) Los wrappers de export de capacitaciones e inventario pasaron a un objeto
de filtros compartido con su listado, y ahora los dos construyen los query params con la misma
función: descargar y ver en pantalla no pueden divergir. (2) `FiltersBar` ganó dos controles
—rango de fechas y multi-selección— y el patrón de hook quedó documentado en
`components/features/shared/filtros.ts`. (3) `vacaciones_service.py` bajó de 150 a 109 líneas
extrayendo `create` a `_vacaciones_write.py`, simétrico con `_ausencias_write.py`.

**Impacto en infraestructura:** Ninguno.

*(Sin migraciones, sin variables de entorno, sin dependencias nuevas —los tests de render usan
`react-dom/server`, que ya estaba—, sin buckets, sin endpoints nuevos ni removidos, sin cambios
en el modelo de auth ni en los claims del token, sin dependencias de URL. El contrato HTTP no
se movió: los cambios del frontend son de firma de TypeScript, y el del backend es movimiento
de código dentro de la capa de services.)*

> **Nota para quien revise deploys, no acción:** se sumó `tests/test_paridad_list_export.py`,
> que recorre `app.routes` y compara los query params de cada endpoint de export contra los de
> su listado. Es un test de estructura, corre sin base de datos y sin red. Si alguna vez falla
> en CI tras agregar un módulo, no es un problema de entorno: es un export que quedó
> desalineado con su listado.

---

## 2026-07-27 · Nonce de un solo uso en el callback OAuth · commit `<pendiente>`

**Qué cambió:** el callback de Google ahora valida un **nonce de un solo uso persistido**. Al
generar la URL de consentimiento se emite un valor aleatorio de 256 bits, se guarda su SHA-256
en la tabla nueva `oauth_states` con vencimiento a 10 minutos, y se manda como parámetro
`state`. Cuando el proveedor redirige el navegador de vuelta, el callback busca esa fila, la
borra y toma de ahí el usuario al que corresponde el flujo. **La identidad sale siempre de la
fila persistida.** Piezas nuevas: `services/_oauth_state.py` (provider-agnóstico),
`repositories/oauth_state_repo.py` y la migración 080.

**Impacto en infraestructura:**
- 🔴 **Migración nueva: `080_create_oauth_states.sql`. NO destructiva** — solo `CREATE TABLE` +
  PK + UNIQUE + FK a `users` (ON DELETE CASCADE) + un índice. No toca ninguna tabla existente,
  no borra ni transforma datos.
- 🔴 **ORDEN DE DEPLOY: la migración va ANTES que el código.** Si el código sale primero, la
  tabla no existe y **el flujo de conexión con Google no funciona** hasta que se corra la
  migración — ni la generación de la URL ni el callback. El resto de la aplicación no se ve
  afectada: es un flujo aislado que hoy usa el equipo de RRHH para conectar su cuenta de Gmail.
  Nada más depende de esta tabla.
- **`backend/db/schema.sql` actualizado** con la tabla, sus constraints y su índice. Sigue
  siendo la fuente de verdad de reconstrucción; pasa de 51 a 52 tablas.
- **La tabla se autolimpia: no necesita cron ni job periódico.** Cada vez que se emite un
  nonce, el mismo request borra los vencidos (`DELETE ... WHERE expires_at < now()`). La
  limpieza corre en el camino que crea las filas, así que se autobalancea. Vercel no tiene
  cron y esto no lo necesita. En AWS tampoco hay que programar nada.
- **Volumen despreciable**: una fila por cada vez que alguien aprieta "Conectar Google", con
  vida máxima de 10 minutos. La tabla se mantiene prácticamente vacía en régimen.
- **`/api/integraciones/google/callback` sigue siendo pública** (`PUBLIC_ROUTES`), y tiene que
  seguir siéndolo: a esa ruta el proveedor redirige el **navegador** del usuario, y ese salto
  no lleva el JWT. Lo que autentica ese request es el nonce. Mantiene el límite de 10/minuto.
- Sin variables de entorno nuevas, sin dependencias nuevas, sin buckets, sin endpoints nuevos
  ni removidos, sin cambios en el modelo de auth de la aplicación ni en los claims del token.

---

## 2026-07-27 · Dividir integracion_service.py · commit `<pendiente>`

**Qué cambió:** refactor puro. `integracion_service.py` estaba en 201 líneas contra un límite de
150 — el peor over-limit del backend. El flujo OAuth de Google se movió **verbatim** a
`services/_google_oauth.py` como dos funciones libres que reciben los colaboradores
(`construir_url_autorizacion` y `procesar_callback(repo, ...)`), y el service las delega en una
línea cada una. Quedan 110 y 123 líneas. Cero cambios de comportamiento, cero cambios de firma
pública: la suite pasó de 608 a 608 sin tocar un solo test.

**Impacto en infraestructura:** Ninguno.

*(Movimiento de código dentro de la capa de services. Sin migraciones, sin variables de entorno,
sin dependencias, sin buckets, sin endpoints nuevos ni removidos, sin cambios en el modelo de
auth ni en los claims del token, sin dependencias de URL nuevas. `routers/integraciones.py` no
se tocó y el callback OAuth sigue en la misma ruta pública, con el mismo comportamiento.)*

---

## 2026-07-27 · Validación de X-Empresa-Id + rol real en costos · commits `<pendiente>` ×2

**Qué cambió:** el middleware validaba solo el **formato** del header `X-Empresa-Id`, así que
un UUID bien formado de una empresa inexistente entraba y viajaba aguas abajo. Ahora se verifica
que la empresa exista, contra un **caché por proceso** (`utils/empresas_cache.py`) y no contra la
base en cada request. Un id inexistente se descarta en silencio y queda `None` (vista
consolidada), igual que un header ausente. Aparte, `costo_service` pasaba `rol=None` hardcodeado
al check de período: ahora pasa el rol real del usuario.

**Impacto en infraestructura:**
- 🔴 **El backend pasa a depender de que la tabla `empresas` sea legible — pero PEREZOSAMENTE,
  no al arranque.** El proceso levanta sin tocar la base; la primera lectura ocurre en el primer
  request que traiga un `X-Empresa-Id` con UUID. **Importa si armás un healthcheck o un readiness
  probe que corra antes de que la DB esté disponible:** `GET /health` **no** consulta `empresas`
  ni ninguna otra tabla, así que sigue respondiendo 200 con la base caída. Eso es deliberado — no
  lo cambies para "que valide la DB" sin decidir antes qué querés que haga el balanceador.
- 🟡 **Fail-open declarado.** Si la consulta a `empresas` falla, el header **se acepta sin
  validar** y se loguea a **ERROR** (`"No se pudo cargar el caché de empresas"`). Es intencional y
  contraintuitivo: descartar el header **ensancha** la vista (`None` = todas las empresas), así
  que ante un blip de base aceptar es la opción conservadora. **Ese ERROR es una alerta que vale
  la pena cablear**: significa que el backend está sirviendo con la validación desactivada.
- 🟡 **Carga sobre la base: despreciable, pero no cero.** En régimen, 1 query cada 300s por
  proceso (`SELECT id FROM empresas`, sin joins ni orden). Un miss puede disparar un refresco
  extra, acotado a 1 cada 10s por proceso — o sea que ni un atacante martillando UUIDs falsos
  puede convertir esto en carga. Con N instancias serverless, multiplicá por N: sigue siendo
  ruido. **Ojo con el escalado**: el caché es por proceso, así que una empresa nueva puede tardar
  hasta 300s en ser visible en las instancias que no la vieron (el refresco-en-miss cubre el caso
  normal). Aceptable dado que hoy hay **1 empresa en producción, creada el 14/7 y nunca
  modificada**.
- 🟡 **Nuevo WARNING que sirve como señal de seguridad**: `"X-Empresa-Id descartado: la empresa no
  existe"`, con el path y el UUID. Un UUID sintácticamente válido que no existe **no sale del uso
  normal del producto** — vale como indicador de manipulación. No se devuelve ningún status nuevo
  a propósito: un 400 sería un oráculo de enumeración de empresas, justo lo que cerró la Fase 2.
- **Se corrige una pérdida silenciosa de auditoría.** `auditoria.empresa_id` tiene FK a `empresas`
  (verificado en el schema vivo). Tres paths escribían ahí el empresa del header sin validar
  (`costo_service`, `candidato_service`, `offboarding_service`): con un id falso el INSERT violaba
  la FK, `AuditService` se tragaba la excepción por diseño, y **la operación de negocio se
  completaba perdiendo el registro de auditoría**. Verificado además que `auditoria.empresa_id` es
  **NULLABLE**, así que el modo consolidado (`None`) nunca estuvo afectado — 133 eventos en
  producción, 9 con `empresa_id` NULL, todos guardados bien.
- Sin migraciones, sin variables de entorno nuevas, sin dependencias, sin buckets, sin endpoints
  nuevos, sin cambios en el modelo de auth ni en los claims del token.

---

## 2026-07-27 · Rate limiting por franjas · commit `<pendiente>`

**Qué cambió:** el rate limiting pasó de cubrir un solo endpoint (`/api/auth/login`) a cubrir
toda la API. Se agregó `backend/utils/rate_limit.py` con el limiter único, un `key_func`
propio y el handler del 429; el baseline global lo aplica `SlowAPIMiddleware` y las franjas
sensibles llevan decorador por endpoint. El 429 ahora sale con el formato de error del repo
(`{error, message, code}` + `Retry-After`), no con el de slowapi.

**Impacto en infraestructura:**
- 🔴 **Variable de entorno nueva: `TRUSTED_PROXY_HOPS`** (int, default `1`). Cuántas capas de
  proxy confiables hay delante del app. Define de qué entrada de `X-Forwarded-For` se saca la
  IP del cliente, que es la **clave del contador**. `1` = Vercel (su edge agrega la IP real).
  En AWS: **`1` con ALB solo, `2` si además hay CloudFront adelante**. `0` desactiva la lectura
  del header y usa la IP de la conexión (local, sin proxy).
  ⚠️ **Un valor de más no "afloja" el límite: colapsa todo el tráfico en un único contador y
  deja al equipo entero afuera.** Es la variable a revisar primero si aparecen 429 masivos.
- 🔴 **Variable de entorno nueva: `RATE_LIMIT_STORAGE_URI`** (default `memory://`).
- 🔴 **Dependencia de infraestructura PENDIENTE — sin esto los límites son parciales.** Con
  `memory://` los contadores viven en la memoria del proceso: en serverless cada cold start
  arranca en cero, y con N instancias vivas el límite efectivo es **N×** el configurado. Para
  que sean un control real hace falta un **store compartido (Redis / ElastiCache)** y apuntar
  ahí `RATE_LIMIT_STORAGE_URI`. El enchufe está puesto y probado; **falta la instancia**.
- 🟡 **Afecta cualquier regla de WAF, ALB o CDN que se escriba.** El app ya devuelve 429 por su
  cuenta en las franjas de abajo. Si además se pone throttling en el borde, los dos se suman y
  el efectivo es el más restrictivo — conviene que el borde sea más laxo que estos números:

  | Franja | Endpoints | Límite |
  |---|---|---|
  | público sin auth | assessment `evaluacion` GET · `/submit` POST · `integraciones/google/callback` | 10/min · 5/min · 10/min |
  | credenciales | `auth/login` · `auth/refresh` · `usuarios/cambiar-password` | 5/min · 20/min · 10/hora |
  | import | los 5 endpoints de import | 10/hora **compartido entre los 5** |
  | export | 7 endpoints de export | 30/hora **compartido entre los 7** |
  | costo externo | `reportes/generar` (con `tipo=adhoc` llama a Claude) | 20/hora |
  | todo lo demás | ~170 endpoints | 300/min |

- 🟡 **`GET /health` quedó EXENTO a propósito.** No lo limites en el borde tampoco: lo consultan
  los health checks de la plataforma, desde una sola IP y con alta frecuencia. Limitarlo hace
  que el balanceador marque la instancia como caída y la saque de rotación.
- **El 429 depende de CORS.** El middleware de rate limiting se montó **dentro** de CORS para
  que la respuesta salga con headers CORS; si no, el front la ve como error de red y no puede
  leer el código. Si se mueve el orden de middlewares, se rompe esto.
- Sin migraciones, sin dependencias nuevas (`slowapi==0.1.9` ya estaba), sin buckets, sin
  endpoints nuevos.
- **Nota para quien sume endpoints:** tres exports (`objetivos`, `inventario_items`,
  `evaluaciones_resultados`) quedaron bajo el baseline en vez de la franja de export, porque el
  decorador los pasaba del límite de 80 líneas del router. **Se les agrega cuando esos routers
  se dividan** — hay un test que falla y lo recuerda.

---

## 2026-07-27 · Cerrar la exposición pública de assessment · commit `<pendiente>`

**Qué cambió:** el módulo de assessment quedó apagado en el backend detrás de un flag. Estaba
oculto en el front pero el backend seguía entero y expuesto, con **2 rutas públicas sin auth**.
Con el flag apagado el router no se monta y esas rutas dejan de ser públicas, así que responden
igual que cualquier path inexistente. **No se borró código**: services, repos, schemas,
migraciones y tests quedan intactos. Se eliminó además un regex del middleware de auth
(`^/assessment/[^/]+$`) que salteaba la autenticación y no matcheaba ninguna ruta real.

**Impacto en infraestructura:**
- 🔴 **Variable de entorno nueva: `ASSESSMENT_ENABLED`** (bool, default `false`). Es la única
  palanca: prenderla y redeployar reactiva el módulo entero, sin tocar código. **Hoy no hay que
  cargarla en ningún entorno** — el default apagado es el estado deseado.
- 🔴 **Cambió la superficie PÚBLICA de la API, y eso afecta las reglas de WAF/ALB.** Estas dos
  rutas dejaron de ser alcanzables sin token:
  - `GET  /api/assessment/evaluacion/{token}`
  - `POST /api/assessment/evaluacion/{token}/submit`

  **La lista completa de rutas públicas (sin auth) es ahora exactamente:** `/health`,
  `/api/auth/login`, `/api/auth/refresh` y `/api/integraciones/google/callback`. Cualquier regla
  que asuma que `/api/assessment/*` puede llegar sin `Authorization` ya no aplica. Si en algún
  momento se pone `ASSESSMENT_ENABLED=true`, las dos rutas de arriba vuelven a la lista.
- **Con el módulo apagado la respuesta es deliberadamente indistinguible** de una ruta que nunca
  existió: mismo status y mismo body, nunca un 403 ni un mensaje que confirme que el módulo está
  ahí. No sirve como señal de detección: un scanner apuntando a `/api/assessment/*` produce
  exactamente el mismo tráfico de error que uno apuntando a cualquier path inventado.
- Sin migraciones, sin dependencias, sin buckets, sin cambios en el modelo de auth ni en los
  claims del token (cambió **qué rutas** saltean el middleware, no **cómo** se valida el token).

---

## 2026-07-27 · Ocultar el módulo de sucesión · commit `e00edcf`

**Qué cambió:** se apagó el módulo de Sucesión en el frontend por decisión de producto, sin
borrar nada. Dos flags, uno por archivo: `SUCESION_ACTIVA: boolean = false` en
`nav-config.ts` (saca el ítem del sidebar) y `useState(false)` en `sucesion/page.tsx` (la
página redirige a `/dashboard`). El backend queda **entero y expuesto**: endpoints,
permisos y tests intactos. La ruta `/sucesion` sigue existiendo y sigue gateada por
`AuthGuard`. Se revierte con dos líneas.

**Impacto en infraestructura:** Ninguno.

---

## 2026-07-27 · Renombrar las referencias de Sofia a RRHH · commit `e9df215`

**Qué cambió:** rename de nomenclatura interna, de "Sofia" a "RRHH", en 25 archivos: docs,
comentarios y docstrings (`backend/main.py`, `backend/integrations/supabase_client.py`,
`backend/db/schema.sql` y varios `*_NEW.py` de `migracionAWS/`). **Solo texto** — cero
cambios de comportamiento, de firmas o de configuración. En paralelo, **el repositorio de
GitHub pasó a llamarse `RRHH`**.

**Impacto en infraestructura:**
- **Dependencia de URL — el remote de git cambió.** `origin` es ahora
  `https://github.com/Franco-Bincovich/RRHH.git`. Cualquier clon viejo, script de CI,
  webhook o deploy key que apunte al nombre anterior tiene que actualizarse. GitHub redirige
  el nombre viejo, pero es una red de seguridad temporal — no dependas de ella.
- 🔴 **Los proyectos de Vercel NO se renombraron.** Siguen llamándose **`sofia-front`** y
  **`sofia-backend`**, y el dominio del backend sigue siendo
  `sofia-backend-pi.vercel.app`. El nombre del repo y el de los proyectos de deploy ahora
  **divergen a propósito**: renombrarlos cambiaría las URLs `*.vercel.app` y rompería
  `NEXT_PUBLIC_API_URL`. Al buscar el proyecto en el dashboard, buscá "sofia", no "RRHH".
- Sin migraciones, sin env vars, sin dependencias, sin buckets, sin endpoints nuevos.

---

## 2026-07-27 · Fase 3 — deuda estructural · commits `51832e2` + `a6acaed`

**Qué cambió:** tres refactors sin cambio funcional. (1) Se resolvió un **N+1** en el
análisis por área de sucesión: `sucesion_repo` hacía una query de `assessment_resultados`
por empleado y ahora trae todo en una sola con `.in_()` — con 200 empleados, de 201
requests a 2. (2) `sucesion/page.tsx` pasó de 855 a 85 líneas, repartido en 8 componentes y
2 hooks. (3) `fetchEmpleados`/`exportarEmpleados` pasaron de parámetros posicionales a un
objeto de opciones, con 10 call sites migrados.

**Impacto en infraestructura:**
- **Ninguno en configuración.** Sin migraciones, sin env vars, sin dependencias nuevas, sin
  buckets, sin endpoints nuevos ni removidos. El contrato HTTP quedó intacto: el cambio de
  `fetchEmpleados` es de firma de TypeScript, no de query params.
- **Nota de capacidad, no de acción:** el fix del N+1 baja de forma marcada la cantidad de
  conexiones concurrentes a la base en el endpoint de análisis por área. Si vas a dimensionar
  el pool de RDS a partir de mediciones, tomalas después de este commit — las anteriores
  sobreestiman.

---

## 2026-07-26 / 27 · Fase 2 — barrera de empresa en todo el backend · commits `bd95e98` + `9d7baa7`

**Qué cambió:** todo endpoint que recibe un id de recurso de afuera ahora valida que ese
recurso pertenezca a la empresa del request. Quedaron **92/92 endpoints aplicables** con la
barrera y **13/13 superficies de Vacaciones y Ausencias** componiendo además el eje de
ownership; 8 endpoints están marcados NO APLICA con su razón. El filtro va preferentemente en
el `WHERE` de la query, no en un chequeo posterior en el service.

**Impacto en infraestructura:**
- **Sin migraciones, sin env vars, sin dependencias, sin buckets.**
- **Sin endpoints nuevos ni removidos** — verificado: cero líneas `@router.*` agregadas o
  borradas en los dos commits.
- 🔴 **Cambió el comportamiento de ~92 endpoints ante un id de otra empresa, y eso afecta
  los tests de humo post-deploy.** Antes, pasar el UUID de un recurso ajeno devolvía **200 con
  el recurso** (la fuga que se cerró). Ahora devuelve **404**. Si armás smoke tests o pruebas
  de carga que reutilizan UUIDs fijos entre entornos o entre empresas, van a fallar con 404 —
  **eso es la barrera funcionando, no una regresión.** Los datos de prueba tienen que ser
  coherentes con la empresa del header `X-Empresa-Id`.
- **El 404 es deliberadamente indistinguible.** "No existe" y "es de otra empresa" devuelven el
  mismo status, el mismo `code` y el mismo mensaje. Nunca un 403. Si escribís una regla de WAF
  o una alerta que trate el 403 como señal de intento de acceso indebido, acá no va a haber
  403 que capturar — el evento a monitorear es el 404, que también aparece en tráfico legítimo.
- **`X-Empresa-Id` ausente o con valor `todas` significa "vista consolidada", no "sin
  permiso".** En ese modo la barrera no restringe. Cualquier proxy, CDN o capa de caché que
  toque este tráfico **tiene que incluir `X-Empresa-Id` en la clave de caché**: si no, una
  respuesta consolidada puede servirse a un request scopeado a una empresa, y viceversa.

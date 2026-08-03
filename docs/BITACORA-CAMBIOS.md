# Bitácora de cambios — impacto en infraestructura

**Qué es:** un log corrido de cada sesión de trabajo, ordenado de más reciente a más antiguo,
que declara **qué cambió y qué tiene que hacer infraestructura al respecto**. No es un
historial de features ni un resumen de commits: es la lista de cosas que rompen, condicionan
o requieren acción del lado del deploy.

**Para quién:** el dev que está montando la infraestructura en AWS en paralelo. La idea es
que se entere de todo lo que le afecta **sin tener que leer los commits ni el código**.

**Es el único historial de cambios del repo.** (`CHANGELOG.md` se borró el 2/8/2026: estaba
congelado en 14 líneas mientras esto tenía 1700, así que no cumplía ninguna función.)

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

## 2026-08-03 · Cards del dashboard plegables + contador de alertas · commit pendiente

**Qué cambió:** solo front. Las tres cards del dashboard cuyas listas crecen sin techo
—headcount por área, alertas activas, y cumpleaños/aniversarios— pasaron a ser plegables y
llevan un contador en el encabezado. Con la segunda empresa cargada ya son 12 áreas y 7
alertas; con 500 empleados serían decenas, y hoy empujaban todo lo demás fuera de la pantalla.
Se reusó `ConfigSection.tsx` (el acordeón de /configuracion) en vez de construir un segundo
desplegable: se le agregaron tres props opcionales —`icon` pasó a opcional, más `preview` y
`disabled`— y /configuracion lo sigue usando exactamente igual. `HeadcountBar` salió de
`DashboardAdmin.tsx` a un `HeadcountPanel.tsx` propio (109 → 80 líneas). El estado
abierto/cerrado **no se persiste** y los contadores salen de los datos que ya llegaban.

**Impacto en infraestructura:** **Ninguno.** Sin migraciones, env vars, dependencias, buckets,
endpoints ni cambios de auth. **El backend no se tocó** — cero requests nuevos: el dashboard
pide lo mismo que antes y el corte y los contadores se calculan sobre esa misma respuesta.

## 2026-08-03 · Una baja de usuario ahora saca a la persona del sistema · commits pendientes ×5

**Qué cambió:** hasta hoy, dar de baja a alguien **no lo sacaba**. `users.activo` existía en el
schema y **no lo leía nadie**: el middleware solo miraba el rol, y el JWT no sabe nada de una
baja (la firma y el `exp` siguen siendo válidos). Además el rol se resolvía con **una query por
request**, el front gobernaba con el rol que guardó en el login, y una sesión **no vencía
nunca**. Cinco commits: dos cortes de archivo, el caché, el corte por `activo` + la baja blanda,
el rol vigente en el front, y la inactividad.

**Impacto en infraestructura:** **Ninguna migración, env var, dependencia, bucket ni tabla
nueva.** **La 089 sigue siendo la única migración pendiente de correr.** Un endpoint nuevo,
`GET /api/auth/me`, **autenticado** (no público). Las columnas `users.activo` y
`users.ultimo_acceso` ya existían: esta tanda las pone a trabajar, no las crea.

> 🔑 **Permiso del ban — verificado, no hay nada que habilitar.** El ban usa
> `update_user_by_id`, la MISMA llamada de la Admin API que el cambio de contraseña ya hacía
> con la `SUPABASE_SERVICE_KEY`. Escrito en `docs/DEPLOY.md` junto con el procedimiento de
> reversión y con lo que hay que rehacer el día del cutover a AWS (allá `ban_duration` no
> existe; el equivalente es revocar `refresh_tokens`, mig 076).

### 🔴 Lo que va a notar un usuario logueado cuando esto salga

1. **Si está activo y usando la app, nada.**
2. **Un cambio de rol o una baja tardan hasta 60 s en regir** (TTL del caché). La baja hecha
   desde la app rige en el acto en el proceso que la ejecutó (se invalida la entrada), pero en
   serverless hay N procesos: **el techo real es el TTL**.
3. **A quien le cambien el rol con la sesión abierta, se le recarga la pestaña una vez.** Es el
   precio de que el sidebar, el menú y los botones de escritura lean el rol al montar. Después
   de esa recarga no vuelve a pasar.
4. **A quien den de baja cae en `/login`** con la sesión limpiada, en la primera navegación.
5. 🔴 **A las 8 h sin usar la app hay que volver a loguearse.** Hoy la sesión no vencía nunca:
   **es el cambio que más se va a notar.** A las 7 h 45 min aparece un banner con "Seguir
   conectado". La primera vez, el front hace un intento de refresh inútil antes de mandar al
   login — un parpadeo, no un error.
6. **El primer request de cada usuario escribe `ultimo_acceso`** (hoy está NULL en las 3 filas).

### Commits 1 y 2 — dos cortes de archivo, refactor puro

`utils/_sesion_inactividad.py` (la política: 8 h, 5 min) sale de `utils/usuario_estado.py`
(212 → 174); `middleware/_empresa_header.py` (`resolver_empresa_id`) sale de `middleware/auth.py`
(209 → 167). **Suite idéntica y sin tests nuevos**; lo único que cambió en tests es **una línea
de import**. El corte de la política no es por tamaño: el caché es infraestructura y las 8 h son
una decisión de producto que se va a discutir con RRHH.

### Commit 3 — el caché de estado de usuario

`utils/usuario_estado.py`, molde de `utils/empresas_cache.py`, TTL 60 s. 🔴 **Acá es
fail-CLOSED, al revés que aquel**: allá descartar el header **ensancha** (`None` = consolidado),
acá el rol **es** la autorización. **Y es la política que ya regía** —el `try/except` del
middleware dejaba `rol=None` → 403—, así que se conserva, no se cambia. Ni el fallo se cachea
(un blip de 1 s se volvería 60 s de gente afuera) ni una entrada vencida se sigue sirviendo
(sería fail-open con otro nombre).

### Commit 4 — `activo` rige, y el DELETE pasa a baja blanda

`rol` y `activo` viajan en la **misma fila y la misma query**. `activo=false` → **403
`USUARIO_INACTIVO`** desde el middleware, antes de cualquier handler. La otra mitad es el **ban
en Supabase Auth**: `/api/auth/refresh` es **pública** y no pasa por el middleware, así que sin
el ban un usuario desactivado renovaría tokens para siempre.

🔴 **El DELETE ya no borra.** Antes borraba `auth.users` y el CASCADE se llevaba `public.users`,
con dos costos: el `ON DELETE SET NULL` de `empleados.user_id` **desvinculaba al empleado**, y la
auditoría vieja quedaba apuntando a un id que no resolvía a ningún nombre. Ahora es
`activo=false` + ban, **reversible**. El orden importa y está comentado en el código: primero la
baja en nuestra base (la que corta), después el ban; si el ban falla se avisa con 502 pero **no
se revierte**, porque revertir dejaría al usuario adentro.

### Commit 5 — rol vigente en el front + inactividad de 8 h

`GET /api/auth/me` no toca la base: responde con lo que el middleware ya resolvió. El `AuthGuard`
lo consulta en cada navegación. La inactividad se mide con `ultimo_acceso`, que se escribe
**throttleado a 5 min y mirando el VALOR, no un marcador local** — así N procesos no escriben N
series. 🔴 **El chequeo va antes del sellado**: al revés, el propio request renovaría el reloj y
la sesión no vencería jamás. Y **el login sella `ultimo_acceso`**: sin eso, alguien que estuvo
9 h afuera se logueaba bien y su primer request moría con `SESION_EXPIRADA`, en loop.

**Tests: backend 1551 → 1599 · front 285 → 298.** Mutation checks corridos en los cinco puntos
que sostienen esto (middleware ignorando `activo`, `select` sin `activo`, baja dura restaurada,
sellado antes del chequeo, throttle borrado): **los cinco rojean**.

---

## 2026-08-02 · La pantalla de Proyectos no terminaba de cargar nunca · commit pendiente

**Qué cambió:** el listado `/proyectos` quedaba en skeleton para siempre, con el endpoint
respondiendo **200**. La causa es de front y de una sola línea: `load()` en
`app/(dashboard)/proyectos/page.tsx` prendía el loading y **no lo apagaba** — el
`finally { setLoading(false) }` se perdió en el commit **`e3df1f9`** (27/7, "dividir
proyectos_repo, proyectos/page.tsx y AsignacionesTab"), donde era la línea contigua al array de
dependencias del `useCallback` y el hunk se llevó las dos. No fue la sesión de asignación por
área (`5e1e464` no tocó ese archivo). Afectaba **los tres caminos** —éxito, error y lista
vacía—, no solo el error: los datos llegaban y se guardaban, pero la grilla corta en el
`if (loading)` antes de mirarlos. Solo el **listado**; el detalle y las tabs de equipo y horas
siempre tuvieron su `finally`.

La carga se movió a `components/features/proyectos/cargarProyectos.ts` (41 líneas), que apaga el
loading en un `finally` y **se puede testear sin renderizar** — vitest corre sin jsdom, así que
dentro del componente esto no se podía verificar de ninguna forma. La página quedó en 69/150.

**Impacto en infraestructura:** **Ninguno.** Sin migraciones, env vars, dependencias, buckets ni
endpoints nuevos. Cero cambios de backend: ninguna ruta cambió de path, método ni contrato. **La
089 sigue siendo la única migración pendiente de correr.** Es un fix de front puro — alcanza con
que salga el deploy de `sofia-front`; el backend no necesita salir primero.

### El barrido estructural nuevo (lo que importa más que el fix)

Esto pasó una división de componentes y 214 tests sin que nadie lo notara, y era una pantalla
completa caída en producción. Ningún test del front podía verlo: sin jsdom los efectos no
corren, y un render a string muestra el skeleton inicial igual con el bug que sin él.

Se agregó **`components/features/shared/loadingSeApaga.test.ts`**, sexto barrido estructural del
repo y primero del front que cubre una clase de falla de runtime: descubre por filesystem todo
`set*Loading(true)` / `set*Cargando(true)` de `app/`, `components/` y `hooks/` y exige que un
`finally` lo apague, aceptando los dos idiomas que el repo usa (`try/finally` y
`.finally(() => …)`). **61 pares hoy, guarda de mínimo en 55.** Corrido contra el código roto
señalaba `proyectos/page.tsx` y **nada más** — el resto del front ya estaba sano.

⚠️ Verifica la **forma**, no el comportamiento: un `finally` que apague el loading equivocado
pasa igual. Cubre "alguien borró el apagado", que es lo que se llevó puesta la pantalla. El
comportamiento de la carga concreta lo prueban los 8 tests de `cargarProyectos.test.ts` (éxito,
error de red, lista vacía, 200 sin `items`, orden de las llamadas). **Front: 214 → 285 tests.**

---

## 2026-08-02 · Limpieza de código: oráculo cerrado, dead code borrado, cero over-limit · commits pendientes ×5

**Qué cambió:** cinco commits de limpieza sobre `docs/DEUDA-TECNICA.md`. Uno solo cambia
comportamiento observable (el 404 de dos altas); el resto son borrados, cortes de archivo,
documentación y un test nuevo.

**Impacto en infraestructura:** **Ninguna migración, env var, dependencia, bucket ni endpoint
nuevo.** Ninguna ruta cambió de path ni de método. **La 089 sigue siendo la única migración
pendiente de correr** y esta sesión no la tocó.

### 🔴 Lo único que cambia el CONTRATO de la API (commit 1)

Dos altas devolvían **422 `EMPRESA_MISMATCH`** cuando el recurso existía en OTRA empresa, y 404
cuando no existía. Esa diferencia de status **confirma que el recurso ajeno existe** — el oráculo
de enumeración que la Fase 2 cerró en 92 endpoints y que acá quedó suelto porque estos dos no
responden a un id del path sino al cruce de DOS entidades.

- `POST /api/capacitaciones/asignaciones` — la capacitación ahora se busca **acotada a la empresa
  del empleado**; si no aparece, **404 `CAPACITACION_NOT_FOUND`**, idéntico a "no existe".
- `POST /api/evaluaciones/instancias` — el empleado se busca **acotado a la empresa del ciclo**;
  si no aparece, **404 `EMPLEADO_NOT_FOUND`**.

El filtro va **en el WHERE** (Forma A), no comparando después de traer la fila: el caller ya no
puede distinguir los dos casos aunque quiera. **`EMPRESA_MISMATCH` ya no existe en el código.**
Verificado antes de tocar nada: ningún test y ninguna línea del front esperaban ese 422.

> ⚠️ **Para quien monitoree la API:** un cliente que hoy trate el 422 de estos dos endpoints como
> caso especial va a ver un 404. No hay ninguno — se buscó.

### Lo que se borró (commit 2), y cómo se verificó

`repositories/costo_repo.py` (135) · `repositories/assessment_repo.py` (131) ·
`components/features/evaluaciones/EliminarLoteButton.tsx` (74). **Cero callers los tres**,
reverificados uno por uno con grep sobre `services/`, `routers/`, `repositories/`, `tests/` y
`main.py` antes de borrar cada archivo.

🔴 **`ev_*` y assessment NO se tocaron, y no son lo mismo:** sus routers **están montados y
responden**. "Apagado por flag" u "oculto en la UI" **no es** "muerto" — de los 5 sospechosos del
relevamiento, 3 estaban vivos. Las 6 tablas huérfanas siguen en pie: se limpian en el cutover.

> Para el porteo a AWS: **`costo_repo` y `assessment_repo` eran 2 de los 5 "casos pesados"**
> (embeds anidados de 2 niveles) que `migracionAWS/MIGRACION_A_RDS.md` listaba. **No hay que
> portarlos.** Ya está anotado en ese documento.

### Cortes de archivo (commit 4) — el backend quedó en CERO over-limit

Primera vez que pasa. Ocho archivos: `_onboarding_templates_row` 159→87 (partido en tres) ·
`_audit_payloads` 167→119 · `ev_instancias_repo` 146→98 · `ev_plantillas_repo` 129→93 ·
`reporte_anual` 154→112 · `usuario_service` 149→77 · `ev_instancias_service` 149→113.
**Refactor puro: ninguna aserción de test cambió** (una sola línea de `import` se reapuntó, en
`test_onboarding_template_visibilidad.py`, porque el símbolo cambió de módulo).

🔴 **El aprendizaje que importa más que los cortes:** dos satélites tenían escrito *"acá el límite
es 200"* en su docstring, y por eso uno llegó a **159 sin que nadie lo notara**. Un `_*.py` dentro
de `repositories/` **es un repositorio y su límite es 100**. Partir un archivo para respetar un
límite es correcto; redefinir el límite del archivo nuevo, no.

### Tests nuevos (commits 1 y 5)

- **`tests/test_empresa_mismatch_cerrado.py`** (10) — fija que los dos 404 sean indistinguibles
  (status, code y mensaje) **y** que la empresa viaje en la query, con un espía del cliente de
  Supabase. Mutation check: con el bug reinstalado caen 6 de 10.
- **`tests/test_espejo_permisos.py`** (10) — 🔴 **cierra el último espejo manual sin red**:
  `frontend/services/permisos.ts` contra `backend/utils/permisos.py` (secciones, acciones, roles,
  `MANDOS_MEDIOS_SECCIONES`, fail-closed). Hoy coinciden, así que **nació en verde**: era el
  momento más barato. Con guarda de mínimo por extracción — si el regex deja de matchear, falla en
  vez de comparar conjuntos vacíos. Mutation check: las tres mutaciones probadas lo hacen fallar.

Con estos, **el repo tiene cinco barridos estructurales**, todos con guarda de mínimo.

### Documentación (commit 3)

`CLAUDE.md` tenía **10 números falsos** (975 tests → 1551 · 61 archivos de test → 89 · migración
081 → 089 · 54 repos → 69 · 52 tablas → 58 · 113 services → 129 · 180 gates → 190 …) y la sección
de líneas entera obsoleta. Se sumó además **todo lo de las últimas ~15 sesiones que no estaba
escrito**: el mailer y las plantillas, los subtipos de ausencia, el ownership cruzado
(`_alcance_mandos.py`), el lector de CSV unificado, los superiores del import y las vacaciones
pendientes.

🔴 **Y se reescribió la lista de "código muerto candidato a borrar", que fue lo que indujo el
error del propio relevamiento.** El criterio ahora está escrito: **callers reales, no visibilidad
en la UI**, con una tabla explícita de qué NO está muerto (`ev_*`, assessment, sucesión) y por qué.

**Suite: 1551 verdes · `tsc` 0 · `next build` OK · `npm test` 214 verdes.**

---

## 2026-08-02 · Limpieza de `docs/`: 28 → 17 archivos · commits pendientes ×5

**Qué cambió:** solo documentación — **cero líneas de código de producción**, salvo un comentario
en `repositories/_empleado_write_repo.py:80` que citaba un documento borrado. Se agregaron dos
documentos que no existían (`DEPLOY.md` y `DECISIONES.md`), se corrigieron seis que mentían, y se
borraron catorce que ya no describían nada real.

**Impacto en infraestructura:** 🟢 **positivo y directo — `docs/DEPLOY.md` es para el dev de AWS.**
Es el hueco que faltaba: hasta hoy **no había ningún documento que dijera cómo levantar el sistema
de cero**. Trae las 5 env vars obligatorias (verificadas contra `config/settings.py`, no contra la
doc), todas las opcionales con su default, el orden de deploy de los dos proyectos de Vercel, los
techos de plataforma que no se pueden subir por configuración (300 s `maxDuration`, 4,5 MB de
payload rechazados **antes** de que el código los vea, 30 s de timeout httpx, ~8 s de
`statement_timeout`) y qué cambia en AWS. **Ninguna migración, env var, dependencia, bucket ni
endpoint nuevo:** esta sesión no tocó nada de eso.

### 🔴 `MODELO_DATOS.md` — por qué se borró, y no es lo mismo que los otros trece

**Se declaraba "la fuente de verdad única del modelo de datos" y describía un schema que no
existe.** No estaba desactualizado en los bordes: describía **13 tablas que nunca se crearon con
esa forma** — los catálogos `seniorities`, `roles`, `equipos`, `tipos_licencia`, `motivos_baja`, y
`horas_proyecto` con columnas (`costo_hora_snapshot`, `fecha_carga`, `origen`) que la tabla real no
tiene. Un dev que lo tomara literalmente escribiría queries contra tablas inexistentes.

Un documento así **es peor que no tener documentación**: no tener nada obliga a leer el schema;
tener esto invita a no leerlo. Ya estaba marcado como obsoleto en `CLAUDE.md`, y la marca no
alcanzó — seguía en `docs/`, con el título intacto, y su comentario había llegado al código.

**Queda en el historial de git** y hay una lápida en `CLAUDE.md:10` para que nadie lo busque ni lo
recree. **La única fuente de verdad del schema es `backend/db/schema.sql`**, contrastado contra el
catálogo vivo de producción.

### Los otros trece borrados, y el motivo de cada grupo

| Qué | Cuántos | Por qué |
|---|---|---|
| `DIAGNOSTICO-*.md` (5) + `Resultado_import.md` + `Resultado_nomina_batch.md` | 7 | Diagnósticos de sesión, 2.363 líneas describiendo código **ya implementado** — el código lo cuenta mejor y sin poder divergir. **Lo único que no se podía recuperar del código —las opciones descartadas y por qué— se fusionó en `docs/DECISIONES.md`.** El razonamiento completo sigue en git. |
| `AUDITORIA_TECNICA_HRKARSTEC.md` + `AUDITORIA_HR_KARSTEC.md` | 2 | Fotos del 29/5/2026. Sus hallazgos vigentes ya están en `DEUDA-TECNICA.md`, verificados contra el código actual; el resto describía problemas resueltos hace meses. |
| `EXTRACCION_NEXIO_PARA_PORTAR.md` | 1 | Guía de portación de otro proyecto. La portación se hizo. |
| `INVESTIGACION_ROLES.md` | 1 | El modelo de roles quedó cerrado y documentado en `CLAUDE.md` + `utils/permisos.py`. |
| `CHANGELOG.md` | 1 | Congelado en 14 líneas mientras `BITACORA-CAMBIOS.md` tenía 1.700. Dos historiales, uno abandonado. |
| `INVENTARIO-DOCS.md` | 1 | El diagnóstico que ordenó esta limpieza. Se ejecutó entero; conservarlo sería un TODO ya hecho. |

**Verificado con grep, no de memoria:** ningún archivo del repo apunta a un documento borrado. Las
tres menciones que quedan son deliberadas — la lápida de `CLAUDE.md:10`, esta entrada, y
`BASES-DE-DESARROLLO.md`, que nombra "CHANGELOG.md" como norma general de la agencia, no como
archivo de este repo.

### Lo que se corrigió (no se borró)

`docs/README.md` decía que **el backend no arranca sin la API key de Resend** — es falso, tiene
default, y era la clase de error que hace perder una tarde montando un entorno. Además contaba
migraciones hasta la 074 cuando van 89. `ARCHITECTURE.md` decía Next.js 15 (es 16).
`backend/db/README.md` tenía los tres números del schema mal (47/310/220 → 58/364/151).
`ESTADO-VS-COMPROMISO.md` y `MATRIZ-FILTROS.md` no incluían nada de las últimas ~15 sesiones.
`SMOKE-TEST-RESULTADOS.md` conserva la corrida del 30/7 pero ahora avisa que es vieja.

> ⚠️ **`docs/` quedó en 17 archivos, no en 15.** Los dos de diferencia son
> `PLAN_DESARROLLO_AHORA.md` y `PLAN_DESARROLLO_DESPUES.md`, que **se conservan a propósito** como
> registro de la intención original de producto (así estaba previsto en el inventario). Son los
> únicos dos documentos del repo que se leen como historia y nunca como instrucción.

---

## 2026-08-02 · Lector de CSV unificado y unicidad de ausencias · commits pendientes ×2

**Qué cambió:** los tres imports (nómina de empleados, nómina de costos, evaluaciones) pasan a
leer el CSV por un único lector, y `solicitudes_ausencia` gana la clave de identidad que va a
sostener la idempotencia del import mensual de novedades. Dos commits: (1) el lector, (2) la
migración 089.

**Lo que NO se hizo, y es deliberado:** no se escribió el vocabulario de columnas del archivo de
novedades. RRHH todavía no mandó la estructura definitiva, y un mapeo con nombres provisorios es
documentación disfrazada de código. Queda una nota en `services/_import_csv.py` que dice dónde va
a vivir cuando llegue y qué archivos históricos se vieron.

### 🔴 ORDEN DE DEPLOY

1. **Correr `backend/migrations/089_ausencias_unicidad.sql`.**
2. `sofia-backend` deploya y da 200 en `/health`.
3. El front no cambia en esta sesión.

✅ **086, 087 y 088 están las tres corridas** (verificado contra el catálogo vivo). La 089 es la
única pendiente.

### Migración

- **089 `ausencias_unicidad`** — **NO destructiva**: crea un índice único sobre
  `solicitudes_ausencia (empleado_id, fecha_desde, fecha_hasta, tipo_id)`. Reflejada en
  `db/schema.sql`.
- 🔴 **Correrla ANTES de que se cargue el histórico de ausencias, y esta vez es literal.** Hoy la
  tabla tiene **0 filas** y **0 duplicados** por esa clave (verificado con un
  `GROUP BY … HAVING count(*) > 1` contra producción), así que no puede fallar. Con el histórico
  cargado, si viniera la misma ausencia dos veces —justo lo que este índice existe para impedir—
  **`CREATE UNIQUE INDEX` FALLA** y hay que deduplicar a mano decidiendo qué fila sobrevive.
- ⚠️ **Qué prohíbe, dicho explícito:** dos filas con el mismo empleado, mismo tipo y exactamente
  las mismas dos fechas, que difieran solo en `motivo` o `justificada`. Se evaluó y se aceptó: eso
  no son dos ausencias, es la misma cargada dos veces. **NO prohíbe solapamientos parciales** —
  `ausencias_service` documenta que no se validan, y sigue siendo así: el índice es un
  subconjunto estricto.
- `vacaciones_pendientes` **ya tenía** su `UNIQUE (empleado_id, periodo)` desde la 083: ese import
  se apoya en ella sin trabajo nuevo.

### 🔴 UN BUG REAL ARREGLADO: UTF-16 entraba como basura y el import lo cargaba

Los dos routers de nómina hacían `try utf-8-sig / except → latin-1`. **`latin-1` nunca falla**:
decodifica cualquier byte. Un CSV en UTF-16 entraba como `'ÿþA\x00p\x00e\x00l...'` y el import
**se completaba**, cargando nombres ilegibles en la base. Verificado en vivo antes de tocar nada.

Ahora la detección de UTF-16 (BOM y sin BOM) corre **antes**, así que latin-1 solo se alcanza
cuando el archivo genuinamente lo es.

⚠️ **Es un cambio de comportamiento en un flujo de producción**: un archivo UTF-16 que hoy se
carga como basura pasa a leerse bien. Es el arreglo, no una regresión, y ningún test fijaba la
basura. **La suite quedó en el mismo número que antes del cambio (1514) hasta que se sumaron los
tests nuevos** — o sea, cero regresiones en los dos flujos existentes.

### Sobre el BOM

El paso de UTF-8 usa **`utf-8-sig`**, que consume el BOM si está y se comporta como `utf-8` si no.
⚠️ Aclaración honesta, porque quedó anotado al revés en la conversación: **el BOM ya se manejaba
bien en los dos flujos** (nómina usaba `utf-8-sig` y evaluaciones tenía su rama explícita).
Verificado dos veces con archivos reales. Lo que se hizo es **blindarlo en un solo lugar**: con
`utf-8` pelado el `\ufeff` queda pegado al primer header, `str.strip()` NO lo saca (no es
whitespace en Python) y el error diría "falta la columna Apellido" con Apellido presente. Hay un
test que lo fija para que nadie lo cambie por `utf-8` "simplificando".

### 🔴 BLOQUEO PARA EL IMPORT DE VACACIONES PENDIENTES — es para RRHH, no de código

El archivo histórico de vacaciones **solo trae LEGAJO**, y `legajo` está **0 de 19** en
producción: RRHH nunca lo mandó, aunque el import de nómina ya sabe leerlo
(`HEADERS_OPCIONALES`). **Ese import hoy no tendría con qué matchear a nadie.**

Se resuelve de una de dos formas, las dos con RRHH:
- que la nómina mensual traiga la columna **Legajo**, o
- que el archivo de vacaciones traiga **DNI** (que es lo que hay que pedir ahora, mientras la
  estructura se está definiendo).

**No se implementó un fallback por nombre**: el archivo de vacaciones tampoco trae nombre. Queda
escrito en `services/_import_csv.py` para quien reciba el archivo definitivo.

### Variables de entorno · dependencias · Storage · endpoints · auth · dominios

**Ninguno.** Sin variables, sin dependencias, sin buckets, sin endpoints nuevos (los routers
existentes cambiaron por dentro: ya no decodifican, pasan bytes), sin cambios en el token.

---

## 2026-08-02 · Asignar un ÁREA ENTERA a un proyecto · commits pendientes ×3

**Qué cambió:** se puede sumar todos los empleados de un área a un proyecto de una vez, en vez de
elegirlos de a uno. Tres commits: (1) división de `asignaciones_service` (139/150), (2)
`ya_asignados` como grupo propio del resultado, (3) el alta por área + la UI.

**"Asignar por equipo" NO se hizo, y no es un olvido:** `empleados.equipo` está **0/19** en
producción (15 dicen "NO APLICA" y 4 vacío). No hay nada que agrupar. El trabajo era por ÁREA,
que sí está cargada 19/19. Si RRHH quiere equipos de verdad, es una entidad nueva y un proyecto
aparte — antes hay que definir si un equipo es distinto del área.

### 🔴 ORDEN DE DEPLOY

1. `sofia-backend` deploya y da 200 en `/health`.
2. Recién entonces `sofia-front`.

**SIN MIGRACIÓN.** `proyecto_asignaciones` ya tenía todas las columnas: el alta por área no
agrega un dato nuevo, resuelve una lista de ids y usa el camino de escritura que ya existía.

⚠️ Si el front sale antes, el botón "Asignar el área" pega a un endpoint que no existe y da un
error genérico. No rompe la pantalla (el alta manual sigue andando), pero el mensaje no ayuda.

### Endpoint nuevo (CON auth)

- `POST /api/proyectos/{proyecto_id}/asignaciones/area` — gate `Seccion.PROYECTOS + WRITE`, 201.
  Sin franja de rate limit propia: escribe lo mismo que el bulk que ya existía y en el mismo
  volumen (el área más grande de producción tiene 9 personas).

### 🔴 CAMBIO DE CONTRATO en un endpoint que YA funcionaba

`AsignacionBulkResult` gana un tercer grupo: **`ya_asignados`**, separado de `errores`. Es
**aditivo** (nada se saca), pero **cambia lo que devuelve el bulk manual**, que ya estaba en
producción: un empleado que ya estaba asignado deja de contarse como error.

Es lo correcto —asignando un área entera lo normal es que la mitad ya esté, y "15 errores" se lee
como un fallo masivo— y la evidencia de que hacía falta estaba en el propio front: el mensaje
tenía que aclarar a mano *"N no se pudieron (ya asignados o inactivos)"* porque el tipo no
distinguía las dos cosas. Ahora lo dice el backend.

⚠️ **Cualquier consumidor del bulk que cuente `errores.length` va a ver un número menor.** Hoy el
único consumidor es el modal, y ya está actualizado.

### La decisión de diseño que hay que conocer antes de tocar esto

**Es una FOTO, no un vínculo vivo.** Se resuelven los empleados del área EN ESE MOMENTO y se
crean asignaciones individuales; el proyecto NO queda atado al área. Un alta posterior en el área
no entra sola, y —lo que importa— **sacar a alguien del área no le borra la asignación**. Un
vínculo vivo sí lo haría, y `proyecto_asignaciones` lleva `rol`, `valor_hora` y fechas POR
PERSONA, además de que `horas_proyecto` cuelga de una asignación concreta: borrarla se llevaría
horas cargadas, que es justo lo que `ASIGNACION_CON_HORAS` (409) protege.

**Y la barrera de empresa va en DOS PASOS separados**, que es lo que el próximo lector va a
querer "arreglar": el ÁREA se valida contra el header (404) y los EMPLEADOS se resuelven **sin**
filtro de empresa. Pasarle el `empresa_id` a `empleados_de_area` sería redundante (los empleados
de un área son de la empresa del área por construcción) y **silencioso**: un área ajena devolvería
lista vacía y el endpoint respondería "0 asignados, 0 errores" sin decir nada. Está escrito en
`services/_asignaciones_bulk.asignar_area`.

⚠️ **El caso cruzado no se puede probar con datos reales**: hay UNA sola empresa en producción y
las 9 áreas son todas suyas. Vive en los tests hasta que exista la segunda.

### Variables de entorno · dependencias · Storage · auth · dominios · procesos

**Ninguno.** Sin variables, sin dependencias, sin buckets, sin cambios en el token, sin nada
atado a una URL, y sin procesos de fondo (el alta por área es síncrona: el área más grande son
9 personas).

### 🚩 Para preguntarle a RRHH

`GESTION DE DEUDA` y `GD - GESTION DE DEUDA` son casi con seguridad **la misma área duplicada**
por el import de nómina (una por cada grafía del CSV). Con áreas duplicadas, "asignar el área"
asigna a la mitad de la gente.

---

## 2026-08-02 · Subtipos de ausencia: jerarquía de dos niveles · commits pendientes ×4

**Qué cambió:** el catálogo de tipos de ausencia pasa a tener **dos niveles**
("ENFERMEDAD FAMILIAR → Madre/padre", como vienen los archivos reales de RRHH), y el tipo
**"Injustificada" se desactiva**. Cuatro commits: (1) divisiones previas del front, (2) migración
088 + las dos guardas del modelo, (3) el filtro por familia, (4) panel de configuración y modal
de carga.

### 🔴 ORDEN DE DEPLOY

1. **Correr `backend/migrations/088_tipos_ausencia_jerarquia.sql`.**
2. Esperar a que `sofia-backend` deploye y dé 200 en `/health`.
3. Recién entonces `sofia-front`.

✅ **Las migraciones 086 y 087 YA ESTÁN CORRIDAS** (verificado contra el catálogo vivo el
2/8/2026: existen `empleado_superior_pendiente`, `plantillas_mail`, `mail_enviado` y
`usuario_integraciones.es_remitente_sistema`). **No se acumulan**: la 088 es la única pendiente.

⚠️ Si el front sale antes que el backend, el select de tipos pierde el agrupamiento (los subtipos
aparecerían planos) y el filtro por un padre devolvería solo sus filas directas. No rompe la
pantalla, pero da resultados incompletos sin avisar.

### Migraciones

- **088 `tipos_ausencia_jerarquia`** — **NO destructiva**: una columna nullable
  (`padre_id`, self-FK con `ON DELETE RESTRICT`), un CHECK de autorreferencia, un índice parcial,
  y una **baja LÓGICA** (`UPDATE ... SET activo = false`) de "Injustificada". No borra ni
  reescribe ninguna fila.
- `db/schema.sql` **actualizado**: la columna, la FK, el CHECK y el índice.

### 🔴 POR QUÉ ESTA MIGRACIÓN NO PUEDE ESPERAR

`solicitudes_ausencia` tiene **CERO filas** en producción. Hoy esto es un `ALTER TABLE` y un
`UPDATE` sobre 4 filas de catálogo. En cuanto RRHH cargue el histórico de ausencias —que está
esperando la definición del parser de import— el mismo cambio se convierte en una **reasignación
de `tipo_id` sobre filas vivas**: cada ausencia cargada como "Injustificada" habría que moverla a
un tipo real adivinando cuál era, un dato que no existiría en ningún lado. La ventana se cierra
sola y no vuelve a abrirse.

### Qué pasa con "Injustificada" (y por qué se desactiva, no se borra)

Mezclaba dos ejes que el modelo ya separa: la NATURALEZA de la ausencia (`tipo_id`) con su
CALIFICACIÓN (`justificada`). Y `_reporte_ausentismo` **ya calcula el ausentismo injustificado
leyendo `justificada`, no el tipo** — o sea que el eje correcto ya estaba en uso y este tipo solo
podía contradecirlo. Se desactiva porque `solicitudes_ausencia.tipo_id` es una FK **sin
ON DELETE**: borrarlo fallaría, y si no fallara se llevaría el historial.

🚩 **"Otro" NO se toca todavía.** Es un anti-tipo (existe para que la carga no se trabe y su
efecto real es que la información se pierde ahí adentro), pero sin el catálogo real cargado
sacarlo trabaría la carga. **Se desactiva cuando RRHH cargue sus tipos propios.**

### Variables de entorno · dependencias · Storage · endpoints · auth · dominios

**Ninguno.** Sin variables nuevas, sin dependencias, sin buckets, sin endpoints nuevos (los de
tipos ya existían y solo aceptan un campo más), sin cambios en el token, sin nada atado a una URL.

### Procesos que no corren en serverless

**Ninguno.** El filtro por familia resuelve los hijos en UNA query adicional, solo cuando hay
filtro de tipo. Con profundidad garantizada en 2 no hay recursión.

### Detalle que le sirve al dev de AWS

**Se cerró un hueco en `tests/_postgrest_schema.py`**: no detectaba que un embed
**self-referencial** por nombre de tabla es ambiguo. `entre(a, a)` cuenta UNA relación, pero
PostgREST igual responde **PGRST201** porque esa única FK se recorre en los dos sentidos. Es la
misma clase de bug que dejó 6 reportes en blanco en producción. Ahora lo atrapa, y el embed de
producción desambigua por columna (`padre:padre_id`), siguiendo el precedente de
`_empleado_row.manager:manager_id`.

---

## 2026-08-02 · Envío de mails por Gmail con plantillas editables · commits pendientes ×6

**Qué cambió:** el sistema pasa a **enviar mails**, cosa que hoy no hace (existía
`resend_api_key` y ningún service la importaba). Se manda **por Gmail**, reusando el OAuth que ya
existe, con plantillas que RRHH escribe desde `/configuracion`. Seis commits: (1a) división de
`gmail_service` (150/150) extrayendo el token a `_google_token.py`, (1b) los **tres bugs del
refresh** que ya estaban rotos para la lectura, (2) casilla del sistema + scope de envío +
aviso en la UI, (3) `services/mailer/` como punto único + salida de Resend, (4) migración 087 +
modelo, (5) catálogo de variables y render, (6) envío con presupuesto y la sección de la UI.

### 🔴 ORDEN DE DEPLOY

1. **Correr `backend/migrations/086_create_empleado_superior_pendiente.sql`** — 🚩 quedó
   pendiente de la sesión anterior y **va PRIMERO**. Son independientes entre sí, pero el orden
   numérico es el contrato del directorio.
2. **Correr `backend/migrations/087_mails_plantillas_y_remitente.sql`.**
3. Esperar a que `sofia-backend` deploye y dé 200 en `/health`.
4. Recién entonces `sofia-front`.
5. **Después del deploy: sacar `RESEND_API_KEY` y `RESEND_FROM_EMAIL` de Vercel** (`sofia-backend`).

⚠️ **El paso 5 va DESPUÉS y no antes.** Mientras el código viejo esté vivo, `resend_api_key` es
una env var obligatoria sin default: sacarla antes del deploy **tumba la app entera** —ni
`/health` responde—, porque `Settings()` se instancia en el import de `config.settings`.

### Migraciones

- **087 `mails_plantillas_y_remitente`** — **NO destructiva**. Tres piezas en una sola migración
  a propósito (mismo cambio funcional; partirla obligaría a coordinar tres pasos de deploy):
  · `usuario_integraciones` + `es_remitente_sistema` (con **índice único parcial**: garantiza que
    haya UNA sola casilla) y + `scopes text[]`;
  · **`plantillas_mail`** — `empresa_id` NULLABLE = plantilla global, con dos índices únicos
    parciales (en SQL `NULL <> NULL`, un UNIQUE común no impediría dos globales);
  · **`mail_enviado`** — el log, con el texto ya renderizado.
- `db/schema.sql` **actualizado**: 2 tablas nuevas (55 en total), 2 columnas, 3 FK, 2 PK, 1 CHECK
  y 6 índices.

### 🔴 EL SCOPE NUEVO OBLIGA A RECONECTAR — decirlo antes de que alguien intente mandar

Se agrega `https://www.googleapis.com/auth/gmail.send`. **Google NO amplía retroactivamente un
grant ya otorgado.** La integración que RRHH tiene conectada hoy:

- **sigue funcionando para LEER** (los mails de candidatos): no se rompe nada;
- **NO va a poder enviar** hasta que la persona reconecte. El primer intento devolvería
  **403 `ACCESS_TOKEN_SCOPE_INSUFFICIENT`** — no un 401: el token es válido, falta el permiso.

Por eso se persisten los scopes concedidos y **la pantalla de Configuración ya avisa** ("esta
cuenta está conectada solo para lectura, volvé a conectarla"). Reconectar es un clic: el flujo ya
fuerza la pantalla de consentimiento (`prompt=consent`), así que devuelve refresh token nuevo.

### 🔴 HAY QUE DESIGNAR UNA CASILLA DEL SISTEMA — sin eso no sale ningún mail

`usuario_integraciones` es por usuario y no tiene `empresa_id`. Sin una casilla designada, el
mail saldría de la cuenta personal de quien apretó el botón, y **un proceso automático no
tendría de qué cuenta salir**. El envío corta con `MAIL_SIN_REMITENTE` (400) y un mensaje que
dice qué hacer; no hay fallback silencioso a "la del usuario logueado", a propósito.

⚠️ **La FK `usuario_integraciones.user_id → users(id)` es `ON DELETE CASCADE`**: si se da de baja
al usuario que sostiene la casilla, la integración se borra con él y el envío deja de funcionar.
Hoy eso NO es silencioso (falla al intentar mandar, y la pantalla muestra que no hay casilla),
pero se entera al MANDAR y no al BORRAR. 🚩 La guarda —bloquear esa baja con un 409— **no se
implementó**: vive en `usuario_service.eliminar_usuario`, que está en **149/150**, así que exige
dividirlo primero. Queda propuesta como tanda propia.

### Endpoints nuevos (los 5 CON auth, ninguno público)

- `GET /api/plantillas` · `PUT /api/plantillas` · `DELETE /api/plantillas/{id}` ·
  `POST /api/plantillas/preview` — gate `Seccion.CONFIGURACION` (preview: **además** lectura de
  EMPLEADOS, porque lee datos de un empleado real).
- `POST /api/plantillas/enviar` — gate CONFIGURACION + WRITE y **franja de rate limit propia,
  `scope="mail"`, 20/hora**: manda correo a nombre de la empresa, no puede correr bajo el
  baseline de 300/min.

### Variables de entorno

- **SE SACAN: `RESEND_API_KEY` y `RESEND_FROM_EMAIL`** (ver el orden arriba). Un test estructural
  impide que `resend_api_key` vuelva de un merge distraído.
- **NUEVA, con default: `MAIL_PRESUPUESTO_SEGUNDOS`** (default **120.0**). Presupuesto de un
  envío masivo; más chico que el del import (280) porque acá cada unidad es una llamada de red
  externa. No hace falta declararla, pero conviene.
- Sin dependencias nuevas: el Markdown→HTML se implementa a mano justamente para **no** sumar una
  librería de sanitización.

### Procesos que no corren en serverless

**Ninguno nuevo, y es deliberado.** No hay cola ni background job: no existen en este stack (cero
`BackgroundTasks`, cero `asyncio.create_task` en el backend, y en serverless un thread
post-respuesta muere con la función). El envío masivo usa **presupuesto de tiempo + reporte
parcial**, calcado de `LoteNomina`, y la **idempotencia del log** hace que reintentar el mismo
lote no reenvíe lo que ya salió. El peor caso que eso evita no es "tarda": es mandar 30, morir en
el timeout de Vercel (`maxDuration: 300`) y que el reintento mande esos 30 de nuevo.

### Datos personales

⚠️ **`mail_enviado` contiene datos personales por definición** (nombre, dirección y el cuerpo
entero). Se lee gateada por CONFIGURACION y **NO tiene endpoint de export** — el repo ni siquiera
expone un `find_all` paginado, solo un `ultimos()` con límite duro. Cuando el volumen moleste, la
salida es una política de retención (borrar el cuerpo a los N meses), no dejar de registrar.

### Buckets de Storage · auth · dominios

**Ninguno.** No hay buckets nuevos, no cambia el modelo de autenticación ni los claims del token,
y nada queda atado a una URL nueva (el callback OAuth es el que ya existía).

---

## 2026-08-02 · Superior cruzado entre empresas: el import escribe `manager_id` y el ownership de mandos_medios ignora la empresa · commits pendientes ×6

**Qué cambió:** dos cosas que se habilitan mutuamente. (a) El import de nómina **ya escribe
`manager_id`**: leía "Apellido Superior"/"Nombre Superior" de las 19 filas y las tiraba
(`manager_id` estaba 0/19 en producción, y sin ese campo un usuario `mandos_medios` no ve
absolutamente nada). Ahora las resuelve en una **segunda pasada, después del loop**, porque el
jefe puede estar en una fila posterior a la de su subordinado. (b) Se cerró la decisión de
producto de que **un empleado puede tener superior de otra empresa del grupo**: para
`mandos_medios` el `manager_id` REEMPLAZA al filtro de empresa, en lectura y en escritura.
Seis commits: (1) división previa del service de import, (2) aflojar la validación de empresa
del superior + arreglar el chequeo de ciclos, (2b) las dos validaciones de superior a
`services/_empleados_manager.py` —refactor puro, `_empleados_utils` se había pasado de 150 al
documentar la excepción—, (3) el ownership cruzado, (4) el import escribiendo `manager_id`,
(5) migración 086 + botón "resolver pendientes".

### 🔴 ORDEN DE DEPLOY — la migración 086 va PRIMERO

1. **Correr `backend/migrations/086_create_empleado_superior_pendiente.sql`** en producción.
2. Esperar a que `sofia-backend` deploye y dé 200 en `/health`.
3. Recién entonces `sofia-front`.

Si el front sale antes, el panel de pendientes de `/empleados` pega a dos endpoints que no
existen todavía. **No rompe la pantalla** (el panel se traga el error y no se renderiza), pero
tampoco avisa de nada. Y si el backend sale sin la migración, el import corre igual y escribe los
`manager_id` —la persistencia de pendientes es best-effort y solo loguea un warning—, pero los
pendientes se pierden y el botón no tiene qué resolver.

### Migraciones

- **086 `create_empleado_superior_pendiente`** — tabla NUEVA. **No destructiva**, no toca datos
  existentes, `CREATE TABLE IF NOT EXISTS`. Guarda el nombre crudo del superior que el import no
  pudo resolver, para poder completarlo después sin re-subir el CSV. PK = `empleado_id`,
  FK a `empleados` con `ON DELETE CASCADE` y a `empresas`. Un índice por `empresa_id`.
  🚩 **Es solo hacia adelante:** el import de julio ya corrió sin ella y sus superiores no
  quedaron registrados. Se recuperan re-subiendo ese CSV, no desde la base.
- `db/schema.sql` **actualizado** con la tabla, sus 2 FK, su PK y su índice (53 tablas).

### Endpoints nuevos (los dos CON auth, ninguno público)

- `GET  /api/importacion/superiores-pendientes` — gate `IMPORTACION + READ`.
- `POST /api/importacion/superiores-pendientes/resolver` — gate `IMPORTACION + WRITE`, y **entra
  en la franja de rate limit `scope="import"` (10/hora compartido con el import de archivos)**.
  Escribe lo mismo que el import, así que comparte su presupuesto a propósito.

### 🔴 LA INVARIANTE DE LA FASE 2 AHORA TIENE UNA EXCEPCIÓN DOCUMENTADA

Hasta hoy la regla era absoluta: **toda consulta filtra por empresa**. Ya no. Para el rol
`mandos_medios`, y solo en VACACIONES y AUSENCIAS, el `manager_id` reemplaza ese filtro: sus
subordinados son suyos sin importar de qué empresa del grupo sean.

La excepción vive **concentrada en `backend/services/_alcance_mandos.py`**, en un módulo propio
para que se lea como lo que es y no como un patrón a copiar. Ahí está el porqué completo. Tres
cosas que hay que saber sin leer el código:

- **`_ownership_filter.py` NO se tocó**, ni su contrato de la tupla `(ids, vacio)`. La
  intersección empresa ∩ ownership nunca ocurrió ahí dentro: ocurre en el WHERE del repo, como dos
  predicados independientes. Alcanzó con no mandarle el `empresa_id`.
- **La excepción NO alcanza a `admin_rrhh` ni a `gerencia_lectura`**, ni a ninguna otra sección.
- ⚠️ **Si algún día se agrega una sección a `MANDOS_MEDIOS_SECCIONES`, hay que revisar si compone
  ownership.** Los REPORTES **no lo hacen** (cero `ownership` en `services/reportes/`): hoy no es
  una fuga porque el gate de permisos los frena con 403, pero abrirlos a ese rol devolvería datos
  org-wide sin filtrar.

### Bug arreglado de paso (no era del cambio, ya estaba)

**Un ciclo de jefaturas que cruzaba empresas no se detectaba.** `ensure_no_ciclo_manager`
recorría la cadena acotada al `empresa_id` del request: el primer salto fuera de la empresa
devolvía `None` y la función respondía "no hay ciclo". Un ciclo A(empresa 1) → B(empresa 2) → A
cuelga `ids_subordinados` igual que uno interno. Ahora el recorrido es global.

### Variables de entorno · dependencias · Storage · auth · dominios

**Ninguno.** No hay variables nuevas, ni dependencias, ni buckets, ni cambios en el token o en
los claims, ni nada atado a una URL.

### Procesos que no corren en serverless

**Ninguno nuevo**, pero un aviso de costo: la resolución de superiores hace **una lectura
full-table de `empleados`** (4 columnas, una sola vez por import o por clic del botón). Es
deliberado y está justificado en `repositories/_empleado_lookup_repo.indice_por_nombre`: el jefe
puede estar cargado en una empresa que no tiene ni una fila en el CSV que se importa, así que
acotar la búsqueda por empresa fallaría **en silencio** justo en el caso cruzado. 🚩 **Disparador
para revisarlo: que el padrón pase de unos pocos miles de empleados** (hoy son 19). La salida
entonces NO es volver a acotar por empresa, sino un índice normalizado en la base.

---

## 2026-08-02 · Configuración de reglas de negocio: dos tablas nuevas y el "22" sale de código · commits pendientes ×5

**Qué cambió:** las reglas de vacaciones y ausentismo dejaron de estar hardcodeadas y pasaron a
`parametros_empresa` y `reglas_vacaciones_escala` (migración **085**), las dos con `empresa_id NULL`
= fila global y lectura por `COALESCE(mi empresa, global)`. Se agregó `Seccion.CONFIGURACION`,
un router propio `/api/configuracion`, y a `tipos_ausencia` dos columnas: `empresa_id` nullable y
`cuenta_ausentismo`. La pantalla `/configuracion` se dividió (era 390/150) y ahora es un acordeón
con tres bloques nuevos. Cinco commits: (1) división de la pantalla sin cambio funcional,
(2) el gate por bloque, (3) migración + backend, (4) el 22 configurable, (5) la UI.

### 🔴 ORDEN DE DEPLOY — la migración 085 va PRIMERO, y no es opcional

1. **Correr `backend/migrations/085_configuracion_reglas.sql`** en producción.
2. Esperar a que `sofia-backend` deploye el commit nuevo y dé 200 en `/health`.
3. Recién entonces `sofia-front`.

**Por qué importa acá más que de costumbre:** el cálculo del ausentismo pasó a LEER la base de
días hábiles de `parametros_empresa`. Si el backend sale antes que la migración, el reporte R10
y el KPI 26 del dashboard fallan con `CONFIG_GLOBAL_FALTANTE` (500) — el dashboard lo absorbe con
su fail-safe por KPI y lo muestra vacío + anotado en `errores`, pero **el reporte de ausentismo
descargable falla entero**. El resto de la app no se ve afectado.

**Impacto en infraestructura:**

- **Migración 085 (`085_configuracion_reglas.sql`) — NO CORRIDA, la corre Franco.** Crea
  `parametros_empresa` y `reglas_vacaciones_escala`, siembra su fila global, y altera
  `tipos_ausencia`. **Es aditiva salvo por UN paso:** dropea la constraint
  `tipos_ausencia_nombre_key` (`UNIQUE (nombre)`) y la reemplaza por dos índices únicos
  parciales. No puede perder datos —solo afloja una restricción— pero un rollback exige
  reponerla a mano. Idempotente (`IF NOT EXISTS` / `ON CONFLICT DO NOTHING`).
  - ⚠️ **No pudo verificarse por ejecución:** no hay Postgres en el entorno de desarrollo y no
    se ejecuta DDL contra producción desde acá. Revisada a mano contra el catálogo vivo.
  - 🔴 Los índices únicos son **parciales** a propósito. Un `UNIQUE (empresa_id)` común NO
    restringe las filas globales, porque en SQL `NULL <> NULL`: dejaría entrar filas globales
    duplicadas y la lectura elegiría una al azar, cambiando las reglas de todas las empresas
    según el plan de la query. Hay un test que lo custodia.
- **Endpoints nuevos** — `GET /api/configuracion`, `PUT /api/configuracion/parametros`,
  `PUT /api/configuracion/escala`, `PATCH /api/ausencias/tipos/{tipo_id}`. **Ninguno es
  público**: los tres primeros van con `Seccion.CONFIGURACION`, el PATCH también.
  `GET /api/ausencias/tipos` acepta ahora `?incluir_inactivos=true`.
- **Variables de entorno:** ninguna nueva.
- **Dependencias:** ninguna nueva. El acordeón usa `@base-ui/react`, que ya estaba.
- **Storage, jobs, auth, CORS:** sin cambios.
- **Un repo más a portar a asyncpg** (`configuracion_repo.py`) → van **55**.

**Decisiones que conviene conocer antes de tocar esto:**

- 🔴 **El PERÍODO VACACIONAL ("octubre a abril") es un concepto NUEVO y hoy SOLO se guarda.**
  No es cuándo se ganan los días ni cómo se mide la antigüedad: es cuándo se pueden TOMAR.
  **NO existe ninguna validación que impida cargar una licencia fuera de esa ventana**, y no la
  va a haber hasta que se defina si BLOQUEA o solo AVISA — las dos opciones tienen consecuencias
  opuestas sobre los imports históricos. La pantalla lo dice en un aviso explícito. Lo mismo vale
  para la escala, el corte de antigüedad, el primer año y el vencimiento: se guardan y se
  muestran, y **ningún cálculo los consume todavía**. El único valor cableado es
  `base_dias_habiles`.
- **`cuenta_ausentismo` NO reemplaza a `solicitudes_ausencia.justificada`** — es aditivo. Son
  preguntas distintas: `justificada` es un HECHO de la instancia ("¿esta vez trajo
  certificado?"), `cuenta_ausentismo` es una POLÍTICA del tipo ("¿maternidad computa?"). Las
  cuatro combinaciones son reales. `DEFAULT TRUE` = comportamiento idéntico al previo a 085.
- **`Seccion.CONFIGURACION` es propia y NO reusa VACACIONES ni AUSENCIAS**, porque
  `mandos_medios` tiene WRITE en esas dos y no debe poder cambiar la escala de toda la empresa
  desde la pantalla en la que carga una licencia.
- **`/configuracion` sigue sin gate de RUTA** (`permisos.ts` la deja fuera de `RUTA_SECCION`):
  ahí vive el cambio de contraseña, que todo usuario necesita. El gate va **por bloque**, con
  dos criterios distintos: integraciones se OCULTAN (son formularios de escritura, no hay nada
  que leer), reglas y tipos se muestran en SOLO LECTURA (el valor es información, y
  `gerencia_lectura` lee todos los reportes). Los tres gates se deciden **en la página**, no
  dentro de cada componente, porque el fetch vive en hooks y los hooks corren igual.
- **`_dashboard_kpis.py` se pasó de 150 al cablear la configuración** → se extrajo
  `calcular_headcount` a **`services/_dashboard_headcount.py`** (movido verbatim). Quien
  importe `calcular_headcount` desde `_dashboard_kpis` ahora rompe.

**Desprolijidades encontradas, no introducidas por esta sesión:**

- **`CLAUDE.md` decía que la última migración era la 081; van por la 084** (082 `es_publica` en
  onboarding_templates, 083 período de vacaciones, 084 drop de `modalidad_contratacion`). Con
  esta sesión, **085**. También declara **975 tests** cuando la suite corre **1299**. Los dos
  números quedan desactualizados en el doc; **no se tocaron en esta sesión más allá de las
  líneas del "22"**, porque corregir el estado general de CLAUDE.md excede el alcance y merece
  su propia pasada.
- **`CLAUDE.md` referencia `services/_kpi_helpers.py`, que NO EXISTE.** Los cálculos compartidos
  viven en `_dashboard_kpis.py` y en los submódulos de `reportes/`.
- **En la Mac aparecen archivos duplicados `* 2.ts` dentro de `.next/`** (`routes.d 2.ts`,
  `cache-life.d 2.ts`, …), probablemente por sincronización de iCloud. **Rompen `tsc --noEmit`
  con TS6200/TS2300 y no son código del repo** — `.next/` está gitignoreado. Se regeneran
  después de cada `npm run build`. Fix: `find .next -name "* 2.*" -delete`. **Si aparece un
  error de tsc en esos archivos, no es tuyo.**

---

## 2026-08-02 · Alertas del dashboard: agregadas, bloqueos de módulo y href propio · commits pendientes ×4

**Qué cambió:** el panel de alertas del dashboard dejó de ser "una línea por empleado sin email"
y pasó a tener tres familias: **bloqueos de módulo** (una tabla vacía deja un módulo inutilizable),
**alertas agregadas** de campo vacío con conteo y link al listado filtrado, y las informativas de
KPIs. Se agregó el filtro `sin_manager` a empleados, que es a donde linkea la alerta agregada.
Cuatro commits: (1) extracciones previas sin cambio funcional, (2a) divisiones de archivos sobre
el límite, (2b) el filtro, (3) el mecanismo de alertas.

### 🔴 Cambio de contrato en la respuesta de `GET /api/dashboard`

`AlertaResponse.entidad_id` **se reemplazó por `href`** (ruta ya armada por el backend, o `null`).
El front convertía SIEMPRE `entidad_id` en `/empleados/{id}`, así que la primera alerta de otro
tipo con id habría llevado a una ficha de empleado inexistente. El molde de adjuntos
(`entidad` + `entidad_id`) tampoco servía: una alerta agregada lleva a un **listado filtrado**
(`/empleados?estado=activo&sin_manager=true`), que no es un par (entidad, id).
**No hay consumidor externo** — el único cliente es nuestro front, que ya está migrado en el mismo
lote. Si alguien tenía un script contra ese endpoint, el campo dejó de existir.

### Endpoints tocados

- `GET /api/empleados` y `GET /api/empleados/exportar` aceptan **`sin_manager`** (bool, tri-estado:
  ausente = sin filtro · `true` = sin superior · `false` = con superior). Va en los DOS por la
  invariante list↔export; `tests/test_paridad_list_export.py` lo habría exigido solo.
- No hay endpoints nuevos, ninguno público, ninguno con rate limit distinto.

### Lo que el dashboard consulta ahora (5 conteos más por request)

`_dashboard_alertas.py` agrega un `select("id").limit(1)` por cada tabla de bloqueo
(`costos_nomina`, `inventario_items`, `capacitaciones`, `presupuesto_areas`, `vacantes`) más un
`count="exact"` sobre `empleados` por cada campo vigilado. **Las cinco tablas tienen `empresa_id`
propio (verificado contra el catálogo), así que el filtro va en el WHERE (Forma A)** y ninguna
necesita resolverse por join. Todo queda dentro del `_safe` por sección que ya existía: si un
conteo falla, el resto del dashboard se devuelve igual.
⚠️ Son 6-7 queries livianas más por carga de dashboard. Contra RDS no debería notarse; si el
dashboard se vuelve un punto caliente, el candidato natural es cachear los bloqueos (cambian de
estado una vez en la vida del sistema, no por request).

**Impacto en infraestructura:** Ninguno. Sin migraciones, sin env vars, sin dependencias, sin
Storage, sin procesos de fondo, sin cambios de auth. **La 085 sigue libre.**

### Notas para el que porte a asyncpg

- **Dos repos "nuevos" que en realidad son cortes:** `_empleado_lookup_repo.py` (los tres lookups
  de una fila, sacados de `empleado_repo.py` que estaba en 98/100) sigue el nombre del molde
  `migracionAWS/backend/repositories/empleado_lookup_repo_NEW.py` **a propósito**, para que el port
  aterrice ahí. Dos diferencias con el molde, documentadas en el archivo: acá las dos bajas ya
  viven en `_empleado_write_repo` y `find_by_id` sí entra al satélite.
- `find_all` usa **`.not_.is_("manager_id", "null")`** para el complemento. En asyncpg es
  `manager_id IS NOT NULL` — no traducirlo a `!= NULL`, que en SQL nunca es TRUE.
- El conteo de la alerta agregada usa **`estado = 'activo'`**, no `<> 'baja'`. No es
  intercambiable: tiene que ser el MISMO predicado que lleva el `href`, o el número del mensaje
  deja de coincidir con lo que ve el usuario al hacer clic (ver abajo).

### Lo que encontraron los tests, para que no se repita

1. **La alerta agregada mentía.** Contaba `<> baja` (6) y su href llevaba a un listado sin filtro
   de estado (7): el usuario leía 6, hacía clic y veía 7. El test que parsea el href y se lo pasa
   al repo REAL de empleados fue el que lo detectó. Ahora los dos lados llevan `estado = activo`.
2. **El mutation check sobrevivió a la primera.** Revertir el predicado a `<> baja` pasaba en verde
   porque el padrón del fake no tenía **ningún empleado en licencia** — la única fila que separa
   los dos predicados. Con esa fila agregada, la mutación mata 5 tests. Es la pregunta obligatoria
   de la regla transversal contestada en el archivo.
3. **`useFiltrosEmpleados.ts` estaba en 89/80 desde antes** y no figuraba en la lista de deuda de
   `CLAUDE.md`. Ahora quedó en 67, partido en tres (estado · catálogos · campos).

### ⚠️ Anotado, NO resuelto (fuera del alcance de esta sesión)

- **El gate del catálogo de tipos de ausencia es `AUSENCIAS + WRITE`**, así que `mandos_medios`
  puede crear tipos que son **globales** y afectan a todas las empresas. Con una sola empresa no se
  nota; se vuelve visible el día que exista la segunda. Debería gatearse por configuración.
- **`tipos_ausencia_service.create_tipo` disfraza cualquier excepción como `TIPO_DUPLICADO` (422)**:
  un timeout o un constraint distinto le dicen al usuario "el tipo ya existe".
- **La nota del "22 días hábiles"** (`_reporte_ausentismo.py:16`) tiene el número **tipeado dentro
  del string**, no interpolado. El día que el valor salga de configuración, la nota miente.
- **`CLAUDE.md` dice que las migraciones van por 081 y van por 084** (082/083/084 entraron con los
  últimos tres commits). Además dice 143 tests de front en 10 archivos: son 159 en 11.

---

## 2026-07-30 · Embed roto de sucesión + el validador de schema pasa a cubrir los repos · commits pendientes ×2

**Qué cambió:** se arregló el embed que tenía `GET /api/sucesion/planes` en **500** desde meses, y
—lo que importa más— el validador de selects contra `db/schema.sql` **dejó de mirar solo los
reportes y ahora barre `repositories/` y `services/` completos**.

### 🔴 Por qué: es la CUARTA vez que aparece la misma clase de bug

| # | Dónde | Síntoma |
|---|---|---|
| 1 | Los 6 reportes de Fase 1 | columnas inexistentes y embeds ambiguos → 400 / PGRST201 |
| 2 | Listado de plantillas de onboarding | mismo patrón |
| 3 | `planes_carrera_repo` | pedía `planes_carrera_hitos!planes_carrera_hitos_plan_emp_fkey`; la FK real es **`pc_hitos_plan_emp_fkey`** → **500** |
| 4 | `assessment_repo` + `assessment_resultados_repo` | **dos embeds ambiguos** (`assessment_links` y el anidado `assessment_campanas`, dos FKs cada uno) → PGRST201 latente |

**Ninguna la detectó la suite, y no por mala suerte: es estructural.** El fake de Supabase
implementa `select(*a, **k)` **ignorando el argumento**, así que acepta cualquier spec —exista o no
la columna, resuelva o no el embed—. Ningún test que pase por el fake puede desmentir un nombre mal
escrito. La #3 la encontró el **smoke test**; la #4 la encontró **el barrido nuevo**, en el mismo
commit que lo agregó.

`tests/_postgrest_schema.py` se había construido para cerrar la clase y validaba **solo los
generadores de reportes**. Los repos quedaron afuera, y por ahí entraron los casos 2, 3 y 4.

### El barrido nuevo — `tests/test_selects_repos.py`

- **Descubre los selects por INTROSPECCIÓN del AST**, nunca por una lista de archivos: los tres
  casos se colaron justamente por no estar en una lista. Un repo nuevo queda cubierto solo.
- Resuelve constantes de módulo, f-strings armados con ellas, y **constantes importadas de otro
  módulo** — el patrón `from ._empleado_row import SELECT, TABLE` que usan los repos partidos por
  límite de líneas, que son los más grandes.
- **Cobertura hoy: 46 selects con embed validados** sobre 189 encontrados.
- **Tres guardas contra el falso verde:** mínimo de selects (150), mínimo de embeds (40), y que
  ningún select dinámico aparezca sin declararse. Verificado por mutación: al romper la detección
  el barrido **falla** en vez de pasar en el vacío.
- Los **16 selects que no se pueden resolver estáticamente se DECLARAN con su motivo**, nunca se
  sacan del barrido. Están declarados **por archivo con su conteo**, así que un `.select(variable)`
  nuevo en un archivo ya declarado también dispara.
- Los generadores de reportes siguen cubiertos por `test_reportes_columnas.py`, que los valida
  **mejor**: ejecuta cada uno con un Supabase falso que captura el select real, dos veces, con y
  sin `area_id`. Un barrido estático solo vería una de las dos ramas — y ahí vivía el bug de
  ausentismo.

### Impacto en infraestructura

- **Ninguno.** Sin migraciones, sin env vars, sin dependencias, sin cambios de endpoint ni de
  contrato. Son tres nombres de FK en strings de select, más tests.
- **Sin orden de deploy.** El fix corrige queries contra el schema que YA está en producción.
- ⚠️ **`GET /api/sucesion/planes` estaba en 500 en producción** y ahora responde. El módulo de
  sucesión está oculto en el front, pero el backend está montado y el endpoint es alcanzable con
  token: por eso nadie lo reportó.
- ⚠️ Los dos embeds de **assessment** eran un bug LATENTE: el módulo está apagado
  (`ASSESSMENT_ENABLED=false`) y ese código no corre. Quedan arreglados para cuando se encienda.
  **`assessment_repo.py` sigue en 131 líneas contra un límite de 100** — ya estaba en 130 antes de
  esta sesión y CLAUDE.md lo documenta como legacy con CERO callers, candidato a borrar.

**Deuda que queda anotada:** `_postgrest_schema` valida nombres y relaciones, no tipos, filtros ni
RLS. Y los `.select()` con tabla o spec dinámicos (16) siguen sin validación estática — de esos,
los 7 de reportes están cubiertos en runtime y los 9 restantes son helpers genéricos verificados
caller por caller como sin embeds.


## 2026-07-29 · Import de nómina recuperable: presupuesto de tiempo · commits pendientes ×4

**Qué cambió:** el import de nómina ya no muere en silencio si se pasa de tiempo. Ahora tiene un
**presupuesto en segundos**: procesa filas, y cuando se acerca al techo **para ENTRE FILAS** y
devuelve el reporte completo de lo que hizo, marcado como parcial. En vez de un `504` con
`"Error del servidor"`, RRHH recibe *"llegó hasta la fila 73, quedaron 47, volvé a subir el mismo
archivo para continuar"*. **No se tocó la arquitectura del import** (sigue fila por fila) ni se
agregó persistencia de progreso: el reintento se apoya en el dedup por DNI que ya existía.

### 🔴 VARIABLE DE ENTORNO NUEVA — `IMPORT_PRESUPUESTO_SEGUNDOS`

**Default: `280.0`. Tiene default seguro, pero conviene declararla explícita en `sofia-backend`.**

**EL TECHO ESTÁ VERIFICADO** (docs de Vercel al 1/7/2026): con **fluid compute** —habilitado por
defecto en proyectos creados después de abril 2025, y este es de 2026— el plan **Hobby tiene 300 s
de default Y de máximo**.

- ⚠️ **En Hobby los 300 s son también el MÁXIMO: no se puede subir.** Un presupuesto > 300 no
  compra nada; el request muere antes de que el import pueda cortar solo.
- **280 deja 20 s de margen** para serializar la respuesta y emitir el evento de auditoría del
  corte — las dos cosas que ocurren DESPUÉS de la última fila.
- Un valor **≤ 0 significa SIN LÍMITE** (procesa todo, comportamiento previo). Degradado seguro:
  una configuración en 0 por error no rompe el import. Hay un test que fija que el **default sí
  enforza** un presupuesto, para que nadie lo lleve a 0 en silencio — y afirma la CONDUCTA
  (`> 0`), no el número, así que ajustar el valor no lo rompe.
- 🔴 **En AWS hay que REVISARLO en el cutover.** El techo lo van a poner ALB / Lambda / ECS, no
  Vercel.

> **Dato para el dev de infraestructura, ya resuelto:** `backend/vercel.json` declara
> `maxDuration: 300` **dentro de `builds[].config`**, que es el formato legacy v2 — la duración de
> una función se configura en la clave `functions` de nivel superior, que ese archivo no tiene.
> **Está mal ubicado, pero es INOCUO: el default de la plataforma ya es 300 s.** No hace falta
> tocarlo; sí conviene no confiar en él como si estuviera configurando algo.

### 🔴 TECHO DE PAYLOAD DE LA PLATAFORMA — 4,5 MB por request · LOS CUATRO LÍMITES ALINEADOS

Vercel rechaza cualquier request con body > **4,5 MB**, y lo hace **antes de invocar la función**:
el código nunca lo ve. Un límite propio por encima de ese número **no protege nada** — solo cambia
quién produce el error, y la plataforma produce un 413 crudo que el usuario no puede interpretar.

**No era decisión de producto:** los 10 MB no eran un requisito alcanzable. Un adjunto de 6 MB
**hoy no se puede subir**, con el límite en 10 MB o en 4,2. Lo único que decide el número es si el
usuario entiende por qué.

**Los cuatro límites de subida quedaron en 4,2 MB, derivados de un solo valor** (`utils/files.py`):

| Constante | Antes | Ahora |
|---|---|---|
| `MAX_SIZE_CSV` | 5 MB | **4,2 MB** |
| `MAX_SIZE_CERTIFICADO` | 10 MB | **4,2 MB** |
| `MAX_SIZE_ADJUNTO` | 10 MB | **4,2 MB** |
| `MAX_SIZE_CV` (era `cv_service._MAX_SIZE`) | 5 MB, en otro archivo | **4,2 MB**, constante compartida |
| `MAX_SIZE_LOGO` | 2 MB | **2 MB** — sin cambio, es criterio propio y ya estaba debajo del techo |

🔴 **`LIMITE_PLATAFORMA_MB = 4.5` en `utils/files.py` es el ÚNICO número a revisar cuando cambie
el hosting.** Los cuatro derivan de `MAX_SIZE_SUBIDA`, que sale de ahí con ~0,3 MB de margen (el
request pesa más que el archivo: un multipart lleva boundaries, headers por parte y el nombre).
**En AWS ese techo lo define API Gateway / ALB, no la app** → se toca ese número, no los cuatro.
`tests/test_limites_subida.py` **barre las constantes por introspección** y falla si alguna queda
por encima del techo, así que un límite nuevo también queda cubierto sin tocar el test.

**Dos fuentes que se eliminaron** (es como se desincronizan):
- `cv_service` tenía su propio `_MAX_SIZE` y su propio *"5 MB"* hardcodeado en el mensaje. Ahora
  usa la constante compartida y el texto sale de `mensaje_supera_tamano`. Conserva su `code` y su
  status propios (`CV_TOO_LARGE`, 413): no se cambió el contrato HTTP.
- El **front** tenía dos números distintos, los dos mal: `FileUpload` decía 10 MB y `CvField` 5 MB.
  Ahora salen de `frontend/lib/limitesSubida.ts`. ⚠️ Es **espejo manual** del backend —mismo patrón
  y mismo riesgo que `permisos.ts` ↔ `permisos.py`, sin test que los compare—; el backend sigue
  siendo el único que enforza, el front solo da feedback antes de gastar la subida.

⚠️ El mensaje pasó de división entera a `:g`, porque con 4,2 MB decía *"4 MB"* y le mentía al
usuario sobre cuánto puede subir. Los límites redondos siguen diciendo *"2 MB"*.

### 🔴 PRIMERA MEDICIÓN DE TIEMPO DEL REPO

`logger.info("Import nómina empleados")` ahora incluye **`segundos`**, `parcial` y
`filas_sin_procesar`, **siempre**, no solo cuando corta. Hasta hoy **no existía una sola medición
de duración en ningún import del repo** (verificado en los cinco archivos del camino), así que el
presupuesto se calibraba a ojo. **Con el primer import real, ese log es el dato para ajustar la
env var** — y también para decidir si el rediseño a batch sigue siendo necesario. El campo
`segundos` viaja además en la respuesta HTTP.

### Contrato HTTP — 4 campos nuevos (aditivos, nada se saca)

`ImportacionNominaEmpleadosResult` suma: `parcial` (bool), `ultima_fila_procesada` (int|null),
`filas_sin_procesar` (int), `segundos` (float|null). Ningún consumidor existente se rompe.

### Otros dos cambios que van en el mismo empujón

- **Un UPDATE cuyo diff sale vacío ya NO se audita** (`services/_audit_omision.py`, aplicado en
  `AuditService.registrar`). Aplica a **todo el sistema**, no solo al import: una edición manual
  que no cambia nada tampoco deja evento. El escenario que lo motivó es el reintento —reimportar
  73 filas idénticas insertaba **73 filas en `auditoria` con `{}` y `{}`**, que no registran nada.
  🔴 La regla distingue `{}` ("difeé y no hubo cambios" → omitir) de `None` ("no se guarda dato, a
  propósito" → registrar). Esa distinción es lo que protege a `payload_cambio_password`, que es un
  UPDATE con los dos campos en `None` y cuyo valor está entero en el `evento`.
- **Bug de refresco del front, arreglado.** `ImportarNominaModal` solo llamaba `onSuccess()` si la
  respuesta llegaba, así que en un timeout **la lista de empleados no se refrescaba**: RRHH cerraba
  el modal viendo los datos viejos y creyendo que no se había cargado nada, con N empleados nuevos
  en la base. Ahora el refresco depende de que se haya **disparado** el import, no de que la
  respuesta haya vuelto.

### Impacto en infraestructura

- **Variables de entorno:** 🔴 **`IMPORT_PRESUPUESTO_SEGUNDOS` (nueva, default 280.0)** — ver arriba.
- **Migraciones:** ninguna. **Dependencias:** ninguna. **Buckets:** ninguno. **Endpoints:**
  ninguno nuevo; `POST /api/importacion/nomina-empleados` suma 4 campos a su respuesta.
  **Auth:** sin cambios. **Procesos fuera de serverless:** ninguno.
- **Orden de deploy:** indistinto (no hay migración). El backend con los campos nuevos y el front
  viejo conviven: los campos se ignoran.

---

## 2026-07-29 · Import de nómina: fix chico de performance, legajo y deprecación de modalidad (mig 084) · commits pendientes ×7

**Qué cambió:** el import de nómina de empleados dejó de hacer cuatro lookups que ya tenía
resueltos, consolidó la auditoría de las altas en un evento de lote, aprendió a leer la columna
**Legajo** (opcional), y se corrigió el reporte de distribución, que leía una columna que nadie
escribía. **La arquitectura del import NO se tocó**: sigue procesando fila por fila. El rediseño
a batch es otra sesión, y este trabajo existe para poder decidirla con un número medido.

### 🔴 EL DATO QUE DEFINE LA SESIÓN SIGUIENTE — no hace falta volver a medirlo

**Round-trips a la base POR FILA del CSV: de 8–13 a 2–8** (sin legajo; con legajo, +1).

| Escenario | Antes | Ahora |
|---|---|---|
| Alta, sin gerencia, sin fecha reconocida | 4 | **2** |
| Alta con gerencia | 8 | **3** |
| Alta con gerencia + cesión nueva | 13 | **8** |
| Update con gerencia + cesión ya existente (reimport) | 11 | **6** |

Para un archivo de 120 filas del caso realista: **~960 → ~400 round-trips**.

🔴 **Y el hallazgo que reordena la prioridad: la CESIÓN es ahora el costo dominante.** De las 8
queries del caso realista, **5 son `_nomina_cesiones.crear_si_falta`** (`cesion_service.listar`
= 2 queries, y si tiene que crear, +3 más). Ese camino NO se tocó en esta tanda. Sin él, un alta
con gerencia cuesta **3**.

**Implicancia concreta para quien retome:** antes de rediseñar el import a batch —dos pasadas,
chunks, upsert, mapa fila→resultado— **batchear las cesiones sale mucho más barato y baja de 8 a
4**. Recién ahí el batch tiene que justificarse contra ~4 por fila, no contra los 13 originales.
El diagnóstico completo (incluido por qué el batch es "batch" y no "batch + replicar
validaciones") quedó en el historial de git (`docs/Resultado_nomina_batch.md`, borrado el 2/8/2026).

**El conteo está FIJADO POR TESTS**: `tests/test_nomina_fix_chico.py::TestRoundTripsPorFila`
asserta 2 para un alta, 2 para un update y 3 para un alta con legajo, contando invocaciones de
repo con fakes que las registran. Si alguien vuelve a meter un lookup por fila, falla.

### Impacto en infraestructura

- **🔴 MIGRACIÓN 084 — `084_drop_modalidad_contratacion_y_nivel.sql`. ES DESTRUCTIVA (DROP
  COLUMN) y su ORDEN DE DEPLOY ES EL INVERSO al de una migración aditiva: EL CÓDIGO VA PRIMERO,
  LA MIGRACIÓN DESPUÉS.** Si las columnas se borran mientras el código viejo sigue arriba, todo
  SELECT que las pida —el listado de empleados, la ficha, el export— falla con **42703**. Con el
  código nuevo ya desplegado quedan sin lectores y el DROP no rompe nada.
  - Borra `empleados.modalidad_contratacion` (0/19 en producción, nadie la escribía) y
    `empleados.nivel` (0/19, cero referencias en el código). No hay UN dato que migrar: esa es
    toda la ventana, y se cierra cuando entren los imports de 50-120 empleados.
  - ⚠️ **`modalidad_trabajo` NO se toca.** Es otro concepto (dónde trabaja: presencial/remoto/
    híbrido, con CHECK cerrado). Su 19/19 en "presencial" **no es un dato cargado**: es el
    default de `schemas/empleado.py`, porque el CSV no trae la columna. Anotado para que nadie
    lo lea como "todos son presenciales".
- **`db/schema.sql` actualizado**: 53 tablas (sin cambio) · 341 → **340 constraints** (se va el
  CHECK de `nivel`) · 135 índices (sin cambio). Las dos columnas salieron del `CREATE TABLE
  public.empleados`.
- **Variables de entorno:** ninguna. **Dependencias:** ninguna. **Buckets:** ninguno.
  **Endpoints:** ninguno nuevo ni modificado. **Auth:** sin cambios. **Procesos fuera de
  serverless:** ninguno.
- ⚠️ **Contrato de la API, cambio menor:** el `EmpleadoResponse` deja de traer
  `modalidad_contratacion`. El front ya no la pide (ficha, modal, tipos y la whitelist de
  autocompletado se limpiaron en la misma tanda), pero cualquier consumidor externo del JSON la
  perdería.
- ⚠️ **`/api/empleados/valores-conocidos`**: la whitelist `CAMPOS_AUTOCOMPLETABLES` cambió
  `modalidad_contratacion` por `tipo_contrato`. Dejar la vieja habría dado 42703 tras la migración.

### El bug que se corrigió, para que no se vuelva a introducir

El reporte **R4 (distribución de plantilla)** y el **KPI de distribución del dashboard** leían
`modalidad_contratacion`, y mostraban **"Sin especificar" para toda la plantilla teniendo el
dato en la columna de al lado**. La causa: la migración 060 creó `modalidad_contratacion` como
campo de ficha, y poco después la 065 resolvió lo mismo por otro lado — mandó la columna
"Modalidad Contratacion" del CSV a `tipo_contrato` y la pasó a TEXT para que entrara. La 065
consolidó **de hecho pero no de derecho**: dejó la columna vieja viva, vacía y con un lector.
Ahora el generador lee `tipo_contrato` y la columna duplicada ya no existe.

### Lo que quedó anotado y NO se hizo

- **El batch del import.** Sesión aparte, y con la cesión como primer candidato (arriba).
- **`_nomina_cesiones` sigue con 2-5 queries por fila.** No estaba en el alcance de esta tanda.
- **El upsert de `nomina_import_repo.batch_upsert_nomina` manda la lista entera sin chunk.**
  Deuda latente, no problema actual: con 120 filas anda.

### Nota para el dev de AWS

Los cuatro atajos de lookup se implementaron como **parámetros keyword-only con default seguro
que ES el resultado de la validación**, no como flags que la apagan: `areas_validadas`,
`prior`, `auditar` y `AsignacionPrecargada`. **Con el default, todo caller que no sea el import
se comporta exactamente igual que antes** — hay un test que lo fija (`test_el_alta_manual_sigue_auditando`).
Al portar a asyncpg, esa forma se conserva: lo que cambia es de dónde sale el dato, no que la
validación exista.

---

## 2026-07-29 · Vacaciones: período, días pendientes y liquidación (mig 083) · commits pendientes ×4

**Qué cambió:** las vacaciones ahora distinguen **cuándo se tomaron** de **a qué año
corresponden** (`periodo`), y los **días que no se tomaron** pasan a existir como entidad
propia en una tabla nueva, `vacaciones_pendientes`. Los archivos históricos de RRHH traen las
dos cosas mezcladas: licencias del 13/4/2026 al 19/4/2026 que son del período 2025, y "2
semanas pendientes del 2025" que no tienen fechas porque nadie faltó ningún día. También se
agregó `dias_liquidados` a las dos tablas y un endpoint de edición para la licencia tomada.

🔴 **POR QUÉ DOS TABLAS Y NO FECHAS NULLABLE — no fusionarlas después "por simplicidad".** Se
diagnosticó permitir `fecha_desde`/`fecha_hasta` NULL en `solicitudes_vacaciones` sobre el
código real: **rompe 15 lugares, 6 con crash y 9 EN SILENCIO**. Ocho de los nueve silenciosos
comparten una sola causa: en SQL un predicado sobre NULL da NULL, que **no es TRUE**, así que
la fila se cae del WHERE — y como el `count` viaja en la misma query, se cae también del total.
Un filtro no deja pasar esas filas: **las esconde, y el total viaja escondido con ellas.** Los
dos peores: el reporte de saldos (R11) **infla el saldo** —le dice a RRHH que el empleado tiene
más días de los que tiene— y el bloqueo por período cerrado **deja de aplicar**. Con tablas
separadas, `fecha_desde` y `fecha_hasta` siguen NOT NULL y nada de eso pasa: los reportes, el
mapa, el saldo, el export y los filtros no ven la tabla nueva. Hay tests que lo verifican.

🔴 **`dias_liquidados` es un INT y no un bool `liquidada`.** En el archivo real **todas** las
filas dicen "Liquidado", incluidas las tomadas, porque las vacaciones siempre se pagan: lo que
separa las dos tablas es **si se tomó**, no si se pagó. Y con un bool no se puede representar
una liquidación **parcial** (5 de 10 días) sin una segunda fila del mismo `(empleado, período)`,
que es justo lo que la UNIQUE prohíbe. La UI lo maneja como un tilde binario; el modelo ya
soporta el parcial si RRHH lo confirma, sin otra migración.

**Impacto en infraestructura:**

- **🔴 MIGRACIÓN 083 — `083_vacaciones_periodo_y_pendientes.sql`. ORDEN DE DEPLOY: LA MIGRACIÓN
  VA ANTES QUE EL CÓDIGO.** El backend nuevo escribe `periodo` y `dias_liquidados` en cada alta
  de vacaciones y lee la tabla `vacaciones_pendientes` al abrir la pantalla; si el código sale
  primero, **el alta de vacaciones falla con 500** (columna inexistente) y la sección de días
  pendientes tira error. Al revés no rompe nada: la migración es **no destructiva** (agrega
  columnas nullable/con default y crea una tabla) y es segura de correr con la app arriba.
- **Tabla nueva `vacaciones_pendientes`** con `UNIQUE (empleado_id, periodo)` — le da
  idempotencia al import histórico (`ON CONFLICT` actualiza en vez de duplicar), que es
  precisamente lo que `solicitudes_vacaciones` **no** tiene. Lleva FK compuesta contra
  `empleados(id, empresa_id)`, igual que `sv_empleado_empresa_fk`, y RLS habilitada sin
  policies (deny-all; el control es app-level, mismo criterio que 061 y 066).
- **`db/schema.sql` actualizado**: pasa de 52 a **53 tablas**, de 331 a **341 constraints** y
  de 132 a **135 `CREATE INDEX`**.
- **Trigger nuevo** `trg_vacaciones_pendientes_updated_at` — usa `public.set_updated_at()`, la
  misma función que el resto. **Suma uno a los 36 triggers de `updated_at` que `schema.sql` no
  trae y que la migración 077 (en `migracionAWS/`) recrea: pasan a ser 37.**
- **Endpoints nuevos, todos con auth y gate `Seccion.VACACIONES`** (ninguno público):
  `GET·POST /api/vacaciones-pendientes`, `GET /api/vacaciones-pendientes/empleado/{id}`,
  `PUT·DELETE /api/vacaciones-pendientes/{id}`, y `PUT /api/vacaciones/{id}` (edición de la
  licencia tomada). **Prefijo propio y no `/api/vacaciones/pendientes`**: el `GET
  /api/vacaciones/{id}` se comería la ruta estática, la misma colisión que `main.py` ya había
  resuelto montando `vacaciones_empleado` antes que `vacaciones`.
- **Variables de entorno:** ninguna. **Dependencias:** ninguna. **Buckets:** ninguno.
  **Procesos fuera de serverless:** ninguno. **Auth:** sin cambios.

**Anotado, fuera de alcance de esta sesión:**
- **El cálculo del saldo NO se tocó**: sigue funcionando exactamente como antes. Depende de si
  los días no usados se acumulan al año siguiente, que se define con RRHH. Hay un test que
  falla si alguien engancha los pendientes al saldo antes de esa definición.
- **El bloqueo por período cerrado NO aplica a los pendientes**, deliberadamente. Las cuatro
  razones están escritas en `services/vacaciones_pendientes_service.py`. Revisar cuando RRHH
  cierre un período de verdad Y se defina la acumulación.
- **El import queda pendiente**: no hay ancla de matcheo (`legajo` está 0/19 y el CSV de nómina
  ni siquiera trae esa columna — ver `docs/DECISIONES.md`).

**Corrección al `CLAUDE.md`:** decía "79 archivos SQL, backend va por 081". Eran **80** y iba
por **082**; con esta sesión son **81** y va por **083**.

---

## 2026-07-28 · C6 sesión 2 · visibilidad pública/privada de plantillas (mig 082) · commits pendientes ×4

**Qué cambió:** las plantillas de onboarding ahora pueden ser **compartidas** (las ve todo el
equipo, es el default) o **privadas** (solo su autor). El filtro va server-side, en el WHERE, y
se compone por INTERSECCIÓN con la barrera de empresa —empresa primero—; `gerencia_lectura`
no se filtra, ve todo. Un `created_by IS NULL` cuenta como pública, que es lo único que evita
dejar plantillas inalcanzables cuando se borra el usuario dueño (la FK es ON DELETE SET NULL).
El gate vive en un helper nuevo, `services/_template_scope.py`, y no en el service: **tres
caminos leen una plantilla por id sin pasar por esa clase** (`add_tarea`, el alta de onboarding
y la plantilla por defecto), así que un gate adentro del service quedaba incompleto por
construcción. Cierra el Bloque C.

🔴 **CAMBIO DE CONTRATO HTTP — `POST /api/onboarding/{empleado_id}/iniciar`.** Pedir el
`template_id` de una plantilla de OTRA empresa devolvía **422 `EMPRESA_MISMATCH`**; ahora
devuelve **404 `TEMPLATE_NOT_FOUND`**, el mismo que un id inventado. El 422 era un oráculo de
enumeración: un status distinto confirmaba que esa plantilla existe. La guarda se **borró** (no
quedó como guarda muerta) porque además era inalcanzable: la plantilla ahora se resuelve contra
la empresa del EMPLEADO antes de decidir, y `empleados.empresa_id` es NOT NULL. Si algún
cliente discriminaba por 422, deja de recibirlo.

🔴 **Agujero semántico cerrado:** `get_default_template` elegía "la primera plantilla activa de
la empresa" sin mirar visibilidad. Sin el fix, una plantilla marcada privada podía seguir
siendo la que el sistema usa para onboardear a todo el equipo.

**Impacto en infraestructura:**
- **Migraciones: 082** `082_add_es_publica_onboarding_templates.sql` — agrega
  `es_publica boolean NOT NULL DEFAULT true` + un índice parcial sobre las privadas.
  **NO DESTRUCTIVA**: solo agrega una columna con default, no toca datos y **no cambia lo que
  ve nadie** (el default reproduce el comportamiento actual). Segura con la app arriba.
- ⚠️ **ORDEN DE DEPLOY: LA MIGRACIÓN VA ANTES QUE EL CÓDIGO.** El código nuevo pide `es_publica`
  en el SELECT de los dos endpoints de lectura de plantillas; si el código sale primero, esas
  queries piden una columna inexistente y PostgREST responde **400 42703**. Al revés no hay
  problema: la columna con su default es inerte para el código viejo.
- **`backend/db/schema.sql` actualizado**: la columna en `CREATE TABLE onboarding_templates` y
  el índice `idx_onboarding_templates_privadas`.
- **Variables de entorno:** ninguna. **Dependencias:** ninguna. **Storage:** ninguno.
- **Endpoints:** ninguno nuevo. `PUT /api/onboarding/templates/{id}` acepta `es_publica` en el
  body y puede devolver **403 `TEMPLATE_NO_SOS_AUTOR`** (código nuevo) si quien lo manda no es
  el autor. `TemplateResponse` suma `es_publica` — aditivo, no rompe clientes.
- **Procesos fuera de serverless:** ninguno. **Autenticación:** sin cambios en el modelo ni en
  los claims; se **lee** `request.state.user["rol"]` además del `id`, los dos ya estaban.
- **URLs/dominios:** ninguno.

---

## 2026-07-28 · C6 sesión 1 · autor de las plantillas de onboarding · embed ambiguo · commits pendientes ×5

**Qué cambió:** preparación de C6 (visibilidad pública/privada), sin agregar todavía la
visibilidad. Se dividieron las dos páginas de templates, que estaban muy sobre el límite
(290 y 412 líneas), en 6 componentes + 1 hook bajo `components/features/onboarding/`. Se
alinearon los `confirm()`/`alert()` nativos al patrón canónico `ConfirmDialog` + toast de
Vacantes. Y se cableó `created_by`, que existía en la tabla desde la migración 007 con FK a
`users` pero **ningún camino de escritura la escribía**: toda plantilla creada por la app
nacía sin autor. Ahora el router lee el usuario del request, el repo lo persiste y la
respuesta lo expone con el nombre resuelto.

🔴 **Bug PREVIO encontrado y corregido en el camino, con impacto en producción:** los dos
endpoints de lectura de templates (`GET /api/onboarding/templates` y `.../{id}`) embebían
`onboarding_tareas(...)` sin nombrar la FK. Hay **DOS** relaciones entre `onboarding_tareas` y
`onboarding_templates` —la simple sobre `template_id` y la compuesta `(template_id, empresa_id)`
que agregó el retrofit multiempresa—, así que PostgREST no puede elegir y responde **300
PGRST201 en vez de datos**. No se había notado porque la tabla tiene 0 filas en producción y
nadie usó el módulo. Es el mismo caso que las 2 FKs de `costos_nomina` a `empleados`. Se nombró
la FK (`onboarding_tareas!onboarding_tareas_template_id_fkey`) y quedó cubierto por un test que
valida los dos `select` contra `db/schema.sql` con `tests/_postgrest_schema.py`.

**Impacto en infraestructura:**
- **Migraciones:** ninguna. `created_by` ya existía (migración 007). **No se agregó
  `es_publica`** — va en la sesión 2, y ahí sí habrá migración (la 082 es el próximo número
  libre; 001–081 está completo sin huecos entre `backend/migrations/` y `migracionAWS/`).
- **Variables de entorno:** ninguna.
- **Dependencias:** ninguna.
- **Buckets de Storage:** ninguno.
- **Endpoints:** ninguno nuevo. `POST /api/onboarding/templates` cambia su **firma interna**
  (ahora recibe `request`), no su contrato HTTP. `TemplateResponse` **suma dos campos**
  (`created_by`, `created_by_nombre`) — es aditivo, no rompe clientes.
- **Procesos fuera de serverless:** ninguno.
- **Autenticación:** sin cambios en el modelo ni en los claims. Se **lee** `request.state.user["id"]`,
  que `AuthMiddleware` ya dejaba puesto.
- **URLs/dominios:** ninguno.
- ⚠️ **Para el que migre a AWS:** el fix del embed depende del nombre de constraint
  `onboarding_tareas_template_id_fkey`. Si la reconstrucción en RDS renombra esa constraint,
  el embed vuelve a romperse — el test lo detecta, porque valida contra `db/schema.sql`.

---

## 2026-07-28 · Domicilio desglosado (migración 081) · commit pendiente

**Qué cambió:** `empleados.domicilio` era un único campo de texto libre, así que el domicilio
no se podía filtrar ni agregar. Se agregaron seis columnas estructuradas (calle, número,
piso/depto, localidad, provincia, CP). El texto libre se conserva. La provincia se valida
contra las 24 jurisdicciones argentinas.

**Impacto en infraestructura:** 🔴 **UNA MIGRACIÓN. Tiene ORDEN DE DEPLOY.**

- **`081_add_domicilio_desglosado.sql` — NO DESTRUCTIVA.** Solo agrega seis columnas nullable
  y dos índices parciales sobre `empleados`. No toca datos, no reescribe `domicilio`, no
  dropea nada. Es segura de correr con la aplicación arriba.
- 🔴 **ORDEN: LA MIGRACIÓN VA ANTES QUE EL CÓDIGO.** El backend nuevo hace `SELECT *` sobre
  `empleados` y valida la respuesta contra un schema que ya incluye las seis columnas; si el
  código sube primero, PostgREST devuelve filas sin esos campos. Como son opcionales, Pydantic
  no rompe — pero el modal guardaría los valores contra columnas inexistentes y el error
  aparecería recién al escribir, no al leer. **Migración → deploy backend → deploy front.**
- **`backend/db/schema.sql` actualizado** (columnas + los dos índices). Sigue siendo la fuente
  de verdad de reconstrucción.
- **Endpoint nuevo:** `GET /api/empleados/provincias` — autenticado, gateado por
  `Seccion.EMPLEADOS + READ`. Devuelve las 24 jurisdicciones para el select del modal.
- **`ubicacion` NO se tocó.** Es otra cosa: sale de "Ubicación Física" del CSV y es dónde la
  persona trabaja, no dónde vive. Sigue en 14/19.
- Sin variables de entorno, sin dependencias, sin buckets, sin cambios en el modelo de auth.

> **LOS CAMPOS NACEN VACÍOS, y no hubo nada que migrar.** `domicilio` estaba **0/19** en
> producción antes de esta tanda: ni un solo empleado tenía domicilio cargado. Eso quiere decir
> que **no hubo migración de datos ni parseo de texto libre** — que era el riesgo principal del
> trabajo y simplemente no se materializó. Verificado después de correr la migración: 19 filas,
> las seis columnas nuevas en NULL, `ubicacion` intacta en 14.
>
> Consecuencia: como en las dos tandas anteriores, **esto entrega capacidad, no valor
> observable**. Los cortes por provincia y localidad existen y están testeados, pero no hay
> nada que cortar hasta que RRHH cargue domicilios.

> ⚠️ **LA PROVINCIA ES UNA LISTA CERRADA, Y ESO ES LO QUE HACE QUE EL CAMPO SIRVA.** Si fuera
> texto libre, "Córdoba" / "CORDOBA" / "Cba" convivirían y agrupar por provincia volvería a ser
> imposible — o sea, un campo estructurado que no estructura nada.
>
> · Los nombres son los **oficiales del IGN**, tomados de la API Georef del Estado
>   (`apis.datos.gob.ar/georef/api/provincias`), no escritos de memoria. Incluyen los acentos y
>   la forma larga "Tierra del Fuego, Antártida e Islas del Atlántico Sur" — **ojo con esa: trae
>   comas**, así que en cualquier CSV va entre comillas.
> · **NO hay CHECK en la base ni tabla de catálogo.** La lista vive en UN solo lugar
>   (`backend/schemas/_provincias.py`) y el `Literal` de Pydantic rechaza con 422 lo que no esté.
>   Un CHECK sería una segunda copia; una tabla, un join y un ABM que nadie usaría.
> · El frontend **no tiene su propia copia**: la pide al endpoint nuevo. Hay un test que barre
>   el front y falla si alguien pega la lista ahí — el problema conocido de `permisos.ts` como
>   espejo manual de `permisos.py`, que esta vez se evitó por construcción.

## 2026-07-28 · Historial salarial en el legajo · area_id legible en auditoría · commit pendiente

**Qué cambió:** la ficha del empleado suma una sección de historial salarial que sale de la
serie de `costos_nomina` (una fila por empleado por mes), no del log de cambios. Endpoint nuevo
`GET /api/costos/nomina/empleado/{empleado_id}`. Además, el modal de auditoría dejó de mostrar
`area_id` como UUID: lo resuelve a nombre al renderizar.

**Impacto en infraestructura:** Un endpoint nuevo, ninguna migración.

- **`GET /api/costos/nomina/empleado/{empleado_id}`** — autenticado, **no** público. Gateado por
  `Seccion.COSTOS + READ` (no por EMPLEADOS, aunque se consuma desde la ficha) y con barrera de
  empresa sobre el empleado objetivo. Sin rate limiting propio: cae en el baseline general, como
  el resto de las lecturas.
- **Sin export**, a propósito. Si más adelante hace falta, hereda el chequeo de tope de filas.
- `routers/costos.py` estaba en 80/80: las dos escrituras salieron a `routers/costos_escrituras.py`.
  **Las rutas NO cambian** — el router nuevo se monta en el mismo prefijo `/api/costos`.
- Sin migraciones, sin variables de entorno, sin dependencias, sin buckets, sin cambios en el
  modelo de auth.

> **🔴 ESTA TANDA ENTREGA CAPACIDAD, NO VALOR VERIFICABLE. `costos_nomina` tiene 0 filas en
> producción.**
>
> No hay un solo sueldo cargado, para ninguno de los 19 empleados. Consecuencias concretas:
>
> · **La sección se ve, y dice "Todavía no hay sueldos cargados para este empleado".** Eso es lo
>   que va a ver RRHH el día que abran un legajo. No está rota.
> · **No se pudo verificar contra datos reales.** A diferencia de las tandas anteriores, donde
>   una query a producción confirmaba o desmentía el comportamiento, acá no hay nada contra qué
>   contrastar. **Los tests son la única red** — están escritos con eso en mente y cubren el
>   orden de la serie, las dos barreras, el vacío y la derivación del neto.
> · Lo mismo vale para el orden cruzando el cambio de año (diciembre 2025 después de enero 2026):
>   está testeado, no observado.
>
> Cuando RRHH cargue nómina, **esto hay que mirarlo en producción antes de darlo por bueno.**

> ⚠️ **QUÉ MONTOS MUESTRA, porque la tabla tiene cuatro y solo uno se carga.** `salario_bruto` es
> el sueldo (lo escriben los dos caminos). `cargas_sociales` también, y de ahí sale el neto
> (bruto − cargas), que **no es una columna**. `bonos` y `otros_costos` no los escribe nadie:
> columnas muertas, siempre 0. Y `total` es una columna GENERADA (bruto+cargas+bonos+otros), o
> sea el costo para la empresa, no lo que cobra la persona — por eso el endpoint **no** lo
> devuelve: en un legajo se leería como sueldo.

> **Sobre `area_id` en el modal de auditoría:** se resuelve al RENDERIZAR, no se guarda el nombre
> al escribir. Así quedan legibles también los 19 eventos ya guardados, que tienen el UUID
> adentro. **Efecto conocido: muestra el nombre ACTUAL del área, no el que tenía cuando se hizo
> el cambio.** Si un área se renombra, los eventos viejos pasan a mostrar el nombre nuevo. Es
> deliberado — la alternativa (congelar el nombre en el diff) solo serviría hacia adelante y
> reintroduciría un campo derivado, que es justo el bug que se acaba de cerrar.

## 2026-07-28 · El historial de cambios del legajo mostraba cambios que nunca ocurrieron · commit pendiente

**Qué cambió:** el diff de auditoría de empleados dejó de compararse sobre el objeto de
respuesta completo y pasa a compararse sobre columnas reales. Lo mismo en ausencias y
vacaciones, que tenían la misma forma sin haber llegado a manifestarla. Los payloads de costos
y de usuarios salieron a módulos propios para que el archivo volviera a entrar en su límite.

**Impacto en infraestructura:** Ninguno.

*(Sin migraciones, sin variables de entorno, sin dependencias, sin buckets, sin endpoints
nuevos ni removidos, sin cambios en el modelo de auth. No se borró ni se modificó ninguna fila
de `auditoria`.)*

> **🔴 QUÉ SE MOSTRABA MAL, Y DESDE CUÁNDO.**
>
> La ficha de cada empleado tiene una sección "Historial de cambios". Sobre 113 eventos de
> `entidad='empleado'` en producción, **93 tenían un diff que decía, textualmente, que el área
> y la empresa del empleado habían pasado a vacío**:
>
> ```
> antes:   {"area_nombre": "SALUD", "empresa_nombre": "SERVICIOS Y CONSULTORIA ... DOSUBA"}
> después: {"area_nombre": null,    "empresa_nombre": null}
> ```
>
> Ninguna de las dos cosas había cambiado nunca. La pantalla se lo afirmaba al usuario sobre
> empleados reales, con nombre y apellido. **Desde el primer día que existe el módulo:** los
> 94 eventos de modificación que hay en la base están todos afectados, el más viejo del
> 14/7/2026, que es cuando se cargaron los empleados.
>
> **La causa** es una asimetría de lectura, no un error de lógica. El "antes" se leía con un
> SELECT que resuelve los nombres de área y empresa por join; el "después" venía del
> `UPDATE ... RETURNING`, que no los trae. Comparar los dos objetos completos convertía esa
> diferencia de LECTURA en un cambio de DATOS. Los nombres nunca fueron columnas de
> `empleados`: son producto de cómo se consultó la fila.
>
> **Por qué la suite no lo veía:** el fake del repositorio construía el "antes" y el "después"
> con la misma factory, así que los dos lados tenían los nombres iguales y el fantasma no podía
> reproducirse. 899 tests en verde sobre un bug visible en la primera query a producción — el
> mismo modo de falla que los reportes de Fase 1.
>
> **Los eventos viejos NO se borran.** Un log del que se sacan las filas incómodas deja de ser
> auditoría, y además esos eventos sí registran algo cierto: que alguien editó el registro ese
> día. Lo que cambia es cómo se renderizan: las claves derivadas se filtran en pantalla y un
> evento que se queda sin campos visibles se muestra como *"Se editó el registro, sin cambios
> en campos auditados"*, que es exactamente lo que pasó. El filtro está declarado en un solo
> lugar y **solo aplica a eventos anteriores al fix**; cuando no queden, se borra entero.

> ⚠️ **UN EFECTO SECUNDARIO QUE CONVIENE CONOCER, porque agranda lo que se audita.** El diff
> ahora EXCLUYE los campos derivados en vez de ENUMERAR una lista de columnas. La lista curada
> que usan el alta y la baja tiene 7 campos, y `empleados` tiene 29 columnas editables más
> —`manager_id`, `dni`, `email_corporativo`, `fecha_ingreso`, `dias_vacaciones_asignados`…—.
> Enumerar habría dejado de registrar esas ediciones **en silencio**, que en un log de
> auditoría es peor que el fantasma que se vino a sacar. Consecuencia operativa: los eventos de
> modificación de empleado pueden traer más claves que antes, y la tabla `auditoria` va a
> crecer algo más rápido por evento. Nada que dimensionar hoy (133 filas en total), pero vale
> saberlo antes de estimar el volumen en RDS.

## 2026-07-28 · Seis reportes de Fase 1 estaban rotos en producción · exports de nómina y auditoría · entrevista de salida · commit pendiente

**Qué cambió:** cinco tandas. (1) Dos repos y un service se dividieron para volver a entrar en
su límite de líneas, sin cambio de comportamiento. (2) **Se arreglaron siete queries rotas en
los generadores de reportes**: dos pedían columnas que no existen y cinco armaban embeds que
PostgREST rechaza por ambiguos. (3) El listado de auditoría y la nómina del período ahora se
exportan a PDF/Excel/CSV/Word con los mismos filtros que la pantalla. (4) La entrevista de
salida del offboarding se puede registrar desde la ficha. (5) Áreas apareció en el sidebar.

**Impacto en infraestructura:** Endpoints nuevos, ninguna migración.

- **Tres endpoints nuevos**, los tres **autenticados** (ninguno público):
  - `GET /api/costos/nomina/exportar`
  - `GET /api/auditoria/exportar`
  - `PUT /api/offboarding/{instancia_id}/entrevista`
  Los dos de export entran en la franja de rate limiting compartida `export` (30/hora), la
  misma que ya usaban los otros ocho. No hay cupo nuevo que dimensionar.
- **Sin migraciones.** La entrevista de salida usa `offboarding_instancias.entrevista_salida` y
  `notas_entrevista`, que **ya existían en la tabla** desde su migración original y nunca se
  habían cableado. Verificado contra el catálogo de producción antes de escribir.
- Sin variables de entorno, sin dependencias, sin buckets, sin cambios en el modelo de auth.

> **🔴 LO QUE MÁS TE IMPORTA DE ESTA ENTRADA: seis de los once reportes de Fase 1 nunca
> funcionaron en producción, y la suite de 799 tests los daba por buenos.**
>
> Los reportes de rotación, onboarding, ausentismo, saldos de vacaciones, listado de
> vacaciones/ausencias, masa salarial y presupuesto vs. real devolvían un error de PostgREST en
> cada llamada — con datos o sin ellos, desde el día que se entregaron. Dos causas:
>
> 1. **Nombres de columna que no existen.** El reporte de rotación pedía `motivo` cuando la
>    columna se llama `motivo_egreso`. El de onboarding pedía `progreso`, que no es una columna
>    sino un cálculo sobre las tareas. PostgREST responde `400 42703`.
> 2. **Embeds ambiguos.** `areas(nombre)` desde `empleados` se lee correcto y no lo es: hay
>    **dos** relaciones entre esas tablas (`empleados.area_id` y `areas.responsable_id`), y
>    PostgREST no elige — responde `300 PGRST201`. Lo mismo entre `presupuesto_areas` y `areas`,
>    que tienen dos FKs. La solución es nombrar la constraint en el embed.
>
> **Por qué ningún test lo vio, que es lo que hay que llevarse:** el fake de Supabase de la
> suite implementa `select(*a, **k)` **ignorando el argumento**. Acepta cualquier spec, exista
> o no la columna. Peor: un test tenía la columna mal escrita **también en su fixture**, así
> que código y test coincidían en un nombre que la base no tiene y el test pasaba en verde.
>
> **Lo que cierra la clase, no el caso:** se agregó un test que ejecuta los 13 generadores
> contra un fake que **valida el spec contra `db/schema.sql`** — columnas y relaciones. Cada
> generador corre dos veces, con y sin filtro de área, porque el filtro cambia la query. Si
> mañana alguien escribe una columna que no existe, falla en la suite y no en producción.
>
> **Para la migración a AWS esto es directamente relevante:** el mismo agujero explica por qué
> el aprendizaje de PGRST201 ya estaba documentado y aun así volvió a aparecer siete veces. Al
> pasar a asyncpg los embeds de PostgREST desaparecen (pasan a ser JOINs explícitos), así que
> **las cinco queries de embed hay que reescribirlas igual**; las dos de nombre de columna se
> arreglan solas al escribir el SQL a mano, pero recién ahí — no antes.

> ⚠️ **Un dato de producción, por si te sirve para dimensionar:** la tabla `auditoria` tiene
> **133 eventos** (14/7 al 27/7), muy lejos del tope de 5.000 del export. `offboarding_instancias`
> está **vacía**, y por eso nadie notó que el reporte de rotación estaba caído.

## 2026-07-27 · El export avisa en vez de truncar en silencio · commits `<pendiente>` ×2

**Qué cambió:** los exports verifican cuántas filas devolvería la consulta **antes** de armar el
archivo. Si supera 5.000, devuelven un 422 con un mensaje que dice cuántas hay, cuál es el
máximo y que use los filtros — en vez de entregar un archivo cortado sin ninguna señal. El
número es una constante única (`services/_limite_export.py`) que reemplazó tres literales
`100000` sueltos y una constante local. En el front, el menú de exportar dejó de descartar el
error del backend y ahora muestra su mensaje.

**Impacto en infraestructura:** Ninguno.

*(Sin migraciones, sin variables de entorno, sin dependencias, sin buckets, sin endpoints nuevos
ni removidos, sin cambios en el modelo de auth. Un export dentro del tope se comporta
exactamente igual que antes.)*

> **🔴 DOS COSAS QUE ENCONTRÉ MIRANDO LOS TECHOS DE TIEMPO, y que te sirven aunque no sean de
> esta tanda:**
>
> 1. **`vercel.json` declara `maxDuration: 300` dentro de `builds[].config`**, que es el formato
>    legacy. En la config moderna `maxDuration` va en `functions`. **Muy probablemente esté
>    siendo ignorado** y rija el default del plan (10 s en Hobby, 60 s en Pro). Vale
>    verificarlo en el dashboard: si el timeout real es 10 s, hay más operaciones además del
>    export que pueden estar al límite.
> 2. **El techo efectivo de las queries son los 30 s del cliente Supabase**
>    (`settings.supabase_timeout`), no los 120 s del `statement_timeout` de Postgres. Y hay una
>    ambigüedad sin resolver: PostgREST se conecta como `authenticator`, que tiene
>    `statement_timeout=8s`, y `service_role` no define uno propio — si el que rige es el de la
>    sesión, el techo real son **8 s**. No se puede determinar leyendo catálogos; hace falta
>    medirlo contra el endpoint REST.
>
> Nada de esto bloquea el deploy: 5.000 filas está cómodo debajo de cualquiera de esos techos,
> así que el límite elegido no depende de cuál sea el verdadero.

---

## 2026-07-27 · Filtro por proyecto en cuatro módulos · commits `<pendiente>` ×2

**Qué cambió:** empleados, vacaciones, ausencias y evaluaciones pueden acotarse por proyecto —
"las filas de la gente asignada a ese proyecto". En vacaciones y ausencias el filtro se compone
por intersección con el ownership de `mandos_medios` y con el de área: `_ownership_filter` pasó
a resolver **tres** ejes. Antes se dividieron `empleado_repo.py` (174→98, el peor over-limit del
backend) y `routers/evaluaciones_resultados.py` (80→69), y `_area_scope.py` se renombró a
`_scope_filtros.py`.

**Impacto en infraestructura:** Ninguno.

*(Sin migraciones, sin variables de entorno, sin dependencias, sin buckets, sin cambios en el
modelo de auth ni en los claims del token. `proyecto_id` es un query param opcional más.)*

> **Un endpoint cambió de archivo, no de ruta.**
> `GET /api/evaluaciones/resultados/lotes/{lote_id}/evaluados/export` se mudó a
> `routers/evaluaciones_resultados_export.py`, con la misma ruta y el mismo comportamiento. Al
> mudarlo **recibió la franja de rate limiting que le faltaba desde A2** (30/hora compartida con
> el resto de los exports): si alguien tenía una regla de borde asumiendo que ese export no
> estaba limitado, ahora lo está.

> **Nota de consultas, no acción:** el filtro agrega **una query batch** a
> `proyecto_asignaciones` por request que lo use — no escala con la cantidad de filas del módulo
> filtrado. Cuando haya volumen, la columna candidata a índice es
> `proyecto_asignaciones.proyecto_id`.

> **Sobre los tests, para que no se lea mal:** 5 tests existentes cambiaron **el target de un
> monkeypatch y de un import** al dividirse `empleado_repo.py` — estaban acoplados a símbolos
> privados (`_row`, el `supabase_admin` del módulo) que el corte movió. **Ningún assert, valor
> esperado ni caso cambió**, y el comportamiento del código es idéntico. El refactor fue puro;
> lo que se corrigió es un acoplamiento del test a internals.

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

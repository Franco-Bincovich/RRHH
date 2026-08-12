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
## 2026-08-12 · Fase 0.9 · Las 4 fugas de acceso a datos se mueven a `repositories/` · commit pendiente

**Qué cambió:** cierre de Fase 0. De las 62 llamadas a la base que vivían fuera de
`repositories/`, **se movieron 4**, se **declararon 58** con un barrido nuevo, y se escribió
`docs/handoff-aws/ACCESO-A-DATOS.md`, que es la entrega de la sesión para el dev de infra.

### Los dos repos destino estaban los DOS en 99/100

`usuario_repo.py` **99/100** y `nomina_repo.py` **99/100**: ninguno admitía un método más. Hubo
que dividir los dos ANTES de mover nada:

- **`_usuario_lookup_repo.py` (61 líneas)** — los cuatro lookups de UNA fila. El corte es por
  FORMA de la consulta, no por tamaño: acá viven las que devuelven una fila o `None`; las
  escrituras, los chequeos de unicidad (que devuelven bool) y el listado se quedaron.
  `usuario_repo` bajó a **98**.
- **`_nomina_evolucion.py` (53 líneas)** — la evolución de 12 meses, que es el único bloque del
  repo que no devuelve filas de nómina sino una serie agregada, y se lleva su helper
  `_prev_period`. `nomina_repo` bajó a **80**.

Molde de los dos: `empleado_repo.py` — funciones libres en el satélite y delegadores de una línea
que sostienen la interfaz pública. **Ningún caller de producción cambió.**

### Cuáles de las 3 fugas de `users` necesitaron método nuevo

| Fuga | Resolución |
|---|---|
| `objetivo_service.py:138` | ✅ **`get_estado` ya existía** (caché del middleware). Trae `rol` y `ultimo_acceso` de más; **no se le recortaron columnas** — eso tocaría a su otro caller |
| `objetivos_import_preview.py:36` | ✅ **`listar_activos` ya existía** (listado + export). Trae `rol` de más y viene ordenado por apellido; el índice que arma el preview es por email/username/nombre, no por posición |
| `auth_service.py:37` | 🆕 **`find_by_username`**, el único que faltaba. La búsqueda por `ilike` sin comodines no tenía método |
| `nomina_csv_service.py:18` | 🆕 **`periodos_cargados`** en `nomina_repo` |

**Dos de cuatro se resolvieron reusando lo que había**, y eso se ve en el conteo: la suite bajó
de 3256 a 3254 porque `test_selects_repos` parametriza por `select` descubierto, y dos queries
dejaron de existir en vez de mudarse. El total de llamadas a la base bajó de **388 a 386** sin
perder una sola consulta.

⚠️ **Un cambio de forma, declarado:** `_validate_responsable` pasó de `maybe_single()` (devuelve
dict) a `limit(1)` (devuelve lista), porque es la forma que `usuario_repo` ya usaba en sus otros
tres lookups. El comportamiento observable es idéntico (fila o nada → mismos 422), pero el fake
del test tuvo que seguir la forma.

⚠️ **`objetivo_service` NO bajó de líneas: 142 → 142.** El pedido era que bajara, y no podía: la
query que salió **era una sola línea**, así que reemplazarla por la llamada al repo es neutro.
`auth_service` sí bajó, 134 → **125**, porque ahí salieron 9 líneas de `try/except` alrededor de
un `.single()`.

### El barrido — 4 familias, no 23 archivos

**`tests/test_acceso_a_datos.py` (6 tests).** Recorre por AST `services`, `routers`, `utils`,
`middleware`, `scripts`, `config` y `schemas`, y rojea ante cualquier `.table()`/`.rpc()` que no
caiga en una familia declarada.

🔑 **Las excepciones son por FAMILIA y la clave es un substring del path, no un archivo.**
Declarar los 19 archivos uno por uno daría la lista que nadie mira (K2, K7). Son **4** —
`reporte`, `dashboard`, `organigrama`, `procesos`— cada una con su motivo escrito, y **hay un
test que impide que pasen de 5**: si hacen falta seis, el problema no es la lista, es que la
regla dejó de valer. Un archivo nuevo de reportes entra solo, sin tocar el barrido.

Por AST y no por texto: varios docstrings nombran tablas y un grep los marcaría. Guarda de
mínimo (≥250 archivos descubiertos) y contracara (`repositories/` **tiene** que seguir
consultando, ≥60 archivos) para que no pase en verde sobre un conjunto vacío.

**Mutación:** una query nueva en `vacante_service` (familia no declarada) → **1 test en rojo**,
nombrando `services/vacante_service.py:27`. El barrido también se cazó a sí mismo mientras se
escribía: uno de los motivos decía "ídem" y el test de "toda familia tiene motivo escrito" lo
rechazó.

### 🔴 ACCIONES DE INFRAESTRUCTURA — `docs/handoff-aws/ACCESO-A-DATOS.md`

- **El número:** 386 llamadas, **328 en `repositories/`** (85%), **58 afuera** en 19 archivos de
  `services/`, todas inventariadas con archivo:línea.
- 🔴 **Los DOS catálogos de tabla dinámica**, que son lo que un porteo por búsqueda y reemplazo
  **no ve**: `procesos_service._META` (el que produjo el **500 del Panel de Procesos** cuando
  J5a borró las `ev_*` — la pantalla muere entera, no degrada una tarjeta) y
  `_dashboard_alertas_catalogo.BLOQUEOS`. Con la regla que sale de ahí: antes de renombrar o
  dropear una tabla, grepearla en esos dos archivos.
- **`.rpc()` es CERO en todo el backend**: no hay lógica de Postgres invocada desde la app.
- **Supabase Auth es superficie aparte** (`_usuario_alta.py`, `usuario_service.py`) y **no entra
  en las 386**; su reemplazo ya está en las migraciones 075/076 de `migracionAWS/`.
- **Los 5 helpers de `repositories/` con `table` por parámetro SÍ se resuelven** leyendo el
  caller: no son el caso difícil.
- 🔴 **Sección de estado, para que no planifique sobre algo que puede cambiar:** las 48 de
  reportes y dashboard quedan como **CANDIDATAS** a moverse si el trabajo de features termina
  antes del **6/9**. Si a esa fecha siguen donde están, se quedan y son suyas. **Después del 6 no
  se toca nada**: moverle el piso mientras portea es peor que dejarlas.
- **Migraciones / env vars / dependencias / buckets / endpoints / auth / dominios:** ninguno.

**Verificación:** `pytest -q` → **3260 passed** (3254 tras mover las fugas + los 6 del barrido) ·
los 14 barridos + el nuevo verdes (494 tests) · **encoding limpio: 0 BOM y 0 caracteres de
reemplazo** en todos los archivos tocados, revisado con `git diff` (es la segunda vez en dos días
que el encoding de Windows muerde el repo; esta vez se usó solo la herramienta de edición).

---
## 2026-08-12 · Fase 0.7 · Storage pasa a tener un punto de contacto ÚNICO · commit pendiente

**Qué cambió:** nace **`backend/integrations/storage.py`** (94 líneas) y los **7** services que
hablaban con Storage dejan de nombrar buckets y de llamar al SDK. Es la recomendación #2 de las
tres migraciones anteriores: un wrapper simétrico, para que el código de negocio no se toque el
día del cutover a S3.

> ⚠️ **Eran SIETE, no seis.** El inventario traía 6 services con la constante hardcodeada; el
> séptimo —`_adjuntos_masivo.py`— no nombraba ningún bucket **porque lo lee de la fila**
> (`adj.bucket`), pero llamaba al SDK igual. Es la fuga que un inventario por constante no ve, y
> es justo el caso que más condiciona el diseño.

**Dónde se cortó y por qué ahí:** en `integrations/`, no en `services/`. Es la convención del repo
(`integrations/` son los wrappers de servicios externos) y el archivo **no tiene una línea de
negocio**: no valida, no arma paths, no audita. El contraejemplo aparente es `services/mailer/`,
que también es punto de salida único y también habla con un proveedor externo, pero **ownea**
plantillas, render y variables y apenas contiene un `_gmail.py` privado. Acá no hay nada que
ownear: son cuatro llamadas. Y el desempate práctico: el día del cutover, el archivo que cambia de
proveedor conviene que esté al lado del otro que cambia por lo mismo (`supabase_client.py`).

**La API es neutral al proveedor a propósito** — afuera no se ve `from_()`, ni `file_options`, ni
la clave `signedURL` del dict de Supabase: `subir` · `url_firmada` · `url_publica` · `borrar`, más
`DOCUMENTOS` / `CVS` / `AVATARS`.

🔴 **`bucket` se recibe como `str` y no como Enum, por la base.** `adjuntos.bucket` es una COLUMNA
con `DEFAULT 'documentos'`: el nombre está grabado en filas de producción. Dos caminos leen el
bucket DE LA FILA —la descarga de un adjunto y el borrado masivo—, así que el módulo tiene que
poder operar sobre un valor que llega de la base. Un Enum movería el fallo de "el proveedor
rechaza" a "la conversión revienta": otro error, en otro lugar, y esta sesión no cambia
comportamiento.

**¿Hacían lo mismo de formas distintas?** Casi no, y la única diferencia real **no se unificó**:
`cv_service` es el único de los cuatro uploads que puede recibir el `content_type` vacío (el
archivo llega de un mail) y resuelve su default con `or "application/octet-stream"`. Ese default se
quedó **en el call site**, no se subió al módulo: es una regla de ese flujo. Los dos borrados
tienen su propio `try/except` con log —"si Storage falla, seguí igual y dejá el objeto huérfano"—
y también se quedaron en los services: es decisión de negocio, y traerla al módulo unificaría dos
criterios que hoy coinciden por casualidad, no por diseño.

**Tests:** `tests/test_storage_punto_unico.py` (143 líneas, 5 tests) recorre `services/` y
`repositories/` **por AST** y rojea si alguien vuelve a nombrar un bucket o a llamar al SDK.
🔑 **Por AST y no por texto**: varios docstrings dicen "bucket privado 'documentos'" —prosa
correcta— y un grep los marcaría, con lo que el barrido nacería con falsos positivos y se apagaría.
Hay un quinto test que fija justamente eso: que la prosa NO cuenta, para que nadie "arregle" un
falso positivo borrando documentación. Lleva guarda de mínimo (≥150 archivos descubiertos), por lo
de `barridoFront` en Windows.

**Los tests existentes NO se reescribieron.** Los de adjuntos y logo necesitaron **una línea cada
uno**: el monkeypatch alcanzaba el SDK como `<service>.supabase_admin`, y ese nombre ya no existe
en el service. Se retargetearon a `<service>.storage.supabase_admin` —sin agregar imports, sin
tocar los fakes ni una sola aserción—, aprovechando que `supabase_admin` es el MISMO objeto y
parchear su atributo `.storage` sigue siendo global.

**Mutaciones, verificadas:** que `cv_service` vuelva a escribir `"cvs"` a mano → **1 test en rojo**
(`test_ningun_service_ni_repo_nombra_un_bucket`, nombrando archivo y bucket). Que el módulo apunte
a un bucket equivocado (`CVS = "cvs-equivocado"`) → **1 test en rojo, y es el estructural, no uno
funcional**.

> 🔴 **Ese segundo resultado es un HALLAZGO, no un aprobado:** ningún test funcional afirma el
> NOMBRE del bucket. Los fakes de adjuntos y logo reciben el bucket en `from_()` y lo descartan sin
> mirarlo, así que un bucket equivocado los deja verdes. Queda anotado en `STORAGE.md`: **un typo
> en un nombre de bucket de S3 no lo va a detener un test funcional.** No se tocaron esos tests
> (la consigna era no modificarlos); cerrarlo es una tanda propia.

**Impacto en infraestructura:**

- 📌 **Se escribió `docs/handoff-aws/STORAGE.md`**, que es la entrega de esta sesión para el dev de
  infra: los 3 buckets con qué guarda cada uno, su acceso y sus paths; **qué archivo toca y cuáles
  NO** el día del cutover; y las cinco cosas que hay que saber antes de portar.
- 🔴 **`avatars` es el ÚNICO bucket público**, y su URL se **persiste** en `empresas.logo_url`. Si
  el dominio del bucket cambia en AWS, esas filas quedan apuntando al viejo. Los otros dos guardan
  solo la key y firman en cada request: no tienen ese problema.
- 🔴 **Si en AWS se renombran los buckets, hay que migrar `adjuntos.bucket`** o mapear los nombres
  viejos dentro del módulo.
- **El E2E de adjuntos sigue sin ejecutarse nunca** (apunta al bucket de producción). El cutover es
  el momento de escribirlo contra un bucket de prueba.
- **Migraciones / env vars / dependencias / endpoints / auth / dominios:** ninguno. El
  comportamiento no cambió: mismos buckets, mismos paths, mismo manejo de errores.

**Verificación:** `pytest -q` → **3256 passed** (3251 + los 5 nuevos) · los 13 barridos + el nuevo
verdes (490 tests) · `npm test` **647/647** y `tsc --noEmit` exit 0 — el front no se tocó.

> ⚠️ **Nota de método, porque casi cuesta caro:** el reemplazo de imports se hizo primero con un
> `Get-Content`/`Set-Content` masivo de PowerShell y **corrompió el encoding de los 6 archivos**
> (PS 5.1 lee UTF-8 sin BOM como cp1252 y reescribe con BOM: cada `ó` quedó `Ã³`). Se detectó en el
> `git diff` —que mostraba cambios en líneas que nadie tocó— y se revirtió byte a byte
> reinterpretando cp1252→UTF-8. **Para editar código con acentos en Windows, usar la herramienta de
> edición, no `Set-Content`.**

---
## 2026-08-12 · Fase 0.6 · Los 5 ids de entrada pasan de `str` a `UUID` + la 109 ya corrió · commit pendiente

**Qué cambió:** los cinco schemas de ENTRADA que declaraban un id como `str` ahora lo declaran
`UUID`. Es preparación del porteo a asyncpg —con el SDK de Supabase el id viaja como string y el
tipo no molesta; con asyncpg vuelve como objeto y un schema que dice `str` explota— y de paso
mueve la validación a la frontera: un id vacío o mal formado sale **422** en vez del **500** que
daba Postgres con `22P02`. Es el mismo bug que ya nos costó un 500 en producción con
`AreaCreate.empresa_id`.

| Schema | Endpoint | Qué hubo que tocar en el camino |
|---|---|---|
| `NominaCreate.empleado_id` | `POST /api/costos/nomina` | **`str()` en DOS lugares** de `nomina_repo.save_nomina`: el `.eq()` del lookup y el payload del upsert |
| `FilaNominaPreview.empleado_id` | `POST /api/importacion/nomina/confirmar` | **`str()`** en el armado de filas de `nomina_import_service` |
| `ImportacionNominaConfirmarRequest.empresa_id` | idem | **`str()`** ídem, y explícito hacia el payload de auditoría |
| `FilaObjetivoPreview.responsable_id` | `POST /api/importacion/objetivos/confirmar` | 🔴 **SACAR** la conversión: `_a_create` hacía `UUID(...)` y `UUID(objeto_uuid)` levanta TypeError |
| `ImportacionObjetivosConfirmarRequest.empresa_id` | idem | 🔴 ídem, más `str()` explícito hacia el payload de auditoría |

🔑 **La lección del rastreo: el resultado fue OPUESTO en los dos imports.** En el de nómina
faltaba una conversión; en el de objetivos SOBRABA. Aplicar una regla fija ("tipar UUID ⇒ agregar
`str()`") habría roto el confirmar de objetivos entero. Hay que seguir el camino hasta PostgREST y
**ejecutarlo**, no leerlo: `objetivo_repo.save` ya convertía campo por campo desde antes —el falso
positivo conocido— y no necesitaba nada.

**Lo que NO se tocó, con razón:** `responsables_ids: List[str]` en el mismo schema de objetivos.
Tiene el mismo problema de fondo y su `UUID(u)` sigue vivo y funcionando, pero **no entró en el
inventario de los cinco** y cambiarlo pide el mismo rastreo completo. Queda anotado en el schema,
no hecho a medias.

**Tests:** `tests/test_ids_tipados_uuid.py` (433 líneas, **17 tests**). Todos entran **por HTTP
contra el app real** —no instancian los schemas a mano, que es el error que dejó pasar el bug de
clientes— y cada campo tiene su caso positivo (el valor llega entero al otro lado) y sus dos
negativos (`""` y `"no-es-un-uuid"` → 422, nunca 500). La serialización, que ningún test de HTTP
toca porque el doble del service corta antes del repo, se cubre llamando a los **repos y services
REALES** con un doble de `supabase_admin` que hace `json.dumps` en el punto donde el payload sale
hacia PostgREST. Molde: `test_area_empresa_tipada.py`.

> 🔴 **Un detalle que cambia si el test sirve o no:** el confirmar de objetivos atrapa toda
> excepción por fila y la devuelve como error de esa fila, así que **con el bug vivo respondía 200
> igual**. Un test que mirara solo el status pasaba. Por eso se afirma `importados == 1` y
> `errores == []`.

**Mutaciones, verificadas:** volver `FilaNominaPreview.empleado_id` a `str` → **4 tests en rojo**;
sacar el `str()` del armado de filas del import → **1 test en rojo**, con
`TypeError: Object of type UUID is not JSON serializable`.

**18 tests existentes hubo que actualizar** (fixtures con ids inventados tipo `"emp-1"` y `"e9"`,
que el schema ahora rechaza). No es daño colateral: es la señal de que el contrato se apretó.

### ✅ La 109 ya corrió — corregido en los tres lugares

Franco la corrió. Verificado en el catálogo: `clientes` **sin** `empresa_id`, 2 índices
(`clientes_pkey` y `ux_clientes_nombre_global`), **0 FKs salientes**, y los 4 clientes con su hora
imputada intactos. `db/schema.sql` volvió a **"AL DÍA"** y el párrafo de "va por delante" se borró,
que es la regla que el propio archivo declara. Actualizados también `CLAUDE.md`, `DEPLOY.md` y
`docs/handoff-aws/README.md`. **No quedan migraciones pendientes: 080, 089 y 102–112 corridas.**

> 🔴 **Es la TERCERA vez que ese encabezado queda desfasado**, y las tres están ahora escritas ahí
> como justificación de la regla: (1) decía "va por delante" con las migraciones ya corridas;
> (2) lo mismo con la 112, cuatro días después; (3) al arreglar (2) se marcó "AL DÍA" verificando
> **solo el conteo de tablas**, y la 109 no crea ni borra tablas, así que era invisible. La regla
> —tocarlo en la MISMA sesión que la migración, al escribirla y al correrla— ya está anotada como
> tal, con los tres casos.

**Impacto en infraestructura:**

- **Ninguno inmediato.** Cero migraciones, variables, endpoints, buckets, dependencias o cambios
  de auth. El contrato de red **no cambia**: JSON lleva los ids como string en las dos direcciones,
  y el front reenvía las filas del preview tal cual las recibió (verificado en
  `ImportarNominaCSVModal` e `ImportarObjetivosModal`: pasan `preview.filas_validas` sin tocar).
  Por eso no hubo que tocar una línea del front ni de sus tipos.
- 📌 **Para el porteo:** estos cinco eran deuda de porteo, no deuda menor. Quedan **0** ids de
  entrada tipados `str`. Los ~37 que el grep de control sigue mostrando son de **salida**
  (`*Response`, que se arman desde el row ya serializado y no entran en ninguna query) o **ids
  externos** (`message_id`, `email_id`, `post_id` de Gmail/LinkedIn, que **no son UUID y tienen que
  seguir siendo `str`**).
- ⚠️ `repositories/nomina_repo.py` quedó en **99/100**. Estaba en 98 y el comentario del cambio lo
  llevó a 106; se condensó a una línea al lado del código en vez de un bloque. **El próximo cambio
  en ese archivo exige dividirlo primero.**

**Verificación:** `pytest -q` → **3251 passed** (3234 + los 17 nuevos) · los 13 barridos verdes
(485 tests en los 10 de backend) · `npm test` **647/647** y `tsc --noEmit` exit 0 — el front no se
tocó, se corrieron para confirmarlo.

---
## 2026-08-12 · Fase 0.5 · Los cuatro artefactos de reconstrucción + **la 109 estaba pendiente y nadie lo sabía** · commit pendiente

**Qué cambió:** el repo queda con los cuatro archivos con los que se levanta RDS desde cero.
**`db/funciones_y_triggers.sql`** (165 líneas) y **`db/seed.sql`** (120) son nuevos; `db/schema.sql`
y `docs/handoff-aws/README.md` se tocaron. Los dos nuevos salieron del **catálogo vivo**, no de
`migrations/`.

### 🔴 LO MÁS IMPORTANTE NO ESTABA EN EL PLAN: LA MIGRACIÓN 109 NO ESTÁ CORRIDA

Apareció al derivar qué tablas necesitan trigger: `clientes` seguía apareciendo con `empresa_id`.
Verificado objeto por objeto contra el catálogo: **producción todavía tiene `clientes.empresa_id`,
su FK `clientes_empresa_id_fkey`, el índice `idx_clientes_empresa` y el índice único viejo
`ux_clientes_nombre_por_empresa`** — los cuatro objetos que la 109 dropea. Y 3 de los 4 clientes
cargados tienen `empresa_id` no nulo.

**Correrla es seguro y hay que hacerlo:** la 108 (que sí corrió) ya dejó puesta la unicidad global
`ux_clientes_nombre_global`, así que en ningún momento la tabla queda sin unicidad de nombre; y por
diseño la 109 iba después de que el código del bloque L estuviera en producción, y lo está desde
`bca5de6`. **Un rebuild desde `schema.sql` ya sale en el estado post-109** (el archivo declara la
tabla sin la columna): la que está atrás es producción, no el artefacto.

> ⚠️ **Cómo se coló, que es la parte que sirve:** el 11/8 este documento y `CLAUDE.md` dijeron
> "108–112 todas corridas" habiendo verificado **solo el conteo de tablas** (52 = 52). La 109 no
> crea ni borra tablas —borra una columna y tres objetos—, así que era **invisible a esa
> comprobación**. Contar tablas no alcanza para afirmar que un archivo refleja producción: hay que
> mirar el objeto que la migración toca. Corregido en `schema.sql`, `CLAUDE.md` y `DEPLOY.md`.

### Los cuatro artefactos

1. **`db/schema.sql`** — se sacó la FK `users.id → auth.users(id) ON DELETE CASCADE` y `users.id`
   quedó con `DEFAULT gen_random_uuid()`.
2. **`db/funciones_y_triggers.sql` (NUEVO)** — `fn_misma_empresa()` + los **8** triggers
   `trg_emp_*`, leídos del catálogo con `pg_get_functiondef`/`pg_get_triggerdef`.
3. **`077_recrear_triggers_updated_at.sql`** — sin cambios, ya estaba en `migracionAWS/`.
4. **`db/seed.sql` (NUEVO)** — `tipos_ausencia` (5), `parametros_empresa` (1 fila global),
   `reglas_vacaciones_escala` (3 tramos). **Sin `empresas`, `users` ni `plantillas_mail`**: eso es
   dato de negocio y viaja en el dump.

### 🔴 ACCIONES DE INFRAESTRUCTURA

- **La secuencia de reconstrucción, con la invocación exacta, está en
  `docs/handoff-aws/README.md`.** Los cuatro con `psql -v ON_ERROR_STOP=1 -f`, en orden
  `schema → funciones_y_triggers → 077 → seed`, los cuatro con exit 0. `ON_ERROR_STOP=1` **no es
  opcional**: sin él psql sigue tras un error y termina en 0 igual, así que un replay a medias se
  lee como exitoso. Los triggers van **antes** del seed a propósito.
- 🔴 **`backend/migrations/094_recrear_triggers_empresa.sql` NO se usa en el rebuild y quedó
  declarado como historia.** Declara 9 triggers; el noveno es `trg_emp_sucesion` sobre
  `sucesion_posiciones`, tabla que dropeó la 112 — y aborta el script, porque
  `DROP TRIGGER IF EXISTS x ON tabla` falla igual cuando la que no existe es la **tabla**. Misma
  mina que J5a desactivó en la 077. **No se tocó la 094**: es una migración.
- 🔴 **Correr la 109 en producción** (ver arriba).
- **`schema.sql` no refleja producción en un punto más, a propósito:** la FK a `auth.users`. **Esto
  no toca Supabase y no hay que correr nada allá** — el archivo describe la base destino. En
  producción la FK sigue y se queda. Verificado en el código
  (`services/_usuario_alta.py:74-90`): hoy el id lo genera **Supabase Auth** y la app lo pasa
  explícito en el INSERT, así que el `DEFAULT` **no cambia nada del comportamiento actual**; solo
  habilita el INSERT sin `id`, que es lo que hace falta del otro lado. **Lo que sí hay que reponer
  en la app del destino es el `ON DELETE CASCADE`**: el alta tiene un rollback (`_rollback_auth`)
  que hoy se apoya en él para no dejar el perfil huérfano.
- 🟠 **Conflicto conocido, sin resolver, anotado en el archivo de triggers:** `trg_emp_empleados`
  vigila `manager_id` y **exige que el superior sea de la misma empresa**, mientras que la decisión
  de producto del 2/8 permite superior cruzado entre empresas — y sobre esa premisa están
  `services/_alcance_mandos.py` y el import de nómina de la migración **086, titulada justamente
  "superior cruzado entre empresas"**. Hoy no explotó porque hay **0 empleados con manager de otra
  empresa** (verificado). El día que se cargue el primero, el UPDATE falla con "Cruce de empresa en
  empleados.manager_id". La 086 no menciona el trigger: el choque nunca se discutió. **Se reprodujo
  tal cual está en producción** —el artefacto refleja, no decide— pero hay que resolverlo antes del
  cutover.
- **Migraciones nuevas / variables de entorno / dependencias / buckets / endpoints / auth de la
  app / dominios:** ninguno.

### Lo que el seed documenta y no se puede regenerar a la ligera

🔴 **Los UUID de `tipos_ausencia` van FIJOS.** `services/_carga_licencia.py:51` tiene hardcodeado
`TIPO_LICENCIA_ID = '9f3b7c2a-1d4e-4a6b-8c5d-0e1f2a3b4c5d'` (lo sembró la migración 107). Un seed
con `gen_random_uuid()` rompe la carga de licencias del link público **con violación de FK, en
producción y no en los tests** —el fake no tiene FKs—, y además deja sin resolver los `tipo_id` de
cualquier dump de `solicitudes_ausencia` que se restaure después.

El "qué se rompe sin cada catálogo" se verificó en el código, no se supuso: **sin `tipos_ausencia`
no se puede crear NINGUNA ausencia** (`solicitudes_ausencia.tipo_id` es NOT NULL con FK) · **sin la
fila global de `parametros_empresa`** el service levanta `CONFIG_GLOBAL_FALTANTE` (500) y con eso
cae el reporte de ausentismo y la pantalla de Configuración, mientras el KPI del dashboard degrada
solo esa card por el `_safe` · **sin `reglas_vacaciones_escala`**, hoy, **ningún cálculo se rompe**
(el propio service dice que la escala "se persiste y se muestra, y nada la aplica todavía"): lo que
queda vacío es la pantalla de Configuración.

**Verificación:** `pytest -q` → **3234 passed**, sin cambios · los barridos que leen `schema.sql`
(392 tests) verdes · **el replay contra un Postgres limpio NO se corrió**: hay PostgreSQL 16
instalado y corriendo en la Lenovo, pero `pg_hba.conf` exige `scram-sha-256` y la contraseña no
está en el repo. Es la verificación de Fase 3 (J1). Script listo para correrlo en un comando.

---
## 2026-08-12 · El encabezado de `schema.sql` deja de mentir + el barrido del front deja de ser ciego en Windows · commit pendiente

**Qué cambió:** dos fixes que salieron de la auditoría de documentación de la sesión anterior, más
la entrada faltante del bloque D (arriba, fechada 7/8 en su lugar cronológico).

1. 🔴 **`backend/db/schema.sql` — el encabezado afirmaba que producción tenía 63 tablas** y que el
   archivo "iba por delante" hasta que se corriera la 112. **La 112 corrió el 11/8**: producción
   tiene 52, verificado contra el catálogo. El propio archivo dejaba la instrucción de volver el
   párrafo a "AL DÍA" al correrla, y no se había hecho. Se reescribió el bloque de estado, se
   actualizaron las dos referencias a `001..093` (ahora `001..112`) y se marcó como histórica la
   verificación del 7/8 (58 tablas / 153 FKs / 151 índices), que describía el archivo de antes de
   las migraciones 108–112.
   **Por qué importa más que un número:** es el artefacto del que el dev de infra levanta RDS. Un
   encabezado que miente sobre si el archivo **adelanta** o **refleja** manda a buscar un drift que
   no existe, o hace confiar en una tabla que todavía no está. Ya había mentido en las dos
   direcciones, así que el aprendizaje del archivo se amplió con la regla práctica: **el bloque se
   toca en la misma sesión que la migración, las dos veces — al escribirla y al correrla.**
2. **`frontend/services/barridoFront.test.ts` — descubría CERO exports en Windows.** Armaba los
   paths con `path.join` (separador `\`) y después filtraba con `p.includes("/services/")` y
   `p.split("/")`, que nunca matcheaban. Resultado: `SERVICES` vacío, `EXPORTS` vacío, y **tres
   tests en rojo en la Lenovo y verdes en la Mac**, sin que hubiera cambiado una línea del código
   auditado. Se normaliza el separador **en el único lugar donde nacen los paths** (`archivosDe`),
   no en cada comparación: arreglarlo en los dos consumidores dejaría al tercero naciendo con el
   bug.

**Lo que hay que leer de esto, más allá del fix:** el barrido no falló, **falló ruidosamente**.
Las guardas de mínimo (`expected 0 to be >= 200`) hicieron exactamente su trabajo: sin ellas el
test habría informado *"ningún export huérfano"* sobre un conjunto vacío, en verde, para siempre.
Es el caso #5 de la regla del repo con otra cara — la aserción no era vacua por una clave
inexistente, sino por un **conjunto vacío que dependía de la plataforma**.

**Barrido del patrón, antes de tocar nada** (regla del dev de infra: arreglar uno y olvidar
cuatro). Se buscó `path.join` + comparación contra un `/` literal en todo el repo:
**un solo archivo lo tenía**, con dos líneas afectadas (148 y 151). Los otros tres tests del front
que recorren el árbol (`pageSize`, `loadingSeApaga`, `contrasteTokens`) filtran por **nombre de
archivo** (`e.name`), nunca por un tramo del path, y usan el path solo para leer — inmunes. Los
barridos del backend usan `Path.parts`, `.stem`, `.name` y `.as_posix()`, que son
separador-agnósticos **por diseño**; los `"/"` que aparecen ahí son paths de URL de FastAPI, no del
sistema de archivos.

**Verificación de que el fix es completo y no parcial:** después de normalizar, el barrido
descubre en Windows **450 archivos y 50 services**, que es **exactamente** la cantidad de `.ts`/
`.tsx` que git tiene trackeados bajo `app|components|hooks|services` (450) y de no-test bajo
`services/` (50). O sea: ve el árbol entero, no un subconjunto. Los 264 exports contra los 263
anotados en el propio test (medidos en la Mac el 10/8) y los 450 contra 438 archivos son **deriva
del repo, no diferencia de plataforma**: en el commit que estrenó el barrido había 439 archivos
trackeados y hoy hay 450.

> ⚠️ **Dato suelto, no bloqueante:** el comentario del test dice que las guardas se fijaron "~25%
> por debajo del valor real (263 exports, 438 archivos, **792 imports**)", pero `totalImports`
> —la variable que la guarda mide— da **2710**. El 792 parece ser el tamaño del `Set` de pares
> únicos, que es otra cosa. La guarda de imports (`>= 600`) es entonces mucho más floja de lo que
> su propio criterio declara. No se tocó: subirla es una decisión, no una corrección.

**Impacto en infraestructura:**

- 🔴 **`db/schema.sql` cambió, pero SOLO en comentarios de encabezado.** Cero DDL tocado: ni una
  tabla, columna, constraint ni índice. Un rebuild produce exactamente lo mismo que antes. Se
  verificó con los tres barridos que leen el archivo (`_postgrest_schema`, `test_selects_repos`,
  `test_triggers_updated_at`), todos verdes.
- **La 094 sigue pendiente de corrección** — ver la entrada del 7/8. Es lo único de estas dos
  sesiones que le bloquea trabajo al dev de infra.
- **Migraciones / variables de entorno / dependencias / buckets / endpoints / auth / dominios:**
  ninguno. El cambio del front es un archivo de test.

**Verificación:** `pytest -q` → **3234 passed** (idéntico antes y después) · `npm test` → **647/647
en 53 archivos, en Windows** (era 644/647) · `tsc --noEmit` exit 0.

---
## 2026-08-12 · Ordenamiento de la documentación del handoff + auditoría de lo que ya no era cierto · commit pendiente

**Qué cambió:** se creó **`docs/handoff-aws/`** y se movieron ahí los cinco archivos que estaban
sueltos en la raíz del repo: `COMPARATIVA_VERCEL_SUPABASE_VS_AWS.md`, `PATRONES_CODIGO_AWS.md`,
el README del dev de infra (→ `README-DEV.md`) y `README-handoff-aws.md` (→ `README.md`).
`PLAN-6-SEPTIEMBRE.md` fue a `docs/`. En la raíz quedan solo `CLAUDE.md` y `AUDITORIA_FUNCIONAL.md`.
Después se auditó **cada documento de `docs/` y `CLAUDE.md`** contra el código y el catálogo vivo.

🔴 **EL HALLAZGO DE FONDO NO FUE UN NÚMERO: `CLAUDE.md` apuntaba al plan equivocado.** Declaraba
como vigente a `docs/Plan de trabajo` (v2, **27/7**), cuando hay **cinco** documentos de plan y ése
es el tercero más viejo: `PLAN-DE-TRABAJO.md` (5/8) dice en su encabezado que lo supersede, y
`PLAN-6-SEPTIEMBRE.md` (12/8) es el que tiene la fecha de entrega comprometida. **Cualquier agente
—o persona— que arrancara leyendo `CLAUDE.md`, que es lo que ese archivo pide, trabajaba contra un
plan de hace dos semanas.** Se escribió la jerarquía de los cinco, numerada, en un solo lugar, con
la regla de que un plan nuevo actualiza esa lista en la misma sesión. Ninguno se borró: cada uno es
el registro de una etapa.

**Las afirmaciones falsas corregidas** (~20, todas verificadas contra el código o el catálogo):
suite 3280→**3234** y 153→**157** archivos · 69→**66** routers y 247→**225** rutas · 197→**192**
services y 87→**82** repos · 58→**52** tablas · migraciones "hasta la 107, 105 archivos" → **hasta
la 112, 110** · `Seccion` 26→**28** valores y 190→**204** gates en 61 routers · 27→**26** exports ·
el barrido de límite de export decía barrer 11 services y son **18** · triggers "van a bajar cuando
corra J5b" → **ya corrió**: 43 = 35 + 8 · 33→**28** archivos de front sobre 150.

**Y cuatro que no eran conteos, que son las que más costaban:** `ev_*` descrito como *"los 3
routers están MONTADOS, borrarlos rompe endpoints publicados"* cuando el módulo se borró entero el
11/8 · las 6 tablas huérfanas descritas como *"se limpian después del cutover"* cuando ya se
dropearon · `_costos_write.py` marcado como violación activa de Vista vs Acción cuando está
arreglado desde el 6/8 · el import de costos marcado como *"no audita nada"* en un archivo que 400
líneas más abajo lo listaba como resuelto.

**Documentos tocados:** `CLAUDE.md`, `docs/README.md` (además: `pyproject.toml` que ya no existe,
`RESEND_API_KEY` como obligatoria contradiciendo su propio aviso, un `.venv` descrito como
commiteado que `git ls-files` no conoce, y el índice al que le faltaban cinco documentos),
`DEPLOY.md`, `DEUDA-TECNICA.md`, `ORDEN-SESIONES-CODIGO.md`, `MATRIZ-FILTROS.md`,
`ESTADO-VS-COMPROMISO.md`. **Las entradas históricas de esta bitácora NO se reescribieron**: una
entrada que decía "doce barridos verdes" era cierta el día que se escribió.

**Impacto en infraestructura:**

- **Ninguno en el sistema.** Cero código, cero migraciones, cero variables, cero endpoints.
- 📌 **Para el dev de infra, dos cosas útiles:** su material vive ahora en **`docs/handoff-aws/`**,
  y `docs/README.md` (el índice) y `DEPLOY.md` ya no le dan números de tablas, migraciones ni
  triggers que estaban vencidos. **`DEPLOY.md` es el documento por el que tiene que empezar.**
- **Su material es CONTEXTO, no instrucciones.** Queda escrito en `CLAUDE.md` y en el README de la
  carpeta: el checklist de 50 ítems no se ejecuta y no se hace refactor preventivo hacia sus
  patrones. El código existente del proyecto manda.

**Verificación:** ningún test lee `docs/` (verificado sobre las 157 suites de backend y las 53 del
front), así que los movimientos no rompen nada · `pytest -q` → **3234 passed**, idéntico.

---
## 2026-08-12 · `pip install` roto en Windows: los `requirements*.txt` pasan a ASCII puro · commit pendiente

**Qué cambió:** en la Lenovo, `pip install -r requirements.txt` **abortaba entero** con
`UnicodeDecodeError: 'charmap' codec can't decode byte 0x8f in position 841`. No era pip roto ni
el archivo corrupto: **`pip._internal.utils.encoding.auto_decode` decodifica el archivo con
`locale.getpreferredencoding(False)`** salvo que encuentre un BOM o una cookie PEP-263 en las dos
primeras líneas. En Windows ese locale es **cp1252**, que no mapea cinco bytes
(`0x81 0x8D 0x8F 0x90 0x9D`). El `0x8F` salía del emoji **`⚠️` de un COMENTARIO** (línea 21 de
`requirements.txt`): `U+FE0F` (VARIATION SELECTOR-16) se codifica `EF B8 8F` en UTF-8. Un
comentario carteleaba el install completo — pip falla al decodificar el archivo, así que **no
instalaba NADA**, no es que salteara una línea.

**`requirements-dev.txt` tenía exactamente el mismo bug** (offset 1604, mismo `⚠️`), y como
CLAUDE.md exige instalar los dos, el próximo que monte el entorno se choca dos veces.

Los dos archivos pasaron a **ASCII puro** (acentos transliterados, emoji reemplazados por
`IMPORTANTE:` / `OJO:`). **Ningún pin cambió**: 19 requisitos en prod y 4 en dev, idénticos,
verificados parseando con el `auto_decode` de pip. Se agregó
**`backend/tests/test_requirements_ascii.py`** (6 tests) como guarda de regresión.

**Por qué ASCII y NO un BOM ni `# -*- coding: utf-8 -*-`:** las dos alternativas funcionan y las
dos son peores. Dejan el archivo dependiendo de una heurística de pip —y la cookie **solo se lee
en las DOS primeras líneas**, así que un comentario nuevo arriba la desactiva EN SILENCIO— y no
cubren a ninguna otra herramienta que lea el archivo con el locale del sistema. ASCII puro no
depende de pip, ni de su versión, ni del locale.

🔴 **La trampa que hace que la regla sea ASCII y no "casi ASCII":** los acentos (`á` = `C3 A1`) y
`🔴` (`F0 9F 94 B4`) **NO rompen** — cp1252 los mapea a mojibake y pip sigue de largo. Solo
revientan esos cinco bytes. O sea que la regla real ("UTF-8 menos cinco bytes") es **invisible al
ojo**: `⚠` (U+26A0) es inofensivo y `⚠️` (U+26A0 U+FE0F) es fatal, y **en el editor se ven
IGUAL**. Una regla que nadie puede verificar mirando no es una regla.

**Impacto en infraestructura:**

- **Dependencias:** ninguna nueva, ninguna versión cambiada. Solo el encoding del archivo.
- 🔴 **Para el dev de infra (es el punto de este hallazgo):** si montás el backend en Windows con
  el locale por defecto, **te chocás con esto en el primer comando**, en los dos archivos. Ya está
  arreglado en `main`; si trabajás sobre un clon viejo o un branch anterior al fix, el workaround
  de una vez es `set PYTHONUTF8=1` (o `chcp 65001`) antes del `pip install` — pero la solución
  real es traerse estos archivos. **En Linux/macOS/Docker/Vercel el bug NO aparece**: ahí el
  locale ya es UTF-8, y por eso los deploys venían pasando sin que nadie lo notara. Es un bug
  exclusivo del entorno de desarrollo Windows.
- ⚠️ **Regla nueva a respetar en AWS y en cualquier `requirements*.txt` que se agregue:** ASCII
  puro, comentarios incluidos. La cubre `tests/test_requirements_ascii.py`, que descubre los
  archivos **por glob** (no por lista escrita a mano), así que un `requirements` nuevo queda
  barrido solo. Lleva guarda de mínimo (`>= 2` archivos) y un test que **ancla el detector contra
  los bytes históricos exactos** antes de creerle un verde.
- **Migraciones / env vars / endpoints / buckets / auth / dominios:** ninguno.

**Estado del entorno de la Lenovo al cerrar la sesión:** `pip install` de los dos requirements
OK sin trucos (sin `PYTHONUTF8`, sin `chcp`), y **`pytest -q` → 3234 passed, 0 failed, 0 skipped**
en 157 archivos. Faltaban instalar **`pypdf`** (el paquete cuyo bloque de comentarios traía
justamente el `⚠️`) y **`ruff`** — este último no es cosmético: `tests/test_nombres_definidos.py`
lo invoca y **falla, no se saltea**, si no está.

> ⚠️ **Dato suelto para chequear en otra sesión, no bloqueante:** la suite da **3234** (3228 sin
> los 6 tests nuevos) contra los **3280 documentados en CLAUDE.md** el 11/8, con 157 archivos
> contra los 153 de esa medición. Todo verde y sin errores de colección ni skips, así que no hay
> nada roto; o el número de CLAUDE.md quedó viejo o hay barridos parametrizados que hoy descubren
> menos casos. No se investigó: excede el alcance de esta sesión.

---
## 2026-08-11 · J5b — migración 112: drop de las 11 tablas muertas · commit pendiente

**Qué cambió:** se escribió **`backend/migrations/112_drop_tablas_muertas.sql`** (🔴 DESTRUCTIVA,
irreversible) y se sacaron las 11 tablas de **`backend/db/schema.sql`**, que baja de 63 a **52
tablas** (1650 → **1430** líneas, 231 borradas + 11 de encabezado nuevo). Cierra el bloque J5.

### 🔴 ACCIÓN DE INFRAESTRUCTURA — ORDEN OBLIGATORIO

```
DEPLOY de J5a  →  112 (esta migración)
```

**La 112 NO se puede correr antes del deploy.** El código que hoy sirve tráfico todavía consulta
`ev_ciclos`/`ev_instancias` desde **dos superficies que no son de evaluaciones**: el Panel de
Procesos (que muere entero con un 500 `PROCESOS_ERROR`, no degrada una fila) y el reporte anual
(que deja de generarse). Al revés no pasa nada: el código de J5a ya no las nombra.

**Va SIN `CASCADE`, deliberadamente.** Verificado contra el catálogo el 11/8: **cero FK entrantes
desde tablas vivas**, cero vistas, cero matviews, cero funciones dependientes. Sin `CASCADE`, una
dependencia futura hace fallar el drop ruidosamente; con `CASCADE` la borraría en silencio.

**Orden interno:** las 5 `ev_*` hijas primero (`ev_resultados → ev_instancias → ev_criterios →
ev_ciclos → ev_plantillas`, 5 FK internas), después las 6 huérfanas en cualquier orden.

**Se lleva:** 50 índices · 9 triggers (8 `updated_at` + `trg_emp_sucesion`) · 17 policies RLS ·
66 constraints (29 FK). Cero secuencias, cero ENUMs — todo cae solo con `DROP TABLE`.
**Producción pasa de 63 a 52 tablas y de 52 a 43 triggers no internos (35 `updated_at` + 8
`trg_emp_*`).** Las queries de verificación posterior están comentadas al final del archivo, con
los valores esperados leídos del catálogo ANTES del drop.

**Las migraciones 004, 015, 021, 022, 023, 030 y 040–044 se CONSERVAN** como historial, igual que
la 102.

> ⚠️ **`schema.sql` queda POR DELANTE de producción hasta que Franco corra la 112** — declara 52
> tablas y producción tiene 63. Está escrito en su encabezado, con la marca 🚩 de volver a "AL
> DÍA" cuando se corra. Un rebuild desde el archivo ya sale sin las once, que es lo correcto: en
> RDS no tienen que existir nunca.

**La excepción con vencimiento se cerró.** `tests/test_triggers_updated_at.py` tenía
`_PENDIENTES_DE_DROP_J5B` (8 tablas) y un test que la vigilaba; el test **disparó solo** al sacar
las tablas de `schema.sql`, con el mensaje que pedía cerrarla. Se borraron **las dos cosas** —
constante y test— y el barrido volvió a ser igualdad estricta bidireccional: **35 tablas con
`updated_at` = 35 triggers en la 077, cero diferencia en las dos direcciones**.

**Verificación:** pytest **3228 passed** (era 3229; −1 es el test de vencimiento) · los 13
barridos verdes, incluidos los 3 que leen `schema.sql` · `ruff` limpio · front **647/647** y
`tsc` exit 0, sin tocar una línea.

---
## 2026-08-11 · J5a — desmontaje del módulo `ev_*` (solo CÓDIGO) · commit pendiente

**Qué cambió:** se borraron **17 archivos** del módulo `ev_*` (4 routers, 6 services, 5 repos,
`schemas/evaluaciones.py` y su test) — **19 endpoints publicados por HTTP e inalcanzables desde la
UI**, uno de ellos roto desde hacía meses (`PUT /api/evaluaciones/plantillas/{id}`: `model_dump`
sin `mode="json"` sobre `area_id`). `registro_routers.py` baja de 163 a **155**.

> ⚠️ **`services/_evaluaciones_export.py` y `schemas/evaluaciones.py` no se llaman `ev_*` y sí
> eran del módulo.** Y al revés: **`services/_audit_payloads_ev.py` SÍ se llama `ev` y NO lo es** —
> dos de sus funciones las usa el módulo de evaluaciones VIVO. Se le sacaron solo las dos que
> quedaron sin caller. Nombrar por prefijo no alcanzó en ninguna de las dos direcciones.

🔴 **IMPACTO EN INFRAESTRUCTURA — HAY UNO, Y ES EL PUNTO DE LA SESIÓN:**

**`migracionAWS/backend/migrations/077_recrear_triggers_updated_at.sql` pasó de 43 a 35
`CREATE TRIGGER`.** Se le sacaron los 8 que apuntan a tablas que J5b dropea (las 5 `ev_*` +
`sucesion_posiciones`, `notificaciones_config`, `configuracion_empresa`). **Sin esto el script
abortaba entero** contra un `schema.sql` ya limpio: `DROP TRIGGER IF EXISTS x ON tabla` **también
falla si la TABLA no existe** — el `IF EXISTS` cubre el trigger, no la relación. Es el archivo que
el dev de infra corre después de `schema.sql`.

**Nada más de infra.** Sin migraciones nuevas, sin env vars, sin dependencias, sin endpoints
nuevos, sin cambios de auth ni CORS. **Las 11 tablas siguen intactas en la base**: dropearlas es
J5b. La ventana entre los dos bloques está declarada en
`tests/test_triggers_updated_at.py::_PENDIENTES_DE_DROP_J5B`, con una guarda que **rojea cuando
J5b saque las tablas de `schema.sql`**, para que la excepción no sobreviva a su motivo.

**Dos features vivas que consultaban tablas `ev_*` y no degradaban:**
- `services/procesos_service.py` — contaba `ev_ciclos`/`ev_instancias`. Arma los 7 procesos en una
  list-comprehension dentro de UN try/except: la tabla ausente daba **500 y se llevaba el panel
  entero**, no una fila. Filas sacadas, **no reapuntadas** al módulo vivo (un lote importado no
  tiene `abierto`/`cerrado`).
- `services/_reporte_anual_metricas.py` — métrica `ev_finalizadas` en `anual_consolidado`. Sin
  try/except en ningún escalón: el informe entero dejaba de generarse. Métrica **sacada**.

**Test nuevo:** `tests/test_sin_ev_procesos_y_anual.py` (4 tests) cubre las dos, **por HTTP contra
la app real**. El fake **levanta ante una tabla desconocida en vez de devolver 0** — sin eso el
test pasaría verde con `ev_ciclos` todavía declarado. Mutación verificada: la tabla muerta de
vuelta en `_META` **y** en `_ESTADOS` rojea los dos tests (500 `PROCESOS_ERROR` y
`assert not ['ev_ciclos']`).

**Verificación:** pytest **3229 passed** (era 3280; −56 removidos, +5 agregados) · los 13 barridos
verdes · `ruff --select F821,F822,F823` limpio en todo el backend · front **647/647** y `tsc` exit
0, **sin un solo cambio**: el front nunca referenció `ev_*`.

> 📌 También: `docs/DEUDA-TECNICA.md` §8-bis anota la fragilidad que queda (procesos no degrada) y
> `CLAUDE.md` corrige el conteo de triggers, que decía 36 + 9 = 45 cuando el catálogo tiene
> **43 + 9 = 52**. La 077 declaraba 43, así que el que mentía era `CLAUDE.md`.

---
## 2026-08-11 · Contraste del popup de los `<select>` en modo oscuro · commit pendiente

**Qué cambió:** **una sola regla CSS** en `frontend/app/globals.css:131-158`, dentro del
`@layer base` que ya existía. Le da a `option` y a `optgroup` un `background-color` y un `color`
propios bajo `.dark`, con los tokens `--popover` / `--popover-foreground` que ya estaban
definidos. Arregla los **86 `<select>` nativos del front de una vez**: el popup lo dibuja el
navegador pintando cada `option` con el fondo del `<select>`, y 60 de los 86 declaran
`bg-transparent`, así que quedaba la superficie blanca de UA con el texto casi blanco heredado
del tema — **1.04:1, ilegible**. Ahora da **14.01:1**. `docs/DEUDA-TECNICA.md` suma una sección 9
con las cuatro superficies del mismo tipo que **no** se tocaron (autofill de Chrome, 8 `<textarea>`
crudos sin clase de placeholder, 132 tooltips nativos, 10 checkbox sin `accent-color`).

**Impacto en infraestructura:** **Ninguno.** Sin migraciones, sin variables de entorno, sin
dependencias nuevas, sin endpoints, sin cambios de auth ni de CORS. Es un archivo de estilos del
front: sale por el deploy normal de `sofia-front` y **no requiere tocar `sofia-backend`**.

**Test nuevo:** `frontend/app/contrasteTokens.test.ts` (186 líneas, 1 test) mide el ratio WCAG de
los 4 pares fondo/texto del bloque `.dark`, parseando los valores REALES del archivo (hex y
oklch) — no constantes copiadas. La regla de `option` no elige colores, los toma prestados de
`--popover`/`--popover-foreground`, así que un ajuste de paleta puede volver el popup ilegible sin
tocar la regla; el test ataja eso. **Descubrió una brecha real: `--primary`/`--primary-foreground`
en oscuro da 3.68:1** (en claro, 6.18:1) — anotado en `docs/DEUDA-TECNICA.md` §9, no arreglado por
ser decisión de marca.

**Verificación:** `tsc --noEmit` exit 0 · vitest **647/647 en 53 archivos** (646 + el test nuevo)
· pytest **3280 passed**. Backend y front sin cambios de comportamiento; el +1 es el test.
`globals.css` queda en **174/200**.

**Sincronización de docs (misma fecha, solo documentación):** el test nuevo entra como **barrido
estructural 13**. `CLAUDE.md` → Tests pasa de DOCE a TRECE con su entrada, y se remidieron las dos
líneas de conteo de la suite (backend 3231→**3280**, front 620/49→**647/53**).
`docs/ORDEN-SESIONES-CODIGO.md` y `docs/DEUDA-TECNICA.md` §4 tenían conteos viejos (doce y cinco):
corregidos, y los dos ahora **apuntan a `CLAUDE.md` como único inventario** en vez de repetir la
lista. En `docs/PLAN-DE-TRABAJO.md` §10.3 se corrigió además un error de fondo: **T12 ya estaba
hecho** (`tests/test_callers_huerfanos.py`, con alcance más amplio del que pedía el plan) y **T11
quedó descartado en la forma en que se pidió** — lo que existe es más angosto a propósito, con los
44 métodos de escritura sin auditoría fuera por construcción.

**Impacto en infraestructura de esta parte:** **Ninguno.** No se tocó una línea de código.

> 🔴 **Lo único que falta es una verificación VISUAL, y decide entre dos arreglos distintos.**
> En Chromium sobre Windows/Linux `option { background-color }` se respeta desde siempre; en
> **macOS** el popup del `<select>` fue un menú nativo durante años e **ignoraba los estilos de
> autor**, y recién se volvió estilable en versiones recientes. Como se trabaja en las dos
> plataformas, **hay que probarlo en las dos**. Si en la Mac no la toma, el plan B para ese
> navegador es cambiar `bg-transparent` por `bg-background` en las ~20 constantes que lo declaran
> (60 sitios) — **no está implementado a propósito**: se decide con el resultado de la prueba.

---
## 2026-08-10 · Migraciones 110 y 111 — idempotencia de vacaciones y dedup de objetivos · commits pendientes

**Qué cambió:** dos índices únicos. **Ninguna es destructiva**: solo agregan, no tocan datos ni
columnas. Las dos van DESPUÉS del deploy, pero **no dependen de él** — el código actual no las
usa; existen para habilitar el import de vacaciones y para tapar un duplicado del de objetivos.

### 🔴 EL ORDEN OPERATIVO COMPLETO

```
108  (ya corrida, ANTES del deploy)
  ↓
DEPLOY del código                     ← L2+L4+L5+L7+L9 y el fix de áreas, en el mismo push
  ↓
109  (DESTRUCTIVA — clientes)         ← necesita el código nuevo ARRIBA
  ↓
110  (vacaciones)                     ← no dependen del deploy; van después para no mezclar
  ↓
111  (objetivos)
```

**Por qué la 109 va después del deploy:** dropea `clientes.empresa_id`, y el código viejo todavía
la lee (`SELECT *` con `ClienteResponse.empresa_id` obligatorio) y la escribe. Corriéndola antes,
el módulo de clientes queda en 500 hasta que salga el código. El detalle de las tres inversiones
posibles está en la entrada del BLOQUE L.

**Por qué la 110 y la 111 van al final:** no las necesita ningún código desplegado, así que
mezclarlas con el paso riesgoso solo agrega ruido al diagnóstico si algo falla.

### 110 — `uq_vacacion_empleado_rango_tipo (empleado_id, fecha_desde, fecha_hasta, tipo)`

Sin esto **el import de vacaciones no se puede construir idempotente**: `on_conflict` de PostgREST
exige una constraint única. Resubir la planilla duplicaría todas las licencias del archivo, sin
error — los saldos quedan mal y el ausentismo cuenta doble.

✅ **`solicitudes_vacaciones` tiene 0 filas** (verificado hoy): entra sin deduplicar nada. **Ésta
es la ventana**; con histórico cargado habría que resolver a mano cuál de dos filas idénticas
sobrevive, sobre licencias de gente real.

Corrige la asimetría con `solicitudes_ausencia`, que lo tiene desde la 089.
⚠️ **Las columnas no son las mismas:** ausencias usa `tipo_id` (FK); vacaciones usa `tipo`
(varchar con CHECK). Se verificó en el catálogo, no se dedujo por analogía.

### 111 — `ux_objetivo_responsable_titulo (empresa_id, responsable_id, lower(titulo))`

El import de objetivos **inserta siempre**: `_a_create` no chequea existente y la tabla solo tenía
`pkey`. Es el único de los cuatro imports del repo sin ninguna defensa.

🔴 **La clave NO es el título solo.** Es lo que identifica una fila de la planilla: las dos
columnas que el import declara requeridas (`Titulo` + `Responsable`). Dos responsables pueden
tener legítimamente "Cerrar el trimestre"; con el título solo, el segundo rebota y RRHH tendría
que inventar títulos distintos para el mismo objetivo de dos personas.
🔴 **`fecha_entrega` NO entra**, aunque parezca identidad: es NULLABLE, y en Postgres los NULL no
colisionan — incluirla desactivaría el índice **en silencio** para todo objetivo sin fecha.

✅ **`objetivos` tiene 1 fila y 0 colisiones** bajo esa clave (verificado con el `GROUP BY … HAVING
count(*) > 1`).

### Verificación posterior

Las dos migraciones traen al final, comentadas, las queries que confirman el resultado — incluida
**la prueba real de unicidad**: un INSERT duplicado dentro de `BEGIN/ROLLBACK`, que es lo único
que distingue "el índice existe" de "el índice funciona". Cada una trae además su **contraste**
(el caso legítimo que NO debe rebotar), sin el cual un índice demasiado ancho pasaría la prueba.

`db/schema.sql` quedó con los dos índices y sus comentarios (1641 → 1651 líneas).

---

## 2026-08-10 · Fix del 500 al crear un área + barrida de ids mal tipados · commits pendientes

**Qué cambió:** crear un área con el sidebar en "Todas las empresas" —el default— tiraba **500**
en producción. `AreaCreate.empresa_id` estaba tipado `str`, así que el `""` que mandaba el front
pasaba Pydantic y moría en Postgres. Ahora es `UUID` y sale como 422 legible. `responsable_id`
también pasó a `UUID | None`.

**Para infraestructura: NO hay acción.** Sin migraciones, sin env vars, sin dependencias, sin
endpoints nuevos ni borrados. Cambia el CÓDIGO de estado de un camino de error (500 → 422) y el
tipo de dos campos de un body; el schema de base no se toca.

### El camino completo del 500

```
areas/page.tsx:236   empresaId={getEmpresaActivaId() ?? undefined}   → undefined en consolidado
AreaModal.tsx:107    empresa_id: empresaId ?? getEmpresaActivaId() ?? ""   → ""   (sin validación)
schemas/area.py:12   empresa_id: str          → Pydantic ACEPTA el ""
Postgres             22P02 invalid input syntax for type uuid   → 500
```

Es el mismo bug del `empresa_id: ""` de clientes **con un agravante**: allá el schema tipaba
`UUID` y salía un 422 (feo pero honesto); acá el tipo `str` movía la validación de la frontera al
motor de base de datos, donde el error ya no es del pedido sino del servidor.

### 🔴 EL ARREGLO DEL TIPO HABRÍA ROTO EL ALTA Y LA EDICIÓN

Cambiar `str → UUID` no alcanza: **`model_dump()` pelado devuelve el objeto UUID**, y el cliente
de Supabase no lo sabe serializar (`Object of type UUID is not JSON serializable`). Faltaba
`mode="json"` en **`area_repo.save` Y en `area_repo.update`** — o sea que el fix habría cambiado
un 500 en el caso vacío por un 500 en **todos los casos buenos**.

🔴 **Solo se vio EJECUTANDO los dos caminos, no leyéndolos.** El `save` se detectó al escribir el
fix; el `update` recién apareció al tipar `responsable_id` y correr los dos por separado.

### Los 5 campos que quedan mal tipados

`NominaCreate.empleado_id` · `ImportacionNominaConfirmarRequest.empresa_id` ·
`ImportacionObjetivosConfirmarRequest.empresa_id` · `FilaNominaPreview.empleado_id` ·
`FilaObjetivoPreview.responsable_id` — todos `str` donde va un UUID.

⚠️ **Están protegidos por CONVENCIÓN DEL FRONT, no por el tipo**: el modal usa un id de una lista,
o valida el select, o el valor vuelve de un preview. **Esa es exactamente la condición que tenía
áreas hasta hoy** — hasta que el sidebar en consolidado produjo un caso que el front no cubría.

Fuera de esa lista, ya inventariados: `PresupuestoCreate.area_id` (endpoint sin puerta), los 2 de
assessment (módulo apagado) y los 3 de Gmail/LinkedIn (correctos como `str`, no son UUIDs).

### 🔴 `ev_plantillas` está ROTO, sin arreglar — y es un argumento para J5

`services/ev_plantillas_service.py:75` arma el payload con `model_dump(exclude_none=True)` sobre
`PlantillaUpdate`, que tiene `area_id: Optional[UUID]`, y **`ev_plantillas_repo.update:52-57`
tampoco lo convierte**: el UUID va directo al `.update()`. Editar una plantilla con área da 500.

**No se arregló a propósito** (fuera del alcance de la sesión), pero importa para el handoff:

- El **router está montado y responde**. La UI de `ev_*` se borró, las tablas están vacías, y por
  eso el bug sobrevivió: **ese camino nunca se ejercitó**.
- 🚩 **Es un argumento a favor de J5** (drop de las 11 tablas muertas): código publicado que nadie
  puede alcanzar desde la aplicación y que está roto sin que nadie se entere.
- 🔴 **Y fija un requisito de orden: los routers `ev_*` se desmontan ANTES del DROP.** Dropear las
  tablas con los routers montados deja endpoints publicados apuntando a tablas inexistentes.

### La barrida de `model_dump()` sin `mode="json"`

62 apariciones crudas → 6 escrituras sobre schemas con campos UUID → **5 falsos positivos**
(`_empleado_write_repo` ×2, `inventario_items_repo`, `vacante_repo` ×2): todas convierten los
UUID **a mano, línea por línea, después del `model_dump()`**. El único real es `ev_plantillas`.

### Verificación

Backend **3280 passed** (era 3275) · Front **646 passed** · doce barridos verdes · `tsc` exit 0.

Cuatro mutaciones, todas rojean: `empresa_id → str` (2 failed) · sin validación en el modal
(2 failed) · el modal manda la empresa del sidebar (2 failed) · sin `mode="json"` en `save`
(1 failed) · `responsable_id → str` (3 failed).

### Divisiones que hicieron falta antes del fix

`AreaModal.tsx` **207 → 135** (`areaForm.ts` + `AreaFormFields.tsx` + `guardarArea.ts`) ·
`areas/page.tsx` **271 → 128** (`useAreas.ts` + `AreasTabla.tsx` + `AreaEliminarDialog.tsx`).

⚠️ **`repositories/area_repo.py` quedó en 100/100** — sumar el `mode="json"` a los dos caminos lo
dejó en el techo exacto. **Va a la lista de archivos al filo: el próximo cambio ahí exige
dividirlo primero.**

---

## 2026-08-10 · BLOQUE L · Clientes como catálogo GLOBAL (L1–L9) · commits pendientes

**La decisión:** un cliente **NO pertenece a ninguna empresa**. Se ve, se crea y se da de baja con
el selector del sidebar en cualquier modo, y cualquier empleado imputa horas contra cualquier
cliente. `clientes` pasa a comportarse como `tipos_ausencia`.

**El motivo medido:** los 3 clientes de producción son todos de **una** de las dos sociedades, y el
padrón entero de la otra **no podía ni identificarse** en el link público — el gate lo rechazaba
con `sin_clientes`.

### 🔴 PARA INFRAESTRUCTURA: SON DOS MIGRACIONES CON EL DEPLOY EN EL MEDIO

```
108 (preparación, no destructiva)  →  DEPLOY del código  →  109 (cierre, DESTRUCTIVA)
```

**Ninguno de los tres pasos se puede adelantar:**

| Si se invierte | Qué pasa |
|---|---|
| Deploy **antes** de la 108 | El alta de clientes falla con **23502**: el código nuevo no manda `empresa_id` y la columna sigue `NOT NULL`. |
| 109 **antes** del deploy | El código viejo entra en **500 por dos caminos**: `42703` en el INSERT y `ValidationError` de Pydantic en cada lectura (`SELECT *` con `ClienteResponse.empresa_id` obligatorio). Módulo de clientes caído. |
| 109 **sin** la 108 | 🔴 **EL PEOR, PORQUE NO FALLA.** Se dropea `ux_clientes_nombre_por_empresa` sin que exista el reemplazo global, y la tabla queda **sin ninguna unicidad de nombre, en silencio**: "Acme" pasa a poder cargarse dos veces y los reportes por cliente se parten. El `existe_nombre` del service sigue devolviendo su 409, así que el 99% de las veces parece funcionar. La 109 lleva una guarda que aborta si no encuentra `ux_clientes_nombre_global`. |

La 108 corrida sola no hace nada (sacar un `NOT NULL` no cambia ninguna fila ni ningún INSERT que
siga mandando el valor), así que es segura de correr en cualquier momento antes del deploy.

**Sin env vars nuevas, sin dependencias, sin buckets, sin cambios de auth ni de CORS.**

### Las nueve sesiones

| | Qué hizo |
|---|---|
| **L1** | Refactor puro previo. `identificacion_service.py` 150/150 → **119** + `_identificacion_resolver.py` **65**, corte entre decisión y orquestación, para que el gate quedara entero en un archivo. `ClienteModal.tsx` **NO** se dividió: L5 le sacaba ~37 líneas y dividir antes obligaba a tocar dos veces el mismo test. |
| **L2** | Backend de clientes: `empresa_id` sale de schemas, repo, service, routers y auditoría. Migración **108**. Dejó 25 tests rojos a propósito y **rompió el link público** (ver abajo). |
| **L4** | Cierra lo que L2 rompió + el gate de identificación pasa a preguntar por el SISTEMA, no por la empresa del empleado. |
| **L5** | Front: el modal pierde el `<select>` de empresas (147 → **112**). |
| **L6** | Migración **109** + `db/schema.sql` al estado post-109. |
| **L7** | Reemplaza los 25 rojos, uno por uno. Suite a 0 failed. |
| **L8** | 🔴 El total de horas por cliente deja de recortarse por empresa, y aparece el **desglose por sociedad** dentro de cada cliente. |
| **L9** | Cierra la incoherencia que L8 dejó: el detalle y el borrado también dejan de recortarse. Divide `routers/horas_cliente.py` (80/80) en lecturas + escrituras. |

*(No hay L3: la numeración se reservó para el front y quedó absorbida en L5.)*

### Las decisiones del bloque — NO se rediscuten

1. **Un cliente no pertenece a ninguna empresa.** Revierte lo declarado en `102_clientes.sql`:
   *«`empresa_id` NOT NULL: un cliente es de UNA empresa del grupo. No hay clientes globales.»*
2. **Unicidad de nombre GLOBAL y case-insensitive** (`ux_clientes_nombre_global` sobre
   `lower(nombre)`). Es más estricta que antes: dos sociedades ya no pueden tener cada una su "Acme".
3. **El evento de auditoría de cliente va con `empresa_id` NULL.** Precedente ya establecido por
   `usuario` (los usuarios no cuelgan de una empresa) y por el lote de nómina. Usar el header como
   fallback habría mentido sobre de quién es la entidad.
4. **El gate `sin_clientes` se queda**, ahora a nivel SISTEMA: con cero clientes en todo el sistema
   nadie puede imputar y devolver `sin_clientes` es honesto. El valor del CHECK no cambia, cambia
   su condición de disparo.
5. 🔴 **Las horas de un cliente son del cliente.** Las empresas son sociedades de un mismo grupo
   económico: **el total nunca se recorta por empresa**, y eso alcanza al listado, al export, al
   detalle y al borrado. El selector de empresa del sidebar **no manda en esa pantalla**, y la
   pantalla lo dice con una línea visible. El reparto por sociedad no se pierde: se muestra
   desglosado dentro de cada cliente.

### 🔴 L2 rompió L4, y la premisa de por qué lo iba a tolerar era falsa

L2 se escribió asumiendo que el link público *"iba a quedar pasando un `empresa_id` que el repo ya
ignora"*. **Python no ignora posicionales de más.** Verificado ejecutando:

- `carga_horas_service.py:131` → `find_by_id(cliente_id, empresa_id)` → **TypeError** → 500 en toda
  carga de horas del link público.
- `carga_horas_service.py:117` → `find_all(empresa_id)` → el UUID liga contra `incluir_inactivos`,
  que es truthy → 🔴 **no revienta: el select público ofrecía clientes dados de baja.**

El segundo es peor porque no falla, miente. **L2 y L4 van en el mismo push.**

### 🔴 El caso del #21 — por qué los rojos se listan uno por uno y nunca por grupo

`test_el_diff_registra_el_antes_y_el_despues` estaba dentro de `TestAuditoria`, el bloque que
perdía su objeto. **No era un test de aislamiento**: era el **único test del diff de auditoría de
clientes en todo el repo**, y afirma que `activo` NO aparece en `datos_nuevos` — el diff fantasma
que costó **93 eventos falsos** en producción. Borrar el bloque entero se lo hubiera llevado
puesto **con la suite en verde**.

De los 25: 8 arreglados solo en el fixture, 7 reescritos sobre un caso que sí existe, 1
**invertido**, 6 reemplazados por `test_clientes_global.py`, y **3 que había que escribir porque
nada los cubría**.

### 🔴 Tests VERDES con la premisa muerta — 18 casos en cinco sesiones

Los rojos son los fáciles: se ven. Lo caro es lo que queda en verde afirmando un mundo que ya no
existe.

| Sesión | Qué |
|---|---|
| **L4** (1) | `test_el_cliente_se_valida_contra_la_empresa_de_la_sesion` — el fake devolvía `None` comparando contra `EMPRESA_IMPOSTORA`; con `empresa_id=None` **sigue dando `None`**, así que pasaba por un motivo que ya no existía. |
| **L5** (3) | `ClientesTabla.test.tsx` rompía `tsc` y su test *"sin colapsar homónimos"* se apoyaba en *"el índice único es POR empresa"* · `erroresCliente` citaba un literal que el backend dejó de emitir · `clientes/page.tsx` decía *"la empresa la pone el header"*. |
| **L7** (4) | Cuatro **docstrings de falsabilidad** describían la barrera de empresa como el modo de falla a vigilar: son las instrucciones para el próximo que toque el archivo. |
| **Diagnóstico** (7) | `CLAUDE.md:125, 235, 245, 471, 631` · `MATRIZ-FILTROS.md:140, 176`. Corregidos en este cierre. |
| **L8/L9** (3) | `_horas_vista_repo.py` decía que el filtro era por `fecha` y `empresa_id`; los docstrings del detalle y la baja hablaban de una barrera que se sacó. |

### 🔴 Dos agujeros de cobertura que solo aparecieron por mutación

Ninguno se veía leyendo el código ni el nombre de los tests.

- **L8 — el export no estaba cubierto.** Recortar `svc.exportar` por empresa dejó **34 tests en
  verde**: los dos tests de export armaban las filas a mano con
  `construir_filas_export(repo.find_por_periodo(...))` y **nunca entraban al service**.
- **L9 — la query no estaba cubierta.** Volver a filtrar por empresa en el `find_by_id` REAL dejó
  **37 tests en verde**: los tests del borrado cruzado van por el service, que corre contra
  `_RepoFalso`. El service estaba cubierto; la query no.

Los dos están cerrados con tests que atraviesan la capa mutada. Ver `DEUDA-TECNICA.md §5`.

### Números

| | Antes | Después |
|---|---|---|
| Backend | 3247 passed | **3271 passed**, 0 failed, 0 skipped |
| Front | 636 passed | **637 passed**, 0 skipped |

Doce barridos verdes. `tsc --noEmit` exit 0. `ruff check` sin hallazgos nuevos en los tocados.

### Archivos de migración

- **`108_clientes_global_preparacion.sql`** — `DROP NOT NULL` + `CREATE UNIQUE INDEX
  ux_clientes_nombre_global (lower(nombre))`. No destructiva.
- **`109_clientes_global_cierre.sql`** — dropea `ux_clientes_nombre_por_empresa`,
  `idx_clientes_empresa`, `clientes_empresa_id_fkey` y la columna. Guarda contra correrse sin la
  108, y al final las **queries de verificación posterior** comentadas.

**`horas_proyecto.cliente_id` y su FK NO se tocan**, ni `horas_proyecto.empresa_id` /
`empleado_empresa_id`: se rastrearon los dos caminos de inserción y **ninguno toma la empresa del
cliente** (salen del empleado y del proyecto).

### ⚠️ CONSECUENCIAS ASUMIDAS — decididas, no olvidadas

1. **Los eventos de auditoría de cliente solo se ven en modo consolidado.** `audit_repo.py:78-79`
   hace `.eq("empresa_id", X)` y en Postgres eso excluye los NULL. El consolidado **es el default
   del sidebar**, así que el camino normal funciona — pero un operador que selecciona una empresa
   para investigar algo **deja de ver los eventos de cliente y nada se lo avisa**. No hay leyenda
   ni contador de "N eventos ocultos".
2. **El mensaje "Ya existe un cliente con ese nombre" queda mudo si el cliente existente está dado
   de baja.** `existe_nombre` incluye los inactivos a propósito (el índice único tampoco los
   excluye), pero el listado los esconde por defecto (`clientes/page.tsx:33`). El operador recibe
   el 409 sobre algo que **no puede encontrar**, y nada le sugiere tocar "Ver bajas". Es
   **preexistente** —pasaba igual dentro de una empresa— pero el catálogo global lo hace **más
   frecuente**: ahora el cliente que bloquea el nombre puede ser uno que la otra sociedad dio de
   baja y que este operador nunca vio.

### Pendientes que el bloque deja abiertos

- **El desglose por empresa renderizado no tiene test de front.** Vive dentro del panel colapsado y
  `ClientesColapsables` arranca cerrado, así que `renderToStaticMarkup` nunca lo expande. Cubierto
  por los 5 tests de backend y por `tsc`, no por render.
- **Ningún test de la vista de horas por cliente pega por HTTP.** Es el hueco de los 82 endpoints
  ya medido (K7), no algo que L9 introdujo.
- **`_usuario_id` quedó del lado de las escrituras** en `horas_cliente_escrituras.py`, distinto de
  `clientes.py`, donde quedó del lado de las lecturas por razones históricas. El criterio bueno es
  el nuevo: el helper vive donde se usa.

## 2026-08-10 · L1 · División de `identificacion_service.py` (refactor puro, cero cambio de comportamiento) · commit pendiente

**Qué cambió:** nada de comportamiento. Es la sesión previa al bloque que convierte clientes en
catálogo global (L4/L5): ese bloque toca archivos que estaban en el límite de líneas, así que la
división va antes y en commit propio.

**Se dividió UNO de los dos previstos.**

**Para infraestructura: NO hay acción.** Sin migraciones, sin env vars, sin dependencias, sin
endpoints nuevos ni borrados, sin cambios de auth ni de CORS. Un archivo nuevo en `services/`.

### `identificacion_service.py` 150/150 → **119** + `_identificacion_resolver.py` **65**

**El corte es entre la DECISIÓN y la ORQUESTACIÓN**, no por cantidad de líneas. Salió
`_resolver` —los cinco desenlaces posibles de una identificación, incluido el gate
`hay_clientes_activos`— como `decidir(repo, limitador, dni)`. Quedó en el service el `identificar`:
registrar el intento, nivelar el tiempo, levantar el `AppError` único y emitir la sesión.

Es la única costura donde ninguno de los dos lados necesita saber del otro: el resolver no conoce
excepciones, logs ni tiempo; el orquestador no conoce los cinco motivos. **El gate que toca L4
quedó entero en un solo archivo**, que era el objetivo de hacer esto antes y no después.

🔴 **`_PISO_SEGUNDOS` NO se movió, a propósito.** Tres tests lo monkeypatchean sobre el módulo:
`test_identificacion_publica.py:128` y `:329`, y `test_identificacion_rate_limit.py:72`. Moverlo
al archivo nuevo los habría roto sin que cambiara ni una línea de comportamiento.

### 🔴 `ClienteModal.tsx` NO se dividió — y la razón vale más que la división

Estaba en 147/150, o sea **al filo, no sobre el límite**. Dos motivos para dejarlo:

1. **L5 lo resuelve solo.** Al sacar el `<select>` de empresas, L5 borra de ese archivo los 3
   imports de empresa, los 2 `useState`, el `useEffect` de `fetchEmpresas`, la línea de siembra
   con sus comentarios, el bloque del `<select>` y el `const SEL`: **≈37 líneas**. Queda en
   **~110/150**, cómodo.
2. **Dividir antes obligaba a modificar `guardarCliente.test.ts` DOS veces**, y la primera para
   adaptarlo a una estructura que L5 desarma. Ver la anotación en `DEUDA-TECNICA.md §5`.

### Verificación de que es refactor y no otra cosa

- **Backend 3247 passed · Front 636 passed · 0 skipped** — exactamente los mismos números que
  antes de la sesión. **Cero tests tocados**, ni siquiera una línea de import.
- Los doce barridos verdes (521 backend + 36 front). `tsc --noEmit` exit 0.
- **Mutación de control:** romper el gate (`hay_clientes_activos` siempre disponible) rojea
  **5 tests antes de dividir y 5 después**. Mismo número ⇒ la lógica movida sigue enteramente
  bajo el alcance de la suite, sin código huérfano.
- `ruff check`: **6 hallazgos antes, 6 después**, mismos códigos (`I001`, `UP006`, `UP035`,
  `UP045`×3), solo redistribuidos entre los dos archivos. No se corrigieron: son deuda de estilo
  preexistente y arreglarlos habría salido del refactor.

---

## 2026-08-10 · El 422 entra al contrato de errores + el alta de clientes deja de mandar `empresa_id` vacío · commit pendiente

**Qué cambió:** dos cosas, y la primera es MUCHO más ancha que la segunda. (1) `main.py` no
registraba handler para `RequestValidationError`, así que **todo 422 de todo endpoint salía con
el `{"detail": [...]}` de Pydantic**, sin `message` ni `code` — y `toApiError`, embudo único del
front, caía a `"Error del servidor"` / `"UNKNOWN"`. Ahora el 422 sale con el contrato
`{error, message, code: "VALIDACION_INVALIDA"}` y un mensaje en castellano. (2) `ClienteModal`
mandaba `empresa_id: getEmpresaActivaId() ?? ""`, que en modo consolidado —el default del
sidebar— es `""`: el alta de clientes devolvía **422 en producción, siempre**. Ahora el modal
tiene el `<select>` de empresas que ya tenían `ItemModal` y `CapacitacionModal`.

**Para infraestructura: NO hay acción.** Sin migraciones, sin env vars nuevas, sin dependencias,
sin buckets, sin endpoints nuevos ni borrados, sin cambios de auth ni de CORS. Nada que correr.

**Lo único que cambia del lado del deploy es el BODY de las respuestas 422** (el status sigue
siendo 422). Si algún consumidor externo parseaba `detail`, deja de encontrarlo — hoy el único
consumidor es nuestro front, que buscaba `message`/`code` y ahora sí los encuentra.

### DOS codes distintos en el 422, según quién armó el dato

- `loc[0] == "body"` → **`VALIDACION_INVALIDA`**: lo llenó una persona, se nombra el campo.
- query / path / header → **`PEDIDO_INVALIDO`**: lo armó el front. **No se nombra el campo**,
  porque pedirle al usuario que corrija "page size" lo manda a buscar un input que no existe.
  Es el caso `page_size=200` que ya quemó dos veces. El campo va igual al log completo.
- `loc` mixto → gana body (la rama accionable).

### 🔗 Hay un archivo GENERADO nuevo: `backend/tests/_contrato_errores.json`

Lo escribe `backend/tests/test_validacion_422.py` capturando respuestas REALES del app, y lo lee
`frontend/services/api.test.ts` para alimentar a `toApiError`. **No editarlo a mano.** Es lo que
acopla las dos puntas del contrato: con el body copiado a mano en el test del front, renombrar
`message` en el backend rojeaba solo el backend — se midió. Implica un orden: si tocás el handler
y corrés solo vitest, ves verde hasta correr pytest.

`toApiError` pasó a ser `export` en `frontend/services/api.ts` — **solo para poder testearla**;
sigue sin tener callers fuera del módulo (el barrido #12 la cuenta viva por uso intra-módulo).

### 🔴 Por qué esto vale más que el bug que lo destapó

El 422 de clientes era **un** síntoma. La causa —el 422 fuera del contrato— afectaba a las 27
pantallas, y ya había quemado dos veces antes sin que se lo identificara: `useDestinatarios` y
`useCandidatosProyecto` pedían `page_size=200`, el backend respondía 422 y **la pantalla decía
"no hay datos" con la base llena**. Se cerró aquella vez con `pageSize.test.ts`, que evita que
alguien pida de más — pero no arreglaba que un 422 fuera indescifrable. Ahora ese mismo caso
responde `"Revisá los datos del formulario: page size (es demasiado grande)."`

### Qué se muestra y qué solo se loguea (criterio, en `middleware/_mensaje_validacion.py`)

Sale la **hoja** del campo, humanizada, y qué le pasa. **No** sale el `loc` completo (describe el
anidamiento del schema), **no** sale el valor recibido, **no** salen el `msg`/`type`/`url` de
Pydantic. Al log van el `loc` completo y el `type` — 🔴 **el `input` no va tampoco al log**: un
`password` mal formado escribiría la contraseña en claro en los logs de la plataforma.

### 🔴 El hueco de test que esto destapa, y que NO se cerró

Los 30 tests de clientes pasaban con el bug vivo, y **los fakes no tenían nada de malo**: la
barrera de empresa está genuinamente probada. El problema es otro y es del repo entero — esos
tests **instancian `ClienteCreate(empresa_id=uuid4(), ...)` a mano**, o sea empiezan del lado de
adentro de la validación. Se midió el barrido que lo cerraría ("todo endpoint con body tiene un
test que atraviesa HTTP") y **nace con 77 huérfanos sobre 82 endpoints**: solo **7 de 154**
archivos de test atraviesan HTTP. No se forzó — declarar 77 excepciones sería una lista que nadie
mira. **Queda como decisión pendiente de Franco.**

---

## 2026-08-10 · Limpieza del módulo de horas + barrido de código muerto del FRONT · commit pendiente

**Qué cambió:** nada de runtime. Se cerraron los tres cabos que la verificación previa dejó
anotados, y uno de ellos abrió un agujero estructural que valía más que el cabo.

**Para infraestructura: NO hay acción.** Sin migraciones, sin env vars nuevas, sin rutas nuevas
ni borradas. Las condiciones para encender el link público **no cambiaron**:
`HORAS_PUBLICO_ENABLED=true` en `sofia-backend` y al menos un cliente cargado.

### 🔴 El barrido de endpoints tenía un punto ciego, y se encontró por accidente

`services/clientes.ts::fetchCliente` nació sin un solo caller y sobrevivió cinco sesiones con
`test_callers_huerfanos.py` en verde. El motivo importa más que el caso: **ese barrido empareja
(path, método) contra los LITERALES de path escritos en el front**, no contra las funciones que
de verdad se llaman. `updateCliente` y `deleteCliente` escriben el MISMO literal con otro método,
así que le seguían "dando caller" al GET. Un wrapper muerto tapa a su endpoint.

**Se borró la función** (el endpoint queda publicado por completitud REST, declarado con su
razón) **y se escribió el barrido que faltaba**: `frontend/services/barridoFront.test.ts`, que
mira el otro eje —quién IMPORTA a quién—. Los dos barridos son necesarios: cada uno ve lo que el
otro no puede.

**Lo que encontró apenas se encendió** (263 exports barridos, 10 huérfanos, todos declarados con
razón). Dos son features publicadas e **inalcanzables desde la UI**, y ninguna es del módulo de
horas:
- 🔴 **`POST /api/costos/presupuesto`** — `setPresupuesto` es el único lugar del front donde se
  escribe ese path, y nadie la llama. **Fijar un presupuesto no se puede hacer desde la UI.**
  Encaja con lo que ya estaba verificado en producción: cero eventos `set_presupuesto` en
  auditoría. Se creía que era falta de uso; es falta de puerta.
- 🔴 **La asignación SINGLE a un proyecto** — la pantalla usa el bulk y el alta por área, que son
  otros paths.
- Más `deleteProyecto`, `fetchEmpresaConfig` (devuelve la PRIMERA empresa: con dos cargadas ya no
  significa nada estable), `subscribeEmpresaActiva` (store a medias) y `updateVacacion`.
- Los cuatro falsos positivos que producía —uso dentro del propio módulo, re-exports, colisión de
  nombres entre módulos, imports de tipo— están resueltos y explicados en el encabezado. Verificado
  por mutación: función huérfana nueva → rojo; excepción que consigue caller → rojo; escaneo
  apuntando a un árbol vacío → rojo en las tres guardas de mínimo.

⚠️ **Efecto colateral que hay que conocer antes de escribir un comentario en el front:** el
escáner de paths no distingue un comentario de un template literal. Citar una ruta entre
backticks vuelve a taparle el endpoint al barrido. Pasó al documentar este mismo borrado.

### Documentación puesta al día contra la realidad, no contra otro documento

Todo lo de abajo se midió (introspección de `app.routes`, `find`, catálogo vivo), no se copió:
- **`CLAUDE.md` afirmaba que el link público estaba "Bloqueado: requiere la reunión de
  definición"** — seis sesiones después de que el módulo empezara. Reescrito, más una sección
  propia del módulo en *Otros módulos*.
- Conteos corregidos: routers 52 → **69** · services 129 → **197** · repos 69 → **87** · rutas
  montadas 208 → **247** · migraciones 87 → **105** (va por la **107**) · suite backend 1551 →
  **3231** en 153 archivos · front 214 en 16 → **620 en 49** · barridos estructurales "CINCO" →
  **doce**.
- **Exports: la doc decía 12.** Medido: **27 endpoints con `formato`, 19 con filtros propios**.
- ✅ **La migración 089 estaba anotada como PENDIENTE y está CORRIDA** (el índice
  `uq_ausencia_empleado_rango_tipo` existe en producción). No quedan migraciones pendientes.
- 🟢 **`manager_id` dejó de estar en cero: 0/19 → 11/31.** Desbloquea probar `mandos_medios` y
  hace que el desempate por superior del matcheo de evaluaciones discrimine de verdad. La doc
  todavía decía "todavía no probar ese rol".
- Padrón actualizado: **2 empresas, 31 empleados** (era 1 y 19). `horas_contrato` **0/31** sigue
  siendo el cero que importa para las licencias.
- **`docs/MATRIZ-FILTROS.md`** ahora incluye *Clientes* y *Horas por cliente*. ⚠️ El pedido decía
  que clientes tenía un filtro `search`: **no existe**, ni en el backend ni en la UI. Se documentó
  lo que hay (`incluir_inactivos`) y se dejó escrito que si alguna vez hace falta, tiene que nacer
  server-side.

---

## 2026-08-10 · La pantalla pública de carga de horas (`/horas`) · commit pendiente

**Qué cambió:** el módulo de carga de horas deja de ser backend sin puerta. Se construyó la
pantalla que faltaba entera. **La URL para los empleados es `https://www.hrkarstec.site/horas`.**

### 🔴 Un endpoint público NUEVO que el front hizo inevitable

`GET /api/horas-publico/clientes` — **la ruta pública número 9**. No estaba planificado y es una
ampliación de alcance de esta sesión: `cliente_id` es OBLIGATORIO en la carga y
`GET /api/clientes` exige JWT + `Seccion.CLIENTES`, que un empleado sin cuenta no tiene. **Sin
esta ruta el select nace vacío y la pantalla es decorativa.** Autenticada por el token de sesión
y acotada a la empresa del empleado; devuelve solo `{id, nombre}` — ni `empresa_id`, que es
justo el dato que la identificación se cuida de no dar.

### El token: `sessionStorage`

Sobrevive al refresh (el empleado carga varios renglones y no puede re-tipear el DNI) y muere al
cerrar la pestaña, que con el TTL de 30 minutos del backend es coherente. `localStorage` lo
dejaría vivo en una máquina compartida —el escenario real de este link—; memoria pura lo perdería
con cada F5. El motivo completo está en `components/features/horasPublico/sesionHoras.ts`.

### 🔴 Dos trampas que el front tuvo que esquivar

- **`fetch` directo, NO `apiFetch`.** `apiFetch` pasa por `conRefresh`, que ante un 401 intenta
  refrescar el JWT y si no puede **manda a `/login`**. Acá el 401 es el token del link: pasar por
  ahí le vaciaría la sesión de otro usuario del navegador a un empleado sin cuenta y lo dejaría
  en un login que no le sirve. Mismo motivo por el que `services/assessment.ts` hace lo mismo.
- **La sesión muerta se detecta por CODE, no por status.** Los DOS rechazos son 401
  (`SESION_INVALIDA` e `IDENTIFICACION_INVALIDA`). Mirar el status borraría una sesión sana por
  un dígito mal tipeado.

### ⚠️ El bloqueante de los 0 clientes: qué se puede mostrar y qué no

Verificado contra `identificacion_service._RECHAZO`: los cinco motivos de rechazo salen con el
MISMO code y mensaje, a propósito. **Desde el front NO se puede distinguir "tu empresa no tiene
clientes" de "el DNI no existe"** sin romper esa garantía. La salida que no la rompe es un
complemento **fijo**, mostrado siempre junto al rechazo: *"Si el número es correcto y sigue sin
funcionar, avisale a Recursos Humanos: puede que tu usuario todavía no esté habilitado."* Al ser
constante no filtra en qué caso está quien pregunta, y le da al empleado real la acción que sirve.

### ✅ El ciclo del barrido de huérfanos, cerrado

Las cuatro declaraciones del link estuvieron en `_ENDPOINTS_SIN_FRONT` **exactamente una tanda**.
El disparador escrito en su razón se cumplió y **el propio barrido pidió sacarlas**
(`test_las_excepciones_siguen_sin_caller` da rojo cuando algo declarado empieza a tener caller).

### Para infraestructura

- **Endpoints:** uno nuevo, **PÚBLICO**. Superficie sin auth: de 8 a **9 rutas** con el flag on.
- **Migraciones / variables de entorno / dependencias / Storage / CORS / Auth:** sin cambios.
- 🔴 **Sigue todo apagado por `HORAS_PUBLICO_ENABLED`,** y las dos precondiciones para encenderlo
  no cambiaron: `RATE_LIMIT_STORAGE_URI=redis://` y que RRHH cargue **al menos un cliente** —con
  0 clientes la identificación rechaza a todo el padrón.

---

## 2026-08-10 · 🔴 El barrido era ciego a los módulos apagados + GET de la semana · commit pendiente

### 🔴 LO IMPORTANTE: `test_callers_huerfanos` no veía nada detrás de un flag apagado

`rutas_backend()` importaba `main.app`, que se construye con la config por DEFAULT. Con
`ASSESSMENT_ENABLED` y `HORAS_PUBLICO_ENABLED` en `false`, esos routers **no se montan**, así que
el barrido no los veía. **Medido: veía 247 rutas de 254.**

**Consecuencia real, no teórica:** el link público de carga de horas se construyó ENTERO —tres
endpoints, cinco sesiones— sin una sola pantalla que lo llamara, y el barrido que existe
exactamente para detectar eso **nunca dio rojo**.

**La corrección** arma una app aparte con `registrar()` y **todo campo de `Settings` que termine
en `_enabled` puesto en True**. Es genérica: no nombra ningún flag, así que un módulo gateado que
se agregue mañana entra solo. No recarga `main` —construye una app nueva— para no dejar
`main.app` en un estado distinto según el orden de la suite, y une con las rutas reales porque
`/health` se declara en `main.py` y no en `registrar()`.

**Verificado por mutación**: revirtiendo el arreglo, el barrido falla desde la otra dirección
(las excepciones apuntan a rutas que ya no ve). Queda blindado en los dos sentidos.

**Los cuatro endpoints públicos quedan declarados** con la razón *"la PANTALLA es la sesión
siguiente"* y el disparador para borrarlas: que exista `app/horas/` en el front.

### El GET de "esta semana" — la ruta pública número 8

`GET /api/horas-publico/semana`. Autenticado por el **token de sesión**, nunca por el DNI: leer
con el DNI sería volver a la parte débil del flujo para devolver datos de una persona. El
empleado sale de la sesión; el endpoint no recibe ningún identificador de persona.

Devuelve lo mínimo —fecha, cliente, proyecto, tarea, horas, modalidad— **más las licencias del
período**, que el mockup también muestra. 🔴 **Sin `id`**: el empleado no puede editar ni borrar,
así que un id no le sirve y solo publicaría la clave de una fila en una ruta pública.

- **Semana lunes a domingo, decidida por el backend.** El endpoint NO acepta fechas: un rango
  libre lo convertiría en un lector del historial completo. Acotado a la semana, lo peor que
  puede leer un token robado son siete días — y el token vive 30 minutos.
- **Las licencias entran por SOLAPAMIENTO**: una del viernes al martes aparece en las dos semanas
  que cruza. Con contención desaparecería de las dos y la persona vería una semana que dice que
  trabajó cuando no lo hizo.
- ⚠️ **El token viaja en la query**, porque es un GET. Eso lo pone en access logs e historial —
  justo lo que se evitó con el DNI. La diferencia: el token es rotable y dura 30 minutos, el DNI
  es para siempre. Aun así es el punto más flojo de esta ruta, y por eso la ventana es fija.
- **`routers/horas_publico.py` se dividió** (estaba en 80/80): las dos escrituras se fueron a
  `routers/horas_publico_carga.py`, mismo prefijo, rutas sin cambios.

### Dos limpiezas

- **`HorasService.get_by_asignacion` BORRADO**, junto con `HorasRepo.find_by_asignacion`. Su
  declaración decía "esperando la reunión de definición"; esa reunión ocurrió y el link se
  construyó consultando por `empleado_id`, no por asignación. Verificado: **cero callers** en
  backend y front. No se reescribió la razón porque ya no había nada que preservar.
- **El encabezado de `db/schema.sql` decía "VA POR DELANTE DE PRODUCCION" y era FALSO.** Las
  migraciones 102..107 ya están corridas —verificado una por una contra el catálogo vivo: las
  tres tablas existen, `horas_proyecto` tiene `cliente_id` e `idempotencia`, `asignacion_id` es
  nullable y el tipo "Licencia" está sembrado; 63 tablas de los dos lados—. Corregido, con la
  nota de que ese bloque hay que moverlo en las DOS direcciones y que no hay test que lo cubra.

**Migraciones / variables de entorno / dependencias / Storage / CORS / Auth:** sin cambios.
El módulo público sigue apagado por `HORAS_PUBLICO_ENABLED`.

---

## 2026-08-09 · Vista interna "Horas por cliente" + división de `main.py` · commit pendiente

**Qué cambió:** la pantalla que RRHH usa para ver lo que se cargó: KPIs del mes, clientes
colapsables con el detalle por empleado, "ver detalle" día por día con borrado, filtros de mes y
empresa, y export. **Sin migraciones.** Todo lo público sigue apagado por `HORAS_PUBLICO_ENABLED`.

### 🔴 `main.py` se dividió — paso propio, con la suite verde antes y después

Estaba en 199/200 y esta tanda le sumaba un router. El inventario de los 50+ `include_router`
se fue a **`backend/registro_routers.py`**; `main.py` bajó a **65 líneas** y queda solo con lo que
nadie debe tocar a la ligera: el orden de los middlewares (que es load-bearing), los handlers de
error y el health check exento.

⚠️ **`registrar()` es una FUNCIÓN y los flags se leen ADENTRO.** Si los `if settings.*_enabled`
quedaran a nivel de módulo se evaluarían una sola vez al importar, y `importlib.reload(main)`
—que es como los tests prueban el gateo por flag— dejaría de verlos. El apagado de assessment y
del link público depende de eso.

### Endpoints nuevos (todos autenticados, gate `Seccion.PROYECTOS`)

`GET /api/horas-cliente` · `GET /api/horas-cliente/exportar` · `GET /api/horas-cliente/detalle` ·
`DELETE /api/horas-cliente/{hora_id}`.

**Ninguna sección de permisos nueva.** El dato son filas de `horas_proyecto`, cuyo gate publicado
ya es PROYECTOS. `Seccion.CLIENTES` gatea el CATÁLOGO, que es otra cosa; una sección nueva haría
que las MISMAS filas tengan dos gates según por qué pantalla se entre.

### 🔴 El DELETE no podía ir por `HorasService`

Ese valida por PROYECTO, y una carga del link público tiene `proyecto_id` NULL — o sea le habría
dado **404 a todas las filas que esta pantalla muestra**. La baja nueva valida por `empresa_id`,
que las dos formas de fila tienen NOT NULL, y audita con la empresa de la ENTIDAD.

### Los dos caminos de carga: se muestran los DOS

Las del link tienen `cliente_id`; las del camino viejo no. Filtrar por `cliente_id IS NOT NULL`
era lo cómodo en una pantalla que agrupa por cliente y **habría hecho desaparecer horas válidas en
silencio**. Van a un grupo **"Sin cliente"**, que además es la única forma de que RRHH vea que
existen. El KPI `clientes_con_carga` NO cuenta ese bucket.

### ⚠️ "Editar" NO se implementó, y es deliberado

`HorasService` declara los registros inmutables por decisión escrita. Lo que haría falta está
enumerado en `services/horas_cliente_service.py::_QUE_FALTARIA_PARA_EDITAR` — cinco puntos, de los
cuales dos son reglas de negocio que hoy no están decididas. Es una decisión de producto, no una
feature pendiente.

### Ajuste heredado de la sesión 1

`frontend/types/proyecto.ts` declaraba `costo` y `valor_hora_snapshot` como `number` y desde la
mig 103 pueden venir `null`. Corregido — y `tsc` encontró **dos usos reales** en `HorasTab.tsx`
que habrían impreso `$ NaN`. Ahora muestran "—": una carga sin snapshot no se puede costear, que
no es lo mismo que haber costado cero.

**Migraciones / variables de entorno / dependencias / Storage / CORS / Auth:** sin cambios.

---

## 2026-08-09 · Carga pública de horas y licencias (paso 2) · commit pendiente

**Qué cambió:** el empleado identificado ya puede cargar horas o una licencia. Se suman DOS rutas
públicas más (`POST /api/horas-publico/horas` y `.../licencia`), las reglas duras (30 días, tope
de 12 h sumando lo ya cargado) y la sesión que ata el paso 1 con el paso 2. **Todo sigue apagado
por `HORAS_PUBLICO_ENABLED`**; verificado: con el default, cero rutas montadas.

### 🔴 LA SUPERFICIE PÚBLICA PASA DE 5 A 7 (con el flag encendido)

`/health` · login · refresh · callback de Google · **identificar** · **horas** · **licencia**.

Pero las dos nuevas **NO son tan débiles como la identificación**: exigen un token de sesión de
256 bits (`secrets.token_urlsafe`), guardado hasheado y con TTL de 30 min. O sea **sí cumplen las
condiciones #1 y #2** que la identificación no puede cumplir. La debilidad del módulo queda
CONFINADA al primer paso: adivinar un DNI ya no alcanza para escribir.

### Migraciones — TRES, escritas y NO corridas

- **105 · `sesiones_horas`** `(id, token_hash, empleado_id, empresa_id, expires_at, created_at)`.
  Índice único sobre `token_hash` + **FK COMPUESTA `(empleado_id, empresa_id) → empleados(id,
  empresa_id)`** con `ON DELETE CASCADE`. Esa FK compuesta es la que garantiza EN LA BASE que el
  par de una sesión es coherente — sin ella una sesión podría decir "empleado de ACME, empresa
  DOSUBA" y todo lo escrito quedaría imputado a la sociedad equivocada. Sin `updated_at`.
- **106 · `horas_proyecto.idempotencia`** + índice único **parcial**. Cierra el doble tap.
- **107 · seed del tipo de ausencia "Licencia"** con **UUID FIJO**, global, `cuenta_ausentismo=true`.

🔴 **ORDEN: 102 → 103 → 104 → 105 → 106 → 107.** La 105 depende de `empleados`, la 106 de la 103
(la columna vive en la tabla que la 103 aflojó) y el service de licencias no funciona sin la 107.

### Cómo se resolvió la carrera del tope

Se partió en dos, porque tienen respuestas distintas:
- **El doble tap** (misma carga enviada dos veces) — 🟢 **CERRADO** con `idempotencia` + índice
  único parcial. El reenvío devuelve la carga ya creada, no un error.
- **Dos cargas DISTINTAS simultáneas** (dos pestañas) — 🔴 **DECLARADO COMO LÍMITE CONOCIDO.** Un
  trigger lo resolvería pero los triggers de negocio se dropearon repo-wide en la 058; PostgREST
  no expone transacciones; y un contador denormalizado por (empleado, fecha) se descartó porque
  habría que mantenerlo en sincronía desde todos los caminos —incluido el "editar y borrar" de la
  vista interna, que no existe todavía— y un total que driftea miente sin que nadie lo note,
  mientras que la carrera deja 16 horas VISIBLES y corregibles. 🚩 Se cierra en el cutover a
  AWS/asyncpg con `SELECT ... FOR UPDATE`.

### Las decisiones de la licencia

- Va a `solicitudes_ausencia`. **La 089 está CORRIDA** (verificado contra el catálogo:
  `uq_ausencia_empleado_rango_tipo` existe), así que el doble tap de licencia **ya está protegido
  en la base**; el service solo traduce ese choque a un 409 legible.
- **Tipo propio "Licencia"**, referenciado **por UUID y no por nombre**: `tipos_ausencia.nombre` lo
  edita RRHH desde configuración, así que buscar por texto se rompería con un renombre.
- **`justificada = False` siempre.** Un empleado no puede justificarse a sí mismo. ⚠️ **Consecuencia
  que hay que saber:** hasta que RRHH lo revise, estas licencias caen en la franja "injustificado"
  de `_reporte_ausentismo`. Significa "no revisada todavía", y no hay tercer estado porque la
  columna es booleana.
- **Sin `horas_contrato` se asumen 8 y se avisa** (`horas_por_dia_estimadas` viaja al cliente). La
  columna está 0/31: no dejar cargar dejaría la feature inservible para el padrón entero. 🚩 El
  arreglo de fondo es poblar `horas_contrato`; NO se parsea `empleados.turno`, porque "8 A 17" son
  9 h de reloj que valen 8 de trabajo y esa conversión es una convención que nadie definió.

### ⚠️ Brecha declarada en el tope de 12

`total_horas_del_dia` cuenta **por `empleado_id`**, o sea solo las cargas del link. Las del camino
viejo tienen `empleado_id` NULL (se llega por la asignación) y no entran en la suma. Se acepta
porque `horas_proyecto` tiene 0 filas y ese camino es de costeo de proyecto. 🚩 Revisar si el
camino viejo empieza a usarse.

**Variables de entorno:** ninguna nueva. **Dependencias / Storage / CORS / Auth:** sin cambios.

---

## 2026-08-09 · 🔴 LA QUINTA RUTA PÚBLICA: identificación por DNI · commit pendiente

**Qué cambió:** se agrega la primera ruta sin autenticación desde el callback de Google.
`POST /api/horas-publico/identificar` recibe un DNI y devuelve **solo el nombre de pila**. Es la
identificación del link público de carga de horas; la carga en sí es otra sesión. **Nace APAGADA
por flag y se entrega apagada.**

### 🔴 LO PRIMERO QUE INFRAESTRUCTURA TIENE QUE SABER

- **Variable de entorno NUEVA: `HORAS_PUBLICO_ENABLED`** (default `false`). Enciende la ruta.
  **Verificado: con el default, el router no se monta y la ruta no figura entre las públicas.**
  Encenderla es una decisión de producto y de seguridad, no de deploy.
- 🔴 **`RATE_LIMIT_STORAGE_URI=redis://…` PASA DE MEJORA A PRECONDICIÓN.** En las otras cuatro
  rutas públicas hay un autenticador real detrás (contraseña, refresh token rotativo, nonce de un
  solo uso) y el rate limit solo encarece el abuso. **Acá el rate limit ES la única defensa**, y
  con `memory://` el contador es por proceso: en serverless cada cold start arranca en cero y con
  N instancias el límite efectivo es N×. **No encender el flag mientras el store sea `memory://`.**
- **`TRUSTED_PROXY_HOPS` deja de ser solo cosmético.** La IP que sale de él es a la vez la clave
  del rate limit y lo que se guarda en el log de intentos. Mal configurado, todo el tráfico
  colapsa en un contador y el log guarda la misma IP para todos, o sea deja de servir para ver
  una enumeración.
- **Migración 104 — `intentos_identificacion`.** Tabla nueva, append-only. Escrita y **NO
  corrida**. Sin ella el endpoint funciona igual (el log se traga su error por diseño) pero se
  pierde la única forma de ver que alguien está probando DNIs. **Correrla ANTES de encender el flag.**
- **Endpoints:** uno, **PÚBLICO**. **Dependencias:** ninguna. **Storage:** ninguno.
  **Auth:** sin cambios en el token ni en los claims. **Jobs:** ninguno. **CORS:** sin cambios.

### Contenido de la migración 104

`intentos_identificacion (id, dni, resultado, empleado_id, empresa_id, ip, user_agent,
created_at)`. PK, CHECK de 6 valores para `resultado`, dos FKs con **ON DELETE SET NULL** (un log
que desaparece cuando se borra el objeto investigado no sirve) y tres índices: `created_at`,
`(dni, created_at)` y `(ip, created_at)` — las tres preguntas que la tabla existe para responder.
**Sin `updated_at`**, así que no lleva trigger y queda fuera del barrido de la 077 sola.

🔴 **El DNI se guarda EN CLARO, y es una decisión.** Un SHA-256 de 8 dígitos se revierte en
segundos (10⁸ hashes), así que no protegería nada, y destruiría la utilidad forense: el punto es
que RRHH pueda ver *qué* se intentó. 🚩 **PENDIENTE DE PRODUCTO: política de retención/purga.**
Hoy la tabla crece sin techo con identificadores de personas ajenas a la empresa.

### Lo que se hizo para que la ruta sea lo más segura posible dentro de la restricción

- **Payload mínimo:** solo el nombre de pila. Sin apellido, sin cargo, sin empresa — la empresa
  era el peor de los tres: al empleado no le sirve y a alguien enumerando le arma el mapa de la
  organización DNI por DNI. Tampoco vuelve el `empleado_id`.
- **Rechazo único con UN SOLO `raise` en todo el archivo.** Los cinco motivos (no existe, de
  baja, empresa sin clientes, DNI en dos empresas, bloqueado por límite) salen con el mismo
  status, code y mensaje. El log adentro sí los distingue.
- **Nivelación de timing.** Un DNI inexistente se resuelve con una query y uno que existe dispara
  dos; esa diferencia es medible y convierte el mensaje uniforme en decorativo. Toda respuesta
  espera un piso fijo de **300 ms**. 🚩 **Si cambia la latencia de la base (otro proveedor, otra
  región, el cutover a RDS) hay que RE-MEDIR ese piso**: uno que quedó corto no avisa, deja de
  nivelar en silencio.
- **Dos ejes de rate limit:** 10/min por IP (decorador, franja de "público sin auth") y 20/hora
  por DNI intentado. Son dos ataques distintos y ninguno cubre el del otro.

### ⚠️ Las dos condiciones que esta ruta NO cumple, y no puede cumplir

De las 8 que cumplen las cuatro rutas públicas actuales, fallan las dos primeras: **no tiene un
autenticador propio** (el DNI es un identificador enumerable, no un secreto) y **el valor que
viaja no es un nonce** de 256 bits con TTL y un solo uso (tiene que servir todos los días). Las
dos son consecuencia directa de la decisión de producto de no darle credenciales a los empleados.
Las otras seis se cumplen. **Esta ruta es, por diseño, la más débil de las cinco.**

---

## 2026-08-09 · ABM de clientes: service, routers, export, auditoría y pantalla · commit pendiente

**Qué cambió:** el catálogo de clientes pasa de ser solo modelo a ser usable por RRHH. Se cablea
lo que la sesión anterior dejó sin punta: `ClienteService`, router partido lectura/escritura,
export, auditoría de las tres escrituras, pantalla `/clientes` con su modal, ítem de sidebar y
sección de permisos propia. Sin migraciones nuevas.

### 🔴 Lo que infraestructura tiene que saber

- **Endpoints nuevos, ninguno público.** `GET /api/clientes`, `GET /api/clientes/exportar`,
  `GET /api/clientes/{id}`, `POST /api/clientes`, `PUT /api/clientes/{id}`,
  `DELETE /api/clientes/{id}`. Los seis pasan por `AuthMiddleware` y por
  `require_permission(Seccion.CLIENTES, …)`. El export lleva `shared_limit("30/hour",
  scope="export")` — comparte contador con todos los demás exports, no suma franja nueva.
- **Migraciones:** ninguna. Las 102 y 103 siguen **escritas y sin correr**, y este módulo las
  necesita: sin la 102 la tabla `clientes` no existe y los seis endpoints dan error de base.
  🔴 **Correr la 102 antes de habilitar la pantalla.**
- **Variables de entorno:** ninguna. **Dependencias:** ninguna. **Storage:** ninguno.
  **Auth:** sin cambios en el token ni en los claims. **Jobs / procesos largos:** ninguno.
  **CORS / dominios:** sin cambios.
- **`Seccion.CLIENTES` es nueva**, y toca los dos lados del espejo manual
  (`backend/utils/permisos.py` y `frontend/services/permisos.ts`). No hay que hacer nada del
  lado de infraestructura: los roles y sus capacidades no cambian — admin_rrhh escribe,
  gerencia_lectura lee, mandos_medios no accede, igual que en cualquier sección fuera de
  vacaciones/ausencias.

### Las dos decisiones que quedaron escritas

- **Sección propia y no reusada.** El precedente contrario es `/comunicacion`, que reusa
  `configuracion` porque era una ruta de front sobre endpoints que YA existían y ya estaban
  gateados. Clientes trae routers propios montados en `main.py`, que es justo la invariante que
  el enum declara ("una por módulo con router real"). El razonamiento completo está en el
  comentario de `Seccion.CLIENTES`.
- **La baja es LÓGICA (`activo=False`), no hay DELETE físico.** `horas_proyecto.cliente_id` es
  una FK **sin ON DELETE**: un borrado real de un cliente con horas cargadas no daría 409,
  reventaría contra la constraint y saldría como 500. Ese bug existe hoy en
  `proyectos_service.delete`, que chequea `has_horas` pero **no** las asignaciones — borrar un
  proyecto con equipo y sin horas pasa las dos validaciones y muere en la base. No se replicó.
  El endpoint `DELETE` igual responde 204: para quien consume la API el cliente deja de estar.

### ⚠️ Un hueco del barrido de exports, encontrado al usarlo

`tests/test_limite_export.py::EXPORTS` es una lista **explícita**, no por introspección, y su
guarda de mínimo (`>= 17`) no detecta un export nuevo que nadie agregó: `cliente_service` pasó el
barrido sin ser mirado hasta que se lo declaró a mano. Se agregó y se subió el mínimo a 18, pero
**el próximo export nace con el mismo agujero**. El de paridad list↔export (`test_paridad_list_export`)
sí descubre por introspección de `app.routes` y detectó el par de clientes solo.

---

## 2026-08-09 · Modelo de la carga de horas: tabla `clientes` + carga directa · commit pendiente

**Qué cambió:** solo MODELO (base, schemas y repos) del módulo de carga de horas. Dos migraciones
**escritas y NO corridas**: la **102** crea el catálogo `clientes` (por empresa, lo edita RRHH) y
la **103** habilita en `horas_proyecto` la carga que NO pasa por una asignación de proyecto. No hay
endpoints, ni pantallas, ni ruta pública, ni tope de horas, ni licencia: eso es la sesión siguiente.

### 🔴 Lo que infraestructura tiene que saber

- **Migración 102 — `clientes`.** Tabla nueva: `id, empresa_id, nombre, activo, created_at,
  updated_at`. PK, FK a `empresas` **sin ON DELETE**, índice único **case-insensitive**
  `(empresa_id, lower(nombre))` e índice por `empresa_id`. **Lleva trigger `updated_at`.**
  NO destructiva, idempotente.
- **Migración 103 — `horas_proyecto`.** Agrega `cliente_id`, `empleado_id`, `modalidad`,
  `proyecto_texto`, `tarea_texto`; pasa **`asignacion_id`, `proyecto_id` y `valor_hora_snapshot` a
  NULLABLE**; suma 2 FKs (a `clientes` y a `empleados`, sin ON DELETE), 2 CHECKs y 2 índices
  parciales. NO destructiva (aflojar un NOT NULL es compatible hacia atrás), idempotente.
- 🔴 **ORDEN OBLIGATORIO: 102 antes que 103.** La FK `horas_proyecto_cliente_id_fkey` apunta a
  `clientes`. Y por esa misma dependencia la 102 agrega su PK con un `DO $$ IF NOT EXISTS $$` en
  vez del `DROP CONSTRAINT + ADD` que usa la 086: con la FK ya creada, el DROP aborta.
- **Trigger `updated_at` de `clientes` declarado en los TRES archivos**, que es la regla que ya se
  incumplió dos veces (`usuario_integraciones` en la 032, `plantillas_mail` en la 087, arregladas
  después con la 091): la migración 102 (Supabase), `migracionAWS/.../077` (RDS, ahora 42 triggers)
  y `backend/db/schema.sql`.
- 🔴 **`backend/db/schema.sql` VA POR DELANTE DE PRODUCCIÓN hasta que las dos corran.** Declara 61
  tablas contra las 60 del catálogo vivo. Está así a propósito: es la fuente que leen
  `tests/_postgrest_schema.py`, `test_selects_repos.py` y `test_triggers_updated_at.py`, y un
  `select` que nombre `clientes` sin la tabla ahí hace fallar el barrido. El encabezado del archivo
  lista las diferencias vigentes.
- **Variables de entorno:** ninguna. **Dependencias:** ninguna. **Storage:** ninguno.
  **Endpoints:** ninguno (tampoco públicos). **Auth:** sin cambios. **Jobs / procesos largos:**
  ninguno.

### Lo que NO se rompe, verificado

El camino viejo (`POST /api/proyectos/{id}/horas`) queda intacto y cubierto de punta a punta.
Las filas de carga directa tienen `proyecto_id` NULL y **se caen solas** de las dos consultas que
miran esta tabla desde proyectos (`_proyectos_enrich.batch_costos` usa `.in_()`,
`ProyectosRepo.has_horas` usa `.eq()`, y un NULL no matchea ninguno de los dos): ni suman al costeo
de ningún proyecto ni bloquean ningún borrado. El CHECK `horas_proyecto_forma_check` fija que la
tabla tenga **exactamente dos formas de fila**, con lo que el estado mixto que reventaría
`batch_costos` con un `TypeError` deja de ser representable.

### ⚠️ Dos cosas para la sesión siguiente

- **`empleado_id` es una columna que el diseño no había enumerado y sin la cual no cierra:** hoy la
  tabla llega al empleado por `asignacion_id`, y sin asignación la fila quedaba sin dueño
  (`cargado_por` es FK a `users`, y `empleados.user_id` está 0/31).
- **El front todavía no acompaña.** `frontend/types/proyecto.ts` declara `costo` y
  `valor_hora_snapshot` como `number`, y desde la 103 el backend puede devolver `null` en los dos.
  Hoy no hay ruptura viva porque el único escritor publicado es el camino viejo, que siempre los
  completa — pero hay que ajustarlo antes de exponer la carga directa.

---

## 2026-08-09 · El error del proveedor deja de verse en la ficha del candidato · commit pendiente

**Qué cambió:** cuando el clasificador falla, RRHH veía el error crudo de Anthropic en la ficha —
en inglés, sin decir qué hacer, y con `request_id`, tipo de error y nombre de la API expuestos en
una pantalla de Recursos Humanos. Visto en producción con una corrida sin saldo. Ahora el motivo
que se persiste está en castellano y dice la acción; el detalle técnico va al log.

### Cuántas causas se pueden distinguir DE VERDAD

Verificado contra el SDK instalado (`anthropic==0.34.2`): **no existe `.type` en las excepciones**
—esa property es de SDKs posteriores—, así que la distinción sale de las CLASES. Con eso alcanza
para cuatro de las cinco categorías.

🟡 **La de saldo es la única que NO se puede distinguir por clase, y queda dicho.** El error de
facturación llega como `BadRequestError` (400) con `error.type='invalid_request_error'`: **el mismo
par exacto que una request malformada por un bug nuestro**. El único señalizador es el texto del
proveedor, así que se busca por marcas (`credit balance`, `billing`, `quota`…). Es best-effort y
**degrada bien**: si el wording cambia, el caso cae en `configuracion`, que igual manda a avisarle
a quien administra — la acción correcta con menos detalle. Y un 400 nunca cae en "reintentá":
reintentar un 400 no lo arregla nunca, y mandar a RRHH a apretar diez veces es peor que no decir
nada.

### Punto 4 — el barrido por la misma clase de fuga

Se barrió `services/`, `routers/`, `repositories/`, `integrations/` y `middleware/` buscando
excepciones crudas que lleguen al usuario. **El resto del sistema ya estaba bien**: Zernio, Gmail,
Google OAuth, el token de Google, Storage y el mailer levantan `AppError` con mensajes fijos en
castellano ("Error al consultar Gmail", "No se pudo enviar el mail"), y el handler global de 500
ya devuelve un mensaje fijo y loguea el detalle. El clasificador era el outlier porque su fallo
**se persiste** en vez de levantar, y nadie llevó el criterio hasta ese camino.

Tres de los cuatro candidatos restantes resultaron **falsos positivos**: `objetivos_import_preview`
y `evaluacion_import_service` reenvían `str(exc)`, pero lo que envuelven (`_import_excel.abrir`,
`_import_encoding.decodificar`) ya levanta NUESTRO propio mensaje en castellano y accionable.

🔴 **Uno era real y se arregló, por ser de una línea:** `nomina_csv_service.py:120` tenía un
`except Exception` alrededor de TODO el loop de parseo —**con los lookups a la base adentro**—, y
metía `{exc}` en una fila de error visible. Podía filtrar un error de httpx/Supabase a la pantalla.
El crudo ya estaba en el `logger.error` de la línea anterior, así que sacarlo no pierde nada.

**Impacto en infraestructura:**

- **Sin migraciones, sin endpoints nuevos, sin dependencias.** Es traducción de mensajes.
- **Código nuevo:** `services/_error_ia.py` (categoría + mensaje). `PREFIJO_FALLO` se mudó ahí
  desde `_screening_candidato` y se re-exporta, así que los callers no cambian.
- **El log del fallo ahora lleva `excepcion` (la clase) y `categoria`** además del `str(exc)`
  completo con su `request_id` — el log pasa a ser greppable por causa. **Nada de eso se perdió:
  hay un test que lo fija.**
- 🚩 **Operativo, no de código: la cuenta de Anthropic se quedó sin saldo.** Es lo que disparó
  esta sesión. Hasta que se recargue, toda corrida del clasificador falla y deja el motivo nuevo
  en cada candidato. Los candidatos quedan reintentables (clasificación en NULL).

**Mutación: 10 mutantes, 10 muertos**, incluido el sutil —concatenar el crudo *al final* del
mensaje traducido, que es como volvería a colarse en un refactor distraído.

---

## 2026-08-09 · El clasificador lee la búsqueda entera, no solo el título · commit pendiente

**Qué cambió:** el prompt del clasificador se armaba con `vacante.titulo` y `vacante.descripcion`,
y nada más. Los **cinco campos de "Información del puesto"** —funciones, requisitos, formación,
experiencia, conocimientos técnicos— **no llegaban al modelo**, ni el área. Ahora entran los
SIETE, cada uno con su rótulo.

🔴 **Era peor de lo que suena.** `descripcion` no tiene UI para cargarlo (la ficha lo oculta
cuando está vacío), así que el único campo con contenido que el clasificador leía era inalcanzable
para el usuario. En producción, la única vacante tiene los cinco campos cargados y `descripcion`
vacío: el prompt real decía `Puesto: Analista contable / Descripción: (sin descripción)`. **El
modelo clasificaba CVs contra un título y nada más**, mientras RRHH creía que estaba usando los
requisitos que había escrito.

### Las decisiones que quedaron escritas

🔴 **Cada campo con su rótulo, no concatenado.** "Excel avanzado" pesa distinto bajo *Requisitos*
que bajo *Conocimientos técnicos*, y "Contador Público" es otra cosa como *Formación* que como
*Funciones*. Los rótulos son **los mismos que muestra la UI**: si el prompt dijera "Requisitos
excluyentes" y el formulario dijera "Requisitos", el modelo estaría interpretando una exigencia
que nadie declaró.

🔴 **Los vacíos se OMITEN**, sin relleno tipo "(sin requisitos)". Y el system prompt ahora avisa
que las secciones son variables y que **de una ausencia no se infiere nada** — sin eso, un modelo
que ve tres de siete rótulos puede leer el hueco como una señal.

🔴 **Con solo título, la corrida se saltea entera** (`VACANTE_SIN_CONTENIDO`, 422). No se
clasifica igual: el modelo devolvería una de las tres categorías con un motivo redactado con
seguridad, y **un veredicto convincente derivado de nada no se distingue de uno fundado**. El
chequeo es por VACANTE y una sola vez por corrida, no por candidato: los N fallarían idénticamente,
así cuesta cero llamadas en vez de N y deja un mensaje sobre la búsqueda en lugar de N mensajes
sobre personas. 🚨 Va **después** de la barrera de empresa — un 422 sobre una vacante ajena
confirmaría que existe.

🔴 **Dos topes, no uno.** `MAX_CAMPO` 2.000 (para que un pegado de medio manual en *Funciones* no
deje *Requisitos* afuera) y `MAX_BLOQUE` 6.000 (acota el costo: este texto viaja en CADA llamada
del lote). Un truncado **se avisa dos veces**: dentro del prompt, para que el modelo no evalúe
media frase creyendo que es la frase entera; y en la respuesta del botón, porque quien tiene que
acortar la búsqueda es RRHH y no lee el prompt.

⚠️ `descripcion` se conserva, **último y solo si tiene contenido**: es legacy y hoy no hay dónde
escribirlo, pero queda contemplado si algún día se expone.

### Por qué pasó desapercibido, y qué lo impide ahora

**No había un solo test que mirara la forma del bloque `<busqueda>`** — grep de `busqueda>`,
`Puesto:` o `sin descripción` sobre `tests/` no devolvía nada. Y los fakes de vacante de todos los
tests se construían con `SimpleNamespace(titulo=..., descripcion=...)`: **reproducían el bug**, así
que sacar cinco de los siete campos pasaba en verde.

`tests/test_busqueda_prompt.py` (53 tests) ancla qué campos entran, con un fake
(`tests/_vacante_fake.py`) que trae los siete con frases **distintas y reconocibles**. Al agregar
el chequeo de contenido, **30 tests existentes se pusieron en rojo** porque sus vacantes falsas
solo tenían título y descripción — la prueba de que el fake venía tapando el problema.

**Mutación: 20 mutantes, 20 muertos.** Los siete campos sacados de `CAMPOS`, los siete
*declarados pero no renderizados* (la versión sutil, que es la que mide si las aserciones de
contenido muerden), más relleno en los vacíos, sin sanitizar, orden invertido, truncado sin aviso,
sin detección de vacante vacía, y `descripcion` primero. Cada campo lo nombra su propio test.

**Impacto en infraestructura:**

- **Sin migraciones.** Las siete columnas ya existían y ya llegaban al schema: el corte estaba en
  la firma de `clasificar()`, que tomaba dos strings sueltos teniendo el objeto disponible un
  escalón más arriba.
- **Código nuevo:** `services/_busqueda_prompt.py`. Firmas cambiadas: `clasificar()` y
  `armar_user()` toman la `VacanteResponse` entera.
- **Endpoint:** ninguno nuevo. `POST /api/screening/vacantes/{id}` ahora puede devolver **422
  `VACANTE_SIN_CONTENIDO`** y su respuesta suma `busqueda_truncada: bool`.
- **Costo por CV:** sube. Antes viajaban ~2 líneas de búsqueda, ahora hasta 6.000 caracteres
  (~1.500 tokens) por llamada, que se pagan una vez por candidato. Es el costo de que el modelo
  tenga contra qué comparar; el `MAX_BLOQUE` es lo que le pone techo.
- **Variables de entorno, dependencias, buckets, auth, CORS:** sin cambios.

---

## 2026-08-09 · Los tres huecos del CV screening · commit pendiente

**Qué cambió:** el módulo prometía tres cosas que no cumplía. (A) La clasificación **ya se puede
corregir a mano**, y la corrección queda marcada como humana y auditada individualmente. (B) El
**fallo del clasificador ahora persiste** y se distingue en pantalla de "todavía no se clasificó"
y de "el CV no se pudo leer". (C) Se puede **abrir el CV desde la ficha de la vacante**, que es
donde ocurre todo el flujo del screening.

### Las decisiones que quedaron escritas

🔴 **Cómo se registra que corrigió un humano: columna + evento, y ninguno sobra.**
`clasificacion_origen` ('modelo'|'humano') se escribe en el MISMO update que la clasificación —
`AuditService` se traga los errores por diseño, así que si el único marcador fuera el evento, un
insert fallido volvería a mezclar la corrección con las del modelo sin que nadie se entere; y la
pregunta "¿cuántos los puso el modelo?" es un filtro sobre `candidatos`, no sobre `auditoria`.
El **evento** hace falta igual porque la corrección PISA `clasificacion_ia`: el veredicto original
del modelo solo sobrevive en `datos_anteriores`, y sin ese par no se puede medir en qué dirección
se equivoca el filtro.

🔴 **El fallo se persiste en `clasificacion_motivo` con la clasificación en NULL, NO en
`screening_warning`.** Aquella columna **gatea el salteo**: escribir el fallo ahí lo volvería
permanente e irreintentable, justo al revés de lo que hace falta. Con `clasificacion_ia` en NULL,
`find_para_clasificar` lo vuelve a tomar solo. Y significan cosas distintas: `screening_warning`
es "el archivo no se pudo leer" (pedir otro CV) y esto es "la llamada falló" (reintentar).

🔴 **Una corrección no la pisa ninguna corrida posterior**, porque `find_para_clasificar` filtra
`clasificacion_ia IS NULL`. No es un efecto lateral afortunado: es la garantía que hace que
corregir valga la pena, y tiene test propio.

⚠️ **`CandidatoCard` perdió `cursor-pointer` y `hover:shadow-md`**: nunca tuvo `onClick`, así que
prometía un click inexistente. Las acciones ahora son botones explícitos debajo.

### Divisiones

`cv_screening_service.py` 149/150 → **131** (`_screening_candidato.py`, 76) ·
`routers/screening.py` 75/80 → **61** (`routers/screening_criterio.py`, 52; **las URLs no
cambiaron**). Las dos con la suite verde antes de seguir.

🚩 Al extraer `_uno`, la escritura salió del alcance de `test_auditoria_coherente` —que solo mira
módulos que YA emiten eventos— y su excepción declarada se borró (el barrido lo exigió). La regla
"un evento por lote" no cambió; lo que se perdió es que un barrido la vigile. Queda escrito en el
encabezado de `_screening_candidato.py`.

### Mutación: 8 mutantes, 3 sobrevivieron a la primera vuelta

Los tres eran el mismo error: los fakes de repo implementaban `set_correccion`, `set_fallo` y
`find_para_clasificar` a mano, así que los tests afirmaban sobre el FAKE y no sobre el repo.
Sobrevivían: marcar la corrección como 'modelo', que el fallo cayera a 'dudoso', y sacar el
`.is_("clasificacion_ia","null")`. Se cerró con `TestLoQueEscribeElRepoDeVerdad`, que faltea el
cliente de Supabase y captura lo que el repo manda (molde: `TestElOrdenLoPoneLaQuery`). Los 8
mueren.

**Impacto en infraestructura:**

- 🔴 **Migración 101 (`101_clasificacion_origen.sql`) — PENDIENTE.** No destructiva, idempotente.
  Agrega `candidatos.clasificacion_origen` con CHECK ('modelo','humano') y **backfillea a
  'modelo' las filas que ya tenían clasificación**. **Va DESPUÉS de la 100.** La cola pendiente
  es ahora **095 → 096 → 097 → 098 → 099 → 100 → 101**, en ese orden.
- **`db/schema.sql`** actualizado con la columna y su CHECK.
- **Endpoint nuevo (1, con auth):** `PUT /api/screening/candidatos/{candidato_id}/clasificacion`
  (`Seccion.CANDIDATOS + WRITE`). **Sin rate limit propio, a propósito**: no gasta tokens, y
  limitar a un humano que revisa de a uno castigaría justo el uso que el módulo pide.
- **Router nuevo:** `routers/screening_criterio.py`, montado en `/api/screening/criterio`. Es una
  división del anterior: **ninguna URL cambió**.
- **Variables de entorno, dependencias, buckets:** ninguna nueva. Auth, CORS y dominios sin cambios.
- **Export de candidatos:** columna nueva **"Clasificado por"** (Sistema | Revisión manual).
- **`docs/PLAN-DE-TRABAJO.md` §F2.4 reescrito:** describía `crear_candidato_desde_email` como bug
  vivo y proponía una migración 093 con `UNIQUE (empresa_id, gmail_message_id)`. Esa función se
  borró, la migración salió como **098** y la clave lleva además `cv_sha256` (la unidad es el CV,
  no el mail). No se borró la entrada: dice cómo quedó.

---

## 2026-08-09 · Clasificador de CVs (fase 3 de 3 del screening) · commit pendiente

**Qué cambió:** cada CV que entra se clasifica contra su vacante en **relevante / dudoso /
no_relevante**, con un motivo en una frase. Es un **filtro de descarte, no una decisión**: no
rankea, no puntúa, no elige, y un humano revisa siempre —incluidos los `no_relevante`, que la
pantalla no oculta ni colapsa—. El criterio de las tres categorías es configurable por empresa
desde /configuracion, con restauración a los valores generales. Se corre desde un botón propio en
la vacante, NO desde la ingesta de mails.

**Impacto en infraestructura:**

- 🔴 **Migración 100 (`100_cv_screening_clasificacion.sql`) — PENDIENTE, no corrida.** No
  destructiva e idempotente. Agrega `candidatos.clasificacion_ia` (TEXT nullable con CHECK de las
  tres categorías) y `candidatos.clasificacion_motivo`, más un índice parcial; y crea la tabla
  **`parametros_screening`** (criterio configurable, `empresa_id NULL` = fila global, dos índices
  parciales, trigger `updated_at`, fila global sembrada con los defaults). **Va después de la
  099**, que también sigue pendiente.
- 🔴 **`db/schema.sql` estaba desactualizado y se corrigió**: le faltaban `cv_texto` y
  `screening_warning` de la **migración 099** (la sesión anterior no lo tocó). Ahora refleja 099 y
  100. Quien reconstruya desde cero no puede usar una copia previa a hoy.
- 🔴 **`migracionAWS/.../077_recrear_triggers_updated_at.sql`**: se le agregó el trigger de
  `parametros_screening`. Sin eso, la reconstrucción en RDS dejaría esa tabla con `updated_at`
  congelado en el alta — corrupción silenciosa, que es justo lo que la 077 vino a evitar.
- **Variables de entorno:** ninguna nueva. Usa el `ANTHROPIC_API_KEY` que ya existe.
- **Dependencias:** ninguna nueva. Usa el `anthropic==0.34.2` ya fijado.
- **Modelo de IA:** `claude-haiku-4-5` (alias **sin fecha**, ver la mina ya desactivada de los
  strings con fecha). Es el segundo consumidor real de Anthropic después de `reporte_adhoc`.
- **Endpoints nuevos (4, todos con auth):** `POST /api/screening/vacantes/{vacante_id}` ·
  `GET|PUT /api/screening/criterio` · `POST /api/screening/criterio/restaurar`. Router propio
  montado en `main.py` con prefijo `/api/screening`. Ninguno público.
- ⏱️ **Rate limit propio del botón: 20/hora** (`limiter.limit`), mismo criterio y mismo número que
  `POST /reportes/generar`: cada corrida son N llamadas a Claude y cada una cuesta plata.
- **Serverless:** la corrida tiene **presupuesto de tiempo propio de 240 s** (`_presupuesto.py`),
  por debajo del `maxDuration: 300` de `vercel.json`, más un **tope de 200 CVs por corrida**. Los
  dos cortes se REPORTAN (`parcial`, `tope_alcanzado`, `sin_procesar`) y son reintentables: el
  backend pide `clasificacion_ia IS NULL`, así que volver a apretar el botón no reclasifica ni
  recobra nada ya hecho. **No corre en la ingesta de mails a propósito** — aquella ya usa sus
  240 s en Gmail y Storage, y sumarle N llamadas al modelo la cortaría a la mitad.
- **Costos:** el control es el tope por corrida + los topes de entrada/salida (20.000 caracteres
  de CV, 300 tokens de respuesta), **no** un cupo diario por usuario. El `check_usage_limit` de
  `SEGURIDAD-PENTEST.md` §6.2 defiende la repetición del usuario, que acá ya está cerrada por
  idempotencia; además su `usage_repo` no existe en el repo.
- **Buckets de Storage:** ninguno nuevo.
- **Auth / claims / CORS / dominios:** sin cambios.

---

## 2026-08-09 · Extracción del texto de los CVs (fase 2 de 3 del screening) · commit pendiente

**Qué cambió:** los CVs que entran ahora se leen. El texto queda en `candidatos.cv_texto` y, si no
se pudo, el motivo en `candidatos.screening_warning`. Es la ENTRADA del clasificador (fase 3).

🔴 **MIGRACIÓN 099 — NO CORRIDA.** Pendientes: 095, 096, 097, 098 y 099.

### La dependencia nueva, verificada antes de fijarla

`pypdf==5.1.0`: wheel **`py3-none-any`** (297 KB, 1,16 MB descomprimido), **sin binarios
nativos** —así que `@vercel/python` no compila nada— y **cero dependencias obligatorias en 3.11+**
(el único `Requires-Dist` sin extra es `typing_extensions`, y solo para `python<3.11`). Licencia
**BSD**. PyMuPDF quedó descartado por AGPL.
⚠️ Los PDF cifrados con AES necesitan `cryptography`, que **ya está** por `PyJWT[crypto]` y
`python-jose[cryptography]` (49.0.0 instalada). No se agregó el extra `pypdf[crypto]` para no
duplicar el pin.

### Las decisiones que quedaron escritas

🔴 **`screening_warning` es TEXTO, no un booleano.** Un flag obliga a abrir el archivo para saber
qué pasó, que es el trabajo que esto viene a evitar. Los motivos no son intercambiables: "protegido
con contraseña" → pedirle la contraseña; "formato .doc" → pedirlo en PDF; "sin texto extraíble" →
es un escaneo, abrirlo a mano. Cada uno tiene una acción distinta.
🔴 **Tope de 20.000 caracteres (~5.000 tokens).** Esto viaja a Claude y los tokens se pagan: un CV
de 15 páginas pasa los 40.000 y el excedente casi nunca decide una preselección. **Se trunca, no
se descarta**, y el truncado se avisa. Constante de módulo, no env var — subirlo es una decisión
de costo.
🔴 **Piso de 200 caracteres** para llamarlo legible: un escaneo devuelve basura corta (un número de
página), no vacío, así que "hay algo" no sirve como criterio.
⚠️ **Sin OCR y sin `.doc` viejo**, los dos a propósito: Tesseract son ~50 MB y binarios nativos;
`.doc` pide `antiword` o `textract` para un formato que Word exporta a PDF en dos clicks.
⚠️ **`cv_texto` NO se expone en `CandidatoResponse`**: pesa hasta 20 KB por fila y engordaría todos
los listados sin que nadie lo mire. Solo viaja `screening_warning`.

Se engancha en `_cv_alta.py`, el módulo que ya comparten la ingesta automática y la asignación
manual — **una sola implementación**. El texto viaja en el MISMO INSERT (los bytes ya están en
memoria), así que no hay un update posterior que pueda fallar y dejar al candidato mudo.

### 🔴 DOS BUGS ENCONTRADOS Y ARREGLADOS, los dos míos de esta sesión

1. **`extra={"filename": ...}` en un `logger.warning` levanta `KeyError`.** `filename` es un
   atributo RESERVADO de `LogRecord`; pasarlo en `extra` explota **dentro del manejador de
   errores**, o sea justo cuando algo ya salió mal. Es la misma familia que el `user_id` muerto en
   un `logger.error` de la sesión 3B. Barrí el backend entero por AST buscando las 20 claves
   reservadas en `extra=`: **era el único**. Corregido a `archivo`.
2. **El warning genérico pisaba al específico.** Un PDF cifrado devuelve texto vacío, así que caía
   en la rama de "menos de 200 caracteres" y salía como "sin texto extraíble" — perdiendo el
   motivo justo en el caso donde más sirve. Ahora el aviso específico gana. Lo encontró el test.

### Verificación

**Siete mutaciones:** el archivo roto propaga → **22 rojos** · el genérico pisa al específico
(el bug 2) → **1** · sin tope de tamaño → **1** · el docx no lee tablas → **1** · el motivo del
`.doc` se vuelve genérico → **1** · el mapper descarta el warning → **1** · el texto no se
persiste → **2**.

🔴 **Los PDF de los tests son PDF de verdad**, generados con `reportlab` (que ya estaba) y cifrados
con `pypdf`. Ni un mock: un doble que devolviera `"texto de prueba"` no puede desmentir si el
parser está bien invocado, si el cifrado se detecta o si un truncado revienta.
🔴 **El test del lote usa DOS CVs, uno bueno y uno roto.** Con uno solo, "el lote sigue" y "el lote
se cortó" son indistinguibles — las dos implementaciones dejarían 0 o 1 candidato.

**Backend 2844 passed, 0 skipped** (eran 2823; +21). Los ocho barridos: **487**. `tsc --noEmit` en
**0**, front **523 passed, 0 skipped**. `ruff F401/F811/F821` limpio.
✅ De paso bajaron los warnings de la suite de 5 a **3**: un docstring no-raw con `\\d` que había
quedado en `test_cv_matcher.py`.
⚠️ `CandidatoDetailPanel.tsx` llegó a 154/150 al sumarle el aviso → salió `CandidatoCv.tsx`; quedó
en **145**. `_cv_texto.py` **140/150** y `_cv_pendientes.py` **135/150**: poco margen.

**Impacto en infraestructura:**
- 🔴 **Migración 099 PENDIENTE.** Dos columnas nullable, no destructiva, en transacción. Sin
  backfill (`candidatos` está en 0). **El backend la necesita corrida antes de deployar**: sin las
  columnas, el INSERT del candidato falla.
- 🔴 **DEPENDENCIA NUEVA DE PRODUCCIÓN: `pypdf==5.1.0` en `requirements.txt`.** Es la primera de
  esta rama del proyecto que va al runtime. Pura Python, sin build step; el deploy de Vercel no
  necesita nada extra. Para AWS, lo mismo: entra en el `pip install` normal.
- ⚠️ **Costo de CPU en la ingesta**: parsear un PDF de varias páginas son décimas de segundo por
  archivo. Entra dentro del presupuesto de 240 s de la corrida, pero se suma al de red — si el
  lote empieza a cortarse por tiempo, este es el segundo sospechoso después de Gmail.
- Sin variables de entorno, buckets ni endpoints nuevos.

---

## 2026-08-09 · Fase 6: los CVs sin match pasan a ser utilizables · commit pendiente

**Qué cambió:** un CV que no matcheó ninguna vacante ahora se puede asignar. Antes se veían los
huérfanos y no había NINGUNA forma de asignarlos — ni endpoint, ni método de repo, ni UI.

### 🔴 LA VERIFICACIÓN DE VIABILIDAD, ANTES DE IMPLEMENTAR

El diseño (no persistir los pendientes, releer la casilla) dependía de poder saber qué
`message_id` ya se procesaron **sin bajar sus adjuntos**. **Tal como estaba, NO se podía**: el
chequeo de idempotencia (`existe_cv_de_gmail`) corre DESPUÉS de descargar, porque su clave es el
sha256 del CONTENIDO. Releer la casilla habría re-descargado todo lo ya resuelto en cada apertura.

Lo que lo vuelve viable, y por eso el diseño se sostiene: `candidatos.gmail_message_id` **ya tiene
índice** (mig 098), así que una query batch `.in_(...)` sobre los ≤50 ids listados responde
"¿cuáles ya se procesaron?" antes de tocar la red. Y para ESTA pantalla la granularidad por
mensaje es **exacta**, no una aproximación: un pendiente es por construcción un mail que creó
CERO candidatos.
⚠️ **La ingesta automática CONSERVA su chequeo por sha**, y la diferencia importa: ahí un mail sí
puede quedar procesado a medias (un CV creado y otro fallado), y saltearlo entero por mensaje
perdería el segundo para siempre. Son dos métodos distintos a propósito
(`_candidato_gmail.existe_cv` vs `message_ids_procesados`).

**Efecto colateral buscado:** "cuántos adjuntos válidos trae" se cuenta con lo que el mensaje ya
declara (`filename`, `mimeType`, `body.size` — lo mismo que mira `cv_service.validar`), así que la
pantalla cuesta **N+1 llamadas y CERO descargas**. Los bytes recién se piden al asignar.

### Las divisiones (paso propio, suite verde antes de seguir)

`candidato_repo.py` estaba en **100/100 exacto**: salieron el write path a `_candidato_write.py` y
las dos lecturas de la ingesta a `_candidato_gmail.py` → **94**. Y `_cv_ingesta_mail.py` cedió el
alta a **`_cv_alta.py`**, que es exactamente lo que comparten los dos caminos: desde que hay
vacante para adelante, la ingesta automática y la asignación manual no tienen una sola diferencia.
`cv_ingesta_service` se partió además en un `cv_pendientes_service` propio — son casos de uso
distintos (procesar sola la casilla vs mostrarle a RRHH lo que quedó afuera).

### Lo nuevo

**Pantalla de pendientes** (`MailsPendientes`, en el listado de vacantes): remitente, asunto,
fecha, cuántos CVs trae y por qué no matcheó, con selector de búsqueda y botón de asignar. Un mail
con 0 CVs válidos no se puede asignar — no crearía nada.
**Al asignar**: mismo orden y mismo criterio que la ingesta (`_cv_alta.crear_de_un_cv`), con la
empresa **de la vacante elegida**. Un mail con varios CVs crea varios candidatos sobre la misma
búsqueda.
**Filtro "sin vacante asignada"** en listado Y export, con el `.is_("vacante_id","null")` **en el
WHERE** y el traductor único `queryCandidatos` en `services/candidatos.ts` (que no existía; molde
`queryVacantes`). `test_paridad_list_export` pasaba TRIVIALMENTE mientras candidatos no tenía
ningún query param — ahora tiene uno y el barrido lo verifica de verdad.
**Asignar un candidato ya creado**: `PUT /api/candidatos/{id}/vacante`.
🔴 **La barrera son DOS comprobaciones y las dos hacen falta**: que el candidato sea alcanzable
desde el header, y que la vacante sea **de la empresa del CANDIDATO** — esto último no se puede
delegar al header, porque en modo consolidado vale `None` y no restringe nada. Sin ese chequeo se
podría mover un candidato de Karstec a una búsqueda de Dosuba.

### Verificación

**Siete mutaciones:** no saltear los procesados → **2 rojos** · saltear DESPUÉS de pedir el
mensaje (mismo resultado, doble costo) → **1** · la vacante deja de validarse contra la empresa
(en los dos caminos) → **1 + 1** · el filtro sale del WHERE → **1** · contar todos los adjuntos en
vez de los que parecen CV → **2** · reasignar a alguien que ya tiene búsqueda → **1**.

🔴 **El fake tiene un mail YA procesado y otro no.** Con uno solo, "saltea" y "trae todo" son
indistinguibles. Y **cuenta las llamadas a Gmail**: la mutación 2 produce la misma lista con el
doble de costo, así que sin afirmar sobre `mensajes_pedidos` pasaría desapercibida. El fake de
candidatos trae con vacante y sin vacante — con solo huérfanos, el filtro no se puede desmentir.

**Backend 2823 passed, 0 skipped** (eran 2793; +30). Los ocho barridos: **487**. `tsc --noEmit` en
**0**. Front **523 passed, 0 skipped** (+1, explicado: el barrido `loadingSeApaga` descubrió
`MailsPendientes.tsx` — verificado en su reporte). Rutas **226 → 229** (+3). Gate ejercitado:
`/casilla/pendientes` es READ (pasa gerencia_lectura), las dos escrituras dan **403** para todo lo
que no sea admin.
⚠️ `_cv_pendientes.py` **135/150**, `routers/vacantes_integraciones.py` **77/80** y
`CandidatoDetailPanel.tsx` **145/150**: poco margen.
⚠️ `vacantes/page.tsx` 174 → **178**: deuda previa declarada.

**Impacto en infraestructura:**
- **Sin migraciones nuevas.** Usa las columnas y los índices de la 098, que **sigue pendiente**
  junto con 095, 096 y 097.
- **Endpoints nuevos (3):** `GET /api/vacantes/casilla/pendientes` (READ),
  `POST /api/vacantes/casilla/asignar` (WRITE), `PUT /api/candidatos/{id}/vacante` (WRITE).
- **Query param nuevo** `sin_vacante` en `GET /api/candidatos` y `/exportar`.
- ⚠️ **La pantalla de pendientes pega a Gmail en cada apertura** (1 + N mails no procesados). No
  baja adjuntos, pero es tráfico contra la API: si el volumen crece, el techo es la cuota de
  Gmail, no el nuestro.
- Sin variables de entorno, dependencias ni buckets nuevos.

---

## 2026-08-09 · Fase 5: el matcher y la creación del candidato con su CV · commit pendiente

**Qué cambió:** el flujo entero de ingesta. Un botón lee la casilla del sistema, busca el código
de vacante en el asunto de cada mail, baja los adjuntos válidos y crea un candidato por CV con su
archivo en Storage.

🔴 **MIGRACIÓN 098 — NO CORRIDA. La corre Franco.** Pendientes: 095, 096, 097 y 098.

### La migración

`candidatos.gmail_message_id` + `cv_sha256` (los dos nullable), índice único **parcial**
`(empresa_id, gmail_message_id, cv_sha256) WHERE ... IS NOT NULL`, y `'gmail'` sumado al CHECK de
`fuente` (sin eso el INSERT falla y el CV se pierde). No es destructiva: amplía el CHECK, no lo
restringe.

🔴 **La clave es el HASH del contenido, no el `attachmentId`.** El candidato obvio era
`(empresa_id, gmail_message_id, attachment_id)` y **no sirve**: el `attachmentId` está scopeado a
UNA lectura del mensaje, así que la segunda corrida traería otro valor, la constraint no chocaría
y se crearía el duplicado. Compila, se lee razonable y no protege nada.
⚠️ **El índice es parcial y tolera NULLs**: los candidatos cargados a mano no tienen ninguno de
los dos campos, y en Postgres dos NULL no son iguales, así que N candidatos manuales conviven. El
`WHERE` deja escrita la intención para que nadie lo "corrija" a `NULLS NOT DISTINCT` y rompa el
alta manual desde el segundo candidato.

### El matcher (`_gmail_matcher.py`)

Permisivo en la escritura: `vac-0001`, `VAC 0001`, `VAC0001`, `[vac-0001]`, con texto alrededor.
Quien escribe el asunto copia de un aviso desde el teléfono; exigir el formato exacto manda a
revisión manual CVs que traen el código a la vista, y eso no falla con un error.
🔴 **Pero se exigen 4 dígitos como mínimo, y ahí la permisividad se corta.** `VAC-12` NO se
completa a `VAC-0012`: eso haría que un código tipeado a medias resuelva **a otra vacante real**.
Un CV en la búsqueda equivocada no da error y no se detecta nunca.
🔴 **Dos códigos distintos → sin match.** Elegir el primero es una decisión invisible sobre la
carrera de alguien. El mismo código repetido NO cuenta como dos (`[VAC-0001] re: vac 0001` es uno).

### El flujo

`_cv_ingesta_mail.procesar_mail` copia el orden de `_vacante_candidatos.agregar`: validar → crear
→ subir → `set_cv`, y **si Storage falla después de crear, el candidato se conserva sin CV**.
Revertirlo perdería la postulación entera por un problema de disco.
🔴 **Sin match NO se crea nada.** `candidatos.empresa_id` es NOT NULL y sin vacante no hay de
dónde heredarla — el remitente es alguien de afuera. El mail queda listado como pendiente con su
motivo (`sin_codigo`, `codigo_ambiguo`, `vacante_desconocida`, `sin_adjuntos`, `sin_cv_valido`).
🔴 **Un evento de auditoría POR LOTE**, con `empresa_id=None` porque una corrida puede tocar
vacantes de varias empresas. Molde: `payload_importacion_nomina`, no el de costos.

### El presupuesto de tiempo (P2 del plan, ya no postergable)

Se extrajo `services/_presupuesto.py` de `_lote_mails.py` y ahora lo usan los dos. Son 2+ llamadas
a Gmail por CV y `vercel.json` corta a los 300 s sin decir cuál mitad quedó hecha; con presupuesto
se chequea el margen antes de cada mail y se reporta `parcial` + `sin_procesar`. La idempotencia
hace el resto: apretar de nuevo completa el lote sin duplicar.
⚠️ **Queda una TERCERA copia sin migrar: `_nomina_lote.py`.** Mismo cálculo, otro vocabulario. Es
el próximo caller natural; no se tocó por alcance.

### 🔴 El botón nuevo REEMPLAZA al viejo — y eso borró código

`get_emails_candidatos` y `crear_candidato_desde_email` (con sus 2 endpoints, `EmailsSection.tsx`,
`EmailCandidatoRow.tsx` y `test_gmail_candidatos.py`) **se borraron**. No conviven dos criterios
sobre la misma casilla: el viejo listaba con `format=metadata` —que ni siquiera trae los
adjuntos— y decidía qué era una postulación con `_is_cv_email`, un filtro por palabras clave que
descarta en silencio mails que sí traen el código. `gmail_service` quedó con lo que no dependía
de ese caso de uso —hablar con la API— y bajó de 148 a **97**.
⚠️ Los tests del parseo del `From` NO se fueron con él: la función sigue viva y ahora corre sobre
TODOS los mails. Se movieron verbatim a `test_gmail_from_header.py`.
⚠️ El botón vive en el LISTADO de vacantes, no en la ficha: la corrida es sobre la casilla entera
y cada mail elige su búsqueda por el código. Una pasada puede tocar varias vacantes de empresas
distintas.

### Verificación

**Seis mutaciones:** la clave pasa a ser el `attachmentId` → **2 rojos** · el matcher exige el
formato canónico → **4** · acepta menos de 4 dígitos → **3** · con dos códigos elige el primero →
**1** · un fallo de Storage tumba el alta → **1** · un evento de auditoría por mail → **1**.

🔴 **El fake de Gmail devuelve un `attachmentId` DISTINTO en cada lectura con los MISMOS bytes.**
Es lo que hace que el test de idempotencia pruebe algo: con un id estable, la implementación
correcta y la que usa el attachmentId como clave son indistinguibles. El fake de candidatos
modela el índice único, no solo la escritura.

✅ **`test_callers_huerfanos` cerró el ciclo que quedó escrito**: las declaraciones de
`descargar_cvs` y `find_by_codigo` decían "borrar al conectarlo" — se conectaron y se borraron.
`codigo_unico` nació sin caller y se borró en vez de declararse.
✅ **`vacante_repo.find_by_ids` (punto 6) pasó a tener datos con esta sesión** y se cubrió. Su
declaración decía "urgente con la primera vacante con candidatos": el disparador se cumplió.

**Rutas 226 → 226**: +2 (`/casilla/revisar`, `/aviso`) −2 (los dos viejos). Gate ejercitado sobre
`app.routes`: **403** para gerencia_lectura, mandos_medios y sin rol.
**Backend 2793 passed, 0 skipped** (eran 2761; +32). Los ocho barridos: **486**. `tsc --noEmit` en
**0**, front **522 passed, 0 skipped**. `ruff F401/F811/F821` limpio sobre todo lo tocado (los 11
hallazgos del repo son preexistentes, en archivos que esta sesión no abrió).
⚠️ `_gmail_adjuntos.py` **148/150** y `candidato_repo.py` **100/100**: sin margen.
⚠️ `vacantes/page.tsx` 170 → **174**: deuda previa declarada.

**Impacto en infraestructura:**
- 🔴 **Migración 098 PENDIENTE.** No destructiva, en transacción, sobre una tabla con 0 filas.
  **El backend la necesita corrida antes de deployar**: sin `'gmail'` en el CHECK de `fuente`, la
  primera ingesta falla al insertar.
- **Endpoint nuevo:** `POST /api/vacantes/casilla/revisar`, autenticado, gate `VACANTES + WRITE`.
  **Dos endpoints borrados** (`GET /{id}/emails-candidatos`, `POST /{id}/candidatos-desde-email`).
- ⚠️ **Requisito operativo:** la ingesta EXIGE una casilla designada como remitente del sistema y
  el scope `gmail.readonly` ya concedido. Hoy los dos están.
- ⚠️ **Duración:** la corrida puede tardar minutos con 50 mails. El presupuesto es de 240 s contra
  el `maxDuration: 300` de `vercel.json` — si ese techo baja, hay que bajar `PRESUPUESTO_SEGUNDOS`.
- Sin variables de entorno, dependencias ni buckets nuevos (usa `cvs`, que ya existía).

---

## 2026-08-09 · Los 5 mappers sin ejercitar que sí tenían riesgo (18/22) · commit pendiente

**Qué cambió:** SOLO TESTS. **Cero código de producción tocado.** Se cerraron los 5 mappers con
riesgo real de los 9 que quedaban; los otros 4 quedan declarados con el disparador que los
volvería urgentes.

### La clasificación, con evidencia del catálogo vivo (9/8/2026)

**CON DATOS HOY → urgente (cubiertos):**
| Mapper | Tabla | Filas |
|---|---|---|
| `evaluacion_repo.find_resultados_por_evaluados` | `evaluacion_resultados` | **307** |
| `audit_repo._build` | `auditoria` | **143** |
| `proyecto_asignaciones_repo._build` | `proyecto_asignaciones` | **31** |

**VAN A TENER DATOS EN EL BLOQUE I → importante (cubiertos):**
`_vacaciones_utils.enriquecer` (`solicitudes_vacaciones` 0) · `inventario_asignaciones_repo._build`
(`inventario_asignaciones` 0). Se cubren **antes** de que haya datos a propósito: es la situación
exacta en la que estaba `_ausencia_row` cuando se le encontró el `NameError`. Esperar significa
que el primer usuario que abra la pantalla es el que descubre el bug.

**SIN DATOS Y FUERA DEL BLOQUE I → declarados (no cubiertos):**
`capacitacion_repo._build` y `asignacion_repo._build` (capacitaciones, 0 filas, no entran en el
bloque I) · `horas_repo._build` (0 filas; depende del link público de horas, E4 EN PAUSA) ·
`vacante_repo.find_by_ids` (0 filas; 🚩 se vuelve urgente con la primera vacante con candidatos).

🔴 **CORRECCIÓN DE LA SESIÓN ANTERIOR, y es la parte que más importa.**
`evaluacion_repo.find_resultados_por_evaluados` estaba declarado como *"módulo ev_* congelado"*.
**Es falso.** `evaluacion_repo` es el módulo NUEVO de resultados importados
(`evaluacion_lotes`/`_evaluados`/`_resultados`), completo y en producción; el congelado es `ev_*`
(`ev_ciclos`, `ev_plantillas`, `ev_instancias`), que son OTRAS tablas y están en 0. La confusión
por el prefijo del módulo dejó al mapper con **más datos de todo el sistema** declarado como
intocable. La regla quedó escrita en el barrido: **mirar la tabla que lee, no el prefijo.**

### Hallazgos

**Ninguno.** Los cinco mappers funcionan correctamente al ejercitarlos por primera vez. Un
sospechoso descartado con evidencia, para que no se re-investigue: `.order("orden")` en
`find_resultados_por_evaluados` es válido — `evaluacion_resultados` **tiene** la columna `orden`
(NOT NULL), verificado en el catálogo.

### Los tests

`test_mappers_con_datos` (18) y `test_mappers_bloque_i` (13). En los dos, la respuesta a *"¿qué
tendría que ser distinto para que no puedan fallar?"* es la misma y está escrita: **que la lista
estuviera vacía**. Cada bloque tiene su `test_la_lista_vacia_no_prueba_nada` y el anclaje del
early-return por AST.

Lo que los fakes SÍ pueden desmentir: filas de **dos empresas**, personas distintas, y el campo
opcional en null en cada caso —la fila legacy de auditoría con `entidad`/`evento`/`usuario`/
`empresa` en NULL (que ejercita el fallback `entidad ← tabla`, `evento ← acción`), el empleado sin
área en vacaciones, el ítem sin número de serie en inventario—. Todas las aserciones comparan
contenido de SU fila, nunca el largo de la lista.

🔴 **`FakeSupabase` ganó `.order()` que REGISTRA y NO ORDENA.** Un doble que ordenara dejaría
pasar un repo que se olvidó del `.order(...)`: el test vería las filas ordenadas igual. Es el caso
#3 de la regla del repo. El orden se afirma sobre lo que VIAJA EN LA QUERY. Molde:
`test_historial_salarial::TestElOrdenLoPoneLaQuery`.

### Verificación

**Medición final instrumentando la suite: 18/22 ejercitados** (eran 13/22). Los 4 restantes son
exactamente los declarados, todos con tabla en 0.

**Backend 2761 passed, 0 skipped** (eran 2730; +31). Los ocho barridos: **485**.
`ruff --select F821` limpio sobre `repositories/` y `services/`; `F401/F811/F821` limpio sobre los
archivos nuevos.

**Impacto en infraestructura:** **Ninguno.** Solo tests. Sin migraciones, variables de entorno,
dependencias, buckets ni endpoints. **No se tocó una sola línea de `repositories/` ni de
`services/`.**

---

## 2026-08-09 · Los cinco mappers que nunca se ejecutaron + octavo barrido · commit pendiente

**Qué cambió:** SOLO TESTS. **Cero código de producción tocado.** Se ejercitaron por primera vez
los cinco mappers que faltaban, apareció un bug real en uno de ellos, y la clase quedó cubierta
por un barrido.

### 🔴 EL HALLAZGO — `_ev_instancias_row.enrich_rows` descarta el nombre de la empresa

```python
emp_empresa_map = {e["id"]: e.get("empresa_nombre") for e in supabase_admin.table("empresas")
                   .select("id,nombre").in_("id", ...).execute().data or []}
```

El `select` pide `id,nombre`; el dict lee **`empresa_nombre`**, una clave que la fila NO tiene. La
query se hace, los datos vuelven, y se descartan leyendo la clave equivocada: **`empresa_nombre`
sale `None` para TODA instancia de evaluación, siempre**. No hay error, solo una columna
permanentemente vacía. Es la misma familia que el `_TA` de `_ausencia_row`: código que nunca corrió
bajo test.

⚠️ **NO SE ARREGLÓ, por decisión previa**: `ev_*` está congelado, con las tablas en 0 filas y los
routers montados, y se limpia en el cutover a AWS. `test_pendiente_conocido_empresa_nombre_siempre_sale_None`
**fija el comportamiento y documenta que es un bug**; el día que se arregle (o se borre el módulo)
ese test tiene que ROMPERSE y moverse, no borrarse. **Los otros cuatro mappers funcionan bien.**

⚠️ **Un falso positivo descartado, para que no se re-investigue:** `_proyectos_enrich.enriquecer`
hace `float(r.get("presupuesto") or 0)` —anticipa `None`— pero pasa el `None` crudo por `**r` a un
campo `float`. Verificado contra el catálogo vivo: `proyectos.presupuesto` es **NOT NULL DEFAULT 0**
y 0 de 8 filas son nulas, así que esa rama no puede dispararse desde la base. No es bug y no se
testea el caso imposible.

### Los tests

`test_objetivo_row` (10) · `test_proyectos_enrich` (11) · `test_ev_row_mappers` (13), más dos
helpers compartidos: `_fake_supabase.py` (un doble que **devuelve datos** y **honra la columna del
`in_`** — `_objetivo_row` consulta la puente por `objetivo_id`, no por `id`) y
`_mappers_early_return.py` (detección del patrón por AST).

En los tres, la respuesta a *"¿qué tendría que ser distinto para que no puedan fallar?"* es la
misma y está escrita: **que la lista estuviera vacía**. Cada archivo tiene su
`test_la_lista_vacia_no_prueba_nada` y su anclaje del early-return.
⚠️ **El anclaje se hacía leyendo líneas y estaba mal**: salteaba lo que empieza con comilla, así
que fallaba con cualquier docstring de más de una línea (dio un falso rojo en `enriquecer`). Ahora
es por AST —el docstring es un nodo que se descarta por lo que ES— y los tres archivos previos se
migraron a la misma primitiva.

### El octavo barrido — `tests/test_mappers_ejercitados.py`

🔴 **El descubrimiento por AST encontró 22 mappers con el patrón, no 8.** La clase era mucho más
grande de lo que se había medido. El barrido los descubre solos (nunca contra una lista escrita a
mano) y exige que cada uno esté declarado: **ejercitado** (con el módulo de test, cuyo vínculo se
verifica) o **sin ejercitar CON su razón**. Un mapper nuevo rompe el test hasta que alguien decida.

**Estado real, medido instrumentando la suite: 13/22 ejercitados, 9 no.** Esos 9 quedan declarados
y VISIBLES —hoy eran invisibles—, ordenados por riesgo: `audit_repo._build` es el peor
(`auditoria` tiene 133 filas en producción), seguido de capacitaciones, inventario y proyectos.
`_vacaciones_utils.enriquecer` está en la misma situación exacta que estaba ausencias antes del bug:
0 filas en la tabla y el cuerpo sin ejecutar nunca.

🔴 **Qué NO prueba, escrito en su encabezado:** que la lista fuera no vacía. Eso es dinámico y no
se lee del código; lo garantiza el `test_la_lista_vacia_no_prueba_nada` de cada mapper, que es el
molde que el barrido obliga a escribir. Es el mismo proxy que acepta `test_limite_export`.
**Por qué no se hizo dinámico**, que sería la medición real: exigiría envolver los 22 durante toda
la sesión y afirmar al final, y entonces `pytest tests/un_archivo.py` fallaría siempre. Un barrido
que solo sirve corriendo la suite entera se termina desactivando.

### Verificación

**Mutaciones del barrido:** mapper nuevo sin declarar → rojo · declaración apuntando a un mapper
inexistente → rojo · test declarado que no menciona su mapper → rojo. Guarda de mínimo: 18.

**Medición final (item 4): los 8 mappers del planteo original quedaron TODOS ejercitados con
listas no vacías** — `_ausencia_row._build` (3), `_objetivo_row._build` (3),
`_proyectos_enrich.enriquecer` (3), `_ev_instancias_row.enrich_rows` (2), `_ev_plantillas_row.enrich`
(2), `_inventario_items_row._build` (4), `_evaluacion_lotes_enrich.enriquecer_lotes` (2), más
`resultados` (que no tiene early-return y también estaba sin ejercitar).

**Backend 2730 passed, 0 skipped** (eran 2691; +39). Los **ocho** barridos: **485**.
`ruff --select F401,F811,F821` limpio sobre los seis archivos nuevos.

**Impacto en infraestructura:** **Ninguno.** Solo tests: sin migraciones, variables de entorno,
dependencias, buckets ni endpoints. Sin cambios de auth ni de CORS. **No se tocó una sola línea de
`repositories/` ni de `services/`.**

---

## 2026-08-09 · `NameError` latente en el mapper de ausencias + séptimo barrido (F821) · commit pendiente

**Qué cambió:** se arregló un `NameError` que iba a reventar con la primera ausencia cargada, y la
clase entera pasó a estar cubierta por un barrido que corre con `pytest`.

### El fix

`repositories/_ausencia_row.py` usaba `_TA` sin definirlo ni importarlo: al dividir el repo
(migración 088) el USO se mudó al satélite y la constante quedó atrás en un
`_T, _TA = "solicitudes_ausencia", "tipos_ausencia"`. `_build` levantaba
`NameError: name '_TA' is not defined` con **cualquier lista de filas no vacía**, o sea el
listado entero de ausencias.

🔴 **El import de vuelta habría sido circular** (`ausencias_repo` importa `_ausencia_row`), así
que la constante BAJÓ al satélite, que es su único consumidor. Duplicar el literal en los dos
módulos era la otra opción y es como se vuelven a separar. `ausencias_repo` quedó solo con `_T`.

### 🔴 El hallazgo que importa: 6 de 8 mappers de lista nunca se ejercitan con filas

Instrumentando la suite entera (no suponiendo), el largo máximo de lista con que se llamó a cada
mapper de `repositories/`:

| Mapper | Máximo |
|---|---|
| `_ausencia_row._build` | **0 — nunca con filas** |
| `_ev_instancias_row.enrich_rows` | **0** |
| `_ev_instancias_row.resultados` | **0** |
| `_ev_plantillas_row.enrich` | **0** |
| `_objetivo_row._build` | **0** |
| `_proyectos_enrich.enriquecer` | **0** |
| `_inventario_items_row._build` | ok (4 filas) |
| `_evaluacion_lotes_enrich.enriquecer_lotes` | ok (2 filas) |

**Todos empiezan con `if not rows: return []`, así que llamarlos con `[]` no ejecuta una sola
línea del cuerpo.** Tienen tests y el cuerpo está sin probar. Es exactamente el escondite donde
vivió este bug. Los cinco restantes **quedaron sin tocar** (fuera de scope): ninguno tiene hoy un
nombre libre —el barrido nuevo lo garantiza—, pero sus cuerpos siguen sin ejercitarse. `ev_*`
tiene las tablas vacías en producción y `objetivos`/`proyectos` no.

### El séptimo barrido — `tests/test_nombres_definidos.py`

Un nombre libre **no falla al importar**: falla cuando la línea corre. Si el camino no está
cubierto, la suite entera puede estar verde con la bomba puesta. Pasó DOS veces en la sesión
anterior y ninguna la vio ningún test: este `_TA`, y un `user_id` vivo en el `logger.error` de
`gmail_service` después de sacar el parámetro de la firma —un `NameError` **dentro del handler de
error**—.

**Llama a ruff en vez de reimplementarlo.** Resolver scopes bien (comprensiones, closures,
`global`/`nonlocal`, `TYPE_CHECKING`) ya está hecho y mejor; una segunda implementación tendría
falsos positivos que alguien terminaría silenciando, y un barrido que se silencia deja de barrer.
Lo que agrega este archivo no es la detección: es que **corra sola**, como los otros seis.

🔴 **Dos guardas, las dos verificadas por mutación:**
1. **Si ruff falta, FALLA — no se saltea.** Simulado: el mensaje dice qué instalar. Un `skip` acá
   reproduciría el bug de los 61 tests `async def` que se salteaban en silencio según qué tuviera
   instalado cada máquina.
2. **Se cuenta cuántos archivos miró** (539 hoy, mínimo 400). **`ruff check ./ruta_inexistente`
   responde "All checks passed!" y sale con 0** — comprobado. Sin el conteo, un barrido mal
   apuntado o un `exclude` nuevo darían verde sin haber leído nada.

Cubre `F821` · `F822` · `F823` — la familia "el nombre no existe cuando la línea corre". **Ninguna
regla de estilo a propósito**: el repo NO está formateado con ruff y mezclarlo lo volvería
inmantenible.

### Verificación

**Barrido F821/F822/F823 sobre los 539 archivos del backend: UN solo hallazgo, el `_TA`.** Nada
grande escondido. `F811`, `F701` y `E999` también en cero.

**Mutaciones:** `_TA` como nombre libre → **5 rojos** en `test_ausencia_row` + el barrido nuevo ·
early-return borrado → **2 rojos** (la guarda de "lista vacía no prueba nada" deja de mentir) ·
barrido apuntado a una ruta inexistente → **2 rojos** por el conteo mínimo · ruff ausente →
falla con instrucciones.

⚠️ **`ruff==0.16.0` se agregó a `requirements-dev.txt`**, pineado como el resto. Estaba instalado
ad hoc solo en el venv de la Mac. **En una máquina sin él la suite ahora da rojo hasta reinstalar
los dev requirements** — que es la intención: el rojo es la señal, el verde silencioso era el bug.

**Backend 2691 passed, 0 skipped** (eran 2681; +10). Los **siete** barridos: **480**.

**Impacto en infraestructura:**
- **Dependencia de desarrollo nueva: `ruff==0.16.0` en `requirements-dev.txt`.** NO va a
  producción (`requirements.txt` sin tocar) y no cambia el deploy. El dev que monte AWS tiene que
  instalar los dev requirements para correr la suite.
- Sin migraciones, variables de entorno, buckets ni endpoints. Sin cambios de auth ni de CORS.

---

## 2026-08-08 · La lectura de Gmail sale de la casilla del sistema + bajada de adjuntos · commit pendiente

**Qué cambió:** dos cosas, "de dónde y cómo saco los bytes". **Todavía NO se crea ningún candidato
ni se sube nada a Storage**: la sesión termina en "tengo los bytes del CV en memoria y sé de qué
mail vienen".

### A — la casilla

🔴 `gmail_service` pedía el token con `access_token_valido(IntegracionRepo(), user_id)`: la cuenta
de quien apretaba el botón. **Pasaba desapercibido por accidente**: hay UNA sola integración en la
base y esa fila es a la vez la del usuario y la marcada `es_remitente_sistema`, así que "lee la del
sistema" y "lee la del usuario" resolvían al mismo buzón y eran indistinguibles. Con un segundo
usuario conectado, el mismo botón sobre la misma vacante habría devuelto listas distintas según
quién lo apretara, **sin ningún error**. Y un proceso automático no tiene `user_id`: la
automatización futura era imposible.

La resolución se extrajo a **`services/_casilla_sistema.py`**, compartida por el envío y la
lectura. 🔴 **El corte es por lo que se comparte, no por líneas**: si la lectura se copiaba su
versión, el próximo arreglo del remitente quedaba hecho en un lado solo — el argumento con el que
`_google_token` se extrajo en su momento. De paso `mailer/engine.py` bajó de 141 a **108**.
⚠️ **Los dos métodos YA NO RECIBEN `user_id`.** Que el parámetro siguiera en la firma sería
afirmar que la lectura depende de quién pregunta. Los dos routers dejaron de pasarlo.
⚠️ Error propio **`GMAIL_SIN_CASILLA` (400)** con mensaje accionable (molde `MAIL_SIN_REMITENTE`);
el envío conserva su code y su mensaje. Los mensajes difieren a propósito: nombran la consecuencia
concreta de cada camino. El front dejó de hardcodear "conectá tu cuenta de Google" —que ya no es
cierto— y **muestra el mensaje del backend**, que se escribe en un solo lugar.

### B — bajar el adjunto

Las cuatro piezas, ninguna existía: `format=full` (metadata no trae `parts[]`), recorrido
**recursivo** de `parts[]`, `GET /messages/{id}/attachments/{id}`, y `urlsafe_b64decode` con el
padding repuesto.

**Dónde quedó cada cosa, y por qué:** el recorrido y el decode son funciones PURAS sobre el dict
del mensaje → `_gmail_mensaje.py`. La descarga es la única que abre una conexión → satélite propio
**`_gmail_adjuntos.py`**, que era el corte anotado desde el principio y que se crea recién ahora
porque hasta hoy no tenía nada adentro.

🔴 **El recorrido es recursivo porque anidar es lo NORMAL**: el caso típico es `multipart/mixed`
conteniendo un `multipart/alternative` MÁS el adjunto, y cada cliente anida distinto. Un recorrido
de un nivel funciona con el ejemplo que uno arma a mano y **falla en silencio con los mails
reales**: no da error, simplemente no encuentra el CV.
🔴 **Se modela el adjunto INLINE además del referenciado.** Gmail manda los chicos embebidos en
`body.data` y solo los grandes por `attachmentId`. Ir siempre a `/attachments` daría 404 y un CV
de pocos KB se perdería sin rastro.
🔴 **Cada adjunto se valida en su propio `try`** (B5): `validar` levanta 400/413, pensados para un
upload HTTP donde abortar es correcto. En un lote no lo es — un `.png` de firma haría fallar la
revisión entera. Lo que no pasa va a `descartados` CON su motivo.
🔴 **"Traía adjuntos y ninguno servía" es un estado propio** (B6): `sin_cv_util` lo separa de "no
adjuntó nada". Los dos tienen `cvs == []` y piden respuestas distintas.
⚠️ La firma de imagen se descarta **por extensión antes de bajarla**, reusando el criterio de
`cv_service` (importado, no duplicado): ahorra una llamada a Gmail por logo, y en un lote de 20
mails eso es la diferencia con el rate limit.

### Verificación

**Seis mutaciones, cada una restaurando el archivo:** recorrido no recursivo → **14 rojos** ·
`b64decode` estándar → **1** (el test del alfabeto url; el del padding no lo ve, y es correcto que
sean dos tests distintos) · leer la casilla del usuario → **8** · sin captura por adjunto → **2** ·
ignorar el inline → **2** · bajar todo incluida la firma → **1**.

🔴 **El fake de la casilla tiene DOS integraciones con tokens distintos** (`get_remitente` →
TOKEN_SISTEMA, `get_by_user_and_tipo` → TOKEN_USUARIO). Con una sola, "lee la del sistema" y "lee
la del usuario" son indistinguibles — que es exactamente por qué el bug sobrevivió meses. Hay un
test punta a punta que mira el `Authorization` real que sale hacia la API.
🔴 **Los árboles MIME del fake son ANIDADOS**, incluidos `mixed>alternative`, tres niveles, uno con
firma además del CV y uno con adjuntos y ningún CV válido. Con un solo árbol plano, un recorrido no
recursivo pasa todos los tests.

✅ **`test_callers_huerfanos` detectó `descargar_cvs` en el bucket peligroso** (la suite lo
ejercita, producción no lo alcanza). **Se declaró con razón y con la instrucción de borrar la
declaración al conectarlo** — la sesión termina ahí a propósito: mezclarla con la creación del
candidato habría dado un camino de escritura sin tests del recorrido MIME.

**Backend 2681 passed, 0 skipped** (eran 2651; +30). Los seis barridos: **477**. `tsc --noEmit` en
**0**, front **522 passed, 0 skipped**. `test_mailer_punto_unico` verde (se tocó `engine.py`).
⚠️ `EmailsSection.tsx` quedó en **150/150 exacto** y `_gmail_adjuntos.py` en **148/150**.

🔴 **`ruff --select F821` encontró un `NameError` latente que la suite no ve**: al sacar `user_id`
quedó una referencia en el `logger.error` de `get_emails_candidatos` — o sea, un fallo DENTRO del
handler de error. Corregido. **El barrido de imports huérfanos por AST no lo veía: cubre imports,
no nombres libres.** Vale como regla: las dos herramientas cubren cosas distintas.

⚠️ **BUG PREEXISTENTE ENCONTRADO Y NO ARREGLADO (fuera de scope):**
`repositories/_ausencia_row.py:31` usa `_TA`, que **no está definido ni importado en ese módulo**
(vive en `ausencias_repo.py`). Verificado empíricamente: `_build` levanta
`NameError: name '_TA' is not defined` con cualquier lista de filas no vacía. **No falla hoy porque
`solicitudes_ausencia` tiene 0 filas en producción; va a fallar con la primera ausencia cargada**,
y se lleva puesto el listado entero. Es un `import` de una línea. Quedó sin tocar por la regla de
no modificar archivos fuera del scope — **decidilo vos**.

**Impacto en infraestructura:** **Ninguno.** Sin migraciones, variables de entorno, dependencias,
buckets ni endpoints nuevos — las 227 rutas son las mismas. Sin cambios de auth ni de CORS.
⚠️ **Sí cambia un requisito operativo:** la lectura de postulaciones ahora EXIGE que haya una
casilla designada como remitente del sistema. Hoy la hay (`franbincovich@gmail.com`); si se
desconecta, la revisión de mails deja de funcionar con `GMAIL_SIN_CASILLA` en vez de caer a la
cuenta del usuario. Es la intención.

---

## 2026-08-08 · Código de vacante (VAC-0001) y texto listo para el aviso · commit pendiente

**Qué cambió:** cada vacante tiene ahora un código propio, y la ficha muestra la frase completa
para pegar en LinkedIn. Cierra las fases 2 y 3 del flujo de CV screening.

🔴 **MIGRACIÓN 097 — NO CORRIDA. La corre Franco.** Es la única pendiente junto con la 095 y la
096 (esas dos tampoco están en producción, verificado contra el catálogo).

### El contador: secuencia de Postgres en un DEFAULT

Las tres opciones y por qué gana esta:
1. **El service lee el máximo y suma uno** — descartada: es una condición de carrera de manual.
   Dos altas simultáneas leen el mismo máximo y emiten el mismo código. Con una sola persona
   cargando casi nunca se ve; con dos, aparece y es irreproducible.
2. **Trigger BEFORE INSERT** — igual de atómico, pero agrega PL/pgSQL para lo que un DEFAULT
   resuelve en una línea, y este repo ya dropeó sus triggers de negocio en la 058.
3. **Secuencia + DEFAULT** ✅ — `nextval` es atómico y nunca repite, sin locks. No hay ventana
   entre leer y escribir porque no hay lectura.

Y el motivo que decide aparte de la concurrencia: **con el DEFAULT en la base, toda fila nace con
código venga de donde venga** —backend, INSERT a mano, import futuro—. Si lo pusiera la app,
cualquier alta que no pasara por ella dejaría una vacante muda que nunca podría recibir un CV.

⚠️ **La secuencia deja huecos y está bien**: un INSERT fallido consume el número igual. El código
es un identificador, no un conteo; cerrar los huecos costaría exactamente la carrera que se evita.
⚠️ **El CHECK es `[0-9]{4,}` y no `{4}`**: `lpad` no trunca, así que la vacante 10.000 emite
`VAC-10000`. Con `{4}` exacto el CHECK la rechazaría y el alta fallaría sin explicación.
🔴 **El UNIQUE va sobre `upper(codigo)` y es GLOBAL, no por empresa.** Global porque la casilla que
recibe los CVs es UNA para todo el sistema: con un código por empresa, DOSUBA y KARSTEC emiten el
mismo `VAC-0001` y el matcher no puede desempatar —el remitente es alguien de afuera, no aporta
empresa—. Sobre `upper()` porque el lookup es case-insensitive: con un UNIQUE sensible,
`VAC-0001` y `vac-0001` coexistirían y el lookup encontraría DOS filas, que en `maybe_single()`
es un 500, no un 404. **La unicidad tiene que definirse con el mismo criterio con el que se
consulta.**

**Backfill escrito aunque producción tenga 0 vacantes**: el orden add-nullable → backfill → NOT
NULL es el que sobrevive si esto corre sobre una base con datos (un entorno de prueba, un backup
restaurado). Sin backfill, el `SET NOT NULL` falla y la migración queda a medias.

### Lo demás

`VacanteResponse.codigo: str` **obligatorio y ausente de `VacanteCreate`/`VacanteUpdate`**: RRHH no
lo elige ni lo edita, y si la app pudiera mandarlo le ganaría al DEFAULT. `find_by_codigo` en el
repo (`ilike`, case-insensitive, **sin `empresa_id`** por lo de arriba) — es el lookup del matcher.
Columna "Código" primera en el export.

**El texto del aviso lo arma el BACKEND** (`services/_vacante_aviso.py`, endpoint
`GET /api/vacantes/{id}/aviso`, gate `VACANTES + READ`): es la instrucción que va a leer un
candidato, y de que se escriba igual todas las veces depende que el código matchee. Si la armara
el front —o peor, si RRHH la tipeara— cada aviso saldría con una variante ("ref VAC 0001", "poner
el código en el asunto"), el mail entraría igual, el código no matchearía y el CV terminaría en
"sin asignar" sin que nada falle visiblemente. Los corchetes son parte del token, no decoración.
⚠️ **Sin casilla del sistema designada, `texto` sale en `null` y la pantalla dice qué falta
configurar.** Un aviso que diga "Enviá tu CV a None" se publica y nadie se entera hasta que no
llega ni un CV. El código se muestra igual: no depende de ninguna integración.

**Front:** `CodigoPostulacion.tsx` (115) en la ficha, arriba de la publicación. Dos botones de
copiar — el grande copia **la frase entera**, el chico solo el código. `page.tsx` +4 líneas.

### Verificación

**Seis mutaciones, cada una restaurando el archivo** (`__pycache__` borrado entre cada una):
schema sin `codigo` obligatorio → **2 rojos** · lookup con `eq` en vez de `ilike` → **4** · export
sin la columna → **2** · la frase sin corchetes → **1** · UNIQUE por empresa → **1** · la app
mandando el código en el INSERT → **2** (uno de ellos por el índice único del propio fake).

🔴 **El fake de Supabase modela la secuencia Y el índice único, y hay un test que fuerza la
colisión a propósito** (`test_un_codigo_repetido_lo_rechaza_la_base`). Sin él, un fake permisivo
se vería idéntico a uno estricto y todo el archivo estaría afirmando sobre algo que no puede
fallar. El test del código llegando al front corre contra el **mapper real** (`_vrow`), no contra
un fake del service — es la lección de las tres veces que el select traía la columna y el schema
la descartaba en silencio.

✅ **`test_callers_huerfanos` detectó los dos cabos sueltos** y los dos se resolvieron distinto:
`/aviso` se conectó al front (era el plan), y `find_by_codigo` **se DECLARÓ con razón y con la
instrucción de borrar la declaración al construir el matcher** — la columna y su UNIQUE se crean
primero a propósito, porque las vacantes que RRHH cree mientras tanto tienen que nacer con código.

**Backend 2651 passed, 0 skipped** (eran 2621; +30). Los seis barridos: **477**. Rutas **226 →
227** (solo `/aviso`), gate ejercitado sobre `app.routes`: PASA admin y gerencia_lectura, **403**
mandos_medios y sin rol. Front **522 passed, 0 skipped** (sin cambios) y `tsc --noEmit` en **0**.
Imports huérfanos por AST + `ruff --select F401,F811,F821`: cero.
⚠️ `vacante_repo.py` quedó en **100/100 exacto** — el próximo cambio ahí exige dividir primero.
⚠️ `[id]/page.tsx` 434 → **438**: sigue siendo deuda previa declarada, su corte es tanda propia.
**No se corrió `ruff format` ni `prettier`.**

**Impacto en infraestructura:**
- 🔴 **Migración 097 PENDIENTE** (`vacantes.codigo`). Crea la secuencia `vacantes_codigo_seq`,
  la columna NOT NULL con DEFAULT, el índice `vacantes_codigo_uq` sobre `upper(codigo)` y el CHECK
  de formato. **NO es destructiva.** Corre en una transacción. Con 0 vacantes no puede fallar.
  **El backend la necesita corrida antes de deployar**: `VacanteResponse.codigo` es obligatorio,
  así que sin la columna el listado de vacantes revienta al mapear.
- **`db/schema.sql` actualizado** (secuencia + columna + CHECK + índice), que es la fuente de
  reconstrucción.
- **Endpoint nuevo**: `GET /api/vacantes/{id}/aviso`. Autenticado, gate `VACANTES + READ`. No es
  público.
- **AWS/RDS**: es Postgres estándar (secuencia + DEFAULT + índice funcional), sin nada propio de
  Supabase. La secuencia queda `OWNED BY` la columna, así que un DROP TABLE se la lleva.
- Sin variables de entorno, dependencias ni buckets nuevos. Sin cambios de auth ni de CORS.

---

## 2026-08-08 · Cinco divisiones para hacerle lugar al CV screening (refactor puro) · commit pendiente

**Qué cambió:** cero funcionalidad. Cinco archivos sin margen se partieron porque ninguna línea
del CV screening entraba. **La suite quedó en 2621 después de cada una de las cinco**, y las 226
rutas de `app.routes` son idénticas a las del baseline en path, método, gate, query y status.

| Origen | Antes | Ahora | Satélite nuevo | |
|---|---|---|---|---|
| `services/gmail_service.py` | 145/150 | **131** | `_gmail_mensaje.py` (53) | |
| `repositories/vacante_repo.py` | 98/100 | **87** | `_vacante_row.py` (38) | |
| `repositories/candidato_repo.py` | 95/100 | **80** | `_candidato_row.py` (40) | |
| `routers/vacantes_escrituras.py` | 79/80 | **67** | `vacantes_integraciones.py` (50) | |
| `app/(dashboard)/vacantes/[id]/page.tsx` | 577 | **434** | `EmailsSection.tsx` (149) + `EmailCandidatoRow.tsx` (48) | |

🔴 **`_gmail_adjuntos.py` NO se creó, y es la desviación que hay que leer.** El corte anotado era
llevarse *"el recorrido MIME, la descarga del adjunto y el decode base64url"*. **Ese código no
existe**: `gmail_service` pide los mensajes con `format=metadata`, que ni siquiera trae
`payload.parts[]`, así que no había una sola línea de esas tres cosas para mover y el satélite
habría nacido vacío. Se cortó por el criterio que sí divide el archivo hoy —**la red**—:
`_gmail_mensaje.py` se lleva lo que se sabe de un mensaje sin volver a hablar con Gmail
(`_parse_from_header`, `_is_cv_email`), y `gmail_service` queda con las dos conversaciones HTTP y
el caso de uso. **Es el mismo lugar donde aterrizan dos de las tres piezas pendientes**: recorrer
`parts[]` y el decode base64url son funciones puras sobre el dict del mensaje. La única que no es
la llamada a `/attachments/{id}`, y si algún día pesa, **ESA** justifica un `_gmail_adjuntos.py`.

**El corte del router salió por la costura que su propio docstring ya describía**, no por conteo:
`publicar_linkedin` y `candidato_desde_email` son las únicas escrituras del módulo que **no pasan
por `VacanteService`** —llaman directo a Zernio y Gmail, que resuelven la vacante y su empresa por
su cuenta— y es donde crece el CV screening.
🔴 **Verificado ANTES de moverlos que ninguno de los dos está en `limiter._route_limits`**, ni
bajo su clave vieja ni bajo la nueva. La clave es `routers.<módulo>.<función>`: mudar de archivo
un endpoint decorado le resetea el contador en silencio. Los únicos decorados del módulo son
`exportar_vacantes` y `exportar_candidatos`, y **no se tocaron**.

⚠️ **`EmailsSection` necesitó un segundo corte y no estaba previsto:** movida verbatim quedaba en
**165/150**. Salió la card a `EmailCandidatoRow.tsx`, que es el corte presentacional que el repo
ya usa en `CandidatoGrupo`/`CandidatoRow` y `HistorialImportaciones`/`HistorialTable` — el
orquestador tiene el estado, la fila dibuja. El JSX se movió verbatim; lo único nuevo son los
props que antes eran variables del closure. **`EmailsSection` quedó en 149/150: sin margen. El
próximo agregado ahí exige dividir de nuevo.**

⚠️ **`page.tsx` sigue en 434, muy por encima de 150.** Es deuda previa declarada: su corte es una
tanda propia (molde `components/features/sucesion/`, 855 → 85). Lo que esta sesión saca es
exactamente el bloque donde iba a crecer el CV screening.

**Verificación.** Imports huérfanos por AST, archivo por archivo (cada nombre importado contra los
`Name`/`Attribute` del cuerpo que queda), con `ruff --select F401,F811,F821` como segunda opinión:
**cero** en los 9 archivos backend. Rutas por introspección de `app.routes`: **226 → 226**, sin una
sola diferencia de gate, query, status ni nombre; los 2 únicos endpoints que cambiaron de módulo
son los dos sin decorador.
🔴 **El gate se EJERCITÓ, no se leyó:** se invocó el callable real que cuelga de `app.routes`
(filtrando por `_verificar`) con cuatro roles. Los 16 endpoints del módulo dan la matriz esperada
— los dos movidos responden **403 FORBIDDEN** para `gerencia_lectura`, `mandos_medios` y sin rol,
idéntico al resto de las escrituras, y las lecturas siguen pasando para `gerencia_lectura`.
✅ **`test_selects_repos` sigue RESOLVIENDO el embed de vacantes a través del import nuevo** (no
solo pasando): se verificó que devuelve `tabla=vacantes, spec=*, areas!vacantes_area_id_fkey(...)`
en las 3 queries. El barrido ya seguía `ImportFrom` — el precedente es `_empleado_row`.
✅ **`test_contrato_repos` (el barrido nuevo) aguantó su primera división real**: sigue viendo
**320 llamadas en 55 archivos, 216 pares (clase, método)** — los mismos números que antes de
partir nada. `test_callers_huerfanos` verde.

**Backend 2621 passed, 0 skipped** (sin cambios). Los seis barridos estructurales: **465 passed**.
`tsc --noEmit` en **0**.
⚠️ **Front 522 passed (eran 521), y el +1 está explicado y verificado**: `loadingSeApaga.test.ts`
descubre archivos por barrido, y `EmailsSection.tsx` pasó a ser un archivo propio con su
`setLoading(true)` — se confirmó que aparece como caso nuevo en el reporte del test. Es el barrido
cubriendo automáticamente al componente nuevo, que es para lo que existe.
⚠️ Los 2 hallazgos de eslint en los archivos tocados son **preexistentes y viajaron con su código**
(`no-unescaped-entities` por las comillas de `"Revisar emails"`, que estaban en `page.tsx`; y el
`set-state-in-effect` de `page.tsx`, que dispara **105 veces** repo-wide). Baseline del front sin
cambios: 138 problemas. **No se corrió `ruff format` ni `prettier`.**

**Impacto en infraestructura:** **Ninguno.** Sin migraciones, variables de entorno, dependencias,
buckets ni endpoints nuevos — las 226 rutas son las mismas. Sin cambios de auth ni de CORS.
El único archivo de arranque tocado es `main.py`, que suma un `include_router` sobre el prefijo
`/api/vacantes` que ya existía.

---

## 2026-08-08 · El alta de candidato desde Gmail le pedía el método al repo equivocado · commit pendiente

**Qué cambió:** `services/gmail_service.py` llamaba a `self._vacante_repo.save_candidato(...)`.
Ese método **no existe en `VacanteRepo`**: vive en `CandidatoRepo` y lleva **tres** argumentos
`(vacante_id, data, empresa_id)`. La llamada quedaba fuera del try/except, así que el endpoint
`POST /api/vacantes/{id}/candidatos-desde-email` moría con `AttributeError` → handler global →
**500**. El botón "Agregar como candidato" de `/vacantes/[id]` **estuvo roto en producción desde
que los dos repos se separaron**.

🔴 **Nadie lo notó porque `crear_candidato_desde_email` era el ÚNICO método del módulo sin un solo
test.** El resto está cubierto por 8 archivos (`test_vacante_auditoria`, `test_vacantes_export`,
`test_google_token`, `test_assessment_vacantes_scope`…). El punto ciego era quirúrgico: el
barrido de empresa ejercita `get_emails_candidatos`, nunca su hermano de escritura.

**El fix:** `GmailService` instancia además `CandidatoRepo`, y el alta se le pide a él con la
firma real. **La empresa sale de la VACANTE, no del header** — `candidatos.empresa_id` es NOT
NULL y en modo consolidado el header vale `None`: heredarlo haría fallar el insert justo en la
vista más usada. Es Vista vs Acción, misma fuente que el hermano `_vacante_candidatos.agregar`.
Para eso `find_by_id` ahora retiene la fila en vez de evaluarse como bool.

🔴 **El alta NO se metió dentro del try/except, y está escrito por qué.** Ese bloque traduce
cualquier excepción a `GMAIL_ERROR` 502 ("Error al obtener el email de Gmail"): un fallo del
INSERT reportado ahí mandaría a revisar la integración de Google por un problema de base. Es el
mismo error de diagnóstico que `_google_token` documenta como su bug 2. El repo ya trae su propio
contrato (`DB_ERROR` 500 si el insert vuelve vacío), así que ensanchar el try no agregaría un
error del sistema: lo reemplazaría por uno que miente.

**Barrido nuevo — `tests/test_contrato_repos.py` (el sexto estructural).** Verifica por AST que
**todo `self.<attr>.<metodo>()` de un service exista en la clase que el `__init__` ata a ese
atributo**. Mapea atributo → clase leyendo el `__init__` (molde: `_barrido_auditoria`). Cubre
**320 llamadas en 55 archivos, 216 pares (clase, método) distintos**, con guarda de mínimo. Cierra
la CLASE de bug, no la instancia: es un fallo de división de archivos —el import resuelve, el
atributo existe, y Python solo se entera al ejecutar esa línea— y volvería a producirse con el
próximo corte de un repo. **Confirmado de paso que no había ninguna otra llamada rota en todo el
backend.**

⚠️ **Lo que el barrido NO cubre, declarado en su encabezado:** los colaboradores que llegan por
parámetro (`def crear(repo, audit, ...)`, el molde de los satélites `_*_write.py`) y los atributos
que el `__init__` no ata a un constructor. Ahí el tipo lo elige el caller; afirmar contra una
clase concreta sería inventar un contrato que el código no declara. **Es una red sobre el patrón
que produjo el bug, no una red completa.** Tampoco verifica aridad — eso lo cubre el fake.

**Tests nuevos — `tests/test_gmail_candidatos.py` (17).** Alta con los datos parseados · la
empresa sale de la vacante y no del header · barrera de empresa (vacante ajena no crea nada) ·
ajena indistinguible de inexistente · consolidado no restringe · 8 casos del header `From`
parametrizados.
🔴 **El fake de `CandidatoRepo` tiene la firma EXACTA de tres posicionales, sin `**kwargs`**: uno
permisivo habría aceptado la llamada rota y estos tests estarían verdes con el bug puesto. Un test
propio compara la firma del doble contra la del repo real con `inspect.signature`, así el doble no
se despega. Y `save_candidato` construye la respuesta **a partir de lo que recibe**.
⚠️ Un test fija como **pendiente conocido** que los headers RFC 2047 (`=?UTF-8?Q?Jos=C3=A9?=`)
llegan sin decodificar: documenta el agujero, no lo arregla. Cuando se decodifique, ese test tiene
que romperse y **moverse**, no borrarse.

**Verificación por mutación (4, cada una restaurando el archivo):** repo equivocado —el bug
original— **6 rojos** (4 unit + 2 del barrido, las dos capas lo atrapan por separado) · repo
correcto con aridad vieja **4 rojos** (solo el fake; el barrido mira existencia, no aridad) ·
empresa del header **2 rojos** · barrera desactivada **2 rojos**. `__pycache__` borrado entre cada
una (la mina documentada en CLAUDE.md).

**Verificación.** Backend **2621 passed, 0 skipped, 0 failed** (eran 2601; +20). Los seis barridos
estructurales verdes (**465**). `gmail_service.py` **145/150** — 5 líneas de margen, el próximo
cambio ahí exige dividir primero. `ruff check` sobre los tres archivos solo devuelve los códigos
ambientales del repo (`UP006`/`UP035`/`UP045`/`E402`), idénticos a los del molde
`_barrido_auditoria.py`; **no se corrió `ruff format`**.

⚠️ **Lo que este fix NO hace, a propósito (queda anotado, no resuelto):** el alta desde mail
**sigue sin emitir evento de auditoría** —el hermano manual emite `alta_candidato`— y **sigue sin
guardar el `gmail_message_id`**, así que llamarla dos veces con el mismo mail crea dos candidatos.
Las dos son del CV screening (bloque E), no de este bug. Tampoco se tocó el orden de los gates:
`access_token_valido` corre antes de la barrera de empresa, lo cual **no filtra nada** (su error
es del usuario, no del recurso) pero va contra la regla de "la barrera primero".

**Impacto en infraestructura:** **Ninguno.** Sin migraciones, variables de entorno, dependencias,
buckets ni endpoints nuevos — el endpoint ya estaba publicado, solo que devolvía 500. Sin cambios
de auth ni de CORS.

---

## 2026-08-08 · La pantalla del import de objetivos: el cable conectado (E2-11) · commit pendiente

**Qué cambió:** solo frontend. Los dos endpoints del import de objetivos —que existían, estaban
testeados y **no los llamaba nadie**— ahora tienen pantalla.

🔴 **Era el TERCER caso del proyecto de código construido sin la punta del cable**, después de
`set_remitente` (dejó el módulo de mails inalcanzable durante meses) y `POST /plantillas/enviar`
(el sistema no podía mandar un mail). La diferencia con esos dos: este quedó **declarado** como
excepción en `test_callers_huerfanos` en la misma sesión que lo creó, con la instrucción de
borrar la declaración al construir la pantalla. **Las dos entradas están borradas** y el barrido
queda verde sin ellas.

**Lo nuevo:** botón "Importar" gateado por escritura junto a "Nuevo objetivo" ·
`ImportarObjetivosModal` en dos pasos (subir → preview → confirmar → resultado) ·
`ImportObjetivosPreview` y `ImportObjetivosResultado` como componentes propios ·
`services/importacionObjetivos.ts` + `types/importacionObjetivos.ts`.

🔴 **EL RESULTADO NO SE MUESTRA COMO BINARIO**, porque no lo es: el lote no aborta por una fila
con problemas. `ImportObjetivosResultado` tiene TRES estados —nada cargado / todo cargado /
**parcial**— y el parcial dice "se cargaron 12 de 14" con el detalle de las 2 que no. Un cartel
de "Importación completada" sobre un lote donde entró el 30% es la clase de mentira por la que
el usuario cierra el modal creyendo que terminó.

🔴 **En modo consolidado el botón queda deshabilitado con el motivo a la vista**, pegado al
botón y no en el encabezado. Importar es una ACCIÓN: la empresa viaja en el body del confirmar.
Mismo criterio y mismo molde que el guardado de plantillas (`PlantillaAcciones`).

**Los mensajes de error del backend se muestran TAL CUAL** — están redactados para alguien con la
planilla abierta ("Faltan columnas obligatorias: Responsable"). Si el archivo se rechaza entero
(headers faltantes o columna de padre), el usuario se queda en el paso 1: no se cargó nada.

**Verificación.** Front **521 passed, 0 skipped** (eran 504; +17) · backend **2601 passed, 0
skipped** (sin cambios) · `tsc --noEmit` en 0 · barridos verdes (569) · ningún archivo sobre su
límite (el más ajustado: `objetivos/page.tsx` 148/150 y el modal 148/150).
✅ **`test_callers_huerfanos` verde SIN las dos excepciones**, y verificado que tiene dientes:
desconectando el `BASE` del service, el barrido vuelve a rojo con los dos endpoints.

⚠️ Un error de eslint en `objetivos/page.tsx:70` (`set-state-in-effect`) es **preexistente** —el
`useEffect(() => load(), [load])` que ya estaba— y la regla dispara 4 veces más en archivos que
esta sesión no tocó. Los seis archivos nuevos no tienen ningún hallazgo.

**Impacto en infraestructura:** **Ninguno.** Sin migraciones, variables de entorno, dependencias,
buckets ni endpoints nuevos — los dos que se conectan ya estaban publicados. Sin cambios de auth.

---

## 2026-08-08 · Lector de Excel + import de objetivos (E2-11) · commit pendiente

**Qué cambió:** el backend aprendió a LEER Excel —hasta hoy `openpyxl` solo se usaba para
escribir— y se sumó el import de objetivos con preview → confirmar.

**`services/_import_excel.py`** — lector genérico, simétrico a `_import_csv`: devuelve filas como
dicts con headers por clave y valores string, así los parsers no saben de qué formato vinieron.
🔴 **NO importa `_import_encoding` y no es un olvido:** un `.xlsx` es un ZIP con XML que declara
su encoding, así que los cuatro pasos de detección y el `permitir_latin1` no aplican.
**Las seis trampas resueltas** (medidas contra openpyxl 3.1.5, no supuestas): celda vacía `None`
(no `""`) · números que arrastran `.0` · fechas como `datetime` (no `date`, ni string) · espacios
invisibles en los headers · varias hojas → **se lee la PRIMERA, no la activa** (la activa es la
pestaña donde quedó el cursor al guardar) · filas fantasma al final.
⚠️ **`data_only=True` devuelve `None` si el productor nunca calculó la fórmula** — medido: un
.xlsx generado por librería no trae valor cacheado.

**El import** — preview en `objetivos_import_preview.py` y confirmar en
`objetivos_import_service.py`, que es literalmente el molde del Flujo 2 de nómina
(`nomina_csv_service` / `nomina_import_service`). El responsable se resuelve contra **`users`**
por email, username o "nombre apellido"; una fila con responsable inexistente o inactivo **no se
carga y se reporta** — nunca con responsable nulo. El confirmar va por `ObjetivoService.create`,
así que **revalida**: el preview resuelve para MOSTRAR, no para autorizar.

🔴 **QUÉ DEL MODELO NUEVO SOPORTA, declarado y no implícito:** responsables múltiples **SÍ** (la
puente de la 096); jerarquía **NO** — todo nace raíz. El motivo es concreto: la única columna
posible sería el título del padre y **`objetivos.titulo` no tiene UNIQUE**, y si el padre viniera
en el mismo archivo el resultado dependería del ORDEN DE LAS FILAS, que es el bug que
`_nomina_superiores` existe para evitar. **Y no se ignora en silencio:** un archivo con columna de
padre se RECHAZA ENTERO con un mensaje que dice dónde armar la jerarquía.

**Auditoría — primer evento del módulo.** UN evento por lote (`_audit_payloads_objetivos`),
`registro_id` uuid4 de EVENTO, empresa del body, con los ids creados. **Se emite siempre**,
también con lote vacío.
✅ **Verificado lo que se pedía: `test_auditoria_coherente` NO rojea.** El barrido toma como
alcance los ARCHIVOS que emiten eventos, y el que entró es `objetivos_import_service.py` —cuya
única escritura es ese mismo lote—, no `objetivo_service.py`. **El CRUD de objetivos sigue sin
auditar, igual que antes.**

**Verificación.** Backend **2601 passed, 0 skipped** (eran 2561) · front **504 passed, 0 skipped**
(sin cambios) · `tsc --noEmit` en 0 · barridos verdes · **11 mutaciones, todas cazadas**.

🚩 **DOS HALLAZGOS, para el registro:**
1. **La mutación encontró un test que no podía fallar.** `openpyxl normaliza a int los floats
   integrales que él mismo escribe`, así que con una planilla generada en el test la rama
   `float.is_integer()` **nunca se ejecuta** y borrarla quedaba en verde. Se agregó un test
   directo sobre `_valor`, que es el único punto donde la rama es alcanzable; el caso real llega
   de otros productores que escriben `<v>12345678.0</v>`.
2. **`test_callers_huerfanos` cazó dos cosas:** un atajo `_import_excel.leer` sin caller de
   producción (era código muerto, se borró) y los dos endpoints sin pantalla.

**Impacto en infraestructura:** **Endpoints nuevos** — `POST /api/importacion/objetivos/preview`
y `/confirmar`, autenticados (IMPORTACION + WRITE) y bajo la franja `import` (10/hora compartida).
**Dependencias: ninguna nueva** — `openpyxl==3.1.5` ya estaba en `requirements.txt` para el
export; esto es el primer `load_workbook` del repo. Sin migraciones, variables de entorno ni
buckets.
> 🔴 **PENDIENTE DECLARADO: la pantalla del import NO está.** Los dos endpoints quedan publicados
> e inalcanzables desde el front, **declarados con razón** en `test_callers_huerfanos`. Esas dos
> entradas **hay que borrarlas cuando se construya la pantalla** — una excepción que sobrevive a
> su motivo es el ruido contra el que ese mismo barrido avisa.

---

## 2026-08-08 · Subobjetivos con múltiples responsables (E3-5) · commit pendiente

**Qué cambió:** el rediseño del modelo de objetivos. Jerarquía de 2 niveles, responsables
múltiples por tabla puente, y los dos consumidores externos ajustados.

🔴 **DOS MIGRACIONES ESCRITAS Y **NO** CORRIDAS — las corre Franco.** Las dos son **aditivas**:
no hay ningún DROP, ni en estas ni en una futura.
- **095_objetivos_jerarquia.sql** — `objetivos.parent_id` uuid nullable, self-FK
  **ON DELETE CASCADE**, índice `idx_obj_parent`. Reejecutable (`IF NOT EXISTS` + guarda sobre
  `pg_constraint`).
- **096_objetivo_responsables.sql** — tabla puente con **PK compuesta** `(objetivo_id, user_id)`,
  las dos FKs en CASCADE, índice `idx_obj_resp_user` para la pregunta inversa, y **backfill** de
  `responsable_id` con `ON CONFLICT DO NOTHING`.
- `db/schema.sql` quedó sincronizado con las dos (es la fuente de reconstrucción y contra lo que
  `test_selects_repos` valida por AST).

**Decisiones implementadas tal como venían cerradas:** profundidad 2 · estado del padre
INDEPENDIENTE (`cambiar_estado` funciona igual en padres e hijos) · `responsable_id` se conserva
como dueño principal · cascade al borrar el padre · fecha propia · procesos y reporte anual
cuentan SOLO RAÍCES · export con columna "Objetivo padre" · sin auditoría.

**Backend.** `_objetivos_jerarquia.py` con la guarda de las **dos puntas** —el padre elegido no
puede ser hijo, y el que se cuelga no puede tener hijos—, con su limitación declarada: un CHECK
no consulta otra fila, así que **por SQL directo se puede crear un nieto**. El repo se partió en
tres satélites (`_objetivo_row`, `_objetivos_arbol`, `_objetivo_responsables`) para no pasar de
100 líneas.

🔴 **CERO EMBEDS DE POSTGREST, a propósito.** `objetivos` pasó a tener DOS relaciones contra
`users` (la columna de dueño y la puente), que es exactamente el escenario de PGRST201: un embed
`users(...)` que hoy resolvería se vuelve ambiguo y devuelve 300 sin que ningún test con el fake
de Supabase pueda verlo. Todo se resuelve con lookups batch, que además es el patrón que
`_objetivo_row` ya usaba.

🔴 **EL FILTRO POR RESPONSABLE MIRA LOS DOS LADOS** (puente `or` columna de dueño). No es
redundancia: **las migraciones las corre Franco a mano y el código se deploya antes**, y en esa
ventana la puente está vacía — un filtro que mirara solo ahí vaciaría el listado por responsable
sin ningún error. Hay un test dedicado a esa ventana.

**El orden del listado cambió de forma, no de query.** Las raíces salen por `fecha_entrega`
ascendente y los hijos debajo de su padre; el `.order()` sigue en la query y el anidado se arma
en Python. ⚠️ Un hijo cuyo padre no pasa el filtro **se promueve** al nivel superior en vez de
desaparecer: la pantalla y el archivo pueden mostrar de más, nunca de menos y en silencio.

**Frontend.** Kanban: hijos ni como tarjetas ni en el contador, badge de cantidad en el padre ·
ListView: hijos indentados en la misma tabla · Modal: selector de padre (solo raíces, sin sí
mismo) + multi-select de responsables por checkboxes.

**Verificación.** Backend **2560 passed, 0 skipped** (eran 2524) · front **504 passed, 0 skipped**
(eran 498) · `tsc --noEmit` en 0 · barridos estructurales verdes (602) · **11 mutaciones, todas
cazadas** (guarda de profundidad, las dos puntas, procesos, reporte anual, filtro de puente,
ventana pre-096, tope de export, hijos del export, columna padre, filtro del kanban, badge).

🚩 **DOS HALLAZGOS DE LA RED DE TESTS, para el registro:**
1. `test_ordena_por_fecha_entrega_ASCENDENTE` estaba escrito para rojear con la jerarquía y **NO
   rojeó**: el diseño elegido deja el `.order()` intacto. Sigue vivo verificando la mitad que no
   cambió, y se sumó `TestElOrdenDelArbol` para la que sí.
2. Dos tests rojearon con **ConnectError**, no con una aserción: el espía del cliente parcheaba
   solo `objetivo_repo`, y al mover el filtro a un satélite con su propio import, el test pegaba
   a la red. El espía ahora parchea los tres módulos.

**Impacto en infraestructura:** 🔴 **MIGRACIONES 095 y 096 PENDIENTES DE CORRER.** Orden: 095
antes que 096 (la puente referencia `objetivos`, que ya existe, pero el backfill conviene
después de la columna). **Se pueden correr con el código viejo arriba** (son aditivas y nada las
lee todavía) y **el código nuevo tolera que no estén corridas** salvo en un punto: el filtro por
responsable cae a la columna de dueño mientras la puente esté vacía, que es el comportamiento de
hoy. Sin variables de entorno, buckets, endpoints ni cambios de auth. Ninguna ruta cambió.
> ⚠️ Con la 089 (`ausencias_unicidad`) todavía sin correr, quedan **tres** migraciones pendientes
> en producción: 089, 095 y 096.

---

## 2026-08-08 · Preparación del rediseño de objetivos: 3 cortes + la red de tests que faltaba · commit pendiente

**Qué cambió:** preparación para el rediseño del modelo de objetivos (jerarquía + múltiples
responsables). **Cero cambios de comportamiento**: tres divisiones por límite de líneas y 52 tests
nuevos que describen lo que el código hace HOY.

**A · Los tres archivos ahogados**, movimiento verbatim:
- `repositories/objetivo_repo.py` **99/100 → 80**; el mapper `_build` a `_objetivo_row.py` (47).
- `components/features/objetivos/ObjetivoModal.tsx` **156/150 → 109** (ya estaba POR ENCIMA antes
  de tocarlo); los campos del form a `ObjetivoFormFields.tsx` (90). El corte va por los campos y
  no por el estado porque ese es el lado que crece: selector de padre + multi-select.
- `app/(dashboard)/objetivos/page.tsx` **149/150 → 130**; la barra de filtros a
  `ObjetivosFiltros.tsx` (68). NO se migró a `FiltersBar`/`useFiltros<Modulo>` a propósito: eso
  es un rediseño del filtro, no una división.

**B · 52 tests, en `tests/test_objetivos.py`.** El módulo tenía **CERO tests propios**: lo único
que lo tocaba era cobertura de barrido (límite de export, franja de rate limit, paridad
list↔export, limpieza de columnas), que no mira ni una regla de negocio.
🔴 **Se prueba en DOS planos, y no es redundancia:** el service con un repo falso (validación del
responsable, 404, barrera de empresa, qué filtros se pasan) y **el repo con el CLIENTE de Supabase
falseado** (los `.eq()` y el `.order()` que tienen que viajar EN LA QUERY). Un fake de repo que
filtre y ordene en Python fija el contrato pero deja la query real sin probar — es el caso #3 de
la regla del repo, y la mutación lo confirmó: **borrar el filtro de estado del repo solo rojea del
lado de la query**, los tests de service siguen en verde porque el fake filtra por su cuenta.

**Verificado por mutación — 11 mutaciones, todas cazadas:** filtro de estado borrado · orden a
descendente · `.order()` eliminado · `_validate_responsable` en no-op · deja pasar un inactivo ·
`update` validando siempre · `cambiar_estado` sin CHECK · `find_by_id` sin barrera de empresa ·
`DELETE` sin empresa en el WHERE · `delete` sin 404 · export emitiendo el UUID del responsable.

🚩 **Un test está escrito para ROJEAR con el rediseño, a propósito:**
`test_ordena_por_fecha_entrega_ASCENDENTE`. Hoy el listado sale por fecha de entrega ascendente;
con subobjetivos ese orden desarma el árbol. Cuando cambie, el test falla y obliga a decidir el
orden nuevo a propósito en vez de que se mueva de refilón.

**Verificación:** backend **2524 passed, 0 skipped** (eran 2472; +52, todos nuevos — ninguno
existente cambió de resultado) · front **498 passed, 0 skipped** (sin cambio) · `tsc --noEmit` en
0 · los barridos estructurales verdes (564) · cero imports huérfanos.

**Impacto en infraestructura:** **Ninguno.** Sin migraciones, variables de entorno, dependencias,
buckets, endpoints ni cambios de auth. Ninguna ruta cambió: las tres divisiones son internas a su
módulo y no tocan `main.py`.
> ⚠️ **Para la sesión del rediseño**, del diagnóstico previo: `objetivos` tiene **1 fila** en
> producción y **nadie la referencia por FK**, pero **dos consumidores fuera del módulo cuentan sus
> filas** — `services/procesos_service.py` (tablero de Procesos por estado) y
> `services/_reporte_anual_metricas.py:80` ("objetivos cumplidos en el año"). Con jerarquía, los
> dos empiezan a contar padres + hijos sin distinguirlos: no rompen, cambian de significado.

---

## 2026-08-08 · Últimos 3 exports: pendientes de vacaciones, vacantes y offboarding · commit pendiente

**Qué cambió:** los exports pasan de 22 a **25**. Los tres módulos exigieron dividir antes.

**A · Días de vacaciones pendientes.** `vacaciones_pendientes_service.py` (146/150) → 131, con las
tres escrituras y el literal único del 404 en `_vacaciones_pendientes_write.py`.
🔴 **Es el TERCER export del repo que puede FILTRAR DATOS**, después de /equipo y las plantillas
de onboarding: VACACIONES está en `MANDOS_MEDIOS_SECCIONES`, así que su universo no lo acota la
empresa sino el OWNERSHIP (`manager_id`). El export va por `get_all`, el mismo camino del
listado; pegarle al repo por su cuenta —aunque pasando el `empresa_id`— le entregaría a un mando
medio los días de gente que no ve en ninguna pantalla. Verificado por mutación **contra el
contenido del CSV**, no contra lo que devuelve el fake. Acepta los tres filtros del listado
(area/empleado/proyecto), aunque la pantalla todavía no los exponga.
La columna que importa es **"Sin liquidar" = días − liquidados**: es lo que la empresa todavía
debe, y en una planilla se suma por empleado o por área. Van las tres (días, liquidados, resta):
"10 y 10 liquidados" y "0 pendientes" dan los dos 0 y significan cosas distintas.

**B · Vacantes.** Router 80/80 → 57 + `vacantes_escrituras.py`; service 147/150 → 90 con las tres
escrituras de la vacante en `_vacante_write.py` (se llevan sus payloads de auditoría inline; el
ORDEN del borrado —congelar el nombre en los candidatos ANTES de borrar la fila— viaja con
`eliminar`). Export con el filtro `estado`, y el front pasa a tener **una función de traducción
compartida** (`queryVacantes`) entre listado y export.
Quedan afuera del archivo los **bloques de texto libre** (descripción, requisitos, funciones,
copy) y el `linkedin_post_id`: son párrafos que en una celda vuelven ilegible la fila, y un id
interno de otra plataforma. El `estado` sale con el texto de la pantalla, no con el enum.
⚠️ `vacantes/page.tsx` estaba en 217/150: se extrajo `VacantesTable.tsx` y bajó a **170** — sigue
sobre el límite, y el próximo corte natural es la barra de filtros. No se hizo en esta tanda.

**C · Offboarding.** Router 78/80 → 44 + `offboarding_escrituras.py`; service 149/150 → 112 con el
alta en `_offboarding_iniciar.py` (molde del hermano `_onboarding_iniciar.py`; **el orden de los
gates es load-bearing**: la barrera de empresa va ANTES del chequeo de "ya tiene uno activo", o el
409 delata que el empleado existe). Export sin filtros.
🔴 **`notas_entrevista` NO sale en el archivo**, a propósito: es texto libre que escribe RRHH
sobre por qué se fue una persona, y este es justo el archivo que se manda por mail. El flag de si
la entrevista se hizo sí sale — eso es seguimiento del proceso. Los `activos` y `accesos` van
**contados, no volcados** (son listas anidadas: el motor renderiza escalares).

**Los tres tienen 0 filas en producción**, así que nadie va a abrir estos archivos y notar que una
columna dice cualquier cosa. Por eso los fakes traen poblado justo lo que la proyección tiene que
dejar afuera —textos largos, notas de entrevista, listas anidadas—: sin eso, borrar la proyección
entera dejaba los tests en verde.

**Verificación:** 227 rutas (eran 224; las 3 nuevas son los exports, ninguna perdida, mismo path,
método y gate para el resto) · **backend 2472 passed, 0 skipped** (eran 2408) · **front 498
passed, 0 skipped** · `tsc --noEmit` en 0 · los cinco barridos estructurales verdes (558 tests),
con `test_limite_export` de 14 a 17 · 8 mutaciones aplicadas y revertidas, todas cazadas.
Cero archivos sobre su límite en backend.

**Impacto en infraestructura:** **Endpoints nuevos** — `GET /api/vacaciones-pendientes/exportar`,
`GET /api/vacantes/exportar`, `GET /api/offboarding/exportar`. Los tres autenticados (gate READ de
su sección) y bajo la franja compartida de export. 🔴 **La cuota de export ahora se reparte entre
25 endpoints**: siguen siendo 30/hora por IP para todos juntos, y con `RATE_LIMIT_STORAGE_URI=memory://`
es por proceso. Cuantos más exports, más probable que un uso normal choque contra el techo; si
aparecen 429 sin abuso, el arreglo es Redis, no subir el número. Sin migraciones, variables de
entorno, buckets ni cambios de auth.

---

## 2026-08-08 · Franja de export completa + 3 exports nuevos (usuarios, empresas, plantillas) · commit pendiente

**Qué cambió:** cuatro tandas. Los exports pasan de 19 a **22**, y **ya no queda ninguno bajo el
baseline**.

**A · La franja que faltaba.** `objetivos.py` e `inventario_items.py` estaban en 79/80 y corrían
bajo el baseline de 300/min porque el decorador no entraba. Se dividieron por lectura/escritura
sobre el mismo prefijo (`*_escrituras.py`, molde `areas_escrituras.py`) y se les puso
`shared_limit("30/hour", scope="export")`. 🔴 **El export se quedó en su router original a
propósito**: la clave del limiter es `routers.<módulo>.<función>`, así que mudarlo habría cambiado
la clave y dejado su test mirando una clave inexistente, en verde.

**A3/A4 · El test que afirmaba lo contrario se MOVIÓ, no se borró**, y de paso `TestFranjaExport`
pasó de lista escrita a mano a **barrido por introspección de `app.routes`** con guarda de mínimo.
🔴 **Hallazgo:** la lista enumeraba **10 endpoints cuando la app ya tenía 19** — los 9 que faltaban
(areas, candidatos, capacitaciones, equipo, onboarding, periodos, proyectos y los dos de esta
tanda) no estaban exentos de nada, simplemente **nadie los verificaba**, que es peor que no tener
el test. Se sumaron dos tests que el decorador solo no puede dar: que ningún export montado quede
sin franja, y que la cuota sea **compartida** (se consume desde un export y se mide el saldo desde
otro — la diferencia entre 30/hora entre todos y 30/hora **cada uno**, o sea 660/hora reales).

**B · Export de usuarios.** `usuarios.py` (77/80) se dividió; **cambiar-password y el export se
quedaron**, por lo mismo del limiter — "escrituras" acá no es literal, el criterio real es *no
mover nada decorado*. 🔴 La query del listado **vivía en el router** (pegaba a `supabase_admin`
directo): bajó al repo para que listado y archivo salgan del mismo lugar. Columnas: las cinco de
la pantalla + Activo. **Sin credenciales, sin ban, sin `must_change_password`, sin `ultimo_acceso`,
sin id** — y el fake del test trae esos campos puestos, para que borrar la proyección no pueda
quedar en verde.

**C · Export de empresas.** `empresa_service.py` (147/150) se partió: `upload_logo` salió a
`_empresa_logo.py` (se lleva Storage y su payload de auditoría). Columnas: la ficha completa, no
las 4 de la tabla — **es el único export que hoy se puede verificar mirando el archivo** (hay 2
empresas en producción) y es el que alguien usa para un trámite. Sin `logo_url` ni id.
⚠️ El front `empresas/page.tsx` estaba en **204/150** (deuda previa): se extrajo `EmpresasTable.tsx`
y quedó en 140.

**D · Export de plantillas de onboarding.** `onboarding_templates_service.py` (144/150) se partió
(las 3 operaciones sobre tareas a `_onboarding_templates_tareas.py`). **El router NO hizo falta
dividirlo** —quedó en 43/80 tras el corte previo, verificado, no asumido—. 🔴 **Es el segundo
export del repo que puede FILTRAR DATOS, no traer filas de más**: el universo lo acota la
visibilidad (públicas de mi empresa + privadas mías), que sale del token. Un export que no pase
`user_id`/`rol` entrega las plantillas privadas de otros en un archivo, sin error y sin 403.
Verificado por mutación contra **el contenido del CSV generado**, no contra lo que devuelve el fake
— la primera versión de ese test comparaba contra el fake y **sobrevivía a la mutación**.

**Verificación:** 224 rutas (eran 221; las 3 nuevas son los exports, ninguna perdida, mismo path,
método y gate para el resto) · **backend 2373 passed, 0 skipped** (eran 2262) · **front 498 passed,
0 skipped** · `tsc --noEmit` en 0 · los cinco barridos estructurales verdes, con sus mínimos
subidos (`test_limite_export` de 11 a 14) · 14 mutaciones aplicadas y revertidas, todas cazadas.
Cero archivos sobre su límite de líneas en backend y en los tocados del front.

**Impacto en infraestructura:** **Endpoints nuevos** — `GET /api/usuarios/exportar`,
`GET /api/empresas/exportar`, `GET /api/onboarding/templates/exportar`. Los tres **autenticados**
(gate READ de su sección), los tres bajo la franja compartida de export. 🔴 **Para el que monte
AWS:** la cuota de export es de **30/hora por IP compartida entre los 22 endpoints**, y con
`RATE_LIMIT_STORAGE_URI=memory://` es **por proceso** — con N instancias vivas el límite efectivo
es N×30. Con 3 personas en RRHH exportando, esa franja se puede volver molesta antes que
protectora: si aparecen 429 en uso normal, el arreglo es Redis, no subir el número. Sin
migraciones, variables de entorno nuevas, buckets ni cambios de auth.

---

## 2026-08-08 · Los 61 tests `async def` podían saltearse en silencio · commit pendiente

**Qué cambió:** solo **configuración de test** — cero líneas de producción y cero tests tocados.

- **El síntoma (Windows):** 61 tests `async def` en 14 archivos reportados como *skipped* con
  "async def function and no async plugin installed", **contados dentro del total**. Entre ellos
  `test_critical_flows` (13), `test_usuario_estado` (9), `test_assessment_modulo_flag` (8),
  `test_rate_limit` (6), `test_envio_exige_empresa` (5) y los tres exports nuevos del 7/8
  (`areas` 3, `proyectos` 2, `equipo` 2).
- **La causa NO era `pytest.ini`:** `asyncio_mode = auto` ya estaba y está tracked. 🔴 **Si
  `pytest-asyncio` no está cargado en el intérprete que corre pytest, esa clave no da error: se
  ignora con un warning (`Unknown config option: asyncio_mode`) y los async no fallan, se
  SALTEAN.** El venv de Windows tenía `pytest-asyncio 0.23.8`, que ni siquiera cumplía el
  `>=0.24.0` declarado — o sea que nunca se instaló desde `requirements-dev.txt`. Rangos abiertos
  + instalación manual = la suite dependía de lo que cada máquina hubiera resuelto.
- **`backend/pytest.ini`** suma `required_plugins = pytest-asyncio` (pytest **aborta al arrancar**
  con exit 4 en vez de reportar verde a medias) y `addopts = -rs` (todo skip queda listado con su
  razón, sin depender de acordarse del flag). Verificado con `-p no:asyncio`.
- **`backend/requirements-dev.txt`** pasa de rangos abiertos a **versiones exactas**
  (`pytest==9.1.1`, `pytest-asyncio==1.4.0`, `httpx==0.27.2`, la misma que producción).
- **En la Mac nunca pasó** (0 skipped) y **los 61 pasan todos** al ejecutarse: ninguno estaba mal
  escrito ni destapó un bug. El conteo real de la suite es **2262**; el número que se venía
  reportando en Windows incluía 61 que no corrían.

**Impacto en infraestructura:** **Dependencias** — `requirements-dev.txt` queda pinneado. Es
**solo de desarrollo/CI, NO entra al deploy** (`requirements.txt` de producción no se tocó), así
que Vercel y la imagen de AWS no cambian. Lo único a saber: cualquier máquina o pipeline que corra
la suite tiene que hacer `pip install -r requirements-dev.txt` **después de este cambio**, o pytest
aborta de entrada con `Missing required plugins: pytest-asyncio` — que es exactamente el
comportamiento buscado. Sin migraciones, variables de entorno, buckets, endpoints ni cambios de auth.

---

## 2026-08-07 · BLOQUE D · Tres barridos estructurales + la auditoría que faltaba en tres módulos + **migración 094** · commit `1b972a8`

> 📌 **Entrada escrita el 12/8/2026, cinco días tarde.** Es la ÚNICA que se escribió fuera de su
> sesión, y se detectó en la auditoría de documentación del 12/8: el bloque D era el único de los
> doce cerrados sin entrada. Se deja anotado en vez de disimularlo, porque **lo que se perdió por
> escribirla tarde es justamente lo que la bitácora existe para transmitir**: la migración 094
> estuvo cinco días sin aparecer en el único documento que el dev de infra lee para saber qué
> tiene que correr. El contenido de abajo se reconstruyó del commit y del catálogo vivo.

**Qué cambió:** 27 archivos, +1928/−136. Tres cosas distintas en un commit:

1. **Tres barridos estructurales nuevos** — `test_callers_huerfanos.py` (símbolos de `services/` y
   `repositories/` que nadie llama, y endpoints montados que el front nunca pide),
   `test_auditoria_coherente.py` y la extensión de `test_selects_repos.py` a **todos** los repos,
   más los dos helpers `_barrido_callers.py` y `_barrido_auditoria.py`.
2. **La auditoría que faltaba en tres módulos** — adjuntos (incluida la marca de principal),
   logo de empresa y vacantes/candidatos, con sus payloads en `_audit_payloads_adjuntos.py` y
   cuatro archivos de test nuevos.
3. 🔴 **`backend/migrations/094_recrear_triggers_empresa.sql`** — la función `fn_misma_empresa()`
   y los triggers `trg_emp_*`, extraídos 1:1 del catálogo de producción.

### 🔴 ACCIÓN DE INFRAESTRUCTURA — la 094 es OBLIGATORIA en el rebuild, y NO está en `schema.sql`

**El agujero que cierra:** `fn_misma_empresa()` y los `trg_emp_*` **existían SOLO en producción**.
No estaban en `db/schema.sql` (el snapshot se lee del catálogo y captura tablas, columnas,
constraints, índices y defaults — **0 funciones y 0 triggers**), no estaban en la 077 de
`migracionAWS/` (que recrea únicamente los de `updated_at`) y no estaban en ninguna migración
001–093: se aplicaron a mano durante el retrofit multiempresa y nunca se versionaron.
**Un rebuild desde cero —que es exactamente lo que se va a hacer en RDS— los perdía en silencio.**

**Qué se pierde sin ellos, y por qué no es cosmético.** Son la **única defensa a nivel base**
contra el cruce de empresas por referencia. Una FK garantiza que `empleados.area_id` apunta a un
área que **existe**; no garantiza que esa área sea de la **misma empresa** que el empleado. Sin el
trigger, un INSERT que cruce empresas entra sin error y queda como **dato corrupto silencioso**:
el listado de la empresa A muestra un empleado cuya área es de la B. La barrera de aplicación
(Fase 2) cubre el camino de la API, **no** un INSERT por SQL directo ni un import mal armado.

🔑 **Y no hay red debajo: verificado contra el catálogo el 12/8/2026, de los 12 pares
(columna → tabla padre) que vigilan los triggers vivos, CERO tienen una FK compuesta que los
respalde.** El modelo sí usa ese patrón —hay **22 FKs compuestas** `(x_id, empresa_id) → padre(id,
empresa_id)` en producción— pero sobre otras columnas. Estos 12 pares quedaron fuera de ese
patrón, y el trigger es lo único que los sostiene:

| Tabla | Columnas vigiladas |
|---|---|
| `areas` | `area_padre_id` → `areas` · `responsable_id` → `empleados` |
| `empleados` | `area_id` → `areas` · `manager_id` → `empleados` |
| `vacantes` · `onboarding_templates` | `area_id` → `areas` |
| `planes_carrera` | `responsable_id` → `empleados` *(la FK compuesta que existe es sobre `empleado_id`, que es otra columna)* |
| `assessment_campanas` | `area_id` → `areas` |
| `assessment_links` · `assessment_resultados` | `empleado_id` → `empleados` · `candidato_id` → `candidatos` |

**Qué hay que hacer, en orden:** correr `094_recrear_triggers_empresa.sql` **UNA vez, DESPUÉS de
`db/schema.sql`**, junto con la 077. Es idempotente (`CREATE OR REPLACE` + `DROP TRIGGER IF
EXISTS`). **En producción NO hace falta**: los triggers ya están ahí. Existe **para el rebuild**.

> 🔴 **PENDIENTE ABIERTO detectado el 12/8, y bloquea el rebuild: la 094 quedó desincronizada de
> la 112.** Declara **9** triggers, y el noveno es `trg_emp_sucesion` **sobre
> `sucesion_posiciones`, una de las 11 tablas que la 112 dropeó**. Producción tiene **8** (contados
> hoy: `SELECT count(*) ... WHERE p.proname = 'fn_misma_empresa'` → 8), así que el archivo pide una
> tabla que ya no existe. Un replay de `schema.sql` (52 tablas) seguido de la 094 **aborta**:
> `DROP TRIGGER IF EXISTS x ON tabla` falla igual si la que no existe es la **tabla**, no el
> trigger. **Es la MISMA mina que J5a ya desactivó en la 077** —de ahí se sacaron los 8
> `updated_at` de las tablas muertas— y a la 094 no se le hizo. Hay que sacarle el bloque de
> `trg_emp_sucesion` (líneas 82-85) y corregir el comentario de verificación final, que dice "debe
> devolver 9". **No se tocó en esta sesión: editar una migración es cambio de migración, y esta
> sesión era de documentación.**
>
> **Migraciones:** la **094**, con la salvedad de arriba. **Variables de entorno / dependencias /
> buckets / endpoints públicos / auth / dominios:** ninguno.

---

## 2026-08-07 · Export en /equipo — el único que puede filtrar datos · commit pendiente

**Qué cambió:** **`GET /api/equipo/exportar`**. Los exports pasan de 18 a **19**. Va solo, sin
juntarlo con otros módulos, por un motivo: es el ÚNICO export del repo donde equivocarse **filtra
datos**, no filas de más.

🔴 **En todos los demás módulos el universo lo acota un Query** (`estado`, `area_id`,
`empresa_id`) y el peor caso es un archivo con más filas de las que se ven. **Acá lo acota el
OWNERSHIP** (`ids_empleados_visibles(user_id, rol)`), así que un export con consulta propia le
entregaría a un `mandos_medios` la nómina de gente que no puede ver en ninguna otra pantalla — sin
error y con el archivo ya bajado. Por eso `EquipoService.exportar` **llama a `get_equipo`**, no
reconstruye nada: el conjunto sale del mismo lugar en las dos superficies.

**Dos propiedades que quedaron fijadas por test, no por comentario:**
- **El ownership CRUZA empresas y el export no lo recorta.** Un mando puede tener subordinados de
  otra empresa del grupo (`_alcance_mandos.py`), y el repo filtra solo por `in_("id", ids)`.
  Sumarle un `.eq("empresa_id")` "por consistencia" haría desaparecer a esa persona del archivo.
- **El export expone TRES columnas** (Apellido · Nombre · Empresa) y nada más. `mandos_medios`
  llega a /equipo **sin** permiso de EMPLEADOS: agregarle cargo, área o fecha de ingreso
  convertiría este export en la puerta de atrás a la ficha del empleado.

**Verificado por mutación:** reemplazando `get_equipo(user_id, rol)` por una consulta propia sin
filtro, **7 tests rojean** — incluido el paramétrico que compara listado y export por
comportamiento para los 6 pares (usuario, rol).

**Impacto en infraestructura:** **Ninguno.** Sin migraciones, variables de entorno, dependencias
ni buckets. ⚠️ Un endpoint nuevo dentro del prefijo `/api/equipo` que ya existía; entra en la
cuota compartida de export (30/hora por IP, **por proceso** mientras el store sea `memory://`).
🔴 **Para el que monte AWS:** este endpoint es el que peor tolera un error de identidad —
si el JWT resolviera mal el `user_id` o el `rol`, el archivo sale con el universo equivocado y
nada lo delata. El gate es `Seccion.VACACIONES + READ`, el mismo que el listado.

## 2026-08-07 · Export en candidatos, períodos, catálogo de capacitaciones y onboarding · commit pendiente

**Qué cambió:** cuatro exports nuevos, todos con el molde de `inventario/items`. Los exports pasan
de 14 a **18**. Ninguno de los cuatro obligó a dividir un archivo.

- `GET /api/candidatos/exportar` · `GET /api/periodos/exportar` ·
  `GET /api/capacitaciones/exportar` (CATÁLOGO) · `GET /api/onboarding/exportar`.
- Los cuatro con `shared_limit("30/hour", scope="export")` y `verificar_limite_export`, y
  `/exportar` declarado **antes** de `/{id}`.

**Tres cosas que no eran obvias y condicionan el resultado:**
- 🔴 **`capacitaciones` SÍ tenía filtro** (`solo_activos`), al contrario de lo que decía el
  relevamiento. El export lo acepta: sin él, el archivo traería las capacitaciones inactivas que
  la tabla oculta. Los otros tres no tienen filtros, así que la invariante sale gratis.
- 🔴 **`InstanciaResponse.fecha_inicio` es un `str`, no un `date`.** El `_fecha` que usan los
  otros exports (llama a `.strftime`) reventaría con `AttributeError`. `_onboarding_export` parsea
  el ISO y cae al crudo si no matchea.
- ⚠️ **`periodos` no exporta `cerrado_por` / `reabierto_por`**: son UUIDs de `users` y el repo no
  resuelve el nombre. El "quién" está en `auditoria`, que sí lo resuelve al renderizar.

**Impacto en infraestructura:** **Ninguno.** Sin migraciones, variables de entorno, dependencias
ni buckets. ⚠️ **Cuatro endpoints nuevos**, todos dentro de prefijos que ya existían. Entran en la
cuota compartida de export (30/hora por IP), que sigue siendo **por proceso** mientras
`RATE_LIMIT_STORAGE_URI` sea `memory://` — ahora la comparten 18 endpoints en vez de 14.
🔴 **Los cuatro módulos tienen 0 o 1 fila en producción**, así que estos exports **no se pueden
verificar contra datos reales**: las columnas se eligieron leyendo el schema y lo que muestra cada
pantalla, y la única red que tienen son los tests.

## 2026-08-07 · Corte de areas.py + export de áreas · commit pendiente

**Dos cambios, en este orden.**

**1 · Refactor.** `routers/areas.py` estaba en 72/80 y el export mide +10, así que primero se
partió: **`routers/areas_escrituras.py`** se lleva POST/PUT/DELETE y se monta en el **MISMO
prefijo** `/api/areas`. Molde: `costos_escrituras.py` y `onboarding_templates_escrituras.py`.
**Las rutas no cambiaron**: mismo path, mismo método y mismo gate — verificado ejercitando cada
dependency con `gerencia_lectura`, no leyendo el decorador. `_empresa_str` se importa de
`routers.areas` en vez de duplicarse (patrón `sujeto` de onboarding_templates_escrituras).
Movimiento verbatim: cero lógica reescrita. `areas.py` 72 → **46**, escrituras **64**, `main.py`
173 → **175**. La suite quedó en 2157, el mismo número que antes del corte.

**2 · Feature.** **`GET /api/areas/exportar`**, con el filtro `empresa_id` — el mismo que el
listado — y proyección propia en `services/_areas_export.py`. Los exports pasan de 13 a **14**.
Lleva `shared_limit("30/hour", scope="export")` y `verificar_limite_export`; los dos barridos lo
incorporaron solos.

**Dos límites conocidos, anotados en el código:**
- ⚠️ **El export de áreas NO tiene columna "Empresa".** `AreaResponse` no trae `empresa_nombre`
  —solo el UUID, que no puede salir—, así que en modo consolidado el archivo mezcla las áreas de
  las dos empresas sin distinguirlas, y **hay un "Sistemas" por empresa**. El workaround es
  exportar con el filtro. Cerrarlo es sumar `empresa_nombre` al SELECT de `area_repo`: cambio
  propio, toca schema + mapper.
- ⚠️ **El buscador de `/areas` es CLIENT-SIDE**, así que el archivo trae todas las áreas de la
  empresa, no las que el buscador deja a la vista. Con 12 áreas es tolerable (mismo criterio que
  el listado de evaluaciones); el día que crezca, ese `search` tiene que pasar al backend.

**Impacto en infraestructura:** **Ninguno.** Sin migraciones, variables de entorno, dependencias
ni buckets. ⚠️ **`main.py` monta un router más sobre `/api/areas`** — si hay reglas de ruteo por
path del lado de la infra, el prefijo no cambió, solo el módulo que atiende POST/PUT/DELETE.
🔴 **Para el que porte a asyncpg:** `areas_escrituras.py` importa `_empresa_str` de `areas.py`,
así que los dos archivos se mueven juntos.

## 2026-08-07 · Export de proyectos (y por qué areas quedó afuera) · commit pendiente

**Qué cambió:** **`GET /api/proyectos/exportar`** — el módulo de proyectos ya exporta en pdf /
excel / csv / word, con los MISMOS filtros que el listado (`estado`, `area_id`) y la misma empresa
del header. Cadena copiada del molde `inventario/items`: router → service → proyección propia
(`services/_proyectos_export.py`) → `build_export`. Los exports pasan de 12 a **13**.

- El costeo (`CosteoResumen`, objeto anidado) **se aplana en tres columnas** — el motor renderiza
  escalares, así que sin aplanar la celda saldría con el `repr` de Python; y "costo acumulado" y
  "presupuesto restante" son justo lo que alguien abre el Excel para mirar.
- `% consumido` sale **vacío**, no `0%`, cuando el presupuesto es 0: no hay contra qué medir, y
  "cero por ciento consumido" es una afirmación distinta y falsa.
- Lleva `shared_limit("30/hour", scope="export")` y `verificar_limite_export`. Los dos barridos
  (`test_paridad_list_export`, `test_limite_export`) lo incorporaron **solos**, sin tocarlos.

🔴 **`areas` NO se implementó, por límite de líneas.** `routers/areas.py` está en **72/80** y el
bloque de export mide **+10** (2 imports + endpoint de 5 líneas + 2 blancos + el comentario de
orden de rutas) → **82/80**. La medición salió del delta real de `proyectos.py` (66 → 76), no de
una estimación. **El corte propuesto está abajo y no se escribió.**

**Impacto en infraestructura:** **Ninguno.** Sin migraciones, variables de entorno, dependencias
ni buckets. ⚠️ **Un endpoint nuevo montado** (`GET /api/proyectos/exportar`), dentro del prefijo
`/api/proyectos` que ya existía. Entra en la cuota compartida de export (30/hora por IP), que
sigue siendo **por proceso** mientras `RATE_LIMIT_STORAGE_URI` sea `memory://`.

## 2026-08-07 · Cobertura del módulo de mails: guardado de plantillas e idempotencia · commit pendiente

**Qué cambió:** solo tests — **cero líneas de producción**. Se cerraron los dos huecos que el plan
marcaba como T2 y T3, con dos archivos nuevos (47 tests).

- **T2 · `plantillas_service.guardar` / `.borrar`** no tenían ningún test. Lo que existía cubría
  los gates y el render. 🔴 **Hallazgo:** `test_mail_variables.py` prueba `variables_invalidas`
  **como función suelta**, así que anular el `if malas: raise` de `guardar` dejaba esa suite
  ENTERA en verde y la plantilla rota se guardaba igual. Verificado por mutación.
- **T3 · `MailEnviadoRepo.ya_enviado`** estaba probada solo contra fakes de repo. Ahora se prueba
  contra el **cliente de Supabase falseado**, que registra los `.eq/.gte/.limit`. 🔴 **Hallazgo:**
  borrar el `.eq("estado", "enviado")` deja `test_mail_envio.py` y `test_envio_libre.py` en verde
  — o sea que la garantía de "nadie recibe el mismo mail dos veces" no estaba realmente fijada.
- Queda fijado además el registro del **fallo** (`estado='fallido'` + motivo) desde el punto de
  salida único, y las **dos ramas** de destinatario de la idempotencia (empleado / dirección libre).

**Impacto en infraestructura:** **Ninguno.** Sin migraciones, variables de entorno, dependencias,
buckets ni endpoints. ⚠️ Para el que monte AWS, lo único relevante: estos tests **no tocan la red
ni la base** (falsean el cliente de Supabase), así que corren igual del otro lado del cutover. El
que sí va a haber que reescribir cuando `mail_enviado_repo` se porte a asyncpg es
`test_mail_enviado_repo.py`, porque afirma sobre la API de PostgREST (`.eq/.gte`), no sobre SQL.

## 2026-08-07 · Envío de plantillas a direcciones escritas a mano · commit pendiente

**Qué cambió:** el modal de `/comunicacion` ahora tiene **dos modos**: empleados del sistema (lo
que había) o **direcciones de mail escritas a mano**. `EnvioRequest` suma
`destinatarios_libres: List[str] = []` — **campo opcional con default, así el caller que ya
existía no se toca**.

**Cuatro decisiones que condicionan el uso:**
- 🔴 **Una plantilla con `{{variables}}` NO se puede mandar a una dirección suelta.** Sin empleado,
  el render deja la variable en "" y el mail sale con un hueco donde iba el nombre de la persona.
  La UI deshabilita el modo con el motivo a la vista **antes** de apretar; el backend lo verifica
  igual (422 `PLANTILLA_CON_VARIABLES`), porque la pantalla no es la frontera.
  ⚠️ El predicado es "usa ALGUNA variable", más restrictivo de lo estrictamente necesario:
  `{{empresa_nombre}}`, `{{fecha_hoy}}` y `{{hora_ahora}}` sí resolverían sin empleado. Se eligió
  así porque el costo de los dos errores no es simétrico. La perilla para aflojarlo es una sola
  función (`plantilla_usa_variables`).
- 🔴 **Los dos modos son EXCLUYENTES.** Un body con las dos listas se rechaza (422
  `ENVIO_MODO_MIXTO`): la regla de las variables aplica a un modo y no al otro, así que un lote
  mixto sería mitad permitido.
- **Formato validado en las dos puntas**, con el mismo patrón conservador. Una dirección mal
  escrita **rechaza el lote entero** (422 `EMAIL_INVALIDO`, con la lista de cuáles): la escribió
  una persona hace un segundo y corregirla es inmediato. Tope de **50** direcciones por envío.
- **La idempotencia también vale acá.** Sin `empleado_id`, `MailEnviadoRepo.ya_enviado` pregunta
  por `destinatario`. Sin eso, un lote cortado por presupuesto reenviaría a gente de afuera.

**Impacto en infraestructura:** **Ninguno.** Sin migraciones, variables de entorno, dependencias,
buckets ni endpoints nuevos. `mail_enviado.empleado_id` ya era nullable y la FK es
`ON DELETE SET NULL`, así que un envío libre entra sin tocar el schema. ⚠️ **Para el que monte
AWS:** el índice `idx_mail_enviado_idempotencia` es `(plantilla_clave, empleado_id, created_at)` y
**no cubre la consulta por `destinatario`** que usa el modo libre. Con el volumen de hoy no se
nota; si el envío a direcciones sueltas se vuelve frecuente, hace falta un índice hermano por
`(plantilla_clave, destinatario, created_at)`. No se creó ahora para no meter una migración por
una consulta que todavía no tiene tráfico.

## 2026-08-07 · Módulo Comunicación: ruta propia + historial de mails · commit pendiente

**Qué cambió:** las plantillas de mail salieron de `/configuracion` a una ruta propia
**`/comunicacion`**, con entrada en el sidebar (grupo "Operación") y **dos pestañas**: Plantillas
(mudada tal cual) e **Historial**. El motivo no es estético: mientras fue el ABM de un texto que
se toca dos veces al año, vivir dentro de configuración era correcto; desde que se manda mail a la
gente desde ahí, es operación recurrente e irreversible.

**El historial es feature nueva de punta a punta.** `mail_enviado` se escribía desde la migración
087 y **no lo leía nadie**: `MailEnviadoRepo.ultimos()` no tenía un solo caller y no existían ni
service ni router. Ahora hay **`GET /api/mails`** (router nuevo `routers/mail_historial.py` +
`services/mail_historial_service.py`), con filtro por **estado** y por **rango de fechas**,
ordenado por fecha descendente.

**Cuatro decisiones que condicionan lo que se puede pedir después:**
- 🔴 **NO hay export, y no se le agrega uno.** `mail_enviado` guarda datos personales por
  definición —nombre, dirección y el cuerpo entero del mail—. La decisión ya estaba escrita en el
  repo y se respetó en vez de reabrirla. Consecuencia: este listado **no entra** en
  `test_paridad_list_export.py`, que solo empareja listados que tienen export.
- 🔴 **NO pagina.** Techo duro de **200** filas en el repo, con `limite` en la respuesta para que
  la pantalla avise que ve un recorte. Paginar convertiría un diagnóstico acotado en un volcado.
- **El `select` es una allowlist**: `cuerpo_render` no sale del backend.
- **NO se creó una `Seccion` de permisos nueva.** `/comunicacion` se gatea con `configuracion`,
  que es lo que el backend ya exigía en plantillas, envío e historial. `puede()` es genérica
  (admin escribe · gerencia lee · mandos_medios no entra), así que una sección propia daba el
  mismo resultado a cambio de tocar el espejo manual `permisos.py` ↔ `permisos.ts`.

**Impacto en infraestructura:** **Ninguno.** Sin migraciones, variables de entorno, dependencias
ni buckets. ⚠️ **Un endpoint nuevo montado: `GET /api/mails`** (con auth y gate de permisos, no
público) — el prefijo `/api/mails` es nuevo en `main.py`, tenerlo en cuenta si hay reglas de ruteo
por path del lado de la infra. 🔴 **Para el que monte AWS:** el historial es la primera pantalla
que lee `mail_enviado`, así que esa tabla pasa a tener tráfico de lectura además de escritura —
conviene que el índice por `created_at` exista antes de que la tabla crezca.

## 2026-08-07 · El envío de mails exige empresa concreta (era Optional) · commit pendiente

**Qué cambió:** `POST /api/plantillas/enviar` resolvía la empresa con `get_empresa_id` (Optional),
a diferencia del `guardar` y el `borrar` del **mismo router**, que usan `require_empresa_id`. Con
`None`, `PlantillaMailRepo.find` saltea la plantilla PROPIA y resuelve la GLOBAL: **existiendo una
global con la misma clave, el mail salía con un texto DISTINTO del que muestra la pantalla, con
200 y sin ninguna señal**, y el evento de auditoría quedaba con `empresa_id NULL` — fuera del
filtro por empresa de `/auditoria`. La UI ya lo evitaba exigiendo empresa elegida; el endpoint
seguía abierto. Ahora usa `require_empresa_id`, resuelto **en su propia línea, antes de construir
el service**, así nada se arma para un pedido que se va a rechazar.

**Además, el mensaje de `EMPRESA_ID_REQUIRED` pasó a ser accionable.** Decía *"empresa_id
requerido para esta operación"* — jerga de backend que el front muestra **tal cual** en una
pantalla de RRHH, y que no dice qué hacer. Ahora dice que hay que elegir una empresa en el
selector. **El `code` no cambió**, así que nada que dependa de él se entera.

**Impacto en infraestructura:** **Ninguno.** Sin migraciones, variables de entorno, dependencias,
buckets ni endpoints nuevos. ⚠️ **Cambio de contrato menor, para el que integre:** ese endpoint
ahora responde **400 `EMPRESA_ID_REQUIRED`** cuando `X-Empresa-Id` viene ausente o en `"todas"`.
Antes respondía 200 o 404 según hubiera o no una plantilla global. Cualquier cliente que llamara
sin empresa —hoy no existe ninguno— pasa a recibir 400. 🔴 **`require_empresa_id` lo usa también
`routers/configuracion.py`**: el texto nuevo del error sale por ahí igual, y es el único otro
lugar afectado por el cambio de mensaje.

## 2026-08-07 · `page_size=200` contra un endpoint que topea en 100 · commit pendiente

**Qué cambió:** dos selectores de empleados pedían `page_size=200` a `GET /api/empleados`, que
declara `Query(20, ge=1, le=100)`. **No devolvían menos filas: el request moría en 422**, y el
`.catch` de cada hook lo convertía en una lista vacía. El modal de envío de plantillas decía "No
hay empleados activos" y el modal "Asignar empleados" de proyectos decía "Sin candidatos", los dos
con **31 empleados activos en la base** (19 en SERVICIOS Y CONSULTORIA, 12 en KARSTEC - IT NET).
El de proyectos venía roto desde antes; el de plantillas nació roto la semana pasada por copiarle
el 200.

**Tres cosas, no una:**
- El valor pasó a **`MAX_PAGE_SIZE`**, constante nueva en `services/api.ts` — espejo del `le=100`
  que declaran **los seis routers paginados** (`empleados`, `vacaciones`, `vacaciones_pendientes`,
  `ausencias`, `auditoria`, `proyecto_horas`).
- 🔴 **Los dos `.catch` mudos.** La carga se extrajo a `components/features/shared/cargarEmpleados.ts`
  (molde: `cargarProyectos`) y ahora deja **tres estados distinguibles**: cargando · error · lista
  vacía de verdad. En error la UI dice "No se pudieron cargar los empleados" y ofrece **Reintentar**
  (`components/ui/ErrorCarga.tsx`, nuevo). Sin esto el fix era cosmético: el próximo fallo volvía a
  ser invisible.
- 🔴 **Barrido nuevo `services/pageSize.test.ts`**: descubre los call sites leyendo el código y
  verifica que ninguno se pase de `MAX_PAGE_SIZE`. **El test que existía (`empleados.test.ts`)
  llamaba con `pageSize: 200` y pasaba**, porque mockea `apiFetch` entero y el fake no puede
  modelar la validación del backend.

**Impacto en infraestructura:** **Ninguno.** Sin migraciones, variables de entorno, dependencias,
buckets ni endpoints nuevos — no se tocó una línea de backend. ⚠️ **Dato para el que monte AWS:**
el `le=100` de los routers ahora tiene un espejo explícito en el front (`MAX_PAGE_SIZE`). **Si
alguna vez se sube el tope de un router, hay que subir también ese const**, y al revés: quedan
declarados el uno junto al otro en el docstring de `services/api.ts`. El barrido no puede
verificar el lado Python, así que ese par es espejo manual — como `permisos.ts` ↔ `permisos.py`.

## 2026-08-07 · El envío de mails ya tiene punta en el front · commit pendiente

**Qué cambió:** `POST /api/plantillas/enviar` existía montado, testeado y **sin un solo caller en
el front** desde que se hizo el módulo de mails — el segundo caso igual en el mismo módulo, después
de `set_remitente`. Ahora hay un botón **"Enviar" por fila** en `PlantillasSection` (dentro de
`/configuracion`, gateado por el mismo `editable` que Editar) que abre un modal de destinatarios:
elegir → confirmar con el número explícito → resumen. Se agregó el wrapper `enviarPlantilla` en
`services/plantillas.ts`, que era la pieza que faltaba. **El endpoint sale de la lista de
excepciones de `tests/test_callers_huerfanos.py`** (`destinatarios_pendientes` sigue ahí, con su
razón reescrita: es lo único de mails que todavía no tiene punta).

**Dos decisiones que condicionan la operación, no el deploy:**
- 🔴 **En modo consolidado ("Todas las empresas") NO se puede enviar**, y el botón lo dice. El
  backend usa `get_empresa_id` (Optional) y con `None` `PlantillaMailRepo.find` **solo encuentra la
  plantilla GLOBAL**: el mail saldría con un texto distinto del que se ve en pantalla, sin ningún
  error. Para una acción irreversible ese es el peor desenlace, así que la pantalla lo bloquea.
- 🔴 **El resultado se muestra con los cinco números, no como un "Enviado".** El backend manda de a
  uno con presupuesto de tiempo (~120 s) y puede devolver un 200 que significa "salieron 30 de 50".

**Impacto en infraestructura:** **Ninguno.** Sin migraciones, variables de entorno, dependencias,
buckets ni endpoints nuevos — el endpoint ya existía. 🔴 **Dos cosas que ahora sí se van a ejercitar
en producción por primera vez y conviene tener a mano el día del cutover:** (1) el envío usa la
**casilla del sistema** de Gmail (`MAIL_SIN_REMITENTE`, 400, si no está configurada), o sea que
depende del OAuth de Google y de sus scopes; (2) el endpoint lleva rate limit propio **20/hora,
franja `mail`**, y como el store es `memory://` **por proceso**, en serverless el límite efectivo es
N×instancias — mismo caveat que el resto de las franjas, pero acá cada request manda correo real.

## 2026-08-06 · No se puede dar de baja al usuario que sostiene la casilla del sistema · commit pendiente

**Qué cambió:** `DELETE /api/usuarios/{user_id}` ahora rechaza con **409
`USUARIO_ES_REMITENTE_SISTEMA`** la baja del usuario del que cuelga la casilla de correo del
sistema. Antes no había ninguna guarda: bajar a esa persona apaga el envío de mails de **todo el
sistema** (no solo los suyos) y nadie se enteraba hasta que alguien intentaba mandar uno y le
saltaba `MAIL_SIN_REMITENTE`. El chequeo corre **antes** de tocar al usuario. La guarda vive en
`services/_usuario_remitente.py` (satélite nuevo; con el razonamiento adentro, `usuario_service`
se iba a 171/150).

**Impacto en infraestructura:** **Ninguno.** Sin migraciones, variables de entorno, dependencias,
buckets ni endpoints nuevos. 🔴 **El `ON DELETE CASCADE` de `usuario_integraciones.user_id →
users(id)` NO se tocó** — la guarda es de aplicación, a propósito: desde el 3/8 la baja es blanda
(`activo=false` + ban) y ese CASCADE ya no se dispara por esta vía, pero el `activo=false` apaga
el envío igual porque la integración queda colgando de un usuario inactivo. **El agujero existe
aunque el CASCADE nunca corra**, así que no se puede cerrar desde la base.

**Para el que opere el sistema:** si hay que dar de baja a la persona que hoy es la casilla, el
orden es: Configuración → Integraciones → designar otra casilla del sistema → recién ahí la baja.
El mensaje del 409 lo dice.

⚠️ **La guarda es FAIL-OPEN:** si no se puede leer quién sostiene la casilla (Supabase caído), la
baja **sigue** y se loguea a ERROR. Deliberado: dar de baja es una acción de seguridad y no puede
quedar bloqueada por un subsistema no relacionado; lo que la guarda evita es un error operativo
recuperable. Fail-closed convertiría un blip de base en "no se puede echar a nadie".

🔴 **Para quien toque `IntegracionRemitenteRepo.get_remitente()`: el `select("*")` es contrato,
no comodidad.** De esa fila salen el `user_id` que mira esta guarda y los tokens que usa el
mailer. Angostarlo a "las columnas que se usan" apagaría la guarda **en silencio** y rompería el
envío, con toda la suite de service en verde. Hay un test que lo fija
(`test_usuarios.py::TestLaFilaDelRemitenteTraeElUserId`).

---

## 2026-08-06 · El import de costos emite un evento de auditoría por lote · commit pendiente

**Qué cambió:** `POST /api/importacion/nomina/confirmar` persistía el lote de sueldos sin emitir
ningún evento, así que un import de nómina era invisible en `/auditoria`. Ahora emite **uno por
lote** (`evento="importacion_costos"`, `entidad="nomina"`). El `confirmar` era el único de los
tres imports **sin capa de service** —iba router → repo directo, con el armado de las filas y el
conteo dentro del handler—: se creó `services/nomina_import_service.py` y el router bajó de 70 a
**57** líneas. El handler ahora extrae `usuario_id` de `request.state.user` (antes no lo hacía,
así que el evento no habría dicho quién importó).

**Impacto en infraestructura:** **Ninguno.** Sin migraciones, sin variables de entorno, sin
dependencias, sin buckets, sin endpoints nuevos ni cambios de auth. La ruta, su método, su
contrato de request/response y su rate limit (franja `import`, 10/hora compartida) quedan
**idénticos** — el front no necesita redeploy coordinado.

**Para el que mire `/auditoria`:** aparece un `evento` nuevo, `importacion_costos`. 🔴 **No
confundirlo con `importacion_nomina`**, que es el del roster de EMPLEADOS. El nombre viejo quedó
pegado a "nómina" cuando era el único import y **no se puede renombrar**: hay eventos en
producción con ese valor y `auditoria` es inmutable, así que renombrarlo partiría el historial en
dos nombres para la misma operación. Se distinguen por `entidad`: `empleado` el del roster,
`nomina` el de sueldos.

⚠️ **El evento NO lleva `importados`/`actualizados`, y es deliberado.** El upsert de PostgREST
devuelve las filas resultantes pero no dice cuáles fueron INSERT y cuáles UPDATE; esa distinción
solo vive en el `es_actualizacion` que el cliente manda en el body. El evento cuenta
`filas_persistidas` desde el retorno del repo (autoritativo), más `filas_enviadas` y un `parcial`
derivado. La respuesta HTTP sí conserva el desglose para la pantalla.

---

## 2026-08-06 · Auditoría etiquetada con la empresa de la ENTIDAD, no del header · commit pendiente

**Qué cambió:** dos eventos de auditoría (`set_presupuesto` y `baja_candidato`) se etiquetaban
con el `X-Empresa-Id` del header en vez de con la empresa de la entidad afectada, violando
"Vista vs Acción" (el selector del sidebar es visual y no gobierna una escritura). En modo
consolidado el header es `None`, así que el evento quedaba sin empresa aunque la entidad sí la
tuviera. En los dos casos el dato ya viajaba en el SELECT y el **mapper del repo lo descartaba**,
así que el fix fue de tres piezas por instancia: declarar `empresa_id` en el schema de respuesta
(`PresupuestoResponse`, `CandidatoResponse`), mapearlo en el repo (`_to_presupuesto`, `_crow`) y
usarlo en el call site. `cargar_nomina` ya lo hacía bien y quedó como molde. **El import de
costos NO se tocó** — su falta de auditoría es tarea aparte (E1 del plan).

**Impacto en infraestructura:** **Ninguno.** Sin migraciones (las dos columnas ya existían y son
`NOT NULL`), sin variables de entorno, sin dependencias, sin endpoints nuevos, sin cambios de
auth ni de contrato HTTP. Los dos campos nuevos son **aditivos** en el JSON de respuesta de
`PresupuestoResponse` y `CandidatoResponse`; el front no los consume y no requiere redeploy
coordinado.

**Para el que mire `/auditoria`:** los **3 eventos viejos mal etiquetados** (`alta_adjunto`,
`baja_adjunto`, `baja_candidato`, todos de julio 2026 con `empresa_id NULL`) **se dejan como
están** — `auditoria` es inmutable por diseño, y además sus entidades padre ya fueron borradas
(vacante y candidato), así que no hay de dónde recuperar la empresa correcta. Verificado contra
el catálogo vivo.

---

## 2026-08-06 · Filtro por área en ítems de inventario · commit pendiente

**Qué cambió:** el listado y el export de `/inventario` → pestaña Ítems aceptan **`area_id`**.
Antes solo filtraban por `estado`. Cierra el ítem de `MATRIZ-FILTROS.md` para ese módulo.

Llegó en tres commits: dos divisiones previas (el repo 98→70, `ItemsTab.tsx` 152→70) y este.

- **`repositories/_inventario_scope.py`** (NUEVO, 47) — `items_de_area`. Reusa
  `empleados_de_area` y suma el salto por `inventario_asignaciones`.
- **`inventario_items_repo.py`** (82/100) — el filtro va en el **WHERE** (Forma A), con el early
  return del molde cuando el área no tiene gente: un `.in_([])` no es un WHERE válido.
- **`inventario_items_service.py`** (96/150) · **`routers/inventario_items.py`** (**79/80**,
  `area_id` en la misma línea que `estado`, estilo compacto del archivo).
- Front: `useFiltrosItemsInv.ts` (78/80) carga las áreas y limpia el área al cambiar de empresa ·
  `ItemsTab.tsx` (77/150) suma el `<select>` · `ItemsFiltros` gana `areaId` y `queryItems` lo
  traduce a `area_id` — **una sola vez, y le llega al listado y al export**.
- Tests: `tests/test_inventario_filtro_area.py` (NUEVO, 15) + 2 en `filtros-export.test.ts`.
  Backend **1709 passed**, front **373 passed**, `tsc` 0.

🔴 **DEFINICIÓN DEL FILTRO, escrita en `_inventario_scope.py` y no implícita:** "ítems del área
X" = **los que un empleado del área tiene asignados HOY** (`fecha_devolucion IS NULL`), no los
que alguna vez tuvo. El catálogo de ítems muestra TODO —incluidos `disponible` y `baja`—, así
que sin ese recorte un ítem devuelto hace dos años seguiría apareciendo bajo el área de quien lo
usó. Consecuencia declarada: **un ítem sin asignación activa no aparece bajo ninguna área**,
porque no hay área que pueda reclamarlo. Es el modelo, no la implementación.

**Impacto en infraestructura: Ninguno.** Sin migraciones, sin env vars, sin dependencias. Un
`Query` param nuevo, opcional, en dos endpoints que ya existían: aditivo, nada se rompe.
⚠️ `exportar_items` **sigue sin decorador de rate limit** (corre bajo el baseline de 300/min):
`test_rate_limit.py:276-286` lo afirma y sigue en verde. Cuando ese router se divida, hay que
agregarle `shared_limit("30/hour", scope="export")` y mover el caso a `TestFranjaExport`.
⚠️ El filtro suma **2 queries batch** (empleados del área → asignaciones activas) antes de la del
catálogo. No hay N+1.

## 2026-08-06 · Contrato de la asignación en las cards del organigrama · commit pendiente

**Qué cambió:** las cards de `/organigrama` (vista por proyecto) mostraban nombre y rol de cada
persona; ahora muestran también **valor hora y período** de la asignación.

**Salió del alcance "solo front": los tres campos no llegaban.** A diferencia del caso de
`liderazgo` —donde el repo hacía `SELECT *` y el schema descartaba la columna en silencio—, acá
la query de `organigrama_proyectos_service.py` tiene **lista explícita de columnas** y ni siquiera
las pedía. Hubo que tocar las tres capas:

- **`services/organigrama_proyectos_service.py`** — `select(...)` suma `valor_hora, fecha_desde,
  fecha_hasta`, y el nodo los pasa. Nombres verificados contra `db/schema.sql:662-664`.
- **`schemas/organigrama.py`** — `EmpleadoProyectoNodoResponse` declara los tres.
- **`types/organigrama.ts`** + **`CardsProyecto.tsx`** (130/150) + **`contratoAsignacion.ts`**
  (NUEVO): los formateadores salieron a su propio módulo porque la card se pasaba de 150.
- Tests: `contratoAsignacion.test.tsx`, 20 nuevos. Front **371 passed**, `tsc` 0.
  Backend **1694 passed** (sin cambios: ningún test cubría este service).

🔴 **`valor_hora = 0` se muestra "Sin definir", no "$0"**, y una fecha nula es "no se definió",
no "sin límite". Hoy las **31 asignaciones de producción tienen valor_hora 0 y las dos fechas en
NULL**, o sea que el camino "vacío" es el 100% de los casos reales. La traducción vive en el
FRONT: el schema devuelve el 0 tal cual, para no perder —el día que exista— la diferencia entre
un 0 deliberado y uno sin cargar.

**Impacto en infraestructura: Ninguno.** Sin migraciones, sin env vars, sin dependencias, sin
endpoints nuevos. `GET /api/organigrama/proyectos` devuelve **tres campos más** por empleado en
un response que ya existía: es aditivo, ningún consumidor se rompe.
⚠️ La query pide 3 columnas más sobre `proyecto_asignaciones`, sin joins nuevos ni N+1: sigue
siendo **una sola** consulta batch para todas las asignaciones.

## 2026-08-06 · `liderazgo` → `es_lider`: el parser que la 064 dejó sin escribir · commit pendiente

**Qué cambió:** la migración 064 creó la columna `liderazgo` (texto crudo del CSV) y declaró **en
su propio comentario** que *"el parser decide cómo poblar `es_lider` a partir de él"*. Ese parser
nunca se escribió. Resultado verificado contra el catálogo vivo: `liderazgo` poblado **31/31**
('SI' en 3, 'NO' en 28) y `es_lider` en **false en las 31, incluidos los 3 líderes**.

Importa porque `es_lider` es la columna que leen los 15 consumidores (filtro del listado, columna
del export, campo de la ficha) y sobre todo `fetchEmpleadosLideres()`, que decide **qué empleados
se pueden vincular a un usuario `mandos_medios`**: con las 31 en false, ese selector estaba vacío.

- **`migrations/093_backfill_es_lider.sql`** (NUEVA, 🔴 **PENDIENTE DE CORRER**) — puebla
  `es_lider` desde `liderazgo` para las filas existentes. Data-only, no toca estructura.
- **`services/_nomina_empleados_transforms.py`** — `parsear_fila` ahora produce `es_lider` además
  de `liderazgo`, con `parse_bool` (que ya existía y ya devolvía `Optional[bool]`).
- **`schemas/importacion_nomina_empleados.py`** — `es_lider` viaja por alta y update.
- **`services/nomina_empleados_service.py`** — un liderazgo no reconocido se reporta en
  `con_faltantes`. **149/150 líneas: el próximo cambio de ese archivo exige dividirlo primero.**
- **`tests/test_liderazgo_es_lider.py`** (NUEVO, 45 tests). Antes de esto, **ningún test afirmaba
  nada sobre `liderazgo`**. Backend: **1694 passed**.

🔴 **Un valor no reconocido NO se escribe como false.** 'SI'/'NO' mapean; cualquier otro texto
deja `es_lider` sin tocar y se reporta. Un false silencioso convertiría "GERENTE DE ÁREA" en
"no es líder", que es una afirmación que nadie hizo.

**Impacto en infraestructura:**

- 🔴 **Migración 093 pendiente. Correrla DESPUÉS del deploy del código**, por el mismo motivo que
  la 092: con el código viejo, el próximo import de nómina vuelve a dejar `es_lider` en false y
  hay que correrla de nuevo. Con el código nuevo desplegado, el backfill queda firme.
  No destructiva, idempotente, y reversible de hecho (`liderazgo` conserva el texto).
- **Sin cambios en `db/schema.sql`**: la 093 toca DATOS, no estructura. Por lo mismo no lleva
  `NOTIFY pgrst, 'reload schema'`.
- Sin env vars, sin dependencias, sin endpoints nuevos, sin cambios de auth.
- **El front no se tocó y no hace falta tocarlo**: el filtro, la ficha y el export ya leen
  `es_lider` — después del backfill empiezan a decir la verdad solos.
- `liderazgo` **NO se borra**: queda como dato crudo del import y es lo único que permite
  recalcular el mapeo o desambiguar un valor que no entendimos.

## 2026-08-06 · UI para designar la casilla del sistema · commit pendiente

**Qué cambió:** solo front. El endpoint de la entrada de abajo ya no es alcanzable solo por API:
en **Configuración → Google / Gmail**, una cuenta conectada muestra el botón **"Usar como casilla
del sistema"**, y la que ya lo es muestra el chip **"Casilla del sistema"** en vez del botón.

- `services/integraciones.ts` — `designarRemitente()` (POST, sin body).
- `accionesIntegracion.ts` — la acción con su toast de error; recarga la lista al terminar.
- `useIntegraciones.ts` — la expone con `conBloqueo("google-remitente")`.
- `IntegracionesSection.tsx` — el control, dentro del bloque de Google (148/150).
- Tests: `IntegracionesSection.test.tsx` (8 nuevos) + `designarRemitente` agregado al mock de
  `page.test.tsx`. Front: **351 passed** en 27 archivos. `tsc --noEmit`: 0.

**No se ofrece DESdesignar**, y es una decisión, no un olvido: la casilla es única y se cambia
designando otra. Sin casilla, todo envío corta con `MAIL_SIN_REMITENTE`, así que un botón de
apagarla sería un botón de romper el envío sin nada que lo reemplace.

**Impacto en infraestructura: Ninguno.** Sin endpoints nuevos (usa el de la entrada de abajo),
sin env vars, sin dependencias, sin migraciones. El botón queda deshabilitado si la cuenta no
tiene `gmail.send`; **la cuenta que hay hoy en producción SÍ lo tiene** (ver la corrección en la
entrada siguiente), así que va a salir habilitado.

## 2026-08-06 · Designar la casilla del sistema (endpoint nuevo) · commit pendiente

**Qué cambió:** se destrabó el bloqueante V2/F1.1 del plan. `set_remitente()` existía desde la
migración 087 con **cero callers**: no había forma de designar la casilla desde la que salen los
mails, así que **todo envío cortaba con `MAIL_SIN_REMITENTE` (400)**. Ahora hay endpoint.

- **`POST /api/integraciones/google/remitente`** (nuevo). Designa la integración de Google **del
  propio llamante**. Sin body. Gate `Seccion.INTEGRACIONES + WRITE` → **solo `admin_rrhh`**.
  Devuelve el `IntegracionResponse` de google con `es_remitente_sistema=true`.
- **`services/integracion_service.py`** — `designar_remitente(user_id)`. Valida en este orden y
  **antes** de tocar el repo: (a) existe integración de Google activa, si no `404
  INTEGRACION_NOT_FOUND`; (b) la cuenta concedió `gmail.send`, si no `409 SCOPE_ENVIO_FALTANTE`
  con mensaje pidiendo reconectar. 🔴 **La validación previa no es cosmética**: `set_remitente`
  son dos UPDATE sin transacción que DESMARCAN la casilla vigente antes de marcar la nueva, así
  que designar a alguien sin Google conectado dejaría el sistema **sin remitente**, en silencio
  y con un 200. Hay 5 tests que fallan si la llamada al repo se adelanta a las validaciones.
- **`services/_integracion_response.py`** (nuevo, 32 líneas) — el armado del response salió del
  service, que se pasaba a 154/150. Lo comparten `get_integraciones` y `designar_remitente`.
- **Tests**: +10 en `tests/test_google_scopes.py`. El fake del remitente modela **dos**
  integraciones con su flag y reproduce el orden apagar-todas→prender-la-pedida, incluida la
  rama en que el usuario no tiene fila y no se prende nada.

**Impacto en infraestructura:**

- **Endpoint nuevo, NO público**: `POST /api/integraciones/google/remitente`, con auth y gate de
  escritura. No se agregó a `PUBLIC_ROUTES`.
- **Sin rate limit propio**: corre bajo el baseline global de 300/min del middleware.
- **Sin auditoría**, igual que el resto de los endpoints de integraciones (ninguno audita hoy).
- **La migración 087 ya está corrida**, así que la columna y el índice único parcial existen: no
  hace falta nada del lado de la base.
- 🔴 **Para que el envío de mails funcione en producción hay que ejecutar esto una vez**: un
  `admin_rrhh` entra a Configuración y designa la casilla. **No hace falta reconectar nada.**
  > ✏️ **CORRECCIÓN (6/8/2026).** La primera versión de esta entrada decía que la integración
  > conectada tenía `scopes` **sin** `gmail.send` y que **iba a rechazar con 409 hasta
  > reconectarla**. **Es falso.** Verificado contra el **catálogo vivo de producción**, esa fila
  > tiene `[gmail.readonly, gmail.send, userinfo.email, openid]`: `gmail.send` **está**, así que
  > `designar_remitente` pasa la validación de scope y el 409 no se produce. El dato original
  > salía de suponer que la fila era anterior a la migración 087 — no se había verificado contra
  > la base. Lo que sigue siendo cierto es el mecanismo (Google no amplía un consentimiento ya
  > otorgado, y una cuenta sin el scope exige reconectar); lo que era falso es que ESTA cuenta
  > estuviera en ese estado.
- Sin migraciones, sin env vars, sin dependencias, sin storage, sin cambios de auth ni de CORS.
- **La UI no existe todavía** (`IntegracionesSection.tsx` sigue ofreciendo solo Conectar y
  Desconectar): hoy el endpoint solo es alcanzable por API. Es la sesión siguiente.
- Suite backend: **1649 passed**.

## 2026-08-06 · División de `routers/integraciones.py` (refactor puro) · commit pendiente

**Qué cambió:** solo backend, y **solo movimiento de código — cero funcionalidad nueva**.
`routers/integraciones.py` estaba en **77/80** líneas y no entraba el endpoint para designar la
casilla del sistema (`es_remitente_sistema`), que se escribe en la sesión siguiente. Se movieron
**verbatim** los dos endpoints de API keys —`POST /anthropic` y `POST /zernio`— a
**`routers/integraciones_credenciales.py`** (nuevo, 39 líneas), con su propio `APIRouter()`,
`SECCION` y `_service()`. `integraciones.py` quedó en **67**.

Se movieron las API keys y **no** los de Google a propósito: `google_callback` es la única ruta
pública del módulo (`PUBLIC_ROUTES`) y su nombre de módulo está fijado por
`tests/test_rate_limit.py`, que lee la clave `routers.integraciones.google_callback`. Mudarla
habría roto ese test y tocado la pieza más delicada del archivo para ganar espacio.

El router nuevo se monta desde `integraciones.py` con `router.include_router(...)`, colocado
**inmediatamente después** de crear el router principal y no al final: el `DELETE /{tipo}` es
catch-all y montar detrás de él dejaría las rutas incluidas atrás de un comodín.

**Impacto en infraestructura: Ninguno.**

- **`main.py` NO se tocó.** El prefijo `/api/integraciones` sigue declarado en un solo lugar
  (`app.include_router(integraciones_router, prefix="/api/integraciones")`).
- **Ninguna ruta cambió de path ni de método.** Verificado por introspección de `app.routes`: las
  6 siguen registradas idénticas, y las 5 con gate conservan su `require_permission`
  (el callback sigue con 0 dependencies, que es lo correcto: es público).
- Sin migraciones, sin env vars, sin dependencias, sin storage, sin endpoints nuevos, sin
  cambios de auth ni de CORS/callbacks.
- Suite backend: **1639 passed** (`tests/test_rate_limit.py`: 58 passed).

## 2026-08-03 · Modales que entran en pantalla + aviso de modo consolidado · 3 commits pendientes

**Qué cambió:** solo front.

- **C1 · `components/ui/dialog.tsx` (el primitivo, los 35 modales).** El popup se centra con
  `-translate-y-1/2` y no tenía techo de altura, así que un modal largo se desbordaba por arriba
  Y por abajo a la vez: se perdían el título y los botones juntos. Pasaba en **20 de los 35**
  modales. Ahora `DialogContent` reparte sus hijos por tipo (`partirHijos`), fija encabezado y
  pie, y scrollea solo el medio, con `max-h-[calc(100dvh-2rem)]` (`dvh` y no `vh`: en mobile
  `vh` cuenta la barra de direcciones aunque esté desplegada).
  **Los 15 modales que ya traían `max-h-[90vh] overflow-y-auto` siguen andando** — su clase pisa
  al `max-h` del primitivo vía tailwind-merge, verificado por test; lo que ganan es que ahora su
  encabezado y sus botones también quedan fijos.
- **C2 · división de `PlantillaModal`** (142/150, sin margen): los campos del formulario salieron
  a `PlantillaCampos.tsx`. El modal quedó en 109.
- **C3 · aviso de modo consolidado.** Guardar una plantilla con el sidebar en "Todas las
  empresas" devolvía **el mensaje crudo del backend** *"empresa_id requerido para esta
  operación"* (`utils/empresa.py:29`, `EMPRESA_ID_REQUIRED`) al apretar Guardar. Ahora el botón
  está deshabilitado desde que se abre el modal, con el motivo al lado: *"Para guardar, elegí
  una empresa en el selector de arriba a la izquierda"*. **Previsualizar sigue habilitado** — en
  consolidado el render funciona igual y es la mitad útil de la pantalla.

**Impacto en infraestructura:** **Ninguno.** Sin migraciones, env vars, dependencias, buckets,
endpoints ni cambios de auth. Backend intacto. No quedan migraciones pendientes de correr.

> ⚠️ **`DialogHeader` y `DialogFooter` tienen que ser hijos DIRECTOS de `DialogContent`.** El
> reparto es por tipo de elemento; envolver el pie en un componente propio lo manda al cuerpo
> scrollable y los botones vuelven a irse con el scroll. Verificado que hoy los 35 cumplen. Está
> escrito en `partirHijos` y en el punto donde `PlantillaModal` arma su pie.

> 🚩 **Anotado, fuera de alcance de esta tanda:**
> 1. **40 mensajes de backend llegan crudos al front**, en 37 archivos (`e instanceof Error ?
>    e.message`). No todos son un bug: el 422 de variable inválida de plantillas es el mensaje
>    más útil del formulario y se muestra a propósito. **No hay forma hoy de distinguir un
>    `AppError` redactado para el usuario de uno que es jerga interna** — resolverlo es una tanda
>    propia.
> 2. **Las plantillas globales nunca se ejercitaron.** `plantillas_mail.empresa_id` es nullable =
>    plantilla global, con dos índices únicos parciales que lo sostienen (mig 087), el service
>    las lee y el modal ya avisa *"estás editando la general"*. Pero **la 087 no siembra ninguna**
>    y producción tiene **0 plantillas**, así que el mecanismo entero está sin usar. Definir qué
>    plantillas base trae el sistema.
> 3. **No existe botón de Borrar plantilla en la UI.** El endpoint `DELETE /api/plantillas/{id}`
>    y `borrarPlantilla()` en el front existen, pero **nadie los llama** — por eso el fallo en
>    consolidado "no se veía". No se agregó nada: si el borrado tiene que existir, es su tanda.

## 2026-08-03 · Cards del dashboard que no se estiran + "SIN DATOS" deja de ser una categoría · 2 commits pendientes

**Qué cambió:**

- **C1 · layout (solo front).** Las dos grillas de cards con lista llevan `items-start`. CSS Grid
  estira por defecto, así que plegar una card NO le bajaba el alto —se estiraba a la de su
  vecina— y el acordeón quedaba sin efecto: con Headcount abierta en 12 áreas, Alertas plegada
  era un rectángulo vacío de ~850px. Aplica también a Cumpleaños contra Distribución, que ni
  siquiera es plegable: el stretch no distingue. **La grilla de KPIs NO se tocó** — esas nueve SÍ
  necesitan el stretch porque su `description` es de largo variable. Se sacó el
  `className="contents"` de los tres `Accordion.Root`: sin estiramiento que heredar ya no hacía
  nada, y un `display:contents` inerte es un mecanismo que el próximo lector tiene que descartar
  a mano.
- **C2 · `SIN DATOS` (backend).** El reporte de distribución (R4) y su KPI contaban
  `Sin especificar` (24) y `SIN DATOS` (4) como DOS categorías sobre 31 empleados. El literal
  **no lo escribe nuestro código**: viene en el CSV de RRHH y entraba tal cual porque no estaba
  en `_nomina_parsers.VACIOS`, que es la lista canónica de textos que significan "no hay dato".
  Se sumó ahí (`SIN DATOS`/`SIN DATO`) y `_reporte_distribucion._agrupar` pasó a **importar** esa
  lista en vez de chequear solo NULL/`''`. Una sola definición, dos puntos de aplicación: el
  import al ESCRIBIR, el reporte al LEER.

**Impacto en infraestructura:** **UNA MIGRACIÓN NUEVA, pendiente de correr.** Sin env vars,
dependencias, buckets, endpoints ni cambios de auth. Las otras pendientes no cambian: **089**,
**090** y **091**.

- **`092_seniority_sin_datos_a_null.sql`** — `UPDATE empleados SET seniority = NULL WHERE
  seniority = 'SIN DATOS'`. **4 filas**, verificado contra el catálogo (3/8/2026), sin variantes
  de mayúsculas ni espacios, y el literal aparece **solo en esa columna** (se barrieron todas
  las de `empleados`). No borra filas ni columnas, pero **sí pisa datos** — lo que pisa es la
  ausencia de información escrita con otras letras. **No es reversible**: después no se puede
  distinguir cuáles de las 28 filas en NULL decían 'SIN DATOS'.
  > 🔴 **Va DESPUÉS del código, y no por una dependencia técnica.** Corrida antes no rompe nada
  > (la columna ya es nullable y el agrupador nuevo da lo mismo con el literal o sin él), pero
  > el próximo import con el código viejo vuelve a escribirlo y hay que correrla otra vez. Con
  > el código desplegado, el import ya lo convierte a NULL en la entrada y la limpieza queda
  > firme.
  > **`db/schema.sql` NO cambia**: toca datos, no estructura — la columna ya está declarada
  > `seniority text` nullable, sin default ni check. Tampoco lleva `NOTIFY pgrst`.

## 2026-08-03 · Rearmado del saldo de vacaciones por período + triggers updated_at · 4 commits pendientes

**Qué cambió:** se rearmaron dos sesiones del 30/7 que nunca se commitearon y que un
`reset --hard` dejó a medias (los archivos nuevos sobrevivieron por untracked; los que esas
sesiones MODIFICARON se perdieron). Van en 4 commits, cada uno con la suite verde:

- **C0 · entorno.** `test_selects_repos` fallaba 3 tests SOLO EN WINDOWS: la clave se armaba con
  `str(Path)` (backslash) contra excepciones declaradas con `/`. Ahora `.as_posix()`.
- **C1 · triggers `updated_at`.** La `077` de `migracionAWS/` pasó de 36 a **41** triggers.
- **C2 · núcleo puro del saldo.** `config/reglas_vacaciones.py` + `services/_vacaciones_cupos.py`
  + `_vacaciones_fifo.py`: cupo por antigüedad (14/21/28), acumulación 4 años, vencimiento e
  imputación FIFO. Sin repos ni ids: solo datos.
- **C3 · cableado.** El saldo pasa a calcularse por PERÍODO y el reporte R11 usa EL MISMO núcleo
  que la pantalla (antes divergían en cuatro cosas, todas en silencio). R11 se mudó a
  `services/reportes/_reporte_saldos.py`. `vacaciones_service` bajó a 116 líneas partiendo
  `cancel`/`actualizar` a `_vacaciones_write.py`.

**Impacto en infraestructura:** **DOS MIGRACIONES NUEVAS, las dos PENDIENTES de correr.**

- 🔴 **`090_dias_vacaciones_nullable.sql`** — `empleados.dias_vacaciones_asignados` pasa a
  nullable, pierde el `DEFAULT 14` y se backfillea a NULL. **NACIÓ NUMERADA 085 y se renumeró**:
  el 085 lo ocupa `085_configuracion_reglas.sql`, que YA CORRIÓ. Nada lo detectó — el registro de
  migraciones de Supabase tiene UNA fila (la 081), o sea que no es un ledger y el único juez es
  el catálogo. Verificado el 3/8: los 31 empleados están en 14, así que el backfill no pisa
  ningún override real.
  > 🔴 **ORDEN DE DEPLOY QUE NO SE PUEDE INVERTIR: EL CÓDIGO VA ANTES QUE LA MIGRACIÓN.**
  > `schemas/empleado_out.py` declaraba `dias_vacaciones_asignados: int = 14`, NO Optional. Con
  > la columna ya nullable y ese schema viejo, un NULL levanta `ValidationError` → **500 en TODA
  > lectura de empleado**: listado, ficha, export y dashboard, no solo vacaciones. Con el código
  > de C3 desplegado el NULL es un valor esperado y la migración no rompe nada.
- **`091_triggers_updated_at_faltantes.sql`** — crea el trigger `updated_at` de
  `usuario_integraciones` y `plantillas_mail`. **No es deuda de AWS: es un bug vivo en Supabase
  hoy.** Las dos tablas tienen la columna con `DEFAULT now()` y ningún trigger, así que el dato
  se pobla en el alta y NO SE MUEVE NUNCA — en `usuario_integraciones`, que es la tabla del token
  de Google que se reescribe en cada refresh, dice exactamente lo contrario de la verdad.
  Verificado contra `pg_trigger`. No es retroactiva: las filas viejas conservan su fecha
  congelada (escribir `now()` en todas sería una segunda mentira encima de la primera).
- **Orden entre ellas: son independientes.** La 089 sigue pendiente y sigue teniendo que correr
  ANTES de que se cargue el histórico de ausencias.
- Sin env vars, dependencias, buckets ni endpoints nuevos. Sin cambios de auth.

> ⚠️ **Para el que monta AWS:** la `077` ahora crea **41** triggers, no 36. Las 5 que faltaban
> (`usuario_integraciones`, `vacaciones_pendientes`, `parametros_empresa`,
> `reglas_vacaciones_escala`, `plantillas_mail`) quedaban afuera porque la lista está
> hardcodeada. `backend/tests/test_triggers_updated_at.py` compara el schema contra ese archivo
> y rojea si nace una tabla nueva sin su trigger — no le bajes los mínimos.

> ⚠️ **`backend/.env` local (NO versionado, hay que hacerlo en cada máquina, Mac incluida):**
> sacarle la línea `RESEND_API_KEY`. El commit `ea69bae` (2/8) borró ese campo de `settings.py`
> y pydantic-settings rechaza las claves EXTRA que vienen del `.env` → **ningún archivo de test
> del backend se colectaba**. Solo afecta al `.env`: una env var del sistema que no matchee un
> campo no rompe, y por eso Vercel nunca lo notó.

## 2026-08-03 · Cards del dashboard plegables + contador de alertas · commit pendiente

**Qué cambió:** solo front. Las tres cards del dashboard cuyas listas crecen sin techo
—headcount por área, alertas activas, y cumpleaños/aniversarios— pasaron a ser plegables y
llevan un contador en el encabezado. Con la segunda empresa cargada ya son 12 áreas y 7
alertas; con 500 empleados serían decenas, y hoy empujaban todo lo demás fuera de la pantalla.
Se reusó `ConfigSection.tsx` (el acordeón de /configuracion) en vez de construir un segundo
desplegable: lo único que hizo falta agregarle es que `icon` pasara a ser opcional, y
/configuracion lo sigue usando exactamente igual. `HeadcountBar` salió de `DashboardAdmin.tsx`
a un `HeadcountPanel.tsx` propio (109 → 80 líneas). El estado abierto/cerrado **no se
persiste** y los contadores salen de los datos que ya llegaban.

> 🔑 **Plegada, una card muestra SOLO el título y el contador — ni una fila asomando.** Hubo
> una versión intermedia con un prop `preview` que dejaba las 6 primeras a la vista, y se
> sacó: con 6 barras la card ocupa casi lo mismo que con 12, o sea que se pagaba la
> complejidad del acordeón sin recuperar pantalla, que era todo el punto. Con el asomo se
> fueron también `preview` y `disabled` de `ConfigSection` (0 callers) y el
> `CORTE_LISTA`/`partirLista` de `dashboardAdminData.ts`.

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

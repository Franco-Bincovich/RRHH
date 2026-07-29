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

## 2026-07-29 · Import de nómina recuperable: presupuesto de tiempo · commits pendientes ×4

**Qué cambió:** el import de nómina ya no muere en silencio si se pasa de tiempo. Ahora tiene un
**presupuesto en segundos**: procesa filas, y cuando se acerca al techo **para ENTRE FILAS** y
devuelve el reporte completo de lo que hizo, marcado como parcial. En vez de un `504` con
`"Error del servidor"`, RRHH recibe *"llegó hasta la fila 73, quedaron 47, volvé a subir el mismo
archivo para continuar"*. **No se tocó la arquitectura del import** (sigue fila por fila) ni se
agregó persistencia de progreso: el reintento se apoya en el dedup por DNI que ya existía.

### 🔴 VARIABLE DE ENTORNO NUEVA — `IMPORT_PRESUPUESTO_SEGUNDOS`

**Default: `8.0`. Tiene default seguro, pero conviene declararla explícita en `sofia-backend`.**

🔴 **El default es CONSERVADOR a propósito, y hay que revisarlo en cada entorno.** El techo real
de esta app **NO ESTÁ VERIFICADO**:

> **Dato para el dev de infraestructura:** `backend/vercel.json` declara `maxDuration: 300`, pero
> lo hace **dentro de `builds[].config`**, que es el formato **legacy v2**. La duración de una
> función se configura en la clave **`functions` de nivel superior**, que ese archivo **no tiene**
> (verificado: el único `maxDuration` del repo está en esa línea). O sea que **muy probablemente
> esté IGNORADO** y el backend corra con el default del plan. El `vercel.json` de la raíz fue
> borrado hace tiempo, así que no hay otra fuente que lo sobrescriba.

Por eso 8 s asume el peor caso plausible (10 s del plan más bajo) y deja margen para serializar la
respuesta. **Un presupuesto MAYOR que el techo real no sirve de nada**: el request muere antes de
que el import pueda cortar solo, que es justamente lo que esto vino a evitar.

- **En AWS hay que REVISARLO en el cutover.** El techo lo van a poner ALB / Lambda / ECS, no
  Vercel, y probablemente sea más alto → subir el valor para que un archivo entero entre de una.
- Un valor **≤ 0 significa SIN LÍMITE** (procesa todo, comportamiento previo). Es un degradado
  seguro: una configuración en 0 por error no rompe el import. Hay un test que fija que el
  **default sí enforza** un presupuesto, para que nadie lo lleve a 0 en silencio.

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

- **Variables de entorno:** 🔴 **`IMPORT_PRESUPUESTO_SEGUNDOS` (nueva, default 8.0)** — ver arriba.
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
validaciones") está en `docs/Resultado_nomina_batch.md`.

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
  ni siquiera trae esa columna — ver `docs/Resultado_import.md`).

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

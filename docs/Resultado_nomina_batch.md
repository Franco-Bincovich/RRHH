# Resultado_nomina_batch — Import de nómina en batch, legajo, y el bug de modalidad

> **Fecha:** 29/7/2026 · **Tipo:** diagnóstico READ-ONLY (no se modificó código)
> **Escenario:** 2-5 imports de nómina, uno por empresa, de 50-120 empleados cada uno. Hoy hay 19.
> **Método:** archivos fuente + catálogo vivo de producción (`grmdiwxcvcjorlohpwji`) vía MCP.
> Evidencia `archivo:línea` en toda afirmación. Lo no verificado está marcado como tal.

---

## Resumen ejecutivo

| # | Hallazgo |
|---|---|
| 1 | El import hace **8–13 round-trips por fila**. El caso que ya reventó el timeout de Vercel (`nomina_import_repo.py:3-5`) hacía **~3**. Es 3-4× peor, con archivos 6× más grandes. |
| 2 | Saltear los services **no pierde ninguna validación que hoy esté haciendo algo**: las cuatro son no-ops o redundantes. El fix es **"batch"**, no "batch + replicar validaciones". |
| 3 | El reporte por fila **no depende de la escritura, depende del parseo** → se conserva con dos pasadas. |
| 4 | `modalidad_contratacion` y `tipo_contrato` son **el mismo concepto en dos columnas**. La migración 065 consolidó de hecho pero no de derecho. Ventana para arreglarlo gratis: ahora (0 filas). |
| 5 | `legajo` no lo trae el CSV, y `ensure_legajo_unico` es hoy un **no-op**. |
| 6 | **4 archivos exigen dividirse antes** de tocar el camino del batch. |

---

# PARTE 1 — Round-trips por fila

## a) El conteo exacto

`_procesar_fila` (`nomina_empleados_service.py:82-117`). Separado en **priming** (una vez) y **por fila**.

### Priming — una vez, o una vez por empresa

| Qué | Queries | Cuándo |
|---|---|---|
| `list_empresas()` → `EmpresaRepo.find_all` | 1 | 1ª fila del archivo (`_empresas_primadas`, `:122`) |
| `get_areas(empresa_id)` → `AreaRepo.find_all` | **2** | 1ª fila de cada empresa (`:134`). Son 2: el `select` (`area_repo.py:45-53`) + `_counts_by_area()` (`:54`), que es un **segundo scan de `empleados` entero** |
| `proyectos.get_all(empresa_id)` | 1 | 1ª fila con gerencia de cada empresa (`_nomina_proyectos.py:49`) |
| `create_empresa` / `create_area` / `create` proyecto | 1 c/u | una vez por valor distinto de Organismo / Sector / Gerencia |

### Por fila — steady state

| # | Paso | Archivo:línea | Queries |
|---|---|---|---|
| 1 | `find_by_dni(dni, empresa_id)` | `nomina_empleados_service.py:100` | **1** |
| 2a | **Rama CREATE** → `_empleados_write.crear` | | **3** |
| | · `ensure_legajo_unico` | `_empleados_write.py:44` | 0 ⚠️ (ver §l) |
| | · `ensure_area_valida` → `area_repo.find_by_id` | `:45` | 1 |
| | · `ensure_manager_valido` | `:47` | 0 (el import no manda `manager_id`) |
| | · `repo.save` | `:48` | 1 |
| | · `audit.registrar` → insert en `auditoria` | `:49` | 1 |
| 2b | **Rama UPDATE** → `_empleados_write.actualizar` | | **4** |
| | · `ensure_legajo_unico` / `ensure_manager_valido` / `ensure_no_ciclo_manager` | `:77-81` | 0 |
| | · `ensure_area_valida` | `:79` | 1 |
| | · `prior = repo.find_by_id` (read-before para el diff) | `:82` | 1 |
| | · `repo.update` | `:83` | 1 |
| | · `audit.registrar` | `:84` | 1 |
| 3 | `dar_de_baja` (solo filas con Fecha Baja) | `nomina_empleados_service.py:111` | **1** |
| 4 | `resolver_y_asignar` — con gerencia y sin baja | `:113` | **4** |
| | · `proyectos.find_by_id` | `asignaciones_service.py:50` | 1 |
| | · `find_empresa_for_empleado` | `:62` | 1 |
| | · `get_estado_empleado` | `:65` | 1 |
| | · `repo.save` (la asignación) | `:68` | 1 |
| 5 | `crear_si_falta` — con Fecha Ingreso Reconocida | `:116` | **2 o 5** |
| | · `listar` → `_empleado_or_404` + `find_by_empleado` | `cesion_service.py:48-49` | 2 |
| | · si no existe: `crear` → `find_by_id` + `repo.crear` + `audit.registrar` | `:57-62` | +3 |

### El número

| Escenario | Queries/fila |
|---|---|
| Piso absoluto (alta, sin gerencia, sin fecha reconocida) | **4** |
| Alta con gerencia (caso normal del CSV real) | **8** |
| Alta con gerencia + cesión nueva | **13** |
| Update con gerencia + cesión ya existente (reimport) | **11** |

**Para el CSV real, que trae Gerencia y Fecha Ingreso Reconocida: 8–13 por fila.**

> 🔴 **La comparación que decide todo.** `nomina_import_repo.py:3-5` dice que `batch_upsert_nomina`
> existe porque *"los ~3 round-trips por fila excedían el timeout de Vercel"*. **El import de
> empleados hace 8–13.** Con 120 filas son **~960–1560 round-trips** en un request: entre **3× y 4×
> peor** que el caso que ya explotó, con archivos 6× más grandes que los 19 de hoy.

## b) Evitables vs. no evitables

### Resolubles UNA vez para todo el archivo (lookups)

| Query | Hoy (120 filas) | Podría ser |
|---|---|---|
| `find_by_dni` | 120 | **1**: un `select id, dni where empresa_id=... in (todos los DNI del archivo)` |
| `ensure_area_valida` | 120 | **0**: el `area_id` lo acaba de resolver `_area_id` desde su propio cache — se revalida algo que el mismo proceso creó dos líneas antes |
| `prior = find_by_id` (update) | 120 | **0**: el `find_by_dni` del paso 1 ya trajo esa MISMA fila |
| `find_empresa_for_empleado` + `get_estado_empleado` | 240 | **0**: el service acaba de crear/actualizar ese empleado; sabe su empresa y su estado |
| `proyectos.find_by_id` en `asignar` | 120 | **0**: el proyecto sale del cache de `_nomina_proyectos` |
| `cesiones.listar` | 240 | **1** batch por archivo |

**≈ 840 de las ~1000-1500 son lookups redundantes o batcheables.**

### Escrituras que podrían ir en lote

`repo.save` / `repo.update` de empleados (1/fila) → **1 upsert por chunk**. Asignaciones y cesiones también son inserts en lote.

### Auditoría

1 insert por empleado + 1 por cesión → punto (c).

## c) 🔴 La auditoría — y sí, hay duplicación

**Para un archivo de 120 filas:**

| Origen | Eventos | Evidencia |
|---|---|---|
| `payload_alta_empleado` / `payload_update_empleado` | **120** | `_empleados_write.py:49` y `:84` |
| `payload_alta_cesion` | hasta 120 | `cesion_service.py:62` |
| `payload_importacion_nomina` (el de lote) | **1** | `nomina_empleados_service.py:73` |

**≈ 241 filas en `auditoria` por archivo**, contra la regla propia del repo: *"al auditar una importación → un evento por lote, nunca fila por fila"*.

**Hay duplicación real.** El evento de lote (`_audit_payloads_rrhh.py:139-149`) ya guarda
`{archivo, creados, actualizados, con_faltantes, no_cargados}` — el resumen completo. Los 120
individuales agregan el diff campo por campo.

**¿Se puede consolidar sin perder trazabilidad?**

- **Lo que el evento de lote ya cubre:** qué archivo, cuándo, quién, cuántos y en qué grupo.
  Para "¿quién cargó esta nómina?" alcanza.
- **Lo que se perdería:** el diff por empleado en un **update**. Y ahí hay un matiz: reimportar
  el mismo archivo **pisa los campos con lo del CSV** (`build_update`), así que un dato editado a
  mano se pierde. Hoy ese cambio queda registrado; con un solo evento de lote, no.

> **Lectura:** consolidar **las altas** es seguro (un alta es una fotografía y el registro creado
> *es* su propia evidencia). Consolidar **los updates** sí pierde información real. Salida
> intermedia: un evento de lote con la lista de `empleado_id` afectados y los campos que
> cambiaron, en vez de N eventos. **Lo que NO haría es dejar los 120 y sumar el de lote: eso es
> lo que hay hoy, y es duplicación pura.**
>
> ⚠️ Dato de producción que acota la urgencia: `auditoria` tiene **133 filas en total** hoy. Un
> solo import de 120 empleados **duplicaría la tabla entera**. Con 5 empresas, la multiplica por 10.

## d) 🔴 Qué se pierde si el import escribe directo al repo

### En `create_empleado` (`_empleados_write.crear:44-50`)

| Efecto | Consecuencia real de perderlo |
|---|---|
| `ensure_legajo_unico` | **Hoy es un no-op**: el import nunca setea `legajo` (§l). No se pierde nada… hasta implementar §j |
| `ensure_area_valida` | **Redundante en este camino**: el `area_id` lo acaba de crear/resolver `_area_id` contra la misma empresa |
| `ensure_manager_valido` | **No aplica**: el import no manda `manager_id` (el CSV trae Apellido/Nombre Superior como texto, `parsear_fila:143-144`, y no se persisten) |
| `audit.registrar` | Punto (c) — decisión aparte |
| `logger.info` por empleado | Ruido, no pérdida |

### En `update_empleado` (`:77-85`)

| Efecto | Consecuencia real |
|---|---|
| `ensure_no_ciclo_manager` | **No aplica** (sin `manager_id`) |
| `prior = find_by_id` + diff | **Esto sí es pérdida real** — ver (c) |
| Las otras tres | Mismo análisis que arriba |

### Lo que NO está en los services y sobrevive igual

Las constraints de la DB: `empleados_empresa_dni_uq`, `empleados_legajo_empresa_key`,
`empleados_email_corporativo_key`, el CHECK de `modalidad_trabajo`. **No se pierden nunca** —
pero pasan a reportarse como error opaco de Postgres en vez de `AppError` legible.

> **Conclusión: en este camino concreto, saltear los services NO pierde ninguna validación que
> hoy esté haciendo algo.** Las cuatro son no-ops (legajo, manager, ciclo) o redundantes (área).
> Lo único con contenido es la **auditoría**, que es decisión de producto, no validación.
>
> El fix es **"batch"**, no "batch con validaciones replicadas".
>
> ⚠️ **Con una condición:** si se implementa `legajo` (§j), `ensure_legajo_unico` deja de ser
> no-op y pasa a ser una validación real que hay que replicar en el camino batch.

---

# PARTE 2 — El camino del batch

## e) ¿Sirve `empleados_empresa_dni_uq` como `on_conflict`?

**Sí, técnicamente.** Verificado: `UNIQUE (empresa_id, dni)` — constraint real, no índice parcial.
PostgREST acepta `on_conflict="empresa_id,dni"` igual que costos acepta `"empleado_id,anio,mes"`.

🔴 **Tres diferencias con el caso de costos que lo hacen NO equivalente:**

1. **`dni` es nullable en el schema.** Una fila con `dni` NULL no se deduplica (NULLs distintos en
   Postgres) y el upsert insertaría duplicados en silencio. Hoy lo tapa `obligatorios_faltantes`
   (`_nomina_empleados_transforms.py:106`) — **pero esa guarda está en el service, que es justo lo
   que el camino batch saltearía.**
2. **`empleados_email_corporativo_key` es UNIQUE GLOBAL** (verificado: `UNIQUE (email_corporativo)`,
   sin `empresa_id`). Con 2-5 archivos, dos empleados de empresas distintas con el mismo email
   hacen fallar el **chunk entero**, no la fila. Costos no tiene UNIQUEs secundarias.
3. **Un upsert pisa TODAS las columnas del payload.** En un update, `build_update` manda todos los
   campos del CSV → un dato editado a mano se pierde, igual que hoy, pero sin el evento de
   auditoría que hoy lo registra.

## f) 🔴 Empresas y áreas: la dependencia de orden

`empresa_id` y `area_id` son FK NOT NULL: tienen que existir **antes** del upsert de empleados.

**El cache actual NO alcanza.** Está primado desde la DB (`:122-125`, `:134-137`) pero se
**completa a medida que recorre las filas** — la empresa de la fila 80 se crea al llegar a la fila
80. En un flujo batch, la fila 80 se escribe junto con la 1.

**Lo que sí resuelve: dos pasadas sobre el archivo.**

- **Pasada 1 (sin escribir empleados):** parsear todo, juntar el set de `Organismo` y de
  `(Organismo, Sector)` distintos, resolver/crear empresas y áreas. Con 120 filas de una empresa
  son ~1 empresa y ~10 áreas → **~11 escrituras, no 120**.
- **Pasada 2:** upsert de empleados en chunks, con los ids ya en mano.

Es el patrón preview→confirmar de evaluaciones aplicado dentro del mismo request. **Beneficio
adicional:** hoy, si la fila 80 revienta, ya se crearon 79 empleados y algunas empresas. Con dos
pasadas, los errores de parseo se detectan **antes** de escribir nada.

⚠️ **Costo:** el archivo entero en memoria. Para 120 filas × 27 columnas es trivial (~200 KB).

## g) Tamaño de chunk

**Propuesta: 100 filas por chunk.** El techo es el tiempo, no la memoria:

| Techo | Valor | Quién corta |
|---|---|---|
| `statement_timeout` del rol `authenticator` | **~8 s** | 🔴 El que manda |
| Timeout httpx del cliente Supabase (`settings.supabase_timeout`) | 30 s | Por query |
| `maxDuration` de `backend/vercel.json` | 300 s | El request entero |

Por qué 100:
- Un upsert de 100 filas × ~30 columnas es una sola sentencia; queda holgado bajo los 8 s.
- **120 empleados = 2 chunks.** El archivo más grande del escenario entra en dos idas.
- Es la unidad de reporte de error (§h): un chunk fallido se reintenta de a una fila sobre 100, no
  sobre 500.

⚠️ **No derivado de una medición**: no se corrió un upsert de 100 filas contra esta base. Es un
número elegido por margen, no medido.

Y el contraste: `batch_upsert_nomina` (`nomina_import_repo.py:32`) **manda la lista entera sin
chunk**. Con 120 filas anda; es deuda latente, no un problema actual.

## h) 🔴 Trazabilidad fila→resultado con escritura en lote

**El reporte por fila no depende de la escritura, depende del parseo.**

Hoy `no_cargados` se llena en dos momentos distintos (`nomina_empleados_service.py:61-65`):

- **Errores de parseo/validación** (`falta el DNI`, `Fecha inválida`, `DNI duplicado dentro del
  archivo`) → los levanta `tx.parsear_fila` / `obligatorios_faltantes`, **antes de tocar la base**.
  Con dos pasadas (§f) se detectan **todos** en la pasada 1, con su número de fila intacto. **Se
  conservan al 100%, y de hecho mejor que hoy.**
- **Errores de escritura** (violación de constraint) → hoy caen en el `except` genérico de `:63`.

**Solo cambia el segundo grupo.** Si un upsert de 100 filas falla, Postgres devuelve **un** error y
no dice cuál fila lo causó. Tres formas de resolverlo, de menos a más costosa:

1. **Chequeo previo en memoria.** Los conflictos predecibles —DNI repetido dentro del archivo (ya
   existe: `_seen_dni:93`), email repetido, legajo repetido— se detectan **parseando, sin la base**.
   Cubre la mayoría de los casos reales.
2. **Fallback por fila al fallar el chunk.** Si el chunk revienta, reintentar sus 100 filas de a
   una: se paga el costo viejo **solo en el chunk roto** y se recupera el `fila N: motivo` exacto.
   Peor caso 100 round-trips, no 1500.
3. **Mapa `posicion_en_chunk → numero_de_fila_csv`** para nombrar la fila cuando el error trae
   posición.

> La combinación 1+2 conserva el reporte completo. **Es la pieza que más trabajo agrega al fix y la
> que no se puede saltear**: sin ella, el import pasa de "fila 47: falta el DNI" a "el lote falló",
> que es una regresión peor que la lentitud que vino a arreglar.

## i) Éxito parcial

**Sobrevive, y no obliga a todo-o-nada.** Tres razones:

1. Los tres grupos (`cargados_ok` / `con_faltantes` / `no_cargados`) se deciden por **parseo**, no
   por escritura. `con_faltantes` es literalmente "le falta el email" (`:97-98`).
2. `batch_upsert_nomina` ya demuestra el patrón: un upsert por lote que no aborta el request.
3. El precedente de éxito parcial clasificado existe (`proyectos.asignar_bulk`, bulk de borrado de
   lotes de evaluaciones).

⚠️ **Lo único que cambia de semántica:** hoy cada fila se escribe sola, así que la fila 80 rota no
afecta a la 79. Con chunks, un fallo de constraint **aborta el chunk entero** (Postgres es atómico
por sentencia). Sin el fallback de §h.2, una fila mala se llevaría 99 buenas.

---

# PARTE 3 — Legajo

## j) Confirmado: el CSV no trae Legajo

`_nomina_empleados_transforms.py:10-17` — los 27 headers completos:

```
Apellido · Nombre · DNI · CUIT · Sexo · Edad · Email · Fecha Nacimiento · Fecha Ingreso ·
Fecha Ingreso Reconocida · Organismo · Gerencia · Sector · Equipo · Rol · Seniority ·
Categoria · Modalidad Contratacion · Co-sourcing · Apellido Superior · Nombre Superior ·
Liderazgo · Ubicación Física · Carga Horaria · Product Owner · Fecha Baja · Motivo Baja
```

**No está.** La cadena entera lo confirma: `parsear_fila` (`:112-145`) no lo extrae, `_base_nomina`
(`importacion_nomina_empleados.py:65-74`) no lo incluye, `build_create`/`build_update` (`:77-85`)
no lo pasan.

**Qué tocar** (4 archivos, todos con margen):

| Archivo | Cambio | Líneas |
|---|---|---|
| `_nomina_empleados_transforms.py` | +`"Legajo"` en `HEADERS` · +`"legajo": limpiar(_get(row, "Legajo"))` en `parsear_fila` | 145/200 |
| `schemas/importacion_nomina_empleados.py` | +`"legajo"` en `_base_nomina` · verificar que `EmpleadoCreateNomina`/`UpdateNomina` lo declaren | 85/200 |
| `schemas/empleado.py` | Ya lo tiene (`:103`, `:121`) — **nada que hacer** | 155/200 |
| `_empleado_write_repo.py` | Ya lo persiste (payload genérico desde `model_dump`) — **nada que hacer** | 96/100 ⚠️ |

🔴 **Y una decisión que no es técnica: `validar_headers` (`:69-77`) exige TODAS las columnas de
`HEADERS`.** Agregar "Legajo" hace que **todo CSV sin esa columna sea rechazado entero**
(`"Faltan columnas: Legajo"`, fila 1, cero empleados cargados). O RRHH garantiza que todos los
archivos la traen, o el header nuevo va como **opcional** — lo que requiere separar `HEADERS` en
requeridos y opcionales, que hoy no existe.

## k) 🔴 Dos UNIQUEs en el mismo upsert — sí, falla de forma rara

Verificado en el catálogo, `empleados` tiene **cuatro** UNIQUEs:

| Constraint | Definición | Rol en el upsert |
|---|---|---|
| `empleados_empresa_dni_uq` | `(empresa_id, dni)` | el `on_conflict` propuesto |
| `empleados_legajo_empresa_key` | `(legajo, empresa_id)` | 🔴 **conflicto no declarado** |
| `empleados_email_corporativo_key` | `(email_corporativo)` — **GLOBAL** | 🔴 **conflicto no declarado** |
| `empleados_id_empresa_uq` | `(id, empresa_id)` | soporte de FK compuesta |

`ON CONFLICT (empresa_id, dni) DO UPDATE` **solo** intercepta violaciones de *esa* constraint. Si
la fila viola `empleados_legajo_empresa_key` o la de email, el `ON CONFLICT` **no la atrapa** y
sale como error duro que aborta el chunk entero.

**El escenario concreto:** el CSV trae el DNI 30111222 con legajo `A-100`, y en la base el legajo
`A-100` ya lo tiene **otro DNI**. El upsert intenta el UPDATE por DNI, escribe `legajo='A-100'` →
viola `empleados_legajo_empresa_key` → **el chunk de 100 filas falla completo**, con un mensaje que
nombra la constraint pero no la fila.

**No hay forma de declarar dos `on_conflict` en una sentencia.** Se resuelve validando legajo y
email **en memoria antes del upsert** (el chequeo previo de §h.1), no en la base.

## l) `ensure_legajo_unico` — hoy NO corre en el import

Corre en el camino (`_empleados_write.py:44` y `:77`), pero **es un no-op** por su propio guard:

```python
if not legajo or not empresa_id:
    return          # _empleados_utils.py:21-22
```

Como el import **nunca setea `legajo`** (§j), es siempre `None` → **return inmediato, cero queries,
cero validación.** Por eso no aparece en el conteo de (a).

🔴 **Consecuencia de implementar §j sin tocar nada más:** en cuanto el CSV traiga legajo, esta
función pasa a hacer **1 query por fila** (`find_by_legajo`, `_empleados_utils.py:23`) — el conteo
sube de 8-13 a **9-14**. Y en el camino batch, donde se saltea el service, **no corre en
absoluto**: un legajo duplicado lo atrapa Postgres con el error opaco de (k).

Además, `ensure_legajo_unico` valida contra **la base**, no contra el archivo. **Dos filas del
mismo CSV con el mismo legajo pasan las dos** (ninguna está en la base todavía) y la segunda
revienta en el INSERT. Es el mismo agujero que `_seen_dni` (`:43`, `:92-95`) ya cierra para el DNI
— haría falta un **`_seen_legajo`** equivalente.

---

# PARTE 4 — El bug de modalidad

## m) Quién lee qué

**Catálogo, 19 empleados:**

| Columna | Poblada | Valores distintos |
|---|---|---|
| `modalidad_contratacion` | **0/19** | — |
| `modalidad_trabajo` | **19/19** | `["presencial"]` — **un solo valor** |
| `tipo_contrato` | **19/19** | `["RELACION DE DEPENDENCIA"]` |
| `nivel` | **0/19** | — |
| `seniority` | **4/19** | `["SIN DATOS", "TRAINEE"]` |
| `categoria` | **0/19** | — |

**Consumidores:**

| Consumidor | Lee | Evidencia | Qué muestra hoy |
|---|---|---|---|
| **Reporte R4 distribución** | `modalidad_contratacion` | `_reporte_distribucion.py:36,47` | 🔴 **"Sin especificar: 19"** |
| **KPI distribución del dashboard** | `modalidad_contratacion` | `_dashboard_kpis.py:101` → reusa `generate_distribucion` | 🔴 **"Sin especificar: 19"** |
| **Ficha del empleado** | **las dos, en campos separados** | `DatosEmpleadoSection.tsx:57` y `:59` | "presencial" y vacío |
| **Modal de edición** | **las dos** | `form-utils.ts:33,64,78,111` · `DatosLaboralesFields.tsx:74-79` · `_constants.ts:171` | dos inputs distintos |
| **Export de empleados** | `modalidad_trabajo` (como "Modalidad") + `tipo_contrato` | `_empleados_export.py:38-39` | ambos con dato ✅ |
| **Import de nómina** | 🔴 escribe la columna "Modalidad Contratacion" del CSV en **`tipo_contrato`** | `_nomina_empleados_transforms.py:132` | por eso `tipo_contrato` = "RELACION DE DEPENDENCIA" |
| **Listado de empleados** | `modalidad_trabajo` | `EmpleadosTable.tsx:79` | "presencial" |

**Origen del `"presencial"`: es un DEFAULT de schema, no un dato.** `schemas/empleado.py:98` →
`modalidad_trabajo: str = "presencial"`. Los 19 lo tienen porque el import no manda nada y Pydantic
lo completa. **El único valor que existe es el que puso el default.**

## n) ¿Distintos o residuo? **Son el mismo concepto en dos columnas**

La migración 065 lo dice con todas las letras (`065_tipo_contrato_texto_libre.sql:3-21`):

> *"La importación de la nómina real trae el tipo de contrato en la columna **"Modalidad
> Contratacion"** con valores libres (ej. "RELACION DE DEPENDENCIA")... **Decisión de producto:
> `tipo_contrato` pasa a TEXTO LIBRE**... **NO se toca `modalidad_trabajo`**: sigue siendo
> VARCHAR(20) + CHECK ('presencial','remoto','hibrido'). **El import completa 'presencial' por
> default cuando el CSV no trae el dato**."*

Y `modalidad_contratacion` nació en otra rama: la migración **060** (legajo ampliado), listada en el
encabezado de la 064 (`:5`) entre los campos que "ya cubre" el legajo — o sea, se creó como **campo
informativo de ficha**, no como destino del CSV.

**Son tres conceptos, no dos:**

| Campo | Qué es | Quién lo llena |
|---|---|---|
| `modalidad_trabajo` | presencial/remoto/híbrido — **dónde trabaja** | default del schema; editable en el modal |
| `tipo_contrato` | relación de dependencia / monotributo — **cómo está contratado** | 🔴 el CSV, vía la columna "Modalidad Contratacion" |
| `modalidad_contratacion` | ídem conceptual a `tipo_contrato` | **nadie** — solo el modal a mano |

🔴 **`modalidad_contratacion` y `tipo_contrato` son el MISMO concepto con dos columnas.** La 065
mandó el dato del CSV a `tipo_contrato`; la 060 ya había creado `modalidad_contratacion` para lo
mismo. **No es "el reporte lee el equivocado" ni "uno es residuo": es una duplicación de modelo que
la 065 consolidó de hecho pero no de derecho** — dejó la columna vieja viva y sin migrar el dato.

**Eso cambia el fix.** No alcanza con apuntar el reporte a `tipo_contrato`: hay que decidir si
`modalidad_contratacion` se deprecia (y qué pasa con lo cargado a mano en el modal, hoy 0 filas) o
si se mantienen las dos con semánticas separadas — lo que exigiría que alguien defina en qué se
diferencian, cosa que hoy ningún archivo dice.

⚠️ **La ventana es ahora:** con `modalidad_contratacion` en 0/19, consolidar es gratis. Después de
importar 500 empleados con el dato en `tipo_contrato`, es una migración de datos.

## o) `nivel` vs `seniority` — mismo patrón, un escalón más avanzado

| Campo | Origen | Estado |
|---|---|---|
| `nivel` | Migración **003** (`:19`): `VARCHAR(20) CHECK IN ('junior','semi_senior','senior','lider','manager','director','c_level')` | **0/19.** Nadie lo escribe: no está en `parsear_fila` ni en `_base_nomina` |
| `seniority` | Migración **060** (legajo ampliado) — texto libre | **4/19**, valores `"SIN DATOS"` y `"TRAINEE"` |

`nivel` es el enum cerrado original; `seniority` el texto libre que lo reemplazó cuando llegó el
CSV real (cuyos valores no entran en el CHECK de `nivel`). **`nivel` sí es residuo puro**: 0 filas,
ningún consumidor lo lee en el backend (`grep` no devuelve lecturas fuera de los schemas), y el
CHECK lo hace incompatible con el dato real.

**Diferencia con modalidad, que importa para el fix:** acá el reporte **ya lee el campo correcto**
(`seniority`, `_reporte_distribucion.py:36`). `nivel` es borrable sin tocar ningún consumidor.
Modalidad no: ahí el reporte lee el campo vacío.

## p) Líneas contra límites

| Archivo | Líneas | Límite | Margen | Lo toca |
|---|---|---|---|---|
| `services/nomina_empleados_service.py` | **142** | 150 | 🔴 **8** | P1+P2 (el batch entero) |
| `services/_nomina_empleados_transforms.py` | **145** | 200 | 55 | P3 (legajo) |
| `repositories/_empleado_write_repo.py` | **96** | 100 | 🔴 **4** | P2 (upsert batch) |
| `services/_audit_payloads_rrhh.py` | **149** | 150 | 🔴 **1** | P1c (payload de lote nuevo) |
| `services/_empleados_write.py` | 114 | 150 | 36 | P1d |
| `services/_empleados_utils.py` | 111 | 150 | 39 | P3 (`_seen_legajo`) |
| `schemas/importacion_nomina_empleados.py` | 85 | 200 | 115 | P3 |
| `repositories/empleado_repo.py` | **98** | 100 | 🔴 **2** | P2 |
| `services/_nomina_proyectos.py` | 67 | 150 | 83 | P1b |
| `services/_nomina_cesiones.py` | 42 | 150 | 108 | P1b |
| `services/reportes/_reporte_distribucion.py` | 49 | 150 | 101 | P4 |
| `services/_empleados_export.py` | 53 | 150 | 97 | P4 |
| `routers/importacion_nomina_empleados.py` | 34 | 80 | 46 | — |

🔴 **Cuatro exigen dividir ANTES de tocar nada**, y son justamente los del camino crítico:
`nomina_empleados_service.py` (8), `_empleado_write_repo.py` (4), `empleado_repo.py` (2) y
`_audit_payloads_rrhh.py` (1). El batch no entra en ninguno sin partirlos primero.

---

# Fix chico vs. rediseño

## ✅ Fix chico

| Fix | Alcance | Riesgo |
|---|---|---|
| **Apuntar R4/KPI a `tipo_contrato`** | 1 línea (`_reporte_distribucion.py:36,47`) | Bajo — pero es un **parche**: no resuelve la duplicación de (n) |
| **Borrar `nivel`** | Migración + 3 declaraciones de schema | Bajo: 0 filas, cero consumidores |
| **Leer y escribir `legajo`** | 2 archivos, ~6 líneas | Bajo **si** RRHH garantiza la columna; si no, hay que separar headers requeridos/opcionales primero |
| **Sacar los lookups redundantes** de (b) | `ensure_area_valida` en el camino de import, `prior` duplicado, `find_empresa_for_empleado`/`get_estado_empleado` | Medio. **Baja de 8-13 a ~5-8 sin cambiar la arquitectura** — el mejor retorno por línea tocada de la lista |
| **Chunkear `batch_upsert_nomina`** | 1 archivo (`nomina_import_repo.py`) | Bajo. No urgente, pero es deuda latente |

## 🏗️ Rediseño

| Trabajo | Por qué no es chico |
|---|---|
| **Import de empleados en batch** | Cambia la forma del flujo: dos pasadas, upsert por chunks, mapa fila→resultado, fallback por fila. **Exige dividir 4 archivos antes.** Su parte difícil no es el upsert: es §h |
| **Consolidar la auditoría del import** | Decisión de producto (qué trazabilidad se conserva), no refactor. Hoy hay **duplicación real** entre los 120 eventos y el de lote |
| **Consolidar `modalidad_contratacion` / `tipo_contrato`** | Dos columnas para un concepto (n). Requiere una definición de producto que ningún archivo tiene. **Gratis hoy (0 filas), caro después de 500 empleados** |
| **Legajo como ancla de import** | La columna es fácil (j); lo que no lo es: `ensure_legajo_unico` no corre (l), no valida intra-archivo, y en el camino batch choca con la segunda UNIQUE (k) |

## Orden sugerido

1. **Consolidar modalidad** — la única con ventana que se cierra sola.
2. **Sacar los lookups redundantes** — mitad de la mejora de performance, sin tocar la arquitectura.
3. **Legajo** — bloquea el import de vacaciones, y depende de una respuesta de RRHH.
4. **Batch de verdad** — el trabajo grande, y el único que necesita las 4 divisiones previas.

---

# Lo NO verificado (para no completarlo por simetría)

| Ítem | Estado |
|---|---|
| El chunk de 100 filas | **No medido.** Elegido por margen contra el `statement_timeout` de ~8 s, no ejecutado contra esta base |
| `proyectos_repo.find_all` — cuántas queries hace el costeo batch | Contado como **1**; el costeo "batch" podría sumar 1 más. No se leyó el cuerpo completo |
| Si el plan de Vercel honra el `maxDuration: 300` de `vercel.json` | **No verificable desde el repo** |
| Comportamiento exacto del error de PostgREST ante violación de una UNIQUE no declarada en `on_conflict` | Derivado de la semántica de Postgres, **no reproducido** contra esta base |

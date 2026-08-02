# Resultado_import — Diagnóstico del sistema de import y del modelo de vacaciones/ausencias

> **Fecha:** 29/7/2026 · **Tipo:** diagnóstico READ-ONLY (no se modificó código)
> **Para:** preparar el import histórico de vacaciones e inasistencias (CSV `;`, latin1, CRLF).
> **Escenario:** 2-5 archivos, uno por empresa, historia completa de 50-120 empleados cada uno.
> Primero entra la nómina completa (hoy hay 19 empleados).
> **Método:** archivos fuente del repo + catálogo vivo de producción (`grmdiwxcvcjorlohpwji`) vía MCP.
> Toda afirmación lleva evidencia `archivo:línea` o nombre de objeto de DB. Lo no verificado está marcado como tal.

---

## 🔴 Tres correcciones a la premisa

Las tres cambian el diseño, por eso van primero.

### 1. `legajo` no solo está vacío: el import de nómina NUNCA lo escribe

`legajo` está **0/19** en producción. Pero el problema real es upstream:

| Pieza | Evidencia |
|---|---|
| El CSV de nómina (27 col) **no tiene columna Legajo** | `services/_nomina_empleados_transforms.py:10-17` (lista completa de `HEADERS`) |
| No se parsea | `_nomina_empleados_transforms.py:112-145` (`parsear_fila`) |
| No se escribe | `schemas/importacion_nomina_empleados.py:77,82` (`build_create` / `build_update`) |

**Importar la nómina completa de 50-120 empleados por empresa deja `legajo` en NULL en el 100%.** El ancla que necesita el import de vacaciones **no va a existir** después del import de nómina. Hay que construirla.

### 2. El tope de payload no está en el middleware. No existe.

Revisados los tres middlewares (`middleware/auth.py`, `error_handler.py`, `security_headers.py`) y el stack de `main.py:86-95`: **ninguno limita el body**.

El único límite es **`MAX_SIZE_CSV = 5 * 1024 * 1024` (5 MB)** en `utils/files.py:9`, aplicado **post-read** por `validate_upload`. "Post-read" importa: el archivo ya se cargó entero en memoria (`await file.read()`) antes de rechazarse.

### 3. El timeout declarado es 300 s, no 60 s

`backend/vercel.json` → `"config": { "maxDuration": 300 }`.

⚠️ **No verificable desde el repo:** si el plan de Vercel honra los 300 (los planes con tope de 60 s lo recortan en silencio). Confirmar en el dashboard.

---

## Los cinco bloqueantes de diseño

Resumen ejecutivo de lo que impide arrancar. El detalle está en las partes correspondientes.

| # | Bloqueante | Consecuencia si no se resuelve | Ver |
|---|---|---|---|
| 1 | **No hay ancla de matcheo.** `legajo` 0/19 y el import de nómina no lo llena | El import de vacaciones (que solo trae legajo) cae a apellido+nombre, con revisión humana obligatoria a escala 50-120 | [r](#r-legajo-existe-está-019-poblado-y-el-import-no-lo-llena) |
| 2 | **No hay dimensión de período en vacaciones.** Ninguna columna de año, y el cupo es un escalar único | Con historia completa el saldo da **masivamente negativo** para todos | [k](#k-períodoaño-no-existe-ninguna-columna) |
| 3 | **No hay clave natural para idempotencia.** Ni `solicitudes_vacaciones` ni `solicitudes_ausencia` tienen UNIQUE de negocio | No hay `on_conflict` posible → **reimportar duplica todo, en silencio** | [c](#c-idempotencia) |
| 4 | **La escritura no escala.** Flujo 1 es fila-por-fila-vía-services; el único batch manda la lista entera sin chunk | El `statement_timeout` de ~8 s es el techo real. El repo **ya chocó con esto** una vez | [w](#w-escritura-fila-por-fila-o-en-lote) · [x](#x-cuánto-tarda) |
| 5 | **El eje de estado no existe.** `justificada` (bool) no representa APROBADA/RECHAZADA, y su default es `false` | Sin mapeo explícito, **toda la historia entra como injustificada** y el reporte de ausentismo miente | [o](#o-estados-los-datos-traen-dos-ejes-el-modelo-tiene-uno) |

---

# PARTE 1 — Los dos flujos de import existentes

## a) Paso a paso

### Flujo 1 — Nómina de empleados (single-shot, sin preview)

| Capa | Archivo | Qué hace |
|---|---|---|
| Router | `routers/importacion_nomina_empleados.py` (34 líneas) | `POST /nomina-empleados`, `UploadFile`. Gate `IMPORTACION+WRITE` (:17), rate limit `10/hour scope="import"` (:19). Decodifica (:29-31). Llama `importar(texto, filename)` (:33-34). |
| Service | `services/nomina_empleados_service.py` (142) | `DictReader(delimiter=";")` (:49) → `validar_headers` (:50) → loop desde la fila 2 (:59) → `_procesar_fila` en `try/except` **por fila** (:61-65) → audita **un evento de lote** (:73) → devuelve el reporte. |
| Transforms | `services/_nomina_empleados_transforms.py` (145) | Puro, sin IO. `HEADERS` (:10), `parse_fecha` (:38), `parse_bool` (:49), `parse_sexo` (:59), `limpiar` (:32), `validar_headers` (:69), `parsear_fila` (:112). |
| Repos/Services | `EmpleadoRepo.find_by_dni` (:100), `EmpleadoService.create/update` (:102-107), `EmpresaService`, `AreaService`, `NominaProyectos`, `NominaCesiones` | Reusa los services de negocio completos — validaciones + auditoría propia de cada entidad. |

**Persiste:** empleados (create o update) · **empresas nuevas** (`_empresa_id`, :119-129) · **áreas nuevas** (`_area_id`, :131-142) · baja si hay `Fecha Baja` (:110-111) · **proyecto por Gerencia + asignación** (:113) · **cesión** si hay `Fecha Ingreso Reconocida` (:116).

**Devuelve:** `ImportacionNominaEmpleadosResult` con `total/creados/actualizados/cargados_ok` + dos listas por fila (`con_faltantes`, `no_cargados`) con nº de fila y motivo.

> ⚠️ Este flujo **crea empresas y áreas desde el archivo**. Con 2-5 archivos, la columna `Organismo` es lo que va a poblar el mapa multiempresa. También es donde un typo crea una empresa fantasma: el match es por nombre normalizado (`normalizar_nombre`, `:27`), no por id.

### Flujo 2 — Nómina de costos (preview + confirmar)

| Capa | Archivo | Qué hace |
|---|---|---|
| Router preview | `routers/importacion_nomina.py:27-42` | `POST /nomina/preview`. **`empresa_id: str = Form(...)`** (:31) + `UploadFile`. Llama `parse_nomina_csv(text, empresa_id)` (:41). |
| Service | `services/nomina_csv_service.py` (120) | `_existing_nomina(empresa_id)` trae el set `(empleado_id, anio, mes)` ya cargado (:16-19) → `DictReader` **sin `delimiter`, o sea coma** (:40) → valida 5 headers (:44-47) → valida anio/mes/bruto/neto por fila → `find_by_dni(dni, UUID(empresa_id))` (:98) → arma la fila con `es_actualizacion` (:112). |
| Router confirmar | `:45-70` | Recibe `ConfirmarRequest` (JSON con las filas del preview). **Calcula `cargas_sociales = max(0, bruto − neto)`** (:57), llama `repo.batch_upsert_nomina(filas)` (:62). |
| Repo | `repositories/nomina_import_repo.py` (34) | Un solo `upsert(filas, on_conflict="empleado_id,anio,mes")` (:32). |

**Devuelve:** preview → `(filas_validas, errores)` · confirmar → `{importados, actualizados, errores: []}`.
**Persiste:** solo `costos_nomina`. No crea empleados: un DNI inexistente es error de fila (:100).

> 🔴 **Divergencia a tener presente:** Flujo 1 usa `delimiter=";"` (`nomina_empleados_service.py:49`); Flujo 2 usa **coma** (`nomina_csv_service.py:40`, `DictReader` sin `delimiter`). Los archivos nuevos son `;`. **Flujo 2 no es el molde de parseo**, aunque sí lo sea de arquitectura.

## b) De dónde sale la empresa — seguido hasta la query

**Los dos flujos, distinto, y ninguno usa el header.**

| | Origen | Cadena hasta la query |
|---|---|---|
| **Flujo 1** | **De la FILA del CSV** (columna `Organismo`) | `parsear_fila` → `"_empresa": _get(row, "Organismo")` (`_nomina_empleados_transforms.py:141`) → `empresa_id = self._empresa_id(f["_empresa"])` (`nomina_empleados_service.py:90`) → busca/crea (`:119-129`) → `find_by_dni(f["dni"], UUID(empresa_id))` (`:100`) → `.eq("empresa_id", str(empresa_id))` (`empleado_repo.py:79`). **El router nunca llama `get_empresa_id(request)`** — verificado, no está importado. |
| **Flujo 2** | **Del FORMULARIO** | preview: `empresa_id: str = Form(...)` (`importacion_nomina.py:31`) → `parse_nomina_csv(text, empresa_id)` (:41) → `.eq("empresa_id", empresa_id)` (`nomina_csv_service.py:18`) y `find_by_dni(dni, UUID(empresa_id))` (:98). confirmar: `"empresa_id": body.empresa_id` (:58) → literal al upsert. |

**Vista vs Acción está respetado en los dos, por vías distintas.** Importar es una ACCIÓN y **ninguno toca `X-Empresa-Id`**. Flujo 1 lleva la doctrina un paso más lejos: la empresa sale de cada fila, así que un solo archivo puede escribir en varias empresas — por eso su payload de auditoría pone `empresa_id: None` explícitamente (`_audit_payloads_rrhh.py:143`, justificado en :138).

> **Para el import nuevo:** con **un archivo por empresa**, el molde correcto es el de **Flujo 2** (`Form(empresa_id)`), no el de Flujo 1. Es explícito, auditable, y no depende de que el texto del `Organismo` coincida.

## c) Idempotencia

### Flujo 1 — dedup por `(empresa_id, dni)`

Qué pasa exactamente al reimportar el mismo archivo:

1. `find_by_dni` encuentra a los 19 → **rama update** (`nomina_empleados_service.py:100-104`), no create. `creados=0, actualizados=N`.
2. Los campos se **pisan con lo del archivo** vía `build_update`. **Un dato editado a mano después del primer import se pierde.**
3. Se dispara el diff de auditoría de `update_empleado` **por cada empleado** → N eventos UPDATE (aparte del evento de lote).
4. `_seen_dni` (:43, :92-95) protege contra DNI repetido **dentro del mismo archivo** → `ValueError`, la fila va a `no_cargados`. Es intra-archivo, no entre corridas.
5. Empresas y áreas: `setdefault` sobre el cache primado desde la DB (:124, :136) → **no se duplican**.
6. ⚠️ **Efectos colaterales que NO son idempotentes de la misma forma:** `NominaProyectos.resolver_y_asignar` (:113) y `NominaCesiones.crear_si_falta` (:116). El segundo declara idempotencia por fecha en su nombre; **el primero no se verificó en detalle** — `_nomina_proyectos.py` no se leyó entero.

### Flujo 2 — UPSERT real

`upsert(filas, on_conflict="empleado_id,anio,mes")` (`nomina_import_repo.py:32`), respaldado por la UNIQUE real de `costos_nomina`. Reimportar pisa montos, no duplica. **Es el más limpio de los dos y el que hay que copiar.**

### 🔴 El problema para vacaciones/ausencias

Índices reales (`pg_indexes`):

| Tabla | Índices |
|---|---|
| `solicitudes_vacaciones` | `solicitudes_vacaciones_pkey` · `idx_sv_empleado_id` · `idx_sv_empresa_id` · `idx_solicitudes_vacaciones_empresa_tipo` |
| `solicitudes_ausencia` | `solicitudes_ausencia_pkey` · `idx_sa_empleado_id` · `idx_sa_empresa_id` |

**Ninguna UNIQUE más allá de la PK. No hay clave natural sobre la que hacer `on_conflict`. Reimportar duplicaría todo, en silencio.** Es lo primero a resolver.

## d) Encoding — quién reusa qué: **nadie**

Hay **dos implementaciones independientes**, y una está escrita explícitamente como reacción a la otra.

**Los tres imports de nómina** hacen el mismo try/except inline, **duplicado**:
- `importacion_nomina_empleados.py:29-31`
- `importacion_nomina.py:38-40`

`utf-8-sig` → si falla, `latin-1`.

**Evaluaciones** tiene `tx.decodificar(data)` (`_evaluacion_import_transforms.py:46-68`):
BOM UTF-16 LE/BE explícito → BOM UTF-8 → heurística de UTF-16 sin BOM (`_detectar_utf16_sin_bom`, :71-85: cuenta bytes `0x00` en posiciones pares/impares) → UTF-8 estricto → **`ValueError` claro si no se puede determinar**.

🔴 Su docstring nombra al otro flujo como el bug (`:49-50`):
> *"NUNCA cae a latin-1: latin-1 nunca falla y enmascara un UTF-16 como basura (**el bug silencioso de importacion_nomina**)."*

**Ninguno reusa al otro.** Y para un CSV latin1 el detector de evaluaciones **no sirve tal cual**: latin1 no tiene BOM y no es UTF-8 válido → cae en el `ValueError` de `:64-68`. Es un detector para archivos que *son* UTF-8/UTF-16. **Hay que extenderlo — no reusarlo, ni copiar el `except` de nómina.**

## e) Fechas — hay helper, y ya soporta el formato nuevo

**`_nomina_empleados_transforms.parse_fecha`** (`:38-46`) es el único helper de fecha de todos los imports. `%d/%m/%Y` · vacío → `None` · inválido → `ValueError` con mensaje legible.

✅ **Verificado ejecutándolo — `d/m/yyyy` sin padding funciona tal cual:**

```
6/2/2026   -> 2026-02-06
06/02/2026 -> 2026-02-06
31/12/2024 -> 2024-12-31
```

**Pero:** Flujo 2 **no lo usa** (no maneja fechas, solo `anio`/`mes` como int — `nomina_csv_service.py:62,71`) y evaluaciones tampoco (no tiene fechas). **Un solo helper, un solo consumidor.** Está bien construido y aislado (módulo puro, sin IO) → directamente reusable.

⚠️ **CRLF:** `csv.DictReader` sobre `io.StringIO` lo maneja. No se observó manejo explícito de `\r` residual en los valores, aunque el `.strip()` de `_get` (:85) lo cubriría.

## f) Auditoría

| Flujo | ¿Audita? | Evidencia |
|---|---|---|
| Flujo 1 (empleados) | ✅ **Sí**, un evento por lote | `nomina_empleados_service.py:73-74` → `payload_importacion_nomina` (`_audit_payloads_rrhh.py:132-149`) |
| Flujo 2 (costos) | 🔴 **NO** | `importacion_nomina.py:62` hace el `batch_upsert_nomina` y salta directo al `logger.info` de :66. **`AuditService` no está importado en el archivo.** |
| Evaluaciones | ✅ Sí, un evento por lote | `evaluacion_import_orchestrator.py:82-83` |

**Payload de Flujo 1** (`_audit_payloads_rrhh.py:139-149`):

```
entidad: "empleado" · accion: "INSERT" · evento: "importacion_nomina"
registro_id: str(uuid4())   ← id de EVENTO, no de recurso (comentario en :140-141)
empresa_id: None            ← a propósito: el lote cruza empresas (:138)
datos_anteriores: None
datos_nuevos: {archivo, creados, actualizados, con_faltantes, no_cargados}
```

Guarda **el nombre del archivo** — dato valioso para un import histórico.

**Payload de evaluaciones** (`payload_importacion_evaluaciones`, invocado en `orchestrator.py:82`): `lote_id` real como `registro_id`, período, empresa, conteos de evaluados/resultados/equivalencias, y `bool(prior)` (si pisó un lote previo).

---

# PARTE 2 — El patrón preview/confirmar de evaluaciones

## g) El ciclo completo

### `preview` — `evaluacion_import_orchestrator.py:46-60`

1. `parsear(notas, desglose)` → estructuras en memoria.
2. Por evaluado, `ResolutorIdentidad.resolver(empresa_id, ...)` → estado `resuelto` | `ambiguo` | `sin_candidato` + candidatos.
3. `find_lote_by_periodo` → `periodo_existe` + `registros_a_pisar` (cuántos evaluados moriría el CASCADE).
4. **NO PERSISTE NADA.** Cero writes en el método — verificado línea por línea.

### Revisión humana

El front recibe `PreviewResponse` con `evaluados: List[EvaluadoPreview]`, cada uno con `candidatos` para desambiguar y `resultados` incluidos, con un comentario explícito del porqué:
> *"se devuelven para rearmar el confirmar"* — `schemas/evaluacion_import_api.py:32`

### `confirmar` — `:62-87`, siete pasos en este orden exacto

| Paso | Qué | Línea |
|---|---|---|
| — | `_validar_empresa` fail-closed: ningún `empleado_id` de otra empresa | :69, :126-131 |
| (a) | Crea lote con período **temporal** `"{periodo} ::importando::"` — el sufijo esquiva la `UNIQUE(empresa_id, periodo)` para que nuevo y viejo coexistan | :71-73 |
| (b-e) | `_persistir_y_verificar` | :89-106 |
| — | Si falla → `_limpiar_temporal` best-effort y **re-lanza**; el previo queda intacto | :76-78 |
| (f) | `delete_lote(prior)` — **único paso destructivo, al final** | :80 |
| (g) | `_renombrar_al_real` | :81 |
| — | Audita **un evento** con el período real | :82-83 |

**No re-parsea.** El docstring del schema lo declara (`evaluacion_import_api.py:4-5`):
> *"El payload de confirmar es AUTOCONTENIDO: confirmar no re-parsea ni re-resuelve, persiste exactamente lo que el humano aprobó."*

## h) Historial de importaciones con borrado por lote

**Lo que lo hace posible es una tabla-lote con id propio:**

| Pieza | Dónde |
|---|---|
| Tabla `evaluacion_lotes` | `(id, empresa_id, periodo, importado_por, created_at)` — 5 col, `UNIQUE(empresa_id, periodo)` |
| **FK `ON DELETE CASCADE`** hija→lote | `evaluacion_evaluados.lote_id → evaluacion_lotes` · `evaluacion_resultados.evaluado_id → evaluacion_evaluados` |
| Listado enriquecido sin N+1 | `find_lotes` (`evaluacion_repo.py:63-69`) + `_evaluacion_lotes_enrich.py` (empresa, usuario, conteo por lookup batch) |
| Borrado | `delete_lote` (`:52-55`) — un `delete().eq("id")`, el CASCADE hace el resto |
| Bulk + auditoría | router con dependency WRITE inline, éxito parcial clasificado, un evento por baja |

**Para replicarlo en vacaciones/ausencias hay que construir, no adaptar:**

1. Una tabla **`import_lotes`**: `id, empresa_id, archivo, tipo, importado_por, created_at`, conteos.
2. Una columna **`lote_id`** en `solicitudes_vacaciones` y `solicitudes_ausencia`, con FK.
3. Una `UNIQUE` para reimportar — que hoy **no existe** (punto c).

> 🔴 **Decisión no obvia:** en evaluaciones el CASCADE es aceptable porque el lote es inmutable (nadie edita un resultado). **En vacaciones la gente va a editar.** Un CASCADE ciego borraría una vacación importada que después se corrigió a mano. La columna debería ser **nullable**, y el borrado por lote probablemente **no** debería cascadear ciego.

## i) La verificación por conteo — parcialmente reusable, y la parte reusable ya está aislada

Está en **dos niveles**, y eso decide la respuesta.

### Nivel repo — `_insert_completo` (`evaluacion_repo.py:20-28`) ✅ REUSABLE

```python
def _insert_completo(tabla, filas, error_msg):
    if not filas: return []
    data = supabase_admin.table(tabla).insert(filas).execute().data or []
    if len(data) != len(filas):
        raise AppError(error_msg, "DB_ERROR", 500)
    return data
```

**Genérico: recibe la tabla por parámetro y no sabe nada de evaluaciones.** Su docstring dice que existe *"para que la verificación por conteo del import sea confiable"*. Hoy vive en `evaluacion_repo.py`; habría que moverlo a un módulo compartido (`repositories/_insert_completo.py`).

### Nivel orquestador — `_persistir_y_verificar` (`:89-106`) 🔴 ATADO A EVALUACIONES

Conoce `req.evaluados`, arma `id_por_nombre = {(apellido, nombre): id}` (:97) para colgar los resultados de su padre, e itera `a_resultado_creates`. **Es la forma lo que se copia** (persistir → contar → comparar → recién ahí destruir), no el código.

> Para vacaciones/ausencias el problema es **más simple**: no hay jerarquía padre-hijo de dos niveles. Un lote de vacaciones es una lista plana → `_insert_completo` + un `if len(guardados) != len(esperados)` alcanza.

---

# PARTE 3 — El modelo de vacaciones y ausencias

## j) Estructura real (catálogo vivo, `information_schema.columns`)

### `solicitudes_vacaciones` — 11 columnas

| # | Columna | Tipo | Null | Default |
|---|---|---|---|---|
| 1 | `id` | uuid | NO | `gen_random_uuid()` |
| 2 | `empresa_id` | uuid | **NO** | — |
| 3 | `empleado_id` | uuid | **NO** | — |
| 4 | `fecha_desde` | date | **NO** | — |
| 5 | `fecha_hasta` | date | **NO** | — |
| 6 | `dias` | integer | **NO** | — |
| 7 | `comentario` | text | YES | — |
| 8 | `cancelada` | boolean | NO | `false` |
| 9 | `created_at` | timestamptz | NO | `now()` |
| 10 | `updated_at` | timestamptz | NO | `now()` |
| 11 | `tipo` | varchar | NO | `'vacaciones'` |

### `solicitudes_ausencia` — 11 columnas

| # | Columna | Tipo | Null | Default |
|---|---|---|---|---|
| 1 | `id` | uuid | NO | `gen_random_uuid()` |
| 2 | `empresa_id` | uuid | **NO** | — |
| 3 | `empleado_id` | uuid | **NO** | — |
| 4 | `tipo_id` | uuid | **NO** | — |
| 5 | `fecha_desde` | date | **NO** | — |
| 6 | `fecha_hasta` | date | **NO** | — |
| 7 | `dias` | integer | **NO** | — |
| 8 | `justificada` | boolean | NO | `false` |
| 9 | `motivo` | text | YES | — |
| 10 | `created_at` | timestamptz | NO | `now()` |
| 11 | `updated_at` | timestamptz | NO | `now()` |

Ambas: **0 filas en producción.**

## k) Período/año: **NO EXISTE. Ninguna columna.**

Verificado columna por columna arriba. Las únicas fechas son `fecha_desde`/`fecha_hasta` (cuándo se **tomó**) y `created_at` (cuándo se **cargó el registro**). **No hay forma de expresar "esta licencia corresponde al período 2024".**

El saldo lo confirma: `_vacaciones_saldo.calcular_saldo` (`:14-36`) suma **todas** las vacaciones del empleado sin filtro de año — no hay `.gte("fecha_desde", ...)` ni equivalente. Y `asignados` sale de `empleados.dias_vacaciones_asignados`, **un escalar único sin dimensión temporal** (hoy es el default `14` en los 19).

**Consecuencia para el import:** una licencia del período 2024 tomada en 2026 entra como "vacaciones tomadas", punto. El saldo restará **todo el histórico** contra **un solo cupo anual**. Con historia completa de 50-120 empleados, **el saldo va a dar masivamente negativo** — que es justo el caso que el reporte de saldos marca con `excedido` sin ocultarlo.

**No es un bug del reporte: el modelo no tiene la dimensión.** Requiere migración: `periodo` (o `anio_devengado`) en `solicitudes_vacaciones` **y** una tabla de cupos por `(empleado, año)` que reemplace el escalar. Es el cambio de modelo más grande de la lista.

## l) Fechas NOT NULL: **sí, las cuatro**

`fecha_desde` y `fecha_hasta` son **NOT NULL en las dos tablas**. `dias` también, calculado en el write path como `(fecha_hasta - fecha_desde).days + 1` (`_vacaciones_write.py:67`, `_ausencias_write.py:44`).

🔴 **Los registros históricos sin fechas ("vacaciones liquidadas no tomadas") NO ENTRAN.** Tres salidas, todas requieren decisión de producto:

| Opción | Costo | Problema |
|---|---|---|
| Migrar a nullable + `dias` desacoplado | Media | Rompe `derive_estado`, que compara `today < row.fecha_desde` (`_vacaciones_utils.py:17`) |
| Fechas sentinela | Baja | Contamina listados, reportes y el filtro de solapamiento |
| `tipo` nuevo (`liquidada`) fuera del saldo | Baja | La más limpia, pero sigue exigiendo fechas |

## m) `tipos_ausencia`: catálogo **global**, plano, 4 filas

**Estructura:** `id · nombre (text NOT NULL) · es_base (bool, default false) · activo (bool, default true) · created_at · updated_at`.
**6 columnas. Sin `empresa_id`. Sin `codigo`. Sin padre.**

**Contenido real en producción (4 filas, las 4 `es_base=true`, `activo=true`):**

| nombre |
|---|
| Enfermedad |
| Injustificada |
| Otro |
| Personal |

**`tipos_ausencia_nombre_key`: UNIQUE sobre `nombre`, GLOBAL.** El schema lo declara: *"TipoAusencia: catálogo global (sin empresa_id)"* (`schemas/ausencias.py:3`).

🔴 **Con 2-5 empresas esto es un problema:** los tipos son compartidos. Si la empresa A usa "FRANCO COMPENSATORIO" y la B usa el mismo nombre con otro significado, no se pueden separar. Y **"Injustificada" siendo un tipo** ya es un síntoma del punto (o): mezcla la naturaleza de la ausencia con su calificación.

## n) Subtipo: **NO. El modelo es de un solo nivel.**

`tipos_ausencia` no tiene `padre_id`, ni `codigo`, ni jerarquía. `solicitudes_ausencia` tiene **un solo `tipo_id`**. No hay dónde poner el segundo nivel.

Los datos traen dos niveles reales: `ENFERMEDAD FAMILIAR → Madre/padre` · `FRANCO COMPENSATORIO → Franco compesatorio` *(sic — confirmar el typo con RRHH antes de normalizar contra él)*.

**Tres opciones**, sin recomendación fuerte porque depende de si RRHH quiere reportar por subtipo:

| # | Opción | Costo | Trade-off |
|---|---|---|---|
| 1 | **Aplanar**: un tipo por combinación (`"ENFERMEDAD FAMILIAR - Madre/padre"`) | Cero migración | Explota el catálogo; imposible agrupar por tipo padre |
| 2 | **`padre_id` self-FK en `tipos_ausencia`** + `tipo_id` a la hoja | Migración chica | Es lo que el modelo pide |
| 3 | **Columna `subtipo` (text) en `solicitudes_ausencia`** | Más barata | El subtipo queda texto libre sin catálogo — mismo problema que `empleados.equipo` |

⚠️ Las tres chocan con la UNIQUE global de `nombre` en cuanto haya dos empresas con vocabularios distintos.

## o) Estados: los datos traen dos ejes, el modelo tiene UNO

**Lo que existe en `solicitudes_ausencia`: solo `justificada` (boolean).** No hay columna `estado`. **No hay flujo de aprobación en ningún lado del módulo.**

**Lo que traen los datos — `JUSTIFICADA / APROBADA / RECHAZADA` — son dos ejes mezclados:**

| Eje | Pregunta | Mapea a |
|---|---|---|
| 1 — justificación | ¿la ausencia tiene respaldo? | `justificada` (bool) ✅ |
| 2 — aprobación | ¿alguien la aprobó/rechazó? | 🔴 **no existe en el modelo** |

**No son colapsables:** una ausencia puede estar *justificada pero rechazada*, o *aprobada sin justificar*. Meter los tres valores en el boolean pierde información de forma irreversible.

**Cuál alimenta el reporte de ausentismo:** `justificada`, y **solo por su negación**.
`services/reportes/_reporte_ausentismo.py` selecciona `dias, justificada, tipos_ausencia(cuenta_ausentismo), ...`; luego → `if not a.get("justificada"): injust[...] += dias`. Salen dos métricas: `tasa_total_pct` (todos los días) y `tasa_injustificada_pct` (los de `justificada=false`), ambas sobre la base de días hábiles **configurada** (`_tasa` + `base_dias_habiles`, que desde la migración 085 lee `parametros_empresa`; antes era la constante `_BASE_DIAS_HABILES = 22`).

> ⚠️ Desde la 085 hay **dos** filtros distintos y no hay que confundirlos: `cuenta_ausentismo` (política del **TIPO**) decide si la ausencia entra en la cuenta; `justificada` (hecho de la **AUSENCIA**) parte lo que entró en total vs injustificado. Una licencia por maternidad puede estar justificada y aun así no computar.

🔴 **El default de `justificada` es `false`.** Si el import no mapea explícitamente el eje 1, **toda la historia entra como injustificada** y la tasa de ausentismo injustificado sale inflada al 100%. **Error silencioso: no falla nada, solo miente el reporte.**

**En vacaciones el eje es otro:** `cancelada` (bool) + `estado` **derivado en Python, no en DB** (`_vacaciones_utils.derive_estado:13-21` — `cancelada` → `"cancelada"`; `today < fecha_desde` → `"planificada"`; si no → `"tomada"`). Un import histórico cae siempre en `"tomada"`, que es correcto.

## p) Texto libre: sí, sin límite

| Campo | Tipo DB | Pydantic |
|---|---|---|
| `solicitudes_ausencia.motivo` | `text`, nullable, **sin `character_maximum_length`** | `Optional[str] = None`, **sin `max_length`** (`schemas/ausencias.py:36,44,61`) |
| `solicitudes_vacaciones.comentario` | ídem | ídem (`schemas/vacaciones.py:26,38,61`) |

✅ El detalle libre del archivo entra sin truncar. Es el lugar natural para el subtipo si se elige la opción 3, y para el nombre del certificado (Parte 6).

## q) El cálculo del saldo, exacto

**`backend/services/_vacaciones_saldo.py:14-36`** — `calcular_saldo(repo, empleado_id, empresa_id=None)`:

```
:22  asignados = repo.find_dias_asignados(empleado_id, empresa_id)   ← empleados.dias_vacaciones_asignados
:24  if asignados is None: raise EMPLEADO_NOT_FOUND (404)
:25  today = date.today()
:27  for s in repo.find_vacaciones_empleado(empleado_id, empresa_id):
:28      s = derive_estado(s, today)
:29-32   if estado=="tomada":        gozados += s.dias
         elif estado=="planificada": pedidos += s.dias
:35  disponibles = asignados − gozados − pedidos
```

Cuatro cosas que importan para el import:

1. **Sin filtro de año** en el loop (punto k).
2. `find_vacaciones_empleado` — ⚠️ **no se verificó en el repo** si filtra `tipo='vacaciones'` y `cancelada=false`. El docstring de la función (`:15-16`) lo afirma, pero **el filtro no está en el cuerpo de `calcular_saldo`**: tiene que estar dentro del repo. **No leído, no dado por cierto.**
3. `estado` es derivado, no leído: una vacación pasada siempre cuenta como `gozados`.
4. `asignados` es un escalar sin año.

---

# PARTE 4 — Empleados: el ancla del matcheo

## r) `legajo` existe, está 0/19 poblado, y el import no lo llena

**Conteo real (catálogo vivo):**

```
total: 19 · con_legajo: 0 · sin_legajo: 19 · legajos_distintos: 0
con_dni: 19 · con_cuil: 19
```

Columna: `empleados.legajo`, `character varying`, **nullable**, sin default.

**Y el punto que cambia el plan** (ver corrección 1): el CSV de nómina **no trae Legajo**, no se parsea, no se escribe. **Después de importar la nómina completa, `legajo` sigue en NULL para los 100-500 empleados nuevos.**

**El import de vacaciones, que solo trae legajo, no tiene ancla. Opciones:**

| # | Opción | Evaluación |
|---|---|---|
| **A** | Conseguir de RRHH una nómina **con** columna Legajo y extender `HEADERS` + `parsear_fila` + `build_create/update` | ✅ **La única salida limpia.** El legajo pasa a ser el ancla de todo import futuro |
| **B** | Mapeo legajo→empleado cargado aparte (tipo `evaluacion_equivalencias`) | Viable, pero es trabajo manual recurrente |
| **C** | Caer a apellido+nombre | Es lo que evaluaciones tuvo que hacer. Costo conocido: estados `ambiguo`/`sin_candidato`, revisión humana obligatoria, y un desempate por superior que **hoy no discrimina** porque `manager_id` está 0/19 |

> Con 50-120 empleados por empresa, (C) a escala es caro. **(A) es la conversación con RRHH previa a escribir una línea.**

## s) UNIQUE sobre legajo: **sí, por empresa**

```sql
empleados_legajo_empresa_key: CREATE UNIQUE INDEX ON empleados (legajo, empresa_id)
```

**Es `(legajo, empresa_id)` — único por empresa, NO global.** Correcto para multiempresa: dos empresas pueden repetir el legajo 001.

⚠️ Como `legajo` es nullable y Postgres trata NULLs como distintos, **los 19 NULL actuales conviven sin violar nada** — la UNIQUE no fuerza que se cargue.

**Otros índices únicos de `empleados`:**

| Índice | Alcance | Nota |
|---|---|---|
| `empleados_empresa_dni_uq (empresa_id, dni)` | Por empresa | ✅ Correcto |
| `empleados_id_empresa_uq (id, empresa_id)` | — | Soporte de FKs compuestas |
| 🔴 `empleados_email_corporativo_key (email_corporativo)` | **GLOBAL, sin `empresa_id`** | Ver abajo |

🔴 **El email único global es una mina para el import de nómina completa:** **dos empleados de empresas distintas no pueden compartir email**, y con 2-5 archivos eso es plausible (casilla genérica, contratista en dos empresas). La fila fallaría y caería en `no_cargados` con un mensaje de Postgres, no de negocio. Los emails vacíos no molestan (NULLs distintos), y el service ya nulifica los inválidos (`nomina_empleados_service.py:97`).

## t) Helpers de búsqueda: los dos existen y **exigen `empresa_id`**

| Helper | Firma | Evidencia |
|---|---|---|
| `find_by_legajo` | `(legajo: str, empresa_id: UUID)` — **obligatorio, no Optional** | `empleado_repo.py:69`; query `.eq("legajo", legajo).eq("empresa_id", str(empresa_id))` (:73) |
| `find_by_dni` | `(dni: str, empresa_id: UUID)` — **obligatorio** | `:77`; query `.eq("dni", dni).eq("empresa_id", ...).maybe_single()` (:79) |
| `find_by_id` | `(id, empresa_id: Optional[UUID] = None)` — opcional | `:57-59` |

✅ Los dos son **Forma A** (filtro en el WHERE) y usan `maybe_single()`. **Directamente reusables.**

Y un tercero: **`ensure_legajo_unico(repo, legajo, empresa_id, exclude_id)`** (`services/_empleados_utils.py:16-25`) → `LEGAJO_DUPLICADO` (409). Se llama en alta (`_empleados_write.py:44`) y edición (`:77`).
⚠️ Ojo con `:21`: `if not legajo or not empresa_id: return` — **sin empresa no valida nada**.

## u) Cuándo el import crea al empleado

| Flujo | ¿Crea? | Evidencia |
|---|---|---|
| **Flujo 1** | ✅ **Sí** — y también empresa y área | `nomina_empleados_service.py:100-108` (`find_by_dni` → update o create) · `_empresa_id` :119-129 · `_area_id` :131-142 |
| **Flujo 2** | ❌ No | DNI no encontrado → error de fila, se descarta (`nomina_csv_service.py:99-101`) |
| **Evaluaciones** | ❌ No | Sin match → `empleado_id = NULL`, estado `sin_candidato`, **válido, no error** (`evaluacion_import_api.py:71`: *"null = sin candidato (se guarda igual)"*) |

> 🔴 **Para vacaciones, los moldes correctos son Flujo 2 y evaluaciones, no Flujo 1.** Una vacación no puede crear un empleado. Y `solicitudes_vacaciones.empleado_id` es **NOT NULL con FK**, así que la opción "guardar sin match" **ni siquiera está disponible** (a diferencia de evaluaciones, donde la columna es nullable). **Un legajo sin match tiene que ser un error de fila que se resuelve antes de confirmar.**

---

# PARTE 5 — Límites operativos

## v) Tamaño de archivo: **5 MB, y no está en el middleware**

`utils/files.py:9` → `MAX_SIZE_CSV = 5 * 1024 * 1024`.

Aplicado por `validate_upload` (`:26-52`) en los tres imports: `importacion_nomina_empleados.py:27` · `importacion_nomina.py:36` · `evaluaciones_import.py:31,33`.

Revisados los tres middlewares y el stack de `main.py:86-95`: **ninguno inspecciona `content-length` ni limita el body**. El chequeo es **post-read** (`:47` opera sobre `content` ya en memoria).

**¿Alcanzan 5 MB?** Estimación: 1.500 filas × ~200 bytes ≈ **300 KB**. Incluso 10.000 filas quedan bajo 2 MB. **El límite de 5 MB no es el binding constraint.**

⚠️ **No verificable desde el repo:** si Vercel impone un tope de request body más bajo a nivel plataforma. Confirmar en el dashboard antes de dar el número por bueno.

## w) Escritura: fila por fila o en lote

| Flujo | Modo | Evidencia |
|---|---|---|
| **Flujo 1 (empleados)** | 🔴 **Fila por fila**, y peor: vía **services** completos | `nomina_empleados_service.py:59-71` (loop) → `create_empleado`/`update_empleado` (:102-107), cada uno con validaciones, lookup y **su evento de auditoría**. Más `dar_de_baja` (:111), `resolver_y_asignar` (:113) y `crear_si_falta` (:116) → **varios round-trips por fila** |
| **Flujo 2 (costos)** | ✅ **Un solo batch** | `nomina_import_repo.py:32`. ⚠️ **Sin tamaño de chunk: manda la lista entera de una** |
| **Evaluaciones** | ✅ Bulk por tabla | `_insert_completo` (`evaluacion_repo.py:20-28`). Pero `guardar_resultados` se llama **en loop por evaluado** (`orchestrator.py:99-102`) → N inserts, no 1 |

## x) Cuánto tarda

**No hay instrumentación de tiempos en ningún import.** Los `logger.info` registran conteos, nunca duración (`nomina_empleados_service.py:75` · `nomina_import_repo.py:33` · `nomina_csv_service.py:115`). **No se puede saber sin correrlo.**

**Pero el repo ya chocó con esto y lo dejó escrito** — `repositories/nomina_import_repo.py:3-5`:
> *"batch_upsert_nomina persiste todo el lote en una sola query, **en vez de los ~3 round-trips por fila que excedían el timeout de Vercel**."*

Es el precedente exacto del escenario nuevo. Y **Flujo 1 sigue haciendo justo lo que Flujo 2 tuvo que abandonar**. Con 19 empleados nunca dolió; **con 100-500 es el riesgo #1 del import de nómina completa**, antes de llegar a vacaciones.

**Los techos que aplican** (el más bajo gana):

| Techo | Valor | Alcance |
|---|---|---|
| `statement_timeout` del rol `authenticator` (PostgREST) | **~8 s** | 🔴 **El que probablemente corte un batch grande** |
| Timeout httpx del cliente Supabase (`settings.supabase_timeout`) | 30 s | Por query, no por request |
| `maxDuration` de `backend/vercel.json` | 300 s | Sujeto a lo que permita el plan |

> El riesgo no es el `maxDuration`: es el **`statement_timeout` de ~8 s** contra un upsert de 1.500 filas, más el acumulado de round-trips de Flujo 1. **Chunking es obligatorio — y no hay ninguno hoy.**

## y) El preview no persiste nada: **el front devuelve el payload entero**

**Confirmado en los dos flujos, y es la misma decisión.**

| Flujo | Evidencia |
|---|---|
| **Evaluaciones** | `preview` no escribe (`orchestrator.py:46-60`). `PreviewResponse` incluye `resultados: List[ResultadoParseado]` — *"se devuelven para rearmar el confirmar"* (`evaluacion_import_api.py:32`). `ConfirmarRequest` es `{empresa_id, periodo, evaluados}`, **autocontenido** (:73). El router de confirmar recibe **JSON, no archivo** (`evaluaciones_import.py:39`) |
| **Costos** | Idéntico. `ImportarNominaCSVModal.tsx:64` guarda `preview` en estado React; `:135` → `confirmarImportacionNomina(preview.filas_validas, empresaId)` — **manda el array entero de vuelta** |

**Implicancias para un archivo grande:**

1. El CSV cruza la red **dos veces** (subida + devolución en JSON), y el JSON es **más pesado que el CSV** (nombres de campo repetidos por fila, UUIDs resueltos que el original no traía). Para 1.500 filas, varios MB.
2. Ese JSON entra por `ConfirmarRequest` como **body**, no como `UploadFile` → **`validate_upload` no lo toca**. `MAX_SIZE_CSV` solo protege el preview. **El confirmar no tiene ningún límite de tamaño.**
3. Todo el payload vive en **estado de React** entre los dos pasos. Un refresh lo pierde y hay que re-subir.
4. Si el confirmar mandara solo ids, habría que **re-parsear** — y evaluaciones lo rechazó a propósito: re-parsear reintroduce la posibilidad de persistir algo distinto de lo que el humano aprobó.

> **Para 1.500 filas es el punto de diseño que más merece revisarse.** La tercera vía —el preview persiste en una tabla de staging y el confirmar manda solo `preview_id` + correcciones— **no existe en el repo**. Sería construcción nueva, pero es la única que escala y sobrevive a un refresh.

---

# PARTE 6 — Adjuntos

## z) `ausencia` ya es entidad padre soportada — falta el archivo, no el modelo

**Lo que ya está:**

| Pieza | Evidencia |
|---|---|
| Resolver de `ausencia` | `_adjunto_padres.py:35-37` → `AusenciasRepo().find_by_id(entidad_id, empresa_id)` |
| Registrado en `RESOLVERS` | `:51-57`, junto a `empleado`, `vacacion`, `vacante`, `offboarding` |
| Validación + etiquetado | `ensure_padre_de_empresa` (`:66-95`) valida el padre y **devuelve SU `empresa_id`** — Vista vs Acción resuelto. 404 idéntico para "no existe" y "es de otra empresa" (`:94`) |
| Límites | `MAX_SIZE_ADJUNTO = 10 MB` + `ALLOWED_TYPES_ADJUNTO` (PDF/docx/xlsx/imágenes) — `utils/files.py:10,16-23` |

**El bloqueo real: los datos traen el NOMBRE del archivo, no el archivo.**
`adjuntos.storage_path` y `bucket` son **NOT NULL** (verificado en el catálogo) y apuntan a un objeto que tiene que existir en Storage. **No se puede crear una fila de adjunto sin el binario.** No es evitable: es la forma de la tabla.

**Tres caminos, por costo:**

| # | Camino | Costo | Qué se obtiene |
|---|---|---|---|
| 1 | Guardar el nombre en `motivo` (text, sin límite) → `"Certificado: gripe_juan_0324.pdf"` | Cero migración, cero código | Un dato textual, no un adjunto. Nadie descarga nada. **Para un import histórico donde los archivos probablemente ya no existen, puede alcanzar** |
| 2 | Columna `certificado_nombre` en `solicitudes_ausencia` | Una columna | Explícita, filtrable, exportable. Sigue sin ser un archivo |
| 3 | Adjunto real | Alto | Requiere que RRHH entregue los binarios + forma de vincular archivo↔fila (el nombre como clave, con riesgo de colisión) |

🚩 **Dos advertencias sobre el camino 3:**
- Hay que decidir antes **si Storage queda en Supabase o pasa a S3**, o se hace dos veces (misma advertencia que la Entrega 2 de evaluaciones).
- El adjunto **necesita el `id` de la ausencia ya creada** → es un segundo paso después del confirmar, con el mapeo fila→id en la mano. **Ninguno de los tres flujos actuales hace nada parecido.**

---

# Veredicto

## ✅ REUSABLE TAL CUAL

| Qué | Dónde |
|---|---|
| `parse_fecha` — `d/m/yyyy` sin padding, **verificado funcionando** | `_nomina_empleados_transforms.py:38-46` |
| `limpiar` · `parse_bool` · `_norm` · `normalizar_nombre` · `_get` · `validar_headers` · `identificador` | `_nomina_empleados_transforms.py` (módulo puro, sin IO) |
| `normalizar_campo` / `clave_identidad` (sin acentos, para el fallback apellido+nombre) | `_evaluacion_import_transforms.py:93-100` |
| `find_by_legajo(legajo, empresa_id)` y `find_by_dni(dni, empresa_id)` — Forma A, `maybe_single()` | `empleado_repo.py:69,77` |
| `_insert_completo(tabla, filas, msg)` — genérico, recibe la tabla | `evaluacion_repo.py:20-28` |
| `validate_upload` + `MAX_SIZE_CSV` | `utils/files.py:26-52` |
| Gate `IMPORTACION+WRITE` + `shared_limit("10/hour", scope="import")` | `importacion_nomina.py:27-28` |
| `ensure_padre_de_empresa("ausencia", ...)` | `_adjunto_padres.py:35,66` |
| `_rango_fechas.aplicar_rango` (solapamiento) para el listado post-import | `repositories/_rango_fechas.py` |

## 🔧 EXTENDER

| Qué | Por qué |
|---|---|
| **El detector de encoding** | `tx.decodificar` **rechaza latin1** (`:64-68`). Sumarle una rama latin1 explícita — no copiar el `try/except` triplicado de nómina, que es el bug que ese archivo nombra en su propio docstring (`:49-50`) |
| **`_persistir_y_verificar`** | La **forma** se copia; el código está atado al mapa `(apellido,nombre)→id` de evaluaciones (`orchestrator.py:97`). En vacaciones la lista es plana → sale más simple |
| **El molde preview/confirmar** | La arquitectura sirve entera. Lo que hay que rediseñar es el **transporte del payload** (punto y) |
| **`_scope_filtros` / ownership** | Todo filtro nuevo se compone por INTERSECCIÓN, nunca reemplaza |
| **`HEADERS` + `parsear_fila` + `build_create/update` de Flujo 1** | Para que el import de nómina **escriba `legajo`** — condición previa a todo lo demás |

## 🏗️ CONSTRUIR DESDE CERO

| Qué | Por qué, en una línea |
|---|---|
| 🔴 **El ancla del matcheo** | `legajo` 0/19 **y el import de nómina no lo escribe**. Sin esto el import de vacaciones no tiene por dónde entrar |
| 🔴 **Dimensión de período en vacaciones** | No hay columna de año, y el cupo es un escalar único. Con historia completa el saldo da negativo para todos |
| 🔴 **Clave natural / UNIQUE para idempotencia** | Sin UNIQUE de negocio no hay `on_conflict` → reimportar duplica en silencio |
| 🔴 **Escritura en batch con chunking** | El único batch manda la lista entera sin chunk, y Flujo 1 es fila-por-fila-vía-services. El `statement_timeout` de ~8 s es el techo real |
| **Parser de los CSV nuevos** | Headers, tipos y semántica propios. Molde: Flujo 1 (`;`, tolerante, reporte por fila) |
| **Subtipo de ausencia** | `tipos_ausencia` es plano, global, 4 filas, UNIQUE por `nombre` sin empresa |
| **El segundo eje de estado** | `justificada` (bool) no representa APROBADA/RECHAZADA. Y su default `false` hace que, sin mapeo explícito, todo entre como injustificado |
| **Fechas nulas / vacaciones liquidadas** | Las 4 columnas de fecha son NOT NULL. Decisión de producto antes que migración |
| **`import_lotes` + `lote_id` + borrado por lote** | No existe nada equivalente fuera de evaluaciones. Y el CASCADE ciego es riesgoso acá: la gente edita vacaciones |
| **Auditoría del import de costos** | Sigue en cero (`importacion_nomina.py:62`) — deuda ya conocida. El import nuevo no debe nacer con ella |
| **Staging del preview** (opcional pero recomendado) | La tercera vía que evita el round-trip del payload entero. No existe en el repo |

---

# Preguntas para RRHH — antes de diseñar

1. **¿Pueden entregar la nómina con columna Legajo?** Es la pregunta que más condiciona todo lo demás.
2. **¿Qué significa el período de una licencia?** Sin eso, el saldo no tiene arreglo posible.
3. **¿JUSTIFICADA / APROBADA / RECHAZADA son dos ejes?** Confirmarlo antes de colapsarlos en un boolean.
4. **¿Quieren reportar por subtipo, o alcanza el tipo padre?** Decide entre aplanar y migrar.
5. **¿Existen todavía los certificados médicos, o solo los nombres?**
6. **Confirmar el typo `"Franco compesatorio"`** antes de normalizar contra él.

---

# Lo NO verificado (para no completarlo por simetría)

| Ítem | Estado |
|---|---|
| `find_vacaciones_empleado` — ¿filtra `tipo='vacaciones'` y `cancelada=false`? | El docstring de `calcular_saldo` lo afirma, pero el filtro no está en su cuerpo: tiene que estar en el repo. **No leído** |
| `_nomina_proyectos.py` — ¿`resolver_y_asignar` es idempotente? | **No leído entero.** `NominaCesiones.crear_si_falta` sí lo declara por nombre |
| Tope de request body a nivel plataforma Vercel | **No verificable desde el repo.** Confirmar en el dashboard |
| Si el plan de Vercel honra el `maxDuration: 300` de `vercel.json` | **No verificable desde el repo** |
| Manejo de `\r` residual (CRLF) en valores de celda | No se observó manejo explícito; el `.strip()` de `_get` (:85) lo cubriría |

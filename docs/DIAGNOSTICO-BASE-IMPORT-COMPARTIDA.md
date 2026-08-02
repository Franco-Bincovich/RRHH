# Diagnóstico READ-ONLY — base de import compartida (ausencias y vacaciones pendientes)

> **2/8/2026. NO se escribió una sola línea de código.**
> Verificado contra los archivos fuente **y contra el catálogo vivo de producción**.

---

## Resumen ejecutivo

1. 🔴 **La detección de encoding son TRES copias que NO coinciden, y dos tienen un bug conocido.**
   El decodificador de evaluaciones se escribió explícitamente porque el de nómina falla en
   silencio — y el de nómina sigue ahí, **duplicado en dos routers**. Es lo primero a unificar y
   es lo único urgente de todo este documento.
2. **Se comparte MUCHO menos de lo que parece.** De las siete piezas que preguntás, **dos** tienen
   implementación compartida real, **tres** están duplicadas con divergencia, y **dos** son
   legítimamente distintas y no hay que tocar.
3. 🔴 **El import de vacaciones pendientes NO TIENE ANCLA HOY.** El archivo trae solo legajo y
   `legajo` está **0/19** en producción. Sin resolver eso, el flujo se puede construir entero y no
   va a poder importar una sola fila.
4. **Las dos claves de idempotencia son viables, pero ninguna existe como constraint**:
   `vacaciones_pendientes` ya tiene su UNIQUE ✅; `solicitudes_ausencia` **no tiene ninguna** —
   solo PK sobre `id`.
5. ✅ **086, 087 y 088 están las tres corridas.** Próximo libre: **089**.

---

## (a) 🔴 El mapa honesto de los dos flujos

Hay **tres** flujos de import, no dos: nómina de empleados, **nómina de costos** (el olvidado, con
preview+confirmar) y evaluaciones. El tercero importa porque es el que ya tiene el ciclo que
querés replicar.

| Pieza | ¿Compartida? | Estado real |
|---|---|---|
| **Detección de encoding** | 🔴 **TRES COPIAS, DIVERGENTES** | ver abajo |
| **Lectura de CSV + validación de headers** | ❌ **tres copias** | `csv.DictReader` con distinto `delimiter`, distinta normalización de claves y distinto manejo de "faltan columnas" |
| **preview → revisar → confirmar** | ⚠️ **dos implementaciones** | evaluaciones y costos. Nómina de empleados NO tiene preview (single-shot) |
| **Clasificación de resultados** | ❌ **dos modelos distintos** | nómina: 3 grupos por fila · evaluaciones: `problemas` + `anomalias` (que es otra cosa) |
| **Presupuesto de tiempo** | ⚠️ **UNA implementación… y ya tiene una copia** | `LoteNomina` + `LoteMails`, que copié el patrón hace dos sesiones |
| **Reporte por fila con nº de línea** | ✅ **el concepto**, ❌ la implementación | los tres arrancan en `start=2` y tienen su propio schema de fila |
| **Auditoría por lote** | ✅ **el criterio está unificado** | payloads distintos, pero todos "un evento por lote" con `uuid4()` de evento |

### 🔴 El encoding: el hallazgo que importa

```
routers/importacion_nomina_empleados.py:41-43   try utf-8-sig → except → latin-1
routers/importacion_nomina.py:38-40             try utf-8-sig → except → latin-1   ← copia literal
services/_evaluacion_import_transforms.decodificar   BOM explícito · UTF-16 sin BOM
                                                     por heurística · UTF-8 estricto
                                                     · ValueError claro
```

El docstring del tercero **nombra al primero como el bug**:

> *"NUNCA cae a latin-1: latin-1 nunca falla y enmascara un UTF-16 como basura (**el bug
> silencioso de importacion_nomina**). Si no es determinable → ValueError claro, no adivina."*

O sea: **alguien ya diagnosticó este bug, escribió la versión correcta para evaluaciones, y dejó
la rota donde estaba — por duplicado.** `latin-1` decodifica cualquier byte sin fallar nunca: un
archivo UTF-16 entra como caracteres basura y el import "funciona" cargando nombres ilegibles.

Con archivos de RRHH que ya demostraron venir en encodings distintos entre sí (notas en UTF-16,
desglose en UTF-8), esto no es teórico.

⚠️ **Y los routers decodifican**, que es otro problema de capa: un router no debería saber de
encodings. En evaluaciones el decode vive en el parser, donde corresponde.

### El ciclo preview → confirmar: dos implementaciones distintas

| | evaluaciones | costos |
|---|---|---|
| Qué devuelve el preview | filas parseadas + resolución de identidad + resumen + anomalías | filas válidas + errores |
| Qué recibe el confirmar | **el payload completo, aprobado por el humano** | **el payload completo** |
| ¿Re-parsea al confirmar? | **NO**, explícito | **NO** |
| ¿Persiste algo entre las dos? | **NO** | **NO** |

Las dos coinciden en la decisión de fondo (ver (f)). Lo que no comparten es una sola línea de código.

### La clasificación: dos modelos que NO son el mismo

- **Nómina** clasifica **por fila** en tres grupos: cargada OK · cargada con faltantes · no
  cargada. Cada grupo con `fila`, `empleado`, y motivo/faltantes.
- **Evaluaciones** tiene `problemas` (fila + archivo + motivo) **y** `anomalias`, que es otra
  cosa: inconsistencias **del cruce entre dos archivos** ("está en notas finales pero no en el
  desglose"). No tiene número de fila porque no es de una fila.

⇒ **No son la misma clasificación con otros nombres.** El modelo de nómina es el que aplica a
ausencias/vacaciones (un archivo, filas independientes).

---

## (b) 🔴 Qué es extraíble SIN romper nada — la pregunta central

### Extraíble VERBATIM (no toca ningún flujo existente)

| Qué | De dónde | Por qué es seguro |
|---|---|---|
| **`decodificar()`** | `_evaluacion_import_transforms` | Es una función pura sin dependencias. Moverla a `services/_import_encoding.py` y que evaluaciones la importe de ahí es un re-export: cero cambio de comportamiento |
| **Los parsers de valores** | `_nomina_parsers.py` (82 líneas) | 🔴 **YA ESTÁ EXTRAÍDO Y SU ENCABEZADO LO DICE**: *"esta mitad es la reusable. El import histórico de vacaciones e inasistencias viene en el mismo formato… Va a necesitar estos parsers y nada del vocabulario de nómina."* No hay trabajo que hacer: se importa |
| **El PRESUPUESTO de tiempo** | la mitad de `LoteNomina` | `hay_margen`/`segundos`/`cortar` no tocan ni un campo de nómina. Ver (e) |
| **`clave_identidad`** | `_evaluacion_import_transforms` | Ya lo reusa `_superiores_matcher`. Es precedente, no propuesta |

### Extraíble con un cambio ACOTADO y verificable

**El decode de los routers.** Reemplazar las 3 líneas duplicadas de cada router por
`decodificar(content)` **sí cambia el comportamiento**: un archivo que hoy entra como basura
latin-1 pasaría a dar un error claro. Es el arreglo del bug, no una regresión — pero es un cambio
de comportamiento en dos flujos vivos y **merece su propio commit**, no venir de arrastre con la
base nueva.

### 🔴 Lo que NO se extrae en esta sesión (exigiría cambiar lo que funciona)

| Qué | Por qué no |
|---|---|
| **El ciclo preview→confirmar** | Evaluaciones y costos ya lo tienen, cada uno con su schema. Unificarlos obliga a reescribir dos endpoints en producción para un tercero que todavía **no tiene columnas definidas**. Se copia el PATRÓN, no el código |
| **La clasificación de resultados** | `ImportacionNominaEmpleadosResult` está acoplada al reporte de nómina (creados/actualizados/con_faltantes) y la consume la UI. Generalizarla es tocar un flujo vivo por un beneficio hipotético |
| **La lectura del CSV** | Los tres usan distinto delimitador, distinta normalización de claves (`_norm` vs `strip().upper()`) y distinta política de headers faltantes. Un lector genérico con tres flags **no es más simple que tres lectores de 8 líneas** |
| **El matcheo de empleado** | Ver (c): son legítimamente distintos |

---

## (c) El matcheo: **legítimamente distintos, y el nuevo no tiene ancla**

Hay tres caminos hoy, y **no son tres formas de hacer lo mismo**:

| Flujo | Ancla | Por qué esa |
|---|---|---|
| Nómina de empleados | **DNI** (`find_by_dni`) | El CSV lo trae y es único por empresa. Dedup exacto |
| Nómina de costos | **DNI** | Ídem |
| Evaluaciones | **apellido+nombre normalizado** (`clave_identidad`) | 🔴 **Porque el archivo NO trae DNI ni legajo.** No es una preferencia: es lo único que hay |
| Superiores (nuevo) | **apellido+nombre**, sin desempate | Reusa `clave_identidad`; el superior es la incógnita, no puede desempatarse por él |

⇒ **La diferencia no está en el algoritmo: está en QUÉ COLUMNA TRAE CADA ARCHIVO.** Unificarlos
sería inventar un "resolver universal" que reciba un dict de anclas posibles — más código y más
indirección para elegir entre dos `if`.

**Lo que sí está unificado y alcanza:** `clave_identidad` es UNA sola función que ya usan los dos
flujos por nombre. Eso es todo lo compartible.

### 🔴 El problema real de vacaciones: no tiene ancla

- El archivo de vacaciones **solo trae legajo**.
- `legajo` está **0 de 19** en producción. `dni` está 19/19 y `cuil` 19/19.
- ⇒ **Hoy ese import no puede resolver un solo empleado.**

Y no es un problema del import: es un dato que falta. Tres salidas, en orden de preferencia:

1. **Que RRHH cargue el legajo.** El import de nómina de empleados **ya lo soporta**: `"Legajo"`
   está en `HEADERS_OPCIONALES` y su comentario explica que se hizo opcional *"porque es el ancla
   del import de vacaciones, que no trae DNI ni CUIT"*. **Alguien ya vio esto venir.** Si el CSV
   de nómina que mandan trae la columna, se puebla solo al reimportar.
2. **Pedir que el archivo de vacaciones traiga DNI.** Es un pedido a RRHH sobre un archivo que
   todavía no está definido — o sea, **el momento exacto para pedirlo es ahora**.
3. Matcheo por nombre. ⚠️ El archivo de vacaciones **tampoco trae nombre** según lo que vimos.

🚩 **Esto es bloqueante y hay que decidirlo antes de escribir el parser.** Construir el flujo
completo y descubrir después que no matchea a nadie es el peor orden posible.

---

## (d) Idempotencia: las dos claves son viables, una necesita índice

### `vacaciones_pendientes` — ✅ ya está

```
UNIQUE (empleado_id, periodo)   → vacaciones_pendientes_empleado_periodo_key
```

Verificado en producción. La clave que proponés **ya existe como constraint**, así que el upsert
es directo (`on_conflict="empleado_id,periodo"`) y la base garantiza la unicidad. Sin trabajo.

### `solicitudes_ausencia` — 🔴 **no tiene NINGUNA unique**

Verificado: la tabla tiene **solo la PK sobre `id`**. La clave que proponés —empleado +
fecha_desde + fecha_hasta + tipo— **es viable pero hoy no está**.

**Es viable**, y hay evidencia: `vacaciones_repo.find_overlapping` ya trata
`(empleado, tipo, rango)` como la identidad de una licencia, y el service rechaza solapamientos
del mismo tipo. O sea que el modelo **ya asume** que esa combinación identifica una ausencia.

**Hace falta el índice**, por dos razones distintas:
1. **Correctitud del upsert**: PostgREST necesita una constraint única para `on_conflict`. Sin
   ella, "actualizar si existe" habría que hacerlo con un SELECT previo — que tiene ventana de
   carrera y es lo que el import de nómina evita a propósito (detecta el duplicado por la
   violación del UNIQUE, no por un chequeo).
2. **Performance del reimport**: sin índice, cada fila del archivo hace un scan.

⚠️ **Dos detalles antes de escribir la migración:**
- **`tipo_id` es NOT NULL**, así que entra en la clave sin problema de NULLs.
- 🔴 **Hoy no hay ninguna fila** (`solicitudes_ausencia` = 0), así que **crear la UNIQUE es
  gratis**. Con datos cargados, si hubiera duplicados históricos, la creación del índice
  **fallaría** y habría que deduplicar primero. Es la misma ventana que se aprovechó con la 088.

**Y una decisión de producto que hay que tomar, no asumir:** ¿dos ausencias del mismo empleado,
mismo tipo y mismas fechas son **la misma** (reimport) o **dos hechos distintos**? Con esa clave
se está declarando lo primero. Para ausencias parece correcto; conviene que RRHH lo confirme.

---

## (e) El presupuesto de tiempo: reusable en su mitad, y ya tiene una copia

`LoteNomina` (149 líneas) mezcla **dos cosas**:

| Parte | ¿Atada a nómina? |
|---|---|
| `segundos()` · `hay_margen()` · `cortar()` · `filas_con_margen()` | ❌ **NO.** Es tiempo puro: no toca un solo campo de nómina |
| `creados` · `actualizados` · `cargados_ok` · `con_faltantes` · `ids_creados` · `resultado()` | ✅ **SÍ.** `resultado()` proyecta a `ImportacionNominaEmpleadosResult` |

⇒ **La mitad de arriba es extraíble verbatim.**

🔴 **Y hay un dato que hace la decisión por sí solo: ya existe una SEGUNDA copia.** En la sesión
de mails escribí `services/_lote_mails.py`, que copia el patrón (`hay_margen`, reloj inyectado,
corte entre unidades, reporte parcial) con el comentario *"se copia el patrón, no el archivo:
aquel acumula filas de un CSV y este destinatarios"*.

Esa decisión fue correcta **con dos casos**. Con un **tercero** entrando (este import), la
cuenta cambia: tres copias de la misma lógica de reloj es exactamente el umbral donde extraer
deja de ser especulativo.

**Propuesta concreta:** `services/_presupuesto.py` con la clase del reloj y el margen; `LoteNomina`
y `LoteMails` la componen (no la heredan) y conservan sus contadores propios. ⚠️ **Eso toca dos
flujos vivos**, así que va en commit propio y con la suite existente como red — no de arrastre.

---

## (f) La previsualización: **no persiste nada, el front devuelve el payload**

Verificado en los dos flujos que tienen preview:

- **Evaluaciones**: `confirmar(req: ConfirmarRequest)` recibe `evaluados` completos y el
  orquestador **no re-parsea** (su docstring lo dice: *"persiste el payload que el humano APROBÓ
  (no re-parsea ni re-resuelve)"*). El archivo no se guarda en ningún lado.
- **Costos**: `confirmar_importacion_nomina(filas, empresa_id)` recibe las filas del preview.

⚠️ **Y es una decisión con costo, no gratis** — que es justo lo que preguntás:

- ✅ **A favor**: no hay estado de servidor que limpiar, no hace falta una tabla de staging ni un
  TTL, y en serverless (donde cada request puede caer en otra instancia) guardar el parseo en
  memoria **no funcionaría**.
- 🔴 **En contra, y es real**: el payload viaja **dos veces** por la red y el navegador lo tiene
  entero en memoria. Con las evaluaciones (10 evaluados, 307 resultados) es irrelevante. Con un
  archivo mensual de novedades de 200 filas × 8 columnas, sigue siendo chico (~100 KB).
  🚩 **El disparador para revisarlo** es un archivo de miles de filas, no el volumen actual.
- ⚠️ **Y hay un riesgo que no es de tamaño**: el cliente puede MODIFICAR el payload entre preview
  y confirm. Evaluaciones lo cubre revalidando la empresa de cada empleado en `confirmar`
  (`_validar_empresa`, fail-closed). **El import nuevo tiene que hacer lo mismo**: lo que se
  confirma no es lo que se parseó, es lo que el cliente devolvió.

---

## (g) Qué UI se puede construir hoy — **tu lectura es correcta, con una corrección**

✅ **Se puede construir hoy, sin conocer las columnas:**

| Pieza | Molde |
|---|---|
| Botón + selector de archivo | `SubirPaso.tsx` (88) o `ImportarNominaModal.tsx` (122) |
| Tabla de previsualización | `RevisarPaso.tsx` (97) + `EvaluadoFila.tsx` (72) |
| Resumen de resultados | `NominaResultView.tsx` (100) |
| Reporte de errores por fila | ídem — ya renderiza tres grupos con `fila`, `empleado` y motivo |
| El paso a paso subir→revisar→confirmar | `ImportarEvaluacionesPanel.tsx` (55) |

🔴 **La corrección: la tabla de previsualización NO es genérica hoy.** `EvaluadoFila.tsx` conoce
los campos de un evaluado (perfil, nota, resolución de identidad). Para que sea genérica hay que
diseñarla como **"filas con estado"**: `{ fila: number, resumen: string, estado: ok|advertencia|error, motivo?: string }`.

Eso **sí se puede definir hoy** y es lo que hace que el día del archivo real solo haya que
escribir el mapeo — pero es un componente **nuevo**, no una reutilización de `EvaluadoFila`.

⚠️ **Lo que NO se puede construir sin las columnas:** la pantalla de **revisión editable**. En
evaluaciones el humano corrige la resolución de identidad fila por fila; para eso hay que saber
qué campo se corrige. Si el import nuevo necesita edición, esa parte espera.

---

## (h) Dónde vive el mapeo de columnas cuando llegue

El molde ya existe y es exactamente el que nombrás. La separación de `_nomina_parsers.py` /
`_nomina_empleados_transforms.py` es **la respuesta**, y su encabezado ya lo anticipa:

```
services/_import_encoding.py          ← decodificar()  [compartido, extraído de evaluaciones]
services/_nomina_parsers.py           ← parse_fecha, parse_bool, limpiar…  [YA compartible]
services/_novedades_columnas.py       ← 🔴 EL ÚNICO ARCHIVO NUEVO cuando llegue el archivo:
                                          HEADERS, obligatorios, y parsear_fila()
services/novedades_import_service.py  ← el flujo, que NO cambia
```

**La prueba de que el molde funciona:** `_nomina_empleados_transforms.py` es exactamente eso para
nómina — 113 líneas de vocabulario puro, sin una línea de flujo. El archivo nuevo sería su
hermano.

---

## (i) 🔴 Lo honesto: se comparte MENOS de lo que parece

**Mi lectura, sin maquillar:** de las siete piezas, lo que de verdad se comparte es
**el encoding, los parsers de valores y el reloj del presupuesto.** Nada más.

- **El ciclo preview→confirmar es un PATRÓN, no código.** Las dos implementaciones existentes no
  comparten una línea y **está bien así**: cada una tiene el schema de su dominio. Un
  `ImportGenerico<T>` con callbacks para parsear, validar, resolver y persistir sería más difícil
  de leer que los tres flujos por separado, y cada caso nuevo le agregaría un parámetro.
- **La clasificación no se puede generalizar sin saber qué se clasifica.** Nómina tiene "cargado
  con faltantes" porque el email es opcional; evaluaciones tiene "anomalías del cruce" porque son
  dos archivos. El import nuevo va a tener sus propios estados, y **todavía no sabemos cuáles**.
- **El matcheo son tres anclas distintas porque son tres archivos distintos** (c).

⚠️ **El riesgo concreto de abstraer ahora:** el archivo real no está definido. Una base diseñada
contra un archivo hipotético va a acertar en lo fácil (leer un CSV) y errar en lo que importa
(qué significa una fila, qué la hace duplicada, qué la hace inválida). Y una base equivocada es
**más cara** que duplicar: hay que desarmarla con tres flujos colgando.

**Recomendación: extraer las tres piezas reales, copiar el patrón, y NO construir una base
genérica.** Lo que hace que "el día del archivo sea solo el mapeo" no es una abstracción: es que
el vocabulario de columnas viva en un archivo aparte, que es lo que (h) ya resuelve.

---

## (j) Líneas de todo lo que se tocaría

| Archivo | Hoy | Límite | Qué le pasa |
|---|---:|---:|---|
| `services/_evaluacion_import_transforms.py` | 126 | 150 | ✅ pierde `decodificar` (~24) al extraerse |
| `services/_nomina_parsers.py` | 82 | 150 | ✅ **no se toca**: ya es compartible |
| `routers/importacion_nomina_empleados.py` | 78 | 80 | ⚠️ **2 de margen.** El cambio de decode es −3/+1, así que ENTRA — pero cualquier otra cosa no |
| `routers/importacion_nomina.py` | 62 | 80 | ✅ |
| ⚠️ `services/_nomina_lote.py` | **149** | 150 | 🔴 **1 de margen.** Extraer el presupuesto lo BAJA; cualquier otro cambio exige cortar primero |
| `services/_lote_mails.py` | 96 | 150 | ✅ |
| `services/nomina_csv_service.py` | 120 | 150 | ✅ (solo si se unifica el decode) |
| **Nuevos** | | | `_import_encoding.py` (~35) · `_presupuesto.py` (~60) · `_novedades_columnas.py` (~90, cuando llegue) · `novedades_import_service.py` (~120) · repo + schemas + router |
| Front nuevos | | | tabla genérica de preview (~90) · panel del flujo (~60) · modal (~110) |

**+1 repo → 58 a portar a asyncpg** (regla 14).

---

## (k) Próximo número de migración libre: **089**

✅ **Verificado contra el catálogo vivo: las TRES están corridas.**

| | Evidencia en producción |
|---|---|
| **086** `empleado_superior_pendiente` | ✅ la tabla existe |
| **087** `mails_plantillas_y_remitente` | ✅ `plantillas_mail` y `mail_enviado` existen (2/2) |
| **088** `tipos_ausencia_jerarquia` | ✅ `tipos_ausencia.padre_id` existe |

`backend/migrations/` llega a 088 · `migracionAWS/` tiene 075-077 · **próximo libre: 089**.

**La 089 la necesitaría** la UNIQUE de `solicitudes_ausencia` de (d) — y conviene correrla
**antes de que se cargue el histórico**, por lo dicho ahí.

---

## Orden propuesto (si se avanza)

1. **Unificar el decode** — arregla un bug real, en dos flujos vivos, con la suite como red.
   Commit propio. **Es lo único urgente de este documento.**
2. **UNIQUE de `solicitudes_ausencia`** (mig 089) — hoy es gratis, con datos no.
3. **Extraer el presupuesto** — con la tercera copia en camino, deja de ser especulativo.
4. **Resolver el ancla de vacaciones con RRHH** 🔴 — bloqueante, y no es trabajo de código.
5. **La UI genérica y el flujo** — lo que se puede construir sin las columnas.
6. **El mapeo** — el día que llegue el archivo. Un archivo, como pide (h).

---

## Apéndice — inventario

**Encoding:** `routers/importacion_nomina_empleados.py:41-43` · `routers/importacion_nomina.py:38-40`
· `services/_evaluacion_import_transforms.py:46-68` (el bueno, con el bug del otro escrito en su
docstring).
**Parsers:** `_nomina_parsers.py` (82, ya compartible, encabezado lo declara).
**Lectura CSV:** `nomina_empleados_service.py:62` · `nomina_csv_service.py:39` ·
`evaluacion_import_service.py:34-51`.
**Preview→confirmar:** `evaluacion_import_orchestrator.py:46,62` · `nomina_csv_service.py`.
**Presupuesto:** `_nomina_lote.py:65-105` · `_lote_mails.py:55-85` (la copia).
**Matcheo:** `find_by_dni` · `clave_identidad` (`_evaluacion_import_transforms:98`) ·
`_superiores_matcher.clave`.
**Catálogo vivo:** `legajo` 0/19 · `dni` 19/19 · `cuil` 19/19 · `solicitudes_ausencia` 0 filas y
**sin UNIQUE** · `vacaciones_pendientes` 0 filas **con** `UNIQUE(empleado_id, periodo)`.

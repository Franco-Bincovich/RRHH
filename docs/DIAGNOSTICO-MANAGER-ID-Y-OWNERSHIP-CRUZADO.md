# Diagnóstico READ-ONLY — `manager_id` desde el import + ownership cruzado entre empresas

> **2/8/2026 · Sesión de diagnóstico. NO se escribió una sola línea de código.**
> Todo lo de acá está verificado contra los archivos fuente, con `archivo:línea`.

---

## Resumen ejecutivo (lo que hay que saber antes de leer el detalle)

1. **El camino de escritura de `manager_id` ya existe entero.** El schema lo acepta, el repo lo
   persiste, la validación lo chequea. **Lo único que falta es el puente CSV→schema**, que son 2
   líneas en `_base_nomina`. El trabajo real no es escribir el campo: es *resolver el jefe*.
2. **La intersección empresa ∩ ownership NO vive en `_ownership_filter.py`.** Vive en el WHERE del
   repo, como dos predicados independientes (`.eq("empresa_id")` y `.in_("empleado_id", ids)`). El
   conjunto de ownership **ya es ciego a la empresa** (`ids_subordinados` es un `.eq("manager_id")`
   pelado). ⇒ **El cambio de la Parte B no toca el archivo más delicado del repo.**
3. **El dashboard de mando YA implementa la regla nueva** (no recibe `empresa_id` en absoluto).
   Cero cambios ahí — y por eso mismo, si la Parte A sale sola, ese dashboard va a contar gente que
   el listado no muestra.
4. **Las escrituras ya etiquetan bien**: la empresa de la fila sale del empleado, no del header.
5. 🔴 **En producción hay UNA sola empresa.** El caso cruzado **no es reproducible con datos reales**
   hasta que exista la segunda. Todo lo de la Parte B se verifica con fakes o no se verifica.

---

# PARTE A — Escribir `manager_id` desde el import

## (a) Dónde se pierden exactamente las dos columnas

**Se leen bien.** `services/_nomina_empleados_transforms.py:111-112`:

```python
"_superior_apellido": limpiar(_get(row, "Apellido Superior")),
"_superior_nombre":   limpiar(_get(row, "Nombre Superior")),
```

Están además declaradas como requeridas en `HEADERS` (`:18-19`), así que un archivo sin ellas se
rechaza entero. El comentario de `:108` ya avisa: *"No se persisten en empleados"*.

**Se pierden en UN solo punto: `schemas/importacion_nomina_empleados.py:73-85`.**
`_base_nomina(f, email)` arma el dict de campos CSV→empleado y **no incluye `manager_id`**.
`build_create` (`:88`) le suma `empresa_id`+`area_id`; `build_update` (`:93`) solo `area_id`.
Ninguno de los dos mira `f["_superior_*"]`. El docstring del módulo lo dice explícito (`:7`):

> *"Preserva el superior sin resolver el manager (pieza posterior)."*

Y `nomina_empleados_service._procesar_fila` (`:94-145`) nunca lee esas dos claves: pasa de
`tx.parsear_fila(raw)` a `build_create`/`build_update` sin tocarlas.

**Lo que YA funciona aguas abajo (no hay que construirlo):**
- `schemas/empleado.py:103` y `:121` — `EmpleadoCreate.manager_id` y `EmpleadoUpdate.manager_id`
  existen, `Optional[UUID]`. `EmpleadoCreateNomina`/`EmpleadoUpdateNomina` los heredan.
- `repositories/_empleado_write_repo.py:34-35` (create) y `:51-53` (update) los persisten, con el
  manejo correcto del null explícito (`exclude_unset` para distinguir "sin superior" de "no tocar").
- `services/_empleados_write.py:54,98,99` valida manager y ciclos.

⇒ **El puente son ~2 líneas.** El costo real está en (b) y (c).

## (b) ¿Sirve lo de evaluaciones? Sí, la mitad — y la otra mitad no.

### SÍ reusar: `clave_identidad` (`services/_evaluacion_import_transforms.py:98-100`)

```python
def clave_identidad(apellido: str, nombre: str) -> str:
    return normalizar_campo(f"{apellido} {nombre}")   # trim + colapsa espacios + sin acentos + casefold
```

Es **pura, sin I/O, sin dependencias del proyecto** (lo dice su propio encabezado, `:4`). Hace
exactamente lo que hace falta y hace lo que `_norm` de nómina **no** hace: sacar acentos
(`_sin_acentos`, `:88`). Reusarla —importarla, no copiarla— también garantiza que el jefe se
normalice **igual** en los dos imports, que es lo que permite que una equivalencia aprendida en un
import sirva en el otro.

### NO reusar la clase `ResolutorIdentidad` (`services/evaluacion_matcheo_service.py:18`)

Cuatro razones concretas, todas verificadas:

1. **Está acoplada a `EvaluacionMatcheoRepo`** (`:19-20`): sus dos lecturas son
   `find_equivalencia(...)` sobre `evaluacion_equivalencias` y `find_empleados_empresa(...)`.
   Ninguna de las dos aplica al import de nómina.
2. **Devuelve `ResolucionIdentidad`**, un schema de `schemas/evaluacion_import.py`. Meter nómina ahí
   acopla dos imports que hoy son independientes.
3. 🔴 **Su desempate es el superior** (`_anotar_superior`, `:56-64`; `_superior_coincide`, `:67-75`).
   Acá el superior **es la incógnita**: usar esa señal para resolverlo es circular.
4. 🔴 **Su invariante documentada es "SIEMPRE dentro de la empresa del lote… nunca global"**
   (docstring `:3-4`) — que es *exactamente* lo que la decisión de producto nueva rompe.

### Lo que sí se copia como criterio (no como código)
- **Cero matcheo difuso por similitud** (`:8`: *"un apellido parecido le asignaría notas a la persona
  equivocada"*). Acá el daño equivalente es peor: un `manager_id` mal asignado **le da a un mando
  medio acceso de lectura y escritura sobre gente que no es suya**.
- **Los tres estados** `resuelto` / `ambiguo` / `sin_candidato`. Con la decisión nueva se agrega un
  cuarto eje: la búsqueda ya **no** se acota a la empresa del empleado.

⇒ **Propuesta:** un resolver propio y chico (`services/_nomina_superiores.py`, ver (o)), que importe
`clave_identidad` y aplique estos criterios. No una generalización del de evaluaciones.

## (c) 🔴 El problema de orden

**Cómo se procesa hoy** — `services/nomina_empleados_service.py:68`:

```python
for n, raw in lote.filas_con_margen(list(reader)):
    nuevo, faltan, empleado_id = self._procesar_fila(raw, n)
```

**Una sola pasada, secuencial, con el INSERT/UPDATE ejecutado dentro de la iteración**
(`:125` update / `:131` create). No hay segunda pasada, no hay índice en memoria de lo creado, y
`_procesar_fila` no devuelve nada del superior.

**Consecuencia con el archivo real:** Libertelli está en la fila 11 y tiene 13 subordinados. Las 10
filas anteriores se procesan **antes** de que su registro exista → si el manager se resolviera dentro
del loop, esas 10 quedarían sin jefe y las 3 posteriores sí lo tendrían. Un resultado que depende del
orden de las filas del Excel es exactamente el tipo de bug que nadie reproduce.

**Qué hace falta para que el orden no importe: una SEGUNDA PASADA.**

- En el loop, acumular `(empleado_id, clave_identidad(sup_apellido, sup_nombre))` en una lista —
  **sin resolver nada**. Costo: cero queries extra.
- Después del loop (y **antes** del evento de auditoría de `:82`), una función que:
  1. traiga **una sola vez** el universo de candidatos a jefe (ver abajo qué universo),
  2. arme el índice `clave → [empleado_id]`,
  3. resuelva las N claves contra ese índice **en memoria**,
  4. emita solo los UPDATE de `manager_id` de los que resolvieron.

  Total: 1 lectura + K escrituras, no N×2 queries.
- **Qué universo traer:** con la decisión nueva, **no** se puede acotar a la empresa de cada
  empleado. Las opciones son (i) todos los empleados de todas las empresas —hoy 19 filas, mañana no—
  o (ii) las empresas presentes en el archivo. La (ii) es la correcta: acota sin inventar una regla,
  y el CSV trae la columna `Organismo` en cada fila.
- 🔴 **Interacción con el presupuesto de tiempo.** `LoteNomina.filas_con_margen` (`:68`) puede cortar
  el archivo a la mitad (`parcial=True`). La segunda pasada debe correr **solo sobre las filas que
  efectivamente se procesaron** (por eso se acumula en el loop, no se re-lee el CSV). Lo que quede
  sin resolver cae en el mecanismo de (d) — que es el mismo destino que el de un jefe ausente. Es
  decir: el corte parcial degrada al mismo estado que ya hay que soportar, no a uno nuevo.
- 🔴 **Ciclos.** La segunda pasada escribe managers en lote. `ensure_no_ciclo_manager` hoy solo corre
  en el camino de update (`_empleados_write.py:99`), **no en el de create** (`:54` no lo llama). El
  bulk de la segunda pasada **tiene que** chequear ciclos, y con la corrección de (f).

**El caso real del archivo, para dimensionar:** 5 de los 6 jefes **no están en el archivo**. La
segunda pasada no los va a encontrar por más bien que esté escrita. Sin (d), 6 de 19 empleados
quedan sin jefe y **sin rastro de quién era**.

## (d) Dónde guardar el nombre del jefe no encontrado

Tres opciones evaluadas:

| | Dónde | A favor | En contra |
|---|---|---|---|
| **1** | 2 columnas en `empleados` (`superior_apellido_csv`, `superior_nombre_csv`) | 0 repos nuevos · 0 joins · migración trivial | Quedan NULL para siempre en el 90% de las filas · "dame los pendientes" es un scan de `empleados` con predicado compuesto · residuo de import en la tabla central |
| **2** ✅ | Tabla nueva `empleado_superior_pendiente (empleado_id PK, empresa_id, apellido_csv, nombre_csv, created_at)` | El estado pendiente **es transitorio**: la fila se borra al resolver, y "dame los pendientes" es un `SELECT *` de una tabla que normalmente está vacía · aloja después el mapeo aprendido (espejo de `evaluacion_equivalencias`) · no ensucia `empleados` | +1 repo a portar a asyncpg (**regla 14**) · +1 migración |
| **3** | Reusar `evaluacion_equivalencias` | Ya existe, ya es "texto CSV → empleado confirmado a mano" | ❌ Es de evaluaciones por nombre y por scope · mezclar dos dominios en una tabla para ahorrar una migración es exactamente el tipo de atajo que después nadie entiende |

**Recomendación: opción 2.** El argumento decisivo no es la limpieza sino la **consulta del botón**:
"resolver pendientes" pregunta *"¿qué quedó sin resolver?"*, y esa pregunta sobre la opción 1 es un
barrido de toda la tabla de empleados que además crece con cada empleado que nunca tuvo pendiente.
Sobre la opción 2 es leer una tabla que en estado sano tiene 0 filas.

**Dos detalles de diseño que hay que fijar antes de escribirla:**
- `empresa_id` es **la del empleado**, no la del jefe (que es justamente lo desconocido). Sirve para
  scopear el listado del botón, no para acotar la búsqueda.
- 🔴 La fila se escribe **también cuando el estado es `ambiguo`** (dos homónimos), no solo cuando es
  `sin_candidato`. Son los dos casos que un humano tiene que desempatar; distinguirlos en el listado
  sí (un campo `motivo`), pero los dos van a la misma tabla.

**Si se prefiere no sumar un repo** (regla 14 es real: hoy son 54 repos a portar), la opción 1 es
defendible y **no bloquea nada** — la decisión es reversible con una migración. Lo que **no** es
aceptable es no guardar nada: sin eso, el botón de (d) no tiene de dónde sacar la lista y la única
alternativa es re-subir el CSV, que es el flujo que ya existe.

## (e) `ensure_manager_valido` — dónde está, quién la llama, qué se rompe

**Dónde:** `services/_empleados_utils.py:35-61`.

```python
if manager_id is None: return
if not repo.find_by_id(str(manager_id), empresa_id):
    raise AppError("Superior no encontrado", "MANAGER_NOT_FOUND", 404)
```

**Quién la llama: exactamente dos call sites**, los dos en `services/_empleados_write.py`:
- `:54` — alta (`create_empleado`)
- `:98` — edición (`update_empleado`)

No hay más. Es una superficie chica, lo cual es una buena noticia para el cambio.

🔴 **Su docstring documenta como MOTIVO justamente lo que la decisión de producto ahora quiere**
(`:40-41`):

> *"Importa más allá de la integridad del organigrama — el ownership de mandos_medios se resuelve
> por manager_id, y un superior de otra empresa haría que `ids_subordinados` cruce la frontera."*

Eso **no era un efecto colateral: era el objetivo**. La decisión nueva lo convierte en la feature.
⚠️ **Ese docstring es lo primero que hay que reescribir**, o el próximo que lo lea va a "arreglar" el
aflojamiento pensando que es una regresión de Fase 2.

**Qué cambia:** la función **no se borra**. Sigue haciendo algo necesario —verificar que el superior
**exista**— y sigue dando el 404 idéntico. Lo que cambia es el scope: pasar `empresa_id=None`
(existencia global) en lugar de la empresa del request. La FK `empleados_manager_id_fkey`
(`db/schema.sql:1094`) ya garantiza existencia a nivel base, pero fallaría con un error crudo de
Postgres en vez de un `AppError` legible — por eso la validación se queda.

**Qué se rompe si se afloja:**

1. **Tests.** `tests/test_empleado_manager_empresa.py` afirma el rechazo en al menos 4 lugares
   (`:134`, `:142`, `:215`, `:222`). El archivo entero existe para probar esto — su docstring (`:5-7`)
   explica el porqué con las mismas palabras que el de la función. **Se invierten, no se borran**
   (regla del repo: un test que cierra un pendiente se MUEVE al que verifica lo contrario).
2. **La invariante de Fase 2 documentada en `CLAUDE.md`.** Hay que escribir la excepción **en el
   docstring de la función y en la sección "Patrón de barrera de empresa"**, con el porqué, o la
   próxima sesión la revierte de buena fe.
3. **Un ensanchamiento real, chico:** `find_by_id(manager, None)` acepta cualquier UUID existente →
   un admin de la empresa A puede confirmar que un UUID de empleado existe en el sistema. Requiere
   adivinar un UUID v4, y el 404 sigue siendo idéntico al de "no existe", así que **no hay oráculo de
   enumeración nuevo** — pero es honesto decir que la superficie creció.
4. 🔴 **El impacto de verdad no está acá.** Aflojar esta validación es 1 línea; lo que se rompe es
   **río abajo**, en todo lo que asume que el organigrama no cruza empresas. Eso es la Parte B.

## (f) `ensure_no_ciclo_manager` con cadenas cruzadas — **NO, hoy no funciona**

`services/_empleados_utils.py:104-125`. El recorrido (`:121`):

```python
nodo = repo.find_by_id(actual, empresa_id)
if nodo is None or nodo.manager_id is None:
    return          # ← "no hay ciclo"
```

Y el call site le pasa la empresa: `_empleados_write.py:99` →
`ensure_no_ciclo_manager(repo, id, data.manager_id, empresa_id)`.

**Con una cadena que cruza empresas, el `find_by_id` acotado devuelve `None` en el primer salto que
sale de la empresa, y la función retorna "no hay ciclo".** Un ciclo A(empresa 1) → B(empresa 2) →
A(empresa 1) **no se detecta**, y un ciclo entre empresas cuelga `ids_subordinados` igual que uno
interno.

El docstring lo dice sin saber que se iba a volver el problema (`:111-113`):

> *"`empresa_id` acota el recorrido a la empresa… recorrer dentro de la empresa evita que una cadena
> cruzada (dato ya corrupto) altere el veredicto."*

Bajo la regla vieja, una cadena cruzada era **dato corrupto** y acotar era lo correcto. Bajo la
nueva es **dato legítimo**, así que el recorrido tiene que ser global.

**Fix: un argumento** — pasar `empresa_id=None` desde `_empleados_write.py:99`. `max_saltos=50`
(`:105`) sigue siendo la red contra datos ya corruptos y **cobra más importancia**, porque el grafo
global es más grande que el de una empresa. No hace falta subirlo: 50 niveles de jerarquía es absurdo
en cualquier organigrama real.

🔴 **Segundo hallazgo, independiente:** el chequeo de ciclos **no corre en el alta**
(`_empleados_write.py:54` llama a `ensure_manager_valido` pero **no** a `ensure_no_ciclo_manager`).
Hoy es inocuo —un empleado recién creado no puede ser jefe de nadie todavía— pero **el bulk de la
segunda pasada de (c) escribe managers sobre empleados que ya existen**, así que ese camino sí tiene
que chequear ciclos explícitamente. No se puede asumir que lo hereda del alta.

---

# PARTE B — Ownership cruzado

## (g) 🔴 El mapa completo — dónde se aplica cada eje

```
routers/vacaciones.py:45,52,59,74,79        get_empresa_id(request)  ─┐  (X-Empresa-Id)
routers/ausencias.py:38,44,51,66,71                                   │
                                                                      │
  ┌───────────────────────────────────────────────────────────────────┘
  │
  ├─ EJE OWNERSHIP (ciego a la empresa, de punta a punta)
  │    _ownership_filter.resolver_empleado_ids            (:83)
  │      └→ _ownership_filter.resolver_filtro_empleados   (:32)
  │           └→ ownership.ids_empleados_visibles         (ownership.py:21)
  │                ├→ repo.find_by_user_id(user_id)       (empleado_ownership_repo.py:19)  ← SIN empresa
  │                └→ repo.ids_subordinados(emp_id)       (empleado_ownership_repo.py:42)  ← SIN empresa
  │                                                          `.eq("manager_id", empleado_id)` pelado
  │         devuelve → (empleado_ids, vacio)
  │
  └─ EJE EMPRESA (viaja APARTE, directo al repo)
       VacacionesRepo.find_all(empresa_id, empleado_ids, ...)
         if empresa_id: q = q.eq("empresa_id", str(empresa_id))     ← predicado 1
         if empleado_ids is not None: q = q.in_("empleado_id", ids) ← predicado 2
```

### 🔑 El hallazgo central

**La intersección empresa ∩ ownership NO ocurre dentro de `_ownership_filter.py`. Ocurre en el WHERE
del repo, como dos predicados independientes unidos por AND.**

`_ownership_filter.resolver_filtro_empleados` recibe `empresa_id` **para una sola cosa**: acotar la
resolución del filtro de **área** (`:65`, `repo.ids_empleados_por_area(empresa_id, area_id)`). No lo
usa para nada más — su propio docstring lo dice (`:52`: *"empresa activa (None = consolidado) para
acotar la resolución de área"*).

⇒ **El conjunto de ownership ya cruza empresas hoy.** `ids_subordinados` no tiene ni un `.eq` de
empresa. Lo único que impide que un mando vea al subordinado de otra empresa es el `.eq("empresa_id")`
que el repo aplica **por separado**.

### Los otros dos helpers (camino por fila, no por listado)

- **`ownership.puede_gestionar_empleado`** (`ownership.py:57-80`) — delega en
  `ids_empleados_visibles`, **también ciego a la empresa**. Call sites (9):
  `vacaciones_service.py:81,103,119` · `_vacaciones_write.py:50` · `_ausencias_write.py:38,65,104` ·
  `ausencias_service.py:68` · `vacaciones_pendientes_service.py:78`.
  **La empresa se aplica ANTES, en la query que trae la fila** (`find_by_id(str(id), empresa_id)`).
- **`_empleado_scope.ensure_empleado_visible`** (`_empleado_scope.py:53-84`) — es literalmente
  `ensure_empleado_de_empresa(...)` (empresa, **en el WHERE del repo**) **y después**
  `puede_gestionar_empleado(...)` (ownership, en Python). Los dos fallan con el mismo 404.
  Call sites: `vacaciones_service.py:72,134` · `vacaciones_pendientes_service.py:98,105`.

**En los tres caminos el patrón es el mismo: la empresa está en la QUERY, el ownership está DESPUÉS,
en Python.** Eso es lo que hace que el cambio de (h) sea chico.

## (h) El cambio mínimo

### `_ownership_filter.py` NO SE TOCA. Ni una línea.

Es la conclusión que sale de (g): ese archivo no aplica el filtro de empresa. El eje empresa es un
**parámetro que viaja aparte**. Alcanza con **neutralizarlo en el punto donde se lee**:

```python
# services/_ownership_filter.py (vecino, misma unidad de sentido) o utils/empresa.py
def empresa_efectiva(empresa_id, rol):
    """🔴 EXCEPCIÓN DELIBERADA A LA BARRERA DE EMPRESA (Fase 2) — leer antes de "corregir".

    Para mandos_medios el manager_id REEMPLAZA al filtro de empresa: sus subordinados son
    suyos sin importar de qué empresa del grupo sean, en lectura Y en escritura (decisión de
    producto, 2/8/2026). Devolver None acá saca el `.eq("empresa_id")` de la query y deja al
    `.in_("empleado_id", ids)` del ownership como ÚNICA restricción — que es exactamente la
    semántica pedida, porque ese conjunto ya es ciego a la empresa (ids_subordinados no filtra).

    Es seguro SOLO porque para mandos_medios el ownership NUNCA devuelve "sin restricción":
    ver la invariante en el docstring de resolver_filtro_empleados y el test que la fija.
    NO extender esta excepción a otros roles ni a otras secciones.
    """
    return None if rol == "mandos_medios" else empresa_id
```

Se aplica en los puntos donde `empresa_id` entra a un service de vacaciones/ausencias. Es un
**reemplazo in-line, 0 líneas netas** en cada call site.

### Dos matices que hay que entender antes de escribirlo

1. **`ensure_empleado_visible` queda apoyado 100% en el ownership.** Con `empresa_id=None`,
   `ensure_empleado_de_empresa` deja de restringir y la única barrera que queda es
   `puede_gestionar_empleado`. Es correcto por diseño (fail-closed: un mando sin subordinados da
   `[]` → `False`), pero significa que **un `manager_id` mal escrito ya no tiene una segunda red**.
   Esto es el argumento más fuerte para que la Parte A resuelva jefes de forma conservadora
   (sin fuzzy, ambiguo→pendiente) y para que ninguna de las dos partes salga sin la otra.
2. **El filtro de área para un mando pasa a resolverse sobre todas las empresas**
   (`ids_empleados_por_area(None, area_id)`). Es lo consistente: un mando con subordinados en dos
   empresas los tiene en dos áreas distintas, y la intersección con `visibles` lo recorta a su gente
   igual. Pero conviene documentarlo, porque `etiquetaArea` del front sufija con el nombre de la
   empresa justamente porque las áreas son por empresa.

### Superficie a tocar (los 13 endpoints no cambian de firma)
`vacaciones_service.py` (6 usos de `empresa_id`) · `ausencias_service.py` (5) ·
`vacaciones_pendientes_service.py` (3). Los routers **no se tocan**: siguen pasando
`get_empresa_id(request)` y el service decide. Eso mantiene el cambio en una sola capa.

## (i) 🔴 El contrato `(ids, vacio)` — verificación

**El contrato no se rompe, y la razón es estructural, no accidental: el cambio no entra a
`_ownership_filter.py`.** Los tres retornos siguen exactamente igual.

Pero hay una invariante de la que **ahora depende la seguridad del sistema entero**, y hoy no está
escrita ni testeada:

> **Para `rol == "mandos_medios"`, `resolver_filtro_empleados` NUNCA puede devolver `(None, False)`.**

Por qué es la pieza crítica: `(None, False)` significa *"el caller NO filtra por empleado"*. Hasta
hoy, si eso pasara para un mando, el `.eq("empresa_id")` del repo seguiría acotándolo a su empresa —
un bug feo pero contenido. **Después de (h) ese `.eq` ya no está.** `(None, False)` + `empresa_id=None`
= **la tabla entera de todas las empresas**.

**Verificación de que hoy se cumple** (`_ownership_filter.py:58-80`):
- `visibles = ids_empleados_visibles(...)`. Para `mandos_medios` solo puede ser `[]` o `[ids]`
  (`ownership.py:44-54`: el `return None` está en la rama de admin/gerencia, y la rama de
  `mandos_medios` siempre devuelve una lista — como mínimo `[emp_id]`, su propio registro).
- `[]` → `:59-60` → `(None, True)`. ✅
- `[ids]` → `:62-63` `conjuntos.append(visibles)` → `conjuntos` **no vacío** → la línea `:74`
  (`return None, False`) es **inalcanzable**. El retorno final `:80` es `(inter, False)` con `inter`
  no vacío, o `(None, True)`. ✅

⇒ **Hoy la invariante se cumple.** No está garantizada por nada más que esa lectura del código, así
que el cambio tiene que traer **el test que la fija** (ver (q)). Es la aserción más importante de
toda esta tanda.

`resolver_empleado_ids` (`:83-104`) no la afecta: solo estrecha (`:101` acota a un id, `:103` va a
`(None, True)`). Nunca ensancha.

## (j) Las escrituras — confirmado, la empresa sale del empleado ✅

`services/_vacaciones_write.py:52`:
```python
empresa_id = repo.find_empresa_for_empleado(str(data.empleado_id))
```
→ `vacaciones_repo.find_empresa_for_empleado` = `SELECT empresa_id FROM empleados WHERE id=…`
**sin filtro de empresa**. Y se escribe así: `repo.save(str(data.empleado_id), empresa_id, ...)`
(`:71-76`). El `SolicitudVacacionesCreate` **no tiene** campo `empresa_id` — el usuario no lo provee.

Idéntico en `services/_ausencias_write.py:40-46`. El docstring del service lo declara como regla de
negocio (`vacaciones_service.py:6`: *"empresa_id se hereda del empleado (no lo provee el usuario)"*).

**Auditoría:** también correcta. `_ausencias_write` audita con `row.empresa_id` (la de la fila);
`vacaciones_service.py:109` (cancel) con `row.empresa_id`. **No es el bug de `_costos_write.py:80`.**

⇒ **Un mando aprueba una vacación de un subordinado de empresa B → la fila queda etiquetada empresa
B.** Correcto, y aparecerá en los listados de B para un admin de B. **Cero cambios en las escrituras.**

**Dos consecuencias que hay que decir en voz alta:**
- `verificar_periodo_abierto(empresa_id, ...)` (`_vacaciones_write.py:55`) usa la empresa **del
  empleado** → el bloqueo de período que aplica es el de **B**, no el del mando. Es lo correcto (el
  período es de la empresa dueña del dato) pero es contraintuitivo: un mando puede quedar bloqueado
  por un cierre de una empresa que no es la suya.
- 🔴 `cancel` y `actualizar` (`vacaciones_service.py:102,118`) hacen `find_by_id(str(id), empresa_id)`
  con el **header**. **Sin (h), un mando ni siquiera puede CARGAR la fila del subordinado ajeno para
  cancelarla** — le da 404 antes de llegar al ownership. El aflojamiento de lectura de (h) es lo que
  habilita la escritura; no son dos cambios, es uno.

## (k) El dashboard de mando — **ya cuenta por ownership** ✅

`services/dashboard_equipo_service.py:40`:
```python
def get_dashboard(self, user_id: str, rol: str) -> DashboardEquipoResponse:
```

**No recibe `empresa_id`. En absoluto.** Resuelve `ids_empleados_visibles(user_id, rol, ...)` (`:52`)
y se lo pasa tal cual al repo. Y `repositories/dashboard_equipo_repo.py` — leído entero — **no tiene
un solo `.eq("empresa_id")`**: `count_empleados` filtra por `.in_("id", ids)`, `_q_solapando` por
`.in_("empleado_id", ids)`. Idem `services/equipo_service.py:47`.

⇒ **Cero cambios. Ya implementa la regla nueva.**

🔴 **Y de ahí sale el riesgo de orden más importante de todo el diagnóstico:** si la **Parte A sale
sola** (managers cruzados escritos) sin la Parte B, este dashboard **ya** va a contar a los
subordinados de la otra empresa —porque nunca filtró por empresa— mientras el listado de
`/vacaciones` **no** los va a mostrar (el `.eq("empresa_id")` del repo sigue puesto). **Números que no
coinciden con la lista.** Exactamente el síntoma que la pregunta (k) anticipaba, pero llegando por A
y no por B. Ver (n).

## (l) Reportes y exports

**Exports de vacaciones y ausencias: SÍ componen ownership.** ✅
`VacacionesService.exportar:64` llama a `self.get_all(...)` con los mismos parámetros — es el mismo
camino, mismo `resolver_empleado_ids`, mismo `verificar_limite_export` sobre el total ya filtrado.
Idéntico en `AusenciasService.exportar`. Es la invariante 2 del Bloque B (list ↔ export), y el
barrido de `tests/test_paridad_list_export.py` la sostiene.
⇒ **Después de (h), un mando que exporta obtiene sus subordinados de otras empresas.** Que es lo
pedido. Sin cambios adicionales.

**Reportes: NO componen ownership.** 🔴 Verificado por grep: cero apariciones de `ownership`,
`ids_empleados_visibles` o `puede_gestionar_empleado` en `services/reportes/` (los 9 submódulos),
`reporte_service.py` y `routers/reportes.py`. Los reportes toman empresa+área **del formulario**
(principio Vista vs Acción) y no conocen el rol.

**Hoy NO es una fuga**, porque `Seccion.REPORTES` **no está** en `MANDOS_MEDIOS_SECCIONES`
(`utils/permisos.py:73`, que es `frozenset({VACACIONES, AUSENCIAS})`) → un mando recibe 403 en el
gate antes de tocar el generador.

**Es una mina.** El día que alguien agregue `REPORTES` a `MANDOS_MEDIOS_SECCIONES` —o cree un reporte
"de mi equipo"— va a devolver datos org-wide sin filtrar por ownership, sin error y sin aviso. Es el
mismo patrón que el falso positivo de Fase 2 (*"el router pasando empresa_id no prueba nada"*).
**Recomendación:** un comentario en `services/reportes/_common.py` y, mejor, un test que afirme que
`MANDOS_MEDIOS_SECCIONES == {VACACIONES, AUSENCIAS}` con la razón escrita — barato y cierra la clase.

## (m) El selector de empresa del sidebar para un mando

**Qué pasa hoy** (`frontend/components/layout/EmpresaSelector.tsx`):
```
:21   fetchEmpresas()                       → GET /api/empresas
                                              gateado Seccion.EMPRESAS + READ (routers/empresa.py:25)
                                              → un mando recibe 403
:23   .catch(() => {})                      → se traga el error, empresas queda []
:26   if (empresas.length === 0) return null → NO RENDERIZA
```

⇒ **El selector ya no se le muestra a un mando medio — pero por accidente, no por diseño.** Depende
de un 403 tragado en un `.catch` vacío. Si mañana `GET /api/empresas` se abre a más roles (razón
perfectamente plausible: el front necesita nombres de empresa para etiquetar), el selector reaparece
solo, sin que nadie lo decida.

**Y hay un residuo que sí viaja:** `services/api.ts:24` inyecta
`headers["X-Empresa-Id"] = empresaId ?? "todas"` leyendo `empresaStore` (localStorage) en **todas**
las llamadas, sin mirar el rol. Un valor viejo —un usuario al que le cambiaron el rol, un navegador
compartido— sigue mandando una empresa concreta. **Hoy eso sí restringe** los listados del mando. Y
un mando no tiene forma de cambiarlo ni de verlo, porque el selector no se renderiza: **queda con un
filtro invisible que no puede sacar.** Eso ya es un bug menor, hoy, antes de todo este cambio.

**Después de (h), ese header pasa a ser inocuo para el mando** — que es la solución real del residuo.

**Recomendación:** hacer el ocultamiento **explícito** en vez de heredado del 403 (`if (rol ===
"mandos_medios") return null`, o gatear por permiso como hace el sidebar con `NAV_GROUPS`) y limpiar
el valor guardado para ese rol. **Pero es cosmético y va DESPUÉS**: el backend de (h) es lo que hace
que el header deje de importar, y con eso el bug del filtro invisible se cierra solo.

---

# TRANSVERSAL

## (n) ¿Se pisan las dos partes? Sí, en una dirección — y el orden importa

**A sin B = estado inconsistente visible.** Apenas el import escriba un `manager_id` cruzado:
- `ids_subordinados` (ciego a la empresa) lo devuelve → `DashboardEquipoService` (sin filtro de
  empresa) **lo cuenta**;
- el listado de `/vacaciones` (con `.eq("empresa_id")`) **no lo muestra**;
- ⇒ el dashboard dice 14 y la lista muestra 1. Ver (k).

**B sin A = inerte.** Sin un solo `manager_id` cruzado en la base (hoy: 0 managers de cualquier tipo,
1 sola empresa), (h) no cambia absolutamente ningún resultado. Es el cambio más seguro de los dos
**precisamente porque hoy no tiene datos sobre los que actuar.**

**Orden recomendado (3 sub-sesiones, una tarea atómica cada una — regla 7):**

| # | Qué | Por qué en ese lugar |
|---|---|---|
| **1** | **(e) + (f)** — aflojar `ensure_manager_valido` a existencia global · `ensure_no_ciclo_manager` con `empresa_id=None` · invertir los tests de `test_empleado_manager_empresa.py` · **reescribir los dos docstrings con la excepción y su porqué** | Es la habilitación. Dos líneas de código y mucho texto. Sin esto, ni el import ni una edición manual pueden crear un manager cruzado ni siquiera para testear. Y `ensure_no_ciclo_manager` **tiene que** estar arreglado antes de que exista el primer manager cruzado, no después. |
| **2** | **(h) + (i)** — `empresa_efectiva` en los 3 services · el test de la invariante `(None, False)` · el test repo-level de que el `.eq("empresa_id")` desaparece de la query | Inerte hasta que existan datos ⇒ **el momento más barato y más seguro para hacerlo**. Que los caminos de lectura ya estén listos cuando aparezca el primer manager cruzado. |
| **3** | **(a)+(b)+(c)** — el puente CSV→schema, el resolver, la segunda pasada. **Requiere dividir `nomina_empleados_service.py` primero** (ver (o)). | Es lo que produce los datos. Ponerlo último significa que el día que el primer `manager_id` cruzado existe, **todos** los caminos que lo leen ya lo manejan. |
| **4** | **(d)** — tabla/columnas de pendientes + botón | Es sobre el residuo de 3. No tiene sentido antes de saber cuántos quedan pendientes de verdad. |
| **5** | **(m)** — ocultar el selector explícitamente | Cosmético. Después de 2 el header ya es inocuo. |

**Regla 15:** cada una de esas sub-sesiones escribe su entrada en `docs/BITACORA-CAMBIOS.md` en la
misma sesión.

## (o) Líneas contra límites

| Archivo | Hoy | Límite | Veredicto |
|---|---:|---:|---|
| 🔴 `services/nomina_empleados_service.py` | **145** | 150 | **5 de margen. HAY QUE DIVIDIR ANTES DE ESCRIBIR** (regla 2) |
| `services/_nomina_empleados_transforms.py` | 113 | 150 | ✅ sin cambios (ya lee las columnas) |
| `schemas/importacion_nomina_empleados.py` | 96 | 200 | ✅ +2-3 líneas |
| `services/_empleados_utils.py` | 125 | 150 | ✅ (e) y (f) son docstring + 1 argumento |
| `services/_empleados_write.py` | 133 | 150 | ✅ 1 argumento |
| `services/_ownership_filter.py` | 104 | 150 | ✅ **no se toca** |
| `services/ownership.py` | 80 | 150 | ✅ no se toca |
| `services/vacaciones_service.py` | 136 | 150 | ✅ reemplazo in-line, 0 netas |
| ⚠️ `services/vacaciones_pendientes_service.py` | **139** | 150 | ✅ pero 11 de margen — ojo si además se comenta |
| `services/ausencias_service.py` | 82 | 150 | ✅ |
| `services/_vacaciones_write.py` / `_ausencias_write.py` | 82 / 110 | 150 | ✅ sin cambios (j) |
| `services/dashboard_equipo_service.py` | 72 | 150 | ✅ **0 cambios** (k) |
| `repositories/empleado_ownership_repo.py` | 83 | 100 | ✅ 0 cambios (ya es ciego a la empresa) |
| 🔴 `repositories/empleado_repo.py` | **96** | 100 | **4 de margen — el lookup batch por nombre NO va acá** |
| `repositories/_empleado_lookup_repo.py` | 51 | 100 | ✅ destino natural del lookup por nombre |
| `frontend/.../EmpresaSelector.tsx` | 68 | 150 | ✅ |

**Cortes que hay que hacer, no negociables:**
- 🔴 **`nomina_empleados_service.py` (145/150) → extraer la segunda pasada a
  `services/_nomina_superiores.py` (nuevo).** El molde ya está y es del mismo módulo:
  `_nomina_proyectos.py` (`resolver_y_asignar`) y `_nomina_cesiones.py` (`crear_si_falta`) son
  exactamente eso — un colaborador que el service invoca en **una línea** después de procesar la
  fila. `_nomina_superiores` sería el tercero, con la diferencia de que se invoca **después del
  loop**, no dentro. Ahí adentro van: el índice de claves, el resolver, el bulk de UPDATE y el
  chequeo de ciclos.
- 🔴 **El lookup de candidatos a jefe NO va en `empleado_repo.py`** (96/100, y su encabezado dice que
  `find_all` es justo lo que crece con cada filtro). Va en `_empleado_lookup_repo.py` (51) o en un
  repo propio del import.
- **Si se elige la tabla de (d): +1 repo → 55 a portar a asyncpg (regla 14).** Moldearlo sobre
  `migracionAWS/empleado_repo_NEW`.

## (p) Próximo número de migración libre: **086**

Verificado en las **dos** carpetas:
- `backend/migrations/` — llega a **085** (`085_configuracion_reglas.sql`), con hueco en 075-077.
- `migracionAWS/backend/migrations/` — **075, 076, 077** (`add_password_hash`,
  `create_refresh_tokens`, `recrear_triggers_updated_at`).

⇒ El máximo global es **085** y **no hay huecos reusables**: 075-077 están tomados por AWS. Reusar
uno de esos números colisionaría el día del merge de las dos carpetas. **Próximo libre: 086.**
(La Parte B **no necesita migración**. La necesitan (d) —tabla o columnas de pendientes— y nada más.)

## (q) ⚠️ Cómo se testea sin un solo mando ni un solo `manager_id`

### 🔴 El límite duro, primero
**En producción hay 1 (una) empresa.** El caso cruzado entre empresas **no es reproducible con datos
reales bajo ninguna circunstancia** hasta que exista la segunda. Sumado a `manager_id` 0/19 y a cero
usuarios `mandos_medios`, **toda la Parte B se verifica con fakes o no se verifica.** Eso no es un
impedimento —las 13 superficies actuales de ownership se probaron así— pero hay que decirlo antes de
declarar nada "verificado".

### Lo que SÍ se puede testear hoy, con fakes

**El fake obligatorio** (regla transversal: *"¿qué tendría que ser distinto en el fake para que este
test pueda fallar?"*) debe modelar **dos empresas Y un manager que las cruza** — que es justo lo que
ningún fake del repo modela hoy:

```
empleado X → empresa A, manager_id = M
empleado M → empresa B          (el mando)
ids_subordinados(M) → [X]       (ciego a la empresa, como el real)
```
Un fake donde X y M están en la misma empresa **no puede desmentir nada**: el test pasa igual con el
cambio y sin él.

**Los cuatro tests que hay que escribir:**

1. 🔴 **La invariante de (i)** — `resolver_filtro_empleados` con `rol="mandos_medios"` **nunca**
   devuelve `(None, False)`, sobre una tabla de entradas (con/sin área, con/sin proyecto, con/sin
   subordinados). **Es la aserción de la que depende la seguridad de todo el cambio.**
2. **Repo-level: que el `.eq("empresa_id")` REALMENTE desaparezca de la query.** Falseando el cliente
   de Supabase y capturando los `.eq()`, con el molde ya existente
   (`TestElWhereDelRepoLlevaLaEmpresa` en `test_offboarding_entrevista.py`,
   `TestElOrdenLoPoneLaQuery` en `test_historial_salarial.py`). **Un fake a nivel service no puede
   ver esto** — y "el filtro de empresa salió de la query" es exactamente la afirmación del cambio.
   Doble aserción: **ausente** para `mandos_medios`, **presente** para `admin_rrhh`.
3. **Header rancio:** el mando con `X-Empresa-Id: B` en el header ve igual a su subordinado de A.
   Es el escenario de (m) y el que prueba que el header dejó de gobernar.
4. **(c) el orden:** un CSV sintético con el jefe en la **última** fila, y todos sus subordinados
   antes. Assert: los N quedan con `manager_id` apuntándole. **Test puro, no necesita datos reales** —
   es el único de toda la tanda que reproduce el problema real del archivo tal cual es.

Más: invertir los 4 casos de `test_empleado_manager_empresa.py` (e) y un test de ciclo cruzado A→B→A
que **hoy pasaría en verde estando roto** (f).

### Lo que NO se puede probar hasta que haya datos

| Qué | Por qué | Qué lo desbloquea |
|---|---|---|
| Que `find_by_user_id` resuelva para un mando real | Requiere un `users.rol='mandos_medios'` **y** un `empleados.user_id` apuntándole. **Hoy: 0 de cada uno.** | RRHH crea 1 usuario mando vinculado a un empleado (p. ej. Libertelli, 13 subordinados) |
| La tasa real de matcheo de "Apellido Superior"+"Nombre Superior" | **5 de 6 jefes no están en el archivo.** La única evidencia real disponible son los 13 de Libertelli | Nada — es un límite del archivo, no del código. Es *el* argumento para (d) |
| Si hay homónimos que disparen `ambiguo` | Con 19 empleados la ambigüedad es estadísticamente inalcanzable | Volumen real de datos |
| 🔴 **El caso cruzado end-to-end** | **1 sola empresa en producción** | Que exista una segunda empresa con empleados |
| El comportamiento del mando en la UI | Ningún usuario con ese rol existe | El usuario de la primera fila |

**Mínimo para desbloquear:** un usuario `mandos_medios` vinculado a un empleado con subordinados.
Con eso se valida el 80% (ownership dentro de una empresa, dashboard, listados, export). El 20%
restante —el cruce— **espera a la segunda empresa, y hasta entonces vive solo en los tests.**

---

## Apéndice — inventario de archivos, para no re-diagnosticar

**Parte A:** `services/_nomina_empleados_transforms.py:111-112` (lee) ·
`schemas/importacion_nomina_empleados.py:73-96` (**pierde**) ·
`services/nomina_empleados_service.py:68,94-145` (loop) ·
`services/_evaluacion_import_transforms.py:98` (`clave_identidad`, reusar) ·
`services/evaluacion_matcheo_service.py:18` (`ResolutorIdentidad`, **no** reusar) ·
`services/_empleados_utils.py:35,104` (las dos validaciones) ·
`services/_empleados_write.py:54,98,99` (los dos call sites) ·
`repositories/_empleado_write_repo.py:34,51` (ya persiste) · `db/schema.sql:1094` (FK).

**Parte B:** `services/_ownership_filter.py:32,58,83` (**no se toca**) ·
`services/ownership.py:21,57` · `repositories/empleado_ownership_repo.py:19,42,65` (ciego a empresa) ·
`services/_empleado_scope.py:28,53` · `repositories/vacaciones_repo.py:~25` (el `.eq` que se va) ·
`services/vacaciones_service.py` · `ausencias_service.py` · `vacaciones_pendientes_service.py` ·
`services/dashboard_equipo_service.py:40` + `repositories/dashboard_equipo_repo.py` (**ya correctos**) ·
`services/_vacaciones_write.py:52` / `_ausencias_write.py:41` (**ya correctos**) ·
`utils/permisos.py:73` (`MANDOS_MEDIOS_SECCIONES`) ·
`frontend/components/layout/EmpresaSelector.tsx:21,26` + `frontend/services/api.ts:24`.

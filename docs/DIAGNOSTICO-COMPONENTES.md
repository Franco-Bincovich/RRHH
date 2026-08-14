# DIAGNÓSTICO — qué componentes tiene que tener la biblioteca

> **Fecha:** 13/8/2026 · **Alcance:** read-only sobre `frontend/`. No se editó código, no se creó
> ningún componente, no se tocó git.
>
> **Fuente:** el código, barrido con grep/AST manual. Ninguna cifra sale de `docs/` ni de memoria.
> Los conteos de importadores excluyen siempre los `*.test.*`. Las líneas se midieron con
> `grep -c ''` (equivalente a `.Count`: cuenta la última línea aunque no termine en salto).
>
> **Superficie:** 36 `page.tsx` bajo `app/(dashboard)/` + 5 fuera (`login`, `horas`,
> `evaluacion/[token]`, `cambiar-password`, `page.tsx` raíz). Las "25 pantallas" del pedido son
> las de dashboard menos las 5 rutas `[id]` de detalle y las 6 que no son listados.

---

## 0. El resumen en una línea

**No falta una biblioteca: falta UN componente.** `components/ui/` tiene 19 archivos y **no tiene
`select.tsx`** — y eso solo explica **24 de las 44 constantes de estilo locales**, repartidas en
24 archivos, **8 de ellas idénticas carácter por carácter**. El segundo agujero es del mismo
tipo: **`rounded-xl border bg-card` aparece en 34 archivos** y solo 8 pasan por un componente.

---

## 1. LOS PATRONES QUE SE REPITEN

Conteo por **archivos que lo contienen** (no por ocurrencias, salvo donde se aclara).

| Patrón | Pantallas / archivos | Versiones distintas | En qué se diferencian |
|---|---|---|---|
| **Encabezado de página** | **34 de 36** páginas de dashboard · 49 invocaciones, 24 con `action` | **1** | 🟢 `components/layout/PageHeader.tsx` (21 líneas). El patrón MÁS resuelto del repo. Las 2 excepciones: `dashboard/page.tsx` (delega en `DashboardAdmin`/`DashboardMando`, que sí lo usan) y `onboarding/templates/[id]/page.tsx` (no lo usa). |
| **Barra de filtros** | **11** con `FiltersBar` · **17** a mano · 8 sin filtros | **2 + 17** | `FiltersBar` (128 líneas, 5 tipos de control) vs. 17 pantallas con `<select>`/`type="search"` sueltos. 🔴 El caso que lo resume: **`FiltersBar` se extrajo DE `AuditFilters`, y auditoría nunca migró** — `AuditFilters.tsx:11` tiene un `FIELD_CLASS` **byte-idéntico** al de `FiltersBar.tsx:38`. |
| **Tabla con acciones por fila** | **29** con `ui/table` · **7** con `<table>` crudo | **2** | Los 7 crudos son 5 previews de import (`ImportarNominaCSVModal`, `NominaModal`, `ImportObjetivosPreview`, `ImportObjetivosResultado`, `FichaEvaluadoModal`) + `MapaVacaciones` (calendario, no listado) + `comunicacion/HistorialTabla` (que declara sus propios `TH`/`TD`). **Solo el último es deuda real.** |
| **Paginación** | **7 archivos · 4 pantallas** (auditoría, ausencias, empleados, vacaciones) | **1** | `ui/Pagination.tsx` (47 líneas). 🔴 Es **Prev/Next**, no numérica. Las otras ~21 pantallas de listado **no paginan** — coincide con los "47 listados sin paginación" de `DIAGNOSTICO-ESCALA.md`. |
| **Tarjeta de KPI / métrica** | **3** (`DashboardAdmin`, `DashboardMando`, `horasCliente/KPIsHorasPanel`) | **3** | Ninguna comparte código. Es el patrón con MENOS repetición: el dashboard es el único consumidor real, y el de horas nació aparte. **No es prioridad de biblioteca.** |
| **Modal de formulario** | **44** archivos con `DialogContent` | ~44 | Todos sobre `ui/dialog.tsx` (primitivo shadcn, 221 líneas). Lo que difiere es TODO lo de adentro: 25 tienen errores por campo (`FormErrors` / `errors.`), **cada uno con su propio tipo**. |
| **Modal de confirmación destructiva** | **9** con `ConfirmDialog` | **1** | 🟢 `ui/ConfirmDialog.tsx` (64 líneas), con `destructive` y `loading`. Resuelto. |
| **Estado vacío** | **29** archivos · 33 invocaciones | **1** | 🟢 `ui/EmptyState.tsx` (21 líneas). ⚠️ **8 de las 33 mencionan "los filtros" en genérico y NINGUNA dice qué filtro con qué valor.** |
| **Estado de carga** | **46** con `Skeleton` · **22** con `"Cargando..."` en texto · **11** con `animate-spin` | **3 lenguajes + 15 formas** | 🔴 Tres vocabularios de carga conviviendo. Y dentro de Skeleton, **15 combinaciones de clase distintas**; la más repetida es `h-10 w-full` (**10 veces**) — que es *una fila*, no la grilla de una tabla. |
| **Estado de error con reintento** | **31** `ErrorState` + **4** `ErrorCarga` | **2, y a propósito** | ✅ **El único par ya resuelto.** `ErrorCarga.tsx` documenta en su encabezado que no es un duplicado sino otro tamaño (en línea, dentro de un panel, vs. pantalla completa). ⚠️ Su propio docstring señala una copia a mano pendiente: `usuarios/EmpleadoLiderSelect.tsx:36-48`. |
| **Badge / chip de estado** | **48** importan `ui/badge` | **1 primitivo, 12 mapas** | El primitivo tiene 6 variantes (`default`, `secondary`, `destructive`, `outline`, `ghost`, `link`). 🔴 Pero hay **12 mapas `ESTADO_VARIANT`/`ESTADO_VARIANTS`/`ESTADO_BADGE`/`MOTIVO_VARIANT`/`NIVEL_VARIANT` escritos por separado**, más **3 archivos que arman el chip a mano** con `rounded-full px-2` (`organigrama/ArbolProyecto`, `organigrama/CardsProyecto`, `sucesion/AnalisisAreaModal`). |
| **Toast** | **43** archivos importan `sonner` · **51** llamadas | sin unificar | 🔴 **No hay helper compartido.** Cada `catch` escribe su propio mensaje. Un `toast.error` de red y uno de validación se ven igual y dicen cosas distintas según quién lo escribió. |

### Los dos que el pedido no listaba y son más grandes que varios de los listados

| Patrón | Archivos | Estado |
|---|---|---|
| **Panel / tarjeta de contenido** (`rounded-xl border bg-card`) | **34** | 🔴 Solo **8** pasan por un componente (`empleados/ficha/_primitives.tsx::Section`). Los otros 26 escriben la caja a mano. **Es el segundo componente que falta.** |
| **Menú de export** | **25** | 🟢 `components/features/export/ExportMenu.tsx` (70 líneas). Vive en `features/`, no en `ui/`, pero está adoptado y funciona. |

---

## 2. LO QUE YA EXISTE Y SE PUEDE REUSAR

### `components/ui/` — 19 archivos, por adopción

| Componente | Importadores | Lectura |
|---|---|---|
| `button.tsx` | **137** | Universal. Ver §3, el problema del tamaño. |
| `badge.tsx` | 48 | Adoptado; lo que falta es el mapeo estado→variante. |
| `skeleton.tsx` | 46 | Adoptado, pero conviven 2 lenguajes más de carga. |
| `label.tsx` | 43 | Adoptado… y aun así 4 archivos declaran su propio `LABEL_CLS`. |
| `dialog.tsx` | 43 | Primitivo shadcn (221 líneas). No se toca. |
| `input.tsx` | 38 | Adoptado… y aun así 6 archivos declaran su propio `INPUT_CLS`/`AREA_CLS`. |
| `ErrorState.tsx` | 31 | ✅ |
| `table.tsx` | 29 | ✅ |
| `EmptyState.tsx` | 29 | ✅ |
| `FiltersBar.tsx` | **16** | 🟡 **El caso de "existe y no se adoptó"** — ver abajo. |
| `textarea.tsx` | 13 | ✅ |
| `ConfirmDialog.tsx` | 9 | ✅ |
| `Pagination.tsx` | **7** | 🟡 Adoptado por quien puede: solo 4 listados paginan en el backend. |
| `separator.tsx` | 5 · `ErrorCarga.tsx` 4 · `avatar.tsx` 3 · `dropdown-menu.tsx` 2 · `sonner.tsx` 1 · `RolesInput.tsx` 1 | Uso puntual, sin duplicados detectados. |

Fuera de `ui/`: **`PageHeader`** (34 páginas) y **`ExportMenu`** (25) son, de hecho, parte de la
biblioteca aunque no vivan ahí.

### 🔴 El componente que existe y la mitad del front ignora: `FiltersBar`

16 importadores contra **17 pantallas que arman sus filtros a mano**. Y el motivo está escrito en
el código, no hay que suponerlo:

- **`objetivos/ObjetivosFiltros.tsx:14-16`** declara explícitamente que no se migró porque
  "eso es un rediseño del filtro, no una división". Son 4 `<select>` a mano.
- **`auditoria/AuditFilters.tsx`** es el precedente **del que se extrajo `FiltersBar`**, y se
  quedó con su copia — incluida la constante idéntica.

**La lectura:** `FiltersBar` no se ignoró por ser malo, se ignoró porque **migrar un filtro es
tocar la página, el hook y el service a la vez**, y ninguna tanda tuvo eso como objetivo. Los 11
que sí lo usan son exactamente los módulos que pasaron por el Bloque B.

### 🔴 Un archivo muerto que compite con la fuente de verdad

**`frontend/styles/design-system.ts`** — 47 líneas con `COLORS`, `TYPOGRAPHY`, `RADIUS`,
`SPACING`, `BREAKPOINTS`. **Cero importadores.** No es solo código muerto: es un **segundo
catálogo de tokens** (`primary: "#1A56DB"`, `RADIUS.md: "8px"`) que compite con `globals.css`,
que es de donde salen los tokens reales y lo que `app/contrasteTokens.test.ts` vigila. La
biblioteca nueva no puede nacer al lado de esto sin decidir cuál manda.

---

## 3. LAS CONSTANTES DE ESTILO LOCALES — **44 declaraciones en 38 archivos**

### Familia SELECT — **24 constantes, 24 archivos, 6 alturas distintas**

Todas describen el mismo control. Agrupadas por valor exacto:

| Grupo | Valor | Cuántas | Dónde |
|---|---|---|---|
| **S1** | `h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 disabled:opacity-50` | **8 IDÉNTICAS** | `ausencias/ausenciasForm.ts:23` · `capacitaciones/AsignacionModal.tsx:38` · `capacitaciones/CapacitacionModal.tsx:39` · `inventario/AsignarModal.tsx:20` · `inventario/ItemModal.tsx:26` · `objetivos/ObjetivoCamposOpcionales.tsx:36` · `shared/SeleccionEmpleado.tsx:22` · `vacaciones/vacacionesForm.ts:39` |
| **S2** | S1 **sin** `disabled:opacity-50` | **4 IDÉNTICAS** | `areas/areaForm.ts:22` · `capacitaciones/EstadoModal.tsx:20` · `inventario/DevolverModal.tsx:17` · `vacantes/vacanteForm.ts:42` |
| **S2b** | S2 **sin** `w-full` | 1 | `empleados/modal/_constants.ts:171` |
| **S3** | `min-h-[2rem]` en vez de `h-8`, sin `w-full` | **4 IDÉNTICAS** | `capacitaciones/CatalogoTab.tsx:20` · `inventario/ItemsTab.tsx:15` · `objetivos/ObjetivosFiltros.tsx:19` · `vacantes/page.tsx:24` |
| **S4** | `h-9 w-full`, resto igual | **2 IDÉNTICAS** | `horasPublico/CargaForm.tsx:13` · `vacantes/PublicacionSection.tsx:14` |
| **S5** | `min-h-9 … px-3 py-1.5 … ring` (sin `/50`) | 2, difieren **solo en `w-full`** | `evaluaciones/page.tsx:18` · `evaluaciones/importar/SubirPaso.tsx:12` |
| **S5b** | S5 con `min-w-64` | 1 | `evaluaciones/importar/EvaluadoFila.tsx:8` |
| **S6** | `min-h-11 …` | **2 IDÉNTICAS — y una vive DENTRO de `components/ui/`** | `ui/FiltersBar.tsx:38` · `auditoria/AuditFilters.tsx:11` |
| **S7** | foco distinto: `focus-visible:border-ring focus-visible:ring-3` | 2 (una `h-8`, otra `h-9`) | `assessment/CampanaModal.tsx:35` · `sucesion/_sucesion_ui.ts:36` |
| **S8** | outliers de 1 | 3 | `periodos/PeriodoForm.tsx:15` (`h-11 border-border`, **sin ningún estilo de foco**) · `costos/NominaModal.tsx:27` (`rounded-md border` pelado, `focus:` en vez de `focus-visible:`) · `reportes/EmpresaAreaSelector.tsx:8` (usa el estilo de INPUT para un `<select>`) |

**Lo que difiere sin motivo aparente: la altura.** Seis valores para el mismo control —
`h-8` (13) · `min-h-[2rem]` (4) · `h-9` (4) · `min-h-9` (3) · `min-h-11` (2) · `h-11` (1) — y no
hay ningún patrón que los explique (no es "los de modal son chicos y los de filtro grandes":
`vacantes/page.tsx` filtra con `min-h-[2rem]` y `auditoria` filtra con `min-h-11`).

**Lo que difiere con algo real:** `disabled:opacity-50` (presente en 9, ausente en 15) — separa
los selects que se deshabilitan mientras guarda el formulario de los que no. Es una **variante
legítima**, no una divergencia.

🔴 **`periodos/PeriodoForm.tsx:15` es el único sin estilo de foco visible.** No es un matiz
estético: es el único control de la familia que un usuario de teclado no puede ubicar.

### Familia INPUT / TEXTAREA — **6 constantes, y duplican `ui/input.tsx` (38 importadores)**

`flex min-h-[2.75rem] w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50`

**5 IDÉNTICAS:** `comunicacion/EnvioDestinatarios.tsx:6` · `proyectos/AsignacionModal.tsx:16` ·
`proyectos/AsignarEmpleadosModal.tsx:21` · `proyectos/HoraModal.tsx:18` ·
`proyectos/ProyectoModal.tsx:21`. La sexta (`comunicacion/EnvioLibre.tsx:12`, `AREA_CLS`) es la
misma con `min-h-28` — o sea, el textarea.

### Familia LABEL — **4 IDÉNTICAS, y duplican `ui/label.tsx` (43 importadores)**

`block text-xs font-medium text-foreground mb-1` — las cuatro en `proyectos/`:
`AsignacionModal.tsx:17` · `AsignarEmpleadosModal.tsx:22` · `HoraModal.tsx:19` ·
`ProyectoModal.tsx:22`.

> 🔑 **`proyectos/` es el módulo que más duplica: 8 de las 44 constantes son suyas, y los 4
> modales son copias entre sí.** Es el mejor candidato individual de migración.

### Familia CHECKBOX — **3 versiones y no existe `checkbox.tsx`**

`vacaciones/CamposVacacion.tsx:21` (`size-4 rounded border-input accent-primary`) ·
`evaluaciones/HistorialTable.tsx:10` (igual + `shrink-0 cursor-pointer`) · y una **tercera
inline** dentro de `ui/FiltersBar.tsx:88` (`size-4 rounded border-input`, **sin
`accent-primary`**). Las tres pintan la misma casilla y la de la barra de filtros no toma el
color de marca.

### Familia TAB — **2 IDÉNTICAS y no existe `tabs.tsx`**

`app/(dashboard)/assessment/page.tsx:46` · `sucesion/_sucesion_ui.ts:30`.

### Familia TH/TD — 2, en el único módulo que arma su tabla a mano

`comunicacion/HistorialTabla.tsx:19-20`.

### 🔴 Y la constante que NO está declarada pero es la más repetida de todas

**`min-h-11`: 139 ocurrencias en 79 archivos.** Es el parche del tamaño táctil de 44px, escrito
a mano en cada botón, porque `ui/button.tsx` define `default: h-8 · sm: h-7 · lg: h-9 · icon:
size-8` — **ninguna de las cuatro llega a 44px**. Es una decisión de accesibilidad que el
primitivo no toma y que 79 archivos toman por él, uno por uno.

---

## 4. LAS PANTALLAS, DE MÁS A MENOS PARECIDAS

Matriz por pantalla (se barrió la página **y** su carpeta `components/features/<módulo>/`).
`bar` = usa `FiltersBar` · `mano` = tiene `<select>`/`type="search"` propios.

| Pantalla | Hdr | Filtros | Tabla | Pag. | Vacío | Error | Skel | Export |
|---|---|---|---|---|---|---|---|---|
| **empleados** | sí | bar | sí | **sí** | sí | sí | sí | sí |
| **vacaciones** | sí | bar | sí | **sí** | sí | sí | sí | sí |
| **ausencias** | sí | bar | sí | **sí** | sí | sí | sí | sí |
| **auditoría** | sí | mano | sí | **sí** | sí | sí | sí | sí |
| capacitaciones | sí | bar | sí | – | sí | sí | sí | sí |
| inventario | sí | bar | sí | – | sí | sí | sí | sí |
| evaluaciones | sí | bar | sí | – | sí | sí | sí | – |
| objetivos | sí | bar | sí | – | – | – | sí | sí |
| áreas | sí | mano | sí | – | sí | sí | sí | sí |
| clientes | sí | mano | sí | – | sí | sí | sí | sí |
| vacantes | sí | mano | sí | – | sí | sí | sí | sí |
| usuarios | sí | mano | sí | – | sí | sí | sí | sí |
| costos | sí | mano | sí | – | sí | sí | sí | sí |
| assessment | sí | mano | sí | – | sí | sí | sí | – |
| períodos | sí | mano | sí | – | – | sí | sí | sí |
| empresas | sí | – | sí | – | sí | sí | sí | sí |
| equipo | sí | – | sí | – | sí | sí | sí | sí |
| comunicación | sí | bar | sí | – | – | sí | – | – |
| candidatos | sí | mano | – | – | sí | sí | sí | sí |
| onboarding | sí | mano | – | – | sí | sí | – | sí |
| onboarding/templates | sí | mano | – | – | sí | sí | – | sí |
| offboarding | sí | – | – | – | sí | – | – | sí |
| horas-por-cliente | sí | – | – | – | sí | sí | sí | sí |
| proyectos | sí | bar | – | **sí** | – | sí | – | sí |
| sucesión | sí | mano | – | – | sí | – | sí | – |
| reportes | sí | mano | sí | – | – | – | – | – |
| **dashboard** | sí | – | – | – | – | sí | – | – |
| **organigrama** | sí | – | – | – | – | – | – | – |
| **procesos** | sí | – | – | – | – | – | – | – |
| **configuración** | sí | mano | – | – | – | – | sí | – |
| *(5 rutas `[id]`)* | sí¹ | mixto | mixto | mixto | sí | sí | sí | – |

¹ salvo `onboarding/templates/[id]`, que no usa `PageHeader`.

**Balance:**
- **18 pantallas** tienen la forma completa encabezado → filtros → tabla → (vacío/error/carga).
  **Son las que más ganan.**
- **4 de esas 18 paginan.** Las otras 14 tienen la forma pero no el paginado, y eso **no lo
  arregla la biblioteca**: falta `page`/`page_size` en el backend.
- **Excepciones legítimas (6):** `dashboard` y `organigrama` (no son listados, como decías) +
  **`procesos`** (paneles de conteo), **`reportes`** (catálogo de tarjetas + historial),
  **`configuración`** (formularios de reglas) y **`offboarding`** (proceso, no listado filtrable).
- **Zona gris (3):** `proyectos` y `candidatos` tienen forma de listado pero **renderizan tarjetas,
  no tablas** (`ProyectosGrid`, `CandidatoGrupo`); `sucesión` está apagado por flag.

**Las 5 fichas `[id]`** (empleados, vacantes, proyectos, empresas, onboarding/templates) son un
patrón propio y hoy **no comparten nada**: solo `empleados/[id]` tiene primitivas
(`ficha/_primitives.tsx`), y las importan 8 archivos — 7 de ellos del propio módulo, más
`adjuntos/AdjuntosSection.tsx`.

---

## 5. QUÉ TAN LEJOS ESTÁ LO QUE HAY DE LOS CINCO PATRONES DEFINIDOS

| Patrón | ¿Reestilar o rehacer? | Por qué, medido |
|---|---|---|
| **1. FILTROS con chips, contador y "limpiar todo"** | 🟢 **Extender. Cero call sites cambian.** | `FiltersBar` recibe `campos: FiltroCampo[]`, y cada campo **ya trae `label`, `value` y `opciones`** — o sea que los chips y el contador se derivan **de lo que ya llega**, sin tocar la firma. `filtrosActivos()` (`shared/filtros.ts`) ya calcula exactamente el conjunto que el contador muestra. "Limpiar todo" pide **una prop opcional** (`onLimpiar?`). 🔴 **El trabajo real no es el componente: son las 17 pantallas con filtros a mano.** |
| **2. TABLA: paginación numérica, filas 46px, marca 3px al hover, acciones visibles** | 🟡 **Tabla: reestilar. Paginación: rehacer el cuerpo, conservar la firma.** | 46px, la marca de hover y las acciones visibles son **CSS sobre `ui/table.tsx`** (los 29 consumidores no cambian). `Pagination.tsx` sí hay que rehacerlo entero — su cuerpo **es** el par Anterior/Siguiente — pero su firma (`page, total, pageSize, onPageChange`) es la correcta y sobrevive, así que **los 7 call sites no se tocan**. 🔴 **Lo caro son las 14 pantallas con forma de listado que no paginan: eso es una tanda de BACKEND, no de biblioteca.** |
| **3. FICHA: barra de identidad + paneles independientes en 3 columnas** | 🔴 **Rehacer: no existe.** | `empleados/[id]/page.tsx:99-106` es un `space-y-4` con **7 secciones apiladas en una columna**. La grilla de 3 columnas existe pero **adentro** de cada panel (`ficha/_primitives.tsx:20`), no como layout. Ninguna de las otras 4 fichas tiene ni barra de identidad ni primitivas. 🟢 Lo reusable: **promover `Section`/`Field`/`LoadingSkeleton` a `ui/`** — hoy los usan 8 archivos y hay **26 más que reimplementan la caja**. |
| **4. MODAL: banner de resumen + mensaje por campo** | 🟡 **Nivel por campo: existe en 25. Banner: no existe en ninguno — construir.** | 25 archivos de `features/` manejan errores por campo, **cada uno con su propio tipo `FormErrors` local**. Los únicos 3 con algo parecido a un resumen (`ImportarNominaCSVModal`, `ImportObjetivosPreview`, `ImportObjetivosResultado`) son **previews de import, no validación de formulario**. `ui/dialog.tsx` es primitivo shadcn: no se toca. Hace falta un `FormErrorSummary` **más un tipo `FormErrors` compartido**, y ese contrato hay que unificarlo **antes** de escribir el banner. |
| **5. VACÍO con valores reales de filtro · CARGA con esqueleto de la grilla** | 🟢 **Vacío: extender (prop nueva, 33 usos intactos).** 🔴 **Carga: construir + migrar 33 archivos.** | `EmptyState` acepta hoy `description: string`; una prop `filtros?: {label, valor}[]` es aditiva. Hoy **8 de 33 mencionan "los filtros" y ninguna dice cuáles**. Del lado de carga hay que escribir un `TableSkeleton` (columnas × filas) y sobre todo **migrar los 22 archivos que escriben `"Cargando..."` y los 11 con `animate-spin`**, que son un lenguaje distinto, no una variante. |

**La respuesta a "3 sesiones o 12":** de los cinco, **tres se extienden sin romper un solo call
site** (1, 5-vacío, y la tabla del 2). **Dos hay que construir** (ficha en 3 columnas, banner de
validación). **Ninguno de los cinco obliga a tocar las 25 pantallas para que la biblioteca
exista** — las pantallas se tocan para *adoptarla*, que es un eje separado y es donde está el
volumen.

---

## 6. LÍNEAS DE LOS ARCHIVOS QUE HABRÍA QUE TOCAR

**29 archivos > 150** (límite de componente React). **2 no cuentan**: `dropdown-menu.tsx` (268) y
`dialog.tsx` (221) son primitivos generados de shadcn.

**Sobre el límite, y la biblioteca los toca:**

| Archivo | Líneas | Qué le toca la migración |
|---|---|---|
| `app/(dashboard)/costos/page.tsx` | **624** | panel a mano, filtros a mano, tabla |
| `app/(dashboard)/vacantes/[id]/page.tsx` | **451** | ficha, panel a mano |
| `app/(dashboard)/onboarding/page.tsx` | 396 | panel a mano, filtros a mano |
| `costos/ImportarNominaCSVModal.tsx` | 377 | `<table>` crudo, banner de validación |
| `app/(dashboard)/offboarding/page.tsx` | 311 | panel a mano |
| `costos/NominaModal.tsx` | 287 | `SELECT_CLS` outlier, `<table>` crudo |
| `app/(dashboard)/assessment/page.tsx` | 233 | `TAB_CLASS`, `ESTADO_VARIANT` |
| `app/(dashboard)/empresas/[id]/page.tsx` | 230 | ficha |
| `empresas/EmpresaModal.tsx` | 226 | banner de validación |
| `assessment/CampanaModal.tsx` | 208 | `SELECT_CLASS` (S7) |
| `empresas/EmpresaAreasTab.tsx` | 206 | panel + tabla |
| `sucesion/NineBox.tsx` | 198 | (módulo apagado) |
| `auditoria/auditLabels.ts` | 197 | catálogo de labels |
| `capacitaciones/CapacitacionModal.tsx` | 192 | `SEL` (S1) |
| `app/(dashboard)/assessment/[id]/page.tsx` | 192 | panel a mano |
| `capacitaciones/AsignacionModal.tsx` | 188 | `SEL` (S1) |
| `onboarding/OnboardingChecklist.tsx` | 186 | panel a mano |
| `vacantes/CandidatoModal.tsx` | 181 | banner de validación |
| `app/(dashboard)/vacantes/page.tsx` | 178 | `SELECT_CLASS` (S3) |
| `empleados/modal/_constants.ts` | 172 | `SELECT_CLASS` (S2b) |
| `organigrama/ArbolProyecto.tsx` | 170 | chip a mano |
| `inventario/ItemModal.tsx` | 161 | `SEL` (S1) |
| `capacitaciones/CatalogoTab.tsx` | 159 | `SELECT_CLASS` (S3) |
| `vacaciones/MapaVacaciones.tsx` | 152 | `<table>` crudo |

**Al filo (135-150) — 25 archivos más.** Los que importan porque la migración los TOCA:

- **`empleados/EmpleadoModal.tsx` 150/150** y **`candidatos/CandidatoDetailPanel.tsx` 150/150** —
  🔴 **el próximo cambio EXIGE dividir primero.**
- `usuarios/page.tsx` 149 · `objetivos/ImportarObjetivosModal.tsx` 148 ·
  `horasPublico/CargaForm.tsx` 148 (`SELECT` S4) · `empleados/page.tsx` 144 ·
  `vacantes/PublicacionSection.tsx` 143 (`SELECT_CLASS` S4) · `clientes/page.tsx` 142 ·
  `proyectos/[id]/page.tsx` 141 · `ausencias/page.tsx` 141 ·
  `sucesion/AnalisisAreaModal.tsx` 140 (chip a mano) · `usuarios/CrearUsuarioModal.tsx` 137 ·
  `objetivos/ObjetivoModal.tsx` 137 · `proyectos/HorasTab.tsx` 135.

**Hooks > 80:** `useFiltrosVacaciones.ts` **95** · `useFiltrosAsignacionesCap.ts` **89**. Los dos
son de filtros, o sea que **la extensión de `FiltersBar` los toca a los dos, y los dos ya están
sobre el límite.** Molde para cortarlos (ya identificado en `CLAUDE.md`): `useOpcionesAusencias`.

🔴 **El efecto neto sobre las líneas no es todo hacia abajo.** Sacar una constante de estilo
resta 1-3 líneas por archivo; **meter el banner de validación SUMA** a los 25 modales que hoy no
lo tienen. **Los 5 modales que ya están sobre 150 (`ImportarNominaCSVModal` 377, `NominaModal`
287, `EmpresaModal` 226, `CampanaModal` 208, `CapacitacionModal` 192) hay que dividirlos ANTES
del banner, no después** — la regla del repo es proponer la división antes de escribir.

---

## (a) COMPONENTES A CONSTRUIR, ordenados por cuántos archivos los usarían

| # | Componente | Alcance medido | Nuevo / extender |
|---|---|---|---|
| 1 | **`Select`** | **24 archivos** con constante propia (+ `FiltersBar`, que tiene la suya) | 🆕 **No existe `select.tsx`.** Es el agujero más grande y el más barato. |
| 2 | **`Panel` / `Section` + `Field`** | **34 archivos** con `rounded-xl border bg-card`; 8 ya usan la versión local | ⬆️ **Promover `empleados/ficha/_primitives.tsx` a `ui/`** |
| 3 | **Tamaño táctil en `Button`** | **79 archivos · 139 ocurrencias** de `min-h-11` | 🔧 Ajustar las variantes de `button.tsx` (borra 139 parches) |
| 4 | **`EstadoBadge`** | **12 mapas** + 3 chips a mano; 48 archivos usan `badge` | 🆕 Absorbe los mapas estado→variante+label |
| 5 | **`FiltersBar` con chips, contador y limpiar** | 11 lo usan hoy · **17 pantallas** a migrar | ⬆️ Extender, firma intacta |
| 6 | **`FormErrorSummary` + tipo `FormErrors` compartido** | **25 modales** con errores por campo · 44 con `Dialog` | 🆕 |
| 7 | **`TableSkeleton`** | **33 archivos** con carga no-skeleton (22 texto + 11 spinner) + 15 formas de skeleton | 🆕 |
| 8 | **`toast` helper** | **43 archivos · 51 llamadas** sueltas | 🆕 |
| 9 | **`Pagination` numérica** | 7 call sites (firma intacta) · habilita 14 pantallas más | 🔄 Rehacer el cuerpo |
| 10 | **`EmptyState` con valores de filtro** | 29 archivos · 33 usos; 8 lo piden hoy en genérico | ⬆️ Prop aditiva |
| 11 | **`Checkbox`** | 3 versiones (2 constantes + 1 inline en `FiltersBar`) | 🆕 |
| 12 | **`FichaLayout`** (barra de identidad + 3 columnas) | **5 rutas `[id]`** | 🆕 |
| 13 | **`Tabs`** | 2 constantes idénticas | 🆕 (baja prioridad) |

## (b) QUÉ ES VARIANTE Y QUÉ ES COMPONENTE DISTINTO

**Variantes de uno solo:**
- **Los 24 selects son UNO** con dos ejes reales: `disabled` (presente en 9, ausente en 15) y
  tamaño. Las 6 alturas **no son variantes: son divergencia** — hay que elegir una, y la
  candidata es la de `FiltersBar` (`min-h-11`), que es la única que cumple los 44px que 79
  archivos persiguen a mano.
- **`INPUT_CLS` (5) + `AREA_CLS` (1)** son `Input` y `Textarea`, **que ya existen**: no son
  componentes nuevos, son 6 archivos que no adoptaron los que hay.
- **`LABEL_CLS` (4)** es `ui/label.tsx`, misma historia.
- **Los 12 mapas de estado** son un componente con **datos** distintos, no 12 componentes.
- **`Panel` y `Section`** son el mismo: `Section` = `Panel` + título + grilla de `Field`.

**Componentes distintos de verdad:**
- **`ErrorState` vs `ErrorCarga`** — pantalla completa vs. en línea. Ya está decidido y escrito;
  **no unificar.**
- **`EmptyState` vs `ErrorState`** — "no hay datos" y "falló la consulta" son mensajes distintos
  y la confusión entre los dos es un bug documentado del repo.
- **`Pagination` vs `TableSkeleton`** — obvio, pero comparten el dato `pageSize`: el esqueleto
  tiene que dibujar tantas filas como la página va a traer, o la pantalla salta al cargar.
- **`ConfirmDialog` vs modal de formulario** — el primero está resuelto y **no debe absorber** al
  segundo: `vacantes` es el patrón canónico de borrado del repo y funciona.

## (c) SESIONES ESTIMADAS

**Construir la biblioteca: 4 sesiones.**
1. `Select` + `Checkbox` + tamaño táctil de `Button` (las tres tocan primitivos y cierran 27 de
   las 44 constantes).
2. `Panel`/`Section`/`Field` promovidos + `EstadoBadge`.
3. `FiltersBar` extendida + `EmptyState` extendida + `Pagination` numérica (los tres conservan
   firma → migración gratis).
4. `FormErrorSummary` + `FormErrors` unificado + `TableSkeleton` + helper de `toast`.

**Migrar las pantallas: 7-9 sesiones.** El volumen no son las 25 pantallas, son los **conteos por
patrón**: 24 archivos de select · 26 de panel · 79 de `min-h-11` · 17 de filtros a mano · 25
modales para el banner · 33 de carga · 12 mapas de estado. A ~4-6 archivos por sesión con test y
`tsc` en 0, más las divisiones obligatorias (5 modales sobre 150 + 2 archivos en 150/150 + 2
hooks sobre 80).

**Total: 11-13 sesiones.** 🔴 **Y hay una que NO está en ese número:** la paginación numérica
solo se puede aplicar a 4 pantallas hoy. Llevarla a las otras 14 exige `page`/`page_size` en 14
módulos del **backend** — eso es una tanda propia y es la que decide si el patrón 2 se entrega
completo o a medias.

## (d) POR CUÁLES EMPEZARÍA

1. **`clientes` (142) y `áreas` (128)** — ya tienen `PageHeader` + `EmptyState` + `ErrorState` +
   `Skeleton` + `ConfirmDialog` + `ExportMenu`, y `clientes/page.tsx` declara en su docstring que
   copió la estructura de `areas` "no su tamaño". Son las más nuevas, las más limpias, están bajo
   el límite y entre las dos tienen 1 constante de select. **Migrarlas es el molde y no arriesga
   nada.**
2. **`proyectos/`** — 8 de las 44 constantes son de ese módulo y **sus 4 modales son copias entre
   sí** (`INPUT_CLS` + `LABEL_CLS` idénticos ×4). Es el mayor retorno por archivo tocado del repo.
3. **`capacitaciones` + `inventario`** — las dos ya están en `FiltersBar`, y entre las dos tienen
   **6 constantes de select** de dos grupos distintos (S1 y S3). Cierran dos grupos de una.
4. **`auditoría`** — cerrar el caso que más habla: migrar `AuditFilters` a la `FiltersBar` que se
   extrajo de él, y borrar el `FIELD_CLASS` duplicado. Además es una de las 4 que ya paginan, así
   que es donde la paginación numérica se puede **probar de verdad hoy**.
5. **`empleados` / `vacaciones` / `ausencias`** — las otras 3 que paginan. Van juntas y van
   después, porque son las de más tráfico y las que más caro pagan un error visual.

**Lo que dejaría para el final:** `costos/page.tsx` (624) y `vacantes/[id]/page.tsx` (451) — hay
que dividirlas antes de tocarlas, y esa división es una sesión propia cada una.

## (e) LO QUE NO PUDE DETERMINAR

1. **Si las filas de 46px y la marca de 3px al hover salen solo de `ui/table.tsx`.** Los 29
   consumidores escriben su propio `<TableRow>`/`<TableCell>`; no leí los 29. Si alguno fija
   altura o padding propio, la migración de ese patrón deja de ser "cambiar clases en un archivo".
2. **Si subir el tamaño base de `Button` rompe el layout.** 139 sitios usan `min-h-11` **encima**
   de la variante; si la base pasa a 44px, los sitios con `size="sm"`/`icon` cambian de tamaño y
   eso solo se ve corriendo la app. `tsc` no lo detecta y `vitest` corre sin jsdom.
3. **Los tokens exactos de Claude Design** (colores, espaciados, radios). En el repo solo está
   `frontend/styles/design-system.ts`, que tiene **0 importadores** y valores que **compiten con
   `globals.css`**. Antes de escribir el primer componente hay que decidir cuál manda — y
   `app/contrasteTokens.test.ts` ya vigila `globals.css`, no ese archivo.
4. **Cuántos controles de filtro hay realmente en las 17 pantallas "a mano".** Conté *archivos*
   con `<select>`/`type="search"`, no controles. El esfuerzo de migración del patrón 1 depende de
   ese número, no del de pantallas.
5. **Si `procesos`, `reportes` y `configuración` quieren la forma de listado.** Los marqué como
   excepciones legítimas por lo que el código hace hoy; que deban seguir siéndolo es una decisión
   de producto, no algo que se lea del código.

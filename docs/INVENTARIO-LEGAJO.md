# INVENTARIO DEL LEGAJO — todos los campos que existen hoy

> **Fecha:** 14/8/2026 · **Alcance:** read-only. No se editó código, no se creó ninguna
> migración, no se tocó git.
>
> **Fuentes, en este orden:** (1) el **catálogo vivo** de producción (Supabase
> `grmdiwxcvcjorlohpwji`, "HR Karstec") vía MCP — cada conteo sale de un `SELECT` corrido hoy;
> (2) el **código** del repo, con `archivo:línea`. `docs/` **no** se usó como fuente.
>
> **Padrón: 31 empleados, 2 empresas, los 31 en `estado='activo'`.**

---

## 1. TODAS LAS COLUMNAS DE `empleados` — **58**

`ordinal_position` llega a 60 con dos huecos (**14** y **44**): son `modalidad_contratacion` y
`nivel`, dropeadas por la migración 084. No hay ninguna columna más.

| # | Columna | Tipo | Null | Default | CHECK / UNIQUE / FK | Cargados /31 | Valores |
|---|---|---|---|---|---|---|---|
| 1 | `id` | uuid | NO | `gen_random_uuid()` | PK · UNIQUE `(id, empresa_id)` | 31 | |
| 2 | `user_id` | uuid | SÍ | | FK `users` ON DELETE SET NULL | **1** | |
| 3 | `legajo` | varchar(20) | SÍ | | UNIQUE `(legajo, empresa_id)` | **0** | |
| 4 | `nombre` | varchar(100) | **NO** | | | 31 | |
| 5 | `apellido` | varchar(100) | **NO** | | | 31 | |
| 6 | `email_corporativo` | varchar(255) | SÍ | | UNIQUE global | 31 | |
| 7 | `email_personal` | varchar(255) | SÍ | | | **0** | |
| 8 | `telefono` | varchar(30) | SÍ | | | **0** | |
| 9 | `fecha_nacimiento` | date | SÍ | | | 31 | |
| 10 | `fecha_ingreso` | date | **NO** | | | 31 | |
| 11 | `fecha_egreso` | date | SÍ | | | **0** | |
| 12 | `area_id` | uuid | SÍ | | FK `areas` ON DELETE RESTRICT | 31 | 12 áreas |
| 13 | `cargo` | varchar(100) | SÍ | | | **0** | 🔴 DEPRECADO |
| 15 | `modalidad_trabajo` | varchar(20) | SÍ | | CHECK `presencial\|remoto\|hibrido` | 31 | presencial 30 · hibrido 1 |
| 16 | `tipo_contrato` | text | SÍ | | *(texto libre, mig 065)* | 31 | `RELACION DE DEPENDENCIA` 30 · `HONORARIOS` 1 |
| 17 | `estado` | varchar(20) | **NO** | `'activo'` | CHECK `activo\|baja\|licencia\|suspendido` | 31 | **activo 31** |
| 18 | `manager_id` | uuid | SÍ | | FK self ON DELETE SET NULL | **11** | |
| 19 | `foto_url` | text | SÍ | | | **0** | |
| 20 | `created_at` | timestamptz | **NO** | `now()` | | 31 | |
| 21 | `updated_at` | timestamptz | **NO** | `now()` | trigger `set_updated_at` | 31 | |
| 22 | `cuil` | varchar(20) | SÍ | | | 31 | |
| 23 | `potencial` | varchar(10) | **NO** | `'medio'` | CHECK `alto\|medio\|bajo` | 31 | **medio 31** (todos el default) |
| 24 | `desempeno` | varchar(10) | **NO** | `'medio'` | CHECK `alto\|medio\|bajo` | 31 | **medio 31** (todos el default) |
| 25 | `rol` | varchar(100) | SÍ | | | **0** | 🔴 DEPRECADO |
| 26 | `empresa_id` | uuid | **NO** | | FK `empresas` ON DELETE RESTRICT | 31 | 19 / 12 |
| 27 | `dni` | varchar(20) | SÍ | | UNIQUE `(empresa_id, dni)` | 31 | |
| 28 | `dias_vacaciones_asignados` | integer | SÍ | | | **1** | NULL = regla por antigüedad |
| 29 | `roles` | text[] | **NO** | | CHECK `array_length(roles,1) >= 1` | 31 | 10 distintos — ver abajo |
| 30 | `tipo_documento` | text | SÍ | | | **0** | |
| 31 | `sexo` | text | SÍ | | *(texto libre)* | 31 | `Femenino` 16 · `Masculino` 15 |
| 32 | `telefono_alternativo` | text | SÍ | | | **0** | |
| 33 | `domicilio` | text | SÍ | | | **0** | |
| 34 | `estudios` | text | SÍ | | | **0** | |
| 35 | `ubicacion` | text | SÍ | | | **26** | CÓRDOBA CAPITAL 11 · BUENOS AIRES 7 · LABOULAYE 3 · BELL VILLE 2 · INDEFINIDO 2 · `Rivera Indarte 734` 1 |
| 36 | `turno` | text | SÍ | | | 31 | `8 A 17 HS.` 28 · `7.30 A 16.30 HS.` 1 · `8 A 14 HS.` 1 · `10 A 18 HS.` 1 |
| 37 | `horas_contrato` | integer | SÍ | | | **0** | |
| 38 | `organismo` | text | SÍ | | | **0** | 🔴 ver §4 |
| 39 | `gerencia` | text | SÍ | | | 31 | RECUPERO DEL GASTO HOSPITALARIO 13 · CALIDAD DE DATOS 11 · BERAZATEGUI 3 · ADMINISTRACION 1 · OTROS PROYECTOS 1 · CAPITAL HUMANO 1 · TECNICA Y TRIBUTARIA 1 |
| 40 | `sector` | text | SÍ | | | **0** | 🔴 ver §4 |
| 41 | `seniority` | text | SÍ | | | **3** | SENIOR 1 · TRAINEE 1 · EXPERT 1 |
| 42 | `perfil` | text | SÍ | | | **0** | |
| 43 | `categoria` | text | SÍ | | | **2** | `"3"` ×2 |
| 45 | `referido` | text | SÍ | | | **0** | |
| 46 | `es_lider` | boolean | SÍ | `false` | | 31 | false 28 · **true 3** |
| 47 | `fecha_ingreso_reconocida` | date | SÍ | | | **10** | |
| 48 | `equipo` | text | SÍ | | | **0** | |
| 49 | `co_sourcing` | boolean | SÍ | | | **0** | |
| 50 | `product_owner` | boolean | SÍ | | | 31 | |
| 51 | `liderazgo` | text | SÍ | | | 31 | `NO` 28 · `SI` 3 |
| 52 | `motivo_baja` | text | SÍ | | | **0** | |
| 53 | `domicilio_calle` | text | SÍ | | | **0** | |
| 54 | `domicilio_numero` | text | SÍ | | | **0** | |
| 55 | `domicilio_piso_depto` | text | SÍ | | | **0** | |
| 56 | `domicilio_localidad` | text | SÍ | | | **0** | |
| 57 | `domicilio_provincia` | text | SÍ | | *(lista cerrada en Pydantic, no en DB)* | **0** | |
| 58 | `domicilio_cp` | text | SÍ | | | **0** | |
| 59 | `fecha_ingreso_prevista` | date | SÍ | | | **0** | 🔴 sin una sola línea de código |
| 60 | `fecha_baja_prevista` | date | SÍ | | | **0** | 🔴 sin una sola línea de código |

**Valores de `roles` (10 distintos, 1 rol por persona):** FACTURISTA DE PRESTACIONES MEDICAS 9 ·
ANALISTA FUNCIONAL 7 · ANALISTA 3 · ADMINISTRATIVO 3 · OPERADOR DE GESTION 2 · LIDER DE EQUIPO 2 ·
DESARROLLADOR 2 · ANALISTA DE GESTION 1 · **FACTURISTA DE PRESTACIONES MÉDICAS 1** · LIDER DE
PROCESO 1.
> 🔴 **"MEDICAS" y "MÉDICAS" son dos roles distintos para el sistema** (9 + 1). El array es texto
> libre sin catálogo: la tilde parte el grupo en dos y ningún agrupamiento por rol lo va a juntar.

**FKs salientes (4):** `area_id → areas` (RESTRICT) · `empresa_id → empresas` (RESTRICT) ·
`manager_id → empleados` (SET NULL) · `user_id → users` (SET NULL).
**Triggers:** `trg_empleados_updated_at` (`set_updated_at`) y `trg_emp_empleados`
(`fn_misma_empresa('area_id','areas','manager_id','empleados')`).

### 🔴 Tres cosas del catálogo que no se ven en la tabla de arriba

1. **`potencial` y `desempeno` están al 100 % en su default y NO son cargables por ninguna vía
   viva.** El único escritor del repo es
   `repositories/assessment_resultados_repo.py:89` — y **assessment está apagado por
   `ASSESSMENT_ENABLED=false`** (router desmontado). No están en `EmpleadoUpdate`
   (`schemas/empleado.py:107-151`), así que la pantalla tampoco. Son los dos ejes del 9-box.
2. **`co_sourcing` 0/31 contra `product_owner` 31/31**, y los dos salen del **mismo** parser
   (`parse_bool`) sobre columnas del **mismo** archivo. La columna `Co-sourcing` del CSV real
   llega vacía o con un literal de `VACIOS`; `Product Owner` llega con SI/NO.
3. **`fecha_ingreso_prevista`, `fecha_baja_prevista` y la tabla `recategorizaciones` existen y no
   las nombra ni una línea de código.** Solo aparecen en `migrations/113`, `migrations/116`,
   `db/schema.sql` y `db/funciones_y_triggers.sql`. Son DDL adelantado (el lote 113/116 lo
   declara así), no features a medio hacer.

---

## 2. LO QUE SE VE EN LA FICHA — `/empleados/[id]`

La ficha es un `space-y-4` de **7 secciones apiladas**
(`app/(dashboard)/empleados/[id]/page.tsx:99-106`), en este orden:

1. Datos del empleado · 2. Documentos · 3. Inventario asignado · 4. Historial salarial ·
5. Historial de cambios · 6. Vacaciones · 7. Cesiones.

Arriba de todo, fuera de las secciones: **botón Volver**, el `PageHeader` con el nombre, y los
botones **Dar de baja** (`:83`) y **Editar** (`:90`), los dos solo con permiso de escritura.

### Panel «Información personal» — `DatosEmpleadoSection.tsx:26-42`

| # | Etiqueta en pantalla | Columna | Nota |
|---|---|---|---|
| 1 | Tipo de documento | `tipo_documento` | |
| 2 | Documento | `dni` | |
| 3 | CUIT/CUIL | `cuil` | |
| 4 | N° de legajo | `legajo` | |
| 5 | Sexo | `sexo` | |
| 6 | Fecha de nacimiento | `fecha_nacimiento` | |
| 7 | Teléfono | `telefono` | |
| 8 | Teléfono alternativo | `telefono_alternativo` | |
| 9 | Email | `email_corporativo` | |
| 10 | Email alternativo | `email_personal` | |
| 11 | Domicilio | 🔴 **DERIVADO** de las 6 columnas `domicilio_*` | `_domicilio.ts::domicilioLegible` — "Calle Nº, Piso, Localidad, CP, Provincia", descartando las partes vacías |
| 12 | Domicilio (sin desglosar) | `domicilio` | 🔴 **CONDICIONAL**: solo si el crudo tiene valor **y** los 6 desglosados están vacíos (`_domicilio.ts::mostrarCrudo`) |
| 13 | Estudios | `estudios` | |

### Panel «Información laboral» — `DatosEmpleadoSection.tsx:44-70`

| # | Etiqueta | Origen | 🔴 |
|---|---|---|---|
| 1 | Empresa | `empresa_nombre` | **JOIN a `empresas`** |
| 2 | Área | `area_nombre` | **JOIN a `areas`** |
| 3 | Superior inmediato | `manager_nombre` | **JOIN self a `empleados`** ("Apellido, Nombre") |
| 4 | Rol | 🔴 **DERIVADO**: `roles.join(", ")` **con fallback a `cargo`** (`:21`) | El fallback sobrevive hasta la limpieza S6 |
| 5 | Ubicación | `ubicacion` | |
| 6 | Turno | `turno` | |
| 7 | Horas de contrato | `horas_contrato` | derivado menor: `int → string`, null → "—" (`:20`) |
| 8 | Organismo | `organismo` | **vacío en los 31** |
| 9 | Gerencia | `gerencia` | |
| 10 | Sector | `sector` | **vacío en los 31** |
| 11 | Seniority | `seniority` | |
| 12 | Perfil | `perfil` | **vacío en los 31** |
| 13 | Categoría | `categoria` | |
| 14 | Fecha de ingreso | `fecha_ingreso` | |
| 15 | Modalidad de trabajo | `modalidad_trabajo` | |
| 16 | Tipo de contrato | `tipo_contrato` | |
| 17 | Líder | 🔴 **DERIVADO**: `es_lider ? "Sí" : "No"` | La columna es *nullable* y el ternario colapsa `null` a **"No"** |
| 18 | Estado | `estado`, como `Badge` | mapa local `ESTADO_VARIANTS` (`:6-10`) — **cubre `activo`/`baja`/`licencia`, NO `suspendido`**, que cae al fallback `outline` |

### Lo que el backend devuelve y la ficha NO muestra

`EmpleadoResponse` (`schemas/empleado_out.py`) tiene **47 campos**: 44 columnas + 3 de join. De
esos, la ficha no pinta: `id`, `empresa_id`, `area_id`, `manager_id`, `rol`, `created_at`, las 6
`domicilio_*` por separado (van compuestas), y —las dos que importan—
**`dias_vacaciones_asignados`** y **`referido`**, que **se cargan en el modal y después no se ven
en ningún lado de la ficha**.

### 🔴 Las 14 columnas de `empleados` que ni siquiera salen del backend

No están en `EmpleadoResponse`, así que no hay pantalla que pueda mostrarlas sin tocar el schema:

> `user_id` · `fecha_egreso` · `potencial` · `desempeno` · `foto_url` · `updated_at` ·
> `equipo` · `co_sourcing` · `product_owner` · `liderazgo` · `motivo_baja` ·
> `fecha_ingreso_reconocida` · `fecha_ingreso_prevista` · `fecha_baja_prevista`

**De esas, 5 tienen dato cargado hoy:** `product_owner` (31), `liderazgo` (31),
`fecha_ingreso_reconocida` (10), `potencial` (31) y `desempeno` (31). **El import las escribe y
la aplicación no las lee.**

> ⚠️ Esto es además el límite conocido del diff de auditoría: `_audit_payloads_rrhh.py:60-67`
> arma el diff sobre `EmpleadoResponse`, no sobre la tabla, así que **una edición SQL de
> cualquiera de esas 14 no queda auditada**.

---

## 3. LO QUE SE PUEDE CARGAR — modal de alta y de edición

**Es el MISMO componente** (`components/features/empleados/EmpleadoModal.tsx`, 150/150 líneas),
con un solo flag `isEdit`. `FormData` (`modal/_constants.ts:3-41`) declara **39 claves**.

### La única diferencia real entre alta y edición

| | Alta | Edición |
|---|---|---|
| **Empresa** | 🔴 **select obligatorio**, visible (`OrganizacionSelects.tsx:35-60`) | **no se muestra** — un empleado no se muda de sociedad |
| **Área** | select **deshabilitado hasta elegir empresa**, opciones filtradas por esa empresa (`useEmpleadoFormData.ts:52-70`) | select con **todas** las áreas |
| **Superior** | activos de la empresa elegida | activos de la empresa del empleado, **excluyéndose a sí mismo** (`OrganizacionSelects.tsx:32`) |

Todo lo demás es idéntico.

### Obligatorios (5)

`nombre` · `apellido` · `email_corporativo` · `area_id` · `fecha_ingreso` — más `empresa_id`
solo en el alta. (`_constants.ts:113-142`, marca `required: true`.)

### Desplegables y de dónde salen las opciones

| Campo | Control | Opciones |
|---|---|---|
| `empresa_id` | select | `GET /api/empresas` filtrado por `activa` (`useEmpleadoFormData.ts:38`) |
| `area_id` | select | `GET /api/areas` — por empresa en alta, todas en edición |
| `manager_id` | select | `GET /api/empleados/seleccionables?empresa_id=…` (activos) |
| `modalidad_trabajo` | select | 🔴 **hardcodeado**: `presencial` · `remoto` · `hibrido` (`DatosLaboralesFields.tsx:81-83`) |
| `tipo_contrato` | `<datalist>` (texto libre con sugerencias) | 🔴 **hardcodeado**: `Relación de dependencia` · `Plazo fijo` · `Contratado` · `Pasantía` (`:100-103`) |
| `sexo` | select | 🔴 **hardcodeado `"F"` / `"M"`** (`DatosPersonalesFields.tsx:38-40`) |
| `domicilio_provincia` | select | `GET /api/empleados/catalogos/provincias` (`schemas/_provincias.py`) |
| `es_lider` | checkbox | — |
| `roles` | `RolesInput` multivalor | pool `GET /api/empleados/roles-conocidos` |
| `tipo_documento`, `ubicacion`, `organismo`, `gerencia`, `sector`, `seniority`, `perfil`, `categoria` | **autocompletado de texto libre** | `GET /api/empleados/valores-conocidos?campo=…` — los valores YA usados en `empleados`, sin filtro de empresa (`empleado_catalogos_service.py:15-18`) |

Todo lo demás es **texto libre** (o `date`/`number`).

### 🔴 Dos incompatibilidades de vocabulario entre el modal y lo que hay cargado

1. **`sexo`: el modal escribe `"F"`/`"M"`; los 31 registros dicen `"Femenino"`/`"Masculino"`.**
   El import normaliza con `parse_sexo` (`_nomina_parsers.py:79-86`, `'M'→'Masculino'`), el modal
   no. **Editar cualquier empleado por la pantalla le cambia el valor de forma**, y como la
   columna es texto libre sin CHECK, nada lo impide: quedan cuatro valores para dos sexos.
2. **`tipo_contrato`: el modal sugiere `"Relación de dependencia"`; los 31 dicen
   `"RELACION DE DEPENDENCIA"`** (mayúsculas, sin tilde — como viene del CSV). Es un `<datalist>`,
   o sea que se puede escribir cualquier cosa; la sugerencia no coincide con el dato real.
   Mismo efecto: una edición manual parte el grupo.

### 🔴 Columnas que existen y NINGUNA pantalla puede cargar — **20**

| Columna | Quién la escribe hoy |
|---|---|
| `id`, `created_at`, `updated_at` | la base |
| `user_id` | vínculo con `users`; sin ABM |
| `estado` | `_empleado_write_repo.py:36` fuerza `'activo'` en el alta · `baja_logica` (`:70`) · `dar_de_baja` (`:76`) |
| `fecha_egreso` | **solo** `dar_de_baja` (`:93`), junto con `estado='baja'` en el mismo UPDATE |
| `motivo_baja` | **solo el import** (`_base_nomina`) |
| `potencial`, `desempeno` | **solo assessment, que está apagado** |
| `foto_url` | nadie |
| `cargo`, `rol` | nadie (deprecados) |
| `equipo`, `co_sourcing`, `product_owner`, `liderazgo`, `fecha_ingreso_reconocida` | **solo el import** |
| `domicilio` (texto libre) | 🔴 **está en `FormData` pero ningún control lo renderiza** — `DOMICILIO_FIELDS` (`_constants.ts:152-158`) lo excluye a propósito: "dejó de editarse, se muestra como referencia" |
| `fecha_ingreso_prevista`, `fecha_baja_prevista` | nadie |

> **En síntesis: 6 columnas de `empleados` solo pueden entrar por el import de nómina** —
> `equipo`, `co_sourcing`, `product_owner`, `liderazgo`, `fecha_ingreso_reconocida` y
> `motivo_baja`.

---

## 4. LO QUE ESCRIBE EL IMPORT DE NÓMINA

CSV de **27 columnas requeridas** + 1 opcional, `;`, latin-1
(`services/_nomina_empleados_transforms.py:14-22`). El mapeo se arma en `parsear_fila`
(`:79-129`) y se convierte en payload en `schemas/importacion_nomina_empleados.py:115-135`.

### Excel → `empleados` (22 columnas escritas)

| Columna del Excel | Columna de `empleados` | Transformación | archivo:línea |
|---|---|---|---|
| `Apellido` | `apellido` | crudo | `transforms:106` |
| `Nombre` | `nombre` | crudo | `transforms:107` |
| `Legajo` *(opcional)* | `legajo` | `limpiar` | `transforms:110` |
| `DNI` | `dni` | `limpiar` | `transforms:111` |
| `CUIT` | `cuil` | `limpiar` | `transforms:112` |
| `Sexo` | `sexo` | `parse_sexo`: M→Masculino, F→Femenino | `transforms:113` · `parsers:79` |
| `Email` | `email_corporativo` | `.lower()`, y **null si no valida** | `transforms:114` · `nomina_empleados_service:118` |
| `Fecha Nacimiento` | `fecha_nacimiento` | `parse_fecha` `%d/%m/%Y` | `transforms:115` |
| `Fecha Ingreso` | `fecha_ingreso` | `parse_fecha` | `transforms:116` |
| `Fecha Ingreso Reconocida` | `fecha_ingreso_reconocida` | ISO string | `transforms:117` |
| `Gerencia` | `gerencia` | `limpiar` | `transforms:118` |
| `Equipo` | `equipo` | `limpiar` | `transforms:119` |
| `Rol` | `roles` | `[rol]` — array de **un** elemento | `transforms:120` |
| `Seniority` | `seniority` | `limpiar` | `transforms:121` |
| `Categoria` | `categoria` | `limpiar` | `transforms:122` |
| `Modalidad Contratacion` | **`tipo_contrato`** | crudo, texto libre | `transforms:123` |
| `Co-sourcing` | `co_sourcing` | `parse_bool` SI/NO → True/False/None | `transforms:124` |
| `Liderazgo` | `liderazgo` **y** `es_lider` | 🔴 **se lee DOS veces**: texto crudo + booleano derivado. `None` no escribe ninguno de los dos | `transforms:100-104, 125-126` |
| `Ubicación Física` | `ubicacion` | `limpiar` | `transforms:127` |
| `Carga Horaria` | **`turno`** | `limpiar` | `transforms:128` |
| `Product Owner` | `product_owner` | `parse_bool` | `transforms:129` |
| `Motivo Baja` | `motivo_baja` | `limpiar` | `transforms:131` |

### Columnas del Excel que NO van a `empleados` pero se usan

| Excel | Para qué | archivo:línea |
|---|---|---|
| `Organismo` | 🔴 resuelve/crea la **EMPRESA** (`_empresa`) | `transforms:137` · `nomina_empleados_service:114` |
| `Sector` | 🔴 resuelve/crea el **ÁREA** (`_area`) | `transforms:138` |
| `Apellido Superior` + `Nombre Superior` | `manager_id`, en **segunda pasada** tras el loop | `transforms:139-140` · `service:147` |
| `Fecha Baja` | dispara `dar_de_baja` → escribe `estado='baja'` **y** `fecha_egreso` | `transforms:130` · `service:141-142` |
| `Gerencia` *(segundo uso)* | crea/reusa un **proyecto** y asigna al empleado | `service:145-147` |
| `Fecha Ingreso Reconocida` *(segundo uso)* | crea una **cesión** idempotente | `service:149` |

### 🔴 LO QUE EL IMPORT LEE Y DESCARTA

| Excel | Qué pasa |
|---|---|
| **`Edad`** | 🔴 **Está en `HEADERS` (`transforms:16`), o sea que el archivo se RECHAZA ENTERO si falta — y `parsear_fila` NUNCA la lee.** Es la única columna que el import exige y tira. Y no se recalcula en ningún lado: no hay antigüedad ni edad derivadas (ver §7). |

Es la única. **Pero el descarte más caro no es una columna ignorada, son dos que se leen para otra
cosa:**

> 🔴 **`Organismo` y `Sector` del Excel NUNCA llegan a `empleados.organismo` ni
> `empleados.sector`.** Se consumen como `_empresa` y `_area` para resolver las FKs, y
> `_base_nomina` (`importacion_nomina_empleados.py:115-135`) no los incluye. **Por eso las dos
> columnas están en 0/31 teniendo el dato en el archivo, y por eso la ficha muestra "Organismo —"
> y "Sector —" para los 31.** El dato existe: vive en `empresas.nombre` y `areas.nombre`, con
> otro nombre y sin poder filtrarse como campo del legajo.

### Columnas de `empleados` que el import NUNCA toca — **26**

`id` · `user_id` · `email_personal` · `telefono` · `telefono_alternativo` · `tipo_documento` ·
`area_id`¹ · `cargo` · `rol` · `modalidad_trabajo`² · `manager_id`³ · `foto_url` ·
`created_at` · `updated_at` · `potencial` · `desempeno` · `dias_vacaciones_asignados` ·
`domicilio` · las **6** `domicilio_*` · `estudios` · `horas_contrato` · `organismo` · `perfil` ·
`sector` · `referido` · `fecha_ingreso_prevista` · `fecha_baja_prevista`.

¹ lo resuelve el service desde `Sector`, no el mapeo de campos ·
² el alta toma el default `"presencial"` de `EmpleadoCreate` (`schemas/empleado.py:97`) — **de ahí
salen los 30 "presencial"**, no del archivo ·
³ segunda pasada, no `_base_nomina`.

---

## 5. LO QUE CUELGA DEL LEGAJO SIN ESTAR EN `empleados`

**21 tablas referencian `empleados`** (FK, catálogo vivo). Siete se ven hoy en la ficha:

| Sección de la ficha | Tabla | Qué muestra HOY | Filas hoy | Qué más tiene la tabla y no se muestra |
|---|---|---|---|---|
| **Documentos** | `adjuntos` (polimórfica) | `AdjuntosSection.tsx` — título "Documentos" | **1** en todo el sistema | — |
| **Inventario asignado** | `inventario_asignaciones` | Equipo · N° de serie · Asignado el · Estado (`InventarioSection.tsx:67-70`) | **0** | fecha y estado de devolución, observaciones |
| **Historial salarial** | `costos_nomina` | Mes/año · **Bruto** · **Neto** (`HistorialSalarialSection.tsx:92-105`). 🔴 Se oculta entero sin permiso `COSTOS` (`:73`) | **0** | aportes, contribuciones, el desglose completo del recibo |
| **Historial de cambios** | `auditoria` | `AuditTable` paginado + modal de detalle (`HistorialCambiosSection.tsx:55-61`) | **95** eventos `update_empleado` | — (limitado a lo que el diff captura: ver §2) |
| **Vacaciones** | `solicitudes_vacaciones` | Desde · Hasta · Días · Estado (`VacacionesSection.tsx:67-70`) | **0** | período, saldo, cancelada, adjunto |
| **Cesiones** | `cesiones` | Empresa de cesión · fecha, como lista (`CesionesSection.tsx:88-91`) | **10** | — |
| *(sin sección)* | `proyecto_asignaciones` | 🔴 **nada** | **31** — una por empleado | proyecto, rol, fechas desde/hasta, valor hora |

**Las 14 que NO tienen sección en la ficha:**

| Tabla | Filas | Se ve en otro lado |
|---|---|---|
| `proyecto_asignaciones` | **31** | sí, desde el proyecto — 🔴 **el dato más cargado que cuelga del legajo, y desde la persona no se ve** |
| `evaluacion_evaluados` | **10** | `/evaluaciones` |
| `mail_enviado` | 3 | `/comunicacion` |
| `onboarding_instancias` | 1 | `/onboarding` |
| `horas_proyecto` | 1 | `/horas-por-cliente` |
| `empleado_superior_pendiente` | 1 | cola del import |
| `solicitudes_ausencia` | 0 | `/ausencias` |
| `vacaciones_pendientes` | 0 | `/vacaciones` |
| `empleado_capacitacion` | 0 | `/capacitaciones` |
| `offboarding_instancias` | 0 | `/offboarding` |
| `planes_carrera` | 0 | sucesión (apagado) |
| `evaluacion_equivalencias` | 0 | — |
| `recategorizaciones` | **0** | 🔴 **ningún lado: la tabla existe y no hay código** |
| `assessment_links`, `assessment_resultados`, `sesiones_horas`, `intentos_identificacion`, `areas.responsable_id`, `planes_carrera.responsable_id` | — | módulos apagados / internas |

---

## 6. LOS EXPORTS

`services/_empleados_export.py::construir_filas_export` — **25 columnas**:

Legajo · Nombre · Apellido · DNI · CUIL · Email corporativo · Teléfono · Empresa · Área ·
**Rol principal** (`roles[0]`) · **Roles** (`join(", ")`) · Seniority · Gerencia · Sector ·
Categoría · Manager · Tipo de contrato · Modalidad · Horas de contrato · Fecha de ingreso ·
Localidad · Provincia · Estado · **Es líder** (`"Sí"/"No"`) · **Días de vacaciones**.

### Export ↔ ficha: no coinciden en las dos direcciones

**En la ficha y NO en el export (10):** Tipo de documento · CUIT/CUIL¹ · Sexo · Fecha de
nacimiento · Teléfono alternativo · Email alternativo · **Domicilio completo** (el export solo
lleva Localidad y Provincia, "las dos agregables", por decisión escrita en `_empleados_export.py:44`)
· Estudios · Ubicación · Turno · Organismo · Perfil.

**En el export y NO en la ficha (2):** 🔴 **Días de vacaciones** (`dias_vacaciones_asignados`) y el
desglose **Rol principal / Roles** — la ficha los junta en un solo campo "Rol".

¹ el export sí lleva `CUIL`; la ficha lo llama "CUIT/CUIL". Es el mismo campo.

**Ninguno de los dos** muestra: `potencial`, `desempeno`, `liderazgo`, `product_owner`,
`co_sourcing`, `equipo`, `fecha_ingreso_reconocida`, `referido`, `motivo_baja`, `fecha_egreso`.

---

## 7. DERIVADOS Y CALCULADOS

| Qué | Fórmula | Desde qué campo | Dónde |
|---|---|---|---|
| **Domicilio legible** | `[calle+" "+numero, piso_depto, localidad, cp, provincia]` filtrando vacíos, unido por `", "`; `null` si no hay ninguno | las 6 `domicilio_*` | `_domicilio.ts:12-22` |
| **¿Mostrar el domicilio crudo?** | `domicilio` con valor **Y** `domicilioLegible() === null` | `domicilio` + las 6 | `_domicilio.ts:29-31` |
| **Rol** | `roles.join(", ") \|\| cargo` | `roles`, `cargo` | `DatosEmpleadoSection.tsx:21` |
| **Líder** | `es_lider ? "Sí" : "No"` — `null` → "No" | `es_lider` | `DatosEmpleadoSection.tsx:65` |
| **Cumpleaños del mes** | mes de `fecha_nacimiento` == mes actual, solo `estado='activo'` | `fecha_nacimiento` | `_dashboard_kpis.py:63-77` |
| **Aniversarios del mes** | mes de `fecha_ingreso` == mes actual, solo activos | `fecha_ingreso` | `_dashboard_kpis.py:63-77` |
| **Bajas del mes (KPI)** | `estado='baja'` con **`updated_at`** en el mes | 🔴 `updated_at`, **no** `fecha_egreso` | `dashboard_service.py:75-82` |

### 🔴 La fecha que usa el cálculo de vacaciones — y la que NO existe

**Antigüedad para el cupo de vacaciones** (`services/_vacaciones_cupos.py`):

1. **`fecha_antiguedad(fecha_ingreso, fecha_ingreso_reconocida) = min(las dos)`** (`:24-50`).
   Es `min` y no "la reconocida si está": **reconocer antigüedad SUMA, nunca resta**, así que una
   reconocida posterior al ingreso se ignora sola. Hoy **10 de 31** tienen reconocida.
2. **`anios_antiguedad(desde, periodo)`** (`:68-84`) — 🔴 **la medición NO es al 31/12**: es al
   **día 1 del mes `mes_cierre_antiguedad`** del año del período (`config/reglas_vacaciones.py`).
   Consecuencia: quien cumple 5 años en noviembre de 2026 recibe **14** días por 2026 y recién 21
   por 2027.
3. **`dias_por_antiguedad`** (`:86-95`) — escala por defecto **0–4 → 14 · 5–14 → 21 · 15+ → 28**,
   recorrida de mayor a menor con el primer match.
4. **`dias_anio_de_ingreso`** (`:97-113`) — el año de ingreso es un **CORTE, no un prorrateo**:
   antes de `corte_ingreso` (hoy `(7,1)`) va el cupo completo, desde ahí `dias_ingreso_tardio` = 5.
   🚩 RRHH no cerró dónde cae exactamente julio.
5. **`dias_vacaciones_asignados`** — si tiene un entero, **GANA sobre toda la escala y no caduca**
   (`:118-136`). NULL = se aplica la regla. Hoy **1 de 31** lo tiene.
6. **`periodo_de(fecha) = fecha.year`** (`:53-66`) — año calendario. 🚩 Abierto si RRHH aclara
   que el período va de octubre a septiembre.

> 🔴 **NO EXISTE UN CÁLCULO DE ANTIGÜEDAD PARA MOSTRAR, NI UNO DE EDAD.** La ficha no muestra
> "X años en la empresa" ni la edad; el listado y el export tampoco. La antigüedad solo existe
> **adentro** del cálculo de cupos de vacaciones, y la edad **no existe en ninguna parte** — la
> columna `Edad` del Excel se exige y se descarta (§4), y `fecha_nacimiento` (31/31) solo se usa
> para el KPI de cumpleaños.

---

## (a) COLUMNAS QUE EXISTEN Y ESTÁN VACÍAS EN LOS 31 — **22**

| Columna | Por qué está vacía |
|---|---|
| `legajo` | el CSV real no trae la columna (es `HEADERS_OPCIONALES`) |
| `email_personal`, `telefono`, `telefono_alternativo`, `tipo_documento` | **el import no las toca** y nadie las cargó a mano |
| `estudios`, `horas_contrato`, `perfil`, `referido` | ídem — cargables solo desde el modal |
| `domicilio` + las **6** `domicilio_*` | ídem (7 columnas) |
| 🔴 `organismo`, `sector` | **el dato ESTÁ en el Excel y el import lo desvía a `empresas`/`areas`** — ver §4 |
| `cargo`, `rol` | deprecados, nadie los escribe |
| `foto_url` | sin ningún escritor |
| `fecha_egreso`, `motivo_baja` | no hubo ninguna baja (`estado='activo'` en los 31) |
| `equipo` | el CSV trae la columna; llegó vacía o con un literal de `VACIOS` |
| `co_sourcing` | ídem — contra `product_owner` 31/31, mismo parser |
| `fecha_ingreso_prevista`, `fecha_baja_prevista` | DDL adelantado, **cero código** |

**Casi vacías, que valen lo mismo a efectos de mapeo:** `dias_vacaciones_asignados` **1/31** ·
`user_id` **1/31** · `categoria` **2/31** · `seniority` **3/31** · `fecha_ingreso_reconocida`
**10/31** · `manager_id` **11/31** · `ubicacion` **26/31**.

## (b) SE MUESTRAN PERO NO SE PUEDEN CARGAR DESDE NINGUNA PANTALLA

| Qué se muestra | Dónde | Único escritor |
|---|---|---|
| **Estado** (badge de la ficha) | ficha + export | `dar_de_baja` / `baja_logica` / el `'activo'` forzado del alta |
| **Empresa** | ficha + export | join; se fija en el alta y **no se puede cambiar en la edición** |
| **Área**, **Superior** | ficha + export | joins; sí editables |
| **Domicilio (sin desglosar)** | ficha, condicional | 🔴 **`domicilio` está en `FormData` y ningún control lo renderiza** — es de solo lectura de hecho |
| **Rol** cuando `roles` está vacío | ficha (fallback a `cargo`) | `cargo` no tiene escritor: el fallback es inalcanzable |

Y al revés — **cargables y nunca visibles en la ficha**: `dias_vacaciones_asignados` (sí aparece
en el export) y **`referido`** (no aparece en ningún lado).

Caso aparte: **`potencial` y `desempeno`** no se muestran *ni* se cargan. Su único escritor
(`assessment_resultados_repo.py:89`) pertenece a un módulo apagado por flag, y su único lector
(`sucesion_repo.py`) a otro. Los 31 están en el default.

## (c) LO QUE EL IMPORT DESCARTA

1. 🔴 **`Edad`** — **requerida en `HEADERS` (`transforms:16`), jamás leída.** El archivo se
   rechaza entero si falta y el valor se tira. No hay ningún cálculo de edad en el sistema que
   la reemplace.
2. 🔴 **`Organismo` → nunca llega a `empleados.organismo`.** Se usa para resolver/crear la
   empresa. **0/31.**
3. 🔴 **`Sector` → nunca llega a `empleados.sector`.** Se usa para resolver/crear el área.
   **0/31.**
4. **`Fecha Baja`** no se escribe por el mapeo de campos: dispara `dar_de_baja`, que escribe
   `estado` y `fecha_egreso` en un UPDATE aparte.
5. **`Apellido Superior` / `Nombre Superior`** no se escriben como texto: alimentan la segunda
   pasada de `manager_id`, y lo que no matchea va a `empleado_superior_pendiente` (**1 fila hoy**).
6. **Valores que se pierden por normalización**, no por descarte: todo lo que caiga en `VACIOS`
   (`""`, `NO APLICA`, `N/A`, `NA`, `-`, `--`, `SIN DATOS`, `SIN DATO`) entra como `NULL`
   (`_nomina_parsers.py:40`), y `Liderazgo` con un valor distinto de `SI`/`NO` deja `es_lider`
   **sin escribir** y se reporta como faltante (`transforms:100-104`) — a propósito: mapear
   "GERENTE DE ÁREA" a `false` afirmaría algo que nadie dijo.

# Estado real del sistema vs. lo comprometido con el directorio

**Proyecto:** HR Karstec (RRHH) · **Última verificación:** 27 de julio de 2026

---

## 1. Qué es este documento

Contraste **ítem por ítem** entre lo que los documentos entregados al directorio en **junio de 2026** comprometen (el *plan de implementación* y el *documento ejecutivo*) y lo que el código y la base de datos **realmente hacen hoy**.

**Contra qué se contrastó:**
- Los dos documentos del directorio (junio 2026): plan de implementación y documento ejecutivo — ninguno de los dos vive en el repo. El inventario de ítems se reconstruyó desde la **v1 de `Plan de trabajo`**, que es el instrumento interno derivado de ellos y enumera Entrega 2, Entrega 3 y el frente AWS. Esa v1 vivía en la raíz del repo y **ya no existe como archivo**: quedó consolidada en [`Plan de trabajo`](<Plan de trabajo>) (v2, el único vigente). Para consultar la v1 tal como se la leyó, está en el historial de git (commit `1c5dd30`, última forma en `e9df215`).
- **El código del repo** (`backend/`, `frontend/`, `migracionAWS/`), leído en modo read-only.
- **El catálogo real de la base de producción** vía MCP de Supabase (proyecto `grmdiwxcvcjorlohpwji`, "HR Karstec"), no las migraciones — producción driftea.

**Metodología y sus límites:**
- La evidencia es siempre `archivo:línea` o el nombre del objeto de DB. Donde no hay evidencia verificable, el ítem dice **NO DETERMINADO**, no una suposición.
- `CLAUDE.md` **no** se usó como fuente. Donde `CLAUDE.md` contradice al código, gana el código; las divergencias detectadas están en la sección 6.
- No se verificó comportamiento en runtime contra el sitio productivo. Todo es verificación estática de código + catálogo de DB.
- Los estimados originales en horas los completa Franco: la columna va con `—`.

**Estados usados:**

| Estado | Significado |
|---|---|
| **HECHO** | Existe end-to-end y es alcanzable por el usuario. |
| **PARCIAL** | Existe una parte; la columna "Qué falta" dice exactamente cuál. |
| **NO EXISTE** | Cero rastro en código y en DB. |
| **DISTINTO** | Existe, pero resuelve otra cosa que la comprometida. Va también a la sección 3. |
| **BLOQUEADO** | Depende de un input externo (datos o archivos de RRHH), no de desarrollo. |
| **DESCARTADO** | Se decidió no hacerlo. Va también a la sección 3. |

---

## 2. Tabla maestra

### Bloque 1 — Legajo (Entrega 2)

| # | Ítem | Entrega | Est. orig. | Estado | Evidencia | Qué falta |
|---|---|---|---|---|---|---|
| 1a | Campo **sexo** | E2 | — | **HECHO** | DB `empleados.sexo` (text) · API `backend/schemas/empleado.py:46,105,168` · UI edición `frontend/components/features/empleados/modal/DatosPersonalesFields.tsx:35-36` · UI ficha `.../ficha/DatosEmpleadoSection.tsx:28` | — |
| 1b | Campo **domicilio** | E2 | — | **CERRADO** | DB: seis columnas `domicilio_*` (migración **081**, no destructiva) + `domicilio` legado, reflejadas en `db/schema.sql` · API `schemas/empleado.py` + `schemas/empleado_out.py`, con `domicilio_provincia` validado por `Literal` contra las 24 jurisdicciones (`schemas/_provincias.py`, nombres oficiales del IGN) · catálogo `GET /api/empleados/provincias` · UI: bloque agrupado en el modal (`modal/DomicilioFields.tsx`, provincia como **select cerrado**) y dirección armada en una línea en la ficha (`ficha/_domicilio.ts`) · export de empleados con **Provincia** y **Localidad** | 🔴 **Los seis campos nacen VACÍOS.** `domicilio` estaba 0/19 en producción, así que no hubo migración de datos ni parseo de texto libre. El corte por provincia/localidad existe y está testeado, pero no hay nada que cortar hasta que RRHH cargue domicilios. El texto libre se conserva y se muestra en la ficha como referencia solo mientras los estructurados estén vacíos. **`ubicacion` no se tocó**: es dónde trabaja, no dónde vive. |
| 1c | Campo **horas de contrato** | E2 | — | **HECHO** | DB `empleados.horas_contrato` (integer) · API `schemas/empleado.py:52,111,174` · UI edición `modal/_constants.ts:125` (label "Horas por día", validado entero en `modal/form-utils.ts:18-19`) · UI ficha `ficha/DatosEmpleadoSection.tsx:45` | — (ojo: el label de edición dice "Horas por día" y el de la ficha "Horas de contrato" — mismo campo, dos nombres) |
| 1d | Campo **gerencia** | E2 | — | **HECHO** | DB `empleados.gerencia` (text) · API `schemas/empleado.py:54,113,176` · UI edición con autocompletado `modal/_constants.ts:47,138` · UI ficha `ficha/DatosEmpleadoSection.tsx:47` | — |
| 1e | Campo **liderazgo** | E2 | — | **DISTINTO** | La columna `empleados.liderazgo` (text) **existe en DB** pero **no está en la API** (ausente de los tres schemas de `schemas/empleado.py`) ni en la UI. Lo único que se lee/escribe por API es el booleano `es_lider` (`schemas/empleado.py:61,120,183`; ficha `DatosEmpleadoSection.tsx:57`). El único que escribe `liderazgo` es el import de nómina: `schemas/importacion_nomina_empleados.py:26,36,73` ← `services/_nomina_empleados_transforms.py:134` | El campo cualitativo `liderazgo` es **write-only por import**: se carga desde el CSV y nunca se muestra ni se edita. Falta exponerlo en API + UI, o decidir que `es_lider` lo reemplaza. |
| 1f | Campo **presencialidad** | E2 | — | **DISTINTO** | No existe ninguna columna llamada `presencialidad`. Lo más cercano: `empleados.modalidad_trabajo` (presencial/remoto/hibrido — `modal/DatosLaboralesFields.tsx:74-81`, ficha `DatosEmpleadoSection.tsx:53`) y `empleados.ubicacion` (text libre, ficha `:43`). También existen `turno` (`:44`) y `modalidad_contratacion` (`:55`). | Confirmar si "presencialidad" del documento = `modalidad_trabajo`. Si se esperaba un % o días presenciales por semana, **no existe**. |
| 2 | Renombrar **cargo → rol** | E2 | — | **DISTINTO** | No se renombró: se **unificó** `cargo` (mig 003) + `rol` (mig 029) en `empleados.roles TEXT[]` — ver el porqué en `backend/migrations/059_empleados_roles.sql:3-16`. Las 3 columnas conviven hoy en DB (`cargo`, `rol`, `roles`). La UI muestra siempre `roles` con fallback: `ficha/DatosEmpleadoSection.tsx:19`, `EmpleadosTable.tsx:78`, y el form ya no manda `cargo` (`frontend/types/empleado.ts:70`). | El DROP de `cargo` y `rol` está diferido a la tarea "S6" (`migrations/059:15-16`). Quedan fallbacks `?? cargo` en 2 lugares del front. Es 1 campo multi-valor, no 1 campo renombrado. |
| 3 | **Historial de cambios en el legajo** (rol, área, seniority, sueldo) visible en la ficha | E2 | — | **CERRADO** | Dos secciones en la ficha, separadas a propósito. **Cambios**: `HistorialCambiosSection.tsx`, del audit log filtrado por `entidad="empleado"` + `registro_id`, con paginado y modal — cubre rol, área y seniority, que son columnas de `empleados`. **Sueldo**: `HistorialSalarialSection.tsx`, que NO sale del log sino de la serie de `costos_nomina` (`GET /api/costos/nomina/empleado/{id}`): `UNIQUE (empleado_id, anio, mes)` hace que la progresión ya esté en los datos. No se fusionaron: dos fuentes paginadas server-side no se combinan sin traer todo, y las formas no son compatibles. Gateado por `Seccion.COSTOS` en backend y front. | 🔴 **DOS SALVEDADES.** (1) **El historial de sueldo sale vacío hoy**: `costos_nomina` tiene 0 filas en producción. La capacidad está entregada y testeada, el valor aparece cuando RRHH cargue nómina. (2) Hasta esta tanda, el historial de los otros tres campos **mostraba datos falsos**: 93 de 113 eventos afirmaban que el área y la empresa del empleado se habían vaciado, por un diff que comparaba el registro leído con joins contra el devuelto sin ellos. Corregido; los eventos viejos no se borran y se renderizan como "se editó, sin cambios en campos auditados". |
| 4 | **Historial de vacaciones desde el ingreso**, accesible desde el legajo | E2 | — | **HECHO** | `frontend/components/features/empleados/ficha/VacacionesSection.tsx`, montada en `empleados/[id]/page.tsx:103`. Consume `GET /vacaciones/empleado/{id}` (`VacacionesSection.tsx:48`), sin recorte de fecha → trae todo el histórico. Muestra desde / hasta / días / estado. Solo lectura. | — (hoy sale vacío: `solicitudes_vacaciones` tiene 0 filas en producción — bloqueo de datos, no de código) |
| 5 | **Inventario asignado visible en el legajo** | E2 | — | **HECHO** | `frontend/components/features/empleados/ficha/InventarioSection.tsx`, montada en `empleados/[id]/page.tsx:101`. Consume `GET /inventario/asignaciones?empleado_id=` (`:47`). Muestra equipo, N° de serie, fecha de asignación y estado de devolución. Solo lectura. | — (hoy vacío: `inventario_items` tiene 0 filas en producción) |

> **Extra no comprometido, presente en la ficha:** adjuntos (`AdjuntosSection`, `:100`) y cesiones (`CesionesSection`, `:104`), más el botón de iniciar offboarding (`:80-88`). La ficha tiene hoy 6 secciones — `empleados/[id]/page.tsx:99-104`.

### Bloque 2 — Import / Export (Entrega 2)

| # | Ítem | Entrega | Est. orig. | Estado | Evidencia | Qué falta |
|---|---|---|---|---|---|---|
| 6 | **Export de inventario, evaluaciones y objetivos** | E2 | — | **HECHO** (los 3) | Inventario: dos exports — ítems `routers/inventario_items.py:34` y asignaciones `routers/inventario_asignaciones.py:43`; UI en `components/features/inventario/ItemsTab.tsx` y `AsignacionesTab.tsx`. Evaluaciones: dos — desempeño `routers/ev_instancias.py:33` y resultados importados `routers/evaluaciones_resultados.py:64`; UI vía `services/evaluacionReportes.ts`. Objetivos: `routers/objetivos.py:46`; UI en `app/(dashboard)/objetivos/page.tsx`. | — |
| 6b | Inventario de exports — **quién tiene y quién no** | E2 | — | **PARCIAL** (10 módulos de ~25) | **CON export** (10 endpoints, todos con `Content-Disposition` en `backend/routers/`): empleados, vacaciones, ausencias, capacitaciones (asignaciones), inventario-ítems, inventario-asignaciones, objetivos, evaluaciones de desempeño (`ev_instancias`), evaluaciones-resultados (evaluados de un lote), reportes. **SIN export:** vacantes, candidatos, costos/nómina, presupuesto, proyectos, horas de proyecto, onboarding, offboarding, áreas, auditoría, procesos, usuarios, cesiones, sucesión, assessment, períodos. Organigrama exporta por `window.print()` del navegador, no por el motor (`app/(dashboard)/organigrama/page.tsx:60-72`). | Definir cuáles de los 16 sin export el documento comprometía. Costos/nómina y auditoría son los ausentes más notorios. |
| 7 | **Todos los exports por `build_export` + patrón `_<modulo>_export.py`** | E2 | — | **HECHO** | Los 10 services de export importan `services.export.build_export` — único motor, sin implementaciones sueltas: `empleado_service.py:73`, `vacaciones_service.py:58`, `ausencias_service.py:48`, `asignacion_service.py:39`, `inventario_items_service.py:35`, `inventario_asignaciones_service.py:44`, `objetivo_service.py:44`, `ev_instancias_service.py:53`, `evaluacion_reportes_service.py:47`, `reporte_export_service.py:45`. Cada uno proyecta con su `construir_filas_export` en `services/_<modulo>_export.py` (9 archivos). Motor: `services/export/engine.py:24` (+ renderers `_pdf`/`_excel`/`_csv`/`_word`). | — |
| 8 | **Import Excel (XLSX)** | E2 | — | **NO EXISTE** | `openpyxl` aparece en 2 archivos y **solo para escribir**: `services/export/_excel.py:9` (`from openpyxl import Workbook`) y `_excel_estilos.py:8` (estilos). **Cero `load_workbook`** en todo el backend. Los 3 imports que existen son CSV: `services/nomina_empleados_service.py:49`, `services/nomina_csv_service.py:40`, `services/evaluacion_import_service.py:43` — los tres `csv.DictReader`. | Todo: el reader XLSX, y sobre él los parsers de vacaciones / ausencias / objetivos / evaluaciones. **BLOQUEADO** además por los archivos de ejemplo de RRHH: sin ellos no se define el formato. |

### Bloque 3 — Filtros (Entrega 3)

| # | Ítem | Entrega | Est. orig. | Estado | Evidencia | Qué falta |
|---|---|---|---|---|---|---|
| 9a | Filtro por **área** en capacitaciones | E3 | — | **HECHO** end-to-end | Repo `repositories/asignacion_repo.py:36,39-40` (resuelve empleados del área y filtra) → service `services/asignacion_service.py:32,34` → router `routers/asignaciones_capacitacion.py:23,26` → UI `components/features/capacitaciones/AsignacionesTab.tsx:57,112`. El export acepta el mismo filtro (`asignaciones_capacitacion.py:30-31`, UI `:126`). | — |
| 9b | Filtro por **área** en inventario | E3 | — | **NO EXISTE** | `routers/inventario_items.py:34` solo acepta `estado`; `routers/inventario_asignaciones.py:43-50` solo `empleado_id`. Sin `area_id` en repo, service, router ni UI. | Las 4 capas. |
| 9c | Filtro por **área** en objetivos | E3 | — | **NO EXISTE** | `routers/objetivos.py:46,53` acepta `estado`, `responsable_id`, `prioridad`. Sin `area_id`. Agravante estructural: `objetivos.responsable_id` es FK a **`users`**, no a `empleados` (`backend/schemas/objetivo.py:5`), así que un objetivo no tiene área derivable. | Las 4 capas **y** definir de dónde saldría el área (hoy el modelo no la puede inferir). |
| 9d | Filtro por **área** en proyectos | E3 | — | **NO EXISTE** | `routers/proyectos.py:27-31` acepta solo `estado`; la UI también solo estado (`app/(dashboard)/proyectos/page.tsx:83,120`). El área aparece únicamente **dentro** del modal de asignación, para filtrar candidatos a asignar (`components/features/proyectos/AsignarEmpleadosModal.tsx`), no para filtrar el listado. | Las 4 capas. |
| 10 | Filtro por **proyecto** en colaboradores, vacaciones, ausencias y evaluaciones | E3 | — | **NO EXISTE** (0 de 4) | Grep de `proyectoFiltro` / `proyecto_id` en `frontend/app`, `frontend/components` y `frontend/services` excluyendo el propio módulo de proyectos: **cero resultados**. Backend: `routers/empleados.py:24` (area/estado/search/es_lider), `routers/vacaciones.py:30-38` (area/empleado/estado), `routers/ausencias.py:26-33` (area/empleado/tipo), `routers/evaluaciones_resultados.py:57-61` (sector/perfil/con_nota). Ninguno acepta `proyecto_id`. | Las 4 capas × 4 módulos. La tabla puente `proyecto_asignaciones` existe y tiene 19 filas, así que el dato está — falta el filtro. |

### Bloque 4 — Migraciones correctivas de `empresa_id` (Entrega 3)

| # | Ítem | Entrega | Est. orig. | Estado | Evidencia | Qué falta |
|---|---|---|---|---|---|---|
| 11 | `costos_nomina` y `presupuesto_areas` con **`empresa_id`** | E3 | — | **HECHO** | Catálogo real: `costos_nomina.empresa_id` (uuid) y `presupuesto_areas.empresa_id` (uuid), ambas presentes. Origen: `backend/migrations/055_retrofit_empresa_id.sql:58` y `:69`. | — |
| 12 | Tablas de **assessment** (migs 020–021) con `empresa_id` | E3 | — | **HECHO** (las 4, no solo 020–021) | Catálogo real: `assessment_campanas`, `assessment_links`, `assessment_resultados`, `assessment_reportes` — las cuatro con `empresa_id`. Origen: `migrations/055_retrofit_empresa_id.sql:113,124,135,146`. | — |
| 13 | Tablas de **sucesión** con `empresa_id` | E3 | — | **HECHO** | Catálogo real: `sucesion_posiciones`, `planes_carrera`, `planes_carrera_hitos` — las tres con `empresa_id`. Origen: `migrations/055_retrofit_empresa_id.sql:80,91,102`. | — |
| 13b | Cobertura general de `empresa_id` | E3 | — | **PARCIAL, por diseño** | De 51 tablas de `public`, **8 no llevan `empresa_id`** y en 7 casos es correcto: `empresas` (es la tabla raíz), `users` y `usuario_integraciones` (los usuarios no cuelgan de empresa — decisión de producto), `tipos_ausencia` (catálogo global), `evaluacion_evaluados` y `evaluacion_resultados` (hijas: alcanzan la empresa por `lote_id`), `notificaciones` / `notificaciones_config` (schema muerto, ver #14). El caso a mirar es **`proyecto_asignaciones`**, que no tiene `empresa_id` sino `empleado_empresa_id` (uuid) — modelo distinto a propósito (un proyecto cruza empresas), pero rompe el patrón del resto. | Confirmar que `proyecto_asignaciones.empleado_empresa_id` es la decisión final y no un retrofit incompleto. |

### Bloque 5 — Infraestructura de features no construidas (Entrega 3)

| # | Ítem | Entrega | Est. orig. | Estado | Evidencia | Qué falta |
|---|---|---|---|---|---|---|
| 14 | **Alertas configurables** | E3 | — | **NO EXISTE** (solo el schema, vacío) | Grep de `notificacion` en todo `backend/` y `frontend/`: **cero resultados**. No hay router, service, repo, motor periódico ni UI. Las tablas existen (migs 022/023) y están **vacías**: `notificaciones` 0 filas, `notificaciones_config` 0 filas. Contenido real: `notificaciones (id, user_id, tipo, titulo, mensaje, referencia_tipo, referencia_id, leida, leida_en, created_at)` — cuelga de `user_id`, sin `empresa_id`; `notificaciones_config (id, user_id, tipo_evento, canal, activo, created_at, updated_at)` — un on/off por usuario × evento × canal, **sin ningún catálogo de eventos ni de canales** (ambos son varchar libre). | Absolutamente todo el código. La "infraestructura existente" son 2 tablas vacías de 10 y 7 columnas, sin FKs de negocio ni catálogo — cubren menos de lo que el nombre sugiere. |
| 15 | **Plantillas de mail** | E3 | — | **NO EXISTE** | No existe tabla `email_templates` (ni ninguna con `template` o `plantilla` en el nombre) en el catálogo de `public`. Grep de `email_template` / `plantilla_mail`: cero. Resend: **solo la env var** — `backend/config/settings.py:26-28` (`resend_api_key`, `resend_from_email`) y una aserción en `tests/test_critical_flows.py:135,140`. **Ningún service importa Resend**: hoy el sistema no envía un solo mail. | Tabla, UI de edición, y la integración real de Resend (que no está empezada). |
| 16 | **Bloqueos por módulo con fecha configurable** (cierre de novedades) | E3 | — | **HECHO** — desmiente lo esperado | **Existe y está completo.** Tabla `periodos_cerrados (id, empresa_id, modulo, desde, hasta, estado, cerrado_por, cerrado_at, reabierto_por, reabierto_at)` (mig `062_periodos_cerrados.sql`). Backend: `routers/periodos.py` (listar / cerrar / reabrir, gate `Seccion.PERIODOS`), `services/periodo_service.py` (audita cierre y reapertura), `repositories/periodo_repo.py`. La validación que rechaza escrituras fuera de plazo vive centralizada en `services/_periodo_utils.py::verificar_periodo_abierto`, y está enganchada en 7 puntos de escritura: vacaciones (`vacaciones_service.py:99,138`), ausencias (`_ausencias_write.py:43,68,69,106`) y costos (`costo_service.py:103`). UI completa: `app/(dashboard)/periodos/page.tsx` + `components/features/periodos/PeriodoForm.tsx` y `PeriodoList.tsx`, en el sidebar bajo "Administración" (`nav-config.ts`). Compara contra el **rango de fechas del registro** (solapamiento), no contra la fecha de carga (`_periodo_utils.py:36-38,63-72`). Tests: `tests/test_periodos.py`, `tests/test_periodos_enganche.py`. | Dos huecos reales, no de infraestructura: (a) **solo bloquea a `mandos_medios`** — admin_rrhh y gerencia_lectura nunca se frenan, por diseño explícito (`_periodo_utils.py:47-48`); (b) el enganche de **costos pasa `rol=None` hardcodeado** (`costo_service.py:103`), lo que lo vuelve un **no-op en ese módulo**. |
| 17 | **Objetivos: subobjetivos, múltiples responsables, fechas diferenciadas** | E3 | — | **NO EXISTE** (los 3) | Catálogo real de `objetivos`: `(id, empresa_id, responsable_id, titulo, descripcion, prioridad, estado, fecha_entrega, created_at, updated_at)`. **Sin `parent_id`** → no hay jerarquía. **`responsable_id` es un uuid escalar** (`schemas/objetivo.py:22`), y encima FK a `users`, no a `empleados` (`schemas/objetivo.py:5`) → no hay múltiples responsables ni se puede asignar a un empleado. **Una sola `fecha_entrega`** → no hay fechas diferenciadas. La tabla tiene **0 filas** en producción. | Rediseño del modelo de datos (tabla de jerarquía + tabla puente de responsables + fechas por subobjetivo). Es el ítem más lejano de todos los del bloque. |
| 18 | **Organigrama** | E3 | — | **PARCIAL / DISTINTO** | Hoy renderiza **una sola vista: "Por proyecto · cards"**. Las otras dos están escritas pero apagadas por flag: `app/(dashboard)/organigrama/page.tsx:19-23` — `{empresa, visible:false}`, `{proyecto-arbol, visible:false}`, `{proyecto-cards, visible:true}`. Con una sola vista visible ni siquiera se dibujan los tabs (`:88`). Datos: `fetchOrgProyectos()` → `GET /api/organigrama/proyectos` (`routers/organigrama.py:36`) → `services/organigrama_proyectos_service.py`, o sea **proyectos + sus asignaciones** (`proyecto_asignaciones`, 19 filas / `proyectos`, 6 filas). El árbol clásico Empresa→Área→Empleado tiene endpoint vivo y gateado (`routers/organigrama.py:27`) pero **es inalcanzable desde la UI**. Export = `window.print()` del navegador (`page.tsx:60-72`), no el motor de export. | Decidir si el rediseño está cerrado. Hoy conviven un endpoint huérfano (`GET /api/organigrama`) y dos componentes sin punto de entrada (`ArbolEmpresa`, `ArbolProyecto`). Reactivar cada vista es poner su `visible` en `true`. |
| 19 | **Offboarding: formulario estructurado con motivos tipificados** | E3 | — | **PARCIAL** | Los motivos **sí están tipificados**: `MotivoEgreso = Literal["renuncia","despido","acuerdo_mutuo","fin_contrato","jubilacion","fallecimiento","otro"]` (`backend/schemas/offboarding.py:12-15`), con dropdown en `components/features/empleados/ficha/OffboardingModal.tsx:17,73`. Captura hoy: `empleado_id`, `motivo` (tipificado), `fecha_ultimo_dia`, `descripcion_motivo` (texto libre) — `schemas/offboarding.py:18-22` — más checklist de activos y accesos (`ActivoResponse`, `AccesoResponse`, `:26-38`). | **La entrevista de salida no existe como formulario.** Las columnas `offboarding_instancias.entrevista_salida` (boolean) y `notas_entrevista` (text) están en DB y tienen **cero referencias en todo el código** (backend y frontend) — son columnas muertas. Tampoco hay estadísticas por motivo. La tabla tiene 0 filas en producción. |
| 20 | **Evaluaciones: estadísticas anuales / cruce de más de un lote** | E3 | — | **NO EXISTE** | Los 7 endpoints de reporting de evaluaciones cuelgan todos de **un único `lote_id`**: `/lotes/{lote_id}/metricas`, `/evaluados`, `/evaluados/export`, `/evaluados/{id}/ficha` (`routers/evaluaciones_resultados.py:49,56,64,77`). El único endpoint sin `lote_id` es `GET /lotes` (`:25`), que lista lotes para el selector — no agrega nada. Los cálculos (`services/_evaluacion_metricas.py`) operan sobre las filas de un lote. **No hay evolución por empleado, ni comparativa temporal, ni ranking entre períodos.** En producción hay **1 solo lote** (Julio 2026), así que ninguna comparativa tendría datos aún. | Endpoints de estadística cross-lote + modelo de series temporales + librería de gráficos en el front. Ojo con el invariante ya documentado: las competencias de perfil líder y general **no se pueden mezclar** en un mismo ranking. |

### Bloque 6 — Seguridad y AWS

| # | Ítem | Entrega | Est. orig. | Estado | Evidencia | Qué falta |
|---|---|---|---|---|---|---|
| 21 | **Rate limiting** | AWS/Seg. | — | **PARCIAL — 1 solo endpoint** | `slowapi` está instalado y montado: `backend/main.py:8-9,69-70` (handler de `RateLimitExceeded`) + `routers/auth.py:6-7,14` (`Limiter(key_func=get_remote_address)`). **El único endpoint limitado es `POST /api/auth/login`, a 5/minuto por IP** (`routers/auth.py:25`, documentado en `:3`). Grep de `@limiter.limit` en todo el backend: 1 sola ocurrencia. | Todo el resto de la superficie está sin límite: las 2 rutas públicas de assessment sin auth (`middleware/auth.py:28`), el formulario público de candidatos, `/api/auth/refresh`, los endpoints de import y los de export (que son caros: `page_size=100000`). |
| 22 | **Google OAuth: verificación del callback** | AWS/Seg. | — | **DISTINTO — usa el `user_id`, no un token CSRF** | `services/integracion_service.py:98` pasa `state=user_id` al construir la URL de autorización (documentado como tal en `:82`). El callback lo toma tal cual: `routers/integraciones.py:37-44` → `_service().handle_google_callback(user_id=state, code=code)`. El `state` es **el UUID del usuario**, valor estable y adivinable, no un nonce aleatorio de corta duración, y **no se valida contra nada guardado del lado servidor**. Agravante: `/api/integraciones/google/callback` está en `PUBLIC_ROUTES` (`middleware/auth.py:25`), o sea que se alcanza sin JWT. | Un `state` aleatorio, de un solo uso y con TTL corto, persistido server-side y verificado en el callback. Tal como está, el `state` no cumple su función anti-CSRF. |
| 23 | **`middleware/auth.py`: validación de `X-Empresa-Id`** | AWS/Seg. | — | **NO EXISTE** (ninguna de las dos validaciones) | `backend/middleware/auth.py:133-141`: se lee el header, se descarta si es vacío o `"todas"`, y lo único que se hace es `UUID(empresa_header)` — **una validación de formato**. Si parsea, se guarda en `request.state.empresa_id`; si no, queda `None`. **No se consulta `empresas`** para ver si existe, y **no se consulta ninguna tabla de acceso** para ver si el usuario la tiene habilitada. El resolver aguas abajo (`utils/empresa.py:14-20`) tampoco valida. | La verificación de existencia es un fix chico y localizado. La de acceso por usuario **no es implementable hoy**: la tabla `acceso_empresa` no existe y la decisión de producto vigente es que todo usuario ve todas las empresas — o sea que hoy no hay aislamiento que romper, pero tampoco red si esa decisión cambia. |
| 24 | **Dockerfile / .dockerignore / docker-compose / GitHub Actions** | AWS | — | **NO EXISTE** (los 4) | Búsqueda en todo el repo (excluyendo `node_modules`): sin `Dockerfile`, sin `.dockerignore`, sin `docker-compose*`. No existe el directorio `.github/` → sin workflows de CI/CD. El deploy vive 100% en Vercel (`backend/vercel.json`). | El frente AWS entero. `migracionAWS/` tiene el código de aplicación (auth, `postgres_client.py` asyncpg, repos-molde, migraciones 075–077 y docs) pero **cero infraestructura**: ni contenedores, ni pipeline, ni IaC. |

### Bloque 7 — Los 18 módulos declarados "operativos"

Alcanzabilidad desde el sidebar (`frontend/components/layout/nav-config.ts`), para un usuario `admin_rrhh`:

| Módulo | Estado | Evidencia |
|---|---|---|
| **dashboard** | **ALCANZABLE** — ítem fijo arriba del acordeón | `nav-config.ts:31-32` (`DASHBOARD_ITEM`, `seccion: null` = siempre visible) |
| **colaboradores** (empleados) | **ALCANZABLE** — grupo "Personas" | `nav-config.ts:57` |
| **vacaciones** | **ALCANZABLE** — "Personas" | `nav-config.ts:62` |
| **ausencias** | **ALCANZABLE** — "Personas" | `nav-config.ts:63` |
| **capacitaciones** | **ALCANZABLE** — "Desempeño" | `nav-config.ts:78` |
| **evaluaciones** | **ALCANZABLE** — "Desempeño" | `nav-config.ts:79` |
| **inventario** | **ALCANZABLE** — "Operación" | `nav-config.ts:75` |
| **objetivos** | **ALCANZABLE** — "Desempeño" | `nav-config.ts:80` |
| **proyectos** | **ALCANZABLE** — "Operación" | `nav-config.ts:74` |
| **onboarding** | **ALCANZABLE** — "Incorporación" | `nav-config.ts:68` |
| **offboarding** | **ALCANZABLE** — "Incorporación" | `nav-config.ts:69` |
| **áreas** | **NO ESTÁ EN EL SIDEBAR** — la página existe (`app/(dashboard)/areas/page.tsx`) y la ruta responde, pero ningún ítem de `NAV_GROUPS` apunta a `/areas`. Se llega solo tecleando la URL o desde otra pantalla. | `nav-config.ts:53-92` completo, sin entrada `/areas` |
| **organigrama** | **ALCANZABLE, con una sola de sus tres vistas** | `nav-config.ts:58` · ver ítem 18 |
| **vacantes / selección** | **ALCANZABLE** — "Incorporación", dos ítems separados | `nav-config.ts:66` (vacantes) y `:67` (candidatos) |
| **costos / nómina** | **ALCANZABLE** — "Análisis" | `nav-config.ts:83` |
| **sucesión** | **OCULTO a propósito** — el ítem está construido (`SUCESION_ITEM`, `nav-config.ts:50-51`) pero solo entra al grupo si `SUCESION_ACTIVA`, que es `false` (`:48`, spread condicional en `:70`). Además la página redirige a `/dashboard` (`app/(dashboard)/sucesion/page.tsx:25,28`). Backend, componentes y tests intactos. | `nav-config.ts:48,50-51,70` |
| **reportes** | **ALCANZABLE** — "Análisis" | `nav-config.ts:84` |
| **assessment** | **OCULTO, y más duro que sucesión** — no hay ítem de sidebar, y las dos páginas redirigen. El detalle usa un flag (`assessment/[id]/page.tsx:75,78`), pero el **listado tiene un `router.replace("/dashboard")` incondicional seguido de `return null` y todo el cuerpo real detrás de un `eslint-disable no-unreachable`** (`app/(dashboard)/assessment/page.tsx:74-77`). Backend entero y expuesto, con 2 rutas públicas sin auth (`middleware/auth.py:28`). | `assessment/page.tsx:74-77` |
| **configuración de integraciones** | **ALCANZABLE** — "Administración" → Configuración | `nav-config.ts:91` |

**Resumen:** de los 18 declarados operativos, **15 son alcanzables** desde el sidebar, **2 están apagados a propósito** (sucesión, assessment) y **1 existe pero no tiene punto de entrada** (áreas). Además hay **3 ítems alcanzables que no figuran en la lista de 18**: **auditoría** (`nav-config.ts:85`), **períodos** (`:90` — justamente la feature del ítem 16) y **"Mi equipo"** (`:61`, visible solo para `mandos_medios`).

---

## 3. Divergencias que requieren decisión

Solo el contraste. Sin propuesta de solución.

### 3.1 · "Renombrar cargo → rol" (ítem 2) — DISTINTO
- **El documento dice:** renombrar el campo `cargo` a `rol`.
- **El sistema hace:** no renombró nada. Unificó `cargo` (mig 003) **y** `rol` (mig 029) en un tercer campo **multi-valor** `roles TEXT[]` (mig 059). Las tres columnas conviven hoy en la base. La UI muestra `roles.join(", ")` con fallback a `cargo`.

### 3.2 · "Liderazgo" (ítem 1e) — DISTINTO
- **El documento dice:** campo de liderazgo en el legajo.
- **El sistema hace:** hay dos cosas distintas. `empleados.liderazgo` (texto) existe en la base y **solo se escribe desde el import de nómina** — no está en la API ni en la UI, nadie lo lee. Lo que la ficha muestra es `es_lider`, un booleano Sí/No.

### 3.3 · "Presencialidad" (ítem 1f) — DISTINTO
- **El documento dice:** campo de presencialidad.
- **El sistema hace:** no existe una columna con ese nombre. Existen cuatro campos vecinos que podrían corresponderle según qué se haya prometido: `modalidad_trabajo` (enum presencial/remoto/híbrido), `ubicacion` (texto libre), `turno` (texto libre) y `modalidad_contratacion` (texto libre). Si lo comprometido era un porcentaje o una cantidad de días presenciales, no hay dónde guardarlo.

### 3.4 · "Domicilio completo" (ítem 1b) — RESUELTO (C4, migración 081)
- **El documento dice:** domicilio completo.
- **El sistema hacía:** un único campo de texto libre `domicilio`, no filtrable ni agregable.
- **El sistema hace ahora:** seis columnas estructuradas (calle · número · piso/depto · localidad · provincia · CP). Las tres agregables son provincia, localidad y CP; las otras tres existen para que la dirección sirva para mandar algo. La provincia es una **lista cerrada** de las 24 jurisdicciones: sin eso, "Córdoba"/"CORDOBA"/"Cba" convivirían y el campo no agregaría nada.
- **Lo que falta para que se note:** datos. Estaba 0/19 y sigue en 0/19 — los campos nacen vacíos. El **filtro** por provincia/localidad en el listado quedó fuera a propósito (es trabajo de Bloque B, cerrado) y está anotado en `MATRIZ-FILTROS.md` como candidato para cuando haya domicilios cargados.

### 3.5 · "Bloqueos por módulo con fecha configurable" (ítem 16) — DISTINTO, y a favor
- **Lo esperado al encarar esta verificación:** que no existiera.
- **El sistema hace:** existe completo (tabla, router, service, repo, check centralizado, UI, tests, auditoría). Pero **solo frena al rol `mandos_medios`** por diseño explícito, y el enganche de costos está anulado porque pasa `rol=None`. O sea: para un `admin_rrhh` el período cerrado no bloquea nada.

### 3.6 · "Alertas configurables: activar infraestructura existente" (ítem 14) — DISTINTO
- **El documento dice:** activar la infraestructura existente.
- **El sistema hace:** la "infraestructura" son 2 tablas vacías (10 y 7 columnas) creadas en las migraciones 022/023, sin una sola línea de código que las toque, sin catálogo de eventos ni de canales, y sin `empresa_id` (cuelgan de `user_id`). No hay nada que activar: es construcción desde cero.

### 3.7 · "Organigrama" (ítem 18) — DISTINTO
- **El documento dice:** organigrama.
- **El sistema hace:** una sola vista, cards por proyecto. La vista jerárquica clásica (Empresa → Área → Empleado) está construida, su endpoint está vivo y gateado, y es **inalcanzable desde la UI** por un flag `visible: false`. Falta decidir si el rediseño está cerrado o si esa vista vuelve.

### 3.8 · `X-Empresa-Id` sin validar (ítem 23) — decisión de producto pendiente
- **Lo que el sistema hace:** acepta cualquier UUID sintácticamente válido como empresa activa, sin verificar que exista.
- **El contexto:** la decisión de producto vigente es que **todo usuario accede a todas las empresas**, así que no hay aislamiento que vulnerar hoy. Pero la validación de *existencia* tampoco está, y el día que se introduzca `acceso_empresa`, este es el único punto donde habría que enchufar el control.

### 3.9 · `proyecto_asignaciones` sin `empresa_id` (ítem 13b)
- **El patrón general:** toda tabla de negocio lleva `empresa_id`.
- **El sistema hace:** `proyecto_asignaciones` lleva `empleado_empresa_id` en su lugar, porque un proyecto cruza empresas por diseño. Es coherente con el modelo de datos, pero es la única tabla que rompe el patrón y conviene dejarlo declarado como decisión, no como olvido.

---

## 4. Trabajo hecho que no figura en los documentos

Las cuatro fases ocurrieron **después** de junio de 2026, así que ninguna aparece en el plan de implementación ni en el ejecutivo. Es trabajo entregado que hoy no está contabilizado.

### Fase 0 — Blindaje pre-testing
- **Verificación real de la firma del JWT.** El middleware pasó de `jwt.decode(verify_signature=False)` (bypass total: cualquiera podía fabricar un token) a verificar ES256 contra el JWKS público de Supabase, con expiración, fail-closed y 401 genérico (`backend/middleware/auth.py:60-93`). Se sumó refresh automático con mutex anti-concurrencia y logout que revoca de verdad.
- **Auditoría de nómina que se perdía en silencio:** el payload mandaba el literal `"lote_nomina"` en una columna uuid → el insert fallaba, `AuditService` se tragaba la excepción y el evento desaparecía. Ahora usa un uuid de evento (`services/_audit_payloads_rrhh.py:182`).
- **Pérdida de datos en `confirmar()` de evaluaciones:** el reimport borraba el lote viejo antes de crear el nuevo, sin transacción — un fallo perdía los dos. Ahora: lote nuevo con período temporal → persistir → **verificación por conteo** → recién ahí borrar el viejo → renombrar.
- **Edición de `manager_id`** desde la ficha, con anti-ciclos server-side (auto-referencia, ciclo directo e indirecto, tope de 50 saltos).

### Fase 1 — Reportes y KPIs
- **11 reportes descargables** (PDF/Excel/CSV/Word) sobre el motor genérico: dotación (headcount, altas/bajas nominal, distribución por seniority/modalidad/turno, rotación por motivo), vacaciones y ausencias (listado combinado, ausentismo por área, saldos), costos (masa salarial, presupuesto vs. real, capacitación por área) y auditoría/trazabilidad.
- **9 KPIs de dashboard**, con `_safe` por KPI: si uno falla, los demás se devuelven igual y el fallido queda marcado en `errores` — antes un KPI roto tiraba el dashboard entero a 500.
- Quedó fijado el principio **Vista vs. Acción**: el selector de empresa del sidebar filtra lo que se *mira*; las acciones reciben la empresa como parámetro explícito del formulario.

### Fase 2 — Barrera de empresa (commits `bd95e98` + `9d7baa7`)
- **92 de 92 endpoints** que reciben un id de recurso validan que ese recurso sea de la empresa del request, con el filtro en el `WHERE` de la query donde el repo lo permite. Antes, un UUID de otra empresa entraba igual y la operación se ejecutaba sobre él.
- **13 de 13 superficies** de vacaciones y ausencias componen además el eje de ownership (empresa ∩ ownership, por intersección).
- **8 endpoints marcados NO APLICA con razón escrita** (usuarios, empresa, assessment público, integraciones).
- El 404 es idéntico para "no existe" y "es de otra empresa" — un 403 sería un oráculo de enumeración. Se corrigió también el orden de los gates: la barrera de empresa va antes de cualquier chequeo de estado que responda otro código.

### Fase 3 — Deuda estructural (commits `51832e2` + `a6acaed`)
- **N+1 de sucesión resuelto:** `get_analisis_posicion` hacía una query por empleado. Con batch, 200 empleados pasaron de **201 requests a 2**.
- **`sucesion/page.tsx` de 855 → 85 líneas** (8 componentes + 2 hooks extraídos). Es el precedente de corte para las páginas grandes que quedan.
- **`fetchEmpleados` / `exportarEmpleados` migrados a objeto de opciones** sobre una interfaz compartida, con 10 call sites auditados uno por uno. Elimina la trampa de los parámetros posicionales del mismo tipo.

### Fuera de fase, tampoco en los documentos
- **Módulo de períodos completo** (mig 062 + router + service + repo + check centralizado + UI + tests) — el ítem 16 de este documento.
- **Módulo de evaluaciones por importación de resultados** (migs 078/079): lotes, evaluados, resultados, equivalencias, matcheo por apellido+nombre, métricas con brecha de autopercepción, historial de importaciones con multi-selección y borrado.
- **ABM de usuarios con roles funcionales** (mig 063), **adjuntos polimórficos** (mig 061), **cesiones** (mig 066).

---

## 5. Lo que está bloqueado por datos, no por código

Vale registrarlo porque distorsiona cualquier demo: el sistema está construido pero la base está casi vacía. Conteos reales de producción al 27/7/2026:

| Tabla | Filas |
|---|---|
| `empleados` | 19 |
| `proyectos` | 6 |
| `proyecto_asignaciones` | 19 |
| `evaluacion_lotes` | 1 |
| `objetivos` | 0 |
| `inventario_items` | 0 |
| `capacitaciones` | 0 |
| `horas_proyecto` | 0 |
| `offboarding_instancias` | 0 |
| `planes_carrera` | 0 |
| `sucesion_posiciones` | 0 |
| `assessment_campanas` | 0 |
| `notificaciones` / `notificaciones_config` | 0 / 0 |

Los reportes y KPIs de la Fase 1 son correctos y salen **vacíos**. Antes de cualquier entrega a testing hay que decirlo explícitamente, o se va a leer como "está roto".

---

## 6. Donde `CLAUDE.md` no coincide con el código

Verificado contra los archivos fuente. En todos los casos gana el código.

1. **`CLAUDE.md` no menciona el módulo de períodos** (`periodos_cerrados`, router, service, UI, tests). Es una feature completa y en producción, ausente del documento — y encima es la que responde al ítem 16.
2. **Gate de assessment.** `CLAUDE.md` dice que los dos módulos apagados usan `useState(false)` y que "no hay que convertir el flag en `const`". Cierto para `assessment/[id]/page.tsx:75` y para sucesión. **Falso para el listado**: `app/(dashboard)/assessment/page.tsx:74-75` tiene un `router.replace()` incondicional + `return null` y el cuerpo entero detrás de un `eslint-disable no-unreachable`. No hay flag ahí.
3. **La ficha del empleado tiene 6 secciones** (datos, adjuntos, inventario, historial de cambios, vacaciones, cesiones — `empleados/[id]/page.tsx:99-104`) y `CLAUDE.md` no las documenta en ningún lado. Tres de esas seis son ítems comprometidos con el directorio (3, 4 y 5 de este documento).
4. ~~**`Plan de trabajo` (raíz) está desactualizado en su ítem 1.4**~~ — **CERRADO, ya no aplica.** El hallazgo era doble y las dos mitades se resolvieron: (a) el defecto de comparar "contra la fecha de hoy" ya estaba corregido — el código compara **por solapamiento con el rango del registro** (`services/_periodo_utils.py:31-60`); (b) el `rol=None` que el call de costos pasaba también se cerró — `routers/costos_escrituras.py:39` pasa `u.get("rol")` y `costo_service.cargar_nomina` lo reenvía a `verificar_periodo_abierto`. Además el documento que originaba el hallazgo (la v1 de `Plan de trabajo`, en la raíz) **se borró al consolidar la doc**; el vigente es [`Plan de trabajo`](<Plan de trabajo>) v2. Se deja la entrada en vez de renumerar, para no romper las referencias a los ítems 1–5.
5. **`CLAUDE.md` dice que `docs/AUDITORIA_HR_KARSTEC.md` marca offboarding como hecho y que eso es falso** — confirmado: offboarding es el básico, y las columnas de entrevista de salida están muertas.

---

## 7. Cómo mantener este documento

- **Se actualiza al cerrar cada ítem**, no al final de una fase: se cambia el estado de esa fila, se reemplaza la evidencia por la del código nuevo y se vacía "Qué falta". Si el ítem se cerró de una forma distinta a la comprometida, además se agrega o se corrige su entrada en la sección 3.
- **La evidencia es siempre `archivo:línea` o el nombre del objeto de DB** (tabla, columna, endpoint). Nunca "según CLAUDE.md" ni "según el auto-reporte". Lo de base se verifica contra el catálogo real por MCP, no contra las migraciones.

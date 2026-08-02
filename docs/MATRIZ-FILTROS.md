# Matriz de filtros — inventario de la superficie de corte

**Fecha del relevamiento:** 27/7/2026 · **Método:** verificado contra el código, archivo:línea. No contra `CLAUDE.md`.

**Qué es:** el inventario completo de qué filtros existen hoy en cada módulo, en cuál de las
cuatro capas (repo → service → router → UI) vive cada uno, y si el export los acepta. Es la
base de las sesiones B2–B7: el objetivo de producto es que RRHH llegue a **cualquier corte de
información sin pedirle nada a desarrollo**, y este documento define qué falta para eso.

**Se actualiza al cerrar cada tanda de B.** Una matriz desactualizada hace que la tanda
siguiente se planifique sobre datos viejos.

## Cómo leer la matriz

- **empresa** no es un `Query` en casi ningún módulo: viaja por el header `X-Empresa-Id` y lo
  resuelve `AuthMiddleware`. Cuando la UI muestra un selector de empresa, lo que hace es mandar
  un override de ese header, no un parámetro. La única excepción es `areas`, que sí lo recibe
  como `Query`. Se anota igual porque para RRHH es un filtro más.
- **PARCIAL** = el filtro existe en una punta y no en la otra. Son los más baratos de cerrar.
- **`page`/`page_size`** no se cuentan como filtros.

---

## PARTE 1 — Inventario por módulo

### Empleados

| Filtro | Repo | Service | Router (Query) | UI | ¿Export? |
|---|---|---|---|---|---|
| empresa | `empleado_repo.py:30` | `empleado_service.py:70` | header | `useFiltrosEmpleados.ts:26-27` | ✅ |
| área | `empleado_repo.py:71` | ✅ | `empleados.py:25` `area_id` | `useFiltrosEmpleados.ts:58` | ✅ `:32` |
| estado | `empleado_repo.py:73` | ✅ | `empleados.py:25` `estado` | `useFiltrosEmpleados.ts:58` | ✅ |
| búsqueda (nombre) | `empleado_repo.py:77` (`.or_`) | ✅ | `empleados.py:25` `search` | `useFiltrosEmpleados.ts:59` | ✅ |
| es_lider | `empleado_repo.py:75` | ✅ | `empleados.py:25` `es_lider` | `useFiltrosEmpleados.ts` | ✅ |
| proyecto ‡ | `_scope_filtros.py::empleados_de_proyecto` | ✅ | `empleados.py` `proyecto_id` | `useFiltrosEmpleados.ts` | ✅ |

‡ **Filtro por proyecto (B4), en 4 módulos: empleados, vacaciones, ausencias y evaluaciones.**
Significa *"las filas de la gente asignada a ese proyecto"*. **Sin ventana temporal**: entran
todas las solicitudes del empleado, incluidas las anteriores a su asignación. La alternativa
(acotar a la ventana) hoy no se puede verificar — las 19 asignaciones tienen `fecha_desde` y
`fecha_hasta` en NULL. Disparador para revisarla: que empiecen a cargarse esas fechas.
⚠️ **Poco selectivo por diseño**: los 19 empleados están asignados a algún proyecto y uno solo
concentra 13.

> ✅ **`es_lider` cerrado** (tanda de PARCIALES): control "Liderazgo" en la barra de filtros.
> ⚠️ Hoy los 19 empleados tienen `es_lider = false`, así que "Solo líderes" devuelve 0. El
> filtro es correcto y el campo se setea desde la ficha; falta que RRHH marque a los líderes.

### Vacaciones

| Filtro | Repo | Service | Router (Query) | UI | ¿Export? |
|---|---|---|---|---|---|
| empresa | `vacaciones_repo.py:22` | `vacaciones_service.py:47` | header | `useFiltrosVacaciones.ts:61` | ✅ |
| área | *no llega al repo* † | `vacaciones_service.py:51` | `vacaciones.py:31` `area_id` | `useFiltrosVacaciones.ts:60+` | ✅ `:44` |
| empleado | `vacaciones_repo.py:24` (`.in_`) † | `vacaciones_service.py:51` | `vacaciones.py:32` `empleado_id` | ✅ | ✅ |
| estado | `_vacaciones_utils.py:9` `aplicar_filtro_estado` | `vacaciones_service.py:53` | `vacaciones.py:33` `estado` | ✅ | ✅ |

† **El área no es una columna de la tabla.** Se resuelve a una lista de `empleado_id` en
`_ownership_filter.resolver_empleado_ids` y llega al repo como un solo `.in_("empleado_id", ...)`.
Es el mismo canal por el que entra el ownership — ver Parte 3.

### Ausencias

| Filtro | Repo | Service | Router (Query) | UI | ¿Export? |
|---|---|---|---|---|---|
| empresa | `ausencias_repo.py:49` | `ausencias_service.py:39` | header | `useFiltrosAusencias.ts:58` | ✅ |
| área | *vía empleado_ids* † | `ausencias_service.py:41` | `ausencias.py:27` `area_id` | `useFiltrosAusencias.ts:61` | ✅ `:39` |
| empleado | `ausencias_repo.py:51` (`.in_`) † | `ausencias_service.py:41` | `ausencias.py:28` `empleado_id` | ✅ | ✅ |
| tipo | `ausencias_repo.py:53` | ✅ | `ausencias.py:29` `tipo_id` | ✅ | ✅ |

> **Falta estructural: no hay filtro por FECHA.** Ni en vacaciones ni en ausencias. Ver Parte 5.

### Capacitaciones — catálogo

| Filtro | Repo | Service | Router (Query) | UI | ¿Export? |
|---|---|---|---|---|---|
| empresa | `capacitacion_repo.py:29` | `capacitacion_service.py:24` | header | `CatalogoTab.tsx:77` | ❌ sin export |
| solo_activos | `capacitacion_repo.py:29` | ✅ | `capacitaciones.py:27` | `CatalogoTab.tsx:83` | — |

### Capacitaciones — asignaciones

| Filtro | Repo | Service | Router (Query) | UI | ¿Export? |
|---|---|---|---|---|---|
| empresa | `asignacion_repo.py:49` | `asignacion_service.py:31` | header | `AsignacionesTab.tsx:106` | ✅ |
| área | `asignacion_repo.py:40-42` (subquery a empleados) | ✅ | `asignaciones_capacitacion.py:24` | `AsignacionesTab.tsx:112` | ✅ |
| estado | `asignacion_repo.py:55` | ✅ | `:23` `estado` | `AsignacionesTab.tsx:117` | ✅ |
| empleado | `asignacion_repo.py:51` | ✅ | `:21` `empleado_id` | `useFiltrosAsignacionesCap.ts` | ✅ |
| capacitación | `asignacion_repo.py:53` | ✅ | `:22` `capacitacion_id` | `useFiltrosAsignacionesCap.ts` | ✅ |

### Inventario — ítems

| Filtro | Repo | Service | Router (Query) | UI | ¿Export? |
|---|---|---|---|---|---|
| empresa | `inventario_items_repo.py:47` | `inventario_items_service.py:26` | header | `ItemsTab.tsx:80` | ✅ |
| estado | `inventario_items_repo.py:49` | ✅ | `inventario_items.py:28` | `ItemsTab.tsx:85` | ✅ `:35` |

### Inventario — asignaciones

| Filtro | Repo | Service | Router (Query) | UI | ¿Export? |
|---|---|---|---|---|---|
| empresa | `inventario_asignaciones_repo.py` | `inventario_asignaciones_service.py` | header | `useFiltrosAsignacionesInv.ts` | ✅ |
| empleado | `inventario_asignaciones_repo.py` | ✅ | `inventario_asignaciones.py` | `useFiltrosAsignacionesInv.ts` | ✅ |
| área | `_area_scope.py::empleados_de_area` | ✅ | `inventario_asignaciones.py` `area_id` | `useFiltrosAsignacionesInv.ts` | ✅ |

> El área hereda la semántica de VIGENCIA del listado (`fecha_devolucion IS NULL`): son los
> ítems que esa área tiene HOY en su poder. **No se agregó a ÍTEMS a propósito**: un ítem sin
> asignar no tiene área, así que ese filtro excluiría en silencio todo el stock disponible.

### Objetivos

| Filtro | Repo | Service | Router (Query) | UI | ¿Export? |
|---|---|---|---|---|---|
| empresa | `objetivo_repo.py:47` | `objetivo_service.py:29` | header | `objetivos/page.tsx:90` | ✅ |
| estado | `objetivo_repo.py:48` | ✅ | `objetivos.py:30` | `objetivos/page.tsx:95` | ✅ `:50` |
| responsable | `objetivo_repo.py:49` | ✅ | `objetivos.py:31` | `objetivos/page.tsx:108` | ✅ |
| prioridad | `objetivo_repo.py:50` | ✅ | `objetivos.py:32` | `objetivos/page.tsx:101` | ✅ |

> Módulo **completo y coherente en las 4 capas**. Es el mejor ejemplo del repo junto con auditoría.
> `responsable_id` apunta a `users`, no a `empleados` (limitación de modelo ya documentada).

### Proyectos

| Filtro | Repo | Service | Router (Query) | UI | ¿Export? |
|---|---|---|---|---|---|
| empresa | `proyectos_repo.py` | `proyectos_service.py` | header | `useFiltrosProyectos.ts` | ❌ sin export |
| estado | `proyectos_repo.py` | ✅ | `proyectos.py` | `useFiltrosProyectos.ts` | — |
| área † | `_area_scope.py::proyecto_ids_con_area` | ✅ | `proyectos.py` `area_id` | `useFiltrosProyectos.ts` | — |

† **`proyectos` NO tiene columna de área.** El filtro significa *"proyectos con al menos un
empleado asignado de esa área"*, contando asignaciones **activas e inactivas**. Dos
consecuencias que parecen bugs y no lo son: un proyecto **sin nadie asignado no aparece bajo
ninguna área**, y la resolución de empleados **no se acota por empresa** (un proyecto de A
puede tener gente de B — acotar devolvería cero en silencio). La semántica completa está en
`repositories/_area_scope.py`, que es donde hay que leerla antes de cambiarla.

### Horas de proyecto

| Filtro | Repo | Service | Router (Query) | UI | ¿Export? |
|---|---|---|---|---|---|
| — | `horas_repo.py:49` acepta **solo** `proyecto_id` + paginación | — | `proyecto_horas.py:26-27` solo `page`/`page_size` | — | ❌ sin export |

> **Cero filtros.** No hay corte por fecha, empleado, área ni empresa. Es el módulo de costeo,
> y hoy no permite ningún análisis. Ver Parte 5.

### Evaluaciones — resultados (evaluados de un lote)

| Filtro | Repo | Service | Router (Query) | UI | ¿Export? |
|---|---|---|---|---|---|
| sector | *en Python* | `evaluacion_reportes_service.py:41` | `evaluaciones_resultados.py:58` | `useFiltrosEvaluadosResultados.ts:22` | ✅ `:68` |
| perfil | *en Python* | ✅ | `:58` | `:26` | ✅ |
| con_nota | *en Python* | ✅ | `:59` | `:30` | ✅ |

> 🔴 **Desde B4 el panel tiene filtros de los DOS tipos.** `proyecto_id` es **server-side**
> (resolver quién trabaja en el proyecto necesita la base) y obliga a re-traer al cambiarlo;
> `sector`/`perfil`/`con_nota` siguen aplicándose sobre el array ya traído. Está anotado en el
> hook y en el panel. La duplicación de abajo sigue vigente y ahora convive con un filtro que
> NO puede duplicarse — cuando se unifique, el corte natural es llevar los tres al backend.
>
> 🔴 **El listado filtra CLIENT-side y el export server-side.** `useFiltrosEvaluadosResultados.ts:35-40`
> aplica los tres filtros con un `useMemo` sobre el array ya traído; el export manda los mismos
> valores como `Query`. Dos implementaciones de la misma regla. Aceptable al volumen actual
> (~30 filas por lote) pero es duplicación con riesgo de divergencia.
> El listado de **lotes** (`evaluaciones_resultados.py:25`) no tiene ningún filtro.

### Evaluaciones — instancias (`ev_*`)

| Filtro | Repo | Service | Router (Query) | UI | ¿Export? |
|---|---|---|---|---|---|
| empresa | `ev_instancias_repo.py:61` | `ev_instancias_service.py:44` | header | — | ✅ |
| ciclo | `ev_instancias_repo.py:61` | ✅ | `ev_instancias.py:27` | — | ✅ `:39` |
| estado | `ev_instancias_repo.py:61` | ✅ | `ev_instancias.py:28` | — | ✅ `:40` |

> 🔴 **Backend completo, CERO frontend.** Verificado: no existe ningún archivo `.ts`/`.tsx` que
> llame a `/api/evaluaciones/instancias`, `/ciclos` o `/plantillas`. La UI de `ev_*` se borró y
> las tablas están vacías en producción. **No invertir en filtros acá** — el módulo vivo es
> "resultados importados". Se limpia tras el cutover a AWS.

### Costos / nómina

| Filtro | Repo | Service | Router (Query) | UI | ¿Export? |
|---|---|---|---|---|---|
| empresa | `nomina_repo.py:24` | `costo_service.py:33` | header | ✅ (en la página) | ✅ |
| mes | `nomina_repo.py:24` | ✅ | `costos.py:30,40,49` **obligatorio** | ✅ | ✅ |
| año | `nomina_repo.py:24` | ✅ | `costos.py:31,41,50` **obligatorio** | ✅ | ✅ |

> ✅ **Export agregado (bloque C).** `GET /api/costos/nomina/exportar` acepta exactamente los
> mismos Query que el listado; el front arma los params con la misma función
> (`queryNomina` en `services/costos.ts`), así que un filtro nuevo no puede quedar en uno solo
> de los dos. Cubierto por los dos barridos estructurales (paridad y tope de filas).
>
> **Sigue sin área, sin empleado y sin rango de períodos.** Solo un mes puntual, y obligatorio:
> no se puede pedir "todo el año" ni "de marzo a junio".

### Presupuesto

| Filtro | Repo | Service | Router (Query) | UI | ¿Export? |
|---|---|---|---|---|---|
| empresa + mes + año | `presupuesto_repo.py:59` | `costo_service.py:125` | — | — | — |

> **No hay endpoint de listado de presupuestos.** Solo `POST /api/costos/presupuesto` para
> cargarlos, y una lectura interna que consume el dashboard de costos. No se puede listar ni
> exportar el presupuesto cargado.

### Onboarding

| Filtro | Repo | Service | Router (Query) | UI | ¿Export? |
|---|---|---|---|---|---|
| empresa | `onboarding_repo.py:50` | ✅ | header | ✅ | ❌ sin export |

> Solo trae **instancias activas** (`find_instancias_activas`). No hay filtro por estado, por
> empleado, por template ni por fecha, y no hay forma de ver las cerradas.

### Onboarding · plantillas

| Filtro | Repo | Service | Router (Query) | UI | ¿Export? |
|---|---|---|---|---|---|
| empresa | `_onboarding_templates_row.py::with_empresa` | ✅ | header | ✅ (sidebar) | ❌ sin export |
| visibilidad | `_onboarding_templates_row.py::with_visibilidad` | ✅ | — (sale del token) | ❌ **no hay control** | ❌ sin export |

> La **visibilidad pública/privada** (C6, migración 082) filtra server-side en el WHERE y se
> compone por intersección con la empresa. NO es un filtro elegible por el usuario: sale de
> quién sos (`user_id` + `rol`), no de un `Query`. Por eso figura acá pero sin control de UI.
>
> 🔴 **PENDIENTE, y es trabajo propio: el listado de plantillas no tiene NINGUNA barra de
> filtros.** Agregar "ver solo las mías / solo las compartidas" no es sumar un campo — hay que
> crear el hook `useFiltrosTemplates` y montar `FiltersBar` desde cero, que es fundación. Se
> dejó afuera de C6 a propósito. Si RRHH lo pide, entra como una tanda del bloque B con el
> molde de `components/features/shared/filtros.ts`.

### Offboarding

| Filtro | Repo | Service | Router (Query) | UI | ¿Export? |
|---|---|---|---|---|---|
| empresa | `offboarding_repo.py:57` | ✅ | header | ✅ | ❌ sin export |

> Mismo caso: `find_activos`, sin filtros y sin acceso al histórico. **Esto es el que alimenta
> el reporte de rotación**, así que la falta de corte por motivo/fecha se paga dos veces.

### Áreas

| Filtro | Repo | Service | Router (Query) | UI | ¿Export? |
|---|---|---|---|---|---|
| empresa | `area_repo.py:43` | ✅ | `areas.py:31` `empresa_id` (**Query**, no header) | ✅ | ❌ sin export |
| búsqueda | ❌ | ❌ | ❌ | `areas/page.tsx:63` **client-side** | — |

> Único módulo donde `empresa_id` es `Query` y no header. La búsqueda por nombre existe solo en
> el cliente, sobre el array ya traído.

### Vacantes

| Filtro | Repo | Service | Router (Query) | UI | ¿Export? |
|---|---|---|---|---|---|
| empresa | `vacante_repo.py:32` | `vacante_service.py` | header | `vacantes/page.tsx:128` | ❌ sin export |
| estado | `vacante_repo.py:32` | ✅ | `vacantes.py:25` | `vacantes/page.tsx:140` | — |

### Candidatos

| Filtro | Repo | Service | Router (Query) | UI | ¿Export? |
|---|---|---|---|---|---|
| empresa | `candidato_repo.py:39` | `candidato_service.py` | header | — | ❌ sin export |

> Sin filtro por etapa, por vacante ni por fecha, pese a que el pipeline **tiene** etapas.

### Auditoría

| Filtro | Repo | Service | Router (Query) | UI | ¿Export? |
|---|---|---|---|---|---|
| empresa | `audit_repo.py:79` | `audit_service.py:72` | header | — | ✅ |
| usuario | `audit_repo.py:81` | ✅ | `auditoria.py:29,55` | `AuditFilters.tsx:45` | ✅ |
| entidad | `audit_repo.py:83` | ✅ | `auditoria.py:30,56` | `AuditFilters.tsx:25` | ✅ |
| evento | `audit_repo.py:87` | ✅ | `auditoria.py:31,57` | `AuditFilters.tsx:35` | ✅ |
| registro_id | `audit_repo.py:85` | ✅ | `auditoria.py:32,58` | ❌ **PARCIAL** | ✅ |
| fecha_desde | `audit_repo.py:89` (`.gte`) | ✅ | `auditoria.py:33,59` | `AuditFilters.tsx:55` | ✅ |
| fecha_hasta | `audit_repo.py:91` (`.lte`) | ✅ | `auditoria.py:34,60` | `AuditFilters.tsx:60` | ✅ |

> El módulo con más filtros del repo. ✅ **Export agregado (bloque C):**
> `GET /api/auditoria/exportar` acepta **los seis**, con la misma función de query que el
> listado (`queryAuditoria` en `services/auditoria.ts`). `registro_id` sigue siendo PARCIAL en
> la UI —existe en backend y no tiene control— pero eso ahora vale para listado Y export por
> igual, que es la invariante.
>
> ⚠️ **No confundir con el reporte de auditoría** (`services/reportes/_reporte_auditoria.py`),
> que es otra cosa: un reporte del catálogo de Fase 1, acotado a un mes y con truncado
> declarado. Este export sale con los filtros de la pantalla y falla ruidoso si no entra.

### Períodos · Cesiones · Usuarios

| Módulo | Filtros | Evidencia |
|---|---|---|
| Períodos | solo empresa | `periodo_repo.py:33` · `periodos.py:20` sin `Query` |
| Cesiones | solo por empleado (no es listado global) | `cesion_repo.py:29` · `cesiones.py:22` |
| Usuarios | ninguno; `activo=True` fijo, query inline en el router | `usuarios.py:30-36` |

---

## PARTE 1.b — Tope de filas del export (B7)

Todos los exports de listado verifican el total **antes** de armar el archivo, contra la
constante única `services/_limite_export.LIMITE_FILAS_EXPORT` (**5.000**). Si lo supera,
devuelven `EXPORT_DEMASIADAS_FILAS` (422) con un mensaje que dice cuántas filas hay, cuál es el
máximo y que use los filtros — **no entregan un archivo cortado**.

**El techo real no es la cantidad de filas, es el tiempo**: 30 s del cliente httpx de Supabase
(el más bajo), posiblemente 8 s de `statement_timeout`, y el límite de Vercel. El
`page_size=100000` anterior nunca se alcanzaba: el corte llegaba por timeout, sin mensaje.

**Dos excepciones declaradas**, ambas en `tests/test_limite_export.py::_SIN_CHEQUEO`:
- `reporte_export_service` — exporta un reporte puntual por id, no un listado.
- `_reporte_auditoria` — ya está acotado a un mes y la pantalla no ofrece otro filtro con el que
  angostarlo; fallar dejaría al usuario sin forma de obtener la auditoría de un mes cargado.
  Conserva su **truncado declarado** (nota dentro del archivo diciendo cuántas quedaron afuera).

⚠️ **Alcance parcial en 5 módulos.** En los paginados (empleados, vacaciones, ausencias) el
total llega por `count="exact"` y solo se traen las filas del tope: el control actúa antes de
cargar nada grande. En capacitaciones, inventario ×2, objetivos y ev_instancias los repos no
exponen conteo y sus archivos están en o cerca de su límite, así que el chequeo corre sobre la
lista ya traída — **igual que antes**, sin regresión, pero un volumen que muera por timeout
muere antes de llegar al chequeo. Cerrarlo pide un `contar()` por repo: tanda propia.

## PARTE 2 — El invariante list ↔ export

> **Invariante del repo:** *"el endpoint de export acepta los mismos Query que el list"*.

**En el BACKEND el invariante se cumple en los 7 módulos con export.** Verificado par por par:

| Módulo | List | Export | ¿Igual? |
|---|---|---|---|
| Empleados | `area_id, estado, search, es_lider` | idem (`empleados.py:32`) | ✅ |
| Vacaciones | `area_id, empleado_id, estado` | idem (`vacaciones.py:44`) | ✅ |
| Ausencias | `area_id, empleado_id, tipo_id` | idem (`ausencias.py:39`) | ✅ |
| Capacitaciones/asig. | `empleado_id, capacitacion_id, estado, area_id` | idem (`asignaciones_capacitacion.py:32`) | ✅ |
| Inventario ítems | `estado` | idem (`inventario_items.py:35`) | ✅ |
| Inventario asig. | `empleado_id` | idem (`inventario_asignaciones.py:49`) | ✅ |
| Ev. resultados | `sector, perfil, con_nota` | idem (`evaluaciones_resultados.py:67-69`) | ✅ |
| Ev. instancias | `ciclo_id, estado` | idem (`ev_instancias.py:39-40`) | ✅ |

**🔴 Pero el invariante SÍ está roto en el FRONTEND, en dos módulos.** El backend acepta los
parámetros y el wrapper de JS nunca se los manda, así que el usuario filtra la pantalla, exporta,
y **recibe un archivo con más filas de las que estaba viendo**:

| Módulo | Wrapper | Lo que no pasa |
|---|---|---|
| Capacitaciones | `services/capacitaciones.ts:99` | `empleado_id`, `capacitacion_id` |
| Inventario asig. | `services/inventario.ts:15` | `empleado_id` |

Hoy el síntoma está **enmascarado**: como esos dos filtros tampoco tienen control en la UI
(ver PARCIALES en la Parte 1), nadie puede activarlos. **En el momento en que se agregue el
control, el export miente** — salvo que se arregle el wrapper en la misma sesión.

> 🕓 **CANDIDATO ANOTADO — filtro por provincia / localidad en empleados.** La migración 081
> (C4) desglosó el domicilio en seis columnas, dos de ellas pensadas para agrupar
> (`domicilio_provincia`, con lista cerrada de 24 valores, y `domicilio_localidad`), y las dejó
> indexadas. **El filtro NO se construyó**: Bloque B está cerrado y con 0 domicilios cargados no
> filtraría nada. Cuando RRHH cargue domicilios, es el corte más barato que queda — el índice ya
> está, las dos columnas ya salen en el export de empleados, y el patrón de filtros del módulo
> ya existe.

**Módulos con listado y sin export (9 → 7):** ~~auditoría~~ · proyectos · horas de proyecto ·
~~costos/nómina~~ · presupuesto · onboarding · offboarding · áreas · vacantes · candidatos ·
períodos.
*(auditoría y costos/nómina salieron de esta lista en el bloque C.)*

---

## PARTE 3 — Ownership

**Solo VACACIONES y AUSENCIAS componen ownership**, y es correcto que sea así: `mandos_medios`
solo tiene esas dos secciones (`MANDOS_MEDIOS_SECCIONES`). En el resto llegan únicamente
`admin_rrhh` y `gerencia_lectura`, para quienes no restringe — agregarlo ahí sería código muerto
que aparenta seguridad.

**La composición es por INTERSECCIÓN. Verificado en el código, no asumido:**

`_ownership_filter.py:55` — `inter = [i for i in visibles if i in set(area_ids)]`, con el
comentario explícito *"intersección ownership ∩ área (nunca la unión)"*. Y el caso borde está
resuelto en la dirección correcta: `:56` devuelve `(None, True)` = **vacío** cuando la
intersección queda sin elementos, en vez de caer a "sin filtro".

`resolver_empleado_ids` (`:59-80`) agrega el tercer eje —empleado puntual— con la misma
semántica: `:78-79`, un `empleado_id` **fuera** del alcance del mando da vacío, no el empleado.

**Ningún filtro reemplaza al ownership.** Los tres ejes (ownership, área, empleado) confluyen en
una sola lista que llega al repo como un único `.in_("empleado_id", ...)`
(`vacaciones_repo.py:24`, `ausencias_repo.py:51`).

⚠️ **Consecuencia para B2–B7:** todo filtro nuevo de vacaciones/ausencias que acote *empleados*
tiene que entrar por `_ownership_filter`, no por un `.eq()` nuevo en el repo. Un filtro que
esquive ese canal rompe el ownership en silencio.

Otros consumidores de la capa base (`ids_empleados_visibles`), sin filtros de listado:
`equipo_service.py:47`, `dashboard_equipo_service.py:52`.

---

## PARTE 4 — El patrón actual

### `FiltersBar` vs barra propia

| | Módulos |
|---|---|
| **Usan `FiltersBar`** (4) | empleados, vacaciones, ausencias, evaluaciones/resultados |
| **Barra propia** (9+) | objetivos, vacantes, proyectos, capacitaciones ×2, inventario ×2, áreas, auditoría |

La barra propia **duplica literalmente el mismo `FIELD_CLASS`** (`AuditFilters.tsx:11-13`,
`ItemsTab.tsx`, `objetivos/page.tsx`, …). Es copia-pega de estilo, no una necesidad de diseño.

### `useFiltros<Modulo>` vs estado suelto

| | Módulos |
|---|---|
| **Hook dedicado** (4) | `useFiltrosEmpleados` (72) · `useFiltrosVacaciones` (76) · `useFiltrosAusencias` (74) · `useFiltrosEvaluadosResultados` (44) |
| **Estado suelto en la página/tab** (9+) | objetivos, vacantes, proyectos, ItemsTab, AsignacionesTab ×2, CatalogoTab, áreas, auditoría |

Los tres primeros hooks son **casi idénticos**: los tres cargan empresas y áreas, los tres
manejan `empresaActivaId`, los tres arman `campos: FiltroCampo[]`. Hay ~40 líneas repetidas
tres veces. Esa duplicación es el candidato #1 de refactor de la fundación (Tanda 0).

### Tipos de control: los que hay y los que faltan

`FiltersBar.tsx:10-14` soporta **tres**: `select` · `search` · `date`.

Faltan, en orden de cuántos cortes destraban:

1. **Rango de fechas** (`daterange`) — hoy se arma con dos `date` sueltos (auditoría lo hace a
   mano). Es el control que más módulos necesitan y ninguno tiene bien.
2. **Multi-select** — "estas 3 áreas", "estos 2 estados". Hoy todo filtro es de valor único, así
   que cualquier corte de más de un valor obliga a exportar todo y filtrar en Excel.
3. **Autocompletado / combobox** — el selector de empleado ya trae la lista completa
   (`fetchEmpleadosSeleccionables`). Con 19 empleados un `<select>` alcanza; con 200 deja de
   servir. Es deuda diferida, no urgente.
4. **Rango numérico** — para montos de nómina y presupuesto. Solo aplica a costos.

### Qué es generalizable de Auditoría

Auditoría es el precedente más rico (5 controles → 6 `Query` + paginación → 7 `.eq/.gte/.lte`).
Lo que conviene copiar:

- ✅ **El objeto de filtros único.** `AuditFilters.tsx:17-19`: un solo `set(campo, valor)` que
  hace `onChange({...filtros, [campo]: valor || undefined})`. Un objeto tipado
  (`AuditoriaFiltros`) que viaja entero de la UI al service. **Es exactamente el fix que ya se
  aplicó a `fetchEmpleados` en Fase 3** y el que falta en `vacaciones.ts`/`ausencias.ts`.
- ✅ **El `valor || undefined`**: normaliza `""` a "sin filtro" en un solo lugar.
- ✅ **Los catálogos de labels desacoplados** (`ENTIDAD_LABEL`, `EVENTO_LABEL`): la UI no
  hardcodea los valores del backend.
- ✅ **El repo aplica cada filtro con un `if` plano** (`audit_repo.py:79-91`), sin ramas. Suma un
  filtro = suma una línea.
- ❌ **No copiar**: la barra a mano (debería ser `FiltersBar`) y la ausencia de export.

---

## PARTE 5 — Filtros faltantes de alto valor

Mi lectura, ordenada por **valor / esfuerzo**. El criterio es cuántos cortes destraba y cuántos
"exportar todo y filtrar en Excel" elimina.

### Alto valor / bajo esfuerzo

1. **Rango de fechas en vacaciones y ausencias.** Es la ausencia más grave de todo el inventario:
   los dos módulos de uso diario **no se pueden acotar por período**. Cualquier pregunta de RRHH
   ("ausencias del último trimestre", "vacaciones tomadas en enero") obliga hoy a exportar todo.
   El repo ya tiene el molde: `.gte`/`.lte` en `audit_repo.py:89-91`. **Habilita además el
   cálculo de ausentismo por período arbitrario**, que hoy está clavado al mes.
2. **Cerrar los 6 PARCIALES.** Ya están implementados en backend; solo falta el control en la UI
   (y el wrapper de export en 2 de ellos). Costo casi nulo:
   `es_lider` (empleados) · `solo_activos` (catálogo capacitaciones) · `empleado` y `capacitación`
   (asignaciones capacitaciones) · `empleado` (inventario asignaciones) · `registro_id` (auditoría).
3. **Export de auditoría.** Tiene 6 filtros y ningún export: es el módulo donde el trabajo de
   filtrado ya está hecho y no se puede llevar el resultado. El motor `build_export` es genérico.
4. **Filtro de empresa en proyectos.** El repo y el service ya lo aceptan
   (`proyectos_repo.py:45`); falta el selector, que existe en casi todas las demás pantallas.

### Alto valor / esfuerzo medio

5. **Rango de períodos en costos.** Hoy `mes` y `anio` son **obligatorios y puntuales**
   (`costos.py:30-31`): no se puede pedir un semestre ni un año. Es lo que bloquea el análisis de
   evolución de masa salarial, que es de las primeras cosas que va a pedir gerencia.
6. **Área y empleado en costos/nómina.** El listado de nómina no se puede cortar por área — el
   corte más natural para un análisis de costos. Requiere join a `empleados` (el patrón ya
   existe en `asignacion_repo.py:40-42`).
7. **Filtros en horas de proyecto** (fecha trabajada, empleado, área). Cero filtros hoy. Es el
   módulo de **costeo**: sin cortes no hay análisis posible. Menor prioridad solo porque los
   datos todavía no se cargan.
8. **Histórico + estado en onboarding y offboarding.** Los dos traen solo activos, así que el
   histórico es inalcanzable desde la UI. **Offboarding alimenta el reporte de rotación**, así
   que la falta de corte por motivo y fecha se paga dos veces.

### Valor medio

9. **Etapa y vacante en candidatos.** El pipeline tiene etapas y no se puede filtrar por ellas.
10. **Multi-select en área y estado**, transversal. Convierte "un corte por vez" en "el corte que
    quieras". Depende de la Tanda 0.
11. **Export en vacantes, candidatos, proyectos, onboarding, offboarding.**

### Lo que NO recomiendo hacer

- **Filtros en `ev_*`** (instancias/ciclos/plantillas): backend vivo, **cero frontend**, tablas
  vacías, borrado tras el cutover. Sería trabajo tirado.
- **Filtros en assessment**: módulo apagado por flag (`ASSESSMENT_ENABLED=false`).

---

## PARTE 6 — Costo de líneas

### Backend — sin margen (el próximo filtro exige dividir primero)

**Routers (límite 80):**

| Archivo | Líneas | Necesario para |
|---|---|---|
| `routers/vacaciones.py` | **80/80** 🔴 | rango de fechas |
| `routers/vacantes.py` | **80/80** 🔴 | export |
| `routers/evaluaciones_resultados.py` | **80/80** 🔴 | franja export (deuda de A2) |
| `routers/adjuntos.py` | **80/80** 🔴 | — |
| `routers/asignaciones_capacitacion.py` | 79 | — |
| `routers/inventario_items.py` | 79 | franja export (deuda de A2) |
| `routers/objetivos.py` | 79 | franja export (deuda de A2) |
| `routers/assessment.py` | 78 | — |
| `routers/integraciones.py` | 77 · `routers/usuarios.py` 77 · `routers/ev_instancias.py` 76 | — |

**Services (límite 150):**

| Archivo | Líneas | Necesario para |
|---|---|---|
| `services/vacaciones_service.py` | **150/150** 🔴 | rango de fechas |
| `services/costo_service.py` | **150/150** 🔴 | área/empleado/rango en costos |
| `services/assessment_service.py` | **150/150** 🔴 | — |
| `services/gmail_service.py` | **150/150** 🔴 | — |
| `services/adjunto_service.py` 149 · `usuario_service.py` 149 · `vacante_service.py` 149 | | |
| `services/ev_instancias_service.py` 146 · `evaluacion_service.py` 145 · `reporte_service.py` 143 · `sucesion_service.py` 143 | | |
| **Ya over-limit:** `_audit_payloads_rrhh.py` 189 · `reporte_anual.py` 154 | 🔴 | deuda previa |

> `services/ausencias_service.py` está en **74/150** — tiene margen de sobra (se dividió en Fase 2).
> Es la asimetría a tener en cuenta: **ausencias puede absorber filtros nuevos, vacaciones no.**

**Repos (límite 100):**

| Archivo | Líneas | Necesario para |
|---|---|---|
| `repositories/empleado_repo.py` | **174** 🔴 | ya over-limit |
| ✅ ~~`ev_instancias_repo.py` 146 · `assessment_repo.py` 130 · `costo_repo.py` 135~~ | ✅ | **CERRADO 2/8/2026**: el primero se partió (→98), los otros dos se borraron por 0 callers. Ver `docs/DEUDA-TECNICA.md` |
| `repositories/nomina_repo.py` | **107** 🔴 | filtros de costos |
| `repositories/proyectos_repo.py` | **104** 🔴 | filtros de proyectos |
| `repositories/onboarding_repo.py` 100 · `evaluacion_repo.py` 100 | al límite | histórico de onboarding |
| `objetivo_repo.py` 99 · `offboarding_repo.py` 99 · `empresa_repo.py` 98 · `inventario_items_repo.py` 98 · `vacante_repo.py` 98 · `area_repo.py` 97 · `asignacion_repo.py` 97 · `vacaciones_repo.py` 97 | sin margen | |
| `audit_repo.py` 93 · `ausencias_repo.py` 93 | 7 líneas de margen | rango de fechas |

**Corte propuesto para `vacaciones_service.py`** (ya identificado en `CLAUDE.md`, sigue vigente):
extraer `create` a **`services/_vacaciones_write.py`**, simétrico con el `_ausencias_write.py`
que ya existe (110 líneas). Baja el service a ~110 y le devuelve 40 líneas de margen.

### Frontend — sin margen (límite 150)

| Archivo | Líneas | Necesario para |
|---|---|---|
| `costos/page.tsx` | **618** 🔴 | filtros de costos |
| `onboarding/page.tsx` 410 · `offboarding/page.tsx` 292 | 🔴 | histórico + estado |
| `areas/page.tsx` 261 · `vacantes/page.tsx` 217 | 🔴 | export, búsqueda server-side |
| `capacitaciones/AsignacionesTab.tsx` | **211** 🔴 | cerrar 2 PARCIALES |
| `capacitaciones/CatalogoTab.tsx` 153 · `inventario/ItemsTab.tsx` 152 | 🔴 | cerrar PARCIALES |
| `objetivos/page.tsx` 149 · `vacaciones/page.tsx` 148 · `ausencias/page.tsx` 141 | sin margen | rango de fechas |

> `vacaciones/page.tsx` (148) y `ausencias/page.tsx` (141) están **dentro** del límite pero con
> 2 y 9 líneas de margen. Sumar UN filtro más exige extraer la barra a componente propio primero —
> exactamente lo que ya avisaba el playbook de `CLAUDE.md`, y sigue siendo cierto.

---

## Propuesta de tandas para B3–B6

Agrupadas por **fundación compartida** y por **archivos en común**, no por módulo.

### Tanda 0 — Fundación (2 sesiones) · **bloquea todo lo demás**

**Qué:**
1. `FiltersBar` gana `daterange` y `multiselect`. Es el cuello de botella de casi todos los
   filtros de valor de la Parte 5.
2. Se extrae el hook común de los tres `useFiltros*` (empresa + áreas + `empresaActivaId`,
   ~40 líneas repetidas ×3) a `useFiltrosBase`.
3. **`services/vacaciones.ts` y `ausencias.ts` pasan a objeto de opciones.** Hoy son posicionales
   y están *corridas una posición entre sí* (el export lleva `formato` adelante); copiar un
   filtro de una a la otra desplaza todo y `tsc` lo acepta. **Hacerlo antes de sumar filtros, no
   después** — es la deuda que el `CLAUDE.md` marca en rojo.
4. Se arreglan los **2 wrappers de export rotos** (capacitaciones, inventario asignaciones) antes
   de que la Tanda 1 exponga los controles y el export empiece a mentir.

**División previa:** ninguna. **Por qué primero:** las tandas 1–4 la usan entera.

### Tanda 1 — Cerrar los PARCIALES (1 sesión) · sin fundación

Los 6 filtros que ya existen en backend y solo necesitan control en la UI: `es_lider`,
`solo_activos`, `empleado` + `capacitación` (capacitaciones), `empleado` (inventario),
`registro_id` (auditoría). **La mejor relación valor/esfuerzo del bloque.**

**División previa:** `capacitaciones/AsignacionesTab.tsx` (211) y `CatalogoTab.tsx` (153) hay que
dividirlos antes — sumarles controles los empuja más lejos del límite.
**Depende de:** el punto 4 de la Tanda 0 (los wrappers de export), que se puede adelantar acá.

### Tanda 2 — Fechas en vacaciones y ausencias (2 sesiones) · **la de más valor**

Rango de fechas end-to-end en los dos módulos de uso diario. Comparten `_ownership_filter`,
comparten el patrón de `useFiltros*`, comparten el molde de `.gte`/`.lte`. **Van juntas o se
hace dos veces el mismo trabajo.**

**División previa obligatoria (3 archivos):**
- `services/vacaciones_service.py` 150/150 → extraer `create` a `_vacaciones_write.py`
- `routers/vacaciones.py` 80/80 → dividir
- `vacaciones/page.tsx` 148 y `ausencias/page.tsx` 141 → extraer la barra de filtros

**Depende de:** Tanda 0 (control `daterange` + objeto de opciones).
⚠️ Todo filtro que acote empleados entra por `_ownership_filter`, nunca por un `.eq()` nuevo.

### Tanda 3 — Costos y períodos (2 sesiones)

Rango de meses (en vez de mes puntual obligatorio) + área + empleado en nómina. Es lo que
destraba el análisis de evolución de masa salarial. Todo cae en los mismos archivos, por eso va
junto.

**División previa obligatoria:** `costos/page.tsx` **618** (la página más grande del repo, hay que
dividirla sí o sí) · `services/costo_service.py` 150/150 · `repositories/nomina_repo.py` 107 (ya
over-limit).
**Depende de:** Tanda 0 (`daterange`).

### Tanda 4 — Exports faltantes (1 sesión)

Auditoría (la prioritaria: 6 filtros y ningún export), vacantes, proyectos. El motor
`build_export` es genérico; el trabajo es un `construir_filas_export` por módulo + el endpoint.

**División previa:** `routers/vacantes.py` 80/80.
**Depende de:** nada. Se puede hacer en paralelo con cualquier otra.

### Tanda 5 — Ciclo de vida: onboarding, offboarding, candidatos (2 sesiones)

Histórico + estado + fechas en onboarding/offboarding; etapa + vacante en candidatos. Los tres
comparten la forma "hoy solo se ven los activos". Offboarding alimenta el reporte de rotación,
así que esta tanda desbloquea también ese reporte.

**División previa obligatoria:** `onboarding/page.tsx` 410 · `offboarding/page.tsx` 292.
**Depende de:** Tanda 0 (`daterange`).

### Fuera del bloque B

- **Horas de proyecto** (cero filtros): tiene sentido recién cuando se carguen datos.
- **`ev_*`** y **assessment**: no invertir. Módulos sin UI / apagados.

### Resumen

| Tanda | Sesiones | Depende de | División previa |
|---|---|---|---|
| 0 · Fundación | 2 | — | ninguna |
| 1 · PARCIALES | 1 | T0 (parcial) | 2 tabs de capacitaciones |
| 2 · Fechas vac/aus | 2 | T0 | 3 archivos (2 🔴 al límite) |
| 3 · Costos | 2 | T0 | 3 archivos (1 de 618 líneas) |
| 4 · Exports | 1 | — | 1 router |
| 5 · Ciclo de vida | 2 | T0 | 2 páginas grandes |
| **Total** | **10** | | |

> Son 10 sesiones contra las 9 previstas para B2–B7, y **casi la mitad del esfuerzo es división
> de archivos, no filtros**. Vale decidir de entrada si las divisiones van como commits propios
> dentro de cada tanda (recomendado, y consistente con cómo se manejó A4) o como una tanda de
> saneamiento previa.

---

## Correcciones al relevamiento original (27/7/2026, tanda de PARCIALES)

Al verificar los PARCIALES contra el código aparecieron **dos errores de este documento**:

-1. **Tanda de proyecto (B4), 27/7/2026.** Filtro por proyecto en empleados, vacaciones,
   ausencias y evaluaciones. `_area_scope.py` se renombró a **`_scope_filtros.py`** (el nombre
   ya mentía). `_ownership_filter` pasó a componer **tres** ejes (ownership ∩ área ∩ proyecto)
   con un fold, manteniendo el fail-closed por eje. Divisiones previas: `empleado_repo.py`
   174→98 (+ `_empleado_row.py` + `_empleado_write_repo.py`) y
   `routers/evaluaciones_resultados.py` 80→69 (+ `_export.py`, que al fin recibió su franja de
   rate limiting, pendiente desde A2).

0. **Tanda de área (proyectos + inventario), 27/7/2026.** Cerró el PARCIAL de empresa en
   proyectos y sumó área en los dos módulos. Divisiones previas: `proyectos_repo.py` 104→74
   (+ `_proyectos_enrich.py`), `proyectos/page.tsx` 156→70 (+ `ProyectosGrid` + hook),
   `inventario/AsignacionesTab.tsx` 150→62 (+ tabla + hook). Se extrajo además `etiquetaArea`
   a `components/features/shared/filtros.ts`: estaba **triplicada** en los hooks de vacaciones,
   ausencias y empleados.

1. **`solo_activos` NO era un PARCIAL.** `CatalogoTab.tsx:83` ya tenía el checkbox "Solo
   activos", cableado a `fetchCapacitaciones`. Falso positivo del relevamiento.
2. **`ItemsTab.tsx` (152) no estaba involucrado.** El parcial de inventario era `empleado_id`,
   que vive en `inventario/AsignacionesTab.tsx` (126, con margen). `ItemsTab` está over-limit
   por deuda general, no por esta tanda.

Y una decisión de alcance: **`registro_id` de auditoría se sacó de la tanda.** Es un UUID; como
control de UI implicaría pedirle a alguien que lo pegue a mano. Ya está cableado punta a punta
en el front (`services/auditoria.ts:25`) y **ninguna pantalla linkea a `/auditoria`**: lo que
falta no es el control sino el punto de entrada. La feature real es un botón "ver auditoría de
este registro" que navegue a `/auditoria?registro_id=<id>` + leer el query param al montar.
**Agendada aparte.**

## Lo que NO pude determinar

- **Si los filtros existentes se usan.** No hay telemetría; el orden de la Parte 5 es mi lectura
  del valor para RRHH, no evidencia de uso.
- **El volumen real de datos.** Con 19 empleados y casi todo lo demás vacío en producción, no se
  puede saber qué filtros se vuelven lentos ni cuáles empiezan a necesitar autocompletado en vez
  de `<select>`.
- **Qué cortes pide RRHH efectivamente.** La Parte 5 razona desde el modelo de datos y desde qué
  reportes existen. Conviene contrastarla con ellos antes de fijar el orden de las tandas.

---

## Addendum 2/8/2026 — filtro por familia de tipos de ausencia (mig 088)

Los tipos de ausencia pasaron a tener **dos niveles** (`padre_id`). El filtro por tipo del módulo
de ausencias cambió de comportamiento:

| Capa | Antes | Ahora |
|---|---|---|
| repo | `.eq("tipo_id", X)` | `.in_("tipo_id", [X, *hijos])` |
| service | pasaba el id tal cual | resuelve la familia con `TiposAusenciaRepo.ids_de_familia` |
| router / UI | sin cambios | el select agrupa padre › subtipo |
| **export** | ✅ mismo filtro | ✅ **mismo filtro** — delega en `get_all`, una sola implementación |

🔴 **Elegir un tipo PADRE trae también las ausencias de sus hijos.** Con el `.eq()` viejo un
filtro por padre habría devuelto CERO filas: las ausencias apuntan a la hoja, nunca al padre.
Elegir un HIJO trae solo las suyas (un hijo no tiene hijos: la profundidad está limitada a 2).

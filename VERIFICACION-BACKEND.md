# Verificación del backend — HR Karstec / Capital Humano

> **Este documento no es un plan: es un checklist para auditar.**
> Fecha: 19 de agosto de 2026. El backend se declara terminado y hay que comprobarlo.
>
> Cada ítem está escrito para poder verificarse contra el código o contra el catálogo vivo.
> Si algo no se puede verificar leyendo, está marcado.

---

## Cómo usar este documento

Para Claude Code:

1. **Verificá cada ítem contra el repo y contra el catálogo** (`grmdiwxcvcjorlohpwji`), no
   contra `docs/` — la documentación ya mintió varias veces en este proyecto.
2. **Reportá en las dos direcciones:** lo que falta, y lo que hay en el repo y no está acá. Lo
   segundo importa igual: algo construido que nadie pidió es alcance que se coló.
3. Para cada ítem: ✅ hecho y verificado · ⚠️ hecho parcialmente, con qué falta · ❌ no está ·
   ❓ no se puede determinar leyendo.
4. **No arregles nada.** Esta es una auditoría. Lo que aparezca se decide después.

---

## 1. Migraciones

Todas tienen que estar corridas en producción. Verificar contra el catálogo **por sus objetos**,
no contando tablas: varias no crean ni borran ninguna.

| # | Qué introdujo | Cómo se verifica |
|---|---|---|
| 113 | Las tres tablas nuevas y las columnas de preingreso/baja | `perfiles_puesto`, `recategorizaciones`, `eventos_agenda` existen · `empleados.fecha_ingreso_prevista` y `fecha_baja_prevista` existen |
| 114 | Post-deploy del lote | Ver su propio bloque de verificación |
| 115 | Índices de escala (6) | Los seis índices compuestos existen |
| 116 | Columnas finales: `ofrecemos`, `vacantes.perfil_puesto_id`, las de formación | Las 11 columnas existen · `empleado_capacitacion.empleado_id` es nullable · `ux_ec_nombre_libre` existe |
| 117 | CHECK de recategorizaciones con `categoria_nueva` | `pg_get_constraintdef` de `recategorizaciones_algo_cambia_check` nombra los tres campos |
| 118 | Índices que la paginación habilita (6) | Existen, incluido `idx_empleados_empresa_apellido` |
| 119 | `objetivos.tipo`, índice único de 5 columnas, `areas_involucradas` como `text[]` | La columna es `text[]` NOT NULL DEFAULT `'{}'` · el índice único incluye `tipo` |
| 120 | `'preingreso'` en el CHECK de `empleados.estado` | El CHECK admite los cinco valores |

🔴 **Y verificar que `db/schema.sql` refleje todo lo anterior.** Es el archivo del que el dev de
infra levanta RDS. Su encabezado **no debe** decir qué migraciones están corridas — eso quedó
decidido el 16/8 después de cinco desfasajes.

---

## 2. Perfiles de puesto

**Qué es:** plantillas del grupo para armar búsquedas. Al crear una vacante los campos **se
copian**, no se referencian: editar el perfil después no cambia las vacantes ya creadas.

- [ ] La tabla **no tiene** `empresa_id` ni `area_id`. Es a propósito: `areas.empresa_id` es
      NOT NULL y un perfil con área quedaría atado a una empresa por transitividad.
- [ ] **No tiene competencias**, ni ubicación, ni contador de ocupantes.
- [ ] Campos: nombre · descripción · funciones · requisitos · formación · experiencia ·
      conocimientos técnicos · **ofrecemos** · modalidad · nivel · tipo de contrato · jornada.
- [ ] CRUD completo con baja lógica (`activo`).
- [ ] 🔴 El evento de auditoría va con **`empresa_id` NULL** — un perfil es del grupo.
- [ ] Los CHECK de modalidad, nivel, tipo de contrato y jornada son **idénticos** a los de
      `vacantes`. Si difieren, un perfil guarda un valor que la vacante rechaza al copiarlo.
- [ ] `vacantes.perfil_puesto_id` existe y guarda de qué perfil salió la vacante.
- [ ] `vacantes.ofrecemos` existe: sin ella, "Ofrecemos" sería el único bloque del aviso que no
      se puede adaptar por búsqueda.
- [ ] Los labels del formulario distinguen **experiencia, formación, conocimientos técnicos y
      otros requisitos**. El aviso real (`docs/AVISO-BUSQUEDA-REFERENCIA.md`) los mezcla en un
      bloque, y sin ayuda visible RRHH pega todo en `requisitos`.
- [ ] El router de catálogos se monta **antes** que el del CRUD, o `/campos` cae en `/{id}`.

---

## 3. Recategorizaciones

**Qué es:** registro del cambio de rol, seniority o categoría de una persona. Se ve en una
planilla propia y en el historial de la ficha del colaborador.

- [ ] 🔴 **Sin flujo de aprobación.** No hay estado pendiente, ni aprobador, ni comité.
- [ ] Fecha efectiva **editable hacia atrás**, con la de hoy por defecto.
- [ ] 🔴 Los valores **anteriores** salen de la última recategorización previa a `fecha_efectiva`,
      no del empleado actual. Si no hay ninguna previa, del empleado.
- [ ] 🔴 El update del empleado corre **solo si la fila es la más reciente**. Cargar una del 1/8
      después de una del 1/9 registra el histórico y NO pisa al empleado.
- [ ] `impacto_salarial` **se omite de la respuesta** sin permiso de lectura sobre COSTOS. No se
      gatea la sección entera.
- [ ] 🔴 `roles` reemplaza **solo `roles[0]`**, conservando los secundarios. Y no acumula: el rol
      viejo no queda como secundario.
- [ ] Se puede **editar, no borrar**.
- [ ] El evento de auditoría lleva **entidad propia** `"recategorizacion"`, y su `empresa_id` es
      el del **empleado**, no el del header.
- [ ] Dos endpoints: la planilla paginada y el historial de la ficha (lista plana, sin paginar,
      más reciente primero).
- [ ] `categoria_anterior` y `categoria_nueva` existen y el CHECK las admite como único cambio.

---

## 4. Eventos de agenda

**Qué es:** los recordatorios que Capital Humano se crea. Conviven con las alertas que el
sistema calcula.

- [ ] Campos: título · fecha · `dias_aviso` · `es_publica` · `resuelta` con su timestamp y autor.
- [ ] Visibilidad: las privadas solo las ve su autor. 🔴 **`gerencia_lectura` ve las privadas
      ajenas** — copia el precedente de `onboarding_templates`, sin la rama `created_by IS NULL`
      que ahí es muerta.
- [ ] Resolver es **reversible**, y al desresolver se limpian `resuelta_at` y `resuelta_por`.
- [ ] Se puede editar y borrar.
- [ ] **Sin export.**
- [ ] Sección propia en `Seccion`, con su espejo en `permisos.ts` y en `NAV_GROUPS`.
- [ ] 🔴 La query de pendientes **no lleva `fecha >= hoy`**: un evento vencido y sin resolver
      tiene que seguir apareciendo.
- [ ] El filtro fino (`fecha - dias_aviso <= hoy`) se hace en Python sobre un conjunto acotado —
      PostgREST no puede comparar una columna contra una aritmética.
- [ ] `dias_aviso_evento` y `periodo_prueba_dias` expuestos en Configuración.
- [ ] Tiene front (`/eventos`), construido junto con el backend. **Entra en el reestilado.**

---

## 5. Objetivos

**Qué es:** el tablero del equipo de Capital Humano. Dos vistas que no se comparten.

- [ ] `tipo` con CHECK: `anual` | `operativo`. Cada objetivo pertenece a UNA vista.
- [ ] 🔴 Default de la **columna** es `'anual'`; el del **alta y el import** es `'operativo'`. No
      son el mismo default y no se contradicen.
- [ ] El tipo **no se hereda** entre padre e hijo: un operativo colgando de un anual es válido.
- [ ] `periodicidad` es **texto libre** — "primer trimestre", "tercera semana de septiembre".
- [ ] 🔴 `areas_involucradas` es **`text[]`**, no texto. Con texto plano el desplegable ofrecería
      combinaciones y un ILIKE traería "Sistemas Corporativos" al buscar "Sistemas".
- [ ] El filtro usa `.contains()` **con el literal comillado desde el repo**: `postgrest-py` hace
      `",".join` sin comillar y un área con coma adentro se parte en dos, devolviendo cero sin
      error.
- [ ] El desplegable de valores conocidos sale del **aplanado del array**, y es propio: no se
      tocó `CAMPOS_AUTOCOMPLETABLES`, que está atado a `empleados` y tiene dos tests que lo fijan.
- [ ] El índice único incluye `tipo`: "Cerrar el trimestre" anual y operativo del mismo
      responsable no colisionan.
- [ ] El **23505 se traduce a 409**. Antes era un 500 en el alta manual.
- [ ] El import acepta las tres columnas, todas opcionales. Un archivo viejo sin ellas entra
      igual. Un `Tipo` inválido cae al default, no rechaza la fila.
- [ ] El preview del import compara títulos **case-insensitive**, igual que el índice
      (`lower(titulo)`).
- [ ] El duplicado se reporta con mensaje legible, no con el texto crudo de Postgres.
- [ ] 🔴 `procesos_service` y `_reporte_anual_metricas` **siguen contando las dos vistas juntas**,
      y eso está declarado al lado de la query.
- [ ] Con el filtro por tipo, un hijo cuyo padre no pasa el filtro **se promueve a raíz**. Es
      correcto y está escrito.

---

## 6. Preingresos y bajas

**Qué es:** separar la fecha efectiva de la burocrática. Y el arreglo de un bug vivo.

### El bug que se arregló
- [ ] 🔴 Iniciar un offboarding **ya no escribe `estado='baja'`**. Antes lo hacía en el acto con
      el último día a 30 días vista: el colaborador desaparecía del headcount, del organigrama,
      del denominador de ausentismo, de los saldos de vacaciones, del selector de superior y del
      link público de horas, aunque le quedaran 30 días trabajando.
- [ ] `bajas_mes` y `bajas_periodo` se cuentan por **`fecha_egreso`**, no por `updated_at`. Antes
      la baja se imputaba al mes del trámite y cualquier edición del legajo la re-imputaba.
- [ ] `DELETE /api/empleados/{id}` **cerrado**. No tenía caller y dejaba el legajo de baja sin
      fecha.

### El preingreso
- [ ] `'preingreso'` está en el CHECK de `empleados.estado`.
- [ ] 🔴 Las fechas previstas **nunca cambian el estado**. La transición es un **botón explícito**
      — "confirmar ingreso" / "confirmar baja". Si el sistema promoviera solo, promovería fichas
      incompletas.
- [ ] `fecha_ingreso` de un preingreso se carga con la **fecha prevista** (la columna es NOT NULL
      y sostiene el cálculo de antigüedad y el cupo de vacaciones).
- [ ] 🔴 **Los 5 contadores que cuentan por fecha sin mirar estado excluyen preingreso.** Son el
      punto ciego; ningún estado los protege. ⚠️ **Los archivo:línea de este ítem estaban vencidos
      y se remidieron el 19/8/2026** — los cinco sitios existen y filtran bien, pero se movieron:
      `dashboard_service.py:80` y `:95` (decía `:67`), `_reporte_dotacion.py:37`, `:51` y `:106`
      (decía `:31` y `:89`), `_reporte_movimientos.py:41` y `:62` (decía `:32` y `:44`).
      **Verificar por contenido, no por número de línea**: en un archivo que se edita seguido, la
      línea es la parte que se pudre primero.
- [ ] 🔴 Los **2 sitios de `!= 'baja'`** pasaron a lista blanca `IN ('activo','licencia',
      'suspendido')`. Con `NOT IN`, cualquier valor nuevo cuenta solo. ✅ **Y quedó mejor que lo
      descrito**: no son dos literales duplicados sino la constante compartida
      `ESTADOS_EN_PLANTILLA` (`utils/estados_empleado.py:117`), consumida por `_area_row.py:64` y
      `sucesion_repo.py:91` (el checklist decía `:53` y `:88`).
- [ ] El listado de colaboradores por defecto muestra **dotación real**, no todo. Antes mostraba
      bajas.
- [ ] `EmpleadoUpdate.estado` tipado, no `Optional[str]` sin validar.
- [ ] Los 15 sitios que filtran `= 'activo'` **no se tocaron**: quedan correctos gratis. Verificar
      que sea así.

### El puente desde candidatos
- [ ] El prellenado sale de **candidato → vacante → empleado**, pero 🔴 **son DOS campos, no
      cuatro** (corregido el 19/8/2026 contra `_candidato_contratar_mapeo.py:78-94`): de la
      vacante salen sólo **`area_id`** y **`modalidad_trabajo`** (y `ubicacion`, que este
      checklist no mencionaba). **`roles` viene del BODY**, no de la vacante. Y
      **`tipo_contrato` es un default hardcodeado** (`TIPO_CONTRATO_POR_DEFECTO`,
      "Relación de dependencia"): **no se copia de la vacante a propósito**, porque son
      vocabularios distintos —`vacantes.tipo_contrato` es un enum de 4 valores y
      `empleados.tipo_contrato` es texto libre—, y el propio archivo lo declara como "el error
      más fácil de cometer acá". También escribe `email_personal` ← `candidato.email` (nunca
      `email_corporativo`, que es UNIQUE global).
- [ ] 🔴 **El puente NO acepta un candidato sin vacante**: `_candidato_contratar_guardas.py:57-59`
      exige `cand.vacante_id` y rechaza con **409 `CANDIDATO_SIN_VACANTE`**. Lo que sí existe es
      **otro camino**: el alta manual (`POST /api/empleados`) acepta
      `estado: Literal["activo","preingreso"]`. Son dos rutas distintas, no dos ramas del mismo
      endpoint — el checklist las mezclaba.
- [ ] El candidato se marca con `estado='contratado'` — el valor ya estaba en el CHECK y ningún
      código lo usaba.
- [ ] ❌ **No hay trazabilidad candidato → empleado.** Es DDL y quedó fuera de alcance, en v2.

---

## 7. Formación

**Qué es:** Capacitaciones renombrado y ampliado. Sale del Excel real de Capital Humano (53
filas, 42 con datos, 3 capacitaciones distintas).

- [ ] **No es un módulo nuevo:** `capacitaciones` y `empleado_capacitacion` con columnas nuevas.
- [ ] En `capacitaciones`: `entidad_capacitadora` · `modalidad` · `tipo`. Todas texto libre.
- [ ] En `empleado_capacitacion`: `proyecto` · `anio` · `mes` · `nombre_libre`.
- [ ] 🔴 `empleado_id` es **nullable**: el Excel trae 41 nombres sin DNI. Los que no matchean se
      cargan con `nombre_libre`. Y resuelve la capacitación de alguien que ya no trabaja acá.
- [ ] Los cuatro arreglos del nullable: el guard que no mete `None` en el `.in_()` ·
      `AsignacionResponse.empleado_id` es opcional (`schemas/capacitacion.py:108`) · el export cae
      a `nombre_libre` (`services/_capacitaciones_export.py:42`) · el tipo del front es
      `string | null` (`frontend/types/capacitacion.ts:61`).
      ⚠️ **El primero NO vive en `asignacion_repo.py`, como decía este checklist, sino en el
      satélite `repositories/_asignacion_row.py:38`** (`if r["empleado_id"]`). El `.in_()` que sí
      está en `asignacion_repo.py:43` es **otro**: el del filtro por área, cuyos ids salen de la
      tabla `empleados` y nunca son `None`. Mismo archivo en el nombre, distinto código.
- [ ] `proyecto` es texto libre a propósito: el Excel mezcla empresas, clientes y proyectos.
- [ ] Área y puesto **no se copian**: salen del empleado. Copiarlos haría que el registro mienta
      cuando alguien cambia de área.
- [ ] El índice único de idempotencia usa `coalesce` para que dos filas sin año no sean distintas.
- [ ] ❓ El import del Excel real: verificar si se construyó o quedó pendiente.

---

## 8. Escala y paginación

- [ ] Los listados que crecen con la dotación **paginan**: `page`/`page_size` con `le=100`.
- [ ] 🔴 Todos llevan su orden **más `.order("id")`** de desempate, **ascendente aunque la fecha
      vaya DESC** — así están hechos los índices de la 118.
- [ ] `empleado_repo` **tiene `.order()`**. Antes paginaba sin orden: una fila podía salir dos
      veces o ninguna.
- [ ] El wrapper de respuesta es `{items, total, page, page_size, total_pages}` en todos.
- [ ] Los **totales salen del backend**, no de `.reduce()` sobre la página. `HorasTab` decía
      "9 h" cuando el proyecto tenía 400.
- [ ] Cambiar un filtro **resetea a página 1**.
- [ ] Los contadores del encabezado leen `total`, no la página.
- [ ] Los **exports siguen trayendo todo**, no la primera página, y aceptan los mismos filtros
      que el listado.
- [ ] 🔴 **Los métodos con varios callers no se paginaron en el lugar.** `nomina_repo` tiene tres
      callers que agregan: paginarlo habría dejado los KPIs calculando sobre 20 de 858 filas sin
      error.
- [ ] `/api/areas/opciones` existe: 15 dropdowns esperaban la lista completa de áreas y habrían
      quedado con 20 de 180.
- [ ] `Pagination` es numérica con elipsis, no Prev/Next.
- [ ] El rate limit de export es **por usuario**, no por IP, y son 100/hora.
- [ ] 🔴 **`LIMITE_FILAS_EXPORT` son 20.000, no 5.000** (`services/_limite_export.py:68`). Se subió
      el 13/8/2026 con medición: el 5.000 no cubría ni un mes de auditoría a la escala proyectada
      (~16.000 eventos/trimestre con 1.005 colaboradores). El techo que rige no es el timeout
      httpx de 30 s sino **los 300 s de la función de Vercel** — el 92% del tiempo es construir el
      archivo, no traer las filas. **20.000 no cubre el año entero** (~64.000): eso pide export
      asíncrono, no un número más alto.
- [ ] La lista `EXPORTS` de `test_limite_export.py` tiene **20 entradas** y la guarda es
      `>= 20`, no 18: entraron `perfil_puesto_service` y `recategorizacion_service`.
- [ ] 🔴 **El único listado que todavía NO pagina es `objetivos`** — no cuatro. El catálogo de
      formación, inventario/ítems e inventario/asignaciones ya salieron de esa lista. Y paginar
      objetivos **no es agregar `.range()`**: el export trae padres E hijos, así que el tope se
      cuenta sobre el árbol aplanado, no sobre las raíces.

---

## 9. Reglas transversales — para cada módulo nuevo

Verificar las seis en perfiles, recategorizaciones, eventos y objetivos:

- [ ] **Paginado** desde el día uno.
- [ ] **IDs tipados `UUID`** en Pydantic, nunca `str`. Es el error #1 del porteo a asyncpg.
- [ ] **`model_dump(mode="json")`** en `save` **y** en `update`.
- [ ] **Sin RLS.**
- [ ] **Permisos:** sección en el enum `Seccion` + espejo en `permisos.ts`. `test_espejo_permisos`
      tiene que estar verde.
- [ ] **Auditoría** de alta, edición y baja.
- [ ] **Export** con su entrada en la lista a mano de `test_limite_export` y la guarda subida.
      🔴 Esa lista es manual: un export nuevo **no rojea**, pasa en verde sin control.
- [ ] Los endpoints sin front declarados en `test_callers_huerfanos` **con disparador**, no como
      excepción permanente.

---

## 10. Lo que quedó fuera de alcance — no es deuda, es decisión

Si aparece en el repo, es alcance que se coló. Si no aparece, está bien.

| Qué | Por qué |
|---|---|
| Plan de desarrollo | v2, se muestra como "Próximamente" |
| Carga de horas | v2. Apagada por flag, **no borrada** |
| Inventario | Fuera del menú hasta nuevo aviso |
| Trazabilidad candidato → empleado | Es DDL, no estaba comprometida |
| Competencias en perfiles | Las inventó un prototipo, nadie las pidió |
| Aprobación de recategorizaciones | No existe el flujo |
| Porcentaje de avance en objetivos | Hay estado, no porcentaje |
| Evaluaciones vencidas o programadas | El sistema importa resultados, no corre ciclos |
| Documentos próximos a vencer | No hay lista de documentos obligatorios |
| Bloque N — el legajo según la nómina | Va al final, después del frontend |
| Mover reportes y dashboard a `repositories/` | 48 queries. Solo si sobra tiempo |
| Todo AWS | Del dev de infra |

---

## 11. Los cuatro greps de porteo

Correr y reportar el resultado. Lo que aparezca se arregla o se declara.

> 🔴 **LOS CUATRO ESTABAN CIEGOS Y SE REESCRIBIERON EL 19/8/2026. Estos son los buenos; los de
> abajo, los viejos, quedan escritos SOLO para que nadie los vuelva a pegar de memoria.**
> Cada uno dejaba pasar en silencio justo la clase de caso que venía a buscar — el mismo modo de
> falla que ya habían tenido `_validar_columna` (cortaba con `return` al ver `*`) y el barrido de
> estado (no veía `ESTADOS_EN_PLANTILLA` ni `EmpleadoCreate(**campos)`). **Un control que no puede
> fallar no es un control.**

```bash
# 1 · comparaciones de id sin coaccionar los dos lados
grep -rnE "(^|[^_a-zA-Z])(id|[a-z_]+_id)[[:space:]]*(==|!=)" backend/ --exclude-dir=venv
# 2 · SDK de auth remanente — CUALQUIER cliente, no solo el admin
grep -rnE "supabase[a-z_]*\.auth\." backend/ --exclude-dir=venv
# 3 · escrituras sin serializar — model_dump CON o SIN argumentos
grep -rn "model_dump(" backend/ --exclude-dir=venv | grep -v 'mode="json"'
# 4 · IDs mal tipados — incluye `id` pelado y `Optional[str]`
grep -rnE "\b(id|[a-z_]+_id)[[:space:]]*:[[:space:]]*(Optional\[)?str" backend/schemas/
```

**Por qué cada uno estaba ciego** (medido, no supuesto):

| # | El viejo | Qué no podía ver |
|---|---|---|
| 1 | `grep -rn "uuid.*==" backend/` | Exige el literal `uuid` **en la misma línea**. Devuelve **15 matches y los 15 son falsos positivos** (asserts de test donde `uuid4()` cae cerca de un `==`). De las ~20 comparaciones de id reales del código de producción —todas con la forma `str(a) == str(b)`— **no ve ninguna**. Tampoco ve `!=` salvo que la palabra `uuid` esté escrita. Precisión 0/15, cobertura 0. |
| 2 | `grep -rn "supabase_admin.auth" backend/` | Sólo mira **un** cliente. Los 3 usos por el otro (`supabase_client.auth.*`, en `auth_service.py:42,97` y `usuario_service.py:80`) le pasan por al lado: ve 5 de 8. |
| 3 | `grep -rn "model_dump()" backend/ \| grep -v mode=` | El literal `model_dump()` es **sin argumentos**, así que `model_dump(exclude_none=True)` no matchea. **17 call sites de escritura de producción invisibles**, incluido `_objetivo_payload.py:84`, que la auditoría encontró leyendo código porque el grep no lo mostraba. |
| 4 | `grep -rn ": str" backend/schemas/ \| grep _id` | Doblemente ciego: `": str"` no matchea `Optional[str]` (**26 campos**), y `grep _id` descarta el `id` pelado (**25 campos**, la línea es `    id: str` y no contiene `_id`). Ve 38 de ~89. |

> ⚠️ **Y los cuatro escaneaban `backend/venv/`**, que no es código del proyecto: el grep 3 pasaba
> de 127 matches a 83 con sólo excluirlo. De ahí el `--exclude-dir=venv` en los cuatro.

Los tres `str` de Gmail, LinkedIn y Zernio (`message_id`, `post_id`, `email_id`) son ids externos
y están **bien** como `str`. El resto del inventario —y la distinción entrada/salida, que es la
que decide si rompe al portear— lo mantiene el barrido `tests/test_ids_tipados.py`, no un grep.

---

## 12. Deuda conocida — no se arregla acá, se confirma que sigue anotada

- 🔴 **`TestElPisoDeTiempo` — la descripción vieja de este ítem era FALSA y se corrigió el
  19/8/2026.** Decía "falla según la carga de CPU". **No falla por carga**: la aserción es un
  **piso** (`perf_counter() - t0 >= 0.12`), y la carga sólo puede empujar el tiempo hacia arriba,
  o sea **al verde**. Medido el 17/8: **12 corridas con los 12 cores saturados, 0 fallos**.
  **El mecanismo real** (`docs/DEUDA-TECNICA.md` §5) es que en Windows
  `loop._clock_resolution = 0.015625` (15,6 ms) y **asyncio dispara los timers hasta esa ventana
  ANTES de su vencimiento, a propósito**: un `asyncio.sleep(0.12)` puede volver legítimamente a
  los ~0.1044 s. La aserción pide `>= 0.12` **sin tolerancia**, así que vive a 15,6 ms de un rojo
  que no depende del código. En máquina ociosa, 400 sleeps seguidos: 1 volvió por debajo (0,2%).
  ⚠️ **Lo que dispara la intermitencia es correr dos pytest concurrentes** (el jitter de dos event
  loops expone la fragilidad que ya estaba). **Pero el brazo del `__pycache__` compartido NO está
  establecido como causa**: fue 1 fallo contra 0 con n=6, que no distingue nada, y no existe
  mecanismo por el que compartir bytecode *acorte* un sleep. Anotarlo como "la causa es el
  `__pycache__`" sería repetir el error que esa sección documenta.
  🔑 **La regla de arnés que dejó: toda corrida de pytest va A ARCHIVO, con nombre propio.** El
  fallo original se perdió en un `tail -2` sobre un pipe y recuperarlo costó 12 corridas.
- El modal de empleados escribe `"F"`/`"M"` y los datos dicen `"Femenino"`/`"Masculino"`.
- `proyecto_asignaciones` tiene 31 filas y la ficha no las muestra.
- El export de auditoría no aguanta un año a escala: pide export asíncrono.
- `test_limite_export` con lista escrita a mano.
- `.gitattributes` para el CRLF, antes de que el dev tome el repo desde Linux.
- `'suspendido'` es un valor muerto en el CHECK de estado.
- ✅ **`/api/eventos/pendientes` — YA NO ES DEUDA: la ruta se BORRÓ en A6 (19/8/2026).** No es que
  siga publicada sin caller. `GET /api/dashboard/atencion` pasó a consumir
  `EventoAgendaService.pendientes` **directamente**, así que la lógica sigue viva y la ruta HTTP
  no existe. El porqué está escrito en `routers/eventos_agenda.py:46-51` y el barrido
  `test_callers_huerfanos.py` la sacó de su lista. Queda como precedente de que el mecanismo de
  "excepción con disparador" funciona: salió sola cuando le llegó un consumidor.
- Los endpoints publicados sin pantalla, declarados con disparador.

---

## 13. Lo que quiero en el informe

1. **Los ítems por estado**, con archivo:línea para cada verificación.
2. 🔴 **Lo que está en el repo y no está en este documento.** Alcance que se coló, o algo que
   decidimos y no quedó escrito.
3. **Lo que no se puede determinar leyendo**, y qué haría falta.
4. **El estado real de la suite:** cuántos tests, cuántos barridos, `tsc` limpio.
5. Si algún ítem de la sección 9 falla en algún módulo: es lo que más importa, porque son las
   reglas que hacen que el porteo a AWS no explote.

**No arregles nada.** Esto es una auditoría.

---

*HR Karstec · Checklist de verificación del backend · 19/8/2026*

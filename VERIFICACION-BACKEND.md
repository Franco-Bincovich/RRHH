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
      punto ciego: `dashboard_service.py:67`, `_reporte_dotacion.py:31` y `:89`,
      `_reporte_movimientos.py:32` y `:44`. Ningún estado los protege.
- [ ] 🔴 Los **2 sitios de `!= 'baja'`** pasaron a lista blanca `IN ('activo','licencia',
      'suspendido')`: `_area_row.py:53` y `sucesion_repo.py:88`. Con `NOT IN`, cualquier valor
      nuevo cuenta solo.
- [ ] El listado de colaboradores por defecto muestra **dotación real**, no todo. Antes mostraba
      bajas.
- [ ] `EmpleadoUpdate.estado` tipado, no `Optional[str]` sin validar.
- [ ] Los 15 sitios que filtran `= 'activo'` **no se tocaron**: quedan correctos gratis. Verificar
      que sea así.

### El puente desde candidatos
- [ ] El prellenado sale de **candidato → vacante → empleado**: cuatro de los cinco campos que
      faltan salen de la vacante (área, rol, modalidad, tipo de contrato).
- [ ] Un candidato **sin vacante** también puede pasar a preingreso, pidiendo todo a mano.
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
- [ ] Los cuatro arreglos del nullable: `asignacion_repo` no mete `None` en el `.in_()` ·
      `AsignacionResponse.empleado_id` es opcional · el export cae a `nombre_libre` · el tipo del
      front es `string | null`.
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

```
grep -rn "uuid.*==" backend/                      → comparaciones UUID contra string
grep -rn "supabase_admin.auth" backend/           → SDK de auth remanente
grep -rn "model_dump()" backend/ | grep -v mode=  → escrituras sin serializar
grep -rn ": str" backend/schemas/ | grep _id      → IDs mal tipados
```

Los tres `: str` de Gmail y LinkedIn son ids externos y están **bien** como `str`.

---

## 12. Deuda conocida — no se arregla acá, se confirma que sigue anotada

- Un test que falla según la carga de CPU (`TestElPisoDeTiempo`), tres apariciones.
- El modal de empleados escribe `"F"`/`"M"` y los datos dicen `"Femenino"`/`"Masculino"`.
- `proyecto_asignaciones` tiene 31 filas y la ficha no las muestra.
- El export de auditoría no aguanta un año a escala: pide export asíncrono.
- `test_limite_export` con lista escrita a mano.
- `.gitattributes` para el CRLF, antes de que el dev tome el repo desde Linux.
- `'suspendido'` es un valor muerto en el CHECK de estado.
- `/api/eventos/pendientes` existe y **no tiene caller** — la infraestructura de avisos está
  construida y no se muestra en ninguna parte.
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

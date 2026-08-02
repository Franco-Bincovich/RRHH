# Diagnóstico READ-ONLY — subtipo de ausencias · asignar equipos a proyectos

> **2/8/2026 · Sesión de diagnóstico. NO se escribió una sola línea de código.**
> Verificado contra los archivos fuente **y contra el catálogo vivo de producción** (MCP Supabase,
> proyecto `grmdiwxcvcjorlohpwji`).

---

## Resumen ejecutivo

1. ✅ **Las migraciones 086 y 087 YA ESTÁN CORRIDAS en producción.** Verificado: existen
   `empleado_superior_pendiente`, `plantillas_mail`, `mail_enviado` y la columna
   `usuario_integraciones.es_remitente_sistema`. **No se acumulan. El próximo libre es el 088.**
2. 🔴 **`solicitudes_ausencia` tiene CERO filas.** Cambiar el modelo de ausencias **hoy es
   gratis**: no hay una sola fila que migrar. Con datos cargados, la misma migración pasa a ser
   una reasignación de `tipo_id` sobre filas vivas. **Es la ventana, y se cierra sola.**
3. **Recomendación Parte A: `padre_id` self-FK en `tipos_ausencia`.** No aplanar y no texto libre.
4. 🔴 **Parte B: "asignar por equipo" NO EXISTE como trabajo — `empleados.equipo` está 0/19 en
   producción.** No hay nada que asignar. El trabajo real es **asignar por ÁREA** (19/19 poblado)
   y, si Franco quiere equipos de verdad, eso es una entidad nueva: otro proyecto, otro costo.
5. 🔴 **La "decisión registrada" de que el área no asigna NUNCA FUE UNA DECISIÓN.** Es una
   descripción de lo que el modal hace, que se copió a CLAUDE.md como si fuera una regla. No hay
   motivo escrito en ningún lado. **Pero hay un motivo real que nadie escribió, y hay que
   resolverlo antes de construir** — ver (j).

---

# PARTE A — Subtipo de ausencias

## (a) Estado de `tipos_ausencia` después de la 085 — verificado en producción

La columna `empresa_id` **sí está**, y `cuenta_ausentismo` también. Las 4 filas:

| nombre | es_base | activo | empresa_id | cuenta_ausentismo |
|---|---|---|---|---|
| Enfermedad | true | true | **NULL (global)** | true |
| Injustificada | true | true | NULL | true |
| Otro | true | true | NULL | true |
| Personal | true | true | NULL | true |

```
tipos_ausencia (id, nombre, es_base, activo, created_at, updated_at, empresa_id, cuenta_ausentismo)
```

🔴 **Y el dato que gobierna toda esta parte: `solicitudes_ausencia` tiene 0 filas.**

Todo lo que sigue —cambiar el modelo, reclasificar "Injustificada", partir en dos niveles— **hoy
no toca un solo dato**. Es un `ALTER TABLE` y un `INSERT` de catálogo. El día que RRHH cargue el
histórico de ausencias, exactamente la misma migración se convierte en una reasignación de
`tipo_id` sobre filas vivas, con la clase de riesgo que eso tiene. La 085 ya usó este argumento
para meter `empresa_id` "ahora y no cuando haga falta"; acá aplica con más fuerza, porque además
está el import de ausencias esperando definición.

## (b) 🔴 La recomendación: `padre_id` self-FK

**No es la opción con menos código. Es la única que sostiene los cuatro requisitos a la vez.**

### El descarte de las otras dos, con el tradeoff

**Aplanar (un tipo por combinación)** — "Enfermedad familiar - Madre/padre" como una fila.
Es la más barata: cero migración estructural, cero cambios en los consumidores, el catálogo sigue
plano. Y rompe el primer requisito: **"cuántos días de enfermedad familiar" deja de ser una
consulta y pasa a ser un `LIKE 'Enfermedad familiar%'`** sobre un nombre que RRHH edita desde la
UI. El día que alguien corrija el typo del archivo real —"Franco compesatorio"— el agrupamiento
se parte en silencio. Un reporte que depende de la ortografía de un campo editable no es un
reporte. Además el catálogo explota combinatoriamente: 6 padres × 4 hijos son 24 filas para
administrar en una lista plana.

**Texto libre (`subtipo` en la ausencia)** — 🔴 **es reintroducir `empleados.equipo`, y eso ya
está documentado como error en el repo.** CLAUDE.md lo dice sin ambigüedad: *"Campo `equipo`
(texto libre): sin tabla `equipos`, 'asignar/importar por equipo' no existe"*. Y este diagnóstico
lo confirma con datos: **0/19 poblado**. Un campo de texto libre no es "flexible": es un campo
que nadie puede consultar, agrupar ni validar, y que termina vacío o con cuatro grafías del mismo
valor. El costo se paga después y lo paga otro.

### Lo que gana `padre_id`

```sql
ALTER TABLE tipos_ausencia ADD COLUMN padre_id uuid REFERENCES tipos_ausencia(id);
```

- **Reportar por padre y ver el detalle** es una sola query con `COALESCE(padre_id, id)`. No
  depende de cómo esté escrito el nombre.
- **Alta desde la UI**: agregar un subtipo es un INSERT con `padre_id`. El panel que ya existe
  sirve con un cambio chico (ver (f)).
- **El typo del archivo real deja de importar**: "Franco compesatorio" es el `nombre` de un hijo;
  el agrupamiento va por `padre_id`, no por texto.
- **Es aditivo**: una columna nullable. `padre_id IS NULL` = tipo de primer nivel, que es
  exactamente el modelo de hoy. Las 4 filas actuales no se tocan.

**El costo honesto:** una self-FK necesita dos guardas que hay que escribir, no salen gratis:
1. **Profundidad máxima 2.** Un hijo no puede tener hijos. Sin eso, el modelo admite un árbol y
   la UI se vuelve el árbol complicado que (f) quiere evitar. Se garantiza con un CHECK que exija
   que el padre tenga `padre_id IS NULL` — o, más simple y verificable, con la validación en el
   service más un test.
2. **Anti-ciclos.** Ya existe el molde exacto en el repo: `ensure_no_ciclo_manager`
   (`services/_empleados_manager.py`), con su recorrido y su `max_saltos`. Con profundidad 2 el
   ciclo es casi imposible, pero la guarda es de dos líneas y el precedente está escrito.

### `cuenta_ausentismo`: **vive en el HIJO, con el padre como default de alta**

Es la pregunta más fina de las cuatro y la respuesta no es "en los dos".

- **En el padre solo** no alcanza: dentro de "Licencia" puede haber subtipos que computan y otros
  que no (una licencia por estudio vs. una por maternidad). Si vive en el padre, RRHH no puede
  distinguirlos sin crear un padre nuevo, que es justo lo que la jerarquía vino a evitar.
- **En los dos** es la peor: dos fuentes para el mismo hecho. Un padre con `false` y un hijo con
  `true` no tiene una respuesta correcta, y el que la resuelva va a inventar una regla
  (¿gana el hijo? ¿el más restrictivo?) que después nadie recuerda.
- ⇒ **La ausencia se carga siempre contra un tipo concreto** (hoja si el padre tiene hijos, o el
  padre si no los tiene). Ese tipo es el que decide. **El padre conserva la columna solo como
  valor por defecto al crear un hijo** — un ahorro de tipeo en la UI, no una regla de cálculo.
  Se documenta así y `_reporte_ausentismo` no cambia una línea: sigue leyendo
  `tipos_ausencia(cuenta_ausentismo)` del tipo de la fila.

## (c) Qué pasa con las 4 filas actuales

**Quedan como padres sin hijos, y eso es un estado válido, no transitorio.** `padre_id IS NULL` y
sin hijos = exactamente el comportamiento de hoy. Una ausencia se carga directo contra ellas.

🔴 **Pero dos de las cuatro no son tipos del mismo eje**, y conviene decidirlo ahora que no hay
datos:

- **"Enfermedad"** → es un padre legítimo. Los archivos reales ya traen "ENFERMEDAD FAMILIAR →
  Madre/padre", así que su primer hijo ya está identificado. ⚠️ Ojo: el archivo dice *enfermedad
  familiar*, que probablemente sea **otro padre** distinto de "enfermedad propia". Hay que
  preguntarle a RRHH, no adivinar.
- **"Personal"** → padre legítimo, y es el que más subtipos va a juntar (trámite, mudanza,
  estudio).
- **"Otro"** → 🔴 **es un anti-tipo.** Existe para que la carga no se trabe cuando falta un tipo,
  y su efecto real es que la información se pierde ahí adentro. Con la jerarquía y el alta desde
  la UI, su motivo de existir se debilita: si falta un tipo, ahora se crea. **Recomendación: NO
  borrarlo** (la FK sin `ON DELETE` lo impide y el repo ya lo documenta), pero sí desactivarlo
  (`activo=false`) una vez que el catálogo real esté cargado, y revisar periódicamente qué cayó
  ahí. Es un indicador de catálogo incompleto, no una categoría.
- **"Injustificada"** → ver (d). Es la que hay que sacar.

**Ninguna de las cuatro es en realidad un subtipo de otra.** No hay que reparentar nada.

## (d) 🔴 "Injustificada" — hay que migrarlo, y ahora es gratis

**Sí, mezcla dos ejes, y desde la 085 la mezcla es demostrable, no una opinión:**

| eje | dónde vive hoy | qué contesta |
|---|---|---|
| **naturaleza** de la ausencia | `solicitudes_ausencia.tipo_id` | ¿por qué faltó? (enfermedad, personal…) |
| **calificación** | `solicitudes_ausencia.justificada` (bool) | ¿está justificada? |
| **impacto en la métrica** | `tipos_ausencia.cuenta_ausentismo` | ¿computa en la tasa? |

"Injustificada" es un valor del **segundo** eje ocupando una fila del **primero**. Consecuencias
concretas, no teóricas:

- Una ausencia con `tipo="Injustificada"` y `justificada=true` es representable y **no significa
  nada**. La base la acepta.
- Una ausencia por enfermedad sin certificado no tiene tipo: es `tipo="Enfermedad"` +
  `justificada=false`, o es `tipo="Injustificada"` y se pierde que fue por enfermedad. **Las dos
  cargas son razonables y dan reportes distintos.** Eso es un modelo ambiguo.
- `_reporte_ausentismo` ya calcula el ausentismo injustificado leyendo **`justificada`**, no el
  tipo. O sea que el eje correcto ya está en uso, y el tipo "Injustificada" no participa del
  cálculo: es vocabulario redundante que solo puede contradecirlo.

**Recomendación: desactivarlo (`activo=false`), no borrarlo.** La FK `solicitudes_ausencia.tipo_id`
no tiene `ON DELETE` y el repo ya documenta que por eso **no existe baja física**
(`tipos_ausencia_service.py:8`). Con 0 ausencias no hay nada que reasignar; con datos cargados,
esto sería un UPDATE masivo de `tipo_id` + `justificada`. **Es el mejor argumento de todo el
documento para hacerlo ahora.**

## (e) Los consumidores de `tipo_id` — qué cambia en cada uno

| Consumidor | Archivo | Qué cambia |
|---|---|---|
| **Repo de ausencias** | `repositories/ausencias_repo.py:28,39,54` | El `tipo_map` del enriquecido pasa a traer también el padre → `tipo_padre_nombre`. El **filtro `.eq("tipo_id")` es el cambio de fondo**: filtrar por un padre tiene que traer las de sus hijos → `.in_("tipo_id", [padre, *hijos])`. Un `.eq` dejaría el filtro por padre devolviendo cero |
| **Service / export** | `ausencias_service.py:47,53,56,58` | Nada estructural: `tipo_id` sigue siendo un `Optional[UUID]`. El export gana una columna "Tipo general" |
| **Write** | `_ausencias_write.py:46,71` | Nada, si la ausencia sigue apuntando a UN tipo (la hoja). **Es un argumento fuerte para NO poner `subtipo_id` como segunda FK**: duplicaría el eje |
| **🟡 R10 ausentismo** | `services/reportes/_reporte_ausentismo.py:75-77` | El embed `tipos_ausencia(cuenta_ausentismo)` **sigue funcionando igual** (la ausencia apunta a la hoja y la hoja tiene la columna). Lo que cambia es que hoy agrupa **por área**; agrupar por tipo padre sería un reporte NUEVO, no una modificación |
| **⚠️ `_postgrest_schema`** | `tests/_postgrest_schema.py` | El validador lee `db/schema.sql`. 🔴 Un embed nuevo `tipos_ausencia!...(padre_id...)` **puede volverse ambiguo (PGRST201)**: al agregar la self-FK habrá DOS relaciones entre `tipos_ausencia` y sí misma. Es exactamente el caso que ese validador existe para atrapar. **Hay que nombrar la FK en el embed** |
| **Auditoría** | `services/_audit_payloads.py:54` | `tipo_id` ya está en la lista de campos del diff. Sin cambios |
| **Modal de carga** | `AusenciaModal.tsx` (149/150) | 🔴 De un `<select>` a **dos encadenados** (padre → hijo, el segundo solo si el padre tiene hijos). **El archivo está en 149/150: hay que dividir antes de tocarlo** |
| **Filtros** | `useFiltrosAusencias.ts` (93/80 — 🔴 ya over-limit para un hook) | El filtro de tipo pasa a ofrecer padres e hijos. La resolución "padre → sus hijos" va **server-side** (invariante 1 del Bloque B: si afecta al export, va server-side) |
| **Panel de config** | `TiposAusenciaSection.tsx` (78) + `TipoAusenciaFila.tsx` (60) | Ver (f) |

## (f) El panel de configuración con jerarquía, sin árbol

**Lista de dos niveles con indentación, no un árbol.** Concretamente: la misma `<ul>` que hoy,
donde cada padre arrastra sus hijos indentados debajo, y el alta de un hijo es un botón "+ subtipo"
en la fila del padre.

Por qué eso y no un árbol:
- **La profundidad es 2 y está garantizada** (ver (b)). Un componente de árbol resuelve
  profundidad arbitraria: expandir/colapsar, drag&drop, estado por nodo. Todo eso es para un
  problema que no existe.
- El componente ya está partido en `TiposAusenciaSection` (orquestador, 78) + `TipoAusenciaFila`
  (presentacional, 60), que es la forma correcta: **el hijo se renderiza con la MISMA
  `TipoAusenciaFila`**, con un prop de indentación. Cero componentes nuevos.
- ⚠️ **Con 4 padres y ~10 hijos, todo entra en pantalla sin colapsar.** Si el catálogo real
  llegara a decenas de subtipos, ahí sí conviene colapsar por padre — pero es una decisión que se
  toma con el catálogo cargado, no antes.

## (g) Líneas de todo lo que se toca — Parte A

| Archivo | Hoy | Límite | Estado |
|---|---:|---:|---|
| 🔴 `frontend/.../ausencias/AusenciaModal.tsx` | **149** | 150 | **Dividir ANTES de tocarlo.** El select encadenado no entra |
| 🔴 `frontend/.../ausencias/useFiltrosAusencias.ts` | **93** | **80** | **YA está over-limit** (es un hook). Hay que dividirlo igual |
| `repositories/ausencias_repo.py` | 96 | 100 | ⚠️ 4 de margen. El `.in_()` y el enriquecido del padre no entran cómodos |
| `services/tipos_ausencia_service.py` | 88 | 150 | ✅ |
| `repositories/tipos_ausencia_repo.py` | 67 | 100 | ✅ |
| `services/ausencias_service.py` | 88 | 150 | ✅ |
| `services/reportes/_reporte_ausentismo.py` | 82 | 150 | ✅ (no cambia salvo que se pida el reporte por padre) |
| `frontend/.../TiposAusenciaSection.tsx` | 78 | 150 | ✅ |
| `frontend/.../TipoAusenciaFila.tsx` | 60 | 150 | ✅ |
| `db/schema.sql` + migración | — | — | 1 columna + guardas |

---

# PARTE B — Asignar equipos a proyectos

## (h) Cómo funciona hoy

**Single** — `POST /api/proyectos/{id}/asignaciones` → `AsignacionesService.asignar` →
`_asignar_uno`. Valida proyecto, resuelve `empleado_empresa_id` **del empleado** (permite cruce
multi-empresa a propósito), rechaza empleados en `baja`, y detecta el duplicado por el UNIQUE
`uq_proyecto_empleado`, no por un SELECT previo.

**Bulk** — `POST /api/proyectos/{id}/asignaciones/bulk`
(`routers/proyecto_asignaciones.py:41`, `asignaciones_service.py:93-109`):

```python
AsignacionBulkCreate:  empleado_ids: List[UUID] · rol · valor_hora · fecha_desde · fecha_hasta
AsignacionBulkResult:  asignados: List[AsignacionResponse] · errores: List[{empleado_id, motivo}]
```

Valida el proyecto **una sola vez** y después itera llamando a `_asignar_uno`. **No aborta**:
clasifica en asignados y errores por empleado (patrón nómina). Devuelve 201.

**Modal** — `AsignarEmpleadosModal.tsx` (136). Trae candidatos activos de **todas** las empresas
(`empresaId: "todas"`), acotados por área **server-side**, con búsqueda por texto client-side, y
un set de seleccionados. Los datos de la asignación (rol, valor_hora, fechas) se piden **una vez
para todos**.

## (i) 🔴 "Equipo" no existe — verificado en producción

`empleados.equipo` es **texto libre**, y en producción está **0 de 19 poblado**. Cero.

⇒ **CLAUDE.md sigue teniendo razón**: *"Campo `equipo` (texto libre): sin tabla `equipos`,
'asignar/importar por equipo' no existe"*. No es una limitación teórica: **no hay ni un valor que
agrupar**. Un botón "asignar equipo completo" hoy no tendría nada que ofrecer.

**Entonces son dos trabajos distintos, y hay que elegir cuál se pide:**

| | Qué es | Costo | Qué habilita |
|---|---|---|---|
| **Asignar por ÁREA** | El área ya existe como entidad (`areas`), con FK desde `empleados`, y **19/19 empleados la tienen cargada**. El modal YA filtra por área server-side | **Bajo.** Un endpoint que resuelva "empleados del área X" —que **ya existe**: `repositories/_scope_filtros.empleados_de_area`— y lo pase al bulk que ya está | "Sumá a todo Sistemas a este proyecto" |
| **Crear la entidad EQUIPO** | Tabla `equipos` + pertenencia (¿1:N o N:M?) + ABM + migrar el texto libre (que está vacío, así que no hay nada que migrar) + poblarlo a mano | **Alto.** Tabla, repo, service, router, ABM en el panel, y **el trabajo de RRHH de definir y cargar los equipos** | "Sumá al equipo Core a este proyecto" |

🔴 **El dato nuevo de Franco —"un equipo da servicio a VARIOS proyectos"— es un argumento a favor
de la entidad, no en contra**, y además define su forma: si un equipo trabaja con varios
clientes, la relación equipo↔proyecto es **N:M**, y el equipo es una agrupación estable de
personas independiente del proyecto. Eso NO se puede representar con `empleados.equipo` (un
empleado, un texto), pero tampoco lo pide el área.

**Recomendación: hacer "asignar por área" primero, y tratar "equipos" como proyecto aparte.**
No porque equipos no sirva, sino porque el área **ya tiene los datos cargados** y el equipo no
tiene ninguno: construir la entidad hoy entrega una pantalla vacía que depende de que RRHH
defina y cargue los equipos — el mismo bloqueante que ya tiene frenados los reportes.

⚠️ **Y hay una pregunta de producto previa a la entidad que conviene hacerle a Franco ahora:**
¿un "equipo core que trabaja con varios clientes" es una agrupación **de personas** (Core = Ana,
Beto, Caro) o es **el área misma** con otro nombre? Si en la práctica los equipos coinciden con
las áreas, la entidad no agrega nada y el trabajo es solo el de (h). Con `equipo` en 0/19 no hay
forma de saberlo desde la base.

## (j) 🔴 La "decisión registrada" — no fue una decisión

**Buscada y encontrada en dos lugares, ninguno con un motivo:**

1. `CLAUDE.md:550` — *"El área filtra candidatos, NO asigna."* Entró en el commit **`9a7f184`**,
   que es `docs: actualizar y compactar CLAUDE.md`. Una tanda de documentación, no de diseño.
2. `AsignarEmpleadosModal.tsx:25` — *"El área FILTRA la lista de candidatos (no asigna el área
   completa)."* Entró en **`c3666b0`**, el commit que creó la feature.

⇒ **El comentario del modal DESCRIBE lo que se implementó. La línea de CLAUDE.md copió esa
descripción y, al escribirla en mayúsculas y en un documento de reglas, la convirtió en norma.**
No hay un "por qué" registrado en ningún lado. Es un caso de descripción que se volvió decisión —
y por eso mismo, revisarla no es revertir una decisión: es tomarla por primera vez.

**Ahora bien, hay un motivo real que nadie escribió, y NO se puede ignorar:**

> **¿"Asignar el área" es una FOTO o un VÍNCULO VIVO?**

- **Foto (snapshot):** se resuelven los empleados del área *en ese momento* y se crean N
  asignaciones individuales. Un empleado que entra al área mañana **no** queda asignado.
- **Vínculo vivo:** el proyecto queda asociado al área, y quién está asignado se deriva de quién
  está en el área hoy. Un alta en el área entra sola al proyecto.

🔴 **La segunda rompe cosas que hoy funcionan.** `proyecto_asignaciones` lleva `rol`,
`valor_hora`, `fecha_desde/hasta` **por persona**, y `horas_proyecto` cuelga de una asignación
concreta: un vínculo vivo no tiene dónde poner el valor hora de alguien que todavía no entró, y
**quitar a una persona del área le borraría una asignación con horas cargadas** — que es
justamente lo que `delete` protege hoy con `ASIGNACION_CON_HORAS` (409).

⇒ **Recomendación: FOTO.** "Asignar el área" es un atajo de UI que resuelve la lista y llama al
bulk que ya existe. **Y con eso, la regla vieja sigue siendo cierta donde importaba** —el área no
crea un vínculo estructural con el proyecto— **y deja de ser cierta donde molestaba**: sí puede
sembrar una selección. No hay contradicción con lo registrado; hay una precisión que faltaba.

## (k) El duplicado en el alta masiva — **ya está cubierto**

`_asignar_uno` no chequea antes: intenta el INSERT y traduce la violación del UNIQUE
(`asignaciones_service.py:84-87`):

```python
if "uq_proyecto_empleado" in str(exc):
    raise AppError("El empleado ya está asignado a este proyecto", "ASIGNACION_DUPLICADA", 409)
```

En el bulk ese `AppError` lo captura el `except` del loop y se convierte en una entrada de
`errores` con el motivo legible. **El lote no se corta y el resto se asigna.**

⚠️ **Pero el mensaje va a ser el problema de UX del alta por área.** Hoy el duplicado es un caso
raro (el usuario elige a mano y ve la lista). Asignando un área entera, **lo normal va a ser que
la mitad ya esté asignada**, y el resultado va a mostrar 15 "errores" que no son errores. **Con
el modelo actual eso ya funciona, pero se lee como un fallo masivo.**

**Recomendación:** distinguir el duplicado del resto en el resultado —`ya_asignados` aparte de
`errores`, exactamente como el envío de mails separó `omitidos` de `fallidos`— o filtrar los ya
asignados antes de armar la selección. La primera es más honesta: el backend informa lo que pasó
y la UI decide cómo mostrarlo. **No es un cambio del bulk, es un campo más en el resultado.**

## (l) `valor_hora`, `fecha_desde`, `fecha_hasta` en un alta masiva

**Verificado en producción:** 19 asignaciones, **`valor_hora` distinto de cero en 0**,
`fecha_desde` no nula en **0**, todas `activo=true`. O sea: los tres campos existen y **ninguno
tiene un valor real**.

⚠️ **Corrección respecto de cómo estaba planteado:** `valor_hora` es **`NOT NULL`** en la base
(no nullable). Las 19 filas tienen **0**, que es el default del schema — no están "vacías", están
en cero. La distinción importa: no se puede dejar sin dato, hay que mandar algo.

**El bulk actual ya los pide UNA VEZ PARA TODOS** (`AsignacionBulkCreate`, cuyo docstring lo dice:
*"varios empleados con los MISMOS rol/valor_hora/fechas (compartidos)"*), y el modal los expone
como cuatro campos únicos arriba de la selección.

**Recomendación: mantener exactamente eso, y no pedir nada nuevo.** Razones:
1. Es lo que ya funciona y lo que el schema espera.
2. **Un valor hora por persona en un alta masiva es un formulario de 20 filas** — y con 0 datos
   reales cargados, no hay ninguna evidencia de que haga falta.
3. `rol` compartido es más discutible (las personas de un área tienen roles distintos), pero
   **eso se edita después por asignación** (`PUT /asignaciones/{id}` ya existe), que es el flujo
   correcto: asignar en masa, ajustar el caso particular.

🚩 **Lo que sí hay que decidir con RRHH:** si `valor_hora=0` significa "gratis" o "todavía no lo
sabemos". Hoy son indistinguibles y el reporte de costos los suma igual. No es de esta tanda,
pero es la misma clase de problema que `manager_id` en 0/19: un default que se lee como dato.

## (m) Líneas de todo lo que se toca — Parte B

| Archivo | Hoy | Límite | Estado |
|---|---:|---:|---|
| `routers/proyecto_asignaciones.py` | 63 | 80 | ✅ 17 de margen — un endpoint más entra |
| `routers/proyectos.py` | 66 | 80 | ✅ (no se toca si el endpoint va en el de asignaciones) |
| ⚠️ `services/asignaciones_service.py` | **139** | 150 | **11 de margen.** El resolver por área + separar `ya_asignados` no entra cómodo. Molde de corte listo: `_asignaciones_bulk.py`, como `_vacaciones_write` |
| `services/proyectos_service.py` | 93 | 150 | ✅ |
| `repositories/proyectos_repo.py` | 74 | 100 | ✅ |
| `repositories/_scope_filtros.py` | — | 100 | ✅ **`empleados_de_area` YA EXISTE**: el resolver no hay que escribirlo |
| `schemas/proyectos.py` | — | 200 | +1 campo en `AsignacionBulkResult` |
| `frontend/.../AsignarEmpleadosModal.tsx` | 136 | 150 | ⚠️ 14 de margen. Un botón "seleccionar toda el área" entra; un flujo nuevo, no |

**Sin migración**, si se hace "asignar por área" (foto). **Con migración**, si se crea la entidad
equipo — y ahí son varias tablas.

---

# TRANSVERSAL

## (n) ¿Se pisan? No. Y hay un orden claro por otro motivo

**Son independientes**: no comparten tablas, ni services, ni endpoints, ni pantallas. Se pueden
hacer en cualquier orden o en paralelo sin conflicto de merge.

**Pero el orden lo decide una ventana que se cierra sola:**

1. 🔴 **PARTE A PRIMERO, y no por dependencia técnica: por los datos.** `solicitudes_ausencia`
   está en **0 filas**. Cambiar el modelo de ausencias hoy es un `ALTER TABLE` + `INSERT` de
   catálogo. En cuanto RRHH cargue el histórico —que es un pendiente activo, junto con el import
   de vacaciones/ausencias que está esperando definición del parser— la misma migración se
   convierte en una reasignación de `tipo_id` sobre filas vivas. **El costo de A se multiplica
   con el tiempo; el de B no.**
2. **PARTE B después**, y **acotada a "asignar por área"**. Los 19 empleados ya tienen área
   cargada, así que se puede probar el día que se termina.
3. **"Equipos" como entidad: proyecto aparte**, y no antes de que Franco conteste si un equipo es
   una agrupación de personas distinta del área (ver (i)).

⚠️ **Un solapamiento menor, que no es conflicto pero conviene saber:** las dos partes tocan
archivos que están al filo (`AusenciaModal` 149/150, `useFiltrosAusencias` 93/80 ya pasado,
`asignaciones_service` 139/150). **Ninguno de los tres es compartido entre A y B**, así que las
divisiones no se estorban.

## (o) Próximo número de migración libre: **088**

🚩 **Y la buena noticia: NO se acumulan.** Verificado contra el catálogo vivo, **las dos ya están
corridas en producción**:

| | Evidencia en producción |
|---|---|
| **086** `empleado_superior_pendiente` | ✅ la tabla existe |
| **087** `mails_plantillas_y_remitente` | ✅ `usuario_integraciones.es_remitente_sistema` existe · `plantillas_mail` y `mail_enviado` existen (2/2) |
| **085** (referencia) | ✅ `tipos_ausencia.cuenta_ausentismo` existe |

- `backend/migrations/` llega a **087**; `migracionAWS/backend/migrations/` tiene 075-077.
- Máximo global **087**, sin huecos reusables ⇒ **próximo libre: 088.**
- **Parte A necesita la 088** (el `padre_id` + las guardas + desactivar "Injustificada").
- **Parte B no necesita migración** en la variante recomendada (asignar por área).

---

## Apéndice — inventario, para no re-diagnosticar

**Parte A:** catálogo vivo `tipos_ausencia` (4 filas, todas globales, `cuenta_ausentismo=true`) ·
**`solicitudes_ausencia` = 0 filas** · `migrations/085` líneas 161-171 (la columna) ·
`repositories/ausencias_repo.py:28,39,54` (enriquecido y filtro) ·
`services/reportes/_reporte_ausentismo.py:75-77` (el embed sin hint) ·
`services/tipos_ausencia_service.py:8` (por qué no hay baja física) ·
`tests/_postgrest_schema.py` (el validador que va a ver la self-FK) ·
front: `AusenciaModal.tsx` 149 · `useFiltrosAusencias.ts` 93 · `TiposAusenciaSection.tsx` 78 ·
`TipoAusenciaFila.tsx` 60.

**Parte B:** `services/asignaciones_service.py:43,63,93` (single, `_asignar_uno`, bulk) ·
`:84-87` (el duplicado por UNIQUE) · `schemas/proyectos.py:101-117` (los tres schemas del bulk) ·
`routers/proyecto_asignaciones.py:41` · `repositories/_scope_filtros.empleados_de_area` (ya
existe) · `AsignarEmpleadosModal.tsx:25` y `CLAUDE.md:550` (la "decisión") ·
commits `c3666b0` (feature) y `9a7f184` (docs) · catálogo vivo: `empleados.equipo` **0/19**,
`proyecto_asignaciones` 19 filas / `valor_hora` 0 en todas / `fecha_desde` nula en todas /
6 proyectos, 5 con gente.

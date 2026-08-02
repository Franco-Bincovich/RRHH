# Diagnóstico READ-ONLY — asignar empleados a un proyecto por ÁREA

> **2/8/2026 · Paso 1. NO se escribió una sola línea de código.**
> Verificado contra los archivos fuente **y contra el catálogo vivo de producción**.

---

## (a) El bulk actual

**Endpoint** — `POST /api/proyectos/{proyecto_id}/asignaciones/bulk`
(`routers/proyecto_asignaciones.py:41`), gate `Seccion.PROYECTOS + WRITE`, status 201.

**Qué recibe** (`schemas/proyectos.py:101-107`):

```python
class AsignacionBulkCreate:
    empleado_ids: List[UUID]
    rol: str
    valor_hora: float = 0.0   # ge=0
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
```

El docstring lo dice explícito: *"varios empleados con los MISMOS rol/valor_hora/fechas
(compartidos)"*.

**Qué devuelve** (`:115-117`):

```python
class AsignacionBulkResult:
    asignados: List[AsignacionResponse]
    errores:   List[AsignacionBulkError]   # {empleado_id, motivo}
```

**Cómo clasifica el éxito parcial** (`services/asignaciones_service.py:93-109`):

1. Valida el proyecto **UNA sola vez** contra `empresa_id` → 404 `PROYECTO_NOT_FOUND` si no es de
   la empresa del request. Es la barrera de empresa del endpoint.
2. Itera `_asignar_uno` empleado por empleado, **sin abortar**: cada `AppError` se convierte en
   una entrada de `errores` con su mensaje legible.
3. Los tres motivos que hoy caen en `errores`:
   - `EMPLEADO_NOT_FOUND` (404) — el id no existe.
   - `EMPLEADO_INACTIVO` (422) — el empleado está en `baja`.
   - `ASIGNACION_DUPLICADA` (409) — ya estaba asignado. **Se detecta por la violación del UNIQUE
     `uq_proyecto_empleado`, no por un SELECT previo** (`:84-87`), y esa es una buena decisión:
     un chequeo previo tendría una ventana de carrera.

**El front ya sabe que están mezclados** — `AsignarEmpleadosModal.tsx:74` dice literalmente
*"N no se pudieron (ya asignados o inactivos)"*. Es la evidencia de que la separación que se pide
en el paso 2 no es un capricho: el mensaje actual ya tuvo que hacer esa aclaración a mano.

---

## (b) Dónde entra el alta por área: **endpoint propio, service COMPARTIDO**

**No un modo del bulk existente.** Meter `area_id` como alternativa de `empleado_ids` en
`AsignacionBulkCreate` obligaría a un schema donde *exactamente uno de dos campos* debe venir:
Pydantic lo puede expresar, pero el error que sale es peor que un 404 claro, y cada caller pasa a
tener que conocer la regla. Dos endpoints con dos contratos simples se leen mejor que uno con una
condición.

**Propuesta:**

```
POST /api/proyectos/{proyecto_id}/asignaciones/area
     body: { area_id, rol, valor_hora, fecha_desde, fecha_hasta }
```

🔴 **Pero la CLASIFICACIÓN tiene que ser una sola.** El endpoint de área resuelve los ids del área
y delega en **la misma función** que el bulk. Si cada uno clasificara por su cuenta, el día que
se agregue un motivo nuevo quedaría en uno solo — el patrón de "la misma regla escrita dos veces"
que este repo ya pagó con los filtros front/back.

### 🔴 Consecuencia que hay que aceptar antes de escribir: `ya_asignados` cambia el bulk existente

Separar "ya asignados" de "errores" en el tipo COMPARTIDO `AsignacionBulkResult` mejora también
el bulk manual (deja de reportar como error algo que no lo es). Es **aditivo** —un campo nuevo,
nada se saca— pero **es un cambio de comportamiento observable en una feature que hoy funciona**:
el modal existente va a mostrar menos "errores" que antes.

Es lo correcto y hay que decirlo, no descubrirlo después. La alternativa —dejar el bulk como está
y que solo el de área tenga tres grupos— produce dos formas distintas de reportar lo mismo, que
es peor.

---

## (c) 🔴 ¿Mostrar cuánta gente trae el área? **SÍ, y el reparto real lo vuelve más necesario**

**Verificado en producción — las 9 áreas:**

| área | empleados |
|---|---:|
| SALUD | **9** |
| RECUPERO SUPERINTENDENCIA Y OBRAS SOCIALES | 2 |
| ADMINISTRACION | 2 |
| ANALISIS · GESTION DE DEUDA · FACTURACION · TECNICA, LEGAL Y TRIBUTARIA · CAPITAL HUMANO · GD - GESTION DE DEUDA | **1 cada una** |

**6 de 9 áreas tienen una sola persona.** Sin el conteo, "asignar el área ANALISIS" se lee como
una operación masiva y asigna a una persona; "asignar SALUD" asigna a 9 de golpe. **Las dos
acciones se ven idénticas antes de apretar**, y una es reversible de a una y la otra no tanto
(quitar una asignación con horas cargadas está bloqueado por `ASIGNACION_CON_HORAS`).

**Y hay un dato mejor que el conteo bruto: cuántos QUEDAN por asignar.** Con la mitad del área ya
en el proyecto, "trae 9" es engañoso: van a crearse 4. Mostrar *"9 en el área · 5 ya asignados ·
se van a agregar 4"* es la única versión que no sorprende.

✅ **Y es gratis.** `AsignarEmpleadosModal.tsx:44-48` ya hace
`fetchEmpleados({ areaId: areaFiltro })` cada vez que cambia el área, y ya tiene la lista de
asignados del proyecto. **El conteo sale de datos que el modal ya tiene: cero requests nuevos.**

🚩 **Hallazgo al pasar:** `GESTION DE DEUDA` y `GD - GESTION DE DEUDA` son casi con seguridad la
misma área duplicada por el import de nómina (una por cada grafía del CSV). No es de esta tanda,
pero conviene que RRHH lo mire: con áreas duplicadas, "asignar el área" asigna a la mitad.

---

## (d) El corte de `asignaciones_service.py` (139/150)

**No entra.** Lo que hay que sumar: resolver el área (+3), la barrera del área (+4), la
clasificación en tres grupos (+8), la firma y el docstring del método nuevo (+10). Son ~25 líneas
contra 11 de margen.

**Corte propuesto — `services/_asignaciones_bulk.py`**, que ya estaba identificado:

| queda en `asignaciones_service.py` | se va a `_asignaciones_bulk.py` |
|---|---|
| `get_by_proyecto`, `asignar` (single), `_asignar_uno`, `update`, `delete` | `asignar_bulk`, `asignar_area`, y la clasificación en tres grupos |

Molde: `_vacaciones_write.crear(repo, periodos, ownership, data, ...)` — funciones libres que
reciben los colaboradores por parámetro; el service las delega en una línea. Resultado estimado:
`asignaciones_service` ~105, `_asignaciones_bulk` ~90.

⚠️ `_asignar_uno` **se queda** en el service: lo usan el alta single y el bulk. Moverlo obligaría
a que el service importe del módulo al que delega, que es un ciclo de lectura innecesario.

**Otros archivos y su margen:**

| Archivo | Hoy | Límite | |
|---|---:|---:|---|
| `services/asignaciones_service.py` | **139** | 150 | 🔴 hay que cortar |
| `routers/proyecto_asignaciones.py` | 63 | 80 | ✅ un endpoint más entra |
| `schemas/proyectos.py` | 145 | 200 | ✅ |
| `repositories/_scope_filtros.py` | 84 | 100 | ✅ **no se toca**: `empleados_de_area` ya existe |
| `frontend/.../AsignarEmpleadosModal.tsx` | 136 | 150 | ⚠️ **14 de margen.** El conteo + el botón de área entran justos; si se suma el desglose "ya asignados", hay que cortar |
| `frontend/services/proyectos.ts` · `types/proyecto.ts` | — | 200 | ✅ |

---

## (e) ¿Migración? **No, y está verificado**

`proyecto_asignaciones` ya tiene todo lo que hace falta (columnas confirmadas contra el catálogo
vivo): `proyecto_id`, `empleado_id`, `empleado_empresa_id`, `rol`, `valor_hora`, `fecha_desde`,
`fecha_hasta`, `activo`. El alta por área **no agrega un solo dato nuevo**: resuelve una lista de
ids y usa el camino de escritura que ya existe.

⚠️ Recordatorio de la sesión anterior: `valor_hora` es **NOT NULL** con default 0 — las 19 filas
de producción están en 0. No es "vacío", es cero, y el reporte de costos lo suma.

---

## 🔴 La composición de la barrera de empresa — lo que pediste verificar ANTES de escribir

Hoy hay **dos ejes distintos** y conviene no confundirlos:

```
_asignar_uno (asignaciones_service.py:63-91):
    empleado_empresa_id = find_empresa_for_empleado(empleado_id)   ← la del EMPLEADO
    repo.save(proyecto_id, empleado_id, empleado_empresa_id, ...)
```

- **El PROYECTO** se valida contra el `empresa_id` del request (404 si es de otra empresa). Esa
  es la barrera del endpoint y no cambia.
- **El EMPLEADO puede ser de OTRA empresa**, a propósito: el encabezado del service lo declara
  (*"Un empleado puede pertenecer a una empresa distinta a la dueña del proyecto → permitido"*) y
  por eso existe la columna `empleado_empresa_id`, que guarda la del empleado y no la del
  proyecto.

### 🔴 De ahí sale la decisión que hay que tomar bien: qué barrera lleva el ÁREA

El `area_id` es **un id de recurso que llega de afuera**, así que por la regla permanente de
Fase 2 necesita su propia barrera. Pero **no se puede resolver pasándole el `empresa_id` a
`empleados_de_area`**, que es lo que parece natural:

```python
empleados_de_area(area_id, empresa_id)   # ⚠️ NO
```

Si el área fuera de otra empresa, eso devuelve **lista vacía**: el endpoint respondería
"0 asignados, 0 errores" sin decir nada. Es exactamente el patrón de **filtro que falla en
silencio** que ya apareció dos veces en este repo (el índice de superiores acotado por empresa, y
`proyecto_ids_con_area`). Un recorte que se lee como un resultado.

**La composición correcta, en dos pasos separados:**

1. **Validar el área contra el `empresa_id` del request** → 404 `AREA_NOT_FOUND` si no es de esa
   empresa. Mismo literal y mismo status que "no existe" (regla del 404 idéntico). Ya hay helper:
   `services/_empleados_utils.ensure_area_valida`.
2. **Resolver los empleados SIN filtro de empresa**: `empleados_de_area(area_id)`. Los empleados
   de un área son de la empresa del área por construcción (`ensure_area_valida` lo garantiza en
   toda escritura), así que el filtro sería redundante — y redundante-pero-silencioso es peor que
   ausente.

⚠️ **En modo consolidado (`empresa_id=None`) el paso 1 no restringe**, que es la semántica de
`get_empresa_id`. Un usuario en "Todas las empresas" puede asignar un área de la empresa B a un
proyecto de la A — y **eso es correcto**, es el mismo cruce que el modelo ya soporta.

⚠️ **Hoy eso NO se puede probar con datos reales: las 9 áreas están todas en la MISMA empresa**
(hay una sola empresa en producción). El caso cruzado vive solo en los tests hasta que exista la
segunda.

---

## Casos borde que ya están resueltos y NO hay que reimplementar

| Caso | Qué pasa hoy | ¿Alcanza? |
|---|---|---|
| Empleado en **baja** dentro del área | `EMPLEADO_INACTIVO` (422) → entra en `errores` | ✅ correcto: con un área entera es esperable, y avisa cuál |
| Empleado **ya asignado** | `ASIGNACION_DUPLICADA` (409) por el UNIQUE | ✅ el mecanismo sirve; lo que cambia es **dónde se reporta** (grupo propio) |
| Asignación **con horas cargadas** | `ASIGNACION_CON_HORAS` (409) bloquea el `delete` | ✅ **y es la razón de que esto sea FOTO y no vínculo vivo**: un vínculo vivo borraría esa asignación al sacar a la persona del área |
| **Área vacía** | — | 🔴 **No está resuelto**: hoy no existe el camino. Tiene que dar un mensaje claro ("el área no tiene empleados"), no un 200 con tres listas vacías que se lee como "no hizo nada" |

---

## Resumen de lo que el paso 2 tiene que hacer

1. `services/_asignaciones_bulk.py` (corte de (d)) con la clasificación en **tres grupos**,
   compartida por el bulk manual y el de área.
2. `ya_asignados` en `AsignacionBulkResult` — aditivo, y cambia el mensaje del modal existente.
3. Endpoint `POST /{proyecto_id}/asignaciones/area`.
4. Barrera: **área validada contra el header** (404), **empleados resueltos sin filtro de empresa**.
5. Área vacía → mensaje propio, no un resultado vacío.
6. UI: cuánta gente trae el área **y cuántos ya están**, con datos que el modal ya tiene.
7. Corregir la línea de `CLAUDE.md:550`.
8. **Sin migración.**

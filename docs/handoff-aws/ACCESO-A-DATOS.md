# Acceso a datos — dónde está y qué hay que portear

> **Escrito el 12/8/2026, sesión 0.9.** El trabajo del cutover es reescribir la capa de acceso a
> datos de Supabase SDK a asyncpg. Este documento dice **exactamente dónde vive** ese acceso, sin
> que haya que descubrirlo.

---

## El número

Barrido por AST sobre `backend/`, buscando `.table()` y `.rpc()`:

| | Archivos | Llamadas |
|---|---:|---:|
| `repositories/` | 73 | **328** |
| Fuera de `repositories/` (todo en `services/`) | 19 | **58** |
| **Total** | **92** | **386** |

*(Más 2 en `tests/`, que son fakes y no cuentan. El total de 388 del diagnóstico incluía las 4
fugas que esta sesión movió: dos crearon método nuevo en su repo y dos se resolvieron reusando
uno que ya existía, así que la cuenta bajó de 388 a 386 sin perder ninguna consulta.)*

**El 85% del acceso está contenido en `repositories/`.** Si porteás solo esa carpeta, se te
escapan 58 llamadas en 19 archivos — todas en `services/`, todas inventariadas abajo.

**Routers, middleware, utils, scripts, config y schemas están en CERO.** La regla se respeta en
las capas de entrada; lo que queda afuera es analítico.

> ✅ **Hay un barrido que lo mantiene así:** `backend/tests/test_acceso_a_datos.py`. Recorre por
> AST todas las capas que no son `repositories/` y rojea si aparece una query fuera de las **4
> familias declaradas**. Si al portar nace un service con acceso directo, salta ahí.

---

## 🔴 Lo primero: los dos catálogos de tabla dinámica

**Son los únicos dos lugares donde el nombre de la tabla NO está en el sitio de la query.** Vive
en una estructura de datos y se resuelve en runtime, así que **un porteo por búsqueda y reemplazo
no los ve**.

### 1. `services/procesos_service.py:111` — catálogo `_META` (línea 23)

```python
_META: List[tuple[str, str, str]] = [
    ("onboarding_instancias", "onboarding", "Onboarding"),
    ("offboarding_instancias", "offboarding", "Offboarding"),
    ("vacantes", "vacantes", "Vacantes"),
    ("empleado_capacitacion", "capacitaciones", "Capacitaciones"),
    ("objetivos", "objetivos", "Objetivos"),
]
...
q = supabase_admin.table(tabla).select("id", count="exact").eq("estado", estado)
```

🔴 **Este es el que ya rompió producción.** Cuando el bloque J5a borró las tablas `ev_*`, el
Panel de Procesos **murió entero con un 500 `PROCESOS_ERROR`** — no degradó una tarjeta, se cayó
la pantalla completa, porque el catálogo iteraba sobre una tabla que ya no existía y no hay
`try` por ítem.

**Qué significa para el porteo:** si una de esas 5 tablas cambia de nombre, se particiona o
desaparece, el fallo aparece **en runtime y en producción**, no en el porteo. Y el `count="exact"`
de PostgREST no tiene equivalente directo en asyncpg: es un `SELECT count(*)` aparte.

### 2. `services/_dashboard_alertas.py:64` — catálogo `BLOQUEOS`

Vive en `services/_dashboard_alertas_catalogo.py:31`, como tuplas `Bloqueo(...)`:

```python
BLOQUEOS: Tuple[Bloqueo, ...] = (
    Bloqueo("costos_nomina", ...), Bloqueo("inventario_items", ...),
    Bloqueo("capacitaciones", ...), Bloqueo("presupuesto_areas", ...),
    Bloqueo("vacantes", ...),
)
...
q = _con_empresa(supabase_admin.table(b.tabla).select("id").limit(1), empresa_id)
```

Mismo patrón, distinto síntoma: acá cada alerta es independiente, así que una tabla faltante
rompe **esa** alerta. Las 5 tablas existen hoy.

> 🔑 **La regla que sale de los dos:** antes de renombrar o dropear una tabla, `grep` de su
> nombre en `services/procesos_service.py` y `services/_dashboard_alertas_catalogo.py`. No
> aparece en ninguna query.

### Los 5 helpers con `table` por parámetro — estos SÍ se resuelven

En `repositories/` hay 5 funciones que reciben la tabla como argumento. **No son el caso
difícil**: sus callers están en el mismo módulo y pasan constantes, así que el nombre se lee del
código.

`_ausencia_row.py:29` · `asignacion_repo.py:15` · `dashboard_equipo_repo.py:46` ·
`evaluacion_repo.py:25` · `_evaluacion_lotes_enrich.py:38`

---

## Inventario de las 58 que quedan afuera

Todas en `services/`. Agrupadas por familia, con archivo:línea.

### Familia REPORTES — 12 archivos, 35 llamadas

| Archivo | Líneas |
|---|---|
| `services/reportes/_reporte_dotacion.py` | 23, 31, 38, 46, 82, 89, 99 |
| `services/_reporte_anual_metricas.py` | 26, 29, 42, 47, 75, 80, 87 |
| `services/reporte_adhoc.py` | 38, 43, 48, 54 |
| `services/reportes/_reporte_costos.py` | 29, 35, 92 |
| `services/reportes/_reporte_saldos.py` | 51, 80, 93 |
| `services/reportes/_reporte_ausentismo.py` | 64, 79 |
| `services/reportes/_reporte_movimientos.py` | 32, 44 |
| `services/reportes/_reporte_seleccion.py` | 20, 69 |
| `services/reportes/_reporte_vacaciones.py` | 39, 53 |
| `services/reportes/_reporte_capacitacion.py` | 24 |
| `services/reportes/_reporte_distribucion.py` | 54 |
| `services/reporte_anual.py` | 28 |

**Qué son:** agregaciones de los 14 reportes — counts, sumas y joins. **Por qué están ahí:** cada
generador arma su propia query, y los embeds se construyen por f-string según haya o no filtro de
área. Ningún repo modela esto, y meterlas en los repos de entidad daría repos con métodos que
solo sirven a un reporte.

⚠️ **Sus `select` con embed anidado los valida `tests/test_reportes_columnas.py`** contra
`db/schema.sql`, con y sin filtro de área. Es el test que hay que mirar si un reporte sale vacío
después del porteo — seis de once ya salieron rotos a producción una vez por un embed ambiguo.

### Familia DASHBOARD — 4 archivos, 13 llamadas

| Archivo | Líneas |
|---|---|
| `services/dashboard_service.py` | 58, 68, 76, 84, 92 |
| `services/_dashboard_kpis.py` | 32, 52, 57, 65 |
| `services/_dashboard_alertas.py` | 64 🔴 *(dinámica)*, 77 |
| `services/_dashboard_headcount.py` | 23, 28 |

**Qué son:** los 9 KPIs del dashboard y las alertas. Counts con filtro de empresa.
⚠️ `dashboard_service` calcula cada KPI con un `_safe`: si uno falla, los demás salen igual. **Un
error de porteo acá no tumba la pantalla, deja una tarjeta vacía** — más difícil de detectar.

### Familia ORGANIGRAMA — 2 archivos, 9 llamadas

| Archivo | Líneas |
|---|---|
| `services/organigrama_proyectos_service.py` | 36, 46, 59, 65, 74, 115 |
| `services/organigrama_service.py` | 29, 37, 47 |

**Qué son:** el árbol de empleados/áreas/empresas y la vista por proyectos, sobre tablas que
**sí tienen repo propio**. 🔴 Es la única familia sin motivo de diseño: no existe repo de
organigrama y la lectura nació en el service.

### Familia PROCESOS — 1 llamada

`services/procesos_service.py:111` — ver arriba.

---

## Dos cosas que NO hay que buscar

### `.rpc()` es CERO en todo el backend

No hay una sola función de Postgres invocada desde la aplicación. Todo el acceso es
tabla + filtros vía PostgREST. **No hay lógica en la base que portear** más allá de la función
`fn_misma_empresa()` de los triggers (ver `db/funciones_y_triggers.sql`) y `set_updated_at()`.

### Supabase Auth es superficie APARTE

Dos services usan `supabase_admin.auth.admin.*`, que **no es PostgREST y no toca `public`**:

- `services/_usuario_alta.py:39,74` — crear y borrar la identidad.
- `services/usuario_service.py:84,132` — cambiar contraseña y banear (`ban_duration`).

**No los cuentes en las 388.** Su reemplazo ya está escrito en `migracionAWS/`: migraciones
**075** (`password_hash`) y **076** (`refresh_tokens`), más `*_NEW.py`. Ver `README_AUTH.md`.

---

## 🔴 Estado: qué puede cambiar y hasta cuándo

**Las 48 llamadas de REPORTES y DASHBOARD son CANDIDATAS a moverse a `repositories/`** si el
trabajo de features termina antes del **6 de septiembre**.

- **Si a esa fecha siguen donde están, se quedan ahí y son tuyas.** No se mueven después.
- **Después del 6 de septiembre no se toca nada de esto.** Moverte el piso mientras porteás es
  peor que dejarlas: preferimos que portees 58 llamadas conocidas a que portees 10 y te
  encuentres con que las otras 48 cambiaron de lugar.

**ORGANIGRAMA (9) y PROCESOS (1)** no están en esa lista: mover organigrama es una decisión de
producto pendiente, y procesos es 1 llamada que no justifica el riesgo.

**Lo que ya no va a cambiar:** las 4 fugas que se movieron el 12/8 (`auth_service`,
`objetivo_service`, `objetivos_import_preview`, `nomina_csv_service`) están cerradas, y el
barrido impide que vuelvan.

---

## Referencias

| Qué | Dónde |
|---|---|
| El barrido que sostiene la regla | `backend/tests/test_acceso_a_datos.py` |
| Validación de columnas y embeds de cada `select` | `backend/tests/test_selects_repos.py` · `test_reportes_columnas.py` |
| Que un service no llame un método inexistente de su repo | `backend/tests/test_contrato_repos.py` |
| El schema contra el que se valida | `backend/db/schema.sql` |
| Storage (superficie aparte, ya centralizada) | `STORAGE.md` |

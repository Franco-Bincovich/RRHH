# Los 4 greps de control — corrida del 25/8/2026

> **Qué es esto.** `README.md` de esta carpeta define cuatro greps que se corren antes de cada
> entrega y manda escribir el resultado acá. Este archivo es ese resultado.
>
> 🔴 **Y trae algo más que los números: la verificación de que los greps NO ESTÁN CIEGOS.** Ya
> lo estuvieron una vez —los cuatro se reescribieron el 19/8/2026 porque cada uno dejaba pasar
> en silencio justo lo que venía a buscar— así que un conteo sin control positivo no prueba
> nada: un grep roto devuelve `0` y se lee igual que "está todo limpio".

## Cómo se verificó la ceguera

Se armó un archivo de control con los patrones canónicos —los que cada grep DEBE encontrar y los
que NO debe encontrar— y se corrió cada grep contra él. **El resultado esperado se escribe antes
de correrlo**; si el grep devuelve otra cosa, el ciego es el grep, no el repo.

```
backend/ctrl.py                       backend/schemas/ctrl.py
  if id == otro                         id: str
  if empleado_id != x                   empresa_id: str
  if fila["id"] == uid                  manager_id: Optional[str]
  supabase_admin.auth.admin...          nombre: str        <- NO debe matchear
  supabase_client.auth...               total: int         <- NO debe matchear
  cli.auth.admin.delete_user()
  data.model_dump()
  data.model_dump(exclude_none=True)
  data.model_dump(mode="json")          <- NO debe matchear
```

---

## Resumen

| # | Qué busca | Hits | Control positivo | Veredicto |
|---|---|---|---|---|
| 1 | Comparaciones de id sin coaccionar los dos lados | 76 (2 fuera de `tests/`) | **2 de 3** | 🟠 **VE PARCIAL** — punto ciego nuevo, abajo |
| 2 | SDK de Supabase Auth remanente | 8 usos + 1 comentario | **2 de 3** | 🟠 **VE PARCIAL** — punto ciego conocido, abajo |
| 3 | Escrituras sin serializar (`model_dump` sin `mode="json"`) | 98 (74 fuera de `tests/`) | **2 de 2** | 🟢 Ve lo que dice ver |
| 4 | IDs tipados `str` en `schemas/` | 89 | **3 de 3** | 🟢 Ve lo que dice ver |

---

## 1 · Comparaciones de id — tiene un punto ciego NUEVO

```bash
grep -rnE "(^|[^_a-zA-Z])(id|[a-z_]+_id)[[:space:]]*(==|!=)" backend/ --exclude-dir=venv
```

**76 hits, y 74 están en `backend/tests/`** — código de test, que no se portea. Fuera de tests
quedan **dos**, y sólo uno es real:

| Dónde | Qué es |
|---|---|
| `services/_audit_payloads_rrhh.py:115` | 🟢 **Falso positivo: es prosa.** La frase `(registro_id == empresa_id)` está dentro de un docstring explicando el diseño |
| `services/_empleados_utils.py:24` | 🟠 **Real, a revisar al portear.** `if existing and existing.id != exclude_id:` — `existing.id` sale de la base y `exclude_id` del payload. Con Supabase los dos llegan `str` y funciona; **con asyncpg `existing.id` llega como `UUID` nativo y `exclude_id` sigue siendo `str`, así que la comparación da SIEMPRE `True`** y la guarda de unicidad deja de reconocer al propio registro cuando se lo edita |

> 🔴 **PUNTO CIEGO NUEVO, medido acá: el grep NO ve las comparaciones por subíndice.**
> `if fila["id"] == uid:` no matchea, porque después de `id` viene `"` y el patrón exige espacio
> o el operador inmediatamente. En un repo cuyos repositorios devuelven **dicts de PostgREST**,
> ése es justamente el acceso más frecuente. Complemento sugerido:
> ```bash
> grep -rnE "\[[\"'](id|[a-z_]+_id)[\"']\][[:space:]]*(==|!=)" backend/ --exclude-dir=venv
> ```

## 2 · SDK de Supabase Auth — sólo ve los clientes que se llaman `supabase*`

```bash
grep -rnE "supabase[a-z_]*\.auth\." backend/ --exclude-dir=venv
```

**8 usos reales en 3 archivos** (+1 mención en un comentario de `db/schema.sql`). Son la
superficie completa de lo que hay que reimplementar del otro lado, porque **en AWS no hay
Supabase Auth**:

| Archivo | Llamada | Qué hay que construir en el destino |
|---|---|---|
| `services/auth_service.py:42` | `sign_in_with_password` | Login contra `users.password_hash` (mig 075) |
| `services/auth_service.py:97` | `refresh_session` | Rotación contra `refresh_tokens` (mig 076) |
| `services/auth_service.py:119` | `admin.sign_out` | Borrar los refresh tokens del usuario |
| `services/_usuario_alta.py:74` | `admin.create_user` | Alta local + hash con `bcrypt` |
| `services/_usuario_alta.py:39` | `admin.delete_user` | El rollback del alta. 🔴 Hoy se apoya en el `ON DELETE CASCADE` contra `auth.users`, que del otro lado no existe |
| `services/usuario_service.py:80` | `sign_in_with_password` | Verificación de la contraseña ACTUAL al cambiarla |
| `services/usuario_service.py:84` | `admin.update_user_by_id` | Set del hash nuevo |
| `services/usuario_service.py:132` | `admin.update_user_by_id` (`ban_duration`) | 🔴 **`ban_duration` NO tiene equivalente.** Es la baja blanda de usuarios: hay que revocar los refresh tokens |

> ⚠️ **Punto ciego conocido y aceptado: sólo ve clientes cuyo nombre empieza con `supabase`.**
> Un `cli.auth.admin.delete_user()` pasa de largo. Hoy el repo no tiene ninguno —los dos únicos
> clientes son `supabase_client` y `supabase_admin`, ambos en `integrations/supabase_client.py`—
> así que el grep es completo **por una propiedad del repo, no del patrón**. Si aparece un
> alias, el complemento es `grep -rnE "\.auth\.(admin\.)?[a-z_]+\(" backend/`.

## 3 · Escrituras sin serializar

```bash
grep -rn "model_dump(" backend/ --exclude-dir=venv | grep -v 'mode="json"'
```

**98 hits; 74 fuera de `tests/`.** Por forma:

| Forma | Hits (sin tests) |
|---|---|
| `model_dump()` | 54 |
| `model_dump(exclude_none=True)` | 16 |
| `model_dump(exclude_unset=True, exclude_none=True)` | 2 |
| `model_dump(exclude_unset=True)` | 2 |

Por capa: **55 en `services/`, 13 en `repositories/`, 3 en `schemas/`, 1 en `utils/`.**

**Qué significa, y por qué NO es una lista de 74 bugs.** `mode="json"` es lo que convierte
`UUID`, `date`, `datetime` y `Decimal` a tipos JSON-serializables. Contra **PostgREST** —que
habla HTTP— hace falta cuando el payload lleva alguno de esos tipos; hoy la mayoría de los `_id`
viajan `str` (ver grep 4), así que el problema está enmascarado.

🔴 **Al portear a asyncpg la conclusión SE DA VUELTA y hay que leer esta lista al revés: contra
la base directa, `mode="json"` es lo que NO se quiere.** asyncpg espera `UUID` y `date` NATIVOS,
y un `str` contra una columna `uuid` es error de query. **La lista útil no es "cuáles hay que
arreglar" sino "estos 74 lugares deciden en qué tipo viaja un dato hacia la base, y hay que
revisarlos uno por uno en el cutover".** Es el trabajo más grande de los cuatro greps.

## 4 · IDs tipados `str` en schemas — el grep ya no es la fuente

```bash
grep -rnE "\b(id|[a-z_]+_id)[[:space:]]*:[[:space:]]*(Optional\[)?str" backend/schemas/
```

**89 hits**, y coinciden exactamente con el inventario del barrido que es la fuente autoritativa,
**`backend/tests/test_ids_tipados.py`**:

| Categoría | Campos | Qué implica |
|---|---|---|
| 🔴 **ENTRADA** | **4** | **Lo único que ROMPE el porteo.** Viajan HACIA la base |
| 🟡 **SALIDA** (`*Response`) | **81** | Cosmético: el valor sale de la base y se serializa. No rompe |
| ⬜ **EXTERNOS** | **4** | Los emite un tercero (Google, Supabase Auth). No son uuid nuestros |

**Los cuatro de ENTRADA, que son la lista que importa:**

1. `costo.PresupuestoCreate.area_id` — 🔴 **el más caro**: el único que viaja a un INSERT real de
   una tabla viva (`presupuesto_area`). Con asyncpg, `str` contra columna `uuid` es error de query.
2. `objetivo_filtros.ObjetivosFiltros.responsable_id` — va a un WHERE, no a un INSERT: rompe la
   LECTURA, no la escritura.
3. `assessment.CampanaCreate.area_id` — módulo apagado por flag; hoy no hay camino hasta la base.
4. `assessment.LinkCreate.empleado_id` — ídem.

> 🔑 **Para este patrón el grep ya no es la fuente, y no hay que usarlo como tal.** Un grep no
> puede distinguir un payload de ENTRADA (rompe) de un `*Response` de SALIDA (no rompe), que es
> **toda** la diferencia. El test hace esa separación, descubre por introspección de Pydantic (un
> schema nuevo entra solo) y lleva guardas de mínimo (>=80 campos, >=35 clases). El grep sirve
> para confirmar que el test no se quedó ciego; el inventario sale del test.

---

## Qué hacer con esto

| | |
|---|---|
| **Antes de cada entrega** | Correr los cuatro y actualizar este archivo |
| **Si un conteo baja mucho de golpe** | Sospechar del grep antes que del repo, y correr los controles positivos de arriba |
| **Antes del cutover a asyncpg** | Los 4 de ENTRADA del grep 4 · el hit real del grep 1 · los 8 del grep 2 · y **revisar los 74 del grep 3 uno por uno** |

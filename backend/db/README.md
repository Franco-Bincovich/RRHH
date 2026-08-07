# Reconstrucción de la base — RRHH / HR Karstec

## `schema.sql` es la fuente de verdad

`backend/db/schema.sql` es el artefacto autoritativo de reconstrucción. Refleja el estado
real de la base de producción, leído directamente del catálogo de Postgres
(`information_schema` / `pg_catalog`), no derivado del historial de migraciones.

Correrlo contra un Postgres limpio reconstruye el esquema `public` completo:
**58 tablas, 698 columnas, 364 constraints y 151 índices declarados** (PK, FK, UNIQUE y CHECK,
incluidas las constraints compuestas del modelo multiempresa).

Verificado contra el catálogo vivo el **7/8/2026**: **0 diferencias** en tablas, columnas, FKs,
CHECKs e índices, en las dos direcciones.

Contiene solo estructura: **no incluye datos**, ni funciones, ni triggers, ni los objetos de los
esquemas internos de Supabase (`auth`, `storage`). La única referencia externa es
`users.id -> auth.users(id)`, por lo que la base destino necesita tener ese esquema disponible si
se apunta a un proyecto Supabase real.

## Cómo reconstruir

1. Crear una base vacía.
2. Correr `schema.sql` contra ella (por ejemplo, desde el SQL Editor de Supabase o con
   cualquier cliente de Postgres apuntado a esa base).
3. **No** correr las migraciones encima. El schema ya las incluye a todas.
4. 🔴 Correr los **dos** scripts de triggers — sin ellos el esquema queda completo pero sin
   comportamiento. Producción tiene 50 triggers no internos y `schema.sql` trae 0:
   - `migracionAWS/backend/migrations/077_recrear_triggers_updated_at.sql` → los 41 de
     `updated_at` + la función `set_updated_at`.
   - `backend/migrations/094_recrear_triggers_empresa.sql` → los 9 `trg_emp_*` + la función
     `fn_misma_empresa`, que impiden el cruce de empresas por referencia.

## `migrations/` es historial, no bootstrap

`backend/migrations/` (001 → 094) documenta **cómo se llegó hasta acá**. No es un mecanismo
de bootstrap y correrlas en orden contra una base vacía no reconstruye producción de forma
confiable: hay dependencias de orden rotas, operaciones no idempotentes, y parte del modelo
multiempresa se aplicó a mano en producción (drift) y se versionó retroactivamente de forma
incompleta.

Las migraciones siguen siendo el lugar donde se versiona **cada cambio nuevo** al schema.
Lo que cambia es su rol en un rebuild: ahí no se usan.

Cuando se aplique una migración nueva a producción, `schema.sql` queda desactualizado —
hay que regenerarlo desde el catálogo de la base para que siga siendo fuente de verdad.

## `000_run_all.sql` está DEPRECADO

`backend/migrations/000_run_all.sql` era el consolidado viejo. Declaraba cubrir el orden
001 → 024, quedó ~65 migraciones desactualizado, y reintroduce triggers de auditoría que
fueron dropeados (la captura hoy es app-level).

Tiene un guard al principio (`RAISE EXCEPTION`) que **aborta la ejecución** antes de correr
cualquier sentencia. Se conserva únicamente como historial.

## Lo que este archivo NO cubre

El inventario de variables de entorno, los techos de la plataforma y el orden de deploy viven en
[`docs/DEPLOY.md`](../../docs/DEPLOY.md), que es el documento único para eso. Acá queda solo el
procedimiento de reconstrucción del schema.

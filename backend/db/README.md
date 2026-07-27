# Reconstrucción de la base — RRHH / HR Karstec

## `schema.sql` es la fuente de verdad

`backend/db/schema.sql` es el artefacto autoritativo de reconstrucción. Refleja el estado
real de la base de producción, leído directamente del catálogo de Postgres
(`information_schema` / `pg_catalog`), no derivado del historial de migraciones.

Correrlo contra un Postgres limpio reconstruye el esquema `public` completo:
**47 tablas, 310 constraints y 220 índices** (PK, FK, UNIQUE y CHECK, incluidas las
constraints compuestas del modelo multiempresa).

Contiene solo estructura: **no incluye datos**, ni los objetos de los esquemas internos de
Supabase (`auth`, `storage`). La única referencia externa es `users.id -> auth.users(id)`,
por lo que la base destino necesita tener ese esquema disponible si se apunta a un proyecto
Supabase real.

## Cómo reconstruir

1. Crear una base vacía.
2. Correr `schema.sql` contra ella (por ejemplo, desde el SQL Editor de Supabase o con
   cualquier cliente de Postgres apuntado a esa base).
3. **No** correr las migraciones encima. El schema ya las incluye a todas.

## `migrations/` es historial, no bootstrap

`backend/migrations/` (001 → 074) documenta **cómo se llegó hasta acá**. No es un mecanismo
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
001 → 024, quedó ~50 migraciones desactualizado, y reintroduce triggers de auditoría que
fueron dropeados (la captura hoy es app-level).

Tiene un guard al principio (`RAISE EXCEPTION`) que **aborta la ejecución** antes de correr
cualquier sentencia. Se conserva únicamente como historial.

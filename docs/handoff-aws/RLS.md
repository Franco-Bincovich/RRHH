# RLS — las 58 policies que NO se portan, y las 32 tablas que no tienen ninguna

> **Para el dev que monta la infraestructura en AWS.** Medido contra el catálogo vivo
> (`pg_policies`, `pg_class.relrowsecurity`, `pg_event_trigger`) el **26/8/2026**.
>
> 🔴 **La conclusión operativa, para que no haya que leer el resto si no hace falta: en RDS NO VA
> RLS, `backend/db/schema.sql` no lo trae, y por lo tanto el rebuild nace correcto. No hay nada
> que portar.** Lo que sigue existe porque *"no hay nada que portar"* es una afirmación que
> alguien va a querer verificar, y porque hoy nace correcto **por omisión y no por una línea que
> lo diga** — que es una diferencia que importa el día que alguien copie un objeto de más.

---

## 1 · Lo que hay hoy, en tres números

| | Cantidad |
|---|---|
| Tablas de `public` | **55** |
| Tablas con **RLS encendido** | **55 — todas** |
| Policies | **58** |
| Tablas **con** al menos una policy | **23** |
| 🔴 Tablas con **RLS encendido y CERO policies** | **32** |

🔴 **Ese último número es el que ningún documento del repo decía, y es el que cambia cómo se lee
todo lo demás.** `CLAUDE.md` describe el stack como *"Supabase (PostgreSQL + Auth + Storage), con
RLS"*, a secas. Leído sin este archivo, eso suena a que hay una capa de autorización en la base
que hay que reconstruir del otro lado. **No la hay.** Hay 23 tablas con policies escritas en
distintos momentos de la historia del proyecto, y 32 con RLS encendido que **no tienen ninguna
regla que las deje leer** — o sea que para cualquier rol que no sea `service_role` están en
**deny-all**.

---

## 2 · Por qué nada de esto se nota hoy

**Todo el backend pega contra Supabase con la `service_role`**, que **ignora RLS por definición
del producto** (`integrations/supabase_client.py` → `supabase_admin`). La `anon` key se usa
únicamente en dos lugares del flujo de auth (`services/auth_service.py:42` y `:97`, más
`usuario_service.py:80`), y ninguno de los tres lee tablas de negocio.

Consecuencia directa: **las 58 policies nunca se evalúan en el camino normal**, y las 32 tablas en
deny-all funcionan perfecto. No hay ningún síntoma. Es la razón por la que esto pudo quedar así
sin que nadie lo notara.

> ⚠️ **La contracara, que sí te toca:** como la `service_role` es lo único que hay, **es la llave
> del reino**. Cualquier proceso que la tenga lee y escribe todo. En AWS va en **SSM Parameter
> Store / Secrets Manager**, nunca en un `.env` en disco ni en una variable de build.

---

## 3 · Las 23 tablas con policies

| Tabla | Policies | Comandos |
|---|---|---|
| `users` | 6 | SELECT / INSERT / UPDATE / DELETE |
| `assessment_links` | 4 | ALL / SELECT / UPDATE |
| `assessment_resultados` | 4 | INSERT / SELECT / UPDATE |
| `empleados` | 3 | ALL / SELECT |
| `onboarding_instancias` | 3 | ALL / SELECT |
| `onboarding_progreso` | 3 | ALL / SELECT |
| `planes_carrera` | 3 | ALL / SELECT |
| `planes_carrera_hitos` | 3 | ALL / SELECT |
| `areas` · `assessment_campanas` · `auditoria` · `candidatos` · `costos_nomina` · `empresas` · `offboarding_activos` · `offboarding_instancias` · `onboarding_tareas` · `onboarding_templates` · `presupuesto_areas` · `reportes_generados` · `solicitudes_vacaciones` · `vacantes` | 2 c/u | ALL / SELECT (salvo `auditoria` y `reportes_generados`: INSERT / SELECT) |
| `usuario_integraciones` | 1 | ALL |

### 🔴 Por qué NINGUNA se puede portar tal cual

Se apoyan en dos cosas que **no existen en RDS**:

1. **`auth.uid()`** — la identidad del request la pone Supabase Auth a partir del JWT. En RDS no
   hay schema `auth` ni esa función.
2. **`public.get_current_user_rol()`**, que es el helper del que cuelgan casi todas:

```sql
CREATE OR REPLACE FUNCTION public.get_current_user_rol()
 RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO 'public'
AS $function$ SELECT rol FROM public.users WHERE id = auth.uid() $function$
```

Es `SECURITY DEFINER` **a propósito** (sin eso, consultar `users` desde una policy de `users`
crea una dependencia circular que rompe el login — está anotado en `CLAUDE.md` § Convenciones).
Del otro lado habría que alimentar la identidad por `SET LOCAL` en cada conexión del pool, que es
una capa nueva entera. **Reconstruir esto era exactamente lo que la decisión de producto evitó.**

---

## 4 · Las 32 tablas con RLS y CERO policies

```
adjuntos · capacitaciones · cesiones · clientes · empleado_capacitacion
empleado_superior_pendiente · evaluacion_equivalencias · evaluacion_evaluados
evaluacion_lotes · evaluacion_resultados · eventos_agenda · horas_proyecto
intentos_identificacion · inventario_asignaciones · inventario_items · mail_enviado
oauth_states · objetivo_responsables · objetivos · parametros_empresa
parametros_screening · perfiles_puesto · periodos_cerrados · plantillas_mail
proyecto_asignaciones · proyectos · recategorizaciones · reglas_vacaciones_escala
sesiones_horas · solicitudes_ausencia · tipos_ausencia · vacaciones_pendientes
```

**No es que se olvidaron de escribirles policies: es que nunca hizo falta.** Son las tablas de los
módulos construidos después de que la seguridad app-level ya fuera la decisión. Ninguna se toca
con otra cosa que la `service_role`.

🔑 **Y no llegaron ahí a mano** — ver la sección que sigue.

---

## 5 · 🔴 El event trigger `ensure_rls` — lo más importante de este documento

En el proyecto hay un **event trigger a nivel base de datos** que enciende RLS **solo**, en toda
tabla nueva de `public`:

```sql
-- event trigger: ensure_rls  →  función: public.rls_auto_enable()
CREATE OR REPLACE FUNCTION public.rls_auto_enable()
 RETURNS event_trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'pg_catalog'
AS $function$
DECLARE cmd record;
BEGIN
  FOR cmd IN SELECT * FROM pg_event_trigger_ddl_commands()
             WHERE command_tag IN ('CREATE TABLE','CREATE TABLE AS','SELECT INTO')
               AND object_type IN ('table','partitioned table')
  LOOP
     IF cmd.schema_name IN ('public') THEN
       EXECUTE format('alter table if exists %s enable row level security', cmd.object_identity);
       ...
```

**Eso explica el 55 de 55**, y explica las 32 sin policies: cada tabla creada desde que el trigger
existe nació con RLS encendido **sin que ninguna migración lo pidiera**. Ninguna de las 121
migraciones de `backend/migrations/` tiene un `ENABLE ROW LEVEL SECURITY` para esas tablas — el
estado no sale del historial versionado, sale de este trigger.

### Las dos formas de equivocarse con él, y son opuestas

| Si… | Pasa esto |
|---|---|
| **NO lo replicás** (lo correcto) | Las tablas nuevas en RDS nacen **sin** RLS. Es el comportamiento que se quiere, y es lo que `schema.sql` produce solo |
| **Lo replicás sin querer** — copiando funciones "porque estaban en el catálogo de origen" | 🔴 **Cada tabla que crees de ahí en adelante nace con RLS encendido y sin una sola policy, o sea en deny-all.** Y como la app entra con un rol superusuario del pool, **no vas a notarlo hasta que algo entre con otro rol** — un job de reporting, una réplica de lectura, una herramienta de BI |

🔑 **Es un objeto que no aparece en `pg_dump` de tablas ni en `schema.sql`, así que sólo lo ves si
listás `pg_event_trigger` a propósito.** Por eso está escrito acá.

---

## 6 · Qué trae y qué no trae `schema.sql`

`backend/db/schema.sql` es el artefacto de reconstrucción y **fue verificado objeto por objeto
contra el catálogo vivo el 26/8/2026** (tablas, columnas, tipos, defaults, CHECKs, índices y FKs
coinciden; las únicas dos divergencias son las de `users.id`, deliberadas). Lo que **no** trae:

| No trae | Consecuencia en RDS | ¿Hay que reponerlo? |
|---|---|---|
| `ENABLE ROW LEVEL SECURITY` | Las 55 tablas nacen **sin** RLS | 🟢 **No.** Es el resultado buscado |
| Las 58 policies | No existen | 🟢 **No.** Ver §3: no se pueden portar y no protegen nada hoy |
| `get_current_user_rol()` | No existe | 🟢 **No.** Sólo la usan las policies |
| `rls_auto_enable()` + `ensure_rls` | No existen | 🟢 **No — y es importante que siga siendo así.** Ver §5 |
| `set_updated_at()` + sus **38** triggers | `updated_at` congelado en el valor del INSERT | 🔴 **SÍ.** `migracionAWS/backend/migrations/077_recrear_triggers_updated_at.sql` |
| `fn_misma_empresa()` + sus **8** triggers `trg_emp_*` | Desaparece la única defensa a nivel base contra el cruce de empresas por referencia | 🔴 **SÍ, y leer antes `HANDOFF.md` §5.4**: uno de los 8 contradice una decisión de producto. Artefacto: `backend/db/funciones_y_triggers.sql` |

> 🔴 **La asimetría es toda la gracia de esta tabla: de las cinco cosas que `schema.sql` no trae,
> tres NO se reponen a propósito y dos SÍ.** Un rebuild que copie "todas las funciones del
> origen" reintroduce las tres primeras; uno que no copie ninguna pierde las dos últimas en
> silencio. Por eso los artefactos de triggers son archivos separados y explícitos, y los de RLS
> no existen.

---

## 7 · Qué reemplaza a RLS, y dónde mirarlo

**La decisión, tomada y cerrada: la autorización vive en el service layer.** Dos ejes que se
componen por **intersección**:

| Eje | Qué decide | Dónde vive |
|---|---|---|
| **Permisos por rol** | Qué puede hacer cada rol en cada sección | `utils/permisos.py` + `utils/_secciones.py`. **229 gates `Depends(require_permission(...))` en 74 routers** |
| **Barrera de empresa** | Sobre qué fila puede operar | En el **WHERE de la query**, en `repositories/`. Ver `HANDOFF.md` §2.2 |
| **Ownership** (`mandos_medios`) | Dentro de mi empresa, a qué empleados llego | `services/ownership.py`, y **sólo** en VACACIONES y AUSENCIAS |

🔴 **Lo que eso significa para el porteo, dicho de la forma más concreta posible:** como no hay
RLS abajo que respalde nada, **si al mover un repo a asyncpg se te cae un `.eq("empresa_id", ...)`
no falla nada — devuelve datos de otra empresa, con 200.** Un filtro que desaparece no da error,
da resultados de más. Los barridos nº 38 (`test_routers_escritura_request.py`) y nº 11
(`test_acceso_a_datos.py`) son la red que queda.

---

## 8 · Cómo verificar todo esto vos mismo

```sql
-- 55 de 55 con RLS encendido
SELECT count(*) FILTER (WHERE relrowsecurity) AS con_rls, count(*) AS total
  FROM pg_class WHERE relnamespace = 'public'::regnamespace AND relkind = 'r';

-- 58 policies en 23 tablas
SELECT count(*) AS policies, count(DISTINCT tablename) AS tablas
  FROM pg_policies WHERE schemaname = 'public';

-- las 32 con RLS y ninguna policy
SELECT c.relname FROM pg_class c
 WHERE c.relnamespace = 'public'::regnamespace AND c.relkind = 'r' AND c.relrowsecurity
   AND NOT EXISTS (SELECT 1 FROM pg_policies p
                    WHERE p.schemaname = 'public' AND p.tablename = c.relname)
 ORDER BY 1;

-- 🔴 el event trigger que hay que NO replicar
SELECT evtname, p.proname FROM pg_event_trigger e JOIN pg_proc p ON p.oid = e.evtfoid;
```

---

*HR Karstec · `docs/handoff-aws/` · escrito el 26/8/2026, medido contra el catálogo vivo.*

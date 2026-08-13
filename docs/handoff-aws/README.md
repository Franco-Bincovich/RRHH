# handoff-aws

> Carpeta única de la migración a AWS. Todo lo que el dev de infra necesita, y todo lo que él
> nos dejó, vive acá.

---

## Por qué existe esta carpeta

La migración a AWS la hace **otro dev**, en paralelo a nuestro trabajo de features. Sin un lugar
único, el material se dispersa: parte en `migracionAWS/`, parte en la bitácora, parte en un mail.
Cuando llega el cutover, nadie sabe qué versión es la buena.

**Regla:** si un documento es *para él* o *de él*, va acá. Si es de cómo trabajamos nosotros, va
en `docs/`.

---

## Qué hay adentro

### De él para nosotros — referencia, no instrucciones

| Archivo | Qué es | Cuándo leerlo |
|---|---|---|
| `COMPARATIVA_VERCEL_SUPABASE_VS_AWS.md` | Análisis de 3 migraciones, 50+ errores, 5 patrones recurrentes | Antes de tocar auth, serialización o queries |
| `PATRONES_CODIGO_AWS.md` | Código de referencia: asyncpg, serializers, JWT, bcrypt, Terraform | Solo si hay que extender o debuggear esas capas |
| `README-DEV.md` | El índice original de los dos anteriores | Ya está resumido acá |

**Cómo se usan estos tres:**

- Son **contexto de decisiones ya tomadas**, no una lista de tareas.
- **El código existente del proyecto manda.** Si el proyecto ya tiene su versión de algo
  (`postgres_client`, `serializers`, `auth_service`), no se reemplaza para parecerse a estos
  patrones.
- **Nada de refactor preventivo.** Si el código funciona y no lo estamos tocando, se deja.
- El checklist de 50 items **no se ejecuta**: es referencia pasiva.

### De nosotros para él — se completa al cierre

| Archivo | Qué va | Cuándo |
|---|---|---|
| `HANDOFF.md` | El documento principal: rutas públicas, techos medidos, decisiones que condicionan el cutover | Fase 3 (J4) |
| `BARRIDO-PATRONES.md` | El resultado de los 4 greps de control, con lo que se arregló y lo que se declara | Fase 3 (3.5) |
| [`STORAGE.md`](STORAGE.md) | ✅ **Escrito (12/8).** Los 3 buckets, qué guarda cada uno, y **qué archivo toca y cuáles NO** el día del cutover | Fase 0 (0.7) |
| [`ACCESO-A-DATOS.md`](ACCESO-A-DATOS.md) | ✅ **Escrito (12/8).** Dónde vive el acceso a datos: 328 de 386 llamadas en `repositories/`, las 58 restantes con archivo:línea, y **los 2 catálogos de tabla dinámica que un porteo por búsqueda y reemplazo NO ve** | Fase 0 (0.9) |
| `RLS.md` | Las 58 policies que **no** se portan, y por qué | Fase 3 (J4) |

### Artefactos de reconstrucción

✅ **Los cuatro existen desde el 12/8/2026.** No viven acá —viven donde el sistema los usa— pero
se listan para que él sepa dónde buscar:

| Archivo | Dónde | Qué es |
|---|---|---|
| `schema.sql` | `backend/db/` | **Fuente de verdad.** Tablas, columnas, constraints, índices y defaults. **Cero funciones y cero triggers** |
| `funciones_y_triggers.sql` | `backend/db/` | `fn_misma_empresa()` + los **8** triggers de cruce de empresa. Leído del catálogo vivo |
| `077_recrear_triggers_updated_at.sql` | `migracionAWS/backend/migrations/` | Los **35** triggers de `updated_at` + `set_updated_at()` |
| `seed.sql` | `backend/db/` | Catálogos base sin los cuales el sistema arranca roto |
| `.env.example` | `backend/` | Verificado contra `settings.py` (Fase 3, J2) |

### El orden de reconstrucción, sobre una base recién creada

```bash
psql -v ON_ERROR_STOP=1 -f backend/db/schema.sql
psql -v ON_ERROR_STOP=1 -f backend/db/funciones_y_triggers.sql
psql -v ON_ERROR_STOP=1 -f migracionAWS/backend/migrations/077_recrear_triggers_updated_at.sql
psql -v ON_ERROR_STOP=1 -f backend/db/seed.sql
```

**Los cuatro tienen que dar exit 0.** `ON_ERROR_STOP=1` no es opcional: sin él, `psql` sigue de
largo tras un error y termina con exit 0 igual, así que un replay a medias se lee como exitoso.

> 🟢 **Los cuatro pasos se corrieron de verdad el 13/8/2026, contra un PostgreSQL 16 que no es
> Supabase — la primera vez que este replay se ejecuta fuera de la plataforma.** Los cuatro
> dieron **exit 0** y no apareció ningún bloqueante. Estado final: **55 tablas · 46 triggers no
> internos · 140 FKs · 246 índices.** El detalle está en `docs/DIAGNOSTICO-ESCALA.md` §1.
>
> ⚠️ **Prueba sintaxis y orden, NO compatibilidad con la versión destino:** la base era 16.13 y
> producción es 17.6.

### 🔴 Las migraciones 113, 114 y 115 NO se corren en un rebuild

**`db/schema.sql` ya las incluye.** El archivo va por delante de producción desde el 13/8/2026
(lo dice su propio encabezado), así que quien reconstruya desde él **ya tiene** las 3 tablas
nuevas, las 7 columnas y los índices de las tres migraciones.

Correrlas igual no rompe nada —las tres son idempotentes, verificado— pero **listarlas como paso
del rebuild hace que alguien busque un paso que no falta.** Son parte del historial: se corren
UNA vez contra la base de producción que ya existe, no contra una base recién creada.

Dicho al revés, que es como se usa: **si arrancás de `schema.sql`, el orden de reconstrucción son
los cuatro pasos de arriba y nada más.**

**El orden importa, y no es alfabético:**
1. `schema.sql` crea las tablas. Todo lo demás las necesita.
2. y 3. Los triggers van **antes** del seed: si van después, las filas del seed entran sin pasar
   por las validaciones, que es justo lo que no se quiere ejercitar mal el primer día.
4. `seed.sql` va último, y es el único que escribe filas.

Verificación al terminar — tiene que dar `46`, `8` y `5 / 1 / 3`:

```sql
SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
  JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname='public' AND NOT t.tgisinternal;                        -- 46 (38 + 8)
SELECT count(*) FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid
 WHERE p.proname='fn_misma_empresa' AND NOT t.tgisinternal;              -- 8
SELECT (SELECT count(*) FROM tipos_ausencia           WHERE empresa_id IS NULL),
       (SELECT count(*) FROM parametros_empresa       WHERE empresa_id IS NULL),
       (SELECT count(*) FROM reglas_vacaciones_escala WHERE empresa_id IS NULL);  -- 5 / 1 / 3
```

### 🔴 `backend/migrations/` NO se usa para reconstruir

Son **historial**: documentan cómo se llegó hasta acá. Tienen dependencias de orden rotas,
operaciones no idempotentes, y parte del modelo multiempresa se aplicó a mano en producción y se
versionó retroactivamente de forma incompleta.

**El ejemplo concreto, por si la regla suena a precaución genérica:**
`migrations/094_recrear_triggers_empresa.sql` recrea estos mismos triggers, y **abortaría el
replay**. Declara **9**: el noveno es `trg_emp_sucesion` sobre `sucesion_posiciones`, una de las
once tablas que dropeó la migración 112. Y no falla por el trigger —`DROP TRIGGER IF EXISTS` falla
igual cuando la que no existe es la **tabla**—. Por eso el paso 2 usa `db/funciones_y_triggers.sql`,
que se leyó del catálogo vivo y declara los 8 que existen de verdad. La 094 queda como historia.

### Una diferencia deliberada entre `schema.sql` y producción

`schema.sql` **no trae** la FK `users.id → auth.users(id) ON DELETE CASCADE`, y le pone a `users.id`
un `DEFAULT gen_random_uuid()`. Era el único bloqueante del replay: en RDS no existe el schema
`auth`. **En producción la FK sigue existiendo y se queda ahí** — `schema.sql` describe la base
destino, no la que hoy sirve tráfico.

Hoy el id lo genera **Supabase Auth** y la app lo pasa explícito en el INSERT
(`services/_usuario_alta.py`), así que el DEFAULT no cambia nada del comportamiento actual: solo
habilita el INSERT sin `id`, que es lo que hace falta del otro lado. **Lo que sí hay que reponer en
la app del destino** es el `ON DELETE CASCADE` que borraba el perfil al borrar la identidad: el alta
tiene un rollback (`_rollback_auth`) que hoy se apoya en él.

---

## Los 4 greps de control

Salen de los patrones recurrentes documentados. Se corren antes de cada entrega y el resultado
queda escrito en `BARRIDO-PATRONES.md`.

```bash
grep -rn "uuid.*==" backend/                      # comparaciones UUID contra string
grep -rn "supabase_admin.auth" backend/           # SDK de auth remanente
grep -rn "model_dump()" backend/ | grep -v mode=  # escrituras sin serializar
grep -rn ": str" backend/schemas/ | grep _id      # IDs mal tipados
```

Que el dev los encuentre en septiembre cuesta horas de debugging. Que se los entreguemos
listados cuesta una sesión.

---

## Lo que ya sabemos que le espera

| Tema | Estado | Nota |
|---|---|---|
| FK a `auth.users` en `schema.sql` | ✅ **sacada (12/8)** | Era el único bloqueante del replay. `users.id` quedó con `DEFAULT gen_random_uuid()` |
| Migración **109** | ✅ **corrida (12/8)** | `clientes` quedó sin `empresa_id`. Producción y `schema.sql` coinciden: **no hay migraciones pendientes** |
| `trg_emp_empleados` vigila `manager_id` | 🟠 **conflicto sin resolver** | Exige que el superior sea de la misma empresa, pero la decisión de producto (2/8) permite superior cruzado. Hoy no explota: hay 0 casos. Ver `db/funciones_y_triggers.sql` |
| 5 IDs tipados `str` en vez de `UUID` | 🔴 se arreglan en Fase 0 | Patrón #1 de la lista |
| 3 buckets de Storage hardcodeados | ✅ **centralizados (12/8)** | Eran **7** services, no 6. Todo pasa por `backend/integrations/storage.py`; un barrido estructural lo mantiene así. Ver [`STORAGE.md`](STORAGE.md) |
| 58 policies RLS | ⬜ no se portan | La app entra como `service_role`: hoy no protegen nada |
| Rate limit con `memory://` | 🟠 necesita Redis | El contador es por proceso |
| Jobs en background | 🟠 no funcionan en Vercel | Resuelto por ECS |
| Encoding de `requirements.txt` en Windows | ✅ arreglado | El `⚠️` rompía `pip install` con locale cp1252 |

---

## Coordinación

**Lo que hay que confirmarle antes del 20 de agosto:**
- Qué versión de PostgreSQL va a tener RDS (asumimos 17, igual que producción)
- Cuándo hace el cutover de Storage a S3 — de eso depende si D2 (rutas de archivos de
  evaluaciones) entra o no
- Si necesita algo más de nosotros que no esté en esta carpeta

**La fecha:** el 6 de septiembre recibe el repo completo y estable. Tiene catorce días de
colchón hasta la entrega del 20.

---

*HR Karstec · Carpeta de handoff · 12/8/2026*

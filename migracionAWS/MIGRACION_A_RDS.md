# Migración de RRHH a RDS + asyncpg + S3 + ECS

Mapa para completar la migración. Mismo patrón que Agent Admin: salir de Supabase
(PostgREST + gotrue + Storage, todo sobre Vercel serverless) a Postgres directo por
asyncpg sobre RDS, auth propio, S3 y ECS. Asumo que ya migraste Agent Admin — no explico
asyncpg ni boto3 desde cero, marco lo que es específico de RRHH y las minas que ya pisé.

---

## 1. Qué es esto y estado

Todo lo hecho vive en `migracionAWS/`, **aislado**: no lo importa nada de `backend/`, no
tocó producción. RRHH sigue **100% en Supabase + Vercel** hasta que se ejecute la migración.

```
migracionAWS/
├── README.md
├── MIGRACION_A_RDS.md                         ← este documento
└── backend/
    ├── config/settings_ADD.md                 ← delta de config (agregar database_url, deprecar supabase_*)
    ├── integrations/postgres_client.py        ← cliente asyncpg (pool + helpers)
    ├── middleware/auth_NEW.py                  ← middleware JWT propio (reemplaza JWKS de Supabase)
    ├── migrations/075_add_password_hash.sql    ← password_hash en users (+ FK/DEFAULT comentados)
    ├── migrations/076_create_refresh_tokens.sql
    ├── migrations/077_recrear_triggers_updated_at.sql ← función set_updated_at() + 36 triggers (DDL listo)
    ├── README_AUTH.md                          ← orden de activación del auth propio
    ├── repositories/empleado_repo_NEW.py       ← REPO-MOLDE (copiar para los 43 restantes)
    ├── repositories/empleado_lookup_repo_NEW.py ← satélite del molde (lookups + bajas)
    ├── repositories/token_repo_NEW.py
    └── services/
        ├── auth_service_NEW.py                 ← login + JWT propio (bcrypt local)
        └── token_service_NEW.py               ← refresh con rotación one-time-use
```

Los `_NEW` se renombran al mover a `backend/`. Nada de esto está cableado todavía.

---

## 2. Lo que ya está resuelto

**Higiene de arranque (ya commiteado en el repo real, no en `migracionAWS/`):**
- `.venv` de macOS sacado del tracking (`git rm -r --cached`, 3822 archivos; seguía en disco).
- `EmailStr` → validador manual con regex en `backend/schemas/usuario.py`. `EmailStr` exige
  `email_validator`, que **no está** en `requirements.txt` → sin él el backend **no arranca**
  (falla en import). Igual que en Agent Admin. No re-agregar el paquete.

**Cliente de datos — `backend/integrations/postgres_client.py`:**
- Pool asyncpg global (`init_pool`/`close_pool`/`get_pool`) + helpers `fetch` (list[dict]),
  `fetchone` (dict|None), `fetchval` (escalar), `execute`.
- **Asume proceso persistente (ECS/EC2), NO serverless.** Un pool no sobrevive a lambdas warm
  de Vercel — por eso el backend deja Vercel. No importar mientras siga en Vercel.
- Config: `ssl="require"` (RDS lo exige), `min_size=2/max_size=10/command_timeout=30`. El
  delta de `settings.py` (agregar `database_url`, deprecar `supabase_*`) está en
  `config/settings_ADD.md`. Reemplaza entero a `integrations/supabase_client.py` (195 líneas
  de proxy + monkeypatch HTTP/1.1 que desaparecen).

**Auth propio** (backend `_NEW` + migraciones 075/076): `auth_service_NEW` (login + JWT HS256
propio, bcrypt local), `token_service_NEW` (refresh con rotación one-time-use), `token_repo_NEW`,
`middleware/auth_NEW` (verifica firma propia, no el JWKS de Supabase). **Orden de activación en
`README_AUTH.md`** — respetarlo, hay dependencias (ver hallazgos §3).

**Repo-molde** — `repositories/empleado_repo_NEW.py` (99 líneas) + `empleado_lookup_repo_NEW.py`
(56). **Es EL patrón para los 43 repos restantes.** Convenciones que fija:

| Convención | Regla |
|---|---|
| Parametrización | 100% `$n`. La ESTRUCTURA (columnas/JOINs) se concatena de constantes; los VALORES siempre `$n`. Cero f-strings/`.format` con datos. |
| Embeds → JOIN | LEFT JOIN explícito, **nunca INNER** (preserva filas sin área/empresa/manager). Un `_SELECT` constante por repo. |
| Filtro empresa | `($n::uuid IS NULL OR e.empresa_id = $n)` — un solo SQL, `None` = consolidado. Reemplaza el `_with_empresa` manual. |
| Paginación | `COUNT(*) OVER() AS total_count` (una query; el window corre antes del LIMIT). Devuelve `Tuple[List, int]`. |
| ORDER BY | Columnas de negocio + **una columna ÚNICA al final** (`e.id`). Sin esto, `LIMIT/OFFSET` es no-determinista. |
| Mapper | Recibe el dict ya PLANO por el JOIN, **castea UUID→str** (ver §3), compone campos derivados, cierra con `model_validate`. |
| Nulos | `find_*` → `fetchone` → `None`. El repo **nunca** levanta `AppError` por "no encontrado"; eso es del service. |
| Fechas/UUID | Sin `str(fecha)`: asyncpg bindea `date`/`datetime`/`UUID` nativo. |
| RETURNING | `save`/`update` usan `RETURNING *` **sin** JOIN → `area_nombre=None` post-op, **paridad exacta con hoy** (no "arreglar"). |

---

## 3. Hallazgos de fábrica (minas ya desactivadas)

Ordenados por impacto. Esto te ahorra días.

**1. UUID → str en el mapper.** El SDK devolvía JSON (todo string); asyncpg devuelve `uuid.UUID`
nativo. Los `Response` de RRHH tipan los id como `str` (verificado en `EmpleadoResponse`:
`id`/`empresa_id`/`area_id`/`manager_id` son `str`). **Pydantic v2 no coacciona `UUID→str`** →
revienta en `model_validate`. **Cada repo lo pega.** El molde lo resuelve en el mapper:
```python
data = {k: (str(v) if isinstance(v, UUID) else v) for k, v in r.items() if k not in (...)}
```
Lo mismo aplica a cualquier campo que el `Response` tipe `str` pero la columna sea `uuid`.
Las `date`/`datetime` sí las acepta Pydantic nativas — esas no se tocan.

**2. FK `users.id → auth.users(id)` bloquea el alta sin Supabase.** Todo INSERT en `public.users`
exige hoy una fila previa en `auth.users` (la crea gotrue). Con auth propio hay que:
`ALTER TABLE users DROP CONSTRAINT users_id_fkey;` + `ALTER COLUMN id SET DEFAULT gen_random_uuid();`
(el id lo proveía gotrue, la columna no tiene default). **Bloques SQL comentados en la migración
075** — separados del `ADD COLUMN` a propósito, para que se decidan y no se corran a ciegas.

**3. El `ON DELETE CASCADE` contra `auth.users` es lógica de negocio VIVA.** Hoy
`usuario_service.eliminar_usuario` borra `auth.users` y **confía en el cascade** para limpiar
`public.users`. Al dropear la FK, ese borrado **deja de borrar y NO falla**: el usuario "eliminado"
sigue logueando. Por eso **auth propio + reescritura de `usuario_service` van JUNTOS**, no en pasos
separados. Es el punto más delicado de toda la migración.

**4. `passlib` está roto contra el bcrypt instalado.** `requirements.txt` trae
`passlib[bcrypt]==1.7.4`, pero passlib lee `bcrypt.__about__`, atributo eliminado en bcrypt 4.1+
(instalado: 5.0.0) → `AttributeError`. Reproducido en este repo. Usar `import bcrypt` directo
(así lo hace `auth_service_NEW`). Otra dependencia declarada que no arranca en limpio.

**5. Triggers `updated_at` — `schema.sql` NO los trae.** El snapshot se generó del catálogo y
capturó tablas/columnas/constraints/índices/defaults, pero **0 funciones y 0 triggers**. En prod
siguen vivos `set_updated_at()` + **36 triggers `trg_*_updated_at`** (la migración 058 dropeó solo
los de auditoría, no estos). Sin ellos: `updated_at` se puebla en el alta (por el `DEFAULT now()`)
pero **no se actualiza en UPDATE** — corrupción silenciosa.

**DECISIÓN (cerrada): se RECREAN los 36 triggers en RDS. NO se mueve `updated_at` a la capa de
aplicación.** Es un solo script SQL y es **a prueba de olvidos**: dejarlo en la app dependería de
que nadie se olvide en **ninguna** de las ~332 queries que se reescriben, y un solo olvido = dato
congelado en silencio (el mismo modo de falla que se quiere evitar). El DDL ya está listo en
**`migracionAWS/backend/migrations/077_recrear_triggers_updated_at.sql`** — recrea la función
`set_updated_at()` (definición 1:1 de 001) + los 36 triggers `trg_*_updated_at`, con nombres
extraídos de las migraciones 001–066. Correrlo en el rebuild, **después** de `db/schema.sql`.

---

## 4. Lo que falta (necesita RDS/AWS delante — no era del alcance de hoy)

**Migrar los 43 repos restantes** copiando el molde. Del diagnóstico: **~332 queries** del SDK
(`.table(`≈`.execute()`). Dos familias que colapsan al mismo JOIN:
- **embed PostgREST** (`select("*, areas!..(nombre)")`) — empleado, vacaciones.
- **mapa manual en Python** (trae la tabla aparte y arma un dict) — ausencias (`_q`), inventario.

Casos pesados: los **5 embeds anidados de 2 niveles** son JOIN de 3 tablas —
`costo_repo:17`, `nomina_repo:17`, `onboarding_repo:15`, `assessment_repo:16`,
`assessment_resultados_repo:17`. El **único self-join real** (`manager:manager_id`) ya está
resuelto en el molde.
> ⚠️ **`costo_repo.py` y `assessment_repo.py` se borraron el 2/8/2026** — eran legacy con cero
> callers (`costo_service` usa `nomina_repo`/`periodo_repo`/`presupuesto_repo`). **No hay que
> portarlos:** son 2 de los 5 "casos pesados" de esta lista y desaparecieron sin reemplazo. `0` RPC en todo el código: no hay lógica escondida en funciones de PG.

**~60 queries sueltas en services** (violan la arquitectura router→service→repo; no están en
repos, así que un plan que cuente solo los 44 archivos de `repositories/` subestima ~18%):
`reporte_generators.py` (11), `reporte_anual.py` (9), `dashboard_service.py` (8),
`organigrama_proyectos_service.py` (6), y **`middleware/auth.py:127`** — un `.table("users")`
en el camino caliente de cada request (con el auth nuevo, el rol viaja en el token y ese query
desaparece).

**Reescribir `usuario_service`** — las llamadas a Supabase Auth. Mapeo en `README_AUTH.md`:
`auth_service.py:49/90/112` (sign_in / refresh / sign_out) y `usuario_service.py:36/70/122/126/145`
(delete×2 / create / reauth / update). Ver §3 hallazgo 3: va junto con el drop de la FK.

**Storage → S3.** 3 buckets, 10 llamadas, casi 1:1 con boto3:
- `documentos` y `cvs` — privados, se sirven con signed URL (3600s) → `generate_presigned_url`.
- `avatars` — público (`get_public_url`, logos de empresa) → objeto público / URL directa.
Archivos: `adjunto_service`, `asignacion_service`, `candidato_service`, `cv_service`, `empresa_service`.

**Migración de datos.** El usuario de test **se elimina y se recrea** (no se migran hashes: los
bcrypt de Supabase no se leen por el SDK). Molde: el script v2 de Agent Admin, **PERO**:
- credenciales **por entorno** (Secrets Manager / SSM), **NUNCA hardcodeadas** en el script.
- **sin `ON CONFLICT DO NOTHING` silencioso** — verificar conteos fila por fila. El v1 de Agent
  Admin perdió **139 de 239 filas** sin avisar porque los conflictos se tragaban en silencio.

**Infra.** Terraform/ECS/ALB/Route53/CloudWatch (reusar plantilla de Agent Admin). CORS con las
URLs reales. Cookies `Secure`/`SameSite` por entorno (ver también §6: el fallback a cookie del
middleware nuevo está apagado de facto y abre CSRF si se enciende sin protección). `NEXT_PUBLIC_*`
con rutas relativas.

---

## 5. Base de datos (rebuild)

- **Reconstruir desde `backend/db/schema.sql`.** Es el snapshot autoritativo del catálogo de prod
  (47 tablas, 310 constraints, 220 índices). Correrlo contra una base limpia; **NO** correr las
  74 migraciones encima (son historial — auditadas: sin migraciones vacías, sin números repetidos
  ni huecos 001–074, sin tablas auto-anuladas, sin credenciales).
- **Tres decisiones al reconstruir (cerradas, ver abajo):**
  1. **Recrear los triggers `updated_at` — DECIDIDO** (§3 hallazgo 5). `schema.sql` no los trae;
     se recrean en RDS (NO se mueve `updated_at` a la app). DDL listo en
     `migracionAWS/backend/migrations/077_recrear_triggers_updated_at.sql` (función + 36 triggers).
     Correrlo **después** de `db/schema.sql`.
  2. **NO se implementa RLS en RDS — DECISIÓN EXPLÍCITA (no omisión).** `schema.sql` no trae RLS
     (38 tablas con RLS + ~205 policies en prod, omitidas) y **así queda**: en RDS la seguridad es
     **100% app-level** — ownership (`services/ownership.py`) + permisos por rol (`utils/permisos.py`),
     que RRHH **ya tiene** y son la capa que gobierna. RLS en Supabase era **segunda línea** (el
     backend siempre usó service_key, que la bypassa), no la que decide. Además las policies dependen
     de `auth.uid()` de Supabase, que en RDS no existe. **No "restaurarla" pensando que falta.**
  3. **NO cargar `035_demo_data.sql` — DECIDIDO: se excluye del bootstrap.** Son datos de demo
     (591 líneas, 21 emails sintéticos), no estructura, y no van a producción.
- Los triggers de auditoría **no** se recrean: fueron dropeados a propósito en 058 (la captura de
  auditoría hoy es app-level, vía `AuditService`).

---

## 6. Checklist de los ~40 problemas de Agent Admin

Qué ya viene resuelto de fábrica en RRHH vs. qué te queda a vos:

| Problema (Agent Admin) | Estado en RRHH |
|---|---|
| Placeholders `$n` (SQLi) | ✅ molde |
| Serialización UUID → str en respuestas | ✅ molde (mapper) |
| Serialización `date`/`datetime` | ✅ nativo asyncpg (Pydantic las acepta) |
| Pool asyncpg + lifespan | ✅ `postgres_client.py` (falta cablear el lifespan en `main.py` — hoy no existe) |
| `.venv` en el tracking | ✅ removido |
| `EmailStr` sin `email_validator` (no arranca) | ✅ validador manual |
| `passlib`/bcrypt roto | ✅ `import bcrypt` directo en `auth_service_NEW` |
| Auth propio (JWT + refresh + hash) | ✅ módulo `_NEW` (falta activarlo y reescribir `usuario_service`) |
| FK a `auth.users` bloquea alta | ⚠️ SQL comentado en 075 — decidir y correr |
| Triggers `updated_at` ausentes del schema | ✅ decidido: recrear en RDS — DDL listo en migración 077 (correr tras `schema.sql`) |
| RLS ausente del schema | ✅ decisión explícita: NO se implementa en RDS — seguridad 100% app-level (ownership + permisos por rol) |
| `035_demo_data.sql` (datos de demo) | ✅ decidido: excluir del bootstrap |
| Storage → S3 (3 buckets) | ⬜ pendiente (casi 1:1 boto3) |
| Migración de datos con verificación de conteos | ⬜ pendiente (script v2, sin `ON CONFLICT` silencioso) |
| Cookies `Secure`/`SameSite` por entorno | ⬜ pendiente-infra (+ ojo CSRF del fallback a cookie) |
| `NEXT_PUBLIC_*` rutas relativas | ⬜ pendiente-infra |
| CORS con URLs reales | ⬜ pendiente-infra |
| Terraform/ECS/ALB/Route53/CloudWatch | ⬜ pendiente-infra (plantilla Agent Admin) |
| `asyncio.to_thread(...)` sobre SDK sync → `await` directo | 🔸 nota: los repos nuevos son async; los callers (services) pasan a `await`, y `routers/auth.py` que hoy llama sin await necesita `await` |

Leyenda: ✅ resuelto de fábrica · ⚠️ decisión/acción puntual pendiente · ⬜ pendiente (RDS/AWS delante) · 🔸 nota de patrón.

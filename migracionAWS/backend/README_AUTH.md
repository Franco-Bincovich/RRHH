# Módulo de auth propio — referencia de migración

Reemplaza Supabase Auth (gotrue) por emisión y validación propia de JWT. Todo lo de acá
está **aislado**: no lo importa nadie, `backend/` sigue intacto. Los `_NEW` son para poder
leer viejo y nuevo lado a lado; al migrar se renombran.

## Mapeo

| Archivo del staging | Destino en `backend/` | Estado hoy |
|---|---|---|
| `migrations/075_add_password_hash.sql` | `migrations/075_...` | nueva (074 es la más alta) |
| `migrations/076_create_refresh_tokens.sql` | `migrations/076_...` | nueva |
| `repositories/token_repo_NEW.py` | `repositories/token_repo.py` | **no existe** — gotrue lo hacía |
| `services/token_service_NEW.py` | `services/token_service.py` | **no existe** — gotrue lo hacía |
| `services/auth_service_NEW.py` | `services/auth_service.py` | reemplaza (118 líneas) |
| `middleware/auth_NEW.py` | `middleware/auth.py` | reemplaza (143 líneas) |
| `integrations/postgres_client.py` | `integrations/postgres_client.py` | ya en el staging |

## Orden de activación

1. **Migraciones 075 + 076.** Ojo: 075 tiene dos bloques comentados que NO son opcionales
   (la FK a `auth.users` y el DEFAULT del id). Leer la sección "el punto más delicado".
2. **`token_repo`** — hoja, no depende de nada nuestro.
3. **`token_service`** — depende del repo.
4. **`auth_service`** — depende del repo. Acá los routers pasan a `await` (ver abajo).
5. **`usuario_service`** — el más delicado. Sin esto no se pueden crear usuarios.
6. **`middleware`** — último: hasta que entre, los tokens los sigue emitiendo Supabase.
7. **Recién ahí, deprecar `supabase_url`** de `settings.py`.

El orden importa: el middleware es el **último consumidor de `supabase_url` fuera de la
capa de datos** (`middleware/auth.py:35` arma el JWKS con esa URL). Borrarla antes del
paso 6 rompe la autenticación de toda la app aunque los repositories ya estén en RDS.

## Las 7 llamadas a Supabase Auth

| Dónde | Llamada actual | Reemplazo |
|---|---|---|
| `auth_service.py:49` | `auth.sign_in_with_password` | `AuthService.authenticate_user` (verifica `password_hash` con bcrypt local) |
| `auth_service.py:90` | `auth.refresh_session` | `TokenService.refresh_access_token` (rotación propia) |
| `auth_service.py:112` | `auth.admin.sign_out` | `TokenService.revoke_refresh_token` |
| `usuario_service.py:70` | `auth.admin.create_user` | `INSERT INTO users (..., password_hash)` con `hash_password` |
| `usuario_service.py:36` | `auth.admin.delete_user` (rollback) | ya no hace falta: sin identidad externa, no hay nada que revertir |
| `usuario_service.py:122` | `auth.sign_in_with_password` (reauth) | `verify_password(actual, user.password_hash)` |
| `usuario_service.py:126` | `auth.admin.update_user_by_id` | `UPDATE users SET password_hash = $1` |
| `usuario_service.py:145` | `auth.admin.delete_user` | `DELETE FROM users WHERE id = $1` |

(Son 8 call sites: `admin.delete_user` aparece dos veces, en el rollback y en la baja.)

## ⚠️ El punto más delicado: `usuario_service`

Tres cosas se rompen juntas y en silencio.

**1. La FK bloquea el alta.** `public.users.id` referencia `auth.users(id)`
(`db/schema.sql:1040`). Mientras viva, **todo INSERT en `users` exige una fila previa en
`auth.users`** — o sea, exige Supabase. Con `password_hash` agregado pero la FK viva, crear
un usuario sigue siendo imposible. Hay que dropearla (SQL en 075, comentado).

**2. El `ON DELETE CASCADE` es lógica de negocio viva, no schema.** Hoy
`eliminar_usuario` (`usuario_service.py:145`) borra `auth.users` y **confía en el cascade**
para limpiar `public.users`; un segundo cascade (`ON DELETE SET NULL`) desvincula
`empleados.user_id`. Al dropear la FK ese mecanismo desaparece: el service tiene que hacer
el `DELETE FROM users` a mano. Si se dropea la FK sin tocar el service, **el borrado deja
de borrar** y no falla — el usuario sigue pudiendo loguear.

El mismo cascade sostiene el rollback del alta (`usuario_service.py:90`): el comentario
dice *"borra auth.users; el CASCADE limpia el perfil si se insertó"*. Con auth propio el
alta es **un solo INSERT**, así que el rollback de dos pasos se vuelve innecesario — pero
el `_rollback_auth` hay que sacarlo, no dejarlo apuntando al vacío.

**3. El id no se autogenera.** `users.id` es `uuid NOT NULL` **sin DEFAULT**: siempre lo
proveyó gotrue (`usuario_service.py:79` lo toma de la respuesta de `create_user`). Sin
Supabase hay que generarlo — en la base (`DEFAULT gen_random_uuid()`, SQL en 075) o en
Python. Sin esto, el INSERT falla por `null value in column "id"`.

Lo que **no** cambia: la contraseña temporal (`secrets`, `usuario_service.py:23`),
`must_change_password`, la validación de unicidad y el audit. Todo eso ya es de RRHH.

## Migración de datos: no hay backfill de contraseñas

Los hashes bcrypt de Supabase **no se pueden leer por el SDK**. No hay nada que migrar: los
usuarios se recrean con contraseña temporal + `must_change_password=true` — el flujo que el
ABM ya tiene. Por eso `password_hash` es NULLABLE: un perfil sin credencial no puede
loguear (`authenticate_user` lo rechaza) pero no rompe la migración de las filas
existentes. Son ~3 usuarios de RRHH, no es un problema de escala.

## Desvíos respecto del patrón del proyecto hermano

Cinco, todos por convenciones reales de RRHH (verificadas, no supuestas):

1. **`settings` singleton, no `get_settings()`** — `settings.py:50` expone `settings = Settings()`;
   `get_settings()` no existe en RRHH.
2. **`AppError(message, code, status_code)` con code como STRING**, no enum. Se reusan los
   códigos que el frontend ya conoce: `INVALID_CREDENTIALS`, `INVALID_REFRESH_TOKEN`,
   `UNAUTHORIZED`, `MISSING_TOKEN`, `INVALID_TOKEN`.
3. **Claim `rol`, no `role`** — es el nombre real (columna `users.rol`, y
   `middleware/auth.py:131` arma `{"id", "rol"}`, que leen `utils/permisos.py` y los 142
   endpoints gateados).
4. **bcrypt directo, NO passlib** — `requirements.txt` trae `passlib[bcrypt]==1.7.4`, que
   está **roto** contra el bcrypt instalado (5.0.0): passlib lee `bcrypt.__about__`,
   atributo eliminado en bcrypt 4.1+. Verificado en este repo. No volver a passlib.
5. **Truncado a 72 BYTES, no 72 caracteres** — `password[:72]` son 72 chars, que en UTF-8
   pueden ser hasta 288 bytes; con acentos (esperables en RRHH) bcrypt seguiría
   explotando. Se trunca `password.encode("utf-8")[:72]`.

## Lo que hay que decidir antes de portar

- **Los services nuevos son ASYNC** (asyncpg), los actuales son SÍNCRONOS. `routers/auth.py:30`
  hace `return service.login(...)` sin await. **Al portar, los routers necesitan `await`.**
  Sin el await FastAPI devuelve la corrutina sin ejecutar: el login responde 200 con basura
  en vez de fallar. Es el error más fácil de cometer en esta migración.
- **Fallback a cookie en el middleware**: implementado porque estaba pedido, pero RRHH hoy
  es **header-only** (cero `set_cookie` en el backend, verificado). Aceptar cookies abre
  **CSRF**, del que Bearer estaba inmune. Mientras el frontend no setee la cookie es código
  muerto: o se borra, o se activa junto con SameSite=Strict + token CSRF.
- **El rol viaja en el token**: elimina el `SELECT rol` por request del middleware actual,
  pero un cambio de rol tarda hasta 60 min (o un refresh) en impactar. Hoy es inmediato.
- **`refresh_access_token` no es atómico**: delete + save sin transacción. Si el proceso
  muere en el medio, el usuario vuelve a loguear. Cerrarlo exige compartir conexión en el
  repo (refactor del `postgres_client`).
- **Enumeración de usernames por timing**: si el usuario no existe se responde sin correr
  bcrypt → más rápido. Mitigado de facto por el rate limit de 5/min por IP
  (`routers/auth.py:26`). El fix es un checkpw contra un hash dummy.

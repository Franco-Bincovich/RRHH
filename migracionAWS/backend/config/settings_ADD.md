# Delta de `config/settings.py` para la migración a AWS

Documenta **solo el cambio** que hay que aplicar a `backend/config/settings.py` cuando se
ejecute la migración. El `settings.py` real **no se toca todavía**: este archivo es la
referencia del delta.

Convención del repo: `settings.py` expone un **singleton de módulo** (`settings = Settings()`,
línea 50), consumido con `from config.settings import settings` en 8 archivos. **No hay
`get_settings()`** — si el patrón de referencia lo menciona, viene del proyecto hermano.

---

## AGREGAR

```python
    # Postgres (RDS)
    database_url: str  # postgresql://usuario:password@host.rds.amazonaws.com:5432/dbname
```

Sin default: si falta, pydantic-settings falla al arrancar con un error claro en vez de
intentar conectar a una DSN vacía.

`postgres_client.py` la lee en tiempo de llamada (dentro de `init_pool()`), no en el import.

**Ojo con el password en la DSN:** si tiene caracteres especiales (`@`, `:`, `/`, `#`),
hay que URL-encodearlos o la DSN se parsea mal. En producción esta variable sale de
Secrets Manager / SSM Parameter Store, nunca del `.env` commiteado.

## DEPRECAR (borrar al completar la migración)

Las cuatro se van junto con `integrations/supabase_client.py`:

| Variable | Hoy |
|---|---|
| `supabase_url` | DSN del proyecto Supabase + base del JWKS en `middleware/auth.py` |
| `supabase_anon_key` | cliente anon (respeta RLS) |
| `supabase_service_key` | cliente admin (bypassa RLS) |
| `supabase_timeout` | timeout httpx (30s) → lo reemplaza `command_timeout=30` del pool |

**No borrarlas de una.** `supabase_url` tiene un consumidor que no es la capa de datos:

```python
# middleware/auth.py:35
_JWKS_URL = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
```

El middleware verifica cada JWT contra el JWKS de Supabase (ES256). Mientras auth siga en
Supabase Auth, **`supabase_url` sigue viva aunque la capa de datos ya esté en RDS**. Se
borra recién cuando auth deje de depender de Supabase.

## YA EXISTEN, sin uso real — se activan al migrar auth

```python
    jwt_secret: str
    jwt_expiration_minutes: int = 60
    refresh_token_expiration_days: int = 30
```

Declaradas hoy pero **inertes**: el middleware valida contra el JWKS ES256 (clave pública
de Supabase), no contra `jwt_secret`. Cuando RRHH emita sus propios tokens, estas tres
pasan a ser las de verdad. No hace falta agregarlas — ya están.

---

## Orden

1. Agregar `database_url`. Las de Supabase quedan.
2. Migrar la capa de datos (repositories → `postgres_client`).
3. Migrar auth (requiere resolver que **no existe `password_hash`**: las credenciales viven
   en `auth.users` de Supabase; ver el diagnóstico de migración).
4. Recién entonces borrar las cuatro `supabase_*`.

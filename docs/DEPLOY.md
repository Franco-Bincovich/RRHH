# Deploy y reconstrucción — HR Karstec (RRHH)

> **Para quien monte la infraestructura.** Todo lo de acá está verificado contra el código el
> **2/8/2026**, no copiado de otro documento. Si algo no coincide con lo que ves, **manda el
> código**: `backend/config/settings.py` para variables, `backend/db/schema.sql` para el schema.

---

## 1. Variables de entorno

### Backend — OBLIGATORIAS (sin default)

🔴 **Si falta una, la app NO ARRANCA.** `Settings()` se instancia en el import de
`config/settings.py`, así que un `ValidationError` acá tumba el proceso entero: **ni `/health`
responde**. No hay degradación parcial.

| Variable | Para qué |
|---|---|
| `SUPABASE_URL` | Proyecto Supabase |
| `SUPABASE_ANON_KEY` | Cliente público |
| `SUPABASE_SERVICE_KEY` | Cliente admin — **todo el backend lo usa**; RLS no aplica a este rol. También habilita la **Admin API de Auth** (ver abajo) |
| `JWT_SECRET` | Firma/verificación de sesión |
| `ANTHROPIC_API_KEY` | Reportes con IA. **Obligatoria aunque el reporte adhoc esté oculto** |

> 🔑 **La service key tiene que poder llamar a la Admin API de Auth (`/auth/v1/admin/*`).**
> **Verificado el 3/8/2026: no hay nada que habilitar.** En Supabase, `service_role` ya tiene
> esa capacidad por definición — es la clave que la Admin API espera— y el backend la viene
> usando desde antes: `create_user` y `delete_user` en el alta de usuarios
> (`services/_usuario_alta.py:35,70`), `update_user_by_id` en el cambio de contraseña
> (`services/usuario_service.py:58`) y `sign_out` en el logout (`services/auth_service.py:128`).
> **La baja blanda no agrega un permiso nuevo: usa `update_user_by_id`, la MISMA llamada que ya
> corría** (`usuario_service.py:100`), solo que con `ban_duration` en vez de `password`.
>
> **Lo que sí hay que revisar el día del cutover a AWS:** si la identidad deja de vivir en
> Supabase Auth, `ban_duration` no existe del otro lado. El equivalente hay que construirlo —
> revocar los refresh tokens de `refresh_tokens` (mig 076). Mientras tanto, **la mitad que
> corta de verdad es `users.activo`, que es una columna nuestra y sobrevive a la mudanza**; el
> ban solo cierra la canilla de tokens nuevos.
>
> 🔧 **Revertir una baja (a mano, no hay endpoint):** `UPDATE users SET activo = true WHERE id = ...`
> **y** `update_user_by_id(id, {"ban_duration": "none"})` desde el dashboard o un script con la
> service key. **Hacen falta las dos:** solo la primera lo deja entrar pero sin poder renovar el
> token cuando expire; solo la segunda no lo deja entrar (el middleware sigue viendo `activo=false`).

> ⚠️ **`RESEND_API_KEY` YA NO EXISTE.** Se sacó el 2/8/2026 (los mails salen por Gmail). Era
> obligatoria y ningún service la importaba: lo único que podía hacer era tumbar el arranque.
> **No la agregues.** Si la ves en un documento viejo, ese documento está desactualizado.

### Backend — CON DEFAULT

| Variable | Default | Cuándo tocarla |
|---|---|---|
| `APP_ENV` | `development` | `production` en prod |
| `ASSESSMENT_ENABLED` | `false` | `true` reactiva el módulo entero (router + rutas públicas). **Cero cambios de código** |
| `SUPABASE_TIMEOUT` | `30` (s) | Timeout httpx de PostgREST/Storage. **Es el techo más bajo de un export** |
| `IMPORT_PRESUPUESTO_SEGUNDOS` | `280.0` | Presupuesto del import de nómina. Debe quedar **por debajo** del techo de función |
| `MAIL_PRESUPUESTO_SEGUNDOS` | `120.0` | Presupuesto del envío masivo. Más chico a propósito: cada unidad es red externa |
| `JWT_EXPIRATION_MINUTES` | `60` | |
| `REFRESH_TOKEN_EXPIRATION_DAYS` | `30` | |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | `""` | Sin ellas, conectar Gmail da `GOOGLE_NOT_CONFIGURED` (503). El resto del sistema anda |
| `GOOGLE_REDIRECT_URI` | `http://localhost:8000/api/integraciones/google/callback` | 🔴 **Cambiar en prod** y darla de alta en la consola de Google |
| `FRONTEND_URL` | `http://localhost:3000` | Redirects post-OAuth |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:3001` | 🔴 CSV **sin barra final**. Si falta el origin del front, el preflight `OPTIONS` da 400 y **el login falla** |
| `TRUSTED_PROXY_HOPS` | `1` | Cuántos proxies CONFIABLES hay delante. Define qué entrada de `X-Forwarded-For` es la IP real |
| `RATE_LIMIT_STORAGE_URI` | `memory://` | Store de los contadores de rate limit |

### 🔴 Las dos que hay que revisar sí o sí al mudarse a AWS

**`TRUSTED_PROXY_HOPS`** — se toma `hops[-N]` contando desde la derecha, porque esas entradas las
escribió nuestra infraestructura y las de la izquierda las puede falsificar el cliente.

| Topología | Valor |
|---|---|
| Local, sin proxy | `0` |
| Vercel | `1` |
| AWS con ALB solo | `1` |
| AWS con CloudFront + ALB | `2` |

> 🔴 **Un valor de MÁS colapsa todo el tráfico en un solo contador y deja al equipo entero
> afuera con 429.** Un valor de menos permite falsificar la IP. Verificalo con un request real
> mirando el header, no por deducción.

**`RATE_LIMIT_STORAGE_URI`** — `memory://` es **por proceso**. En serverless cada cold start
arranca en cero y con N instancias vivas el límite efectivo es N×. El enchufe para `redis://…`
ya está puesto en el código; conectarlo es decisión de infraestructura.

### Frontend

| Variable | Obligatoria | Notas |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | ✅ | URL absoluta del backend, **sin barra final**. 🔴 **Es build-time**: cambiarla exige rebuild, no basta con reiniciar. **El día del cutover a AWS, esta es la única variable que cambia** |
| `ANTHROPIC_API_KEY` | ❌ | Solo la usa `/api/ai` (chat, hoy oculto). Si falta, esa ruta da 500; **no rompe el build**. Hoy no está cargada, por decisión |

---

## 2. Reconstruir la base desde cero

🔴 **`backend/db/schema.sql` es la ÚNICA fuente de verdad del schema.** Se lee del catálogo de
Postgres (`information_schema` / `pg_catalog`), no se deriva del historial de migraciones.

**Estado verificado el 7/8/2026 contra el catálogo vivo: 58 tablas · 698 columnas · 364
constraints (153 FK + 103 CHECK + PK/UNIQUE) · 151 índices declarados.** El contraste dio **0
diferencias** en las dos direcciones: no hay nada en `schema.sql` que no exista en producción, ni
al revés. (Producción reporta 259 índices; los 108 de diferencia son los que Postgres crea solo
por PK/UNIQUE, y salen de las constraints que el archivo sí declara.)

### Procedimiento

1. Crear una base vacía.
2. Correr `backend/db/schema.sql` completo.
3. **NO correr las migraciones encima.** El schema ya las incluye a todas.
4. Correr los **dos** scripts de triggers de la tabla de abajo. Sin ellos el esquema queda
   estructuralmente completo pero **sin comportamiento**.

### Lo que `schema.sql` NO trae

🔴 **No trae ninguna función ni ningún trigger.** El snapshot se leyó del catálogo para tablas,
columnas, constraints, índices y defaults. Producción tiene **50 triggers** no internos y el
archivo trae **0**.

| | |
|---|---|
| **Datos** | Solo estructura. Los catálogos base (tipos de ausencia, etc.) hay que sembrarlos |
| 🔴 **Los 41 triggers de `updated_at`** | Se recrean con `migracionAWS/backend/migrations/077_recrear_triggers_updated_at.sql` (+ la función `set_updated_at`). **Sin ellos, `updated_at` queda congelado en el valor del INSERT y nadie se entera** |
| 🔴 **Los 9 triggers `trg_emp_*`** | Se recrean con **`backend/migrations/094_recrear_triggers_empresa.sql`** (+ la función `fn_misma_empresa`). Hacen cumplir que un registro y las filas que referencia sean de la MISMA empresa — una FK garantiza que el área existe, no que sea de la empresa del empleado. **Hasta el 7/8/2026 existían solo en producción, sin ningún artefacto que los recreara: un rebuild los perdía en silencio** |
| **Esquemas internos de Supabase** (`auth`, `storage`) | La única referencia externa es `users.id → auth.users(id)`. 🔴 **En AWS hay que dropear esa FK** y ponerle `DEFAULT gen_random_uuid()`, o no se puede insertar un usuario |

### `migrations/` es historial, NO bootstrap

**001 → 094.** Documentan cómo se llegó hasta acá. Correrlas en orden contra una
base vacía **no reconstruye producción de forma confiable**: hay dependencias de orden rotas,
operaciones no idempotentes, y parte del modelo multiempresa se aplicó a mano en producción y se
versionó retroactivamente de forma incompleta.

Siguen siendo el lugar donde se versiona **cada cambio nuevo**. ⚠️ Al aplicar una migración nueva,
`schema.sql` queda desactualizado: **hay que regenerarlo desde el catálogo**.

> **`000_run_all.sql` está DEPRECADO** y tiene un guard que aborta la ejecución. Declaraba cubrir
> 001 → 024, quedó ~65 migraciones atrás, y reintroduce triggers de auditoría que fueron
> dropeados (la captura hoy es app-level). Se conserva solo como historial.

### Migraciones destructivas — las únicas dos

| # | Qué borra | Riesgo |
|---|---|---|
| **084** `drop_modalidad_contratacion_y_nivel` | 🔴 **DROP COLUMN** sobre `empleados` | Irreversible. Ya corrida |
| **080** `create_oauth_states` | `DROP` de objetos propios antes de recrearlos (idempotencia) | Bajo |

Las 85 restantes son aditivas: `CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`, índices.

**Estado en producción (verificado 7/8/2026 contra el catálogo vivo):** **001 → 093 corridas
TODAS**, incluida la 089 (`ausencias_unicidad`), que estaba pendiente al 2/8. 🔴 **La 094
(`recrear_triggers_empresa`) NO está corrida y NO hace falta correrla en producción**: los 9
triggers ya existen ahí. Existe para el **rebuild** (RDS), que es donde faltaban.

### Buckets de Storage

`documentos` · `cvs` · `avatars`. ⚠️ `_BUCKET = "documentos"` está **hardcodeado** en el service
de adjuntos: al migrar a S3 hay que parametrizarlo. El E2E de adjuntos **nunca se ejecutó** por
eso mismo.

---

## 3. Techos de la plataforma — medidos, no estimados

| Techo | Valor | De dónde sale | En AWS |
|---|---|---|---|
| **Duración de función** | **300 s** | `backend/vercel.json` → `maxDuration` | Lo define **Lambda** (máx 900 s) o el **timeout del ALB** (default 60 s 🔴) |
| **Payload de request** | **4,5 MB** | Vercel lo rechaza **antes de que el código lo vea**: no hay forma de dar un error propio | **ALB: 1 MB por default** en algunos modos 🔴. API Gateway: 10 MB |
| **Timeout de PostgREST** | **30 s** | `settings.supabase_timeout` | Con RDS directo (asyncpg) pasa a ser `command_timeout=30` en `postgres_client.py` |
| **`statement_timeout` del rol** | **~8 s** | Rol `authenticator` de Supabase | Lo define el parameter group de RDS |

### Los límites de la app derivados de esos techos

| Constante | Valor | Dónde | Por qué |
|---|---|---|---|
| `MAX_SIZE_SUBIDA` | **4,2 MB** | `utils/files.py:27` | Por debajo de los 4,5 de plataforma: el multipart agrega headers y el nombre del archivo, así que un archivo de exactamente 4,5 MB ya se pasa |
| `LIMITE_FILAS_EXPORT` | **5000** | `services/_limite_export.py:36` | 🔴 **El techo real de un export no son las filas, es el TIEMPO.** Manda el timeout de 30 s. Un número alto "por las dudas" reproduce el bug con otra cara: en vez de un archivo truncado, un timeout sin mensaje |
| `IMPORT_PRESUPUESTO_SEGUNDOS` | **280** | env | Debajo de los 300. Al agotarse, el import corta **entre filas** y devuelve el reporte parcial |
| `MAIL_PRESUPUESTO_SEGUNDOS` | **120** | env | Más chico: cada unidad es una llamada de red externa |

> 🚩 **Al mudarse a AWS hay que RE-MEDIR estos cuatro.** Están calibrados contra Vercel. Si el
> timeout del ALB queda en 60 s, un import con presupuesto de 280 s muere **antes** de poder
> cortar ordenadamente — y el reporte parcial, que es lo que lo hace reintentable, no llega.

---

## 4. Orden de deploy

**Son dos proyectos separados**, y el orden no es opcional:

1. **Correr las migraciones pendientes** contra la base.
2. **`sofia-backend`** (Root Directory `backend`) → esperar READY y verificar
   `curl -i https://<host>/health` → **200**.
3. **`sofia-front`** (Root Directory `frontend`) → esperar READY.
4. Recién entonces probar la feature.

> Si una feature nueva del front tira 404 en una llamada al backend, **es que el front salió
> antes**. Esperar al backend y reprobar; no tocar código.

### Minas ya desactivadas — no repetir

- 🔴 **Auto-asignación de dominios / Instant Rollback:** si hay un Instant Rollback activo o la
  auto-asignación deshabilitada, cada push crea un deployment que **el dominio no toma**. Síntoma:
  arreglás algo, pusheás, y el bug persiste. **Verificar siempre que el "Production Deployment"
  muestre el commit nuevo.**
- El `vercel.json` de la raíz era config mono-proyecto heredada: **borrado**.
- Había un `package-lock.json` stub en la raíz que confundía la inferencia de workspace: **borrado**.
- `backend/pyproject.toml` hacía que `@vercel/python` lo tratara como paquete instalable y
  abortara el build: reemplazado por `ruff.toml` + `pytest.ini`.
- La raíz `/` del front redirige a `/login`. El backend en `/` da 404 de plataforma (no tiene
  endpoint raíz): **es normal**, `/health` es el que responde.

---

## 5. Notas para AWS (asyncpg / RDS / S3)

El código nuevo vive aislado en `migracionAWS/`, sin tocar `backend/`. Minas ya identificadas:

- **asyncpg devuelve UUID nativos** → cast `str()` explícito en los mappers.
- **`passlib` está roto** (bcrypt 5.0 sacó `__about__`) → usar `import bcrypt` directo.
- **No habrá RLS**: la seguridad es app-level. Es una decisión, no una omisión.
- **Secretos en SSM Parameter Store / Secrets Manager**, nunca hardcodeados. URL-encodear los
  caracteres especiales del password en la DSN.
- `postgres_client.py` ya usa `ssl="require"` y `command_timeout=30`. **Faltan** (decisión de
  infra): timeout de conexión explícito (el default de 60 s cuelga el arranque si RDS es
  inalcanzable) y `verify-full` en vez de `require`.
- **Modelo Anthropic:** que ningún string con fecha sobreviva. Alias sin fecha: `claude-sonnet-4-6`.

---

## Qué leer después

| Necesitás | Documento |
|---|---|
| Qué cambió y qué te afecta, por sesión | [`BITACORA-CAMBIOS.md`](BITACORA-CAMBIOS.md) |
| Verificar que el backend responde | [`SMOKE-TEST.md`](SMOKE-TEST.md) |
| El schema real | `backend/db/schema.sql` |
| Por qué se decidió cada cosa | [`DECISIONES.md`](DECISIONES.md) |

# Deploy y reconstrucción — HR Karstec (RRHH)

> **Para quien monte la infraestructura.** Todo lo de acá está verificado contra el código el
> **2/8/2026**, no copiado de otro documento. Si algo no coincide con lo que ves, **manda el
> código**: `backend/config/settings.py` para variables, `backend/db/schema.sql` para el schema.

---

## 0. Levantar el sistema desde cero

> **Para alguien que nunca vio este repo.** Son cuatro piezas: una base Postgres, un backend
> Python, un frontend Next.js y —opcional— una cuenta de Google para la integración de Gmail.
> El orden importa en dos lugares y están marcados.

### Lo que hace falta tener instalado

| | Versión | Por qué esa |
|---|---|---|
| Python | **3.11 o 3.12** | 3.11 es la de producción (Vercel). En Mac, 3.12 anda; el `python3` del sistema puede traer una versión vieja de `supabase` que rompe el import — **siempre venv** |
| Node | **20+** | Next.js 16 |
| Una base **PostgreSQL** | 15+ | Hoy es Supabase; el destino es RDS |

### El orden, entero

**1 · La base.** Crear una base vacía y correr `backend/db/schema.sql` completo. Después, los
**dos** scripts de triggers (§2). 🔴 **No correr las migraciones encima**: `schema.sql` ya las
incluye a todas, y `migrations/` es historial, no bootstrap. El detalle está en §2.

**2 · El backend.**

```bash
cd backend
python3 -m venv venv && source venv/bin/activate      # en Windows: venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp ../.env.example .env    # y completar los 5 valores obligatorios de §1
uvicorn main:app --reload --port 8000
```

🔴 **Los DOS requirements, no sólo el primero.** Sin `requirements-dev.txt` la suite de tests
falla con **33 errores que no son del código**: sin `pytest-asyncio` los tests async "no están
soportados nativamente" y sin `python-docx` revientan los de export. Es la confusión más
repetida de este repo — instalá los dos antes de creerle a un rojo.

Verificación: `curl -i http://localhost:8000/health` → **200** con `{status, env}`. Es el único
endpoint sin auth del sistema base. 🔴 **`/` da 404 y eso es correcto**: el backend no tiene
endpoint raíz.

**3 · El frontend.**

```bash
cd frontend
npm install
cp ../.env.example .env.local   # 🔴 .env.local, NO .env — Next sólo lee el primero
npm run dev
```

De ese archivo el front sólo usa `NEXT_PUBLIC_API_URL` (obligatoria), `NEXT_PUBLIC_MARCA` y
`ANTHROPIC_API_KEY` (opcional, sólo el chat). Las demás las ignora.

🔴 **`NEXT_PUBLIC_API_URL` es build-time.** En `npm run dev` se relee al reiniciar, pero en un
deploy queda horneada en el bundle: cambiarla en el panel sin redeployar no hace absolutamente
nada. Ver §1.

**4 · Datos mínimos para que las pantallas no salgan vacías.** El schema trae estructura y nada
más. Hace falta, como mínimo: **una empresa**, **un usuario** y **los tipos de ausencia base**.
Crear un usuario a mano son tres pasos y el orden no es opcional:

1. Crear el auth user en el dashboard de Supabase con **Auto Confirm** encendido.
2. Copiar el UUID que quedó.
3. `INSERT` en `public.users` con **ese mismo id** (hay una FK `users.id → auth.users(id)`),
   `rol` en `admin_rrhh` | `gerencia_lectura` | `mandos_medios`.

⚠️ En AWS esa FK se dropea y el id pasa a ser `DEFAULT gen_random_uuid()` — ver §5.

**5 · Google, sólo si se quiere Gmail.** Es independiente del resto: sin configurar, conectar
Gmail devuelve un 503 con `GOOGLE_NOT_CONFIGURED` y **nada más del sistema se rompe**. El
procedimiento está en §6.

### Verificar que quedó bien — los cuatro comandos

```bash
cd backend  && venv/bin/python -m pytest -q       # esperado: 4553 passed, 14 skipped
cd frontend && node_modules/.bin/tsc --noEmit     # esperado: 0 errores
cd frontend && npm test                           # esperado: 1717 passed en 152 archivos
cd frontend && npm run build                      # esperado: "Compiled successfully"
```

🔴 **Los cuatro, y `npm run build` NO es redundante con `tsc`.** Miran cosas distintas: `tsc` los
tipos, `vitest` el comportamiento, y `build` las reglas de Next y la compilación real de
Tailwind/Turbopack — un `import` colocado arriba de un `"use client"` rompe el build y `tsc` no
dice una palabra, porque es una regla de Next y no del sistema de tipos.

> ⚠️ **En Mac, `npm run build` deja basura que rompe el `tsc` siguiente.** Aparecen duplicados
> de `.next/types/routes.d.ts` con un sufijo numérico que va subiendo (`routes.d 2.ts`, luego
> `routes.d 3.ts`), y como `tsconfig.json` incluye `.next/types/**/*.ts`, el `tsc` siguiente da 3
> errores que no son del código. Limpiar con `find .next -name "* [0-9].*" -delete`, o correr el
> build **último**.
>
> ⚠️ **En Mac, `npx tsc` a secas baja el paquete equivocado** (`tsc@2.0.4`, que no es TypeScript).
> Usar siempre el binario local: `node_modules/.bin/tsc`.

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

**Estado reverificado el 26/8/2026 contra el catálogo vivo, ya con las migraciones 113–123
corridas — objeto por objeto, no por conteo:**

| | `schema.sql` | Producción | |
|---|---|---|---|
| Tablas | **55** | **55** | ✅ mismos nombres, `EXCEPT` vacío en las dos direcciones |
| Columnas | **691** | **691** | ✅ y también su tipo, nullable y default |
| CHECK constraints | **106** | **106** | ✅ comparados por definición, no por nombre |
| Índices standalone | **164** | **164** | ✅ incluidos los parciales y los funcionales |
| FKs | **140** | **141** | ✅ la de más es la de `users.id`, ver abajo |
| Triggers no internos | **0** | **46** | 🔴 el archivo no los trae — ver abajo |

**Las ÚNICAS dos divergencias son la misma decisión y están las dos sobre `users.id`:**
`schema.sql` **no declara** la FK `users.id → auth.users(id)` y **sí le pone**
`DEFAULT gen_random_uuid()`. Es específica de Supabase y era el único bloqueante del replay en
RDS (ver `migracionAWS/` y el encabezado del propio `schema.sql`).

- **No compares "constraints" con un solo número.** El catálogo cuenta cada `NOT NULL` como CHECK
  (hoy da 705 en total), así que ese total no es comparable con nada que se lea del archivo. La
  cuenta de FKs sí lo es.
- Producción reporta **259 entradas en `pg_indexes`**; la diferencia con las 164 standalone son
  los índices que Postgres crea solo por PK/UNIQUE, y salen de las constraints que el archivo sí
  declara.
- 🔴 **`schema.sql` tampoco trae RLS**, y producción lo tiene encendido en las 55 tablas. Ver
  [`handoff-aws/RLS.md`](handoff-aws/RLS.md): la decisión es que en AWS **no va**, así que el
  rebuild nace bien — pero por omisión, no por una línea que lo diga.

*(Acá decía «52 tablas · 133/134 FKs · 141/235 índices», medido el 12/8. Los cinco números
quedaron viejos con las migraciones 113–123; `handoff-aws/README.md` ya tenía los correctos.)*

### Procedimiento

1. Crear una base vacía.
2. Correr `backend/db/schema.sql` completo.
3. **NO correr las migraciones encima.** El schema ya las incluye a todas.
4. Correr los **dos** scripts de triggers de la tabla de abajo. Sin ellos el esquema queda
   estructuralmente completo pero **sin comportamiento**.

### Lo que `schema.sql` NO trae

🔴 **No trae ninguna función ni ningún trigger.** El snapshot se leyó del catálogo para tablas,
columnas, constraints, índices y defaults. Producción tiene **46 triggers** no internos y el
archivo trae **0**. *(Recontado contra el catálogo el 26/8/2026: acá decía 43 / 35 / 8, medido el 12/8.)*

| | |
|---|---|
| **Datos** | Solo estructura. Los catálogos base (tipos de ausencia, etc.) hay que sembrarlos |
| 🔴 **Los 38 triggers de `updated_at`** | Se recrean con `migracionAWS/backend/migrations/077_recrear_triggers_updated_at.sql` (+ la función `set_updated_at`). **Sin ellos, `updated_at` queda congelado en el valor del INSERT y nadie se entera.** La 077 declara exactamente esas 38 tablas, verificado el 26/8. Los sobrantes de las 11 tablas que dropeó J5 **ya se sacaron** — si no, `DROP TRIGGER IF EXISTS x ON tabla` aborta el script entero cuando la TABLA no existe. 🔑 Lo vigila el barrido `tests/test_triggers_updated_at.py`, que compara `schema.sql` contra la 077 |
| 🔴 **Los 8 triggers `trg_emp_*`** | Se recrean con **`backend/migrations/094_recrear_triggers_empresa.sql`** (+ la función `fn_misma_empresa`). Hacen cumplir que un registro y las filas que referencia sean de la MISMA empresa — una FK garantiza que el área existe, no que sea de la empresa del empleado. **Hasta el 7/8/2026 existían solo en producción, sin ningún artefacto que los recreara: un rebuild los perdía en silencio.** `trg_emp_sucesion` se fue con `sucesion_posiciones` en la 112 |
| **Esquemas internos de Supabase** (`auth`, `storage`) | La única referencia externa es `users.id → auth.users(id)`. 🔴 **En AWS hay que dropear esa FK** y ponerle `DEFAULT gen_random_uuid()`, o no se puede insertar un usuario |

### `migrations/` es historial, NO bootstrap

**000 → 123** (121 archivos: faltan la 075, 076 y 077, que viven en `migracionAWS/`). 🔴 **123 es el NÚMERO de la última, no la cantidad.** Documentan cómo se llegó hasta acá. Correrlas en orden contra una
base vacía **no reconstruye producción de forma confiable**: hay dependencias de orden rotas,
operaciones no idempotentes, y parte del modelo multiempresa se aplicó a mano en producción y se
versionó retroactivamente de forma incompleta.

Siguen siendo el lugar donde se versiona **cada cambio nuevo**. ⚠️ Al aplicar una migración nueva,
`schema.sql` queda desactualizado: **hay que regenerarlo desde el catálogo**.

> **`000_run_all.sql` está DEPRECADO** y tiene un guard que aborta la ejecución. Declaraba cubrir
> 001 → 024, quedó ~65 migraciones atrás, y reintroduce triggers de auditoría que fueron
> dropeados (la captura hoy es app-level). Se conserva solo como historial.

### Migraciones destructivas — hoy son cuatro

| # | Qué borra | Riesgo |
|---|---|---|
| **084** `drop_modalidad_contratacion_y_nivel` | 🔴 **DROP COLUMN** sobre `empleados` | Irreversible. Ya corrida |
| **109** `clientes_global_cierre` | 🔴 **DROP COLUMN** `clientes.empresa_id` + su FK e índice | Irreversible. Ya corrida. Iba **después** de que el código nuevo estuviera en producción |
| **112** `drop_tablas_muertas` | 🔴 **DROP TABLE ×11** (las 5 `ev_*` y las 6 huérfanas), y con ellas 50 índices, 9 triggers, 17 policies y 66 constraints | Irreversible. Ya corrida. Iba **después** del deploy de J5a, nunca antes |
| **080** `create_oauth_states` | `DROP` de objetos propios antes de recrearlos (idempotencia) | Bajo |

Las restantes son aditivas: `CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`, índices.

**Estado en producción (verificado objeto por objeto el 12/8/2026): ✅ NO hay migraciones
pendientes.** Corridas la **080, 089 y 102–112**. Producción quedó en **52 tablas**, sin ninguna
`ev_*`, y `clientes` sin `empresa_id` (2 índices, 0 FKs salientes, los 4 clientes y su hora
imputada intactos). `db/schema.sql` refleja ese estado exactamente.

🔴 **La 094 (`recrear_triggers_empresa`) NO está corrida y NO hace falta correrla en producción**:
los triggers ya existen ahí. **Y para el rebuild tampoco se usa** — quedó desincronizada de la 112
(declara un trigger sobre una tabla dropeada). El rebuild usa **`db/funciones_y_triggers.sql`**,
generado del catálogo vivo. Ver la sección de reconstrucción en `docs/handoff-aws/README.md`.

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
| `LIMITE_FILAS_EXPORT` | **20000** | `services/_limite_export.py` | 🔴 **El techo real de un export no son las filas, es el TIEMPO — y el timeout que corta NO es el de PostgREST.** Medido sobre 27.597 filas: traer las filas 4,2 s, CSV 4,1 s, Excel 39-53 s, **PDF 126 s**. La base aporta el 8%; el 92% es construir el archivo, así que el que rige es el techo de **función (300 s)**, no los 30 s de httpx. Era 5.000 hasta el 13/8/2026 y no alcanzaba ni para UN MES de auditoría a escala. ⚠️ Lo que 20.000 NO cubre es el año entero (~64.000 eventos): eso pide export asíncrono, no un número más grande |
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

## 6. Google Cloud — la integración de Gmail

**Qué es.** Una sola conexión OAuth que hace **dos** cosas: **recibe** los mails de candidatos
(`gmail_service.py`) y **envía** los mails de RRHH (`services/mailer/`). No hay dos integraciones.

🔴 **Lo primero que hay que entender, porque no es evidente: la casilla es UNA SOLA, del
SISTEMA, y no la del usuario que aprieta el botón.** Es una decisión de producto, no una
limitación: un proceso automático no tiene un `user_id` que aportar, y con casilla designada el
circuito de prueba y el real son el MISMO. Quien conecta define de qué dirección van a salir
todos los mails del sistema.

### Los pasos en la consola

1. **Crear (o elegir) un proyecto** en `console.cloud.google.com`.
2. **Habilitar la Gmail API**: APIs & Services → Library → "Gmail API" → Enable. Sin esto el
   OAuth completa bien y la primera llamada falla con `accessNotConfigured`.
3. **Configurar la OAuth consent screen.**
   - Tipo **Internal** si la casilla es de un Google Workspace del dominio: es lo que
     corresponde y evita el proceso de verificación de Google.
   - Tipo **External** si la casilla es un Gmail común. 🔴 En External, mientras la app esté en
     **Testing**, el `refresh_token` **caduca a los 7 días** y hay que reconectar. Es la mina
     más cara de esta integración y no da ningún error hasta que se rompe. Ver "Lo que queda
     abierto" en el handoff.
   - Agregar los cuatro scopes de abajo y, en Testing, agregar la casilla como **Test user**.
4. **Crear las credenciales**: Credentials → Create → OAuth client ID → **Web application**.
   Copiar `Client ID` y `Client secret` a `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`.
5. **Registrar el redirect URI**, en "Authorized redirect URIs", **exactamente igual** al valor
   de `GOOGLE_REDIRECT_URI`:

   ```
   http://localhost:8000/api/integraciones/google/callback     ← desarrollo
   https://<host-del-backend>/api/integraciones/google/callback ← producción
   ```

   🔴 **Google compara string por string.** Una barra final de más, `http` en lugar de `https` o
   un host distinto dan `redirect_uri_mismatch` y el flujo ni siquiera arranca. Van los dos
   dados de alta, no uno.
6. **Conectar desde la app**: /configuracion → Integraciones → Conectar Google, con la casilla
   del sistema.

### Los cuatro scopes que se piden, y por qué esos

| Scope | Para qué |
|---|---|
| `gmail.readonly` | Recibir los mails de candidatos |
| `gmail.send` | Enviar. **Es el mínimo que permite mandar**: sólo mandar, ni leer ni borrar. Se prefiere a `gmail.modify` o `mail.google.com`, que dan el buzón entero para la misma tarea |
| `userinfo.email` + `openid` | Saber qué casilla quedó conectada, para mostrarla en pantalla |

> 🔴 **AGREGAR UN SCOPE OBLIGA A RECONECTAR, y Google no avisa.** No amplía retroactivamente un
> grant ya otorgado: el `refresh_token` viejo sigue siendo válido y sigue sirviendo para lo que
> ya tenía, pero el primer intento de usar el scope nuevo devuelve **403
> `ACCESS_TOKEN_SCOPE_INSUFFICIENT`** — un 403, no un 401, porque el token es válido y lo que
> falta es el permiso. Por eso el sistema persiste los scopes **realmente concedidos** (no los
> pedidos) y la pantalla de integraciones avisa ANTES, en vez de que alguien se entere por un
> 403 en medio de un envío masivo.

### El `state` del callback no es el `user_id`

Vale saberlo antes de tocar el flujo: el `state` es un **nonce de un solo uso** de 256 bits
(`secrets.token_urlsafe(32)`), persistido **hasheado** en la tabla `oauth_states` (migración
080) con TTL de 10 minutos, y **la identidad del usuario sale de la fila persistida, nunca del
query param**. El consumo es un `DELETE ... RETURNING`: el borrado ES la verificación, así que
si dos callbacks llegan a la vez con el mismo valor, la base le da la fila a uno solo.

🔴 **La tabla `oauth_states` tiene que existir antes de que el flujo funcione.** Si el destino se
levanta desde `schema.sql` ya está incluida; si se migra a mano, es la 080.

---

## 7. Si una migración falla a la mitad

### Lo primero: ¿en qué estado quedó?

**PostgreSQL ejecuta cada statement en su propia transacción implícita, no el archivo entero.**
O sea que un `.sql` que muere en el statement 7 de 12 deja **los 6 primeros aplicados y
commiteados**. No hay rollback automático del archivo. Esto es lo contrario de lo que mucha
gente asume, y es la razón por la que el diagnóstico se hace **mirando el objeto**, no el log.

```sql
-- ¿existe la tabla / la columna / el índice que la migración iba a crear?
select table_name, column_name from information_schema.columns
 where table_name = 'la_tabla' order by ordinal_position;
select indexname from pg_indexes where tablename = 'la_tabla';
select conname, contype from pg_constraint
 where conrelid = 'public.la_tabla'::regclass;
```

🔴 **Contar tablas NO alcanza para decir en qué estado quedó la base, y en este repo eso ya
costó una vez.** El encabezado de `schema.sql` afirmó que las migraciones 108–112 estaban todas
corridas habiendo verificado **sólo el conteo de tablas** (52 = 52). La 109 no crea ni borra
tablas —borra una columna y tres objetos— así que era invisible a esa comprobación, y estuvo
pendiente sin que nadie lo notara. **Hay que mirar el objeto que la migración toca.**

### Cómo se sale, según qué falló

| Caso | Qué hacer |
|---|---|
| **Aditiva** (`CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`, índices) | **Arreglar la causa y volver a correr el archivo entero.** Son idempotentes por construcción: los statements ya aplicados no hacen nada la segunda vez. Es el caso de la enorme mayoría |
| **Destructiva** (`DROP COLUMN` / `DROP TABLE`) | 🔴 **No hay vuelta atrás sin backup.** Antes de correr una, tomar un snapshot de la base. Hoy son cuatro y las cuatro ya corrieron: 084, 109, 112 y 080 |
| **Falló por dependencia de orden** (una FK a una tabla que todavía no existe) | Correr la que falta primero. Las migraciones declaran en su propio encabezado si exigen orden |
| **Falló a mitad y NO es idempotente** | Aplicar a mano **sólo los statements que faltan**, verificando objeto por objeto con las queries de arriba. No reejecutar el archivo: los primeros statements van a chocar |

### La mina concreta que ya está identificada

🔴 **`migrations/094_recrear_triggers_empresa.sql` aborta en un rebuild desde cero.** Declara 9
triggers `trg_emp_*`; el noveno es sobre `sucesion_posiciones`, **tabla que la migración 112
dropeó**. Y `DROP TRIGGER IF EXISTS x ON tabla` falla igual si la que no existe es la TABLA — el
`IF EXISTS` cubre el trigger, no la relación.

**Para el rebuild no se usa la 094**: se usa `backend/db/funciones_y_triggers.sql`, generado del
catálogo vivo. La 094 queda como historial. (Es la misma mina que la 077 ya tenía desactivada;
a la 094 no se le hizo.)

### Antes de correr cualquier migración en producción

1. **Snapshot de la base.** Es un botón en Supabase; en RDS es un snapshot manual.
2. **Leer el encabezado del archivo**: dice si es destructiva y si exige orden.
3. **Correrla en una branch de Supabase o en una copia**, no directo contra producción.
4. **Después, regenerar `backend/db/schema.sql` desde el catálogo.** Una migración aplicada sin
   regenerar el snapshot deja el documento de reconstrucción mintiendo, que es la deuda que este
   repo ya pagó tres veces.

---

## Qué leer después

| Necesitás | Documento |
|---|---|
| Qué cambió y qué te afecta, por sesión | [`BITACORA-CAMBIOS.md`](BITACORA-CAMBIOS.md) |
| Verificar que el backend responde | [`SMOKE-TEST.md`](SMOKE-TEST.md) |
| El schema real | `backend/db/schema.sql` |
| Por qué se decidió cada cosa | [`DECISIONES.md`](DECISIONES.md) |

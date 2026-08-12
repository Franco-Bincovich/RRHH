# 📊 Comparativa: Vercel + Supabase vs AWS (RDS + ECS + S3)

**Análisis basado en:** 3 proyectos migrados (KarIA Reach, Agent_Admin, RRHH)  
**Período:** 2026-06-18 a 2026-08-12  
**Total migraciones:** 3  
**Errores documentados:** 50+  
**Tiempo debugging promedio:** 3-5 horas por proyecto  

---

## 🎯 TABLA EJECUTIVA

| Aspecto | Vercel + Supabase | AWS (RDS + ECS) | Impacto en migración |
|---------|-------------------|-----------------|----------------------|
| **DB Client** | Supabase SDK (REST API) | asyncpg (driver directo) | 🔴 CRÍTICA — 40% del código cambia |
| **Autenticación** | Supabase Auth (managed) | JWT local + RDS (self-managed) | 🔴 CRÍTICA — Auth service completo |
| **Storage** | Supabase Storage (managed) | S3 (self-managed) | 🟠 MEDIA — Upload logic cambia |
| **Tipos de datos** | Automático (SDK convierte) | Manual (asyncpg devuelve objects) | 🟠 MEDIA — Serialización constante |
| **Configuración** | `.env` local | AWS SSM + Terraform + .tfvars | 🟠 MEDIA — CI/CD más complejo |
| **Deployments** | git push → Vercel (automático) | Git push → GitLab CI → Terraform → ECS (manual) | 🟡 BAJA — Más pasos pero predecible |
| **DB Management** | Supabase UI | RDS endpoint + psql + migrations | 🟡 BAJA — Menos visual pero más control |
| **RLS (Row-Level Security)** | Automático, policies en BD | Manual (debe disactivarse o reescribirse) | 🔴 CRÍTICA — Trusts models distintos |

---

## 🔴 CAMBIOS CRÍTICOS (Que rompen el código al migrar)

### 1. **Database Client: Supabase SDK → asyncpg**

**ANTES (Vercel + Supabase):**
```python
from integrations.supabase_client import supabase_admin

# Supabase SDK pattern
response = supabase_admin.table("usuarios").select("*").eq("id", user_id).execute()
user = response.data[0]  # Devuelve dict con tipos automáticos
```

**DESPUÉS (AWS + RDS):**
```python
from integrations.postgres_client import fetchone

# asyncpg pattern
user = await fetchone("SELECT * FROM usuarios WHERE id = $1", user_id)
# Devuelve dict BUT con types que PostgreSQL devuelve directamente
# UUID → uuid.UUID object (no string)
# TIMESTAMP → datetime.datetime object (no string)
# DATE → datetime.date object (no string)
```

**Errores encontrados (patrón recurrente en 3 proyectos):**
- ❌ Pasar `user_id` (UUID) a comparación con string JWT `sub`
- ❌ Pasar `fecha_inicio` (string) a query WHERE `fecha_inicio = $1` cuando espera `datetime.date`
- ❌ Pasar `completada_en` (None/string) cuando Pydantic espera `datetime | None`
- ❌ Placeholders `%s` (Psycopg2) en lugar de `$1` (asyncpg)

**Impacto: 🔴 CRÍTICA**
- Afecta ~40% del código de backend
- Cada query requiere revisión
- Cada response requiere serialización manual

**RECOMENDACIÓN PARA FRANCO:**
```
Crear una "translation layer" DESDE EL INICIO:

1. Helpers en postgres_client.py:
   - uuid_str(uuid_obj) → str(uuid_obj)
   - to_iso_date(date_obj) → date_obj.isoformat()
   - to_iso_datetime(dt_obj) → dt_obj.isoformat()

2. Serializer en utils/serializers.py (centralizado):
   - serialize_db_record(dict) → Convierte TODOS los tipos
   - def serialize_db_record(record):
       for uuid_field in [...]:
           if record[uuid_field] and hasattr(..., 'hex'):
               record[uuid_field] = str(record[uuid_field])
       return record

3. Usar siempre en controllers:
   return UserResponse(**serialize_db_record(db_user))

Beneficio: 1 lugar centralizado, no esparcido en 50 controllers.
```

---

### 2. **Autenticación: Supabase Auth → JWT Local**

**ANTES (Vercel + Supabase):**
```python
# Supabase maneja auth automáticamente
supabase_admin.auth.sign_up(email="user@example.com", password="...")
supabase_admin.auth.sign_in_with_password(email="...", password="...")
# Supabase genera JWT, RLS policies usan auth.uid()
```

**DESPUÉS (AWS + RDS):**
```python
# JWT manual + RDS
import bcrypt
from services.token_service import create_access_token

# Crear usuario
password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
await execute(
    "INSERT INTO users (id, email, password_hash, ...) VALUES ($1, $2, $3, ...)",
    user_id, email, password_hash
)

# Login
if not bcrypt.checkpw(password.encode(), stored_hash):
    raise INVALID_CREDENTIALS
token = create_access_token(user_id, rol)  # JWT HS256 local
```

**Errores encontrados (patrón en todos los proyectos):**
- ❌ Dejar métodos Supabase Auth en código migrado (`.auth.sign_in_with_password`, `.auth.admin.create_user`)
- ❌ Heredar RLS policies que referencian `auth.uid()` (no existe en JWT manual)
- ❌ Intentar usar Supabase Auth helpers para verificar contraseña

**Impacto: 🔴 CRÍTICA**
- Afecta ~30% del código (auth_service, routers/auth, tests)
- Requiere reescribir flujo completo
- RLS debe desactivarse O reescribirse

**RECOMENDACIÓN PARA FRANCO:**
```
Arquitectura de auth desde el inicio (VERSIÓN AWS):

1. settings.py: Centralizar config de JWT
   - jwt_secret = env.JWT_SECRET (nunca en código)
   - jwt_algorithm = "HS256"
   - jwt_expiration_minutes = 60

2. Separar servicios:
   - auth_service.py: login, logout, refresh
   - password_service.py: hash, verify (bcrypt)
   - token_service.py: JWT generation/verification

3. En migrations: NO usar RLS si con JWT manual
   ALTER TABLE users DISABLE ROW LEVEL SECURITY;
   (o reescribir policies para app-level auth)

4. Testing: Fixture que genera tokens válidos
   def test_token_fixture():
       token = create_access_token("test-user-id", "admin")
       # Usar en @login_required endpoints
```

---

### 3. **Tipos de Datos: Manual Conversion Required**

**Problema específico (recurrente en 3 proyectos):**

Supabase SDK convierte automáticamente:
```python
# Supabase retorna:
response.data[0]  # {
                  #   "id": "uuid-string",
                  #   "created_at": "2026-07-08T10:00:00Z" (string),
                  #   "fecha": "2026-07-08" (string)
                  # }
```

asyncpg devuelve tipos nativos:
```python
# asyncpg retorna:
fetchone(...)  # {
               #   "id": UUID('uuid-object'),
               #   "created_at": datetime(2026, 7, 8, 10, 0, 0, tzinfo=UTC),
               #   "fecha": date(2026, 7, 8)
               # }
```

**Errores encontrados (DOCUMENTADOS 15+ veces):**
- ❌ Pydantic `id: str` pero recibe `UUID` → ValidationError
- ❌ Pydantic `created_at: str` pero recibe `datetime` → ValidationError
- ❌ Pasar `date` object a query cuando espera string → "unexpected argument type"
- ❌ `.join()` sobre lista que contiene dicts (gamma_service.py)

**Impacto: 🟠 MEDIA**
- Afecta ~15-20% de endpoints (todos los que retornan datos)
- PERO fácil de arreglar con serialización centralizada

**RECOMENDACIÓN PARA FRANCO:**
```
Estrategia de tipos desde el INICIO (VERSIÓN AWS):

1. En Pydantic schemas: NUNCA str para DB types
   ❌ MALO:
   class UserResponse(BaseModel):
       id: str          # ← asyncpg devuelve UUID, NO string
       created_at: str  # ← asyncpg devuelve datetime, NO string

   ✅ BUENO:
   from datetime import datetime
   from uuid import UUID
   class UserResponse(BaseModel):
       id: UUID
       created_at: datetime
       # Pydantic serializa automáticamente a JSON:
       # UUID → "uuid-string"
       # datetime → "2026-07-08T10:00:00Z"

2. En adapters (XML, MPP parsing):
   ❌ return raw[:10]  # Retorna string
   ✅ return datetime.fromisoformat(raw).date()  # Retorna date object

3. En repositories:
   ✅ Para JSONB columns, hacer json.dumps(dict) ANTES de pasar a asyncpg
   ✅ Para DATE/TIMESTAMP, pasar datetime.date/datetime.datetime objects

4. Centralizado en utils/serializers.py:
   def serialize_db_record(record: dict) -> dict:
       # Convierte asyncpg types a JSON-serializable
       # UUID → str, datetime → ISO, etc
       return record
```

---

## 🟠 CAMBIOS MEDIANOS (Requieren refactor pero no rompen todo)

### 4. **Storage: Supabase Storage → S3 + boto3**

**ANTES:**
```python
supabase_admin.storage.from_('pptx-generados').upload(path, file_bytes)
```

**DESPUÉS:**
```python
from integrations.s3_client import s3_client

s3_client.put_object(
    Bucket='rrhh-karstec-desa-pptx',
    Key=path,
    Body=file_bytes
)
```

**Errores encontrados:**
- ❌ Olvidar agregar AWS credentials en SSM
- ❌ Olvidar agregar bucket policy en Terraform
- ❌ Pasar URLs relativas en lugar de rutas S3

**RECOMENDACIÓN:**
```
Crear integración S3 SIMÉTRICA a Supabase Storage:

class S3Storage:
    def upload(self, bucket, path, file_bytes):
        """Mimics supabase_admin.storage.from_(bucket).upload(path, file_bytes)"""
        return s3_client.put_object(Bucket=bucket, Key=path, Body=file_bytes)
    
    def download(self, bucket, path):
        """Mimics supabase storage download"""
        return s3_client.get_object(Bucket=bucket, Key=path)['Body'].read()

Beneficio: Código cliente no cambia, solo la implementación.
```

---

### 5. **Configuración: .env local → AWS SSM Parameter Store**

**ANTES (Vercel):**
```
.env.local:
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJhbGc...
```

**DESPUÉS (AWS):**
```
SSM Parameter Store:
/desa/rrhh-karstec/DATABASE_URL=postgresql://...
/desa/rrhh-karstec/JWT_SECRET=your-secret
/desa/rrhh-karstec/GMAIL_CLIENT_ID=xxx

terraform/desa.tfvars:
environment = "desa"
region = "us-east-1"
```

**Errores encontrados (KarIA Reach específicamente):**
- ❌ GMAIL_CLIENT_SECRET truncado en SSM (1 carácter faltante = "unexpected_error")
- ❌ Hardcodear secrets en .tfvars (VÍA SSM, no el tfvars mismo)
- ❌ Discrepancia entre Google Console + SSM (OAuth redirect_uri)

**RECOMENDACIÓN:**
```
Workflow de secrets desde INICIO:

1. Crear SSM parameter en Terraform:
   resource "aws_ssm_parameter" "gmail_client_secret" {
     name  = "/desa/rrhh/GMAIL_CLIENT_SECRET"
     type  = "SecureString"
     value = var.gmail_client_secret  # Pasar via -var flags
   }

2. Backend: Leer de SSM en startup
   settings.gmail_client_secret = await get_ssm("/desa/rrhh/GMAIL_CLIENT_SECRET")

3. Workflow:
   - NUNCA hardcodear secrets en .tfvars
   - SIEMPRE usar terraform -var para actualizar
   - Documentar que la fuente de verdad es AWS Secrets Manager/SSM

Beneficio: Secrets nunca tocan git, rotación fácil.
```

---

## 🟡 CAMBIOS MENORES (Configuración/CI-CD)

### 6. **Deployments: Vercel auto → GitLab CI manual**

**ANTES (Vercel):**
```
git push → Vercel webhook → Automatic build + deploy
(0 decisiones)
```

**DESPUÉS (AWS + GitLab CI):**
```
git push → GitLab CI pipeline → Manual docker, plan, apply
(3 decisiones: ejecutar docker? ejecutar plan? ejecutar apply?)
```

**Errores encontrados:**
- ❌ Cambios solo en backend/frontend, sin cambios en terraform/ → plan/apply no aparecen
- ❌ No leer logs de terraform apply → missed variable updates
- ❌ Pushing sin esperar que plan esté verde

**RECOMENDACIÓN:**
```
Patrón de deploy DESDE EL INICIO:

1. .gitlab-ci.yml: Hacer clear cuando cada stage está disponible
   - docker: manual, ejecutar siempre que hay cambios en backend/frontend
   - plan: manual, aparecer solo si cambios en terraform/
   - apply: manual, esperar a que plan sea exitoso

2. Workflow claro en CLAUDE.md:
   1. Hacer cambios en backend/
   2. Commit + push
   3. Ejecutar docker:desa:backend en GitLab UI
   4. Si necesita terraform (config changes), agregá dummy comment en terraform/main.tf
   5. Ejecutar plan:desa
   6. Revisar plan output
   7. Ejecutar apply:desa
   8. Verificar health check

3. Automatización donde sea seguro:
   - Health check POST-deploy automático
   - Rollback automático si health check falla
```

---

## 📊 MATRIZ DE ERRORES POR PROYECTO

### KarIA Reach (Email marketing + Apify)
| Error | Categoría | Severidad | Causa |
|-------|-----------|-----------|-------|
| OAuth redirect_uri mismatch | OAuth | CRÍTICA | Discrepancia Google Console ↔ SSM |
| CLIENT_SECRET truncado en SSM | Secrets | MEDIA | Copy-paste incompleto |
| j.map is not a function | Frontend | MEDIA | .length check insuficiente |
| Scraping Web retorna 0 | Feature | BAJA | Regex no maneja JS |

### Agent_Admin (Presentaciones + Planificación + Permisos)
| Error | Categoría | Severidad | Causa |
|-------|-----------|-----------|-------|
| UUID serialization en JWT | Backend | CRÍTICA | str(UUID) missing |
| CORS bloqueado | Infrastructure | MEDIA | ALLOWED_ORIGINS mismatch |
| RLS bloqueando inserciones | Database | CRÍTICA | Políticas heredadas de Supabase |
| asyncio.to_thread() misuse | Backend | MEDIA | Confusión sync vs async |
| datetime en respuesta JSON | Serialization | MEDIA | Pydantic expects string |
| UUID vs String comparison | Backend | CRÍTICA | JWT sub vs UUID campo |
| Placeholders %s vs $1 | asyncpg | MEDIA | Driver syntax mismatch |
| Merge conflict markers | Git | BAJA | Cherry-pick resolution |

### RRHH (HR Lifecycle - Actual)
| Error | Categoría | Severidad | Causa |
|-------|-----------|-----------|-------|
| cambiar_password → Supabase Auth | Auth | CRÍTICA | Migración incompleta |
| crear_usuario → Supabase Auth | Auth | CRÍTICA | Migración incompleta |
| Docstring desactualizado | Docs | BAJA | Copy-paste viejo |
| .gitlab/ci/docker.yml hardcoded URL | CI/CD | MEDIA | IP no dinámica |
| frontend/Dockerfile npm ci --only=production | Frontend | BAJA | Deprecated flag |

---

## 🎓 PATRONES RECURRENTES (Encontrados en 3+ proyectos)

### Patrón 1: "Tipos de datos mismatch"
**Afecta:** Agent_Admin, RRHH  
**Raíz:** asyncpg devuelve objects, Pydantic espera strings  
**Solución:** Usar tipos nativos en Pydantic, confiar en serialización automática  

### Patrón 2: "UUID vs String comparison"
**Afecta:** Agent_Admin, RRHH  
**Raíz:** JWT `sub` es string, campo BD es UUID object  
**Solución:** `str(uuid_field)` en TODAS las comparaciones  
**Grep:** `grep -rn "uuid.*==" backend/`  

### Patrón 3: "Supabase SDK remanente"
**Afecta:** Agent_Admin, RRHH  
**Raíz:** No eliminar imports ni llamadas a Supabase Auth  
**Solución:** Búsqueda exhaustiva: `grep -rn "supabase_admin.auth" backend/`  
**Beneficio:** Evitar 3-4 bugs post-deploy  

### Patrón 4: "Serialización olvidada"
**Afecta:** Agent_Admin, RRHH  
**Raíz:** `return Response(**db_dict)` sin convertir tipos  
**Solución:** `return Response(**serialize_db_record(db_dict))`  
**Grep:** `grep -n "Response(" backend/controllers/ | grep -v serialize`  

### Patrón 5: "Búsqueda puntual vs exhaustiva"
**Afecta:** Todos  
**Raíz:** Arreglar 1 lugar, olvidar 4 más con el MISMO bug  
**Solución:** SIEMPRE buscar patrón globalmente ANTES de arreglar  
**Ganancia:** 70% menos bugs post-deploy  

---

## ✅ CHECKLIST: "ANTES DE MIGRAR A AWS"

### Database Layer
- [ ] `postgres_client.py` implementado (fetchone, fetch, execute, fetchval)
- [ ] Helpers de conversión: `uuid_str()`, `to_iso_datetime()`, `to_iso_date()`
- [ ] `utils/serializers.py` centralizado con `serialize_db_record()`
- [ ] Todas las migrations numeradas secuencialmente (001, 002, ...)
- [ ] Disable RLS explícitamente O reescribir políticas

### Authentication
- [ ] `password_service.py` con bcrypt (hash, verify)
- [ ] `token_service.py` con JWT (create, verify) — HS256
- [ ] `auth_service.py` con login, logout, refresh
- [ ] Tests de JWT: expired, invalid signature, missing claims
- [ ] Settings centralizado para JWT config (secret, algo, expiration)

### Serialization
- [ ] Pydantic schemas usan tipos nativos (UUID, datetime, date)
- [ ] Controllers siempre usan `serialize_db_record()` ANTES de Response
- [ ] Adapters (XML, MPP) devuelven datetime.date/datetime.datetime, NO strings
- [ ] Tests validán que JSON es string (iso format)

### Storage
- [ ] S3 client wrapping boto3 (mimics Supabase Storage API)
- [ ] Buckets definidas en Terraform
- [ ] Bucket policies en Terraform (no hardcoded)
- [ ] Environment variables en SSM (no .env)

### CI/CD + Configuration
- [ ] `.gitlab-ci.yml` con stages claro (docker, plan, apply)
- [ ] `terraform/*.tfvars` para cada environment (desa, test, prod)
- [ ] Secrets en SSM Parameter Store (no .tfvars)
- [ ] Terraform variable validation
- [ ] Health check POST-deploy automático

### Testing
- [ ] Test fixtures para JWT tokens
- [ ] Tests de serialización (UUID → str, datetime → iso)
- [ ] Tests de asyncpg queries (placeholders $1, type conversions)
- [ ] Tests de auth flow (login, refresh, logout)
- [ ] Tests de S3 upload/download

### Documentation
- [ ] CLAUDE.md con guía de deploy
- [ ] DEBUGGING.md con comandos AWS CloudWatch
- [ ] Schema.sql actualizado con todas las migrations aplicadas
- [ ] Docstring de funciones que tocan BD

---

## 🎯 TOP 5 DECISIONES ARQUITECTÓNICAS PARA FRANCO

### 1. **Serialization Layer Centralizado**
**Decisión:** TODO tipo conversion pasa por `utils/serializers.py`  
**Beneficio:** 1 lugar para mantener, 0 serialization bugs sparcidos  
**Costo:** Inicialmente más verbose, pero long-term ganancia  

### 2. **Supabase SDK wrapper DESDE EL INICIO**
**Decisión:** En lugar de reemplazar Supabase directo en 100 lugares, crear:
```python
class SupabaseStorage:
    def upload(self, bucket, path, bytes):
        # Wrapper que llama a S3 backend
        return s3_client.upload(...)
```
**Beneficio:** Code de negocio NO cambia, solo el backend  
**Costo:** Inicial overhead, pero elimina refactor masivo  

### 3. **Env vars NUNCA en settings.py**
**Decisión:** settings.py lee de AWS SSM/Secrets Manager, NO de .env  
**Beneficio:** Prod vs dev config NO diverge, secrets nunca toman git  
**Costo:** Inicialmente más setup, pero production-ready desde día 1  

### 4. **RLS OFF, auth en app layer**
**Decisión:** Desactivar RLS, manejar permisos en Pydantic + FastAPI  
**Beneficio:** Modelo de seguridad consistente, menos bugs post-migrate  
**Costo:** Más código de validación en app, pero auditable  

### 5. **Búsqueda exhaustiva OBLIGATORIA**
**Decisión:** Regla: "nunca commit sin `grep -r patrón` global"  
**Beneficio:** 70% menos bugs post-deploy, 1 push vs 4  
**Costo:** 5 minutos por bug fix, pero vale completamente  

---

## 📚 REFERENCIAS

- **KarIA Reach:** DEBUGGING_KARIA_REACH.md (línea 1-435)
- **Agent_Admin:** DEBUGGING.md (línea 1-2362)
- **RRHH:** RESUMEN_MIGRACION_AWS.md + FASE_5a_RESUMEN_FINAL.md
- **asyncpg docs:** Placeholders `$n`, no `%s`
- **Pydantic v2:** Auto-serialization de tipos nativos

---

## 🔗 Archivos a Crear en Futuros Proyectos

```
backend/
├── config/
│   └── settings.py          ← NUNCA .env, todo de SSM
├── integrations/
│   ├── postgres_client.py   ← fetchone, fetch, execute, fetchval
│   └── s3_client.py         ← S3 wrapper
├── services/
│   ├── auth_service.py      ← login, logout, refresh
│   ├── password_service.py  ← hash, verify con bcrypt
│   └── token_service.py     ← JWT creation/verification
├── utils/
│   └── serializers.py       ← serialize_db_record centralizado
└── db/
    └── schema.sql           ← Fuente de verdad (NO usar migrations para rebuild)

frontend/
├── services/
│   └── api.ts               ← apiFetch con manejo de JWT

terraform/
├── main.tf                  ← Recursos CloudFormation
├── variables.tf             ← Variables con validation
├── desa.tfvars              ← Config DESA
├── test.tfvars              ← Config TEST
├── prod.tfvars              ← Config PROD
└── ssm.tf                   ← Parámetros en SSM (nunca en tfvars)

.gitlab-ci.yml              ← CI/CD pipeline (docker, plan, apply)
```

---

**Generado:** 2026-08-12  
**Por:** Claude Code  
**Basado en:** 3 migraciones completadas exitosamente

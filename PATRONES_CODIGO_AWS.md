# 🔧 Patrones de Código — Para Copiar en Futuros Proyectos AWS

**Uso:** Copy-paste estos fragmentos al crear un nuevo proyecto para AWS (RDS + ECS + S3)

---

## 1. `integrations/postgres_client.py` — Cliente asyncpg

```python
"""Cliente asyncpg para RDS PostgreSQL."""
import asyncpg
from config.settings import settings

pool: asyncpg.Pool | None = None

async def init_pool() -> None:
    """Inicializa pool de conexiones."""
    global pool
    pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=5,
        max_size=20,
    )

async def close_pool() -> None:
    """Cierra pool de conexiones."""
    global pool
    if pool:
        await pool.close()

def get_pool() -> asyncpg.Pool:
    """Retorna pool global (ya inicializado)."""
    if not pool:
        raise RuntimeError("Pool not initialized. Call init_pool() first.")
    return pool

async def execute(query: str, *args) -> None:
    """Ejecuta query que no retorna filas (INSERT/UPDATE/DELETE/DDL)."""
    conn = await get_pool().acquire()
    try:
        await conn.execute(query, *args)
    finally:
        await get_pool().release(conn)

async def fetch(query: str, *args) -> list[dict]:
    """Ejecuta SELECT que retorna múltiples filas."""
    conn = await get_pool().acquire()
    try:
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]
    finally:
        await get_pool().release(conn)

async def fetchone(query: str, *args) -> dict | None:
    """Ejecuta SELECT que retorna una fila (o None)."""
    conn = await get_pool().acquire()
    try:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None
    finally:
        await get_pool().release(conn)

async def fetchval(query: str, *args) -> any:
    """Ejecuta SELECT que retorna un valor escalar."""
    conn = await get_pool().acquire()
    try:
        return await conn.fetchval(query, *args)
    finally:
        await get_pool().release(conn)
```

---

## 2. `utils/serializers.py` — Conversión de tipos DB a JSON

```python
"""Serialización de tipos asyncpg a JSON-compatible."""
from datetime import datetime, date
from uuid import UUID
import json

def serialize_db_record(record: dict | None) -> dict:
    """Convierte tipos asyncpg a JSON-serializable.
    
    Conversiones:
    - uuid.UUID → str
    - datetime.datetime → ISO string
    - datetime.date → ISO string (YYYY-MM-DD)
    - list/dict (JSONB) → recursar
    - None → None
    """
    if not record:
        return {}
    
    result = dict(record)
    
    # UUID fields → strings
    uuid_fields = {"id", "user_id", "employee_id", "project_id", "area_id", 
                   "team_id", "manager_id", "gerente_id", "creado_por", "actualizado_por"}
    for field in uuid_fields:
        if field in result and result[field]:
            if isinstance(result[field], UUID):
                result[field] = str(result[field])
    
    # datetime fields → ISO strings
    datetime_fields = {"created_at", "updated_at", "creado_en", "actualizado_en",
                       "completed_at", "completada_en", "login_at", "deleted_at"}
    for field in datetime_fields:
        if field in result and result[field]:
            if isinstance(result[field], datetime):
                result[field] = result[field].isoformat()
    
    # date fields → YYYY-MM-DD strings
    date_fields = {"fecha_inicio", "fecha_fin", "date_of_birth", "fecha_nacimiento"}
    for field in date_fields:
        if field in result and result[field]:
            if isinstance(result[field], date) and not isinstance(result[field], datetime):
                result[field] = result[field].isoformat()
    
    # JSONB fields — ensure dict/list, not string
    jsonb_fields = {"metadata", "config", "options", "parametros", "outline"}
    for field in jsonb_fields:
        if field in result and isinstance(result[field], str):
            try:
                result[field] = json.loads(result[field])
            except json.JSONDecodeError:
                pass  # Si no es JSON válido, dejar como está
    
    return result

def safe_to_string(value) -> str:
    """Convierte cualquier tipo a string seguro (recursivo para dicts/lists)."""
    if isinstance(value, str):
        return value
    elif isinstance(value, dict):
        items = []
        for k, v in value.items():
            items.append(safe_to_string(v))
        return " • ".join(i for i in items if i)
    elif isinstance(value, list):
        items = []
        for item in value:
            items.append(safe_to_string(item))
        return "\n".join(i for i in items if i)
    elif isinstance(value, (datetime, date)):
        return value.isoformat()
    elif isinstance(value, UUID):
        return str(value)
    elif value is None:
        return ""
    else:
        return str(value)
```

---

## 3. `services/password_service.py` — Bcrypt wrapper

```python
"""Hash y verificación de passwords con bcrypt."""
import bcrypt

def hash_password(password: str) -> str:
    """Genera hash bcrypt de una contraseña.
    
    Args:
        password: Contraseña en texto plano
    
    Returns:
        Hash bcrypt (utf-8 string, listo para guardar en BD)
    """
    salt = bcrypt.gensalt(rounds=12)
    hash_bytes = bcrypt.hashpw(password.encode(), salt)
    return hash_bytes.decode()

def verify_password(password: str, password_hash: str) -> bool:
    """Verifica si una contraseña coincide con su hash.
    
    Args:
        password: Contraseña a verificar (texto plano)
        password_hash: Hash almacenado en BD
    
    Returns:
        True si coincide, False si no
    """
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except (ValueError, TypeError):
        return False
```

---

## 4. `services/token_service.py` — JWT con HS256

```python
"""Creación y verificación de JWT (HS256 local, sin Supabase)."""
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from config.settings import settings
from utils.errors import AppError

ALGORITHM = "HS256"

def create_access_token(user_id: str, rol: str, expires_minutes: int = 60) -> str:
    """Genera JWT access token.
    
    Args:
        user_id: ID del usuario (como string)
        rol: Rol del usuario (admin_rrhh, management, etc)
        expires_minutes: Expiración en minutos
    
    Returns:
        Token JWT
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)
    
    payload = {
        "sub": str(user_id),  # IMPORTANTE: str, no UUID object
        "rol": rol,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access"
    }
    
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)

def create_refresh_token(user_id: str, expires_days: int = 30) -> str:
    """Genera JWT refresh token (30 días).
    
    Se almacena hasheado en BD refresh_tokens table.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=expires_days)
    
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "refresh"
    }
    
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)

def verify_token(token: str) -> dict:
    """Verifica JWT y retorna payload.
    
    Raises:
        AppError si token es inválido/expirado
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise AppError("Token expirado", "TOKEN_EXPIRED", 401)
    except jwt.InvalidTokenError:
        raise AppError("Token inválido", "INVALID_TOKEN", 401)
```

---

## 5. `services/auth_service.py` — Login/logout/refresh

```python
"""Servicio de autenticación con RDS + JWT local."""
from integrations.postgres_client import fetchone, execute
from services.password_service import hash_password, verify_password
from services.token_service import create_access_token, create_refresh_token, verify_token
from utils.errors import AppError
import bcrypt

async def login(username: str, password: str) -> dict:
    """Login: verifica credenciales, retorna tokens.
    
    Returns:
        {
            "access_token": "...",
            "refresh_token": "...",
            "user": {...}
        }
    """
    # Buscar usuario en BD
    user = await fetchone(
        "SELECT id, username, email, password_hash, rol FROM users WHERE LOWER(username) = LOWER($1)",
        username
    )
    
    if not user:
        raise AppError("Credenciales incorrectas", "INVALID_CREDENTIALS", 401)
    
    # Verificar contraseña
    if not verify_password(password, user["password_hash"]):
        raise AppError("Credenciales incorrectas", "INVALID_CREDENTIALS", 401)
    
    # Generar tokens
    access_token = create_access_token(str(user["id"]), user["rol"])
    refresh_token = create_refresh_token(str(user["id"]))
    
    # Guardar refresh token hasheado en BD
    refresh_hash = bcrypt.hashpw(refresh_token.encode(), bcrypt.gensalt()).decode()
    await execute(
        """INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
           VALUES ($1, $2, NOW() + INTERVAL '30 days')""",
        user["id"], refresh_hash
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": str(user["id"]),
            "username": user["username"],
            "email": user["email"],
            "rol": user["rol"]
        }
    }

async def refresh_token_flow(refresh_token: str) -> dict:
    """Refresh: valida refresh token, emite nuevo access token."""
    # Verificar firma del refresh token
    payload = verify_token(refresh_token)
    if payload.get("type") != "refresh":
        raise AppError("Token inválido", "INVALID_TOKEN", 401)
    
    user_id = payload["sub"]
    
    # Buscar en BD si está registrado (y no ha sido usado 2x)
    token_record = await fetchone(
        "SELECT token_hash FROM refresh_tokens WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1",
        user_id
    )
    
    if not token_record or not bcrypt.checkpw(refresh_token.encode(), token_record["token_hash"].encode()):
        raise AppError("Refresh token inválido", "INVALID_REFRESH_TOKEN", 401)
    
    # Borrar el viejo (one-time use)
    await execute("DELETE FROM refresh_tokens WHERE user_id = $1", user_id)
    
    # Traer usuario para obtener rol actual
    user = await fetchone("SELECT id, rol FROM users WHERE id = $1", user_id)
    
    # Emitir nuevo access + refresh
    access_token = create_access_token(user_id, user["rol"])
    new_refresh = create_refresh_token(user_id)
    
    # Guardar nuevo refresh hasheado
    refresh_hash = bcrypt.hashpw(new_refresh.encode(), bcrypt.gensalt()).decode()
    await execute(
        "INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES ($1, $2, NOW() + INTERVAL '30 days')",
        user_id, refresh_hash
    )
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh
    }

async def logout(user_id: str) -> None:
    """Logout: revoca todos los refresh tokens del usuario."""
    await execute("DELETE FROM refresh_tokens WHERE user_id = $1", user_id)
```

---

## 6. `routers/auth.py` — FastAPI router

```python
"""Endpoints de autenticación."""
from fastapi import APIRouter, Depends, Request
from schemas.auth import LoginRequest, LoginResponse, RefreshRequest
from services.auth_service import login, refresh_token_flow, logout
from utils.errors import AppError

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=LoginResponse)
async def login_endpoint(body: LoginRequest):
    """POST /api/auth/login — Autentica usuario."""
    return await login(body.username, body.password)

@router.post("/refresh")
async def refresh_endpoint(body: RefreshRequest):
    """POST /api/auth/refresh — Emite nuevo access token."""
    return await refresh_token_flow(body.refresh_token)

@router.post("/logout", status_code=204)
async def logout_endpoint(request: Request):
    """POST /api/auth/logout — Revoca refresh tokens."""
    user_id = request.state.user.get("id")
    if not user_id:
        raise AppError("No autenticado", "UNAUTHORIZED", 401)
    await logout(user_id)
```

---

## 7. `config/settings.py` — Configuración centralizada

```python
"""Configuración de la app (desde AWS SSM, no .env)."""
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Configuración principal (TODO DE SSM, NUNCA .env en PROD)."""
    
    # Database (RDS)
    database_url: str  # postgresql://user:pass@host:5432/db
    
    # JWT
    jwt_secret: str  # Mínimo 32 chars, random
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    refresh_token_expiration_days: int = 30
    
    # AWS
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""  # Opcional si usa IAM role
    aws_secret_access_key: str = ""  # Opcional si usa IAM role
    
    # S3
    s3_bucket_pptx: str
    s3_bucket_docx: str
    s3_bucket_avatars: str
    
    # Integraciones
    anthropic_api_key: str
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    
    # Ambiente
    environment: str = "development"  # development, testing, production
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_testing(self) -> bool:
        return self.environment in ("testing", "test")
    
    class Config:
        env_file = ".env"  # Solo si existe (para dev local)
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """Retorna settings singleton."""
    return Settings()

# Global instance (usar como `from config.settings import settings`)
settings = get_settings()
```

---

## 8. `main.py` — Inicialización FastAPI

```python
"""Entrada principal de la app."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from integrations.postgres_client import init_pool, close_pool
from config.settings import settings
from routers import auth, usuarios, proyectos  # Agregar tus routers
import logging

app = FastAPI(title="My App", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Startup/shutdown
@app.on_event("startup")
async def startup():
    """Inicializa pool de conexiones."""
    logger.info("Inicializando pool PostgreSQL...")
    await init_pool()
    logger.info("Pool inicializado")

@app.on_event("shutdown")
async def shutdown():
    """Cierra pool de conexiones."""
    logger.info("Cerrando pool...")
    await close_pool()
    logger.info("Pool cerrado")

# Health check
@app.get("/health")
async def health():
    return {"status": "ok"}

# Routers
app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(proyectos.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 9. `terraform/main.tf` — ECS + RDS + S3 (Mínimo)

```hcl
# Backend + Frontend en ECS
module "rrhh_karstec" {
  source = "./modules/ecs-app-stack"
  
  app_name      = "my-app"
  environment   = var.environment
  region        = var.region
  
  # Backend
  backend_repository_name = aws_ecr_repository.backend.name
  backend_image_tag       = "latest"
  backend_port           = 8000
  
  # Frontend  
  frontend_repository_name = aws_ecr_repository.frontend.name
  frontend_image_tag       = "latest"
  frontend_port           = 3000
  
  # Database
  database_url = "postgresql://${var.db_user}:${data.aws_ssm_parameter.db_password.value}@${var.db_host}:5432/${var.db_name}"
  
  # Environment variables (NO secrets aquí)
  environment_variables = {
    JWT_SECRET            = data.aws_ssm_parameter.jwt_secret.value
    ANTHROPIC_API_KEY     = data.aws_ssm_parameter.anthropic_key.value
    S3_BUCKET_PPTX        = aws_s3_bucket.pptx.id
  }
}
```

---

## 10. `.gitlab-ci.yml` — Minimal pipeline

```yaml
stages:
  - docker
  - plan
  - apply
  - cleanup

variables:
  ACCOUNT_NUMBER: "YOUR_AWS_ACCOUNT"
  REGION: "us-east-1"

# Docker build
docker:desa:
  stage: docker
  script:
    - docker build -t app:latest -f backend/Dockerfile backend/
    - docker tag app:latest $ACCOUNT_NUMBER.dkr.ecr.$REGION.amazonaws.com/my-app-backend:latest
    - docker push $ACCOUNT_NUMBER.dkr.ecr.$REGION.amazonaws.com/my-app-backend:latest
  when: manual

# Terraform plan
plan:desa:
  stage: plan
  script:
    - cd terraform
    - terraform init -backend-config="desa.backend.tfvars"
    - terraform plan -var-file="desa.tfvars" -out=tfplan
  when: manual

# Terraform apply
apply:desa:
  stage: apply
  script:
    - cd terraform
    - terraform init -backend-config="desa.backend.tfvars"
    - terraform apply -auto-approve tfplan
  when: manual
```

---

**Uso:** Copy-paste estas bases y adaptá a tu proyecto. Toda esta código fue extraída de proyectos en producción.


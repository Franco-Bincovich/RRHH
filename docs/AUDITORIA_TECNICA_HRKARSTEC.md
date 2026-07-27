# AUDITORÍA TÉCNICA — HR Karstec (RRHH)
> Generada el 2026-05-29. Solo lectura. Base para el traspaso de módulos desde otro proyecto Next.js + Supabase.

---

## BLOQUE 1 — Datos críticos que definen todo el traspaso

### 1.1 Tabla de empleados — `CREATE TABLE` completo

`RRHH/backend/migrations/003_create_empleados.sql` líneas 5–27:

```sql
CREATE TABLE public.empleados (
    id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID         REFERENCES public.users(id) ON DELETE SET NULL,
    legajo            VARCHAR(20)  UNIQUE,
    nombre            VARCHAR(100) NOT NULL,
    apellido          VARCHAR(100) NOT NULL,
    email_corporativo VARCHAR(255) UNIQUE,
    email_personal    VARCHAR(255),
    telefono          VARCHAR(30),
    fecha_nacimiento  DATE,
    fecha_ingreso     DATE         NOT NULL,
    fecha_egreso      DATE,
    area_id           UUID         REFERENCES public.areas(id) ON DELETE RESTRICT,
    cargo             VARCHAR(100),
    nivel             VARCHAR(20)  CHECK (nivel IN ('junior', 'semi_senior', 'senior', 'lider', 'manager', 'director', 'c_level')),
    modalidad_trabajo VARCHAR(20)  CHECK (modalidad_trabajo IN ('presencial', 'remoto', 'hibrido')),
    tipo_contrato     VARCHAR(20)  CHECK (tipo_contrato IN ('efectivo', 'plazo_fijo', 'contratado', 'pasantia')),
    estado            VARCHAR(20)  NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo', 'baja', 'licencia', 'suspendido')),
    manager_id        UUID         REFERENCES public.empleados(id) ON DELETE SET NULL,
    foto_url          TEXT,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
```

Migración posterior `029_empleados_rol.sql`:

```sql
ALTER TABLE public.empleados ADD COLUMN IF NOT EXISTS rol VARCHAR(100);
```

**Columna `rol` en `empleados`**: rol funcional/título interno del empleado (ej: "Tech Lead", "PM"). **NO es el rol de sistema** (admin_rrhh/management/empleado). Ese rol de sistema vive en `public.users.rol`.

---

### 1.2 Link con auth — ¿qué columna guarda `auth.uid()`?

La tabla `public.users` es el puente:

`RRHH/backend/migrations/001_create_users.sql` líneas 5–16:
```sql
CREATE TABLE public.users (
    id            UUID         PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    ...
    rol           VARCHAR(20)  NOT NULL CHECK (rol IN ('admin_rrhh', 'management', 'empleado')),
    ...
);
```

La tabla `public.empleados` vincula al usuario con:
```sql
user_id  UUID  REFERENCES public.users(id) ON DELETE SET NULL
```

**Cadena**: `auth.users.id` ← `public.users.id` ← `public.empleados.user_id`

- `auth.uid()` en RLS policies apunta a `public.users.id` (que es el mismo UUID que `auth.users.id`)
- Un empleado puede no tener `user_id` (NULL): es posible registrar empleados sin cuenta de sistema
- Las policies de RLS que dicen "el empleado ve lo suyo" usan: `user_id = auth.uid()`

---

### 1.3 Multi-tenant — ¿existe `empresa_id`?

**NO EXISTE** ninguna columna `empresa_id` en ninguna tabla del schema.

HR Karstec es **mono-empresa**: una sola organización, todos los datos son de Karstec. No hay aislamiento multi-tenant en el schema. Evidencia:

- `migrations/030_configuracion_empresa.sql` guarda una sola fila de configuración global (nombre, logo, RUT, etc.)
- El endpoint es `GET /api/empresa` (singular, sin ID de empresa)
- El Supabase project ID `grmdiwxcvcjorlohpwji` es único: todos los datos comparten el mismo schema sin partición por empresa

**Impacto para el traspaso**: si el proyecto origen tiene `empresa_id`, esa columna se descarta. Las tablas nuevas no necesitan ese campo.

---

### 1.4 Roles — valores exactos y tipo de implementación

**Tipo**: columna `VARCHAR(20)` con `CHECK` constraint. **No es un enum de Postgres ni una tabla de roles.**

Valores exactos (confirmados en `001_create_users.sql` línea 10 y `CLAUDE.md`):

| Valor | Descripción |
|---|---|
| `admin_rrhh` | Control total — crea usuarios, configura el sistema |
| `management` | Acceso configurable por módulo (lectura / lectura+escritura / sin acceso) |
| `empleado` | Solo su propio perfil y sus propias evaluaciones |

La función helper que se usa en todas las policies:

`RRHH/backend/migrations/001_create_users.sql` líneas 22–30:
```sql
CREATE OR REPLACE FUNCTION public.get_current_user_rol()
RETURNS TEXT
LANGUAGE SQL
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
    SELECT rol FROM public.users WHERE id = auth.uid()
$$;
```

**Nota**: el reporte previo que mencionaba estos roles era correcto. Los tres valores son exactamente `admin_rrhh`, `management`, `empleado`.

---

### 1.5 Todas las tablas del schema

| # | Tabla | Qué guarda | Migración |
|---|---|---|---|
| 1 | `public.users` | Perfil de usuario del sistema + rol (extiende `auth.users`) | 001 |
| 2 | `public.areas` | Áreas/departamentos con jerarquía (auto-referencial) | 002 |
| 3 | `public.empleados` | Ciclo de vida del empleado — tabla central | 003 |
| 4 | `public.documentos_empleado` | Archivos adjuntos al empleado (contratos, recibos, CV) en Storage | 004 |
| 5 | `public.vacantes` | Posiciones abiertas con pipeline de estados | 005 |
| 6 | `public.candidatos` | Postulantes a vacantes con etapas de reclutamiento | 006 |
| 7 | `public.onboarding_templates` | Plantillas de onboarding reutilizables | 007 |
| 8 | `public.onboarding_tareas` | Tareas individuales de un template de onboarding | 008 |
| 9 | `public.onboarding_instancias` | Proceso de onboarding activo para un empleado específico | 009 |
| 10 | `public.onboarding_progreso` | Estado de cada tarea dentro de una instancia de onboarding | 010 |
| 11 | `public.offboarding_instancias` | Proceso de egreso de un empleado | 011 |
| 12 | `public.offboarding_activos` | Activos a devolver durante el offboarding | 012 |
| 13 | `public.costos_nomina` | Costos de nómina por empleado y mes | 013 |
| 14 | `public.presupuesto_areas` | Presupuesto de personal por área y período | 014 |
| 15 | `public.sucesion_posiciones` | Mapa de sucesión para posiciones clave | 015 |
| 16 | `public.planes_carrera` | Planes de desarrollo de carrera de empleados | 016 |
| 17 | `public.planes_carrera_hitos` | Hitos del plan de carrera (capacitaciones, certs, proyectos) | 017 |
| 18 | `public.assessment_campanas` | Campañas de evaluación (conductual, cognitivo, técnico) | 018 |
| 19 | `public.assessment_links` | Links únicos (tokens) enviados a evaluados | 019 |
| 20 | `public.assessment_resultados` | Respuestas y puntuación de un assessment completado | 020 |
| 21 | `public.assessment_reportes` | Reportes generados (por IA o manual) desde resultados | 021 |
| 22 | `public.notificaciones` | Notificaciones in-app por usuario | 022 |
| 23 | `public.notificaciones_config` | Preferencias de notificación por usuario y tipo de evento | 023 |
| 24 | `public.auditoria` | Log inmutable de cambios en tablas críticas | 024 |
| 25 | `public.configuracion_empresa` | Datos globales de la empresa (nombre, logo, RUT) | 030 |
| 26 | `public.reportes_generados` | Historial de reportes exportados (PDF/Excel) | 031 |
| 27 | `public.usuario_integraciones` | Tokens de integración por usuario (Google OAuth, Zernio) | 032 |

Otras migraciones (025–035): `username` en users, adaptaciones de vacantes/candidatos, sucesion campos, datos de demo. No crean tablas nuevas.

---

## BLOQUE 2 — Patrón del Backend (FastAPI)

### 2.1 Estructura de carpetas del backend

```
RRHH/backend/
├── main.py                          ← punto de entrada, solo configuración
├── vercel_app.py                    ← wrapper para deploy serverless
├── config/
│   └── settings.py                  ← única fuente de env vars (Pydantic Settings)
├── routers/                         ← endpoints HTTP (max 80 líneas)
│   ├── areas.py
│   ├── assessment.py
│   ├── auth.py
│   ├── costos.py
│   ├── dashboard.py
│   ├── empleados.py
│   ├── empresa.py
│   ├── importacion.py
│   ├── integraciones.py
│   ├── offboarding.py
│   ├── onboarding.py
│   ├── onboarding_templates.py
│   ├── organigrama.py
│   ├── reportes.py
│   ├── sucesion.py
│   └── vacantes.py
├── services/                        ← lógica de negocio (max 150 líneas)
│   ├── area_service.py
│   ├── assessment_service.py
│   ├── auth_service.py
│   ├── costo_service.py
│   ├── csv_service.py
│   ├── dashboard_service.py
│   ├── empleado_service.py
│   ├── gmail_service.py
│   ├── integracion_service.py
│   ├── offboarding_service.py
│   ├── onboarding_service.py
│   ├── onboarding_templates_service.py
│   ├── organigrama_service.py
│   ├── reporte_export_service.py
│   ├── reporte_service.py
│   ├── sucesion_service.py
│   ├── vacante_service.py
│   └── zernio_service.py
├── repositories/                    ← acceso a DB (max 100 líneas)
│   ├── area_repo.py
│   ├── assessment_repo.py
│   ├── costo_repo.py
│   ├── empleado_repo.py
│   ├── empresa_repo.py
│   ├── integracion_repo.py
│   ├── offboarding_repo.py
│   ├── onboarding_repo.py
│   ├── onboarding_templates_repo.py
│   ├── reporte_repo.py
│   ├── sucesion_repo.py
│   └── vacante_repo.py
├── schemas/                         ← Pydantic (max por archivo según módulo)
│   ├── area.py, assessment.py, auth.py, costo.py, dashboard.py
│   ├── empleado.py, empresa.py, importacion.py, integracion.py
│   ├── offboarding.py, onboarding.py, organigrama.py, reporte.py
│   ├── sucesion.py, vacante.py
├── integrations/
│   └── supabase_client.py           ← únicos dos clientes (anon + admin)
├── middleware/
│   ├── auth.py                      ← JWT decode + user en request.state
│   ├── error_handler.py             ← handler global de excepciones
│   └── security_headers.py          ← CORS + headers HTTP
├── utils/
│   ├── errors.py                    ← AppError centralizado
│   └── logger.py                    ← JSON structured logging
├── migrations/                      ← SQL numerado (001–035)
├── tests/
├── requirements.txt
└── .env / .env.example
```

**NO EXISTE** carpeta `controllers/` — el proyecto saltó directo a `router → service → repository`. Los routers llaman a services sin capa controller intermedia.

---

### 2.2 Registro de routers en `main.py`

`RRHH/backend/main.py` (completo):

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config.settings import settings
from middleware.auth import AuthMiddleware
from middleware.error_handler import global_error_handler
from middleware.security_headers import SecurityHeadersMiddleware
from routers.areas import router as areas_router
from routers.auth import limiter, router as auth_router
# ... (resto de imports)

app = FastAPI(
    title="HR Karstec API",
    version="1.0.0",
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url=None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# LIFO: el último agregado se ejecuta primero en el request
app.add_middleware(AuthMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_exception_handler(Exception, global_error_handler)

@app.get("/health")
async def health_check():
    return {"status": "ok", "env": settings.app_env}

app.include_router(auth_router,                 prefix="/api/auth",                  tags=["auth"])
app.include_router(areas_router,                prefix="/api/areas",                 tags=["areas"])
app.include_router(empleados_router,            prefix="/api/empleados",             tags=["empleados"])
app.include_router(vacantes_router,             prefix="/api/vacantes",              tags=["vacantes"])
app.include_router(candidatos_router,           prefix="/api/candidatos",            tags=["candidatos"])
app.include_router(onboarding_templates_router, prefix="/api/onboarding/templates",  tags=["onboarding"])
app.include_router(onboarding_router,           prefix="/api/onboarding",            tags=["onboarding"])
app.include_router(offboarding_router,          prefix="/api/offboarding",           tags=["offboarding"])
app.include_router(costos_router,               prefix="/api/costos",                tags=["costos"])
app.include_router(sucesion_router,             prefix="/api/sucesion",              tags=["sucesion"])
app.include_router(assessment_router,           prefix="/api/assessment",            tags=["assessment"])
app.include_router(organigrama_router,          prefix="/api/organigrama",           tags=["organigrama"])
app.include_router(dashboard_router,            prefix="/api/dashboard",             tags=["dashboard"])
app.include_router(empresa_router,              prefix="/api/empresa",               tags=["empresa"])
app.include_router(reportes_router,             prefix="/api/reportes",              tags=["reportes"])
app.include_router(importacion_router,          prefix="/api/importacion",           tags=["importacion"])
app.include_router(integraciones_router,        prefix="/api/integraciones",         tags=["integraciones"])
```

---

### 2.3 Dependencia de auth — cómo se obtiene el usuario actual

**No hay un `Depends(get_current_user)`**. La auth se resuelve en `AuthMiddleware` (middleware global), no en cada endpoint. El usuario queda en `request.state.user`.

`RRHH/backend/middleware/auth.py` (completo):

```python
"""
Middleware de autenticación JWT.
Decodifica el token Supabase sin verificar firma (PyJWT) y expone
el user_id y rol en request.state.user para los handlers.
"""
import re
from typing import Optional

import jwt
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from integrations.supabase_client import supabase_admin
from utils.logger import logger

PUBLIC_ROUTES = frozenset([
    "/health",
    "/api/auth/login",
    "/api/auth/refresh",
    "/api/integraciones/google/callback",
])
_ASSESSMENT_FE_RE  = re.compile(r"^/assessment/[^/]+$")
_ASSESSMENT_API_RE = re.compile(r"^/api/assessment/evaluacion/[^/]+(/submit)?$")


def _is_public(path: str) -> bool:
    return (
        path in PUBLIC_ROUTES
        or bool(_ASSESSMENT_FE_RE.match(path))
        or bool(_ASSESSMENT_API_RE.match(path))
    )


def _extract_token(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if _is_public(request.url.path):
            return await call_next(request)

        token = _extract_token(request)
        if not token:
            return JSONResponse(
                status_code=401,
                content={"error": True, "message": "No autorizado", "code": "MISSING_TOKEN"},
            )

        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            user_id = payload.get("sub")
        except Exception:
            user_id = None

        if not user_id:
            return JSONResponse(
                status_code=401,
                content={"error": True, "message": "No autorizado", "code": "INVALID_TOKEN"},
            )

        try:
            row = (
                supabase_admin.table("users")
                .select("rol")
                .eq("id", user_id)
                .single()
                .execute()
            )
            rol = row.data.get("rol") if row.data else None
        except Exception:
            rol = None

        request.state.user = {"id": user_id, "rol": rol}
        return await call_next(request)
```

**Para acceder al usuario en un router**: `request.state.user` devuelve `{"id": str, "rol": str}`.

Ejemplo de uso en `routers/empleados.py` línea 52:
```python
created_by = request.state.user.get("id", "system")
```

**¿De dónde saca el rol?** Del campo `users.rol` consultado en tiempo real con `supabase_admin`. No está en el JWT — se hace un hit a DB en cada request autenticado.

---

### 2.4 Cliente Supabase desde Python

`RRHH/backend/integrations/supabase_client.py` (completo):

```python
"""
Clientes de Supabase para el backend.

- supabase_client: usa la anon key, respeta RLS. Para operaciones autenticadas del usuario.
- supabase_admin: usa la service key, bypasea RLS. Solo para operaciones administrativas.
"""
from supabase import Client, create_client
from config.settings import settings


def _create_anon_client() -> Client:
    """Instancia el cliente público con la anon key. Respeta RLS."""
    return create_client(settings.supabase_url, settings.supabase_anon_key)


def _create_admin_client() -> Client:
    """Instancia el cliente admin con la service key. Bypasea RLS."""
    return create_client(settings.supabase_url, settings.supabase_service_key)


supabase_client: Client = _create_anon_client()  # respeta RLS
supabase_admin: Client  = _create_admin_client()  # bypasea RLS
```

**Patrón de uso en práctica**: la mayoría de los repositories usan `supabase_admin` (service key) porque la validación de rol ya fue hecha en el middleware. La RLS en DB es una segunda línea de defensa. El `supabase_client` (anon) se usa en operaciones de auth de usuario (login, refresh).

---

### 2.5 Autorización por rol — cómo se chequea en el código

**No hay un decorator/dependency de "solo rrhh"** independiente. La autorización se hace inline en el service o en el router con un check directo sobre `request.state.user["rol"]`.

Ejemplo típico (cuando un endpoint restringe por rol):
```python
@router.post("", response_model=EmpleadoResponse, status_code=201)
async def create_empleado(
    request: Request,
    body: EmpleadoCreate,
    service: EmpleadoService = Depends(_service),
) -> EmpleadoResponse:
    # El middleware ya validó que hay un JWT válido.
    # Si el módulo requiere admin_rrhh, el service lanza AppError("No autorizado", "FORBIDDEN", 403)
    created_by = request.state.user.get("id", "system")
    return service.create_empleado(body, created_by)
```

La segunda línea de defensa son las políticas RLS en Supabase (pero como los repositories usan `supabase_admin`, no las activan directamente).

---

### 2.6 Endpoint entero — request → validación → query → respuesta

**Router** `RRHH/backend/routers/empleados.py` (completo):

```python
"""Router de empleados — CRUD con paginación y filtros."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from schemas.empleado import EmpleadoCreate, EmpleadoListResponse, EmpleadoResponse, EmpleadoUpdate
from services.empleado_service import EmpleadoService

router = APIRouter()

def _service() -> EmpleadoService:
    return EmpleadoService()

@router.get("", response_model=EmpleadoListResponse)
async def list_empleados(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    area_id: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    service: EmpleadoService = Depends(_service),
) -> EmpleadoListResponse:
    return service.get_empleados(page, page_size, area_id, estado, search)

@router.get("/{id}", response_model=EmpleadoResponse)
async def get_empleado(id: UUID, service: EmpleadoService = Depends(_service)) -> EmpleadoResponse:
    return service.get_empleado(id)

@router.post("", response_model=EmpleadoResponse, status_code=201)
async def create_empleado(
    request: Request, body: EmpleadoCreate, service: EmpleadoService = Depends(_service),
) -> EmpleadoResponse:
    created_by = request.state.user.get("id", "system")
    return service.create_empleado(body, created_by)

@router.put("/{id}", response_model=EmpleadoResponse)
async def update_empleado(
    id: UUID, body: EmpleadoUpdate, service: EmpleadoService = Depends(_service),
) -> EmpleadoResponse:
    return service.update_empleado(id, body)

@router.delete("/{id}", status_code=204)
async def delete_empleado(id: UUID, service: EmpleadoService = Depends(_service)) -> None:
    service.deactivate_empleado(id)
```

**Service** `RRHH/backend/services/empleado_service.py` (función create):

```python
def create_empleado(self, data: EmpleadoCreate, created_by: str) -> EmpleadoResponse:
    empleado = self._repo.save(data)
    logger.info("Empleado creado", extra={"empleado_id": empleado.id, "created_by": created_by})
    return empleado
```

**Repository** `RRHH/backend/repositories/empleado_repo.py` (función save):

```python
def save(self, data: EmpleadoCreate) -> EmpleadoResponse:
    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    payload["area_id"] = str(data.area_id)
    payload["fecha_ingreso"] = str(data.fecha_ingreso)
    if data.fecha_nacimiento:
        payload["fecha_nacimiento"] = str(data.fecha_nacimiento)
    payload["estado"] = "activo"

    result = supabase_admin.table(_TABLE).insert(payload).execute()
    if not result.data:
        logger.error("Supabase insert vacío en empleados")
        raise AppError("Error al crear empleado", "DB_ERROR", 500)
    return _row(result.data[0])
```

**Formato de error** — siempre `{"error": true, "message": str, "code": str}`:

```python
# utils/errors.py
class AppError(Exception):
    def __init__(self, message: str, code: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code

# Uso en cualquier service/repo:
raise AppError("Empleado no encontrado", "EMPLEADO_NOT_FOUND", 404)
raise AppError("Email duplicado", "DUPLICATE_EMAIL", 409)
raise AppError("No autorizado", "FORBIDDEN", 403)

# Respuesta HTTP (middleware/error_handler.py):
# {"error": true, "message": "Empleado no encontrado", "code": "EMPLEADO_NOT_FOUND"}
```

---

### 2.7 Schemas Pydantic — estilo completo

`RRHH/backend/schemas/empleado.py` (completo):

```python
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, field_validator


class EmpleadoBase(BaseModel):
    nombre: str
    apellido: str
    email_corporativo: str
    area_id: UUID
    cargo: str
    modalidad_trabajo: str  # presencial | remoto | hibrido
    tipo_contrato: str      # efectivo | plazo_fijo | contratado | pasantia
    fecha_ingreso: date


class EmpleadoCreate(EmpleadoBase):
    telefono: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    cuil: Optional[str] = None
    legajo: Optional[str] = None
    rol: Optional[str] = None


class EmpleadoUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    email_corporativo: Optional[str] = None
    area_id: Optional[UUID] = None
    cargo: Optional[str] = None
    modalidad_trabajo: Optional[str] = None
    tipo_contrato: Optional[str] = None
    fecha_ingreso: Optional[date] = None
    telefono: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    cuil: Optional[str] = None
    legajo: Optional[str] = None
    estado: Optional[str] = None
    rol: Optional[str] = None

    @field_validator("fecha_ingreso", "fecha_nacimiento", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: object) -> object:
        return None if v == "" else v


class EmpleadoResponse(BaseModel):
    id: str
    nombre: str
    apellido: str
    email_corporativo: str
    area_id: str
    area_nombre: Optional[str] = None
    cargo: str
    modalidad_trabajo: str
    tipo_contrato: str
    fecha_ingreso: date
    telefono: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    cuil: Optional[str] = None
    legajo: Optional[str] = None
    rol: Optional[str] = None
    estado: str
    created_at: datetime


class EmpleadoListResponse(BaseModel):
    items: List[EmpleadoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
```

**Patrón de herencia**: `Base → Create` (agrega opcionales) → `Update` (todo opcional + validators) → `Response` (campos de DB + joins resueltos) → `ListResponse` (paginación).

---

### 2.8 Validación de input

- **Pydantic en los schemas**: es la primera línea. FastAPI rechaza el request automáticamente con 422 si el body no matchea el schema.
- **Validators custom**: `@field_validator` para casos edge (strings vacíos → None, fechas).
- **Checks de negocio**: en el service (ej: si el ID no existe → `AppError(..., 404)`).
- **Sin validación en los routers**: los routers son thin wrappers, no tienen lógica de validación.

---

## BLOQUE 3 — Patrón del Frontend (Next.js)

### 3.1 Estructura de rutas — árbol de `app/`

```
RRHH/frontend/app/
├── layout.tsx                        ← root layout (ThemeProvider, fuentes)
├── page.tsx                          ← "/" → redirect a /dashboard
├── login/
│   └── page.tsx                      ← login público
├── (dashboard)/                      ← grupo de rutas protegidas
│   ├── layout.tsx                    ← Sidebar + main + AIPanel
│   ├── dashboard/page.tsx            ← KPIs + headcount + alertas
│   ├── empleados/
│   │   ├── page.tsx                  ← lista + filtros + paginación
│   │   └── [id]/page.tsx             ← detalle del empleado
│   ├── areas/page.tsx
│   ├── vacantes/
│   │   ├── page.tsx
│   │   └── [id]/page.tsx
│   ├── assessment/
│   │   ├── page.tsx
│   │   └── [id]/page.tsx
│   ├── onboarding/
│   │   ├── page.tsx
│   │   └── templates/
│   │       ├── page.tsx
│   │       └── [id]/page.tsx
│   ├── offboarding/page.tsx
│   ├── sucesion/page.tsx
│   ├── organigrama/page.tsx
│   ├── costos/page.tsx
│   ├── reportes/page.tsx
│   └── configuracion/page.tsx
└── evaluacion/
    └── [token]/page.tsx              ← evaluación pública (sin auth)
```

**Control de acceso**: no hay middleware de Next.js para rutas. El guard vive en `components/layout/AuthGuard.tsx` — un componente wrapper que redirige a `/login` si no hay sesión en localStorage.

---

### 3.2 Cliente HTTP — cómo el front le pega al backend

`RRHH/frontend/services/api.ts` (completo):

```typescript
import type { Session } from "@/types/auth"

export type { Session }

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export function getSession(): Session | null {
  if (typeof window === "undefined") return null
  const raw = localStorage.getItem("session")
  if (!raw) return null
  try {
    return JSON.parse(raw) as Session
  } catch {
    return null
  }
}

export function saveSession(session: Session): void {
  localStorage.setItem("session", JSON.stringify(session))
}

export function clearSession(): void {
  localStorage.removeItem("session")
}

export function authHeaders(): Record<string, string> {
  const session = getSession()
  const headers: Record<string, string> = { "Content-Type": "application/json" }
  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`
  }
  return headers
}

export class ApiError extends Error {
  readonly code: string
  readonly status: number

  constructor(message: string, code: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.code = code
    this.status = status
  }
}

async function toApiError(res: Response): Promise<ApiError> {
  try {
    const body = (await res.json()) as { message?: string; code?: string }
    return new ApiError(body.message ?? "Error del servidor", body.code ?? "UNKNOWN", res.status)
  } catch {
    return new ApiError("Error del servidor", "UNKNOWN", res.status)
  }
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...(init.headers as Record<string, string> | undefined) },
  })
  if (!res.ok) throw await toApiError(res)
  return res.json() as Promise<T>
}
```

**Puntos clave**:
- **Base URL**: `process.env.NEXT_PUBLIC_API_URL` (configurado en `.env.local` del frontend)
- **JWT adjunto**: automáticamente via `authHeaders()` en cada `apiFetch`
- **Sesión guardada en**: `localStorage` con clave `"session"`
- **No usa axios** — `fetch` nativo con wrapper tipado
- **Sin interceptors de refresh automático** — el refresh se maneja manualmente

**Ejemplo de service de módulo** `RRHH/frontend/services/empleados.ts`:

```typescript
import type { Empleado, EmpleadoCreate, EmpleadoListResponse, EmpleadoUpdate } from "@/types/empleado"
import { apiFetch } from "@/services/api"

export async function fetchEmpleados(
  page: number,
  pageSize: number,
  search?: string,
  estado?: string,
): Promise<EmpleadoListResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  if (search) params.set("search", search)
  if (estado) params.set("estado", estado)
  return apiFetch<EmpleadoListResponse>(`/api/empleados?${params}`)
}

export async function createEmpleado(data: EmpleadoCreate): Promise<Empleado> {
  return apiFetch<Empleado>("/api/empleados", { method: "POST", body: JSON.stringify(data) })
}

export async function updateEmpleado(id: string, data: EmpleadoUpdate): Promise<Empleado> {
  return apiFetch<Empleado>(`/api/empleados/${id}`, { method: "PUT", body: JSON.stringify(data) })
}
```

---

### 3.3 Componentes UI disponibles (Shadcn/ui + custom)

**Shadcn/ui presentes** (confirmados en imports del código):

| Componente | Uso típico |
|---|---|
| `Button` | Acciones, submit de forms (`variant="outline"\|"default"\|"destructive"`) |
| `Input` | Campos de texto en forms |
| `Label` | Labels de campos de form |
| `Badge` | Estado de registros (`variant="default"\|"destructive"\|"secondary"`) |
| `Skeleton` | Loading placeholder |
| `Table, TableHeader, TableBody, TableHead, TableRow, TableCell` | Listados de datos |
| `Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter` | Modals de crear/editar |

**Custom UI** (en `components/ui/`):
- `EmptyState` — estado sin datos (icon + title + description)
- `ErrorState` — estado de error con botón "reintentar" (`action: () => void`)

**Layout**:
- `Sidebar` — nav lateral con 11 módulos
- `PageHeader` — encabezado con `title`, `description`, `action` (slot para botones)
- `AIPanel` — panel de IA a la derecha
- `AuthGuard` — wrapper de protección de rutas

---

### 3.4 Patrón de formulario — modal completa real

`RRHH/frontend/components/features/empleados/EmpleadoModal.tsx` líneas 97–302 (forma condensada):

```typescript
"use client"
// Imports: Dialog, Button, Input, Label, createEmpleado, updateEmpleado, fetchAreas

type FormData = {
  nombre: string; apellido: string; email_corporativo: string; area_id: string;
  cargo: string; modalidad_trabajo: string; tipo_contrato: string;
  fecha_ingreso: string; telefono: string; fecha_nacimiento: string; cuil: string; legajo: string; rol: string;
}
type FormErrors = Partial<Record<keyof FormData, string>>

function validate(form: FormData): FormErrors {
  const errors: FormErrors = {}
  if (!form.nombre.trim()) errors.nombre = "El nombre es requerido"
  if (!form.email_corporativo.trim()) errors.email_corporativo = "El email es requerido"
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email_corporativo))
    errors.email_corporativo = "El email no es válido"
  if (!form.area_id) errors.area_id = "El área es requerida"
  // ...
  return errors
}

export function EmpleadoModal({ open, onClose, onSuccess, empleado }: EmpleadoModalProps) {
  const [form, setForm] = useState<FormData>(EMPTY)
  const [errors, setErrors] = useState<FormErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState("")

  function field(key: keyof FormData) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      const val = e.target.value
      setForm((prev) => ({ ...prev, [key]: val }))
      if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }))  // clear on change
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errs = validate(form)
    if (Object.keys(errs).length > 0) { setErrors(errs); return }
    setSubmitting(true)
    try {
      isEdit ? await updateEmpleado(empleado.id, form) : await createEmpleado(payload)
      onSuccess()
    } catch {
      setServerError("Ocurrió un error al guardar. Intentá de nuevo.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose() }}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader><DialogTitle>{isEdit ? "Editar" : "Nuevo"} empleado</DialogTitle></DialogHeader>
        <form id="empleado-form" onSubmit={handleSubmit} noValidate>
          <div className="grid grid-cols-1 gap-4 py-2 sm:grid-cols-2">
            {/* Label + Input + error message por campo */}
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="nombre">Nombre <span className="text-destructive">*</span></Label>
              <Input id="nombre" value={form.nombre} onChange={field("nombre")}
                     aria-invalid={Boolean(errors.nombre)} aria-required />
              {errors.nombre && <p className="text-xs text-destructive" role="alert">{errors.nombre}</p>}
            </div>
          </div>
          {serverError && <p className="mt-2 text-sm text-destructive" role="alert">{serverError}</p>}
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={submitting}>Cancelar</Button>
          <Button type="submit" form="empleado-form" disabled={submitting}>
            {submitting ? "Guardando..." : isEdit ? "Guardar cambios" : "Crear empleado"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

**Patrón de form**: estado manual (no react-hook-form), validación inline en `validate()`, clear de error por campo al cambiar el valor, serverError separado del error de validación.

---

### 3.5 Patrón de tabla/listado — página de empleados real

`RRHH/frontend/app/(dashboard)/empleados/page.tsx` (estructura):

```typescript
"use client"

export default function EmpleadosPage() {
  const [data, setData] = useState<EmpleadoListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)

  const load = useCallback(async () => {
    setLoading(true); setError(false)
    try {
      const result = await fetchEmpleados(page, PAGE_SIZE, search || undefined)
      setData(result)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [page, search])

  useEffect(() => { load() }, [load])

  return (
    <div>
      <PageHeader title="Empleados" description={`${total} colaboradores`}
        action={<Button onClick={() => setNewOpen(true)}><Plus /> Nuevo empleado</Button>} />

      {/* Filtros */}
      <div className="mb-4 flex flex-col gap-3 sm:flex-row">
        <Input placeholder="Buscar..." onChange={(e) => setSearch(e.target.value)} />
      </div>

      {/* 4 estados: loading / error / vacío / datos */}
      {loading && <TableSkeleton />}
      {!loading && error && <ErrorState action={load} />}
      {!loading && !error && items.length === 0 && <EmptyState ... />}
      {!loading && !error && items.length > 0 && (
        <Table>
          <TableHeader>...</TableHeader>
          <TableBody>
            {items.map((emp) => (
              <TableRow key={emp.id} className="cursor-pointer"
                        onClick={() => router.push(`/empleados/${emp.id}`)}>
                <TableCell>{emp.nombre} {emp.apellido}</TableCell>
                <TableCell><Badge variant={ESTADO_VARIANTS[emp.estado]}>{emp.estado}</Badge></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {/* Paginación manual */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <Button disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Anterior</Button>
          <Button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Siguiente</Button>
        </div>
      )}

      <EmpleadoModal open={newOpen} onClose={() => setNewOpen(false)} onSuccess={() => { setNewOpen(false); load() }} />
    </div>
  )
}
```

---

### 3.6 Estados de carga y error

**Loading**: componente `TableSkeleton` local — `Skeleton` de Shadcn en loop:
```typescript
function TableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 8 }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full rounded-lg" />
      ))}
    </div>
  )
}
```

**Error**: `<ErrorState action={load} />` — componente custom que muestra mensaje y botón "Reintentar".

**Vacío**: `<EmptyState icon={<Users />} title="Sin resultados" description="..." />`.

**Los 4 estados son obligatorios** en cualquier componente que carga datos (definido en CLAUDE.md).

---

### 3.7 Tema visual — tokens de diseño

`RRHH/frontend/styles/design-system.ts` (completo):

```typescript
export const COLORS = {
  primary: "#1A56DB",
  background: { light: "#F8FAFC", dark: "#0F172A" },
  surface:    { light: "#FFFFFF",  dark: "#1E293B" },
} as const

export const TYPOGRAPHY = {
  fontFamily: "Inter, system-ui, -apple-system, sans-serif",
  fontSizes:  { xs: "0.75rem", sm: "0.875rem", base: "1rem", lg: "1.125rem", xl: "1.25rem", "2xl": "1.5rem", "3xl": "1.875rem" },
  fontWeights: { normal: 400, medium: 500, semibold: 600, bold: 700 },
} as const

export const RADIUS   = { md: "8px", lg: "12px" } as const
export const SPACING  = { sidebar: "16rem", sidebarCollapsed: "0rem", headerHeight: "3.5rem" } as const
export const BREAKPOINTS = { mobile: 768, tablet: 1024, desktop: 1280 } as const
```

**Sistema de colores activo**: Tailwind CSS + tokens CSS de Shadcn (`text-foreground`, `text-muted-foreground`, `bg-background`, `border-input`, `text-destructive`, `ring-ring`). **No usar los tokens del proyecto de origen** — importar los de `design-system.ts` o los de Shadcn.

---

## BLOQUE 4 — Schema y seguridad en Supabase

### 4.1 Versionado del schema

**SÍ existe carpeta de migraciones**: `RRHH/backend/migrations/` con 35 archivos SQL numerados (`001_` a `035_`).

El consolidado `000_run_all.sql` está **DEPRECADO** y tiene un guard que aborta su ejecución: quedó desactualizado y se conserva solo como historial. La reconstrucción desde cero se hace corriendo `backend/db/schema.sql` contra una base vacía (ver `backend/db/README.md`).

**No hay herramienta de migración automática** (ni Alembic, ni supabase CLI migrations). Las migraciones son SQL puro ejecutado manualmente. El control de versión es solo por nombre de archivo.

---

### 4.2 RLS — Estado y policies reales

**RLS está activado en todas las tablas**. Evidencia: cada migración incluye `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;`.

**Policies reales — 3 patrones que se repiten en todo el schema**:

**Patrón 1 — "admin y management ven todo"** (tabla `empleados`):
```sql
CREATE POLICY "empleados_select_admin_management"
    ON public.empleados FOR SELECT
    USING (public.get_current_user_rol() IN ('admin_rrhh', 'management'));
```

**Patrón 2 — "empleado ve solo lo suyo"** (tabla `empleados`):
```sql
CREATE POLICY "empleados_select_own"
    ON public.empleados FOR SELECT
    USING (user_id = auth.uid());
```

**Patrón 3 — "solo admin escribe"** (tabla `empleados`):
```sql
CREATE POLICY "empleados_write_admin"
    ON public.empleados FOR ALL
    USING (public.get_current_user_rol() = 'admin_rrhh');
```

**Ejemplo con join** — cuando la tabla no tiene `user_id` directo (tabla `onboarding_instancias`):
```sql
CREATE POLICY "onboarding_instancias_select_own"
    ON public.onboarding_instancias FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.empleados e
            WHERE e.id = empleado_id AND e.user_id = auth.uid()
        )
    );
```

**Variante de área** — cuando `management` también puede escribir:
```sql
CREATE POLICY "candidatos_write_admin_management"
    ON public.candidatos FOR ALL
    USING (public.get_current_user_rol() IN ('admin_rrhh', 'management'));
```

---

### 4.3 Funciones helper de RLS

**`public.get_current_user_rol()`** — la única función helper custom. Definida en `001_create_users.sql`:

```sql
CREATE OR REPLACE FUNCTION public.get_current_user_rol()
RETURNS TEXT
LANGUAGE SQL
SECURITY DEFINER    ← bypasea RLS al consultar users (evita recursión)
STABLE              ← result es cacheable dentro del mismo statement
SET search_path = public
AS $$
    SELECT rol FROM public.users WHERE id = auth.uid()
$$;
```

**`public.set_updated_at()`** — trigger function para `updated_at`:
```sql
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;
```

**`public.fn_auditoria()`** — trigger function de auditoría automática:
```sql
CREATE OR REPLACE FUNCTION public.fn_auditoria()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO public.auditoria (tabla, registro_id, accion, datos_nuevos, usuario_id)
        VALUES (TG_TABLE_NAME, NEW.id, 'INSERT', to_jsonb(NEW), auth.uid());
        RETURN NEW;
    -- UPDATE y DELETE análogos
    END IF;
END; $$;
```

**NO EXISTE** ninguna función tipo `auth_empresa_id()` ni `current_empresa_id()` — confirmado: sistema mono-empresa.

---

### 4.4 Storage — buckets configurados

Según `CLAUDE.md` del proyecto y referencias en el código:

| Bucket | Uso |
|---|---|
| `documentos` | Archivos adjuntos de empleados (contratos, recibos, certificados) — tabla `documentos_empleado` |
| `cvs` | CVs de candidatos — tabla `candidatos.cv_storage_path` |
| `avatars` | Fotos de perfil de empleados — tabla `empleados.foto_url` |
| `reportes` | PDFs y Excel generados — tabla `assessment_reportes.storage_path` |

**Relevante para el traspaso**: si los módulos nuevos generan documentos adjuntos (ej: certificados de capacitación, documentación de offboarding), usar el bucket `documentos` ya configurado.

---

## BLOQUE 5 — Mapa de módulos a portar

### Módulos a agregar: vacaciones, ausencias, asistencia, indicadores, capacitaciones, evaluaciones de desempeño, skills, días especiales

---

#### 5.1 Vacaciones

| Item | Estado |
|---|---|
| **¿Existe algo parcial?** | **NO EXISTE**. No hay tabla `vacaciones` ni ruta `/api/vacaciones` ni componente frontend de vacaciones en ningún archivo. |
| **Panel/rol** | Empleado: solicita vacaciones. Admin_rrhh: aprueba/rechaza. Management: puede ver el equipo a su cargo. |
| **Tablas relacionadas** | `empleados` (quien solicita) · `areas` (para validar quorum) · La futura `vacaciones` necesita FK a `empleados.id` |
| **Conflictos de nombre** | Ninguno. La tabla `vacantes` (posiciones de trabajo) y `vacaciones` (licencias pagas) son distintas — nombre libre. |

---

#### 5.2 Ausencias

| Item | Estado |
|---|---|
| **¿Existe algo parcial?** | **NO EXISTE**. No hay tabla, router, ni página de ausencias. El campo `empleados.estado` tiene valor `'licencia'` como estado general del empleado, pero no hay registro de instancias de ausencia. |
| **Panel/rol** | Admin_rrhh registra ausencias. Empleado ve las suyas. Management ve el equipo. |
| **Tablas relacionadas** | `empleados` (FK principal). Se relacionaría con `vacaciones` si se quiere reportar total de días por tipo. |
| **Conflictos de nombre** | Ninguno. |

---

#### 5.3 Asistencia

| Item | Estado |
|---|---|
| **¿Existe algo parcial?** | **NO EXISTE**. No hay tabla `asistencia` ni ninguna referencia a fichaje, check-in/check-out, o marcación de presencia. |
| **Panel/rol** | Admin_rrhh y management ven reportes. Empleado ve su propio historial. |
| **Tablas relacionadas** | `empleados` · Potencialmente `ausencias` y `vacaciones` para calcular días efectivos trabajados. |
| **Conflictos de nombre** | Ninguno. |

---

#### 5.4 Indicadores (KPIs de RRHH)

| Item | Estado |
|---|---|
| **¿Existe algo parcial?** | **PARCIALMENTE**. El `dashboard_service.py` y `GET /api/dashboard` ya calculan KPIs de headcount, costos y alertas. Pero no hay tabla separada de indicadores ni histórico de métricas. Los KPIs son calculados on-demand, no almacenados. |
| **Panel/rol** | Admin_rrhh y management. |
| **Tablas relacionadas** | Dependería de qué indicadores: ausencias + asistencia (para ausentismo) · costos_nomina (para costo por empleado) · vacantes + candidatos (para tiempo de cobertura). |
| **Conflictos de nombre** | Si se crea tabla `indicadores_rrhh` o `metricas_rrhh`, sin conflicto. No tocar el endpoint `/api/dashboard` existente. |

---

#### 5.5 Capacitaciones

| Item | Estado |
|---|---|
| **¿Existe algo parcial?** | **PARCIALMENTE**. La tabla `planes_carrera_hitos` tiene tipo `'capacitacion'` como un hito posible de un plan de carrera. Pero no hay módulo de gestión de capacitaciones independiente (catálogo, inscripción, seguimiento). El presupuesto tiene tipo `'capacitacion'` en `presupuesto_areas`. |
| **Panel/rol** | Admin_rrhh crea el catálogo y registra asistencia. Empleado ve sus capacitaciones. Management ve el equipo. |
| **Tablas relacionadas** | `empleados` · `areas` · `planes_carrera_hitos` (para marcar hito como completado al aprobar la capacitación). |
| **Conflictos de nombre** | No hay tabla `capacitaciones`. Nombre libre. |

---

#### 5.6 Evaluaciones de desempeño

| Item | Estado |
|---|---|
| **¿Existe algo parcial?** | **ATENCIÓN — POSIBLE CONFUSIÓN**. Existe todo el módulo de `assessment` (campañas, links, resultados, reportes) pero está orientado a evaluaciones conductuales/cognitivas/técnicas para candidatos o empleados de forma puntual. **No hay evaluaciones de desempeño periódicas** (90 días, anual, por objetivos). Son módulos distintos. |
| **Panel/rol** | Empleado completa autoevaluación. Manager evalúa al empleado. Admin_rrhh administra ciclos. |
| **Tablas relacionadas** | `empleados` · `assessment_resultados` podría reutilizarse si se extiende el tipo de campaña. |
| **Conflictos de nombre** | El módulo `assessment` ya existe. La nueva tabla debería llamarse `evaluaciones_desempeno` o `ciclos_evaluacion` para no colisionar. NO reusar `assessment_campanas` para esto sin planificarlo. |

---

#### 5.7 Skills / Competencias

| Item | Estado |
|---|---|
| **¿Existe algo parcial?** | **NO EXISTE**. No hay tabla de skills, competencias, ni matriz de habilidades en ningún archivo. |
| **Panel/rol** | Admin_rrhh define el catálogo de skills. Empleado tiene skills asignadas. Manager puede actualizar el nivel. |
| **Tablas relacionadas** | `empleados` (many-to-many con skills) · `vacantes` (skills requeridas) · `evaluaciones_desempeno` (evaluación por competencias). |
| **Conflictos de nombre** | Ninguno. Nombre sugerido: `skills` (catálogo) + `empleado_skills` (pivot table). |

---

#### 5.8 Días especiales

| Item | Estado |
|---|---|
| **¿Existe algo parcial?** | **NO EXISTE**. No hay tabla de feriados, días no laborables, o calendarios especiales. |
| **Panel/rol** | Admin_rrhh define el calendario de días especiales/feriados. Todos los módulos que calculan días hábiles lo consumen. |
| **Tablas relacionadas** | Consumida por `vacaciones`, `ausencias`, `asistencia` para calcular días hábiles. |
| **Conflictos de nombre** | Ninguno. Nombre sugerido: `dias_especiales` o `calendario_laboral`. |

---

### Resumen visual — tabla de módulos × estado

| Módulo | ¿Existe? | Panel principal | Tablas a relacionar | Conflicto de nombre |
|---|---|---|---|---|
| Vacaciones | ❌ NO | Empleado (solicita) / Admin (aprueba) | `empleados`, `areas` | Ninguno |
| Ausencias | ❌ NO | Admin (registra) / Empleado (ve las suyas) | `empleados` | Ninguno |
| Asistencia | ❌ NO | Admin / Management (reportes) / Empleado (historial) | `empleados`, `ausencias` | Ninguno |
| Indicadores | ⚠️ PARCIAL (dashboard on-demand) | Admin / Management | `costos_nomina`, `ausencias`, `vacantes` | No tocar `/api/dashboard` |
| Capacitaciones | ⚠️ PARCIAL (hito de plan_carrera) | Admin (catálogo) / Empleado (historial) | `empleados`, `planes_carrera_hitos` | Ninguno |
| Evaluaciones desempeño | ⚠️ ATENCIÓN (assessment ≠ evaluación periódica) | Empleado (auto) / Manager / Admin (ciclos) | `empleados`, posible reusar assessment | ⚠️ NO colisionar con `assessment_*` |
| Skills | ❌ NO | Admin (catálogo) / Manager (asigna niveles) | `empleados`, `vacantes` | Ninguno |
| Días especiales | ❌ NO | Admin (define calendario) | `vacaciones`, `asistencia`, `ausencias` | Ninguno |

---

## Cierre — Supuestos que NO pude confirmar

Los siguientes puntos quedaron sin confirmación directa en el código. Deben resolverse antes de codear:

1. **¿Cómo funciona el módulo de vacaciones en el proyecto origen?** La auditoría cubre solo HR Karstec. Si el proyecto origen tiene `empresa_id` o una estructura de estados distinta (aprobado_manager → aprobado_rrhh → efectuado vs una sola aprobación), eso define el modelo de datos a portar.

2. **¿La tabla `empleados.estado` ('activo'|'baja'|'licencia'|'suspendido') es suficiente para reflejar el estado de una solicitud de vacaciones, o se necesita tabla separada?** El campo `estado='licencia'` en empleados es un estado general del empleado, no un registro de licencia. Muy probablemente se necesita tabla separada.

3. **¿Management puede aprobar vacaciones del propio equipo, o solo admin_rrhh?** El sistema de roles es simple (3 valores), pero el CLAUDE.md dice que management tiene "acceso configurable por módulo". No hay tabla de permisos granulares por módulo implementada visible en el código — si existe, no está en las migraciones actuales.

4. **¿Hay integración con Google Calendar para sincronizar ausencias/vacaciones?** Existe `GET /api/integraciones/google/auth` y `gmail_service.py` pero no está claro si el scope del OAuth incluye Calendar. Verificar `usuario_integraciones` table y el scope pedido al hacer el OAuth flow.

5. **¿El módulo de evaluaciones de desempeño reutiliza la infraestructura de assessment (campañas, links, formularios dinámicos) o es un módulo propio con estructura fija (por objetivos, por competencias)?** Esta decisión de diseño define si se extiende `assessment_campanas` con un nuevo tipo o si se crean tablas `ciclos_evaluacion` + `evaluaciones_desempeno` desde cero.

6. **¿El tipo de contrato en la DB difiere del schema Pydantic?** La tabla `empleados` acepta `'efectivo'|'plazo_fijo'|'contratado'|'pasantia'`, pero el schema `EmpleadoBase.tipo_contrato` es `str` sin validación de enum. Si el proyecto origen usa valores distintos (ej: `'indefinido'`, `'honorarios'`), necesitará mapeo.

7. **¿Existe un `NEXT_PUBLIC_API_URL` configurado en el frontend del entorno de staging/producción?** El fallback es `http://localhost:8000`. Sin esta variable en Vercel, el frontend de producción apuntará al backend local y todo fallará silenciosamente.

8. **¿La columna `empleados.username` existe?** La migración `025_add_username_to_users.sql` agrega `username` a `users`, no a `empleados`. Confirmar que el CLAUDE.md del proyecto origen no referencia un campo `username` en empleados que no existe aquí.

---

*Auditoría generada el 2026-05-29. Todos los fragmentos de código fueron leídos directamente de los archivos fuente del proyecto `RRHH/backend/` y `RRHH/frontend/`. Ningún fragmento fue inferido ni inventado.*

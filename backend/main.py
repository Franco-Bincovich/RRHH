"""
HR Karstec — RRHH
Punto de entrada de la aplicación FastAPI.
Solo configuración de la app — sin lógica de negocio.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from config.settings import settings
from middleware.auth import AuthMiddleware
from middleware.error_handler import global_error_handler
from middleware.security_headers import SecurityHeadersMiddleware
from utils.errors import AppError
from utils.rate_limit import limiter, rate_limit_handler
from routers.areas import router as areas_router
from routers.areas_escrituras import router as areas_escrituras_router
from routers.auth import router as auth_router
from routers.cesiones import router as cesiones_router
from routers.costos import router as costos_router
from routers.costos_escrituras import router as costos_escrituras_router
from routers.empleados import router as empleados_router
from routers.empleados_catalogos import router as empleados_catalogos_router
from routers.empresa import router as empresa_router
from routers.offboarding import router as offboarding_router
from routers.onboarding import router as onboarding_router
from routers.onboarding_templates import router as onboarding_templates_router
from routers.onboarding_templates_escrituras import router as onboarding_templates_escrituras_router
from routers.assessment import router as assessment_router
from routers.dashboard import router as dashboard_router
from routers.organigrama import router as organigrama_router
from routers.importacion_nomina_empleados import router as importacion_nomina_empleados_router
from routers.mail_historial import router as mail_historial_router
from routers.plantillas import router as plantillas_router
from routers.importacion_nomina import router as importacion_nomina_router
from routers.integraciones import router as integraciones_router
from routers.reportes import router as reportes_router
from routers.sucesion import router as sucesion_router
from routers.candidatos import router as candidatos_router
from routers.ausencias import router as ausencias_router
from routers.ausencias_tipos import router as ausencias_tipos_router
from routers.configuracion import router as configuracion_router
from routers.vacaciones import router as vacaciones_router
from routers.vacaciones_empleado import router as vacaciones_empleado_router
from routers.vacaciones_pendientes import router as vacaciones_pendientes_router
from routers.equipo import router as equipo_router
from routers.dashboard_equipo import router as dashboard_equipo_router
from routers.vacantes import router as vacantes_router
from routers.capacitaciones import router as capacitaciones_router
from routers.asignaciones_capacitacion import router as asignaciones_cap_router
from routers.ev_plantillas import router as ev_plantillas_router
from routers.ev_criterios import router as ev_criterios_router
from routers.ev_ciclos import router as ev_ciclos_router
from routers.ev_instancias import router as ev_instancias_router
from routers.evaluaciones_import import router as evaluaciones_import_router
from routers.evaluaciones_resultados import router as evaluaciones_resultados_router
from routers.evaluaciones_resultados_export import router as evaluaciones_resultados_export_router
from routers.inventario_items import router as inventario_items_router
from routers.inventario_asignaciones import router as inventario_asignaciones_router
from routers.objetivos import router as objetivos_router
from routers.usuarios import router as usuarios_router
from routers.procesos import router as procesos_router
from routers.proyectos import router as proyectos_router
from routers.proyecto_asignaciones import router as proyecto_asignaciones_router
from routers.proyecto_horas import router as proyecto_horas_router
from routers.auditoria import router as auditoria_router
from routers.adjuntos import router as adjuntos_router
from routers.periodos import router as periodos_router

app = FastAPI(
    title="HR Karstec API",
    version="1.0.0",
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url=None,
)

# ── Rate limiting ──────────────────────────────────────────────────────────────
# SlowAPIMiddleware aplica el baseline (default_limits del limiter) a todo endpoint SIN
# decorador propio; los decorados los saltea y los resuelve su decorador. Las franjas
# específicas viven en cada router. Ver utils/rate_limit.py.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Middlewares — orden de ejecución al recibir un request:
#   CORS (más externo) → SecurityHeaders → SlowAPI → Auth (más interno).
# add_middleware hace prepend, así que el último agregado es el más externo.
# SlowAPI va DENTRO de CORS para que el 429 salga con headers CORS (si no, el front lo ve como
# error de red y no puede leer el código), y FUERA de Auth para que el límite proteja también
# la verificación del JWT: el fetch del JWKS y el lookup en `users` corren ahí adentro.
app.add_middleware(AuthMiddleware)             # se ejecuta ÚLTIMO (más interno)
app.add_middleware(SlowAPIMiddleware)          # 3°
app.add_middleware(SecurityHeadersMiddleware)  # 2°
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Empresa-Id"],
)  # se ejecuta PRIMERO (más externo)
# AppError registrado por TIPO específico → lo atiende el ExceptionMiddleware interno (dentro
# de CORS), así la respuesta de error reatraviesa el CORSMiddleware y sale con headers CORS.
app.add_exception_handler(AppError, global_error_handler)
# Catch-all de 500 inesperados: queda sobre Exception (ServerErrorMiddleware, fuera de CORS).
app.add_exception_handler(Exception, global_error_handler)

# ── Health check (ruta pública) ────────────────────────────────────────────────
# EXENTO del rate limiting a propósito: lo consultan los health checks de la plataforma (hoy
# Vercel, mañana el target group del ALB), todos desde la misma IP y con alta frecuencia.
# Limitarlo haría que el balanceador marque la instancia como caída y la saque de rotación.
@app.get("/health")
@limiter.exempt
async def health_check():
    return {"status": "ok", "env": settings.app_env}

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(areas_router, prefix="/api/areas", tags=["areas"])
app.include_router(areas_escrituras_router, prefix="/api/areas", tags=["areas"])  # mismo prefijo: las rutas no cambian
app.include_router(empleados_catalogos_router, prefix="/api/empleados", tags=["empleados"])  # ANTES de empleados (rutas estáticas vs /{id})
app.include_router(empleados_router, prefix="/api/empleados", tags=["empleados"])
app.include_router(cesiones_router, prefix="/api", tags=["cesiones"])
app.include_router(ausencias_tipos_router, prefix="/api/ausencias", tags=["ausencias"])  # ANTES de ausencias (rutas estáticas /tipos vs /{id})
app.include_router(ausencias_router, prefix="/api/ausencias", tags=["ausencias"])
app.include_router(vacaciones_empleado_router, prefix="/api/vacaciones", tags=["vacaciones"])  # ANTES de vacaciones (rutas estáticas /saldo y /empleado vs /{id})
app.include_router(vacaciones_router, prefix="/api/vacaciones", tags=["vacaciones"])
app.include_router(vacaciones_pendientes_router, prefix="/api/vacaciones-pendientes", tags=["vacaciones"])  # prefijo propio: /api/vacaciones/{id} se comería una ruta anidada
app.include_router(equipo_router, prefix="/api/equipo", tags=["equipo"])
app.include_router(dashboard_equipo_router, prefix="/api/dashboard-equipo", tags=["dashboard"])
app.include_router(vacantes_router, prefix="/api/vacantes", tags=["vacantes"])
app.include_router(candidatos_router, prefix="/api/candidatos", tags=["candidatos"])
app.include_router(onboarding_templates_router, prefix="/api/onboarding/templates", tags=["onboarding"])
app.include_router(onboarding_templates_escrituras_router, prefix="/api/onboarding/templates", tags=["onboarding"])
app.include_router(onboarding_router, prefix="/api/onboarding", tags=["onboarding"])
app.include_router(offboarding_router, prefix="/api/offboarding", tags=["offboarding"])
app.include_router(costos_router, prefix="/api/costos", tags=["costos"])
app.include_router(costos_escrituras_router, prefix="/api/costos", tags=["costos"])
app.include_router(sucesion_router, prefix="/api/sucesion", tags=["sucesion"])
# Assessment se monta solo si el módulo está activo. Apagado, /api/assessment/* no existe
# para el router y devuelve el 404 de plataforma, idéntico a cualquier ruta inexistente —
# nunca un 403 ni un mensaje que confirme que el módulo está ahí. Sus 2 rutas públicas se
# apagan en el mismo movimiento (middleware/auth.py::_is_public lee el mismo flag).
# PARA REACTIVARLO: ASSESSMENT_ENABLED=true en el entorno.
if settings.assessment_enabled:
    app.include_router(assessment_router, prefix="/api/assessment", tags=["assessment"])
app.include_router(organigrama_router, prefix="/api/organigrama", tags=["organigrama"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(empresa_router, prefix="/api/empresas", tags=["empresa"])
app.include_router(reportes_router, prefix="/api/reportes", tags=["reportes"])
app.include_router(importacion_nomina_empleados_router, prefix="/api/importacion", tags=["importacion"])
app.include_router(plantillas_router, prefix="/api/plantillas", tags=["plantillas"])
app.include_router(mail_historial_router, prefix="/api/mails", tags=["plantillas"])  # historial de envíos
app.include_router(importacion_nomina_router, prefix="/api/importacion", tags=["importacion"])
app.include_router(integraciones_router, prefix="/api/integraciones", tags=["integraciones"])
app.include_router(configuracion_router, prefix="/api/configuracion", tags=["configuracion"])
app.include_router(capacitaciones_router, prefix="/api/capacitaciones", tags=["capacitaciones"])
app.include_router(asignaciones_cap_router, prefix="/api/capacitaciones/asignaciones", tags=["capacitaciones"])
app.include_router(ev_plantillas_router, prefix="/api/evaluaciones/plantillas", tags=["evaluaciones"])
app.include_router(ev_criterios_router, prefix="/api/evaluaciones/plantillas", tags=["evaluaciones"])
app.include_router(ev_ciclos_router, prefix="/api/evaluaciones/ciclos", tags=["evaluaciones"])
app.include_router(ev_instancias_router, prefix="/api/evaluaciones/instancias", tags=["evaluaciones"])
app.include_router(evaluaciones_import_router, prefix="/api/evaluaciones/importar", tags=["evaluaciones"])
app.include_router(evaluaciones_resultados_export_router, prefix="/api/evaluaciones/resultados", tags=["evaluaciones"])
app.include_router(evaluaciones_resultados_router, prefix="/api/evaluaciones/resultados", tags=["evaluaciones"])
app.include_router(inventario_items_router, prefix="/api/inventario/items", tags=["inventario"])
app.include_router(inventario_asignaciones_router, prefix="/api/inventario/asignaciones", tags=["inventario"])
app.include_router(objetivos_router, prefix="/api/objetivos", tags=["objetivos"])
app.include_router(usuarios_router, prefix="/api/usuarios", tags=["usuarios"])
app.include_router(procesos_router, prefix="/api/procesos", tags=["procesos"])
app.include_router(proyectos_router, prefix="/api/proyectos", tags=["proyectos"])
app.include_router(proyecto_asignaciones_router, prefix="/api/proyectos", tags=["proyectos"])
app.include_router(proyecto_horas_router, prefix="/api/proyectos", tags=["proyectos"])
app.include_router(auditoria_router, prefix="/api/auditoria", tags=["auditoria"])
app.include_router(adjuntos_router, prefix="/api/adjuntos", tags=["adjuntos"])
app.include_router(periodos_router, prefix="/api/periodos", tags=["periodos"])

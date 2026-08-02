"""
Núcleo de permisos funcionales (Entrega 2).

Define el modelo de capacidades por rol y la dependency factory que lo aplica
en los routers. Es deliberadamente AUTOCONTENIDO: no importa settings, supabase
ni anthropic, así que no ejecuta IO en import-time y puede testearse como función
pura sin DB ni HTTP.

Modelo de roles:
    admin_rrhh        → acceso total (lectura + escritura) en toda sección.
    gerencia_lectura  → solo lectura en toda sección.
    mandos_medios     → lectura y escritura solo en vacaciones y ausencias.

El enforcement es por dependency (Depends(require_permission(...))), nunca por
middleware. El cableado a cada router se hace en sub-tareas posteriores (16.3/16.4);
acá solo vive el núcleo.
"""
from enum import Enum
from typing import Awaitable, Callable, Optional, Union

from starlette.requests import Request

from utils.errors import AppError


class Accion(str, Enum):
    """Tipo de operación sobre una sección: lectura o escritura."""

    READ = "read"
    WRITE = "write"


class Seccion(str, Enum):
    """
    Conjunto cerrado de secciones del sistema. Una por módulo con router real
    registrado en main.py (auth queda fuera: no es una sección de negocio gateada).
    """

    EMPLEADOS = "empleados"
    AREAS = "areas"
    AUSENCIAS = "ausencias"
    VACACIONES = "vacaciones"
    VACANTES = "vacantes"
    CANDIDATOS = "candidatos"
    ONBOARDING = "onboarding"
    OFFBOARDING = "offboarding"
    COSTOS = "costos"
    SUCESION = "sucesion"
    ASSESSMENT = "assessment"
    ORGANIGRAMA = "organigrama"
    DASHBOARD = "dashboard"
    EMPRESA = "empresa"
    REPORTES = "reportes"
    IMPORTACION = "importacion"
    INTEGRACIONES = "integraciones"
    CAPACITACIONES = "capacitaciones"
    EVALUACIONES = "evaluaciones"
    INVENTARIO = "inventario"
    OBJETIVOS = "objetivos"
    USUARIOS = "usuarios"
    PROCESOS = "procesos"
    PROYECTOS = "proyectos"
    AUDITORIA = "auditoria"
    PERIODOS = "periodos"
    # Reglas de negocio configurables (escala de vacaciones, base de días hábiles, tipos de
    # ausencia). Sección PROPIA a propósito: NO se reusa VACACIONES ni AUSENCIAS porque
    # mandos_medios tiene WRITE en las dos, y cargar una vacación no es lo mismo que cambiar
    # la regla con la que se calculan todas.
    CONFIGURACION = "configuracion"


# mandos_medios solo opera (R+W) sobre estas secciones; en el resto no puede nada.
MANDOS_MEDIOS_SECCIONES = frozenset({Seccion.VACACIONES, Seccion.AUSENCIAS})

# Fuente de verdad de los roles asignables del sistema. Alineada con el CHECK de
# public.users.rol (migración 057) y con las ramas de puede(). Reusar para validar
# cualquier rol entrante — NO hardcodear listas nuevas en otros módulos.
ROLES_VALIDOS = frozenset({"admin_rrhh", "gerencia_lectura", "mandos_medios"})


def puede(
    rol: Optional[str],
    seccion: Union[Seccion, str],
    accion: Union[Accion, str],
) -> bool:
    """
    Decide si un rol puede ejecutar una acción sobre una sección. Función pura.

    Acepta tanto enums como strings en `seccion` y `accion`; los normaliza
    internamente. Es fail-closed: ante cualquier entrada inválida (rol None o
    desconocido, sección o acción que no existen en sus enums) retorna False.

    Args:
        rol: Rol del usuario ('admin_rrhh' | 'gerencia_lectura' | 'mandos_medios').
        seccion: Sección objetivo, como Seccion o su valor string.
        accion: Operación a realizar, como Accion o su valor string ('read'|'write').

    Returns:
        True si el rol tiene la capacidad pedida; False en cualquier otro caso.
    """
    try:
        seccion = Seccion(seccion)
        accion = Accion(accion)
    except (ValueError, TypeError):
        return False

    if rol == "admin_rrhh":
        return True
    if rol == "gerencia_lectura":
        return accion is Accion.READ
    if rol == "mandos_medios":
        return seccion in MANDOS_MEDIOS_SECCIONES
    return False


def require_permission(
    seccion: Union[Seccion, str],
    accion: Union[Accion, str] = Accion.READ,
) -> Callable[[Request], Awaitable[None]]:
    """
    Construye una dependency de FastAPI que exige permiso sobre (seccion, accion).

    El callable devuelto lee el rol desde request.state.user (seteado por
    AuthMiddleware), aplica puede() y lanza AppError FORBIDDEN (403) si no alcanza.
    Es fail-closed: si request.state.user no existe o no trae rol, deniega en vez
    de romper con AttributeError.

    Args:
        seccion: Sección que protege la ruta.
        accion: Operación requerida; READ por defecto.

    Returns:
        Dependency async para usar con Depends(require_permission(...)).
    """

    async def _verificar(request: Request) -> None:
        user = getattr(request.state, "user", None)
        rol = user.get("rol") if isinstance(user, dict) else None
        if not puede(rol, seccion, accion):
            raise AppError(
                "No tenés permiso para realizar esta acción", "FORBIDDEN", 403
            )

    return _verificar

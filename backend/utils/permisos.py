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

⚠️ El enum `Seccion` VIVE EN `utils/_secciones.py` desde que este archivo llegó a 217/200 con la
sección de la agenda de eventos, y se RE-EXPORTA acá: `from utils.permisos import Seccion` sigue
siendo el import correcto y ninguno de los ~204 gates del repo cambió. El corte es por
responsabilidad — el modelo casi no cambia, el catálogo crece con cada módulo.
"""
from enum import Enum
from typing import Awaitable, Callable, Optional, Union

from starlette.requests import Request

from utils._secciones import Seccion
from utils.errors import AppError


class Accion(str, Enum):
    """Tipo de operación sobre una sección: lectura o escritura."""

    READ = "read"
    WRITE = "write"


# mandos_medios solo opera (R+W) sobre estas secciones; en el resto no puede nada.
MANDOS_MEDIOS_SECCIONES = frozenset({Seccion.VACACIONES, Seccion.AUSENCIAS})

# Fuente de verdad de los roles asignables del sistema. Alineada con el CHECK de
# public.users.rol (migración 057) y con las ramas de puede(). Reusar para validar
# cualquier rol entrante — NO hardcodear listas nuevas en otros módulos.
ROLES_VALIDOS = frozenset({"admin_rrhh", "gerencia_lectura", "mandos_medios"})

# Rol que ve las filas PRIVADAS de los demás, en los módulos que tienen visibilidad
# pública/privada por fila (plantillas de onboarding, agenda de eventos).
#
# 🔑 VIVE ACÁ Y NO EN CADA MÓDULO porque es una afirmación sobre el MODELO DE ROLES, no una
# primitiva de ninguno de los dos: "privada" ahí significa privacidad ENTRE PARES DE RRHH (un
# borrador que no quiero en la lista de mis compañeros), nunca confidencialidad frente a la
# dirección — que es lo que `gerencia_lectura` ya significa en todo el sistema. Con una copia por
# módulo, el día que se decida ocultarle algo a gerencia se cambiaría una y la otra seguiría
# abierta, en silencio. Al revés (abrir después lo que se cerró) tampoco se puede.
#
# NO es una excepción row-level al modelo: es el modelo aplicado. `puede()` no lo consulta —
# decide sobre secciones, no sobre filas—; lo consultan los filtros de visibilidad de los repos.
ROL_VE_PRIVADAS_AJENAS = "gerencia_lectura"


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

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
    # Catálogo de clientes (migración 102). SECCIÓN PROPIA, y la decisión merece explicación
    # porque el repo tiene un precedente que dice lo contrario:
    #
    # `/comunicacion` NO creó sección y reusa `configuracion`, con el argumento —correcto— de
    # que `puede()` es genérica: para cualquier sección fuera de MANDOS_MEDIOS_SECCIONES el
    # resultado es idéntico (admin escribe, gerencia lee, mandos nada), así que una sección
    # nueva "daría el mismo resultado a cambio de tocar el espejo manual con permisos.py".
    #
    # Lo que distingue este caso: comunicación era una RUTA DE FRONT sobre endpoints que YA
    # existían y ya estaban gateados con `configuracion`. Clientes es un módulo nuevo con
    # routers propios montados en main.py, y la invariante declarada de este enum es
    # justamente "una por módulo con router real registrado en main.py". Reusar acá dejaría el
    # gate del módulo apuntando a una sección que nombra otra cosa, y el día que alguien quiera
    # que gerencia vea clientes pero no la configuración de reglas, habría que partirlo con
    # datos ya cargados.
    #
    # NO se reusó PROYECTOS —que es la vecina obvia— porque el diseño de la carga de horas dejó
    # a `proyectos` explícitamente FUERA de ese flujo: el proyecto ahí es texto libre. Atarlos
    # por el permiso sugeriría un parentesco que el modelo no tiene.
    #
    # El costo es una línea acá y una en `frontend/services/permisos.ts`, y ese espejo NO es a
    # ciegas: `tests/test_espejo_permisos.py` compara los dos enteros y falla si falta una.
    CLIENTES = "clientes"
    # Catálogo de perfiles de puesto (migraciones 113/116). SECCIÓN PROPIA, por el mismo
    # criterio que CLIENTES: es un módulo nuevo con routers propios montados en
    # registro_routers.py, y la invariante declarada de este enum es "una por módulo con router
    # real registrado".
    #
    # NO se reusó VACANTES —que es la vecina obvia, y con la que va a haber un puente— porque
    # son dos permisos que se van a querer separar: un perfil de puesto es material de consulta
    # estable del equipo, y una vacante es un proceso de selección en curso. Atarlos hoy
    # obligaría a partirlos después con datos cargados, que es exactamente el costo que la nota
    # de CLIENTES describe.
    PERFILES_PUESTO = "perfiles_puesto"
    # Recategorizaciones (migraciones 113/116/117). SECCIÓN PROPIA, mismo criterio que las dos
    # de arriba: módulo nuevo con routers propios registrados.
    #
    # NO se reusó EMPLEADOS —que es la vecina obvia, y de cuya ficha cuelga una de las dos
    # vistas— porque ataría el permiso de RECATEGORIZAR al de editar el legajo, y son dos cosas
    # distintas: cualquiera que administra empleados corrige un teléfono, no cualquiera decide
    # que alguien cambió de categoría.
    #
    # ⚠️ Y NO reemplaza al gate de COSTOS: `impacto_salarial` se omite de la respuesta según
    # `Seccion.COSTOS + READ`, aparte de esto. Son dos ejes: esta sección dice quién ve el
    # módulo, COSTOS dice quién ve el monto adentro.
    RECATEGORIZACIONES = "recategorizaciones"


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

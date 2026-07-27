"""
Validación de la entidad PADRE de un adjunto (extraído: adjunto_service está en 141/150).

Los adjuntos son polimórficos: cuelgan de (entidad, entidad_id). Sin este despachador, `subir`
aceptaba cualquier entidad_id sin verificar que existiera ni que fuera de tu empresa — se podía
colgar un archivo del legajo de un empleado ajeno, y el adjunto quedaba etiquetado con TU
empresa (así que su dueño real ni lo veía).

Devuelve el empresa_id DEL PADRE, no un bool: es lo que el service usa para etiquetar el
adjunto. Con eso la empresa del adjunto sale siempre del recurso, no del selector del sidebar
—principio Vista vs Acción—, y deja de generarse el empresa_id NULL que hoy aparece cuando se
sube en modo consolidado.

Cada resolver usa el find_by_id ya parametrizado por empresa de su repo (ninguno necesitó
parámetros nuevos). "evaluacion" está mapeado a una Sección en adjunto_service pero NO tiene
resolver: no existe un repo que diga a qué apunta (¿lote?, ¿evaluado?, ¿instancia ev_*?) y no
tiene un solo caller en el repo ni en el front. Queda fail-closed hasta que se defina.
"""
from typing import Optional
from uuid import UUID

from utils.errors import AppError


def _empleado(entidad_id: str, empresa_id: Optional[UUID]):
    from repositories.empleado_repo import EmpleadoRepo
    return EmpleadoRepo().find_by_id(entidad_id, empresa_id)


def _vacacion(entidad_id: str, empresa_id: Optional[UUID]):
    from repositories.vacaciones_repo import VacacionesRepo
    return VacacionesRepo().find_by_id(entidad_id, empresa_id)


def _ausencia(entidad_id: str, empresa_id: Optional[UUID]):
    from repositories.ausencias_repo import AusenciasRepo
    return AusenciasRepo().find_by_id(entidad_id, empresa_id)


def _vacante(entidad_id: str, empresa_id: Optional[UUID]):
    from repositories.vacante_repo import VacanteRepo
    return VacanteRepo().find_by_id(entidad_id, empresa_id)


def _offboarding(entidad_id: str, empresa_id: Optional[UUID]):
    from repositories.offboarding_repo import OffboardingRepo
    return OffboardingRepo().find_instancia_min(entidad_id, empresa_id)


# entidad → resolver(entidad_id, empresa_id) -> fila | None. Las 5 que el front usa hoy.
RESOLVERS = {
    "empleado": _empleado,
    "vacacion": _vacacion,
    "ausencia": _ausencia,
    "vacante": _vacante,
    "offboarding": _offboarding,
}


def _empresa_de(fila) -> Optional[str]:
    """empresa_id de la fila del padre, venga como dict (offboarding) o como schema Pydantic."""
    valor = fila.get("empresa_id") if isinstance(fila, dict) else getattr(fila, "empresa_id", None)
    return str(valor) if valor else None


def ensure_padre_de_empresa(entidad: str, entidad_id, empresa_id: Optional[UUID],
                            resolvers: Optional[dict] = None) -> Optional[str]:
    """Valida que el padre exista y sea de `empresa_id`; devuelve SU empresa_id (str o None).

    `empresa_id` None = vista consolidada: no restringe cuál padre se puede elegir, pero la
    empresa devuelta sigue saliendo del padre (por eso el adjunto no queda en NULL).

    El 404 es el mismo para "no existe" y "es de otra empresa" —nunca un 403— para no confirmar
    la existencia de recursos ajenos.

    Args:
        entidad: tipo del padre (empleado | vacacion | ausencia | vacante | offboarding).
        entidad_id: id del padre.
        empresa_id: empresa activa del request. None = sin restricción.
        resolvers: mapa alternativo (inyección de dobles en tests). Default: RESOLVERS.

    Returns:
        empresa_id del padre como str, o None si el padre no la tiene cargada.

    Raises:
        AppError: ENTIDAD_INVALIDA (400) si la entidad no tiene resolver (ej. "evaluacion").
        AppError: PADRE_NOT_FOUND (404) si el padre no existe o es de otra empresa.
    """
    resolver = (resolvers or RESOLVERS).get(entidad)
    if resolver is None:
        raise AppError(f"Entidad no soportada para adjuntos: {entidad}", "ENTIDAD_INVALIDA", 400)
    fila = resolver(str(entidad_id), empresa_id)
    if not fila:
        raise AppError("El registro al que se adjunta no existe", "PADRE_NOT_FOUND", 404)
    return _empresa_de(fila)

"""
Helpers internos del módulo de empleados (capa service).

Dedup extraído de EmpleadoService (T18.4c) para descargar líneas del service tras
instrumentar audit, con comportamiento idéntico (mismos mensajes/códigos de AppError).
Precedente: _vacaciones_utils.py. Funciones finas, sin estado.
"""
from typing import Optional
from uuid import UUID

from repositories.empleado_repo import EmpleadoRepo
from schemas.empleado import EmpleadoResponse
from utils.errors import AppError


def ensure_legajo_unico(
    repo: EmpleadoRepo, legajo: Optional[str], empresa_id: Optional[UUID],
    exclude_id: Optional[str] = None,
) -> None:
    """Lanza LEGAJO_DUPLICADO (409) si `legajo` ya existe en la empresa (excluye exclude_id)."""
    if not legajo or not empresa_id:
        return
    existing = repo.find_by_legajo(legajo, empresa_id)
    if existing and existing.id != exclude_id:
        raise AppError("Ya existe un empleado con ese legajo en esta empresa", "LEGAJO_DUPLICADO", 409)


def empleado_or_404(empleado: Optional[EmpleadoResponse]) -> EmpleadoResponse:
    """Devuelve el empleado o lanza EMPLEADO_NOT_FOUND (404) si es None."""
    if not empleado:
        raise AppError("Empleado no encontrado", "EMPLEADO_NOT_FOUND", 404)
    return empleado


def ensure_area_valida(area_repo, area_id, empresa_id: Optional[UUID],
                       ya_validadas: frozenset = frozenset()) -> None:
    """Lanza AREA_NOT_FOUND (404) si `area_id` no es un área activa de `empresa_id`.

    Las áreas son POR EMPRESA (dos empresas pueden tener un "Sistemas" distinto), y el WHERE de
    empresa del UPDATE de empleados restringe qué fila se toca, no qué valor se escribe: sin esto
    un empleado puede quedar apuntando a un área ajena y aparecer en los listados de otra empresa.

    El guard de nulo vive acá (no en los call sites), igual que en ensure_manager_valido:
    area_id None = "no se toca el área" en un update parcial. empresa_id None = consolidado, no
    restringe. Mismo mensaje y code que "el área no existe" —nunca un 403—: no confirma la
    existencia de áreas de otra empresa.

    `ya_validadas` es un atajo de LECTURA, no un permiso: son ids que el caller YA probó de
    `empresa_id` dentro de la MISMA operación, así que volver a preguntárselo a la base es
    consultar dos veces por lo mismo. Lo usa el import de nómina, que resuelve el área con
    `NominaCatalogos` —cuyo cache solo contiene áreas de esa empresa, por construcción— dos
    líneas antes de llamar acá; sin esto paga una query por fila del CSV.

    🔴 NO es un flag que apague la validación: si el id no está en el set, se valida igual
    contra la base. El default vacío deja el comportamiento IDÉNTICO para todos los demás
    callers (alta y edición manual desde la ficha), que no pasan nada.

    Args:
        area_repo: AreaRepo (o doble de test) — su find_by_id ya filtra por empresa.
        area_id: área candidata (UUID o str). None = no hay nada que validar.
        empresa_id: empresa contra la que se valida. None = sin restricción.
        ya_validadas: ids de área ya probados de `empresa_id` en esta operación. Vacío = validar todo.

    Raises:
        AppError: AREA_NOT_FOUND (404) si el área no existe, está inactiva o es de otra empresa.
    """
    if area_id is None:
        return
    if str(area_id) in ya_validadas:
        return
    if not area_repo.find_by_id(str(area_id), str(empresa_id) if empresa_id else None):
        raise AppError("Área no encontrada", "AREA_NOT_FOUND", 404)

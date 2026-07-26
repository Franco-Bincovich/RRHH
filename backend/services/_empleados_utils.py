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


def ensure_no_ciclo_manager(repo: EmpleadoRepo, empleado_id, manager_id, max_saltos: int = 50) -> None:
    """Lanza MANAGER_CICLO (400) si asignar `manager_id` como superior de `empleado_id` crea una
    jerarquía circular. Sube por la cadena de managers del candidato (find_by_id); si en algún
    salto se llega al propio empleado, hay ciclo — incluye la auto-referencia (manager == empleado).
    `max_saltos` es la red contra datos ya corruptos: si la cadena no termina, se asume ciclo."""
    if manager_id is None:
        return
    emp = str(empleado_id)
    actual: Optional[str] = str(manager_id)
    for _ in range(max_saltos):
        if actual == emp:
            raise AppError("El superior asignado genera una jerarquía circular", "MANAGER_CICLO", 400)
        nodo = repo.find_by_id(actual)
        if nodo is None or nodo.manager_id is None:
            return
        actual = str(nodo.manager_id)
    raise AppError("El superior asignado genera una jerarquía circular", "MANAGER_CICLO", 400)

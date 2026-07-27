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


def ensure_manager_valido(repo: EmpleadoRepo, manager_id, empresa_id: Optional[UUID]) -> None:
    """Lanza MANAGER_NOT_FOUND (404) si `manager_id` no es un empleado de `empresa_id`.

    Barrera contra el superior cruzado entre empresas: el WHERE de empresa del UPDATE restringe
    QUÉ fila se toca, no QUÉ VALOR se escribe, así que sin esto un manager_id ajeno entra igual.
    Importa más allá de la integridad del organigrama — el ownership de mandos_medios se resuelve
    por manager_id, y un superior de otra empresa haría que ids_subordinados cruce la frontera.

    El guard de nulo vive acá (no en los call sites): manager_id None = "sin superior", caso
    válido que no valida nada. empresa_id None = vista consolidada ("Todas las empresas",
    semántica de get_empresa_id): no restringe, cualquier empleado existente sirve de superior.

    Mismo mensaje y mismo code para "no existe" y "existe en otra empresa" —nunca un 403— para
    no confirmar la existencia de empleados ajenos.

    Args:
        repo: EmpleadoRepo (o doble de test) — su find_by_id ya filtra por empresa.
        manager_id: superior candidato (UUID o str). None = no hay nada que validar.
        empresa_id: empresa contra la que se valida. None = sin restricción.

    Raises:
        AppError: MANAGER_NOT_FOUND (404) si el superior no existe o es de otra empresa.
    """
    if manager_id is None:
        return
    if not repo.find_by_id(str(manager_id), empresa_id):
        raise AppError("Superior no encontrado", "MANAGER_NOT_FOUND", 404)


def ensure_area_valida(area_repo, area_id, empresa_id: Optional[UUID]) -> None:
    """Lanza AREA_NOT_FOUND (404) si `area_id` no es un área activa de `empresa_id`.

    Las áreas son POR EMPRESA (dos empresas pueden tener un "Sistemas" distinto), y el WHERE de
    empresa del UPDATE de empleados restringe qué fila se toca, no qué valor se escribe: sin esto
    un empleado puede quedar apuntando a un área ajena y aparecer en los listados de otra empresa.

    El guard de nulo vive acá (no en los call sites), igual que en ensure_manager_valido:
    area_id None = "no se toca el área" en un update parcial. empresa_id None = consolidado, no
    restringe. Mismo mensaje y code que "el área no existe" —nunca un 403—: no confirma la
    existencia de áreas de otra empresa.

    Args:
        area_repo: AreaRepo (o doble de test) — su find_by_id ya filtra por empresa.
        area_id: área candidata (UUID o str). None = no hay nada que validar.
        empresa_id: empresa contra la que se valida. None = sin restricción.

    Raises:
        AppError: AREA_NOT_FOUND (404) si el área no existe, está inactiva o es de otra empresa.
    """
    if area_id is None:
        return
    if not area_repo.find_by_id(str(area_id), str(empresa_id) if empresa_id else None):
        raise AppError("Área no encontrada", "AREA_NOT_FOUND", 404)


def ensure_no_ciclo_manager(repo: EmpleadoRepo, empleado_id, manager_id,
                            empresa_id: Optional[UUID] = None, max_saltos: int = 50) -> None:
    """Lanza MANAGER_CICLO (400) si asignar `manager_id` como superior de `empleado_id` crea una
    jerarquía circular. Sube por la cadena de managers del candidato (find_by_id); si en algún
    salto se llega al propio empleado, hay ciclo — incluye la auto-referencia (manager == empleado).
    `max_saltos` es la red contra datos ya corruptos: si la cadena no termina, se asume ciclo.

    `empresa_id` acota el recorrido a la empresa (None = consolidado, cadena global: el
    comportamiento previo). No devuelve datos —solo decide ciclo/no-ciclo—, pero recorrer dentro
    de la empresa evita que una cadena cruzada (dato ya corrupto) altere el veredicto."""
    if manager_id is None:
        return
    emp = str(empleado_id)
    actual: Optional[str] = str(manager_id)
    for _ in range(max_saltos):
        if actual == emp:
            raise AppError("El superior asignado genera una jerarquía circular", "MANAGER_CICLO", 400)
        nodo = repo.find_by_id(actual, empresa_id)
        if nodo is None or nodo.manager_id is None:
            return
        actual = str(nodo.manager_id)
    raise AppError("El superior asignado genera una jerarquía circular", "MANAGER_CICLO", 400)

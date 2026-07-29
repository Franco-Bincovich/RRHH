"""
Servicio de catálogos de empleados — pools de autocompletado (roles y campos del legajo).
Separado de empleado_service.py (que estaba en su límite de líneas) para que la lógica de
catálogos viva junta, simétrica al router empleados_catalogos.py.
Flujo: router → service → repository → DB
"""
from typing import Optional
from uuid import UUID

from repositories.empleado_roles_repo import EmpleadoRolesRepo
from utils.errors import AppError

# Única fuente de verdad de qué columnas del legajo se pueden autocompletar (A1.2).
# Restringe el endpoint /valores-conocidos: evita exponer columnas arbitrarias de empleados.
CAMPOS_AUTOCOMPLETABLES = frozenset({
    "gerencia", "sector", "seniority", "tipo_contrato",
    "perfil", "categoria", "ubicacion", "organismo", "tipo_documento",
})


class EmpleadoCatalogosService:
    def __init__(self, roles_repo: Optional[EmpleadoRolesRepo] = None) -> None:
        self._roles_repo = roles_repo or EmpleadoRolesRepo()

    def get_roles_conocidos(self) -> list[str]:
        """Pool compartido de roles ya usados (todas las empresas) para autocompletar el form."""
        return self._roles_repo.get_roles_conocidos()

    def get_valores_conocidos(self, campo: str) -> list[str]:
        """Pool compartido de valores ya usados de un campo autocompletable del legajo.

        Valida `campo` contra la whitelist CAMPOS_AUTOCOMPLETABLES (única fuente de verdad
        de qué columnas se pueden autocompletar) ANTES de tocar la DB; un campo fuera de la
        whitelist es un error de cliente, no una query sobre una columna arbitraria."""
        if campo not in CAMPOS_AUTOCOMPLETABLES:
            raise AppError("Campo no válido", "CAMPO_INVALIDO", 400)
        return self._roles_repo.get_valores_conocidos(campo)

    def get_seleccionables(self, empresa_id: UUID) -> list[dict]:
        """Lista liviana de empleados activos de una empresa, para poblar selects (ej. superior inmediato)."""
        return self._roles_repo.get_seleccionables(empresa_id)

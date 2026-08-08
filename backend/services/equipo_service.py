"""
Service del roster "mi equipo": expone el universo de empleados que un usuario
puede ver por ownership, SIN abrir la sección empleados completa.

Reusa services.ownership.ids_empleados_visibles como única fuente del criterio de
"su gente" (no lo reimplementa). Usa dos repos: EmpleadoOwnershipRepo resuelve el
criterio (vínculo usuario→empleado + subordinados); EquipoRepo hace la proyección.
"""
from typing import List, Optional

from repositories.empleado_ownership_repo import EmpleadoOwnershipRepo
from repositories.equipo_repo import EquipoRepo
from schemas.equipo import EquipoMiembroResponse
from services._equipo_export import construir_filas_export
from services._limite_export import verificar_limite_export
from services.export import Descarga, build_export
from services.ownership import ids_empleados_visibles


class EquipoService:
    """Orquesta ownership + repo de proyección para devolver el roster visible de un usuario."""

    def __init__(
        self,
        ownership_repo: Optional[EmpleadoOwnershipRepo] = None,
        equipo_repo: Optional[EquipoRepo] = None,
    ) -> None:
        self._ownership = ownership_repo or EmpleadoOwnershipRepo()
        self._equipo = equipo_repo or EquipoRepo()

    def get_equipo(self, user_id: str, rol: str) -> List[EquipoMiembroResponse]:
        """
        Devuelve el roster de empleados visibles para un usuario según su rol.

        Resuelve el universo con ids_empleados_visibles (contrato de services.ownership):
            None      → sin restricción: todos los empleados (admin_rrhh/gerencia_lectura).
            [ids...]  → solo esos empleados (mando: su registro + subordinados directos).
            []        → sin empleado vinculado / fail-closed → lista vacía sin consultar DB.

        Los empleados se traen con el nombre de empresa resuelto y ya ordenados por
        apellido, nombre en el repo; se mapean al shape de salida {id, nombre, apellido, empresa}.

        Args:
            user_id: UUID (str) del usuario logueado (request.state.user["id"]).
            rol: rol canónico del usuario (ver ROLES_VALIDOS en utils.permisos).

        Returns:
            Lista de EquipoMiembroResponse ordenada por apellido, nombre; [] si no ve a nadie.
        """
        ids = ids_empleados_visibles(user_id, rol, self._ownership)
        if ids == []:
            return []
        filas = self._equipo.find_equipo(ids)
        return [EquipoMiembroResponse.model_validate(f) for f in filas]

    def exportar(self, user_id: str, rol: str, formato: str = "excel") -> Descarga:
        """Exporta el roster visible para ESE usuario.

        🔴 LLAMA A `get_equipo`, NO RECONSTRUYE LA CONSULTA. Es la única línea que importa de
        este método: acá el filtro no viene por Query sino del OWNERSHIP, así que un export con
        su propia consulta le entregaría a un `mandos_medios` la nómina entera —incluida gente
        que no puede ver en ninguna otra pantalla— y no habría ningún error que lo delatara.
        Delegando, el conjunto sale del mismo `ids_empleados_visibles` que el listado y las dos
        superficies no pueden divergir.

        ⚠️ Y por lo mismo NO SE ACOTA POR EMPRESA. Un mando puede tener subordinados de otra
        empresa del grupo (decisión de producto; ver `services/_alcance_mandos.py`), y el repo ya
        filtra solo por `in_("id", ids)`. Agregar un `.eq("empresa_id")` "por consistencia"
        recortaría el archivo respecto de lo que la pantalla muestra.

        Args:
            user_id · rol: los del request. Definen el universo; no hay filtros de Query.
            formato: pdf | excel | csv | word.
        """
        items = self.get_equipo(user_id, rol)
        verificar_limite_export(len(items))
        datos = {"Mi equipo": construir_filas_export(items)}
        return build_export(nombre="Mi equipo", datos=datos, filename_base="equipo", formato=formato)

"""
Servicio de áreas. Lógica de negocio del módulo de Áreas.
Flujo: router → service → repository → DB

🔴 AUDITA LAS TRES ESCRITURAS, Y ES TODO O NADA (25/8/2026). El disparador fue la baja —que el
barrido nº 42 tenía declarada como DEUDA porque `empleados.area_id` la referencia— pero
`tests/test_auditoria_coherente.py` exige que un módulo que audita ALGO audite TODO. El porqué de
cada campo del payload está en `services/_audit_payloads_areas.py`.
"""
from typing import List, Optional
from uuid import UUID

from repositories.area_repo import AreaRepo
from schemas.area import AreaCreate, AreaListResponse, AreaResponse, AreaUpdate
from services._areas_export import construir_filas_export
from services._areas_write import actualizar as _actualizar
from services._areas_write import crear as _crear
from services._areas_write import eliminar as _eliminar
from services._limite_export import LIMITE_FILAS_EXPORT, verificar_limite_export
from services._paginacion import cantidad_paginas
from services.audit_service import AuditService
from services.export import Descarga, build_export
from utils.errors import AppError
from utils.logger import logger

_NO_ENCONTRADA = ("Área no encontrada", "AREA_NOT_FOUND", 404)


class AreaService:
    def __init__(self, repo: Optional[AreaRepo] = None,
                 audit: Optional[AuditService] = None) -> None:
        self._repo = repo or AreaRepo()
        self._audit = audit or AuditService()

    def get_areas(self, empresa_id: Optional[str] = None) -> List[AreaResponse]:
        """El CATÁLOGO completo de áreas activas, sin paginar. Alimenta `/api/areas/opciones`.

        🔴 NO PAGINA, Y NO ES UN OLVIDO: sus consumidores son los ~15 selectores de área del
        front (filtros de vacaciones, ausencias, inventario, capacitaciones, proyectos, reportes,
        los modales de empleado y vacante…) y la resolución nombre→id del import de nómina.
        Todos necesitan el conjunto entero: un dropdown que muestre 20 de ~180 no da error, da
        un área que "no existe". La pantalla de gestión usa `get_pagina`.

        Args:
            empresa_id: Si se provee, filtra las áreas de esa empresa. None = todas.

        Returns:
            Lista de AreaResponse ordenada por nombre.
        """
        return self._repo.find_all(empresa_id)

    def get_pagina(self, empresa_id: Optional[str] = None, search: Optional[str] = None,
                   page: int = 1, page_size: int = 20) -> AreaListResponse:
        """Una página del listado de gestión, con búsqueda por nombre server-side."""
        items, total = self._repo.find_pagina(empresa_id, search, page, page_size)
        return AreaListResponse(items=items, total=total, page=page, page_size=page_size,
                                total_pages=cantidad_paginas(total, page_size))

    def exportar(self, empresa_id: Optional[str] = None, formato: str = "excel",
                 search: Optional[str] = None) -> Descarga:
        """Exporta el listado con los MISMOS filtros que la pantalla, `search` incluido.

        🔴 EL `search` ES LA RAZÓN DE ESTA FIRMA. Hasta el 15/8/2026 el buscador de áreas
        filtraba en el cliente, así que el export no lo veía: buscabas "Sistemas", la pantalla
        mostraba 3 filas y el archivo salía con las 58. Ahora los dos van por `get_pagina`, que
        es lo que hace estructuralmente imposible que vuelvan a divergir.
        """
        pagina = self.get_pagina(empresa_id, search, 1, LIMITE_FILAS_EXPORT)
        verificar_limite_export(pagina.total)  # total exacto (count="exact"), respeta los filtros
        datos = {"Áreas": construir_filas_export(pagina.items)}
        return build_export(nombre="Áreas", datos=datos, filename_base="areas", formato=formato)

    def get_area(self, id: UUID, empresa_id: Optional[str] = None) -> AreaResponse:
        """
        Retorna el detalle de un área por ID.

        Args:
            id: UUID del área a consultar.

        Returns:
            AreaResponse con todos los campos del área.

        Raises:
            AppError: AREA_NOT_FOUND (404) si no existe, está inactiva o es de otra empresa
                (mismo code y mensaje: no confirma la existencia de áreas ajenas).
        """
        area = self._repo.find_by_id(str(id), empresa_id)
        if not area:
            raise AppError(*_NO_ENCONTRADA)
        return area

    def create_area(self, data: AreaCreate, created_by: str) -> AreaResponse:
        """Crea un área nueva. Ver `_areas_write.crear`."""
        return _crear(self._repo, self._audit, data, created_by)

    def update_area(self, id: UUID, data: AreaUpdate, empresa_id: Optional[str] = None,
                    usuario_id: Optional[str] = None) -> AreaResponse:
        """Edición parcial de un área. Ver `_areas_write.actualizar`."""
        return _actualizar(self._repo, self._audit, id, data, empresa_id, usuario_id)

    def delete_area(self, id: UUID, empresa_id: Optional[str] = None,
                    usuario_id: Optional[str] = None) -> bool:
        """La baja es LÓGICA (`activo=False`): la fila queda y el área sale de los selectores.

        La implementación y el porqué del evento están en `_areas_write.eliminar`. La cita queda
        ACÁ además de allá a propósito: el detector de bajas lógicas del inventario de smoke
        (`scripts/_inv_baja_logica.py`) **saltea los módulos `_*.py`**, así que si la única
        evidencia viviera en el write path extraído, `/api/areas/{id}` volvería a aparecer en el
        inventario como «🔴 borra la fila» — mintiéndole al tester en la columna que existe para
        decidir si aprieta el botón."""
        return _eliminar(self._repo, self._audit, id, empresa_id, usuario_id)

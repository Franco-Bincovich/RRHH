"""
Servicio de catálogos de objetivos: los vocabularios que alimentan el formulario y los filtros.

Simétrico con `empleado_catalogos_service.py`, y separado de `objetivo_service.py` por el mismo
motivo que allá: aquél orquesta el ciclo de vida del objetivo (validar, escribir, borrar) y esto
son lecturas de apoyo que no tocan una sola regla de negocio. Además `objetivo_service` está en
142 contra un tope de 150 y esto no entraba.

🔴 HAY DOS CATÁLOGOS Y VIVEN EN LUGARES DISTINTOS, a propósito:

  · **`tipo`** es un vocabulario CERRADO que no depende de los datos: son los dos literales del
    CHECK de la migración 119. Se sirve desde `schemas/objetivo.TIPOS_OPCIONES`, pegado al
    `Literal` que valida, y el router lo devuelve sin pasar por acá — no hay nada que consultar.
  · **`areas_involucradas`** es texto libre: su vocabulario **son los datos**. Sale de la base y
    cambia con cada objetivo que se carga, así que necesita repo, service y esta capa.

Confundirlos es lo que llevaría a guardar las áreas en una constante o a consultar los tipos a la
base. Están separados para que la diferencia se vea al leer el router.
"""
from typing import List, Optional
from uuid import UUID

from repositories.objetivo_areas_repo import ObjetivoAreasRepo


class ObjetivoCatalogosService:
    def __init__(self, repo: Optional[ObjetivoAreasRepo] = None) -> None:
        self._repo = repo or ObjetivoAreasRepo()

    def get_areas_conocidas(self, empresa_id: Optional[UUID] = None) -> List[str]:
        """Las áreas ya usadas, para el desplegable del filtro. None = consolidado.

        No filtra, no valida y no transforma: el aplanado y el orden los hace el repo, en una
        sola pasada sobre lo que trajo la query. Esta capa existe para que el router no llame al
        repositorio directo (regla de capas), no para agregar lógica que no hay.

        Args:
            empresa_id: empresa del request. None = todas.

        Returns:
            Las áreas distintas, ordenadas. Lista vacía si todavía no se cargó ninguna — que hoy
            es el caso: `objetivos` tiene una sola fila y su `areas_involucradas` es `'{}'`.
        """
        return self._repo.get_areas_conocidas(empresa_id)

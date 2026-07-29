"""
Resolución de empresa y área del import de nómina, con cache primado desde la base.

Extraído de `nomina_empleados_service.py`, que estaba en 142/150 y no tenía margen para el
resto del fix (sacar lookups redundantes, consolidar auditoría, sumar legajo). La lógica se
movió VERBATIM: normalización por nombre, primado desde la DB y creación al vuelo son idénticos.

Por qué el cache importa más allá de la performance: cada `area_id` que sale de acá está
GARANTIZADO de la empresa que se pidió —o vino de `get_areas(empresa_id)`, o se creó con
`AreaCreate(empresa_id=...)`— y `areas_validadas()` expone ese conjunto para que el write path
no vuelva a preguntárselo a la base fila por fila.

⚠️ El primado es PEREZOSO y por empresa: `_areas_primadas` se llena cuando aparece la primera
fila de esa empresa, no al construir el objeto. Eso es lo que hace que un archivo con una sola
empresa pague 2 queries de áreas en total y no 2 por fila.
"""
from typing import Optional

from schemas.area import AreaCreate
from schemas.empresa import EmpresaCreate
from services._nomina_parsers import normalizar_nombre
from services.area_service import AreaService
from services.empresa_service import EmpresaService


class NominaCatalogos:
    def __init__(self, usuario_id: str, empresas: Optional[EmpresaService] = None,
                 areas: Optional[AreaService] = None) -> None:
        self._usuario_id = usuario_id
        self._empresas = empresas or EmpresaService()
        self._areas = areas or AreaService()
        self._cache_empresa: dict[str, str] = {}
        self._cache_area: dict[tuple, str] = {}
        self._empresas_primadas = False
        self._areas_primadas: set[str] = set()

    def empresa_id(self, nombre: str) -> str:
        """Crea o reusa la empresa por nombre normalizado (guarda el nombre original). Cachea."""
        clave = normalizar_nombre(nombre)
        if not self._empresas_primadas:
            for e in self._empresas.list_empresas().items:
                self._cache_empresa.setdefault(normalizar_nombre(e.nombre), e.id)
            self._empresas_primadas = True
        if clave not in self._cache_empresa:
            empresa = self._empresas.create_empresa(EmpresaCreate(nombre=nombre.strip()), self._usuario_id)
            self._cache_empresa[clave] = empresa.id
        return self._cache_empresa[clave]

    def area_id(self, empresa_id: str, nombre: str) -> str:
        """Crea o reusa el área por (empresa, nombre normalizado). Cachea."""
        clave = (empresa_id, normalizar_nombre(nombre))
        if empresa_id not in self._areas_primadas:
            for a in self._areas.get_areas(empresa_id):
                self._cache_area.setdefault((empresa_id, normalizar_nombre(a.nombre)), a.id)
            self._areas_primadas.add(empresa_id)
        if clave not in self._cache_area:
            area = self._areas.create_area(
                AreaCreate(empresa_id=empresa_id, nombre=nombre.strip()), self._usuario_id)
            self._cache_area[clave] = area.id
        return self._cache_area[clave]

    def areas_validadas(self) -> frozenset:
        """Ids de área que este objeto ya probó pertenecientes a su empresa (ver encabezado).

        Se le pasa al write path como `areas_validadas` para que no re-consulte la base por un
        área que se resolvió dos líneas antes. NO es un flag que apague la validación: es el
        RESULTADO de la validación, obtenido en la misma operación.
        """
        return frozenset(self._cache_area.values())

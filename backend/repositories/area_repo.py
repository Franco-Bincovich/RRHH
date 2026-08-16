"""
Repositorio de áreas. Acceso directo a Supabase con supabase_admin.
Interfaz pública: find_pagina (el listado) · find_all (el catálogo completo) · find_by_id ·
save · update · delete

Las primitivas —tabla, SELECT, conteo de empleados y mapper— viven en `_area_row.py`: este
archivo estaba en 100/100 cuando le tocaba sumar la paginación y el filtro de búsqueda.
"""
from typing import List, Optional, Tuple

from integrations.supabase_client import supabase_admin
from repositories._area_row import SELECT as _SELECT
from repositories._area_row import TABLE as _TABLE
from repositories._area_row import base as _base
from repositories._area_row import counts_by_area as _counts_by_area
from repositories._area_row import to_response as _to_response
from schemas.area import AreaCreate, AreaResponse, AreaUpdate


class AreaRepo:
    def find_all(self, empresa_id: Optional[str] = None,
                 search: Optional[str] = None) -> List[AreaResponse]:
        """TODAS las áreas activas del filtro, sin paginar.

        🔴 NO PAGINA A PROPÓSITO: es el catálogo que alimenta los ~15 selectores de área del
        front (`/api/areas/opciones`) y la resolución nombre→id del import de nómina
        (`_nomina_catalogos`). Paginarlo acá habría dejado cada dropdown mostrando 20 de ~180,
        sin error y sin aviso. La pantalla de gestión usa `find_pagina`.
        """
        res = _base(empresa_id, search, contar=False).order("nombre").execute()
        counts = _counts_by_area()
        return [_to_response(r, counts) for r in (res.data or [])]

    def find_pagina(self, empresa_id: Optional[str] = None, search: Optional[str] = None,
                    page: int = 1, page_size: int = 20) -> Tuple[List[AreaResponse], int]:
        """Una página del listado de gestión + el total REAL del filtro.

        `.order("id")` = desempate. `nombre` NO es único: las áreas son POR empresa y dos
        sociedades del grupo pueden tener cada una su "Sistemas" — en el padrón de escala 40 de
        58 nombres están repetidos. Sin el desempate, en modo consolidado esas homónimas se
        reordenan entre consultas y una puede salir en dos páginas o en ninguna.
        ASC, que es la forma que tendría `(empresa_id, nombre, id)` si se agrega el índice.
        """
        res = (_base(empresa_id, search, contar=True).order("nombre").order("id")
               .range((page - 1) * page_size, page * page_size - 1).execute())
        counts = _counts_by_area()
        return [_to_response(r, counts) for r in (res.data or [])], (res.count or 0)

    def find_by_id(self, id: str, empresa_id: Optional[str] = None) -> Optional[AreaResponse]:
        """Área activa por id. Si empresa_id se provee, valida pertenencia (None = consolidado).

        maybe_single (no single): con .single() Supabase LANZA cuando no hay filas, así que el
        `return None` de abajo era inalcanzable y un id inexistente daba 500 en vez de 404. Con
        el filtro de empresa eso se volvía la respuesta normal para toda área ajena.
        """
        q = supabase_admin.table(_TABLE).select(_SELECT).eq("id", id).eq("activo", True)
        if empresa_id:
            q = q.eq("empresa_id", empresa_id)
        res = q.maybe_single().execute()
        if not res or not res.data:
            return None
        return _to_response(res.data, _counts_by_area())

    def save(self, data: AreaCreate) -> AreaResponse:
        # 🔴 `mode="json"` NO es cosmético: con `empresa_id: UUID`, un `model_dump()` pelado
        # devuelve el objeto y el cliente de Supabase no lo sabe serializar.
        payload = data.model_dump(exclude_none=True, mode="json")
        res = supabase_admin.table(_TABLE).insert(payload).execute()
        counts = _counts_by_area()
        return _to_response(res.data[0], counts)

    def update(self, id: str, data: AreaUpdate, empresa_id: Optional[str] = None) -> Optional[AreaResponse]:
        """Actualización parcial. empresa_id restringe el WHERE (None = consolidado)."""
        # `mode="json"` por lo mismo que `save`: `responsable_id` es UUID (verificado ejecutando).
        patch = data.model_dump(exclude_none=True, mode="json")
        if not patch:
            return self.find_by_id(id, empresa_id)
        q = supabase_admin.table(_TABLE).update(patch).eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", empresa_id)
        res = q.execute()
        if not res.data:
            return None
        counts = _counts_by_area()
        return _to_response(res.data[0], counts)

    def delete(self, id: str, empresa_id: Optional[str] = None) -> bool:
        """Soft delete (activo=False). empresa_id restringe el WHERE (None = consolidado)."""
        q = supabase_admin.table(_TABLE).update({"activo": False}).eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", empresa_id)
        return bool(q.execute().data)

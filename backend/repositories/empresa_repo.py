"""
Repositorio de empresas. Acceso directo a Supabase con supabase_admin.
Interfaz pública: find_all · find_by_id · save · update · set_logo_url
"""
from typing import List, Optional

from integrations.supabase_client import supabase_admin
from schemas.empresa import EmpresaCreate, EmpresaResponse, EmpresaUpdate

_TABLE = "empresas"
_SELECT = (
    "id, nombre, razon_social, cuit, direccion, telefono, "
    "email, logo_url, activa, created_at, updated_at"
)


def _to_response(row: dict) -> EmpresaResponse:
    return EmpresaResponse(
        id=str(row["id"]),
        nombre=row["nombre"],
        razon_social=row.get("razon_social"),
        cuit=row.get("cuit"),
        direccion=row.get("direccion"),
        telefono=row.get("telefono"),
        email=row.get("email"),
        logo_url=row.get("logo_url"),
        activa=row.get("activa", True),
        created_at=row["created_at"],
        updated_at=row.get("updated_at"),
    )


class EmpresaRepo:
    def find_all(self) -> List[EmpresaResponse]:
        """Retorna todas las empresas ordenadas por nombre."""
        res = (
            supabase_admin.table(_TABLE)
            .select(_SELECT)
            .order("nombre")
            .execute()
        )
        return [_to_response(r) for r in (res.data or [])]

    def find_all_ids(self) -> List[str]:
        """Retorna solo los IDs de todas las empresas, activas e inactivas.

        Query deliberadamente mínima —una columna, sin orden ni joins— porque la consume el
        caché que valida el header X-Empresa-Id, en el camino de autenticación de cada request.
        Incluye las inactivas a propósito: responde "¿este UUID es una empresa real?", no
        "¿está habilitada?". Ver utils/empresas_cache.py.
        """
        res = supabase_admin.table(_TABLE).select("id").execute()
        return [str(r["id"]) for r in (res.data or [])]

    def find_by_id(self, id: str) -> Optional[EmpresaResponse]:
        """Retorna una empresa por ID. None si no existe.

        maybe_single (no single): con .single() Supabase LANZA cuando no hay filas, así que el
        `else None` era inalcanzable y un id inexistente daba 500 en vez del 404 EMPRESA_NOT_FOUND
        que el service pretende devolver. Mismo defecto que tenía area_repo (sesión C).
        """
        res = (
            supabase_admin.table(_TABLE)
            .select(_SELECT)
            .eq("id", id)
            .maybe_single()
            .execute()
        )
        return _to_response(res.data) if res and res.data else None

    def save(self, data: EmpresaCreate) -> EmpresaResponse:
        """Inserta una nueva empresa y retorna el registro creado."""
        payload = data.model_dump(exclude_none=True)
        res = supabase_admin.table(_TABLE).insert(payload).execute()
        return _to_response(res.data[0])

    def update(self, id: str, data: EmpresaUpdate) -> Optional[EmpresaResponse]:
        """Actualiza campos no-None de una empresa existente."""
        patch = data.model_dump(exclude_none=True)
        if not patch:
            return self.find_by_id(id)
        res = (
            supabase_admin.table(_TABLE)
            .update(patch)
            .eq("id", id)
            .execute()
        )
        return _to_response(res.data[0]) if res.data else None

    def set_logo_url(self, id: str, logo_url: str) -> Optional[EmpresaResponse]:
        """Actualiza únicamente el logo_url de una empresa."""
        res = (
            supabase_admin.table(_TABLE)
            .update({"logo_url": logo_url})
            .eq("id", id)
            .execute()
        )
        return _to_response(res.data[0]) if res.data else None

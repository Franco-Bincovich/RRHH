"""Repositorio del audit log. Acceso a Supabase con supabase_admin."""
from datetime import date
from typing import List, Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.auditoria import AuditLogResponse
from utils.logger import logger

_T = "auditoria"


def _build(rows: List[dict]) -> List[AuditLogResponse]:
    """Enriquece filas de auditoría con el nombre del usuario y de la empresa.

    Resuelve los joins a mano (no hay FKs expandidas): junta los ids del page y
    consulta users/empresas en una sola query cada uno. usuario_nombre/empresa_nombre
    quedan None si el id es NULL o no se encuentra (p. ej. usuario borrado)."""
    if not rows:
        return []
    user_ids = list({r["usuario_id"] for r in rows if r.get("usuario_id")})
    emp_ids = list({r["empresa_id"] for r in rows if r.get("empresa_id")})

    user_map: dict = {}
    if user_ids:
        user_map = {
            u["id"]: f"{u['nombre']} {u['apellido']}"
            for u in (supabase_admin.table("users").select("id, nombre, apellido")
                      .in_("id", user_ids).execute().data or [])
        }
    emp_map: dict = {}
    if emp_ids:
        emp_map = {
            e["id"]: e["nombre"]
            for e in (supabase_admin.table("empresas").select("id, nombre")
                      .in_("id", emp_ids).execute().data or [])
        }

    return [
        AuditLogResponse.model_validate({
            **r,
            # Filas legacy (trigger viejo fn_auditoria) traen entidad/evento en NULL:
            # 'tabla' es el nombre viejo de 'entidad' (mapeo directo); 'accion' (NOT NULL)
            # es el fallback honesto de 'evento', que no existía en el modelo viejo.
            "entidad": r.get("entidad") or r.get("tabla"),
            "evento": r.get("evento") or r.get("accion"),
            "usuario_nombre": user_map.get(r.get("usuario_id")),
            "empresa_nombre": emp_map.get(r.get("empresa_id")),
        })
        for r in rows
    ]


class AuditRepo:
    def registrar(self, payload: dict) -> None:
        """Inserta un evento en auditoria. No propaga: si el insert viene vacío, loguea."""
        res = supabase_admin.table(_T).insert(payload).execute()
        if not res.data:
            logger.error("audit_insert_vacio", extra={"evento": payload.get("evento")})

    def listar(
        self,
        empresa_id: Optional[UUID] = None,
        usuario_id: Optional[UUID] = None,
        entidad: Optional[str] = None,
        evento: Optional[str] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
        registro_id: Optional[str] = None,
    ) -> Tuple[List[AuditLogResponse], int]:
        """Retorna (página de eventos ordenados por created_at desc, total real del filtro).

        Filtros opcionales por empresa, usuario, entidad, evento, registro_id y rango de
        fechas (fecha_hasta incluye todo el día). Resuelve nombre de usuario y empresa."""
        # `.order("id")` = desempate. Es el listado donde mas importa: una importacion emite su
        # evento por LOTE y varios eventos comparten `created_at` al milisegundo, asi que sin el
        # desempate paginar la auditoria puede mostrar dos veces el mismo evento o esconderlo.
        # `id` ASC aunque la fecha vaya DESC — forma del indice `idx_auditoria_empresa_created`.
        q = supabase_admin.table(_T).select("*", count="exact").order("created_at", desc=True).order("id")
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        if usuario_id:
            q = q.eq("usuario_id", str(usuario_id))
        if entidad:
            q = q.eq("entidad", entidad)
        if registro_id:
            q = q.eq("registro_id", registro_id)
        if evento:
            q = q.eq("evento", evento)
        if fecha_desde:
            q = q.gte("created_at", str(fecha_desde))
        if fecha_hasta:
            q = q.lte("created_at", f"{fecha_hasta}T23:59:59.999999")
        res = q.range((page - 1) * page_size, page * page_size - 1).execute()
        return _build(res.data or []), res.count or 0

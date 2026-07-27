"""
Repositorio de campañas y links de assessment — queries Supabase.
Interfaz: get_campanas · get_campana · create_campana · create_link · get_link_by_token
"""
import uuid
from typing import Any, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.assessment import CampanaCreate, CampanaResponse, LinkCreate, LinkResponse
from utils.errors import AppError

_CAMP, _LINK = "assessment_campanas", "assessment_links"
_CAMP_Q = "*, empresa_id, empresas(nombre), areas!assessment_campanas_area_id_fkey(nombre)"
_TIPO_TO   = {"completo": "mixto"}
_TIPO_FROM = {"mixto": "completo"}


def _with_empresa(q, empresa_id: Optional[UUID]):
    return q.eq("empresa_id", str(empresa_id)) if empresa_id else q


def _t_db(t: str) -> str: return _TIPO_TO.get(t, t)
def _t_api(t: str) -> str: return _TIPO_FROM.get(t, t)


def _camp_row(r: dict, total: int = 0, done: int = 0) -> CampanaResponse:
    area = r.get("areas") or {}
    empresa = r.get("empresas") or {}
    return CampanaResponse(
        id=r["id"], nombre=r["nombre"], tipo=_t_api(r["tipo"]),
        estado=r["estado"], links_enviados=total, completados=done,
        created_at=r["created_at"], empresa_id=r.get("empresa_id"),
        empresa_nombre=empresa.get("nombre"), area_id=r.get("area_id"),
        area_nombre=area.get("nombre"), posicion_objetivo=r.get("posicion_objetivo"),
    )


def _link_row(r: dict) -> LinkResponse:
    return LinkResponse(
        id=r["id"], campana_id=r["campana_id"], token=r["token"],
        evaluado_nombre=r.get("nombre_destino") or "",
        evaluado_email=r.get("email_destino") or "",
        completado=r.get("estado") == "completado", created_at=r["created_at"],
    )


class AssessmentCampanasRepo:
    def _counts(self, cid: str) -> tuple:
        rows = (supabase_admin.table(_LINK).select("estado").eq("campana_id", cid).execute().data or [])
        return len(rows), sum(1 for x in rows if x["estado"] == "completado")

    def get_campanas(self, empresa_id: Optional[UUID] = None) -> list:
        q = supabase_admin.table(_CAMP).select(_CAMP_Q).order("created_at", desc=True)
        return [_camp_row(r, *self._counts(r["id"])) for r in (_with_empresa(q, empresa_id).execute().data or [])]

    def get_campana(self, campana_id: str, empresa_id: Optional[UUID] = None) -> CampanaResponse:
        q = supabase_admin.table(_CAMP).select(_CAMP_Q).eq("id", campana_id)
        res = _with_empresa(q, empresa_id).maybe_single().execute()
        if not (res and res.data):
            raise AppError("Campaña no encontrada", "CAMPANA_NOT_FOUND", 404)
        return _camp_row(res.data, *self._counts(campana_id))

    def create_campana(self, data: CampanaCreate) -> CampanaResponse:
        payload: dict[str, Any] = {
            "nombre": data.nombre, "tipo": _t_db(data.tipo),
            "estado": "activa", "empresa_id": str(data.empresa_id),
        }
        if data.area_id:
            payload["area_id"] = data.area_id
        if data.posicion_objetivo:
            payload["posicion_objetivo"] = data.posicion_objetivo
        ins = supabase_admin.table(_CAMP).insert(payload).execute()
        if not ins.data:
            raise AppError("Error al crear campaña", "DB_ERROR", 500)
        return self.get_campana(ins.data[0]["id"])

    def create_link(self, data: LinkCreate) -> LinkResponse:
        token = uuid.uuid4().hex + uuid.uuid4().hex
        payload: dict[str, Any] = {
            "campana_id": str(data.campana_id), "email_destino": data.evaluado_email,
            "nombre_destino": data.evaluado_nombre, "token": token,
        }
        if data.empleado_id:
            payload["empleado_id"] = data.empleado_id
        ins = supabase_admin.table(_LINK).insert(payload).execute()
        if not ins.data:
            raise AppError("Error al crear link", "DB_ERROR", 500)
        return _link_row(ins.data[0])

    def get_link_by_token(self, token: str) -> Optional[LinkResponse]:
        res = supabase_admin.table(_LINK).select("*").eq("token", token).maybe_single().execute()
        return _link_row(res.data) if (res and res.data) else None

    def mark_link_completed(self, link_id: str) -> None:
        supabase_admin.table(_LINK).update({"estado": "completado"}).eq("id", link_id).execute()

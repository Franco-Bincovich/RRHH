"""
Repositorio de resultados de assessment — queries Supabase.
Interfaz: get_resultados · get_resultado · save_resultado
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.assessment import ResultadoResponse
from utils.errors import AppError

_LINK, _RES = "assessment_links", "assessment_resultados"
_RES_Q = (
    "*, empresa_id, empresas(nombre), "
    "assessment_links(nombre_destino, email_destino, campana_id, empleado_id, "
    "assessment_campanas(tipo, posicion_objetivo, areas!assessment_campanas_area_id_fkey(nombre)))"
)
_TIPO_FROM = {"mixto": "completo"}


def _with_empresa(q, empresa_id: Optional[UUID]):
    return q.eq("empresa_id", str(empresa_id)) if empresa_id else q


def _t_api(t: str) -> str: return _TIPO_FROM.get(t, t)
def _nivel(score: int) -> str: return "alto" if score > 70 else ("bajo" if score < 40 else "medio")


def _res_row(r: dict) -> ResultadoResponse:
    lnk       = r.get("assessment_links") or {}
    camp      = lnk.get("assessment_campanas") or {}
    camp_area = camp.get("areas") or {}
    empresa   = r.get("empresas") or {}
    pun       = r.get("puntuacion") or {}
    perf      = r.get("perfil_resultado") or {}
    return ResultadoResponse(
        id=r["id"], link_id=r["link_id"],
        empresa_id=r.get("empresa_id"), empresa_nombre=empresa.get("nombre"),
        evaluado_nombre=lnk.get("nombre_destino") or "",
        tipo=_t_api(camp.get("tipo") or ""),
        fecha_completado=str(r["completado_en"]) if r.get("completado_en") else None,
        perfil_dominante=perf.get("perfil_dominante"),
        score_general=pun.get("general"), scores=pun,
        area_nombre=camp_area.get("nombre"),
        posicion_objetivo=camp.get("posicion_objetivo"),
    )


class AssessmentResultadosRepo:
    def get_resultados(self, empresa_id: Optional[UUID] = None) -> list:
        q = supabase_admin.table(_RES).select(_RES_Q).order("created_at", desc=True)
        return [_res_row(r) for r in (_with_empresa(q, empresa_id).execute().data or [])]

    def get_resultado(self, resultado_id: str, empresa_id: Optional[UUID] = None) -> ResultadoResponse:
        q = supabase_admin.table(_RES).select(_RES_Q).eq("id", resultado_id)
        res = _with_empresa(q, empresa_id).maybe_single().execute()
        if not (res and res.data):
            raise AppError("Resultado no encontrado", "RESULTADO_NOT_FOUND", 404)
        return _res_row(res.data)

    def save_resultado(self, link_id: str, campana_id: str, respuestas: list,
                       puntuacion: dict, perfil_resultado: dict, empresa_id: str = "") -> ResultadoResponse:
        """Persiste el resultado, actualiza el link a completado y actualiza el 9-box del empleado."""
        now = datetime.now(timezone.utc).isoformat()
        payload: dict = {
            "link_id": link_id, "campana_id": campana_id, "respuestas": respuestas,
            "puntuacion": puntuacion, "perfil_resultado": perfil_resultado, "completado_en": now,
        }
        if empresa_id:
            payload["empresa_id"] = empresa_id
        ins = supabase_admin.table(_RES).insert(payload).execute()
        if not ins.data:
            raise AppError("Error al guardar resultado", "DB_ERROR", 500)
        supabase_admin.table(_LINK).update({"estado": "completado"}).eq("id", link_id).execute()
        self._actualizar_ninebox(link_id, puntuacion)
        return self.get_resultado(ins.data[0]["id"])

    def _actualizar_ninebox(self, link_id: str, puntuacion: dict) -> None:
        """Actualiza potencial y desempeño del empleado en el mapa 9-Box a partir del assessment."""
        lk = supabase_admin.table(_LINK).select("empleado_id").eq("id", link_id).maybe_single().execute()
        emp_id = (lk.data or {}).get("empleado_id") if lk else None
        if not emp_id:
            return
        s = puntuacion or {}
        pot = _nivel((s.get("apertura", 0) + s.get("responsabilidad", 0)) // 2)
        desemp = _nivel(s.get("general", 0))
        supabase_admin.table("empleados").update({"potencial": pot, "desempeno": desemp}).eq("id", emp_id).execute()

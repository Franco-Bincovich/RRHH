"""
Repositorio de sucesión — mapa de talento y análisis por posición.
Interfaz: get_mapa_talento · get_analisis_posicion
Planes de carrera e hitos → ver planes_carrera_repo.py
"""
import json
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.sucesion import EmpleadoAnalisisResponse, EmpleadoMapaResponse

_EMP = "empleados"
_ASSESS = "assessment_resultados"
_AREA = "areas!empleados_area_id_fkey(nombre)"


def _with_empresa(q, empresa_id: Optional[UUID]):
    return q.eq("empresa_id", str(empresa_id)) if empresa_id else q


def _mapa_row(r: dict) -> EmpleadoMapaResponse:
    area = r.get("areas") or {}
    empresa = r.get("empresas") or {}
    return EmpleadoMapaResponse(
        id=r["id"], nombre=r["nombre"], apellido=r["apellido"],
        cargo=(r.get("roles") or [r.get("cargo")])[0], area_id=r.get("area_id"), area_nombre=area.get("nombre"),
        empresa_id=r.get("empresa_id"), empresa_nombre=empresa.get("nombre"),
        potencial=r.get("potencial", "medio"), desempeno=r.get("desempeno", "medio"),
    )


def _parse_json_field(value):
    """Parsea un campo JSONB que Supabase puede devolver como string en vez de dict/list."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return None
    return value


def _score_de(puntuacion) -> Optional[int]:
    """Score general del assessment. None si no hay puntuación usable (mismo criterio de siempre)."""
    p = _parse_json_field(puntuacion) or {}
    sg = p.get("general") or p.get("total")
    try:
        return int(sg) if sg is not None else None
    except (ValueError, TypeError):
        return None


def _recencia(r: dict) -> tuple:
    """Clave de 'más reciente': los sin completado_en pierden. No se asume orden dentro del in_."""
    c = r.get("completado_en")
    return (c is not None, c or "")


def _scores_por_empleado(ids: list) -> dict:
    """empleado_id → score del assessment más reciente, en UNA sola query (evita el N+1). {} si no
    hay ids: nunca dispara la query con lista vacía. El empleado sin resultado no entra al dict →
    score None, igual que cuando la query por empleado volvía vacía."""
    if not ids:
        return {}
    data = supabase_admin.table(_ASSESS).select(
        "empleado_id, puntuacion, completado_en"
    ).in_("empleado_id", ids).execute().data or []
    ultimos: dict = {}
    for r in data:
        emp, prev = r.get("empleado_id"), ultimos.get(r.get("empleado_id"))
        if emp and (prev is None or _recencia(r) > _recencia(prev)):
            ultimos[emp] = r
    return {emp: _score_de(r.get("puntuacion")) for emp, r in ultimos.items()}


class SucesionRepo:
    def get_mapa_talento(self, empresa_id: Optional[UUID] = None) -> list[EmpleadoMapaResponse]:
        q = supabase_admin.table(_EMP).select(
            f"id,empresa_id,nombre,apellido,roles,area_id,potencial,desempeno,{_AREA},empresas(nombre)"
        ).eq("estado", "activo")
        return [_mapa_row(r) for r in (_with_empresa(q, empresa_id).execute().data or [])]

    def get_analisis_posicion(self, area_id: str, empresa_id: Optional[UUID] = None) -> list[EmpleadoAnalisisResponse]:
        q = supabase_admin.table(_EMP).select(
            "id, nombre, apellido, roles, potencial, desempeno"
        ).eq("area_id", area_id).neq("estado", "baja")
        emps = _with_empresa(q, empresa_id).execute().data or []
        scores = _scores_por_empleado([r["id"] for r in emps])
        rows = [EmpleadoAnalisisResponse(
            id=r["id"], nombre=r["nombre"], apellido=r["apellido"],
            cargo=(r.get("roles") or [r.get("cargo")])[0], score=scores.get(r["id"]),
            potencial=r.get("potencial"), desempeno=r.get("desempeno"),
        ) for r in emps]
        rows.sort(key=lambda x: (x.score is None, -(x.score or 0)))
        return rows

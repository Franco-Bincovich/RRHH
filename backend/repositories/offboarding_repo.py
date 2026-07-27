"""
Repositorio de offboarding — queries Supabase.
Interfaz: find_activos · find_by_empleado · create_offboarding · update_activo
"""
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.offboarding import ActivoResponse, OffboardingCreate, OffboardingResponse
from utils.errors import AppError

_OI = "offboarding_instancias"
_OA = "offboarding_activos"
_EJ = "empleados!offboarding_instancias_empleado_id_fkey(nombre,apellido), empresas(nombre)"
_EXCL = ["completado", "cancelado"]
_DEFAULT_ACTIVOS = [
    ("laptop",            "Computadora portátil de trabajo"),
    ("tarjeta_acceso",    "Tarjeta de acceso al edificio"),
    ("licencia_software", "Licencias de software corporativo"),
    ("celular",           "Teléfono corporativo"),
]


def _with_empresa(q, empresa_id: Optional[UUID]):
    return q.eq("empresa_id", str(empresa_id)) if empresa_id else q


def _activo_row(r: dict) -> ActivoResponse:
    return ActivoResponse(
        id=r["id"], tipo_activo=r["tipo_activo"], descripcion=r.get("descripcion"),
        estado=r["estado"], devuelto=r["estado"] == "devuelto",
    )


def _inst_row(r: dict, activos: list) -> OffboardingResponse:
    emp = r.get("empleados") or {}
    empresa = r.get("empresas") or {}
    total = len(activos)
    devueltos = sum(1 for a in activos if a.get("estado") == "devuelto")
    return OffboardingResponse(
        id=r["id"], empleado_id=r["empleado_id"],
        empresa_id=r.get("empresa_id"), empresa_nombre=empresa.get("nombre"),
        empleado_nombre=f"{emp.get('nombre', '')} {emp.get('apellido', '')}".strip(),
        motivo=r["motivo_egreso"], estado=r["estado"],
        fecha_inicio=str(r.get("created_at", ""))[:10],
        progreso=round(devueltos / total * 100) if total else 0,
        activos=[_activo_row(a) for a in activos], accesos=[],
    )


class OffboardingRepo:
    def _get_activos(self, instancia_id: str) -> list:
        res = supabase_admin.table(_OA).select("*").eq("instancia_id", instancia_id).execute()
        return res.data or []

    def find_activos(self, empresa_id: Optional[UUID] = None) -> list[OffboardingResponse]:
        q = supabase_admin.table(_OI).select(f"*, {_EJ}").not_.in_("estado", _EXCL)
        return [_inst_row(r, self._get_activos(r["id"])) for r in (_with_empresa(q, empresa_id).execute().data or [])]

    def find_by_empleado(self, empleado_id: str, empresa_id: Optional[UUID] = None) -> Optional[OffboardingResponse]:
        q = supabase_admin.table(_OI).select(f"*, {_EJ}").eq("empleado_id", empleado_id).not_.in_("estado", _EXCL).limit(1)
        res = _with_empresa(q, empresa_id).maybe_single().execute()
        if not res.data:
            return None
        return _inst_row(res.data, self._get_activos(res.data["id"]))

    def create_offboarding(self, data: OffboardingCreate, empresa_id: str) -> OffboardingResponse:
        fecha_fin = data.fecha_ultimo_dia or (date.today() + timedelta(days=30))
        ins = supabase_admin.table(_OI).insert({
            "empleado_id": str(data.empleado_id), "motivo_egreso": data.motivo,
            "descripcion_motivo": data.descripcion_motivo, "empresa_id": empresa_id,
            "fecha_ultimo_dia": str(fecha_fin), "estado": "iniciado",
        }).execute()
        if not ins.data:
            raise AppError("Error al crear offboarding", "DB_ERROR", 500)
        inst_id = ins.data[0]["id"]
        supabase_admin.table(_OA).insert([
            {"instancia_id": inst_id, "tipo_activo": t, "descripcion": d, "estado": "pendiente", "empresa_id": empresa_id}
            for t, d in _DEFAULT_ACTIVOS
        ]).execute()
        return _inst_row(ins.data[0], self._get_activos(inst_id))

    def find_instancia_min(self, instancia_id: str, empresa_id: Optional[UUID] = None) -> Optional[dict]:
        """{id, empresa_id} de la instancia, o None si no existe / es de otra empresa. Los activos
        no llevan empresa_id (se alcanzan por instancia_id), así que la barrera va sobre la
        instancia. Devuelve la fila —no un bool— para que el caller reuse su empresa_id."""
        q = supabase_admin.table(_OI).select("id,empresa_id").eq("id", instancia_id)
        res = _with_empresa(q, empresa_id).maybe_single().execute()
        return res.data if res and res.data else None

    def update_activo(self, instancia_id: str, activo_id: str, devuelto: bool) -> bool:
        patch: dict = {"estado": "devuelto" if devuelto else "pendiente"}
        if devuelto:
            patch["fecha_devolucion"] = str(date.today())
        res = supabase_admin.table(_OA).update(patch).eq("id", activo_id).eq(
            "instancia_id", instancia_id
        ).execute()
        return bool(res.data)

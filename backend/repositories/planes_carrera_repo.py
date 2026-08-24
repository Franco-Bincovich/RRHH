"""
Repositorio de planes de carrera e hitos — queries Supabase.
Interfaz: get_planes_carrera · get_plan_by_empleado · create_plan · update_readiness
          get_hitos · create_hito · completar_hito
"""
from datetime import date
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._planes_carrera_hitos import completar as hitos_completar
from repositories._planes_carrera_hitos import crear as hitos_crear
from repositories._planes_carrera_hitos import listar as hitos_listar
from schemas.sucesion import HitoResponse, PlanCarreraCreate, PlanCarreraResponse
from utils.errors import AppError

_PC, _HIT = "planes_carrera", "planes_carrera_hitos"
_EJ = "empleados!planes_carrera_empleado_id_fkey(nombre,apellido,roles)"
# 🔴 `pc_hitos_plan_emp_fkey`: nombre REAL de la FK, y nombrarla es obligatorio (hay dos de hitos a planes). Ver tests/test_selects_repos.py.
_PC_SELECT = f"*, empresa_id, empresas(nombre), {_EJ}, {_HIT}!pc_hitos_plan_emp_fkey(estado)"


def _with_empresa(q, empresa_id: Optional[UUID]):
    return q.eq("empresa_id", str(empresa_id)) if empresa_id else q


def _plan_row(r: dict) -> PlanCarreraResponse:
    emp = r.get("empleados") or {}
    empresa = r.get("empresas") or {}
    hitos = r.get("planes_carrera_hitos") or []
    done = sum(1 for h in hitos if h.get("estado") == "completado")
    return PlanCarreraResponse(
        id=r["id"], empleado_id=r["empleado_id"],
        empresa_id=r.get("empresa_id"), empresa_nombre=empresa.get("nombre"),
        empleado_nombre=f"{emp.get('nombre', '')} {emp.get('apellido', '')}".strip(),
        cargo_actual=(emp.get("roles") or [emp.get("cargo")])[0], cargo_objetivo=r["cargo_objetivo"],
        fecha_objetivo=str(r["fecha_objetivo"]) if r.get("fecha_objetivo") else None,
        readiness=r.get("progreso", 0), hitos_completados=done, hitos_total=len(hitos),
    )


class PlanesCarreraRepo:
    def get_planes_carrera(self, empresa_id: Optional[UUID] = None) -> list[PlanCarreraResponse]:
        q = supabase_admin.table(_PC).select(_PC_SELECT).eq("estado", "activo")
        return [_plan_row(r) for r in (_with_empresa(q, empresa_id).execute().data or [])]

    def get_plan_by_empleado(self, empleado_id: str) -> Optional[PlanCarreraResponse]:
        res = supabase_admin.table(_PC).select(_PC_SELECT).eq(
            "empleado_id", empleado_id
        ).eq("estado", "activo").limit(1).maybe_single().execute()
        return _plan_row(res.data) if (res and res.data) else None

    def get_plan_by_id(self, plan_id: str, empresa_id: Optional[UUID] = None) -> Optional[PlanCarreraResponse]:
        q = supabase_admin.table(_PC).select(_PC_SELECT).eq("id", plan_id)
        res = _with_empresa(q, empresa_id).maybe_single().execute()
        return _plan_row(res.data) if (res and res.data) else None

    def create_plan(self, data: PlanCarreraCreate, empresa_id: str) -> PlanCarreraResponse:
        ins = supabase_admin.table(_PC).insert({
            "empleado_id": str(data.empleado_id), "cargo_objetivo": data.cargo_objetivo,
            "fecha_objetivo": str(data.fecha_objetivo) if data.fecha_objetivo else None,
            "progreso": data.readiness, "empresa_id": empresa_id,
        }).execute()
        if not ins.data:
            raise AppError("Error al crear plan de carrera", "DB_ERROR", 500)
        plan = self.get_plan_by_id(ins.data[0]["id"])
        if not plan:
            raise AppError("Error al recuperar el plan creado", "DB_ERROR", 500)
        return plan

    def update_readiness(self, plan_id: str, readiness: int) -> PlanCarreraResponse:
        upd = supabase_admin.table(_PC).update({"progreso": readiness}).eq("id", plan_id).execute()
        if not upd.data:
            raise AppError("Plan no encontrado", "PLAN_NOT_FOUND", 404)
        plan = self.get_plan_by_id(plan_id)
        if not plan:
            raise AppError("Plan no encontrado", "PLAN_NOT_FOUND", 404)
        return plan

    # Las tres de HITOS delegan en `_planes_carrera_hitos` (extraídas por límite de líneas).
    def get_hitos(self, plan_id: str) -> list[HitoResponse]:
        """Los hitos de un plan. Ver `_planes_carrera_hitos.listar`."""
        return hitos_listar(plan_id)

    def create_hito(self, plan_id: str, titulo: str, descripcion: Optional[str],
                    fecha_objetivo: Optional[str], empresa_id: str,
                    tipo: str = "otro") -> HitoResponse:
        """Alta de un hito. Ver `_planes_carrera_hitos.crear` (ahí está el porqué de `tipo`)."""
        return hitos_crear(plan_id, titulo, descripcion, fecha_objetivo, empresa_id, tipo)

    def completar_hito(self, hito_id: str, empresa_id: Optional[UUID] = None) -> bool:
        """Marca el hito completado. Ver `_planes_carrera_hitos.completar`."""
        return hitos_completar(hito_id, empresa_id)

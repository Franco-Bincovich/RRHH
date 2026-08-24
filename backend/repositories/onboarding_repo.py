"""
Repositorio de onboarding — queries Supabase.
Interfaz: find_instancias_activas · find_instancia_by_empleado · create_instancia
          get_progreso · completar_tarea · get_default_template

Las primitivas compartidas (tablas, SELECT con joins, filtro de empresa, mappers) viven en
_onboarding_row.py.
"""
from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._onboarding_row import (
    EXCLUIDOS, INSTANCIAS, JOIN_EMPLEADO, PROGRESO, TAREAS, TEMPLATES,
    instancia_row, tarea_progreso_row, with_empresa,
)
from repositories._onboarding_templates_filtros import with_visibilidad
from schemas.onboarding import InstanciaDetalleResponse, InstanciaResponse, TemplateResponse
from utils.errors import AppError

_PROGRESO_EMBED = f"{PROGRESO}!onb_prog_instancia_emp_fkey(estado)"


class OnboardingRepo:
    def find_instancias_activas(self, empresa_id: Optional[UUID] = None) -> list[InstanciaResponse]:
        q = supabase_admin.table(INSTANCIAS).select(f"*, {JOIN_EMPLEADO}, {_PROGRESO_EMBED}").not_.in_("estado", EXCLUIDOS)
        return [instancia_row(r) for r in (with_empresa(q, empresa_id).execute().data or [])]

    def find_instancia_by_empleado(self, empleado_id: str, empresa_id: Optional[UUID] = None) -> Optional[InstanciaResponse]:
        q = supabase_admin.table(INSTANCIAS).select(f"*, {JOIN_EMPLEADO}, {_PROGRESO_EMBED}").eq("empleado_id", empleado_id).not_.in_("estado", EXCLUIDOS).limit(1)
        res = with_empresa(q, empresa_id).maybe_single().execute()
        if res is None or not res.data:
            return None
        return instancia_row(res.data)

    def get_progreso(self, instancia_id: str) -> Optional[InstanciaDetalleResponse]:
        inst = supabase_admin.table(INSTANCIAS).select(f"*, {JOIN_EMPLEADO}").eq("id", instancia_id).maybe_single().execute()
        if not (inst and inst.data):
            return None
        progs = supabase_admin.table(PROGRESO).select(f"id,tarea_id,estado,{TAREAS}!onboarding_progreso_tarea_id_fkey(nombre,descripcion,semana,orden)").eq("instancia_id", instancia_id).execute().data or []
        base = instancia_row(inst.data, progs)
        tareas = sorted([tarea_progreso_row(p) for p in progs], key=lambda t: (t.semana, t.orden))
        return InstanciaDetalleResponse(**base.model_dump(), tareas=tareas)

    def create_instancia(self, empleado_id: str, template_id: str, empresa_id: str) -> InstanciaResponse:
        hoy = date.today()
        ins = supabase_admin.table(INSTANCIAS).insert({
            "empleado_id": empleado_id, "template_id": template_id, "empresa_id": empresa_id,
            "estado": "en_progreso", "fecha_inicio": str(hoy),
            "fecha_fin_esperada": str(hoy + timedelta(days=30)),
        }).execute()
        if not ins.data:
            raise AppError("Error al crear onboarding", "DB_ERROR", 500)
        inst_id = ins.data[0]["id"]
        tareas = supabase_admin.table(TAREAS).select("id").eq("template_id", template_id).execute()
        if tareas.data:
            supabase_admin.table(PROGRESO).insert([
                {"instancia_id": inst_id, "tarea_id": t["id"], "estado": "pendiente", "empresa_id": empresa_id}
                for t in tareas.data
            ]).execute()
        return self.find_instancia_by_empleado(empleado_id) or instancia_row(ins.data[0], [])

    def completar_tarea(self, instancia_id: str, tarea_id: str, empresa_id: Optional[UUID] = None) -> bool:
        """Marca completada la tarea. La barrera de empresa va EN EL WHERE (Forma A): una
        instancia ajena no matchea ninguna fila y el UPDATE no escribe nada, así que el 404 de
        arriba y la no-escritura son el MISMO hecho, no dos chequeos que se pueden desincronizar.
        `onboarding_progreso.empresa_id` es NOT NULL, así que el filtro no puede perder filas
        legacy."""
        q = supabase_admin.table(PROGRESO).update({"estado": "completado", "fecha_completada": datetime.utcnow().isoformat()}).eq("instancia_id", instancia_id).eq("tarea_id", tarea_id)
        return bool(with_empresa(q, empresa_id).execute().data)

    def get_default_template(self, empresa_id: Optional[UUID] = None, user_id: Optional[str] = None,
                             rol: Optional[str] = None) -> Optional[TemplateResponse]:
        """Primer template activo VISIBLE de la empresa (plantilla por defecto).

        🔴 EL FILTRO DE VISIBILIDAD ACÁ NO ES UN CONTROL DE ACCESO, ES SEMÁNTICA. Sin él, una
        plantilla que su autor marcó privada podía seguir siendo la que el sistema elige para
        onboardear gente de todo el equipo —basta con que sea la primera activa—, y "privada"
        no habría significado nada en el flujo principal del módulo.

        Reusa `with_visibilidad` de _onboarding_templates_filtros: la regla vive en un solo lugar,
        y este camino no pasa por el repo de templates ni por su service.
        """
        q = supabase_admin.table(TEMPLATES).select("id,empresa_id,nombre,descripcion").eq("activo", True).limit(1)
        res = with_visibilidad(with_empresa(q, empresa_id), user_id, rol).maybe_single().execute()
        if res is None or not res.data:
            return None
        d = res.data
        return TemplateResponse(id=d["id"], nombre=d["nombre"], descripcion=d.get("descripcion"),
                                empresa_id=d.get("empresa_id"), tareas=[])

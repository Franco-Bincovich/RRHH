"""
Repositorio de templates de onboarding — CRUD de templates y tareas.
Interfaz: get_templates · get_template · create_template · update_template
          delete_template · add_tarea · update_tarea · delete_tarea

Las primitivas compartidas (tablas, SELECT con joins, filtro de empresa, mappers) viven en
_onboarding_templates_row.py.
"""
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._onboarding_templates_row import (
    INSTANCIAS, SELECT_DETALLE, SELECT_LISTA, TAREAS, TEMPLATES,
    tarea, template, with_empresa,
)
from schemas.onboarding import TareaResponse, TemplateResponse
from utils.errors import AppError


class OnboardingTemplatesRepo:
    def get_templates(self, empresa_id: Optional[UUID] = None) -> list[TemplateResponse]:
        """Retorna todos los templates activos con conteo de tareas, filtrado por empresa."""
        q = supabase_admin.table(TEMPLATES).select(SELECT_LISTA).eq("activo", True)
        return [template(r) for r in (with_empresa(q, empresa_id).execute().data or [])]

    def get_template(self, template_id: str, empresa_id: Optional[UUID] = None) -> Optional[TemplateResponse]:
        """Retorna un template con todas sus tareas ordenadas por semana y orden."""
        q = supabase_admin.table(TEMPLATES).select(SELECT_DETALLE).eq("id", template_id).eq("activo", True)
        res = with_empresa(q, empresa_id).maybe_single().execute()
        if not (res and res.data):
            return None
        tareas = sorted([tarea(t) for t in (res.data.get(TAREAS) or [])], key=lambda x: (x.semana, x.orden))
        return template(res.data, tareas)

    def create_template(
        self, nombre: str, descripcion: Optional[str], empresa_id: UUID, created_by: Optional[str] = None,
    ) -> TemplateResponse:
        """Crea un template de onboarding asociado a la empresa indicada.

        `created_by` es el usuario que lo crea. Va como None si el caller no pudo determinarlo:
        la columna es nullable y tiene FK a users, así que un placeholder que no sea un UUID
        real haría fallar el insert entero.
        """
        payload = {"nombre": nombre, "descripcion": descripcion, "activo": True,
                   "empresa_id": str(empresa_id), "created_by": created_by}
        res = supabase_admin.table(TEMPLATES).insert(payload).execute()
        if not res.data:
            raise AppError("Error al crear template", "DB_ERROR", 500)
        return template(res.data[0])

    def update_template(self, template_id: str, data: dict) -> Optional[TemplateResponse]:
        """Actualiza nombre y/o descripción de un template."""
        res = supabase_admin.table(TEMPLATES).update(data).eq("id", template_id).eq("activo", True).execute()
        return self.get_template(template_id) if res.data else None

    def delete_template(self, template_id: str) -> bool:
        """Soft delete si tiene instancias; hard delete si no."""
        has_inst = bool(supabase_admin.table(INSTANCIAS).select("id").eq("template_id", template_id).limit(1).execute().data)
        if has_inst:
            supabase_admin.table(TEMPLATES).update({"activo": False}).eq("id", template_id).execute()
        else:
            supabase_admin.table(TEMPLATES).delete().eq("id", template_id).execute()
        return True

    def add_tarea(self, template_id: str, data: dict, empresa_id: str) -> TareaResponse:
        """Agrega una tarea al template, heredando el empresa_id de la plantilla."""
        res = supabase_admin.table(TAREAS).insert({
            "template_id": template_id, "empresa_id": str(empresa_id), "nombre": data["titulo"],
            "descripcion": data.get("descripcion"), "semana": data["semana"],
            "orden": data["orden"], "responsable_tipo": data.get("responsable_tipo", "rrhh"),
            "dias_limite": data.get("dias_limite", 1),
        }).execute()
        if not res.data:
            raise AppError("Error al agregar tarea", "DB_ERROR", 500)
        return tarea(res.data[0])

    def update_tarea(self, tarea_id: str, data: dict) -> Optional[TareaResponse]:
        """Actualiza los campos provistos de una tarea."""
        payload = {k: v for k, v in {"nombre": data.get("titulo"), "descripcion": data.get("descripcion"),
                                      "semana": data.get("semana"), "orden": data.get("orden")}.items() if v is not None}
        if not payload:
            return None
        res = supabase_admin.table(TAREAS).update(payload).eq("id", tarea_id).execute()
        return tarea(res.data[0]) if res.data else None

    def delete_tarea(self, tarea_id: str) -> bool:
        """Elimina una tarea del template."""
        supabase_admin.table(TAREAS).delete().eq("id", tarea_id).execute()
        return True

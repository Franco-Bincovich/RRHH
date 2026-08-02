"""
Repositorio de templates de onboarding — CRUD de templates y tareas.
Interfaz: get_templates · get_template · create_template · update_template
          delete_template · add_tarea · update_tarea · delete_tarea

Las primitivas compartidas viven en tres satélites: `_row` (tablas, SELECT y mappers),
`_filtros` (empresa y visibilidad) y `_write` (las filas que se insertan). Las lecturas componen `with_empresa` y `with_visibilidad` sobre
la misma query, empresa primero; la regla de cada uno está escrita en su función y no se repite
acá, para que no puedan divergir.
"""
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._onboarding_templates_filtros import with_empresa, with_visibilidad
from repositories._onboarding_templates_row import INSTANCIAS, SELECT_DETALLE, SELECT_LISTA, TAREAS, TEMPLATES, tarea, template
from repositories._onboarding_templates_write import payload_tarea, payload_tarea_update, payload_template
from schemas.onboarding import TareaResponse, TemplateResponse
from utils.errors import AppError


class OnboardingTemplatesRepo:
    def get_templates(self, empresa_id: Optional[UUID] = None, user_id: Optional[str] = None,
                      rol: Optional[str] = None) -> list[TemplateResponse]:
        """Templates activos que `user_id` puede ver, con conteo de tareas."""
        q = supabase_admin.table(TEMPLATES).select(SELECT_LISTA).eq("activo", True)
        q = with_visibilidad(with_empresa(q, empresa_id), user_id, rol)
        return [template(r) for r in (q.execute().data or [])]

    def get_template(self, template_id: str, empresa_id: Optional[UUID] = None,
                     user_id: Optional[str] = None, rol: Optional[str] = None) -> Optional[TemplateResponse]:
        """Un template con sus tareas ordenadas, si `user_id` puede verlo.

        Devuelve None indistintamente si no existe, si es de otra empresa o si es privada de
        otro: los tres casos son el mismo 404 aguas arriba (services/_template_scope.py).
        """
        q = supabase_admin.table(TEMPLATES).select(SELECT_DETALLE).eq("id", template_id).eq("activo", True)
        res = with_visibilidad(with_empresa(q, empresa_id), user_id, rol).maybe_single().execute()
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
        res = supabase_admin.table(TEMPLATES).insert(
            payload_template(nombre, descripcion, empresa_id, created_by)).execute()
        if not res.data:
            raise AppError("Error al crear template", "DB_ERROR", 500)
        return template(res.data[0])

    def update_template(self, template_id: str, data: dict, user_id: Optional[str] = None,
                        rol: Optional[str] = None) -> Optional[TemplateResponse]:
        """Actualiza nombre, descripción y/o visibilidad, y relee la fila con sus joins.

        La relectura lleva `user_id` porque el update pudo haber vuelto la plantilla privada:
        sin él, `with_visibilidad` no filtraría (None = sin restricción) y con otro user_id
        devolvería None sobre una fila recién editada legítimamente. El gate de acceso ya
        corrió aguas arriba, en el service.
        """
        res = supabase_admin.table(TEMPLATES).update(data).eq("id", template_id).eq("activo", True).execute()
        return self.get_template(template_id, None, user_id, rol) if res.data else None

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
        res = supabase_admin.table(TAREAS).insert(payload_tarea(template_id, empresa_id, data)).execute()
        if not res.data:
            raise AppError("Error al agregar tarea", "DB_ERROR", 500)
        return tarea(res.data[0])

    def update_tarea(self, tarea_id: str, data: dict) -> Optional[TareaResponse]:
        """Actualiza los campos provistos de una tarea."""
        payload = payload_tarea_update(data)
        if not payload:
            return None
        res = supabase_admin.table(TAREAS).update(payload).eq("id", tarea_id).execute()
        return tarea(res.data[0]) if res.data else None

    def delete_tarea(self, tarea_id: str) -> bool:
        """Elimina una tarea del template."""
        supabase_admin.table(TAREAS).delete().eq("id", tarea_id).execute()
        return True

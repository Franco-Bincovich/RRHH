"""
Servicio de templates de onboarding.
Lógica de negocio para CRUD de templates y sus tareas configurables.

TODO camino que alcanza una plantilla por id pasa por
`services/_template_scope.ensure_template_accesible` — nunca por `self._repo.get_template`
directo. Ese helper aplica empresa ∩ visibilidad y levanta el 404 canónico; el porqué de que
sea un helper libre y no un método de esta clase está en su docstring.
"""
from typing import Optional
from uuid import UUID

from repositories.onboarding_templates_repo import OnboardingTemplatesRepo
from schemas.onboarding import (
    TareaCreate, TareaResponse, TareaUpdate,
    TemplateCreate, TemplateResponse, TemplateUpdate,
)
from services._template_scope import ensure_autor, ensure_template_accesible, template_or_404
from utils.errors import AppError
from utils.logger import logger


class OnboardingTemplatesService:
    def __init__(self, repo: Optional[OnboardingTemplatesRepo] = None) -> None:
        self._repo = repo or OnboardingTemplatesRepo()

    def get_templates(self, empresa_id: Optional[UUID] = None, user_id: Optional[str] = None,
                      rol: Optional[str] = None) -> list[TemplateResponse]:
        """Templates activos de la empresa que `user_id` puede ver (None = todas las empresas)."""
        return self._repo.get_templates(empresa_id, user_id, rol)

    def get_template(self, template_id: UUID, empresa_id: Optional[UUID] = None,
                     user_id: Optional[str] = None, rol: Optional[str] = None) -> TemplateResponse:
        """
        Retorna el detalle de un template con sus tareas ordenadas por semana.

        Raises:
            AppError: TEMPLATE_NOT_FOUND (404) si no existe, está inactivo, es de otra empresa
                o es privada de otro usuario. Los cuatro casos son indistinguibles.
        """
        return ensure_template_accesible(self._repo, template_id, empresa_id, user_id, rol)

    def create_template(self, data: TemplateCreate, created_by: Optional[str] = None) -> TemplateResponse:
        """
        Crea un nuevo template de onboarding asociado a la empresa indicada en el body.

        Nace PÚBLICO (default de la columna, migración 082): compartir es el comportamiento
        actual del módulo y privado es un opt-out deliberado desde el detalle.

        Args:
            data: Nombre, descripción y empresa (la empresa es un dato explícito del form —
                crear es una ACCIÓN, no se toma del header; ver Vista vs Acción en CLAUDE.md).
            created_by: UUID del usuario que lo crea. Es quien podrá volverlo privado.

        Returns:
            TemplateResponse del template recién creado.
        """
        tmpl = self._repo.create_template(data.nombre, data.descripcion, data.empresa_id, created_by)
        logger.info("Template creado", extra={"template_id": str(tmpl.id), "empresa_id": str(data.empresa_id), "created_by": created_by})
        return tmpl

    def update_template(self, template_id: UUID, data: TemplateUpdate, empresa_id: Optional[UUID] = None,
                        user_id: Optional[str] = None, rol: Optional[str] = None) -> TemplateResponse:
        """
        Actualiza nombre, descripción y/o visibilidad del template.

        Cambiar la VISIBILIDAD exige además ser el autor: el resto de la edición es
        colaborativa entre pares de RRHH, pero volver privada la plantilla de otro es una
        acción de un solo sentido (ver `ensure_autor`).

        Raises:
            AppError: TEMPLATE_NOT_FOUND (404) si no lo alcanza por empresa o por visibilidad.
            AppError: TEMPLATE_NO_SOS_AUTOR (403) si toca `es_publica` y no es su autor.
        """
        tmpl = ensure_template_accesible(self._repo, template_id, empresa_id, user_id, rol)  # gate antes de escribir
        payload = {k: v for k, v in data.model_dump().items() if v is not None}
        if "es_publica" in payload:
            ensure_autor(tmpl, user_id)
        if not payload:
            return self.get_template(template_id, empresa_id, user_id, rol)
        # La relectura posterior va con el MISMO user_id: si la plantilla se acaba de volver
        # privada, su autor la sigue alcanzando y la respuesta no queda vacía.
        return template_or_404(self._repo.update_template(str(template_id), payload, user_id, rol))

    def delete_template(self, template_id: UUID, empresa_id: Optional[UUID] = None,
                        user_id: Optional[str] = None, rol: Optional[str] = None) -> bool:
        """
        Elimina el template. Soft delete si tiene instancias asociadas.

        Raises:
            AppError: TEMPLATE_NOT_FOUND (404) si no lo alcanza por empresa o por visibilidad.
        """
        ensure_template_accesible(self._repo, template_id, empresa_id, user_id, rol)  # gate antes del borrado
        self._repo.delete_template(str(template_id))
        logger.info("Template eliminado", extra={"template_id": str(template_id)})
        return True

    def add_tarea(self, template_id: UUID, data: TareaCreate, empresa_id: Optional[UUID] = None,
                  user_id: Optional[str] = None, rol: Optional[str] = None) -> TareaResponse:
        """
        Agrega una tarea a un template existente.

        ⚠️ Este path llamaba a `self._repo.get_template` DIRECTO y era el único de los cinco de
        escritura que no pasaba por el gate del service. Ahora usa el helper como sus hermanos.

        Raises:
            AppError: TEMPLATE_NOT_FOUND (404) si no lo alcanza por empresa o por visibilidad.
        """
        tmpl = ensure_template_accesible(self._repo, template_id, empresa_id, user_id, rol)
        tarea = self._repo.add_tarea(str(template_id), data.model_dump(), str(tmpl.empresa_id))
        logger.info("Tarea agregada al template", extra={"template_id": str(template_id), "tarea_id": str(tarea.id)})
        return tarea

    def update_tarea(self, template_id: UUID, tarea_id: UUID, data: TareaUpdate,
                     empresa_id: Optional[UUID] = None, user_id: Optional[str] = None,
                     rol: Optional[str] = None) -> TareaResponse:
        """
        Actualiza campos de una tarea del template.

        La tarea se alcanza por su template: gatear el template cubre la cadena tarea → template
        → (empresa ∩ visibilidad); las tareas no se resuelven sueltas.

        Raises:
            AppError: TEMPLATE_NOT_FOUND (404) si no lo alcanza por empresa o por visibilidad.
            AppError: TAREA_NOT_FOUND (404) si la tarea no existe.
        """
        ensure_template_accesible(self._repo, template_id, empresa_id, user_id, rol)  # gate antes de escribir
        tarea = self._repo.update_tarea(str(tarea_id), data.model_dump(exclude_none=True))
        if not tarea:
            raise AppError("Tarea no encontrada", "TAREA_NOT_FOUND", 404)
        return tarea

    def delete_tarea(self, template_id: UUID, tarea_id: UUID, empresa_id: Optional[UUID] = None,
                     user_id: Optional[str] = None, rol: Optional[str] = None) -> bool:
        """
        Elimina una tarea del template, previa validación sobre el template padre.

        Raises:
            AppError: TEMPLATE_NOT_FOUND (404) si no lo alcanza por empresa o por visibilidad.
        """
        ensure_template_accesible(self._repo, template_id, empresa_id, user_id, rol)  # gate antes del borrado
        self._repo.delete_tarea(str(tarea_id))
        logger.info("Tarea eliminada", extra={"template_id": str(template_id), "tarea_id": str(tarea_id)})
        return True

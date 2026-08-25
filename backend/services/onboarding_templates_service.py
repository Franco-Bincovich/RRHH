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
from services._limite_export import verificar_limite_export
from services._onboarding_templates_export import construir_filas_export
from services._onboarding_templates_tareas import add_tarea as _add_tarea
from services._onboarding_templates_tareas import delete_tarea as _delete_tarea
from services._onboarding_templates_tareas import update_tarea as _update_tarea
from services._template_scope import ensure_autor, ensure_template_accesible, template_or_404
from services.export import Descarga, build_export
from services._audit_payloads_onboarding_templates import (
    payload_alta_template, payload_baja_template, payload_update_template,
)
from services.audit_service import AuditService
from utils.logger import logger


class OnboardingTemplatesService:
    def __init__(self, repo: Optional[OnboardingTemplatesRepo] = None,
                 audit: Optional[AuditService] = None) -> None:
        self._repo = repo or OnboardingTemplatesRepo()
        self._audit = audit or AuditService()

    def get_templates(self, empresa_id: Optional[UUID] = None, user_id: Optional[str] = None,
                      rol: Optional[str] = None) -> list[TemplateResponse]:
        """Templates activos de la empresa que `user_id` puede ver (None = todas las empresas)."""
        return self._repo.get_templates(empresa_id, user_id, rol)

    def exportar(self, empresa_id: Optional[UUID] = None, user_id: Optional[str] = None,
                 rol: Optional[str] = None, formato: str = "excel") -> Descarga:
        """Exporta las plantillas que ESTE usuario ve, con columnas legibles (sin UUIDs).

        🔴 `user_id` y `rol` NO son opcionales de hecho, aunque la firma los deje en None: van
        al mismo `get_templates` que el listado, y ahí deciden la VISIBILIDAD. Un export que se
        los olvidara traería las plantillas privadas de otros usuarios en un archivo — sin
        error, sin 403 y sin nada en pantalla que lo delate. Es el mismo riesgo que el export
        de /equipo: acá el universo no lo acota un Query, lo acota quién sos.
        """
        items = self._repo.get_templates(empresa_id, user_id, rol)
        verificar_limite_export(len(items))
        datos = {"Plantillas": construir_filas_export(items)}
        return build_export(nombre="Plantillas de onboarding", datos=datos,
                            filename_base="plantillas_onboarding", formato=formato)

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
        self._audit.registrar(**payload_alta_template(tmpl, created_by))
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
        nuevo = template_or_404(self._repo.update_template(str(template_id), payload, user_id, rol))
        self._audit.registrar(**payload_update_template(tmpl, nuevo, user_id))
        return nuevo

    def delete_template(self, template_id: UUID, empresa_id: Optional[UUID] = None,
                        user_id: Optional[str] = None, rol: Optional[str] = None) -> bool:
        """
        Elimina el template. Soft delete si tiene instancias asociadas.

        Raises:
            AppError: TEMPLATE_NOT_FOUND (404) si no lo alcanza por empresa o por visibilidad.
        """
        prior = ensure_template_accesible(self._repo, template_id, empresa_id, user_id, rol)
        # 🔴 El `prior` trae las TAREAS, y son lo que hay que fotografiar: la plantilla ES su
        # lista de tareas, y `onboarding_tareas` no tiene versionado. El modo lo dice el repo,
        # que es el único que sabe si borró o desactivó. Ver el payload.
        modo = self._repo.delete_template(str(template_id))
        self._audit.registrar(**payload_baja_template(prior, modo == "fisica", user_id))
        logger.info("Template eliminado", extra={"template_id": str(template_id), "modo": modo})
        return True

    # Las tres operaciones sobre TAREAS viven en services/_onboarding_templates_tareas.py
    # (extraídas por límite de líneas). El gate del template padre va adentro, no acá.

    def add_tarea(self, template_id: UUID, data: TareaCreate, empresa_id: Optional[UUID] = None,
                  user_id: Optional[str] = None, rol: Optional[str] = None) -> TareaResponse:
        """Agrega una tarea a un template. Ver _onboarding_templates_tareas.add_tarea."""
        return _add_tarea(self._repo, self._audit, template_id, data, empresa_id, user_id, rol)

    def update_tarea(self, template_id: UUID, tarea_id: UUID, data: TareaUpdate,
                     empresa_id: Optional[UUID] = None, user_id: Optional[str] = None,
                     rol: Optional[str] = None) -> TareaResponse:
        """Actualiza una tarea del template. Ver _onboarding_templates_tareas.update_tarea."""
        return _update_tarea(self._repo, self._audit, template_id, tarea_id, data, empresa_id, user_id, rol)

    def delete_tarea(self, template_id: UUID, tarea_id: UUID, empresa_id: Optional[UUID] = None,
                     user_id: Optional[str] = None, rol: Optional[str] = None) -> bool:
        """Elimina una tarea del template. Ver _onboarding_templates_tareas.delete_tarea."""
        return _delete_tarea(self._repo, self._audit, template_id, tarea_id, empresa_id, user_id, rol)

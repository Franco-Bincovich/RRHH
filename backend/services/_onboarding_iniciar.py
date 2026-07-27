"""
Alta de onboarding (extraído para mantener el service ≤150 líneas).

Función libre que recibe los colaboradores (repo, templates_repo, empleado_repo) — mismo molde
que _vacaciones_saldo.calcular_saldo(repo, ...) y _ausencias_write. El service la delega en una
línea. La lógica se movió VERBATIM desde OnboardingService.iniciar_onboarding: resolución de
template, chequeo de empresa empleado↔template y creación de la instancia son idénticos.
"""
from typing import Optional
from uuid import UUID

from schemas.onboarding import InstanciaResponse
from services._empleado_scope import ensure_empleado_de_empresa
from utils.errors import AppError
from utils.logger import logger


def iniciar(repo, templates_repo, empleado_repo, empleado_id: UUID,
            template_id: Optional[UUID] = None, empresa_id: Optional[UUID] = None) -> InstanciaResponse:
    """
    Inicia el onboarding para un empleado.
    Valida que el empleado y el template pertenezcan a la misma empresa.
    Si no se provee template_id, usa el template activo por defecto de la empresa del empleado.

    `empresa_id` (header) es la barrera de a qué empleado se puede apuntar; la empresa en la que
    se escribe se sigue derivando del empleado, como antes. Ownership de rol NO aplica acá:
    Seccion.ONBOARDING no está en MANDOS_MEDIOS_SECCIONES, así que solo llegan admin_rrhh y
    gerencia_lectura, para quienes ids_empleados_visibles no restringe. Por eso se usa
    ensure_empleado_de_empresa y no ensure_empleado_visible.

    El gate va PRIMERO, antes del chequeo de onboarding activo: si fuera después, un empleado de
    otra empresa que ya tiene onboarding respondería 409 en vez de 404 y delataría su existencia.

    Args:
        repo: OnboardingRepo (o doble de test).
        templates_repo: OnboardingTemplatesRepo (o doble de test).
        empleado_repo: EmpleadoRepo (o doble de test).
        empleado_id: UUID del empleado que inicia el onboarding.
        template_id: UUID del template a usar. Opcional; si None usa el por defecto.
        empresa_id: empresa activa del request. None = consolidado, no restringe.

    Returns:
        InstanciaResponse con el onboarding recién creado.

    Raises:
        AppError: EMPLEADO_NOT_FOUND (404) si el empleado no existe o es de otra empresa.
        AppError: ONBOARDING_ALREADY_ACTIVE (409) si el empleado ya tiene un onboarding activo.
        AppError: TEMPLATE_NOT_FOUND (404) si el template especificado o el por defecto no existe.
        AppError: EMPRESA_MISMATCH (422) si el empleado y el template son de distintas empresas.
    """
    empleado = ensure_empleado_de_empresa(empleado_repo, empleado_id, empresa_id)

    # Sin empresa_id a propósito: es un guard de unicidad, y acotarlo podría no ver una instancia
    # existente con empresa drifteada y crear un duplicado. El empleado ya pasó la barrera arriba.
    existente = repo.find_instancia_by_empleado(str(empleado_id))
    if existente:
        raise AppError(
            "El empleado ya tiene un onboarding activo",
            "ONBOARDING_ALREADY_ACTIVE",
            409,
        )

    emp_empresa_uuid = UUID(empleado.empresa_id) if empleado.empresa_id else None

    if template_id:
        template = templates_repo.get_template(str(template_id))
        if not template:
            raise AppError("Template no encontrado", "TEMPLATE_NOT_FOUND", 404)
    else:
        template = repo.get_default_template(emp_empresa_uuid)
        if not template:
            raise AppError(
                "No hay template de onboarding activo configurado para esta empresa",
                "TEMPLATE_NOT_FOUND",
                404,
            )

    if template.empresa_id and empleado.empresa_id and str(template.empresa_id) != empleado.empresa_id:
        raise AppError(
            "El empleado y el template deben pertenecer a la misma empresa",
            "EMPRESA_MISMATCH",
            422,
        )

    empresa_id_str = empleado.empresa_id or str(template.empresa_id or "")
    instancia = repo.create_instancia(str(empleado_id), str(template.id), empresa_id_str)
    logger.info(
        "Onboarding iniciado",
        extra={"empleado_id": str(empleado_id), "instancia_id": str(instancia.id)},
    )
    return instancia

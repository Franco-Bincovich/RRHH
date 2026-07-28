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
from services._template_scope import ensure_template_accesible
from utils.errors import AppError
from utils.logger import logger


def iniciar(repo, templates_repo, empleado_repo, empleado_id: UUID,
            template_id: Optional[UUID] = None, empresa_id: Optional[UUID] = None,
            user_id: Optional[str] = None, rol: Optional[str] = None) -> InstanciaResponse:
    """
    Inicia el onboarding para un empleado.
    Si no se provee template_id, usa el primer template activo VISIBLE de la empresa del empleado.

    `empresa_id` (header) es la barrera de a qué empleado se puede apuntar; la empresa en la que
    se escribe se sigue derivando del empleado, como antes. Ownership de rol NO aplica acá:
    Seccion.ONBOARDING no está en MANDOS_MEDIOS_SECCIONES, así que solo llegan admin_rrhh y
    gerencia_lectura, para quienes ids_empleados_visibles no restringe. Por eso se usa
    ensure_empleado_de_empresa y no ensure_empleado_visible.

    El gate va PRIMERO, antes del chequeo de onboarding activo: si fuera después, un empleado de
    otra empresa que ya tiene onboarding respondería 409 en vez de 404 y delataría su existencia.

    🔴 LA PLANTILLA SE RESUELVE CONTRA LA EMPRESA DEL EMPLEADO, NO CONTRA EL HEADER, y por eso
    ya no existe un EMPRESA_MISMATCH (422). Antes el lookup por id no acotaba por empresa y el
    desajuste se detectaba DESPUÉS, con un status propio — o sea que pedir el id de una
    plantilla de otra empresa devolvía 422 mientras que un id inventado devolvía 404: la
    diferencia confirmaba que esa plantilla existe. Es el mismo oráculo que este archivo ya
    había cerrado en el caso del 409, dos párrafos más arriba. Ahora los dos caminos —id
    explícito y por defecto— filtran por la empresa del empleado ANTES de decidir, así que un
    desajuste es indistinguible de "no existe" y la guarda vieja quedaba, además, inalcanzable
    (`empleados.empresa_id` es NOT NULL, con lo cual la empresa objetivo siempre es concreta).

    Args:
        repo: OnboardingRepo (o doble de test).
        templates_repo: OnboardingTemplatesRepo (o doble de test).
        empleado_repo: EmpleadoRepo (o doble de test).
        empleado_id: UUID del empleado que inicia el onboarding.
        template_id: UUID del template a usar. Opcional; si None usa el por defecto.
        empresa_id: empresa activa del request. None = consolidado, no restringe.
        user_id: usuario que inicia. Sujeto de la visibilidad: una plantilla privada de otro no
            se puede elegir ni explícitamente ni como default.
        rol: rol de ese usuario. `gerencia_lectura` alcanza todas las plantillas.

    Returns:
        InstanciaResponse con el onboarding recién creado.

    Raises:
        AppError: EMPLEADO_NOT_FOUND (404) si el empleado no existe o es de otra empresa.
        AppError: ONBOARDING_ALREADY_ACTIVE (409) si el empleado ya tiene un onboarding activo.
        AppError: TEMPLATE_NOT_FOUND (404) si el template no existe, es de otra empresa que la
            del empleado, es privado de otro usuario, o no hay ninguno por defecto.
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
        # Empresa del EMPLEADO, no del header: es la empresa en la que se va a escribir.
        template = ensure_template_accesible(templates_repo, template_id, emp_empresa_uuid, user_id, rol)
    else:
        template = repo.get_default_template(emp_empresa_uuid, user_id, rol)
        if not template:
            # Mensaje propio y NO el canónico: acá no hay un id ajeno que proteger — el usuario
            # no nombró ninguna plantilla, así que decirle que su empresa no tiene ninguna
            # configurada no filtra nada y es lo único accionable.
            raise AppError(
                "No hay template de onboarding activo configurado para esta empresa",
                "TEMPLATE_NOT_FOUND",
                404,
            )

    empresa_id_str = empleado.empresa_id or str(template.empresa_id or "")
    instancia = repo.create_instancia(str(empleado_id), str(template.id), empresa_id_str)
    logger.info(
        "Onboarding iniciado",
        extra={"empleado_id": str(empleado_id), "instancia_id": str(instancia.id)},
    )
    return instancia

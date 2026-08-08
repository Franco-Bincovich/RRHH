"""
Alta de un proceso de offboarding.

Extraído de `offboarding_service.py`, que estaba en 149/150 y no admitía el endpoint de export.
Molde: `_onboarding_iniciar.py` —el hermano simétrico del módulo de entrada— y
`_offboarding_entrevista.py`, que ya se había separado de este mismo service.

POR QUÉ SALIÓ ESTE MÉTODO: es el único que toca DOS agregados (la instancia de offboarding y la
baja del empleado) y el único con una guarda de estado propia. Los otros son operaciones sobre
una instancia ya creada.

🔴 EL ORDEN DE LOS GATES ES LOAD-BEARING, y por eso viaja completo: la barrera de EMPRESA va
ANTES del chequeo de "ya tiene un offboarding activo". Al revés, un empleado de otra empresa con
un proceso abierto respondería 409 `OFFBOARDING_ALREADY_ACTIVE` en vez de 404 — y ese 409
confirmaría que el empleado existe y que tiene un proceso, que es justo lo que el 404 único
viene a esconder. Es el mismo caso real que ya se corrigió en `_onboarding_iniciar.py`.

⚠️ Vive en `services/`, así que su límite es 150 líneas, como cualquier service. No hereda un
límite más alto por ser un satélite.
"""
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from schemas.offboarding import OffboardingCreate, OffboardingResponse
from services._audit_payloads_offboarding import payload_inicio_offboarding
from services._empleado_scope import ensure_empleado_de_empresa
from utils.errors import AppError
from utils.logger import logger


def iniciar(repo, empleado_repo, audit, data: OffboardingCreate,
            empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None) -> OffboardingResponse:
    """
    Inicia el proceso de offboarding para un empleado.

    La empresa en la que se escribe se hereda del empleado (es un dato del empleado, no del
    contexto de sesión). `empresa_id` del header se usa solo como barrera de a qué empleado se
    puede apuntar; validado eso, ambas coinciden por construcción.

    Crea la instancia y los activos corporativos por defecto a devolver, audita el alta y da de
    baja al empleado. Si la baja falla, el proceso YA quedó creado: se loguea a WARNING y no se
    revierte — dejar el offboarding a medias sería peor que un empleado sin fecha de egreso.

    Args:
        repo: OffboardingRepo (o doble de test).
        empleado_repo: EmpleadoRepo (o doble de test).
        audit: AuditService (o doble de test).
        data: Datos del offboarding — empleado_id, motivo y fecha_ultimo_dia opcional.
        empresa_id: empresa activa del request. Acota A QUÉ EMPLEADO se puede apuntar (no la
            empresa en la que se escribe, que se deriva del empleado). None = todas.

    Returns:
        OffboardingResponse con la instancia creada y activos por defecto.

    Raises:
        AppError: EMPLEADO_NOT_FOUND (404) si el empleado no existe o es de otra empresa.
        AppError: OFFBOARDING_ALREADY_ACTIVE (409) si el empleado ya tiene uno activo.
    """
    empleado = ensure_empleado_de_empresa(empleado_repo, data.empleado_id, empresa_id)

    existente = repo.find_by_empleado(str(data.empleado_id))
    if existente:
        raise AppError(
            "El empleado ya tiene un proceso de offboarding activo",
            "OFFBOARDING_ALREADY_ACTIVE",
            409,
        )

    empresa_id_str = empleado.empresa_id or ""
    offboarding = repo.create_offboarding(data, empresa_id_str)
    audit.registrar(**payload_inicio_offboarding(offboarding, usuario_id, empresa_id_str or None))

    fecha_egreso = data.fecha_ultimo_dia or (date.today() + timedelta(days=30))
    empresa_uuid = UUID(empresa_id_str) if empresa_id_str else None
    if not empleado_repo.dar_de_baja(str(data.empleado_id), fecha_egreso, empresa_uuid):
        logger.warning(
            "Offboarding iniciado pero no se pudo actualizar estado del empleado",
            extra={
                "empleado_id": str(data.empleado_id),
                "instancia_id": str(offboarding.id),
            },
        )

    logger.info(
        "Offboarding iniciado",
        extra={
            "empleado_id": str(data.empleado_id),
            "motivo": data.motivo,
            "instancia_id": str(offboarding.id),
        },
    )
    return offboarding

"""
Registro de la entrevista de salida de un offboarding.

Vive en su propio módulo y no dentro de offboarding_service.py porque ese archivo está en
140/150: el método completo lo cruzaría. Mismo molde que _costos_write.py y _vacaciones_write.py
— función libre que recibe sus colaboradores, y el service delega en una línea, así que el
router y los tests hablan con el service de siempre.

Las columnas `entrevista_salida` y `notas_entrevista` ya existían en la tabla desde su
migración original y nunca se habían expuesto. No hace falta migración: solo cablearlas.
"""
from typing import Optional
from uuid import UUID

from services._audit_payloads_offboarding import payload_entrevista_salida
from utils.errors import AppError


def registrar(repo, audit, instancia_id: UUID, entrevista_salida: bool,
              notas: Optional[str], usuario_id: Optional[str] = None,
              empresa_id: Optional[UUID] = None) -> bool:
    """
    Registra si la entrevista de salida se realizó y sus notas.

    La barrera de empresa va en el UPDATE (el repo la aplica en el WHERE), así que una
    instancia de otra empresa no se toca. El 404 es el MISMO para "no existe" y para "es de
    otra empresa": un código distinto confirmaría que el recurso existe y es ajeno.

    Args:
        repo: OffboardingRepo.
        audit: AuditService.
        instancia_id: UUID de la instancia de offboarding.
        entrevista_salida: si la entrevista se realizó.
        notas: texto libre de la entrevista. None o "" deja la instancia sin notas.
        usuario_id: ID del operador (trazabilidad de audit).
        empresa_id: empresa activa del request. Acota la instancia. None = consolidado.

    Returns:
        True si se registró.

    Raises:
        AppError: OFFBOARDING_NOT_FOUND (404) si la instancia no existe o es de otra empresa.
    """
    if not repo.update_entrevista(str(instancia_id), entrevista_salida, notas or None, empresa_id):
        raise AppError("Offboarding no encontrado", "OFFBOARDING_NOT_FOUND", 404)
    audit.registrar(**payload_entrevista_salida(
        instancia_id, entrevista_salida, notas, usuario_id,
        str(empresa_id) if empresa_id else None,
    ))
    return True

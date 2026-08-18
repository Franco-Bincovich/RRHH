"""
Servicio del puente candidato → empleado. Flujo: router → service → repository → DB.

🔴 POR QUÉ UNA CLASE PROPIA Y NO UN MÉTODO EN `CandidatoService`. Dos razones, y la segunda es
la que manda:

  1. `candidato_service.py` está en **144/150** y no admite un método con docstring. Ese es el
     motivo circunstancial.
  2. El motivo real: **este service compone CUATRO colaboradores** —los repos de candidato y
     vacante, `EmpleadoService` y `AuditService`— y uno de ellos es otro SERVICE, no un repo.
     `CandidatoService` es el service de lectura del módulo de candidatos; colgarle una
     dependencia de `EmpleadoService` lo convertiría en el punto por donde el módulo de
     candidatos conoce al de empleados, que es exactamente lo que este puente existe para
     concentrar en un solo lugar visible.

La clase es fina a propósito: **arma los colaboradores y delega**. La lógica vive en los tres
satélites, que son los que el límite de 150 obligó a separar y los que hay que leer para
entender qué hace el puente:

  · `_candidato_contratar.py`        — EL ACTO: la orquestación y la doble barrera de empresa.
  · `_candidato_contratar_guardas.py` — LAS GUARDAS: las cinco, con el porqué de cada una.
  · `_candidato_contratar_mapeo.py`  — EL MAPEO: de dónde sale cada campo del alta.

⚠️ El alta de empleado NO se reimplementa: se llama a `EmpleadoService.create_empleado`, así que
el puente hereda entero lo que ya está probado (legajo duplicado, área y manager de otra empresa,
la traducción del 23505 a 409 por constraint, y el evento `alta_empleado`).
"""
from typing import Optional
from uuid import UUID

from repositories.candidato_repo import CandidatoRepo
from repositories.vacante_repo import VacanteRepo
from schemas.candidato import ContratarRequest
from schemas.empleado import EmpleadoResponse
from services._candidato_contratar import contratar as _contratar
from services.audit_service import AuditService
from services.empleado_service import EmpleadoService


class ContratacionService:
    def __init__(self, candidato_repo: Optional[CandidatoRepo] = None,
                 vacante_repo: Optional[VacanteRepo] = None,
                 empleado_service: Optional[EmpleadoService] = None,
                 audit: Optional[AuditService] = None) -> None:
        self._candidatos = candidato_repo or CandidatoRepo()
        self._vacantes = vacante_repo or VacanteRepo()
        self._empleados = empleado_service or EmpleadoService()
        self._audit = audit or AuditService()

    def contratar(self, candidato_id: str, data: ContratarRequest,
                  empresa_id: Optional[UUID] = None,
                  usuario_id: Optional[str] = None) -> EmpleadoResponse:
        """Contrata a un candidato en oferta. Delegado a `_candidato_contratar.contratar`.

        Args:
            candidato_id: UUID (str) del candidato.
            data: email corporativo, roles y fecha de ingreso (lo que no se puede derivar).
            empresa_id: empresa activa del request. Acota A QUIÉN se puede apuntar.
            usuario_id: operador, para la trazabilidad de auditoría.

        Returns:
            El empleado creado, en estado `preingreso`.

        Raises:
            AppError: CANDIDATO_NOT_FOUND · VACANTE_NOT_FOUND (404) · CANDIDATO_SIN_VACANTE ·
                CANDIDATO_NO_ESTA_EN_OFERTA · CANDIDATO_NO_CONTRATABLE (409) ·
                FECHA_INGRESO_PASADA (400), más los que hereda del alta de empleado.
        """
        return _contratar(self._candidatos, self._vacantes, self._empleados, self._audit,
                          candidato_id, data, empresa_id, usuario_id)

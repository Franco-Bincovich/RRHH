"""
FASE 6: los mails de la casilla que no se resolvieron solos, y su asignación a mano.

Service propio y no dos métodos más en `CvIngestaService` porque son **casos de uso distintos**:
aquel procesa la casilla entera sin intervención y este le muestra a RRHH lo que quedó afuera
para que decida. Comparten los colaboradores y el alta (`_cv_alta.crear_de_un_cv`), que es donde
importa no duplicar; el resto es vocabulario diferente.

El porqué del diseño —los pendientes NO se persisten, la casilla es la fuente de verdad— está en
`services/_cv_pendientes.py`.
"""
from typing import List, Optional
from uuid import uuid4

from repositories.candidato_repo import CandidatoRepo
from repositories.vacante_repo import VacanteRepo
from schemas.cv_ingesta import AsignacionResponse, MailPendienteItem
from services import _cv_pendientes as _pend
from services.audit_service import AuditService
from services.cv_service import CvService
from services.gmail_service import GmailService, cliente_o
from utils.errors import AppError


class CvPendientesService:
    def __init__(self, gmail=None, vacante_repo=None, candidato_repo=None,
                 cv_service=None, audit=None) -> None:
        self._gmail = gmail or GmailService()
        self._vacantes = vacante_repo or VacanteRepo()
        self._candidatos = candidato_repo or CandidatoRepo()
        self._cv = cv_service or CvService()
        self._audit = audit or AuditService()

    def pendientes(self, cliente=None) -> List[MailPendienteItem]:
        """Los mails que NO se resolvieron solos. Ver `services/_cv_pendientes.py`: los ya
        procesados se saltean por `gmail_message_id` ANTES de tocar la red, y los adjuntos NO se
        bajan — cuántos CVs trae sale de lo que el mensaje ya declara."""
        token, salida = self._gmail.token(), []
        with cliente_o(cliente) as cli:
            ids = self._gmail.ids_con_adjunto(cli, token)
            ya = self._candidatos.message_ids_procesados(ids)
            for mid in [i for i in ids if i not in ya]:
                mensaje = self._gmail.mensaje_completo(cli, token, mid)
                motivo = _pend.motivo_de(mensaje, self._vacantes)
                if motivo:
                    salida.append(MailPendienteItem(**vars(_pend.pendiente_de(mensaje, motivo))))
        return salida

    def asignar_mail(self, message_id: str, vacante_id, empresa_id=None,
                     usuario_id: Optional[str] = None, cliente=None) -> AsignacionResponse:
        """Crea los candidatos de un mail sobre la vacante que eligió RRHH.

        🔴 La vacante se valida contra `empresa_id` (el header) para que nadie apunte a una de
        otra empresa; la EMPRESA DEL CANDIDATO, en cambio, sale de la vacante encontrada. Son dos
        cosas distintas: barrera y Vista vs Acción. Raises VACANTE_NOT_FOUND (404) ·
        CV_SIN_ADJUNTOS (422)."""
        vacante = self._vacantes.find_by_id(str(vacante_id), empresa_id)
        if not vacante:
            raise AppError("Vacante no encontrada", "VACANTE_NOT_FOUND", 404)
        token = self._gmail.token()
        with cliente_o(cliente) as cli:
            mensaje = self._gmail.mensaje_completo(cli, token, message_id)
            creados = _pend.asignar(cli, token, mensaje, vacante,
                                    candidato_repo=self._candidatos, cv_service=self._cv)
        self._audit.registrar(
            usuario_id=usuario_id, entidad="candidato", registro_id=str(uuid4()),
            accion="INSERT", evento="asignacion_manual_cv",
            empresa_id=vacante.empresa_id, datos_anteriores=None,
            datos_nuevos={"gmail_message_id": message_id, "vacante_id": str(vacante_id),
                          "candidatos_creados": len(creados)})
        return AsignacionResponse(candidatos_creados=creados, vacante_id=str(vacante_id))


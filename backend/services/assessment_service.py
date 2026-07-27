"""
Servicio de Assessment Engine — lógica de negocio.
Flujo: router → service → repository → DB
"""
from typing import Optional
from uuid import UUID

from repositories.assessment_campanas_repo import AssessmentCampanasRepo
from repositories.assessment_resultados_repo import AssessmentResultadosRepo
from schemas.assessment import (
    CampanaCreate, CampanaResponse, LinkCreate, LinkResponse,
    ResultadoResponse, RespuestaCreate,
)
from utils.errors import AppError
from utils.logger import logger

_SELF_MAP  = {1: "apertura", 2: "responsabilidad", 3: "estabilidad", 4: "amabilidad", 5: "sociabilidad"}
_COG_OK    = {1: 2, 2: 2, 3: 3}
_TEC_OK    = {1: 2, 2: 2}
_AREAS_SET = frozenset(_SELF_MAP.values())


def _compute_scores(respuestas: list) -> tuple:
    """
    Calcula puntuación AREAS (Likert×20), cognitivo y técnico (MC) desde respuestas raw.
    Retorna (puntuacion_dict, perfil_resultado_dict) con scores por dimensión + general.
    """
    areas: dict = {k: [] for k in _SELF_MAP.values()}
    cog: list = []
    tec: list = []
    for r in respuestas:
        t, pid, resp = r.get("tipo"), r.get("pregunta_id"), r.get("respuesta")
        if t == "self" and pid in _SELF_MAP:
            areas[_SELF_MAP[pid]].append((resp or 1) * 20)
        elif t == "cognitivo" and pid in _COG_OK:
            cog.append(100 if resp == _COG_OK[pid] else 0)
        elif t == "tecnico" and pid in _TEC_OK:
            tec.append(100 if resp == _TEC_OK[pid] else 0)
    pun: dict = {k: int(sum(v) / len(v)) if v else 0 for k, v in areas.items()}
    if cog: pun["cognitivo"] = int(sum(cog) / len(cog))
    if tec: pun["tecnico"]   = int(sum(tec) / len(tec))
    vals = list(pun.values())
    pun["general"] = int(sum(vals) / len(vals)) if vals else 0
    dom = max((k for k in pun if k in _AREAS_SET), key=lambda k: pun[k], default=None)
    return pun, {"perfil_dominante": dom.capitalize() if dom else None, "score_general": pun.get("general")}


class AssessmentService:
    def __init__(
        self,
        campanas_repo: Optional[AssessmentCampanasRepo] = None,
        resultados_repo: Optional[AssessmentResultadosRepo] = None,
    ) -> None:
        self._campanas_repo = campanas_repo or AssessmentCampanasRepo()
        self._resultados_repo = resultados_repo or AssessmentResultadosRepo()

    def get_campanas(self, empresa_id: Optional[UUID] = None) -> list:
        """Retorna todas las campañas filtradas por empresa (None = todas)."""
        return self._campanas_repo.get_campanas(empresa_id)

    def create_campana(self, data: CampanaCreate) -> CampanaResponse:
        """
        Crea una nueva campaña de evaluación con estado 'activa'.
        La empresa viene explícita en el body (root entity).

        Args:
            data: CampanaCreate con nombre, tipo, empresa_id y campos opcionales.

        Returns:
            CampanaResponse con la campaña recién creada.
        """
        campana = self._campanas_repo.create_campana(data)
        logger.info("Campaña de assessment creada",
                    extra={"campana_id": str(campana.id), "tipo": campana.tipo})
        return campana

    def create_link(self, data: LinkCreate, empresa_id: Optional[UUID] = None) -> LinkResponse:
        """
        Crea un link de evaluación con token UUID. Valida que la campaña exista Y sea de la
        empresa activa (None = consolidado): una campaña ajena da el MISMO CAMPANA_NOT_FOUND.
        El link hereda la empresa de la campaña en la DB (FK compuesta) — eso no cambia.

        Args:
            data: LinkCreate con campana_id, evaluado_nombre y evaluado_email.
            empresa_id: empresa activa del request; acota a qué campaña se puede apuntar.

        Returns:
            LinkResponse con el token generado.
        """
        self._campanas_repo.get_campana(str(data.campana_id), empresa_id)
        link = self._campanas_repo.create_link(data)
        logger.info("Link de assessment creado",
                    extra={"link_id": str(link.id), "email": link.evaluado_email})
        return link

    def get_evaluacion(self, token: str) -> LinkResponse:
        """
        Retorna el link por token para la ruta pública de evaluación.
        Lanza TOKEN_NOT_FOUND (404) si no existe o TOKEN_ALREADY_COMPLETED (409) si ya fue completado.
        """
        link = self._campanas_repo.get_link_by_token(token)
        if not link:
            raise AppError("Token de evaluación no encontrado", "TOKEN_NOT_FOUND", 404)
        if link.completado:
            raise AppError("Esta evaluación ya fue completada", "TOKEN_ALREADY_COMPLETED", 409)
        return link

    def submit_evaluacion(self, token: str, data: RespuestaCreate) -> ResultadoResponse:
        """
        Procesa respuestas: calcula scores AREAS + cognitivo + técnico y persiste el resultado.
        La empresa_id se hereda de la campaña asociada al token — NO depende del header HTTP,
        garantizando que la ruta pública (sin login) propague la empresa correctamente.

        Args:
            token: Token del link de evaluación.
            data: RespuestaCreate con lista de respuestas {tipo, pregunta_id, respuesta}.

        Returns:
            ResultadoResponse con scores calculados y perfil dominante.
        """
        link = self._campanas_repo.get_link_by_token(token)
        if not link:
            raise AppError("Token de evaluación no encontrado", "TOKEN_NOT_FOUND", 404)
        if link.completado:
            raise AppError("Esta evaluación ya fue completada", "TOKEN_ALREADY_COMPLETED", 409)

        # Obtener empresa de la campaña (no del header — ruta pública sin autenticación)
        campana = self._campanas_repo.get_campana(str(link.campana_id))
        empresa_id_str = str(campana.empresa_id) if campana.empresa_id else ""

        puntuacion, perfil = _compute_scores(data.respuestas)
        resultado = self._resultados_repo.save_resultado(
            link_id=str(link.id), campana_id=str(link.campana_id),
            respuestas=data.respuestas, puntuacion=puntuacion, perfil_resultado=perfil,
            empresa_id=empresa_id_str,
        )
        logger.info("Evaluación completada",
                    extra={"link_id": str(link.id), "score": puntuacion.get("general")})
        return resultado

    def get_resultados(self, empresa_id: Optional[UUID] = None) -> list:
        """Retorna todos los resultados de assessments completados, filtrados por empresa."""
        return self._resultados_repo.get_resultados(empresa_id)

    def get_resultado(self, resultado_id: UUID, empresa_id: Optional[UUID] = None) -> ResultadoResponse:
        """
        Retorna el detalle de un resultado, acotado a la empresa activa (None = consolidado).
        Lanza RESULTADO_NOT_FOUND (404) si no existe o es de otra empresa (mismo 404).
        """
        return self._resultados_repo.get_resultado(str(resultado_id), empresa_id)

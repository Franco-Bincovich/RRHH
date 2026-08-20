"""
Orquestador del import de evaluaciones (fase 4). Compone lo ya construido: parser (F2) +
resolutor (F3) + persistencia (F1). NO reimplementa nada.

- preview: parsea + resuelve identidades, NO persiste; avisa si el período ya existe.
- confirmar: persiste el payload que el humano APROBÓ (no re-parsea ni re-resuelve). Pisa el
  período previo (delete → CASCADE), guarda evaluados+resultados en bulk, guarda solo las
  equivalencias confirmadas a mano, y audita UN evento por lote.

Invariante no negociable: todo empleado_id resuelto pertenece a la empresa del lote (única
barandilla — las tablas hijas no llevan empresa_id). Se valida en confirmar, fail-closed.
"""
from typing import List, Optional
from uuid import UUID

from repositories.evaluacion_matcheo_repo import EvaluacionMatcheoRepo
from repositories.evaluacion_repo import EvaluacionRepo
from schemas.evaluacion_import_api import ConfirmarRequest, ConfirmarResponse, EvaluadoConfirm, PreviewResponse
from schemas.evaluacion_resultados import LoteCreate
from services import _evaluacion_import_payloads as pl
from services._audit_payloads_ev import payload_importacion_evaluaciones
from services.audit_service import AuditService
from services.evaluacion_import_service import parsear
from services.evaluacion_matcheo_service import ResolutorIdentidad
from services.evaluacion_service import EvaluacionService
from utils.errors import AppError
from utils.logger import logger

# Sufijo del período mientras el lote nuevo se construye: lo hace distinto del período real, así
# la UNIQUE(empresa_id, periodo) permite que el nuevo y el previo coexistan hasta el rename final.
_SUFIJO_TEMP = "::importando::"


class EvaluacionImportOrchestrator:
    def __init__(self, persistencia: Optional[EvaluacionService] = None,
                 resolutor: Optional[ResolutorIdentidad] = None,
                 repo: Optional[EvaluacionRepo] = None,
                 matcheo_repo: Optional[EvaluacionMatcheoRepo] = None,
                 audit: Optional[AuditService] = None) -> None:
        self._svc = persistencia or EvaluacionService()
        self._resolutor = resolutor or ResolutorIdentidad()
        self._repo = repo or EvaluacionRepo()
        self._matcheo = matcheo_repo or EvaluacionMatcheoRepo()
        self._audit = audit or AuditService()

    def preview(self, empresa_id: UUID, periodo: str, notas: bytes, desglose: bytes) -> PreviewResponse:
        """Parsea + resuelve dentro de la empresa, sin persistir. Avisa si el período ya existe."""
        parseo = parsear(notas, desglose)
        previews = [
            pl.preview_de(ev, self._resolutor.resolver(
                empresa_id, ev.apellido_evaluado, ev.nombre_evaluado,
                ev.apellido_superior, ev.nombre_superior))
            for ev in parseo.evaluados
        ]
        prior = self._repo.find_lote_by_periodo(str(empresa_id), periodo)
        a_pisar = len(self._repo.find_evaluados(str(prior.id))) if prior else 0
        return PreviewResponse(
            resumen=pl.resumen_de(previews), evaluados=previews,
            problemas=parseo.problemas, anomalias=parseo.anomalias,
            periodo_existe=prior is not None, registros_a_pisar=a_pisar)

    def confirmar(self, req: ConfirmarRequest, usuario_id: Optional[str] = None) -> ConfirmarResponse:
        """Persiste el payload aprobado SIN ventana de pérdida. La UNIQUE(empresa_id, periodo)
        impide dos lotes del mismo período, así que: (a) crea el lote con período TEMPORAL,
        (b-d) persiste evaluados/resultados/equivalencias, (e) VERIFICA POR CONTEO, (f) recién
        entonces borra el previo, (g) renombra al período real. Si algo falla antes de (f) el
        previo queda intacto y el temporal se limpia. UN evento de auditoría (con el período real)."""
        emp = str(req.empresa_id)
        self._validar_empresa(emp, req.evaluados)
        prior = self._repo.find_lote_by_periodo(emp, req.periodo)
        lote = self._svc.crear_lote(LoteCreate(
            empresa_id=req.empresa_id, periodo=f"{req.periodo} {_SUFIJO_TEMP}",
            importado_por=UUID(usuario_id) if usuario_id else None))
        try:
            n_ev, n_res, n_eq = self._persistir_y_verificar(lote.id, req, emp, usuario_id)  # b–e
        except Exception:
            self._limpiar_temporal(lote.id)  # best-effort; el prior sigue intacto, no tapa el error
            raise
        if prior:
            self._repo.delete_lote(str(prior.id))                      # f — único paso destructivo
        self._renombrar_al_real(lote.id, req.periodo)                  # g — ventana f→g (recuperable)
        self._audit.registrar(**payload_importacion_evaluaciones(
            str(lote.id), req.periodo, emp, n_ev, n_res, n_eq, bool(prior), usuario_id))
        logger.info("Import de evaluaciones confirmado",
                    extra={"lote_id": str(lote.id), "evaluados": n_ev, "resultados": n_res})
        return ConfirmarResponse(lote_id=lote.id, evaluados=n_ev, resultados=n_res,
                                 equivalencias=n_eq, piso_periodo_anterior=bool(prior))

    def _persistir_y_verificar(self, lote_id: UUID, req: ConfirmarRequest, emp: str,
                               usuario_id: Optional[str]) -> tuple:
        """Pasos b–e: persiste y VERIFICA POR CONTEO antes de tocar el lote previo. La verificación
        es el corazón del fix: un insert parcial silencioso DEBE detectarse acá (no alcanza con
        'no hubo excepción'). Devuelve (n_evaluados, n_resultados, n_equivalencias)."""
        guardados = self._svc.guardar_evaluados(lote_id, [pl.a_evaluado_create(e) for e in req.evaluados])
        if len(guardados) != len(req.evaluados):
            raise AppError("Evaluados guardados no coinciden con el lote", "IMPORT_INCOMPLETO", 500)
        id_por_nombre = {(g.apellido_evaluado, g.nombre_evaluado): g.id for g in guardados}
        esperados, n_res = 0, 0
        for e in req.evaluados:
            creates = pl.a_resultado_creates(e)
            esperados += len(creates)
            n_res += self._svc.guardar_resultados(id_por_nombre[(e.apellido_evaluado, e.nombre_evaluado)], creates)
        if n_res != esperados:
            raise AppError("Resultados guardados no coinciden con el lote", "IMPORT_INCOMPLETO", 500)
        n_eq = self._guardar_equivalencias(emp, req.evaluados, usuario_id)
        return len(guardados), n_res, n_eq

    def _limpiar_temporal(self, lote_id: UUID) -> None:
        """Borrado best-effort del lote temporal ante fallo en b–e. No re-lanza: no debe tapar el
        error original (el caller re-lanza el suyo)."""
        try:
            self._repo.delete_lote(str(lote_id))
        except Exception:  # noqa: BLE001 — limpieza best-effort
            logger.error("No se pudo limpiar el lote temporal huérfano", extra={"lote_id": str(lote_id)})

    def _renombrar_al_real(self, lote_id: UUID, periodo: str) -> None:
        """Paso g. Si falla, el lote quedó COMPLETO con nombre temporal y el previo ya se borró —
        no es pérdida, es recuperable renombrando a mano. Se loguea a ERROR con lote_id y período."""
        try:
            self._repo.update_periodo_lote(str(lote_id), periodo)
        except Exception:
            logger.error("Import completo pero el rename al período real falló — renombrar a mano",
                         extra={"lote_id": str(lote_id), "periodo": periodo})
            raise

    def _validar_empresa(self, empresa_id: str, evaluados: List[EvaluadoConfirm]) -> None:
        """Fail-closed: ningún empleado_id puede ser de otra empresa (la barandilla del matcheo)."""
        del_empresa = {str(c.empleado_id) for c in self._matcheo.find_empleados_empresa(empresa_id)}
        if any(e.empleado_id and str(e.empleado_id) not in del_empresa for e in evaluados):
            raise AppError("Hay colaboradores que no pertenecen a la empresa del lote",
                           "EMPLEADO_FUERA_DE_EMPRESA", 422)

    def _guardar_equivalencias(self, empresa_id: str, evaluados: List[EvaluadoConfirm],
                               usuario_id: Optional[str]) -> int:
        """Upsert de SOLO las equivalencias que el humano confirmó a mano (no las automáticas)."""
        n = 0
        for e in evaluados:
            if e.guardar_equivalencia and e.empleado_id:
                self._matcheo.crear_equivalencia(pl.equivalencia_dict(empresa_id, e, usuario_id))
                n += 1
        return n

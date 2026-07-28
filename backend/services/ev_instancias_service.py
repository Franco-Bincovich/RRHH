"""
Servicio de instancias y resultados de evaluación de desempeño.
Flujo: router → service → repository → DB

Herencia de empresa: instancia hereda empresa_id del ciclo (que lo heredó de la plantilla).
Al crear instancia se generan filas vacías en ev_resultados (una por criterio de la plantilla).
Finalizar: calcula puntaje_global si la escala es numérica (promedio ponderado); null si cualitativa.
"""
from datetime import date
from typing import Optional
from uuid import UUID

from repositories.ev_ciclos_repo import EvCiclosRepo
from repositories.ev_instancias_repo import EvInstanciasRepo
from repositories.ev_plantillas_repo import EvPlantillasRepo
from schemas.evaluaciones import (
    InstanciaCreate, InstanciaDetalleResponse, InstanciaListResponse,
    InstanciaResponse, ResultadoUpdate,
)
from services._audit_payloads_ev import (
    payload_carga_resultado_evaluacion, payload_finalizar_evaluacion,
)
from services._evaluaciones_export import construir_filas_export
from services._ev_instancias_utils import calcular_puntaje_global
from services.audit_service import AuditService
from services._limite_export import verificar_limite_export
from services.export import Descarga, build_export
from utils.errors import AppError
from utils.logger import logger


class EvInstanciasService:
    def __init__(
        self,
        repo: Optional[EvInstanciasRepo] = None,
        ciclos_repo: Optional[EvCiclosRepo] = None,
        plantillas_repo: Optional[EvPlantillasRepo] = None,
        audit: Optional[AuditService] = None,
    ) -> None:
        self._repo = repo or EvInstanciasRepo()
        self._ciclos_repo = ciclos_repo or EvCiclosRepo()
        self._plantillas_repo = plantillas_repo or EvPlantillasRepo()
        self._audit = audit or AuditService()

    def get_all(self, empresa_id: Optional[UUID] = None,
                ciclo_id: Optional[UUID] = None, estado: Optional[str] = None) -> InstanciaListResponse:
        """Retorna instancias con nombres resueltos, filtradas por empresa/ciclo/estado."""
        items = self._repo.find_all(empresa_id, ciclo_id, estado)
        return InstanciaListResponse(items=items, total=len(items))

    def exportar(self, empresa_id: Optional[UUID] = None, formato: str = "excel", ciclo_id: Optional[UUID] = None, estado: Optional[str] = None) -> Descarga:
        """Exporta la lista de instancias (columnas legibles, sin UUIDs) respetando ciclo/estado."""
        items = self._repo.find_all(empresa_id, ciclo_id, estado)
        verificar_limite_export(len(items))
        datos = {"Evaluaciones": construir_filas_export(items)}
        return build_export(nombre="Evaluaciones de desempeño", datos=datos, filename_base="evaluaciones_desempeno", formato=formato)

    def get_by_id(self, id: UUID, empresa_id: Optional[UUID] = None) -> InstanciaDetalleResponse:
        """
        Retorna instancia con resultados y configuración de escala de la plantilla.

        Raises:
            AppError: INSTANCIA_NOT_FOUND (404).
        """
        row = self._repo.find_by_id(str(id), empresa_id)
        if not row:
            raise AppError("Instancia no encontrada", "INSTANCIA_NOT_FOUND", 404)
        return row

    def create(self, data: InstanciaCreate) -> InstanciaDetalleResponse:
        """
        Crea una instancia de evaluación para un empleado en un ciclo.
        hereda empresa_id del ciclo. Genera filas vacías de ev_resultados.

        Raises:
            AppError: CICLO_NOT_FOUND (404), CICLO_CERRADO (422),
                      EMPRESA_MISMATCH (422), INSTANCIA_DUPLICADA (409).
        """
        from integrations.supabase_client import supabase_admin
        ciclo = self._ciclos_repo.find_by_id(str(data.ciclo_id))
        if not ciclo:
            raise AppError("Ciclo no encontrado", "CICLO_NOT_FOUND", 404)
        if ciclo.estado == "cerrado":
            raise AppError("No se puede asignar empleados a un ciclo cerrado", "CICLO_CERRADO", 422)
        emp = supabase_admin.table("empleados").select("empresa_id").eq(
            "id", str(data.empleado_id)).maybe_single().execute()
        if not (emp and emp.data):
            raise AppError("Empleado no encontrado", "EMPLEADO_NOT_FOUND", 404)
        if emp.data["empresa_id"] != str(ciclo.empresa_id):
            raise AppError("El empleado y el ciclo no pertenecen a la misma empresa", "EMPRESA_MISMATCH", 422)
        plantilla = self._plantillas_repo.find_by_id(str(ciclo.plantilla_id))
        if not plantilla:
            raise AppError("Plantilla del ciclo no encontrada", "PLANTILLA_NOT_FOUND", 404)
        if self._repo.exists(str(data.ciclo_id), str(data.empleado_id)):
            raise AppError(
                "Este empleado ya tiene una evaluación en este ciclo", "INSTANCIA_DUPLICADA", 409,
            )
        criterios = [{"id": str(c.id)} for c in plantilla.criterios]
        evaluador_id = str(data.evaluador_id) if data.evaluador_id else None
        instancia = self._repo.create(
            str(data.ciclo_id), str(data.empleado_id), evaluador_id,
            str(ciclo.empresa_id), criterios,
        )
        if not instancia:
            raise AppError("Error al crear la instancia", "DB_ERROR", 500)
        logger.info("Instancia de evaluación creada", extra={
            "empleado_id": str(data.empleado_id), "ciclo_id": str(data.ciclo_id),
        })
        return instancia

    def update_resultado(self, instancia_id: UUID, criterio_id: UUID, data: ResultadoUpdate,
                         empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None) -> InstanciaDetalleResponse:
        """
        Carga o actualiza el puntaje/valor de un criterio en una instancia.
        Audita el scoring (diff viejo→nuevo) tras la escritura; `instancia` = snapshot previo.

        Raises:
            AppError: INSTANCIA_NOT_FOUND (404), INSTANCIA_FINALIZADA (422).
        """
        instancia = self._repo.find_by_id(str(instancia_id), empresa_id)
        if not instancia:
            raise AppError("Instancia no encontrada", "INSTANCIA_NOT_FOUND", 404)
        if instancia.estado == "finalizada":
            raise AppError("La instancia ya está finalizada", "INSTANCIA_FINALIZADA", 422)
        payload = {k: v for k, v in data.model_dump(exclude_none=True).items()}
        self._repo.update_resultado(str(instancia_id), str(criterio_id), payload)
        actualizada = self._repo.find_by_id(str(instancia_id), empresa_id)
        self._audit.registrar(**payload_carga_resultado_evaluacion(instancia, actualizada, criterio_id, usuario_id))
        return actualizada  # type: ignore[return-value]

    def finalizar(self, id: UUID, empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None) -> InstanciaDetalleResponse:
        """
        Finaliza una instancia calculando puntaje_global (ver calcular_puntaje_global).
        Audita la finalización (estado + puntaje_global) tras la escritura exitosa.

        Raises:
            AppError: INSTANCIA_NOT_FOUND (404), INSTANCIA_FINALIZADA (409),
                      RESULTADOS_INCOMPLETOS (422) si escala numérica y quedan puntajes vacíos.
        """
        instancia = self._repo.find_by_id(str(id), empresa_id)
        if not instancia:
            raise AppError("Instancia no encontrada", "INSTANCIA_NOT_FOUND", 404)
        if instancia.estado == "finalizada":
            raise AppError("La instancia ya está finalizada", "INSTANCIA_FINALIZADA", 409)
        puntaje_global = calcular_puntaje_global(instancia)
        self._repo.finalizar(str(id), empresa_id, puntaje_global, date.today())
        self._audit.registrar(**payload_finalizar_evaluacion(id, instancia, puntaje_global, str(instancia.empresa_id), usuario_id))
        logger.info("Instancia finalizada", extra={"instancia_id": str(id), "puntaje_global": puntaje_global})
        return self._repo.find_by_id(str(id), empresa_id)  # type: ignore[return-value]

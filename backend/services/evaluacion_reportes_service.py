"""
Servicio de reportes de un lote de evaluaciones: métricas (4 bloques), listado filtrable,
export y ficha individual. Los agregados los computa _evaluacion_metricas (Python puro); acá
solo se orquesta fetch + filtros. Sin ownership: evaluaciones no pasa por ownership.

Los 4 métodos públicos reciben `empresa_id` (la empresa activa del request) y lo validan contra
la empresa del lote ANTES de leer nada — es un parámetro obligatorio a propósito: si mañana
aparece un caller nuevo, omitirlo revienta con TypeError en vez de reabrir la fuga en silencio.
"""
from typing import List, Optional
from uuid import UUID

from repositories.evaluacion_repo import EvaluacionRepo
from repositories._scope_filtros import empleados_de_proyecto
from schemas.evaluacion_reportes import (
    EvaluadoListadoItem, EvaluadoListadoResponse, FichaResponse, MetricasResponse,
)
from services import _evaluacion_metricas as met
from services._evaluaciones_resultados_export import construir_filas_export
from services.evaluacion_service import verificar_empresa_lote
from services._limite_export import LIMITE_FILAS_EXPORT, verificar_limite_export
from services._paginacion import cantidad_paginas
from services.export import Descarga, build_export
from utils.errors import AppError


class EvaluacionReportesService:
    def __init__(self, repo: Optional[EvaluacionRepo] = None) -> None:
        self._repo = repo or EvaluacionRepo()

    def metricas(self, lote_id: UUID, empresa_id: Optional[UUID]) -> MetricasResponse:
        """Los 4 bloques del ciclo en una sola pasada sobre las filas del lote."""
        evaluados, resultados = self._lote_rows(lote_id, empresa_id)
        return MetricasResponse(
            resumen=met.resumen(evaluados, resultados), brecha=met.brecha(evaluados, resultados),
            sectores=met.por_sector(evaluados), competencias=met.competencias(evaluados, resultados))

    def listado(self, lote_id: UUID, empresa_id: Optional[UUID], sector: Optional[str] = None,
                perfil: Optional[str] = None, con_nota: Optional[str] = None,
                proyecto_id: Optional[UUID] = None, page: int = 1,
                page_size: int = 20) -> EvaluadoListadoResponse:
        """Una página de evaluados del lote, con los filtros resueltos EN LA BASE.

        🔴 LOS CUATRO FILTROS VIAJAN AL WHERE. El panel aplicaba tres de ellos (sector, perfil,
        con_nota) sobre el array ya traído: con ~30 filas se veía bien, y a 1.005 por lote
        significa que filtrar por sector no encuentra a nadie que esté fuera de la página que se
        está mirando. El cuarto (`proyecto_id`) ya era server-side.

        🔑 Y AHORA LOS RESULTADOS SE PIDEN SÓLO PARA LA PÁGINA. Antes `_lote_rows` traía los
        ~30.000 resultados del lote entero con un `?evaluado_id=in.(1005 uuids)` de ~37 KB — el
        hallazgo #2 del diagnóstico de escala, que ya devolvía 500 en otro módulo. Con la página
        son 25 ids.
        """
        verificar_empresa_lote(self._repo, lote_id, empresa_id)
        ids_proyecto = empleados_de_proyecto(proyecto_id) if proyecto_id else None
        evaluados, total = self._repo.find_evaluados_pagina(
            str(lote_id), page, page_size, sector, perfil, con_nota, ids_proyecto)
        resultados = self._repo.find_resultados_por_evaluados([str(e.id) for e in evaluados])
        tipos = met.tipos_por_evaluado(resultados)
        return EvaluadoListadoResponse(
            items=[self._item(e, tipos.get(str(e.id), [])) for e in evaluados],
            total=total, page=page, page_size=page_size,
            total_pages=cantidad_paginas(total, page_size),
            sectores=self._repo.sectores_del_lote(str(lote_id)),
        )

    def exportar(self, lote_id: UUID, empresa_id: Optional[UUID], formato: str = "excel",
                 sector: Optional[str] = None, perfil: Optional[str] = None,
                 con_nota: Optional[str] = None, proyecto_id: Optional[UUID] = None) -> Descarga:
        """Export del listado — recibe y aplica los mismos filtros que listado (estándar 1.2)."""
        pagina = self.listado(lote_id, empresa_id, sector, perfil, con_nota, proyecto_id,
                              1, LIMITE_FILAS_EXPORT)
        verificar_limite_export(pagina.total)  # total exacto (count="exact"), respeta los filtros
        datos = {"Evaluados": construir_filas_export(pagina.items)}
        return build_export(nombre="Resultados de evaluaciones", datos=datos,
                            filename_base="evaluaciones_resultados", formato=formato)

    def ficha(self, lote_id: UUID, evaluado_id: UUID, empresa_id: Optional[UUID]) -> FichaResponse:
        """Ficha individual: matriz competencia × tipo de evaluador + promedio de terceros.

        El evaluado se busca SOLO entre los del lote ya validado (cadena evaluado → lote →
        empresa): un evaluado de otra empresa cuelga de otro lote y acá no aparece nunca."""
        evaluados, resultados = self._lote_rows(lote_id, empresa_id)
        ev = next((e for e in evaluados if str(e.id) == str(evaluado_id)), None)
        if not ev:
            raise AppError("Evaluado no encontrado en el lote", "EVALUADO_NOT_FOUND", 404)
        return met.ficha(ev, resultados)

    def _lote_rows(self, lote_id: UUID, empresa_id: Optional[UUID]):
        """Filas del lote, previa validación de empresa (404 idéntico al de lote inexistente)."""
        verificar_empresa_lote(self._repo, lote_id, empresa_id)
        evaluados = self._repo.find_evaluados(str(lote_id))
        resultados = self._repo.find_resultados_por_evaluados([str(e.id) for e in evaluados])
        return evaluados, resultados

    @staticmethod
    def _item(e, tipos: List[str]) -> EvaluadoListadoItem:
        superior = f"{e.apellido_superior or ''} {e.nombre_superior or ''}".strip() or None
        return EvaluadoListadoItem(
            id=str(e.id), empleado_id=str(e.empleado_id) if e.empleado_id else None, apellido=e.apellido_evaluado,
            nombre=e.nombre_evaluado, sector=e.sector, superior=superior, tipos=tipos,
            perfil=e.perfil, nota_final=e.nota_final, asignado=e.empleado_id is not None)

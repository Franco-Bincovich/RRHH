"""
Servicio de Reportes. Orquesta la generación y persistencia de reportes.
Flujo: router → service → generators / repo → DB

Split:
  reporte_generators.py  — headcount, rotación, costos, vacantes, onboarding
  reporte_adhoc.py       — análisis IA con Claude
"""
from datetime import date
from typing import List, Optional
from uuid import UUID

from repositories.reporte_repo import ReporteRepo
from schemas.reporte import HistorialItem, ReporteResponse
from services.reporte_adhoc import generate_adhoc
from services.reporte_anual import generate_anual_consolidado
from services.reporte_generators import (
    generate_altas_bajas,
    generate_costos,
    generate_distribucion,
    generate_headcount,
    generate_onboarding,
    generate_rotacion,
    generate_vacantes,
    periodo_str,
)
from utils.errors import AppError
from utils.logger import logger


class ReporteService:
    def __init__(self, repo: Optional[ReporteRepo] = None) -> None:
        self._repo = repo or ReporteRepo()

    def get_historial(self, empresa_id: Optional[UUID] = None) -> List[HistorialItem]:
        """
        Retorna el historial de reportes.
        Con empresa activa: reportes de esa empresa + consolidados (empresa_id null).
        Con None (Todas): todos los reportes.
        """
        return self._repo.find_historial(empresa_id)

    def generar(
        self,
        tipo: str,
        mes: Optional[int] = None,
        anio: Optional[int] = None,
        prompt: Optional[str] = None,
        generado_por: str = "Sistema",
        empresa_id: Optional[UUID] = None,
    ) -> ReporteResponse:
        """
        Genera un reporte del tipo indicado, lo persiste en el historial y lo retorna.
        empresa_id determina el alcance: si es None el reporte queda como consolidado.

        Args:
            tipo: Tipo de reporte (headcount | rotacion | costos | vacantes | onboarding | adhoc).
            mes: Mes del período (1–12). Requerido para headcount, rotacion, costos.
            anio: Año del período. Requerido para headcount, rotacion, costos.
            prompt: Descripción en lenguaje natural para el reporte adhoc.
            generado_por: Identificador del usuario que solicita el reporte.
            empresa_id: Empresa activa del contexto. None = consolidado.

        Returns:
            ReporteResponse con los datos generados y persistidos.

        Raises:
            AppError: REPORTE_TIPO_ERROR (400) si el tipo no existe.
            AppError: REPORTE_ERROR (500) si falla la generación.
        """
        hoy = date.today()
        mes_e = mes or hoy.month
        anio_e = anio or hoy.year

        generators = {
            "headcount":          lambda: generate_headcount(mes_e, anio_e, empresa_id),
            "rotacion":           lambda: generate_rotacion(mes_e, anio_e, empresa_id),
            "altas_bajas":        lambda: generate_altas_bajas(mes_e, anio_e, empresa_id),
            "distribucion":       lambda: generate_distribucion(empresa_id),
            "costos":             lambda: generate_costos(mes_e, anio_e, empresa_id),
            "vacantes":           lambda: generate_vacantes(empresa_id),
            "onboarding":         lambda: generate_onboarding(empresa_id),
            "adhoc":              lambda: generate_adhoc(prompt or "", empresa_id),
            "anual_consolidado":  lambda: generate_anual_consolidado(anio_e, empresa_id),
        }

        if tipo not in generators:
            raise AppError(f"Tipo de reporte desconocido: {tipo}", "REPORTE_TIPO_ERROR", 400)

        nombres = {
            "headcount":         f"Headcount — {periodo_str(mes_e, anio_e)}",
            "rotacion":          f"Rotación — {periodo_str(mes_e, anio_e)}",
            "altas_bajas":       f"Altas y bajas — {periodo_str(mes_e, anio_e)}",
            "distribucion":      "Distribución de plantilla",
            "costos":            f"Costos — {periodo_str(mes_e, anio_e)}",
            "vacantes":          "Pipeline de Vacantes",
            "onboarding":        "Progreso de Onboarding",
            "adhoc":             f"Análisis IA: {(prompt or '')[:60]}",
            "anual_consolidado": f"Informe Anual {anio_e}",
        }

        try:
            datos = generators[tipo]()
        except AppError:
            raise
        except Exception as exc:
            logger.error("Error al generar reporte", extra={"tipo": tipo, "error": str(exc)})
            raise AppError("Error al generar el reporte", "REPORTE_ERROR", 500) from exc

        reporte = self._repo.save(
            nombre=nombres[tipo],
            tipo=tipo,
            datos=datos,
            generado_por=generado_por,
            empresa_id=empresa_id,
            parametros=(
                {"anio": anio_e} if tipo == "anual_consolidado"
                else None if tipo in ("vacantes", "onboarding", "adhoc", "distribucion")
                else {"mes": mes_e, "anio": anio_e}
            ),
        )
        logger.info("Reporte generado", extra={"tipo": tipo, "id": str(reporte.id)})
        return reporte

"""
Write path del servicio de costos: carga de nómina y presupuesto de área.

Extraído porque costo_service.py estaba en 150/150 y el export del módulo no entraba. Mismo
molde que _vacaciones_write.py y _ausencias_write.py: funciones libres que reciben sus
colaboradores, y el service delega en una línea, así que los call sites no cambian. La lógica
se movió VERBATIM — el orden de las operaciones, el manejo de errores y los payloads de
auditoría son idénticos a antes.
"""
from calendar import monthrange
from datetime import date
from typing import Optional
from uuid import UUID

from schemas.costo import NominaCreate, NominaResponse, PresupuestoCreate, PresupuestoResponse
from services._audit_payloads_rrhh import payload_carga_nomina, payload_set_presupuesto
from services._periodo_utils import verificar_periodo_abierto
from utils.errors import AppError
from utils.logger import logger


def cargar_nomina(nomina_repo, periodo_repo, audit, data: NominaCreate,
                  empresa_id: Optional[UUID], usuario_id: Optional[str],
                  rol: Optional[str]) -> NominaResponse:
    """
    Registra o actualiza la nómina de un empleado para un período (upsert). empresa_id
    se hereda del empleado (lo resuelve el repo); auditado. Bloquea si el mes está cerrado.

    Raises:
        AppError: NOMINA_SAVE_ERROR (500) si la DB falla; PERIODO_CERRADO (409) si el mes está cerrado.
    """
    # rol REAL, no None hardcodeado: con None el check era un no-op que dejaría de proteger en silencio.
    verificar_periodo_abierto(empresa_id, "costos", rol, desde=date(data.anio, data.mes, 1), hasta=date(data.anio, data.mes, monthrange(data.anio, data.mes)[1]), repo=periodo_repo)
    # Best-effort para el diff de auditoría: leé la nómina previa (mismo empleado/mes/anio)
    # ANTES del upsert. Sin previo → primera carga (alta). Falla de lectura → prior=None
    # (el audit es un extra, no debe romper la carga). No toca el repo ni el upsert.
    try:
        prev = nomina_repo.get_nomina_mes(data.mes, data.anio, None)
        prior = next((n for n in prev if str(n.empleado_id) == str(data.empleado_id)), None)
    except Exception:
        prior = None
    try:
        nomina = nomina_repo.save_nomina(data)
    except AppError:
        raise
    except Exception as exc:
        raise AppError("Error al guardar la nómina", "NOMINA_SAVE_ERROR", 500) from exc
    audit.registrar(**payload_carga_nomina(nomina, usuario_id, nomina.empresa_id, prior))
    logger.info(
        "Nómina cargada",
        extra={"empleado_id": data.empleado_id, "mes": data.mes, "anio": data.anio},
    )
    return nomina


def set_presupuesto_area(presupuesto_repo, audit, data: PresupuestoCreate,
                         empresa_id: Optional[UUID],
                         usuario_id: Optional[str]) -> PresupuestoResponse:
    """
    Establece o actualiza el presupuesto de nómina de un área para un período (upsert).
    empresa_id se hereda del área — el repositorio lo resuelve automáticamente.
    Registra el evento de auditoría (empresa_id = el del header, puede ser None).

    Args:
        presupuesto_repo: Repositorio de presupuestos.
        audit: Servicio de auditoría.
        data: Datos del presupuesto (área, período, monto presupuestado).
        empresa_id: Contexto de empresa (header) para validación y audit. None = consolidado.
        usuario_id: ID del operador (trazabilidad de audit).

    Raises:
        AppError: PRESUPUESTO_SAVE_ERROR (500) si la operación en DB falla.
    """
    try:
        presupuesto = presupuesto_repo.save_presupuesto(data)
    except AppError:
        raise
    except Exception as exc:
        raise AppError("Error al guardar el presupuesto", "PRESUPUESTO_SAVE_ERROR", 500) from exc
    audit.registrar(**payload_set_presupuesto(presupuesto, usuario_id, str(empresa_id) if empresa_id else None))
    logger.info(
        "Presupuesto de área configurado",
        extra={"area_id": data.area_id, "mes": data.mes, "anio": data.anio},
    )
    return presupuesto

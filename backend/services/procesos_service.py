"""
Servicio del Panel de Procesos. Agrega conteos de estado por proceso operativo.
Solo lectura — no modifica datos.
Flujo: router → service → DB
"""
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.procesos import EstadoConteo, ProcesoResumen, ProcesosResponse
from utils.errors import AppError
from utils.logger import logger


# (tabla, proceso_id, label)
#
# 🔴 EVALUACIONES NO ESTÁ ACÁ, Y NO ES UN OLVIDO. Hasta el 2026-08-11 el panel contaba
# `ev_ciclos` y `ev_instancias`; se sacaron con el módulo `ev_*` (bloque J5a). NO se
# reapuntaron al módulo de evaluaciones VIVO (`evaluacion_lotes`) porque un lote importado
# no tiene el eje que este panel muestra: no hay `abierto`/`cerrado` ni `iniciada`/`finalizada`
# que contar — un lote existe o no existe. Meterlo con estados inventados daría un tablero
# que se lee igual que los otros seis y significa otra cosa.
_META: List[tuple[str, str, str]] = [
    ("onboarding_instancias", "onboarding", "Onboarding"),
    ("offboarding_instancias", "offboarding", "Offboarding"),
    ("vacantes", "vacantes", "Vacantes"),
    ("empleado_capacitacion", "capacitaciones", "Capacitaciones"),
    ("objetivos", "objetivos", "Objetivos"),
]

_ESTADOS: dict[str, List[tuple[str, str]]] = {
    "onboarding_instancias": [
        ("en_progreso", "En progreso"),
        ("completado", "Completado"),
        ("cancelado", "Cancelado"),
    ],
    "offboarding_instancias": [
        ("iniciado", "Iniciado"),
        ("completado", "Completado"),
        ("cancelado", "Cancelado"),
    ],
    "vacantes": [
        ("nueva", "Nueva"),
        ("en_revision", "En revisión"),
        ("cerrada", "Cerrada"),
    ],
    "empleado_capacitacion": [
        ("pendiente", "Pendiente"),
        ("en_curso", "En curso"),
        ("completado", "Completado"),
    ],
    "objetivos": [
        ("por_hacer", "Por hacer"),
        ("haciendo", "En curso"),
        ("terminado", "Terminado"),
    ],
}


class ProcesosService:
    def get_procesos(self, empresa_id: Optional[UUID] = None) -> ProcesosResponse:
        """
        Calcula conteos por estado de cada proceso operativo.
        Filtra por empresa_id si se provee; None = consolidado de todas.

        Returns:
            ProcesosResponse con un ProcesoResumen por proceso.

        Raises:
            AppError: PROCESOS_ERROR (500) si falla alguna consulta.
        """
        eid = str(empresa_id) if empresa_id else None
        try:
            procesos = [
                self._build_proceso(tabla, proceso, label, eid)
                for tabla, proceso, label in _META
            ]
        except AppError:
            raise
        except Exception as exc:
            logger.error("Error al calcular panel de procesos", extra={"error": str(exc)})
            raise AppError("Error al obtener procesos", "PROCESOS_ERROR", 500) from exc
        logger.info("Panel de procesos calculado")
        return ProcesosResponse(procesos=procesos)

    def _build_proceso(
        self, tabla: str, proceso: str, label: str, eid: Optional[str]
    ) -> ProcesoResumen:
        """Construye el resumen de un proceso con conteos por estado."""
        estados = [
            EstadoConteo(estado=e, label=lbl, total=self._count(tabla, e, eid))
            for e, lbl in _ESTADOS[tabla]
        ]
        return ProcesoResumen(
            proceso=proceso,
            label=label,
            tabla=tabla,
            estados=estados,
            total=sum(ec.total for ec in estados),
        )

    def _count(self, tabla: str, estado: str, eid: Optional[str]) -> int:
        """Cuenta registros por estado y empresa.

        🔴 EN `objetivos` CUENTA SOLO LAS RAÍCES (`parent_id IS NULL`). Desde la migración 095
        los subobjetivos son filas de la MISMA tabla, así que sin este filtro un objetivo con 3
        subtareas contaría como 4 y el tablero de Procesos pasaría de decir "12 objetivos" a
        decir "12 objetivos y subtareas" sin que nadie lo haya decidido — el número no rompe,
        cambia de significado en silencio, que es peor.
        """
        q = supabase_admin.table(tabla).select("id", count="exact").eq("estado", estado)
        if tabla == "objetivos":
            q = q.is_("parent_id", "null")
        if eid:
            q = q.eq("empresa_id", eid)
        return q.execute().count or 0

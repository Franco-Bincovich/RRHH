"""
Service del botón "resolver pendientes": completa los `manager_id` que el import dejó sin asignar.

El caso real: el CSV de nómina trae el nombre del superior, pero 5 de los 6 jefes del archivo NO
están cargados como empleados. El import los deja en `empleado_superior_pendiente` (migración
086) con el nombre crudo y el motivo. El día que RRHH da de alta al jefe que faltaba, este
service resuelve todo lo pendiente CONTRA EL ESTADO ACTUAL de `empleados` — sin re-subir el CSV,
que es lo que hoy sería la única alternativa y que RRHH no necesariamente tiene a mano.

🔴 REUSA `_superiores_matcher`, el MISMO núcleo que el import. No reimplementa el matcheo: si
tuviera el suyo, el botón y el import podrían dar veredictos distintos sobre los mismos datos.
Por eso los tres estados, la normalización de identidad, el chequeo de ciclos y el "cero fuzzy"
son literalmente el mismo código — leer el encabezado de ese módulo.

Qué pasa con cada pendiente al re-resolver:
  · se resolvió  → se escribe el `manager_id` y la fila SE BORRA de la tabla.
  · sigue sin resolverse → la fila queda, con el motivo ACTUALIZADO (puede haber cambiado: lo que
    antes era "no hay ningún empleado con ese nombre" puede ser hoy "2 empleados con ese nombre").
"""
from typing import List, Optional
from uuid import UUID

from repositories.empleado_repo import EmpleadoRepo
from repositories.empleado_superior_pendiente_repo import EmpleadoSuperiorPendienteRepo
from schemas.superiores_pendientes import (
    ResolucionPendientesResult, SuperiorPendienteItem, SuperioresPendientesListResponse,
)
from services import _superiores_matcher as matcher
from utils.logger import logger


class SuperioresPendientesService:
    def __init__(self, repo: Optional[EmpleadoSuperiorPendienteRepo] = None,
                 empleado_repo: Optional[EmpleadoRepo] = None) -> None:
        self._repo = repo or EmpleadoSuperiorPendienteRepo()
        self._empleados = empleado_repo or EmpleadoRepo()

    def listar(self, empresa_id: Optional[UUID] = None) -> SuperioresPendientesListResponse:
        """Cuántos pendientes hay y de quiénes. `empresa_id` None = consolidado."""
        filas = self._repo.listar(empresa_id)
        return SuperioresPendientesListResponse(
            items=[_item(f) for f in filas], total=len(filas))

    def resolver(self, empresa_id: Optional[UUID] = None) -> ResolucionPendientesResult:
        """Reintenta todos los pendientes contra el estado ACTUAL de empleados.

        Args:
            empresa_id: acota QUÉ PENDIENTES se reintentan (los de esa empresa). ⚠️ NO acota
                dónde se busca al superior: eso lo decide `_superiores_matcher`, que busca en
                todas las empresas porque el jefe puede ser de otra (decisión de producto
                2/8/2026). Acotar la búsqueda dejaría sin resolver justo los cruzados.

        Returns:
            Cuántos se resolvieron y qué quedó pendiente, con el motivo de ahora.
        """
        filas = self._repo.listar(empresa_id)
        if not filas:
            return ResolucionPendientesResult(resueltos=0, pendientes=[])

        anotados = [{
            "empleado_id": f["empleado_id"], "empresa_id": f["empresa_id"],
            "apellido_csv": f["apellido_csv"], "nombre_csv": f.get("nombre_csv"),
            "empleado": _nombre_empleado(f),
            "clave": matcher.clave(f["apellido_csv"], f.get("nombre_csv")),
        } for f in filas]

        resueltos, pendientes = matcher.resolver(anotados, self._empleados)
        self._repo.borrar_muchos(resueltos)
        # Los que siguen pendientes se pisan con el motivo NUEVO. Sin esto, la pantalla mostraría
        # para siempre el motivo del día del import, que puede haber dejado de ser cierto.
        self._repo.upsert_muchos([{
            "empleado_id": p["empleado_id"], "empresa_id": p["empresa_id"],
            "apellido_csv": p["apellido_csv"], "nombre_csv": p["nombre_csv"],
            "motivo": p["motivo"],
        } for p in pendientes])

        logger.info("Resolución manual de superiores pendientes",
                    extra={"resueltos": len(resueltos), "pendientes": len(pendientes)})
        return ResolucionPendientesResult(
            resueltos=len(resueltos),
            pendientes=[SuperiorPendienteItem(
                empleado_id=p["empleado_id"], empleado=p["empleado"],
                superior=_superior(p["apellido_csv"], p.get("nombre_csv")),
                motivo=p["motivo"]) for p in pendientes])


def _superior(apellido: Optional[str], nombre: Optional[str]) -> str:
    """El nombre del jefe tal como vino del CSV, para que un humano lo reconozca."""
    return ", ".join(x for x in (apellido, nombre) if x)


def _nombre_empleado(fila: dict) -> str:
    """'APELLIDO, NOMBRE' del empleado, resuelto por el embed del repo (no está duplicado)."""
    emp = fila.get("empleados") or {}
    partes = [x for x in (emp.get("apellido"), emp.get("nombre")) if x]
    return ", ".join(partes) or "(empleado sin nombre)"


def _item(fila: dict) -> SuperiorPendienteItem:
    return SuperiorPendienteItem(
        empleado_id=fila["empleado_id"], empleado=_nombre_empleado(fila),
        superior=_superior(fila["apellido_csv"], fila.get("nombre_csv")),
        motivo=fila["motivo"])

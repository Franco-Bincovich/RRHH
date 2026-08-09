"""Schemas de la corrida de ingesta de CVs desde la casilla del sistema."""
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class IngestaMailItem(BaseModel):
    """Un mail de la corrida. Los que quedaron pendientes son los que RRHH tiene que mirar."""
    message_id: str
    asunto: str = ""
    remitente: str = ""
    codigo: Optional[str] = None
    candidatos_creados: int = 0
    ya_existian: int = 0
    # Adjuntos que existían y no eran un CV (firmas de imagen, logos). Se muestran para que
    # "traía adjuntos y ninguno servía" no se confunda con "no adjuntó nada".
    descartados: List[str] = []
    # sin_codigo | codigo_ambiguo | vacante_desconocida | sin_adjuntos | sin_cv_valido | error
    motivo: Optional[str] = None
    pendiente: bool = False


class IngestaResponse(BaseModel):
    """El resumen de la corrida.

    ⚠️ `ya_existian` se cuenta APARTE de `candidatos_creados` a propósito: un reintento que
    dijera "0 creados" parecería no haber hecho nada, cuando en realidad confirmó que todo lo de
    esa casilla ya estaba adentro.

    `parcial` + `sin_procesar` son el reporte del corte por presupuesto: sin ellos, una corrida
    que se queda sin tiempo es indistinguible de una que terminó.
    """
    mails_leidos: int
    candidatos_creados: int
    ya_existian: int
    pendientes: List[IngestaMailItem] = []
    parcial: bool = False
    sin_procesar: int = 0
    segundos: float = 0.0


class MailPendienteItem(BaseModel):
    """Un mail de la casilla que no se resolvió solo. NO se persiste: se relee cada vez."""
    message_id: str
    asunto: str = ""
    remitente: str = ""
    fecha: str = ""
    # Cuántos adjuntos parecen un CV, contados SIN bajarlos (extensión + `body.size`).
    adjuntos_validos: int = 0
    nombres_adjuntos: List[str] = []
    motivo: str = ""


class AsignarMailRequest(BaseModel):
    message_id: str
    vacante_id: UUID


class AsignacionResponse(BaseModel):
    """Resultado de asignar un mail o un candidato huérfano a una vacante."""
    candidatos_creados: List[str] = []
    vacante_id: str

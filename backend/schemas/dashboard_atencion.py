"""
Schemas del panel "Requiere tu atención" del dashboard (A6).

Dos clases de alerta CONVIVEN en la misma lista, distinguibles por `origen` — el sistema de
diseño lo pide textual: "Dos tipos de alerta conviviendo: las que calcula el sistema y las que
crea Capital Humano a mano. Que se note cuál es cuál."
  · `"calculada"` — derivada del estado actual del padrón (preingresos próximos, fin de período
    de prueba). No lleva id ni autor: no es una fila, es una LECTURA, y desaparece cuando
    desaparece su causa.
  · `"manual"` — un evento de `eventos_agenda` dentro de su ventana de aviso. Lleva `evento_id`
    (con qué se resuelve) y `creado_por_nombre` (las manuales llevan el nombre de quien las creó).

UN solo endpoint devuelve las dos: el front no une listas ni deduce la forma por el tipo.
"""
from datetime import date
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class AlertaAtencion(BaseModel):
    origen: Literal["calculada", "manual"]
    # "ingreso_proximo" | "fin_periodo_prueba" | "evento_manual". `str` y no Literal: un tipo
    # calculado nuevo no tiene por qué romper el contrato del front, que pinta por `origen`.
    tipo: str
    mensaje: str
    # La fecha del HECHO (el ingreso, el fin de prueba, el evento): es la clave de orden del
    # panel. None = sin fecha derivable; va al final, no desaparece.
    fecha: Optional[date] = None
    href: Optional[str] = None
    # Solo en las manuales. `evento_id` es lo que se le pasa al resolver; una calculada no tiene.
    evento_id: Optional[UUID] = None
    creado_por_nombre: Optional[str] = None


class AtencionResponse(BaseModel):
    alertas: List[AlertaAtencion]


class ResolverAtencionRequest(BaseModel):
    """El body del resolver del panel. `origen` viaja a propósito: es lo que permite responder
    con un código PROPIO (`ALERTA_NO_RESOLUBLE`) cuando el front intenta resolver una calculada,
    en vez de un 404 mudo por un id que no existe."""
    origen: Literal["calculada", "manual"]
    evento_id: Optional[UUID] = None

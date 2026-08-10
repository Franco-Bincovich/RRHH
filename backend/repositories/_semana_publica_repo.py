"""
Las dos lecturas del GET público "lo que cargaste esta semana": las horas y las licencias.

Van juntas y en un módulo propio porque son las DOS MITADES DE UNA MISMA RESPUESTA — el mockup
muestra las cargas de horas y las licencias del período en la misma tabla. Separarlas en el repo
de horas y el de ausencias habría dejado la pregunta partida entre dos módulos que no se
conocen, y a alguien que agrega un filtro teniendo que acordarse de tocar los dos.

🔴 LAS DOS FILTRAN POR `empleado_id` EN EL WHERE, y ese id sale de la SESIÓN, nunca del request.
No hay parámetro de empresa: el empleado ya está identificado, así que acotar de más no agrega
nada — y acotar por una empresa que viniera del request sería aceptar un dato del cliente en una
ruta pública.

⚠️ NO se reusa `_horas_vista_repo.find_por_empleado`: esa trae el período ENTERO de la empresa y
filtra en Python, que está bien para la pantalla interna (ya trajo el mes para agrupar) y sería
absurdo acá — cargar la semana de las 31 personas para devolver la de una.
"""
from typing import List

from integrations.supabase_client import supabase_admin
from repositories._hora_row import build
from schemas.horas import HoraResponse

_HORAS = "horas_proyecto"
_AUSENCIAS = "solicitudes_ausencia"


def horas_de(empleado_id: str, desde: str, hasta: str) -> List[HoraResponse]:
    """Las cargas de horas del empleado en el rango, más recientes primero."""
    filas = (supabase_admin.table(_HORAS).select("*")
             .eq("empleado_id", empleado_id)
             .gte("fecha", desde).lte("fecha", hasta)
             .order("fecha", desc=True).execute().data)
    return build(filas or [])


def licencias_de(empleado_id: str, desde: str, hasta: str) -> List[dict]:
    """Las licencias del empleado que TOCAN el rango, más recientes primero.

    🔴 SEMÁNTICA DE SOLAPAMIENTO, no de contención, y es la misma decisión que
    `repositories/_rango_fechas.py` documenta para vacaciones y ausencias: una licencia del
    viernes al martes TIENE que aparecer en las dos semanas que cruza. Con contención
    desaparecería de las dos y la persona vería una semana que dice que trabajó cuando no lo hizo.
    El predicado es `fecha_desde <= hasta AND fecha_hasta >= desde`; las dos mitades son
    independientes, así que un rango abierto saldría gratis si alguna vez hiciera falta.

    Devuelve dicts crudos y no un schema: la respuesta pública proyecta tres campos y traer el
    `AusenciaResponse` completo —con empresa, tipo y nombres resueltos por join— sería cargar
    para descartar en la línea siguiente, justo en la ruta que menos tiene que devolver.
    """
    filas = (supabase_admin.table(_AUSENCIAS)
             .select("id, fecha_desde, fecha_hasta, dias, motivo")
             .eq("empleado_id", empleado_id)
             .lte("fecha_desde", hasta).gte("fecha_hasta", desde)
             .order("fecha_desde", desc=True).execute().data)
    return filas or []

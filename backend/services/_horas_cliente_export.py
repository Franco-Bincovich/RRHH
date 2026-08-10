"""
Proyección de columnas legibles para el export de "Horas por cliente".

🔴 EL EXPORT ES PLANO, UNA FILA POR CARGA — la pantalla es un árbol y el archivo NO.
Un Excel con jerarquía obliga a quien lo abre a des-agrupar a mano antes de poder filtrar o
hacer una tabla dinámica, que es exactamente para lo que RRHH lo baja. Cada fila lleva su cliente
repetido; el motor de export renderiza escalares, no árboles.

Se proyecta desde las MISMAS filas que alimentan el listado, no desde el árbol ya agrupado: si
saliera del árbol, el archivo perdería el día de cada carga (la agrupación lo colapsa) y dejaría
de servir para conciliar contra nada.
"""
from typing import List

from schemas.horas import HoraResponse

_MODALIDAD = {"home_office": "Home Office", "on_site": "On site"}


def _fecha(v) -> str:
    """dd/mm/aaaa; '' si es None."""
    return v.strftime("%d/%m/%Y") if v else ""


def construir_filas_export(items: List[HoraResponse]) -> List[dict]:
    """Una fila por carga, con nombres resueltos y sin UUIDs crudos.

    "Sin cliente" en vez de vacío: una celda en blanco se lee como un dato que falta, y acá
    significa algo concreto —una carga del camino viejo, que no tiene cliente por diseño—.
    """
    return [
        {
            "Cliente": h.cliente_nombre or "Sin cliente",
            "Empleado": h.empleado_nombre,
            "Empresa": h.empleado_empresa_nombre,
            "Fecha": _fecha(h.fecha),
            "Horas": h.horas,
            "Modalidad": _MODALIDAD.get(h.modalidad or "", ""),
            "Proyecto": h.proyecto_texto,
            "Tarea": h.tarea_texto,
            "Descripción": h.descripcion,
        }
        for h in items
    ]

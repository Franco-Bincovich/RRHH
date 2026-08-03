"""
Helpers compartidos por los generadores de reportes (services/reportes/_reporte_*.py):
formato de período, rango de fechas del mes, normalización de empresa_id y los embeds hacia
`areas`. Sin lógica de dominio.
"""
import calendar
from datetime import date
from typing import Optional
from uuid import UUID

# Embeds hacia `areas` con la FK NOMBRADA. No es una preferencia de estilo: hay más de un
# camino entre esas tablas y sin el hint PostgREST no elige — responde 300 PGRST201 y el
# reporte entero muere. Viven acá, compartidos, porque el nombre de la constraint es un
# detalle que ningún generador debería tener que recordar por su cuenta:
#   · empleados ↔ areas   → empleados.area_id  Y  areas.responsable_id (dos relaciones)
#   · presupuesto_areas ↔ areas → la FK simple Y la compuesta con empresa (dos FKs)
EMBED_AREA_DE_EMPLEADO = "areas!empleados_area_id_fkey(nombre)"
EMBED_AREA_DE_PRESUPUESTO = "areas!presupuesto_areas_area_emp_fkey(nombre)"

_MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def periodo_str(mes: int, anio: int) -> str:
    return f"{_MESES_ES[mes]} {anio}"


def rango_mes(mes: int, anio: int) -> tuple[str, str]:
    """Retorna (inicio, fin) ISO del mes como strings."""
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    return date(anio, mes, 1).isoformat(), date(anio, mes, ultimo_dia).isoformat()


def _eid(empresa_id: Optional[UUID]) -> Optional[str]:
    return str(empresa_id) if empresa_id else None


def _nombre(emp: dict) -> str:
    """'Apellido, Nombre' de una fila de empleados (o de un embed hacia ella).

    Subió acá desde `_reporte_vacaciones.py` cuando R11 se mudó a `_reporte_saldos.py`: los dos
    ordenan sus filas por este string, así que dos copias que se separaran ordenarían distinto
    el mismo listado. Es también la clave con la que se cruzan a mano el reporte y la pantalla.
    """
    return f"{emp.get('apellido', '')}, {emp.get('nombre', '')}".strip(", ").strip()


def _area(emp: dict) -> str:
    """Nombre del área embebida, o 'Sin área'. Nunca None: es texto de una celda."""
    return (emp.get("areas") or {}).get("nombre") or "Sin área"

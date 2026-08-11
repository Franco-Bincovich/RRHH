"""
La agrupación de "Horas por cliente" y sus KPIs. Función PURA: recibe filas, devuelve el árbol.

Se agrupa en PYTHON y no en SQL, igual que `_evaluacion_metricas` y por el mismo motivo: son las
cargas de un mes de una empresa —cientos de filas, no millones— y una vista o un RPC para eso
sería infraestructura que hay que mantener sincronizada a cambio de nada. Molde de la forma:
`services/reportes/_reporte_capacitacion.py` (una query, `acum.setdefault()`, totales).

Al ser pura se prueba sin repo, sin red y sin fechas: se le pasan filas y se mira el árbol.

🔴 LAS FILAS SIN CLIENTE NO SE DESCARTAN: van a un grupo "Sin cliente".
Son las del camino viejo (`POST /api/proyectos/{id}/horas`), que no tienen `cliente_id`. Tirarlas
habría sido lo natural en una pantalla que se llama "Horas por cliente", y habría hecho que unas
horas cargadas y válidas desaparezcan sin que nadie lo note — el modo de falla que este repo ya
documentó tres veces. Que aparezcan agrupadas aparte es además la única forma de que RRHH VEA que
existen y decida qué hacer con ellas.
"""
from typing import Any, Dict, List, Tuple

# Etiqueta del grupo de las filas sin cliente. Ver la nota del encabezado.
SIN_CLIENTE = "Sin cliente"

# 🔴 EL DESGLOSE POR SOCIEDAD (L8). El total de un cliente ya no se recorta por empresa: son
# sociedades de un mismo grupo y las horas del cliente son todas. Pero el reparto sigue haciendo
# falta —para saber qué sociedad puso qué—, así que en vez de perderse en el filtro se muestra
# ADENTRO de cada cliente. Sale de `empleado_empresa_nombre`, que la fila ya trae resuelto (es la
# misma columna que usa el export): no hace falta ningún join nuevo.
SIN_EMPRESA = "Sin empresa"


def _linea_clave(h) -> Tuple:
    """Una línea del detalle es (empleado, proyecto, tarea, modalidad).

    Se agrega por esas cuatro y no una fila por carga: alguien que carga tres veces "Reunión"
    para el mismo cliente el mismo día quiere ver 6 h en un renglón, no tres renglones de 2. El
    día por día está en el "ver detalle", que es otro endpoint."""
    return (str(h.empleado_id or ""), h.empleado_nombre or "", h.proyecto_texto or "",
            h.tarea_texto or "", h.modalidad or "")


def agrupar(filas: List) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Filas enriquecidas → (kpis, clientes). Con la lista vacía devuelve KPIs en 0 y [].

    Returns:
        kpis: horas_totales · clientes_con_carga · empleados_que_cargaron · registros
        clientes: [{cliente_id, cliente_nombre, horas, registros, por_empresa: [...], lineas: [...]}]

    `por_empresa` reparte las MISMAS horas del cliente por sociedad: su suma es `horas`, siempre.
    """
    acum: Dict[str, Dict[str, Any]] = {}
    empleados: set = set()
    clientes_reales: set = set()
    horas_totales = 0.0

    for h in filas:
        horas = float(h.horas or 0)
        horas_totales += horas
        if h.empleado_id:
            empleados.add(str(h.empleado_id))
        clave = str(h.cliente_id) if h.cliente_id else SIN_CLIENTE
        if h.cliente_id:
            clientes_reales.add(clave)

        grupo = acum.setdefault(clave, {
            "cliente_id": str(h.cliente_id) if h.cliente_id else None,
            "cliente_nombre": h.cliente_nombre or SIN_CLIENTE,
            "horas": 0.0, "registros": 0, "_lineas": {}, "_empresas": {},
        })
        grupo["horas"] += horas
        grupo["registros"] += 1
        empresa = h.empleado_empresa_nombre or SIN_EMPRESA
        grupo["_empresas"][empresa] = grupo["_empresas"].get(empresa, 0.0) + horas

        emp_id, emp_nombre, proyecto, tarea, modalidad = _linea_clave(h)
        linea = grupo["_lineas"].setdefault((emp_id, proyecto, tarea, modalidad), {
            "empleado_id": emp_id or None, "empleado_nombre": emp_nombre or None,
            "proyecto_texto": proyecto or None, "tarea_texto": tarea or None,
            "modalidad": modalidad or None, "horas": 0.0, "registros": 0,
        })
        linea["horas"] += horas
        linea["registros"] += 1

    clientes = [
        {**{k: v for k, v in g.items() if not k.startswith("_")},
         "horas": round(g["horas"], 2),
         # Mayor primero, y a igualdad por nombre: sin desempate estable el orden dependería del
         # de inserción, o sea del orden en que vinieron las filas de la base.
         "por_empresa": sorted(
             ({"empresa_nombre": n, "horas": round(hs, 2)} for n, hs in g["_empresas"].items()),
             key=lambda x: (-x["horas"], x["empresa_nombre"])),
         "lineas": sorted(
             ({**ln, "horas": round(ln["horas"], 2)} for ln in g["_lineas"].values()),
             key=lambda x: (-x["horas"], x["empleado_nombre"] or ""))}
        for g in acum.values()
    ]
    kpis = {
        "horas_totales": round(horas_totales, 2),
        # Cuenta clientes REALES: el grupo "Sin cliente" no es un cliente, y sumarlo daría un KPI
        # que dice que hay uno más de los que RRHH tiene cargados.
        "clientes_con_carga": len(clientes_reales),
        "empleados_que_cargaron": len(empleados),
        "registros": len(filas),
    }
    return kpis, sorted(clientes, key=lambda c: (-c["horas"], c["cliente_nombre"]))

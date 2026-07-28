"""
Primitivas compartidas del repositorio de nómina: la tabla, el SELECT con joins y el mapper de
fila. Aisladas para que el repo no pase su límite de líneas al sumarle el conteo que necesita
el control de tamaño del export.

Molde: _empleado_row.py. El movimiento es puro — el SELECT y el mapper son idénticos a los que
estaban embebidos en nomina_repo.py.

Las dos FKs nombradas del SELECT no son decoración: `costos_nomina` tiene DOS caminos hacia
`empleados` (la simple y la compuesta por empresa) y `empleados` tiene DOS hacia `areas`
(area_id, y responsable_id en sentido inverso). Sin nombrar la constraint, PostgREST no elige
y devuelve PGRST201 en vez de datos.
"""
from schemas.costo import NominaResponse

TABLE = "costos_nomina"

SELECT = (
    "id,empleado_id,empresa_id,mes,anio,salario_bruto,cargas_sociales,total,"
    "empleados!costos_nomina_empleado_emp_fkey(nombre,apellido,areas!empleados_area_id_fkey(nombre)),"
    "empresas(nombre)"
)


def row(r: dict) -> NominaResponse:
    """Convierte un dict de Supabase en NominaResponse.

    Resuelve los nombres embebidos (empleado, área, empresa) y deriva el neto restándole las
    cargas sociales al bruto, que es como se guarda: la tabla persiste bruto y cargas, no neto.
    """
    emp = r.get("empleados") or {}
    area = emp.get("areas") or {}
    empresa = r.get("empresas") or {}
    bruto = float(r.get("salario_bruto") or 0)
    cargas = float(r.get("cargas_sociales") or 0)
    return NominaResponse(
        id=str(r["id"]),
        empleado_id=str(r["empleado_id"]),
        empresa_id=str(r["empresa_id"]) if r.get("empresa_id") else None,
        empresa_nombre=empresa.get("nombre"),
        empleado_nombre=f"{emp.get('nombre', '')} {emp.get('apellido', '')}".strip(),
        area_nombre=area.get("nombre", "Sin área"),
        mes=int(r["mes"]),
        anio=int(r["anio"]),
        monto_bruto=bruto,
        monto_neto=bruto - cargas,
        total=float(r.get("total") or 0),
    )

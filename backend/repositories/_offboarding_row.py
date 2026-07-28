"""
Primitivas compartidas del repositorio de offboarding: las tablas, el SELECT con joins y los
mappers de fila. Aisladas para que el repo no pase su límite de líneas al sumarle la escritura
de la entrevista de salida.

Molde: _empleado_row.py y _nomina_row.py. El movimiento es puro — el SELECT y los dos mappers
son idénticos a los que estaban embebidos en offboarding_repo.py.

`offboarding_instancias` tiene DOS FKs hacia `empleados` (la simple y la compuesta por
empresa), así que el embed nombra la constraint: sin eso PostgREST no elige y devuelve
PGRST201 en vez de datos.
"""
from schemas.offboarding import ActivoResponse, OffboardingResponse

TABLA_INSTANCIAS = "offboarding_instancias"
TABLA_ACTIVOS = "offboarding_activos"

SELECT_JOINS = "empleados!offboarding_instancias_empleado_id_fkey(nombre,apellido), empresas(nombre)"


def activo_row(r: dict) -> ActivoResponse:
    """Convierte un dict de Supabase en ActivoResponse. `devuelto` se deriva del estado."""
    return ActivoResponse(
        id=r["id"], tipo_activo=r["tipo_activo"], descripcion=r.get("descripcion"),
        estado=r["estado"], devuelto=r["estado"] == "devuelto",
    )


def inst_row(r: dict, activos: list) -> OffboardingResponse:
    """Convierte un dict de Supabase en OffboardingResponse.

    El progreso no se persiste: se calcula acá como porcentaje de activos devueltos sobre el
    total. `motivo` sale de la columna `motivo_egreso`, que es su nombre real en la tabla.
    """
    emp = r.get("empleados") or {}
    empresa = r.get("empresas") or {}
    total = len(activos)
    devueltos = sum(1 for a in activos if a.get("estado") == "devuelto")
    return OffboardingResponse(
        id=r["id"], empleado_id=r["empleado_id"],
        empresa_id=r.get("empresa_id"), empresa_nombre=empresa.get("nombre"),
        empleado_nombre=f"{emp.get('nombre', '')} {emp.get('apellido', '')}".strip(),
        motivo=r["motivo_egreso"], estado=r["estado"],
        fecha_inicio=str(r.get("created_at", ""))[:10],
        progreso=round(devueltos / total * 100) if total else 0,
        entrevista_salida=bool(r.get("entrevista_salida")),
        notas_entrevista=r.get("notas_entrevista"),
        activos=[activo_row(a) for a in activos], accesos=[],
    )

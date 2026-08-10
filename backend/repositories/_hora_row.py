"""
El mapper de `horas_proyecto` a schema, con sus lookups por lotes. Fuente de verdad ÚNICA.

SALIÓ DE `horas_repo.py`, que quedaba en 118 contra un límite de 100 al sumarle la resolución
del empleado directo y del nombre del cliente (migración 103). Molde: `_tipo_ausencia_row.py` y
`_empleado_row.py`, que hacen exactamente esto y por el mismo motivo — que la forma de la
lectura y la traducción a schema no puedan divergir entre dos lugares.

🔴 DE QUIÉN SON LAS HORAS: DOS ORÍGENES, Y EL ORDEN IMPORTA
  · CAMINO NUEVO (carga directa): la fila trae `empleado_id` propio. No hay asignación.
  · CAMINO VIEJO (POST /api/proyectos/{id}/horas): `empleado_id` es NULL y el empleado se
    alcanza por `asignacion_id -> proyecto_asignaciones.empleado_id`, como siempre.
Se prueba primero la columna propia y se cae a la asignación. Al revés daría el mismo resultado
hoy (el camino viejo no escribe `empleado_id`), pero dejaría a la asignación pisando un dato
explícito el día que alguien backfillee la columna.

⚠️ `empleado_empresa_nombre` SALE DE LA COLUMNA PROPIA DE LA FILA, no de la asignación.
`horas_proyecto.empleado_empresa_id` es NOT NULL y el service viejo la escribe copiándola de la
asignación, así que para el camino viejo el valor es idéntico — y para el nuevo es el único que
existe. Resolverla por la asignación, como se hacía antes, dejaba las cargas directas sin
empresa y gastaba un join para llegar a un dato que la fila ya tenía.

🔴 LOS CUATRO `select` VAN CON EL SPEC LITERAL EN EL CALL SITE, no adentro de un helper.
`tests/test_selects_repos.py` resuelve los specs por AST contra `db/schema.sql`: un
`.select(variable)` no se puede resolver y habría que declararlo en `SIN_RESOLVER_DECLARADOS`,
o sea sacarlo del barrido. Con `clientes` recién creada eso es justo lo que NO se quiere — es la
tabla nueva, la que más chances tiene de tener un nombre mal escrito. Construir el objeto query
antes de saber si hay ids es gratis: no hay I/O hasta el `.execute()`.

Todos los lookups son BATCH: una query por dimensión, nunca una por fila (mismo patrón que
`_proyectos_enrich` y `_evaluacion_lotes_enrich`).
"""
from typing import List

from integrations.supabase_client import supabase_admin
from schemas.horas import HoraResponse


def _mapa(query, ids: set, armar) -> dict:
    """{id: valor} para una dimensión. Sin ids no dispara ninguna query."""
    if not ids:
        return {}
    filas = query.in_("id", sorted(ids)).execute().data or []
    return {f["id"]: armar(f) for f in filas}


def build(rows: List[dict]) -> List[HoraResponse]:
    """Filas crudas de horas_proyecto → HoraResponse, con empleado, empresa y cliente resueltos."""
    if not rows:
        return []
    asig_map = _mapa(
        supabase_admin.table("proyecto_asignaciones").select("id, empleado_id"),
        {r["asignacion_id"] for r in rows if r.get("asignacion_id")},
        lambda a: a["empleado_id"])

    # El empleado de cada fila: columna propia primero, asignación después (ver el encabezado).
    emp_de_fila = {r["id"]: r.get("empleado_id") or asig_map.get(r.get("asignacion_id"))
                   for r in rows}

    emp_map = _mapa(
        supabase_admin.table("empleados").select("id, nombre, apellido"),
        {e for e in emp_de_fila.values() if e},
        lambda e: f"{e['nombre']} {e['apellido']}")
    empresa_map = _mapa(
        supabase_admin.table("empresas").select("id, nombre"),
        {r["empleado_empresa_id"] for r in rows if r.get("empleado_empresa_id")},
        lambda e: e["nombre"])
    cliente_map = _mapa(
        supabase_admin.table("clientes").select("id, nombre"),
        {r["cliente_id"] for r in rows if r.get("cliente_id")},
        lambda c: c["nombre"])

    resultado: List[HoraResponse] = []
    for r in rows:
        snap = r.get("valor_hora_snapshot")
        empleado_id = emp_de_fila.get(r["id"])
        resultado.append(HoraResponse.model_validate({
            **r,
            "empleado_id": empleado_id,
            "empleado_nombre": emp_map.get(empleado_id),
            "empleado_empresa_nombre": empresa_map.get(r.get("empleado_empresa_id")),
            "cliente_nombre": cliente_map.get(r.get("cliente_id")),
            # None y NO 0.0 sin snapshot: "no se puede costear" ≠ "costó cero". Ver HoraResponse.
            "costo": None if snap is None else round(float(r["horas"]) * float(snap), 2),
        }))
    return resultado

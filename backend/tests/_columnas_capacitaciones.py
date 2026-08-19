"""
Inventario declarativo de las columnas de `capacitaciones` y `empleado_capacitacion`: qué se
expone, qué NO viaja al front (con la razón) y qué campo del schema es un DERIVADO de joins.

Helper, no test. Lo consume `tests/test_columnas_capacitaciones.py`. Molde:
`tests/_columnas_candidatos.py` + `tests/test_columnas_candidatos.py` (el barrido que salió del
bug de `candidatos.estado`).

🔴 POR QUÉ ES UN ARCHIVO APARTE Y NO UNA GENERALIZACIÓN DEL DE CANDIDATOS. Estas dos tablas
tienen algo que `candidatos` no: sus Responses publican campos que NO son columnas
(`empresa_nombre`, `capacitacion_nombre`, `empleado_nombre`, `area_id`, `area_nombre` — joins
resueltos por `_build`). El barrido de candidatos usa a propósito la clase BASE sin derivados, y
meterle un concepto `DERIVADOS` que su tabla no necesita sería reescribir un barrido ya
entregado para servir a un caso ajeno. Acá el concepto es necesario y el runner lo parametriza
por tabla; el día que un TERCER módulo con derivados lo necesite, el molde a copiar es este.

🔴 LA RAZÓN DE CADA ENTRADA ES EL CONTENIDO DE ESTE ARCHIVO, NO UN CAMPO A COMPLETAR. Sin el
porqué, la próxima persona borra una entrada porque "no se usa" y revive el bug que el barrido
existe para impedir: seis columnas de estas dos tablas (mig 116) vivieron del lado equivocado de
la distinción entre "se decidió no exponerla" y "se olvidaron" hasta el 19/8/2026.
"""
import os

_TEST_ENV: dict[str, str] = {
    "SUPABASE_URL": "https://test-project.supabase.co",
    "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.anon",
    "SUPABASE_SERVICE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.service",
    "JWT_SECRET": "test-secret-for-unit-tests-only-minimum-32-chars!!",
    "ANTHROPIC_API_KEY": "sk-ant-test",
    "RESEND_API_KEY": "re_test",
}
for _k, _v in _TEST_ENV.items():
    os.environ.setdefault(_k, _v)

from typing import Dict, Set  # noqa: E402

from schemas.capacitacion import AsignacionResponse, CapacitacionResponse  # noqa: E402
from tests._postgrest_schema import cargar_schema  # noqa: E402

# La razón de `updated_at` es la misma en las dos tablas (y la misma que en candidatos).
_UPDATED_AT = (
    "metadato de fila que mantiene un trigger. Ningún response del repo lo publica; quién "
    "tocó qué y cuándo se lee en /auditoria, que es el registro que sí lo responde."
)

# ── El inventario, POR TABLA ──────────────────────────────────────────────────
# `schema`: la clase Pydantic que publica la fila.  `no_expuestas`: columnas que a propósito no
# viajan, con su razón.  `derivados`: campos del schema que NO son columnas — los resuelve el
# enriquecido (`_build`) con lookups batch, y por eso la dirección inversa del barrido los
# permite en vez de acusarlos de "campo sin columna detrás".
# Los mínimos son la guarda contra el falso verde: hoy son 13/15 columnas y 14/19 campos; van
# holgados para no ser ruido en cada alta o baja de una columna.
INVENTARIOS: Dict[str, dict] = {
    "capacitaciones": {
        "schema": CapacitacionResponse,
        "no_expuestas": {"updated_at": _UPDATED_AT},
        "derivados": {
            "empresa_nombre": "join a `empresas` resuelto por `capacitacion_repo._build`; "
                              "la tabla guarda `empresa_id`, la pantalla muestra el nombre.",
        },
        "minimo_columnas": 10,
        "minimo_campos": 8,
    },
    "empleado_capacitacion": {
        "schema": AsignacionResponse,
        "no_expuestas": {"updated_at": _UPDATED_AT},
        "derivados": {
            "empresa_nombre": "join a `empresas` resuelto por `_asignacion_row._build` "
                              "(lookup batch); la columna real es `empresa_id`.",
            "capacitacion_nombre": "join a `capacitaciones` resuelto por `_asignacion_row."
                                   "_build`; la columna real es `capacitacion_id`.",
            "empleado_nombre": "join a `empleados` resuelto por `_asignacion_row._build`; "
                               "None en las filas de nombre libre (mig 116), a propósito.",
            "area_id": "ni siquiera es de esta tabla: sale del EMPLEADO de la fila "
                       "(`empleados.area_id`), por eso las filas de nombre libre la tienen None.",
            "area_nombre": "segundo salto del mismo camino: `empleados.area_id` → "
                           "`areas.nombre`, resuelto por `_asignacion_row._build`.",
        },
        "minimo_columnas": 12,
        "minimo_campos": 12,
    },
}


def columnas(tabla: str) -> Set[str]:
    """Las columnas reales de la tabla, del catálogo de reconstrucción (`db/schema.sql`)."""
    return cargar_schema().columnas[tabla]


def campos(tabla: str) -> Set[str]:
    """Los campos que el Response de la tabla declara."""
    return set(INVENTARIOS[tabla]["schema"].model_fields)

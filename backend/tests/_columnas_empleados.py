"""
Inventario declarativo de las columnas de `empleados`: qué se expone, qué NO viaja al front (con
la razón) y qué campo del schema es un DERIVADO de joins.

Helper, no test. Lo consume `tests/test_columnas_empleados.py`. Molde: `_columnas_capacitaciones`
+ su runner, que es el que introdujo el concepto `DERIVADOS`.

🔴 POR QUÉ LLEGÓ TARDE A LA TABLA CENTRAL, que es lo que hay que entender para que no se repita.
El patrón nació en `candidatos` (19/8/2026) y se extendió a `capacitaciones` y
`empleado_capacitacion` ese mismo día. `empleados` —la tabla de la que cuelga TODO el producto,
58 columnas, la que más migraciones acumula— se quedó afuera, y el precio se pagó el 25/8/2026:
**doce columnas que la base tenía y `EmpleadoResponse` descartaba en silencio**, siete de ellas
CON DATO en producción. La más cara era `fecha_ingreso_reconocida`, que **decide el cupo de
vacaciones** y no se mostraba en ninguna pantalla: alguien con un cupo distinto al que su fecha de
ingreso sugiere no tenía forma de saber por qué.

⚠️ NO CONFUNDIR ESTE BUG CON EL DE `organismo`/`sector`/`perfil`, que apareció en la misma tanda
y es el CONTRARIO. Esas tres SÍ estaban expuestas por el schema desde siempre; la ficha mostraba
un guion porque **ninguna fila las tiene cargadas** (0 de 41): el import de nómina lee las
columnas "Organismo" y "Sector" del CSV y las desvía a resolver empresa y área, sin escribir nunca
las columnas del mismo nombre. Un barrido de columnas **no puede ver ese caso** —el schema y la
tabla coinciden perfecto— y este archivo no pretende cubrirlo. Lo que sí cubre es el otro: la
columna que existe, viaja en el `select("*")`, y Pydantic tira.

🔴 LA RAZÓN DE CADA ENTRADA ES EL CONTENIDO DE ESTE ARCHIVO, NO UN CAMPO A COMPLETAR. Sin el
porqué, la próxima persona borra una entrada porque "no se usa" y revive el bug.
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

from schemas.empleado_out import EmpleadoResponse  # noqa: E402
from tests._postgrest_schema import cargar_schema  # noqa: E402

TABLA = "empleados"

# ── Las columnas que NO viajan, cada una con su razón ─────────────────────────
#
# 🔴 SON CINCO Y ERAN DOCE hasta el 25/8/2026 (bloque N6). Las siete que salieron de esta lista
# —`fecha_ingreso_reconocida`, `potencial`, `desempeno`, `liderazgo`, `product_owner`,
# `co_sourcing`, `equipo`— no se declararon: se EXPUSIERON, porque ninguna tenía una razón para
# estar oculta. Nunca hubo una decisión de no mostrarlas; simplemente nadie las agregó al schema
# cuando la migración las creó, que es exactamente la diferencia que este inventario existe para
# hacer visible.
NO_EXPUESTAS: Dict[str, str] = {
    "user_id": (
        "el vínculo con la cuenta de `users`, y NO es un dato del legajo: dice si esa persona "
        "puede entrar al sistema, que es una pregunta de /usuarios y no de la ficha. Hoy está "
        "en 2 de 41 (los operadores de Capital Humano); publicarlo en el response del empleado "
        "expondría un id de auth en toda lectura de listado, export incluido."
    ),
    "foto_url": (
        "no hay foto en el producto: la ficha usa el monograma de iniciales de §3 y no hay "
        "ningún camino que suba una imagen de persona (Storage sirve adjuntos, no avatares). "
        "0 de 41 filas. Exponerla sería publicar un campo que nadie escribe ni pinta."
    ),
    "updated_at": (
        "metadato de fila que mantiene un trigger. Ningún response del repo lo publica; quién "
        "tocó qué y cuándo se lee en /auditoria, que es el registro que sí lo responde."
    ),
    "fecha_ingreso_prevista": (
        "🔴 COLUMNA MUERTA de la migración 113, no una decisión de producto. La creó para "
        "separar la fecha del TRÁMITE de la EFECTIVA, y **no la escribe ni la lee una sola "
        "línea del código** (verificado por grep el 25/8/2026, cero referencias fuera de "
        "schema.sql): 0 de 41 filas. Exponerla publicaría un campo que siempre vale null. "
        "El disparador para sacarla de acá es que alguien construya el flujo de trámite; si "
        "eso no pasa, lo que corresponde es dropear la columna, no declararla para siempre."
    ),
    "fecha_baja_prevista": (
        "🔴 La hermana de `fecha_ingreso_prevista` y el MISMO caso, con el mismo disparador: "
        "migración 113, cero escritores, cero lectores, 0 de 41 filas. Se declaran por separado "
        "y no como un par para que el día que una se use, la otra no salga arrastrada."
    ),
}

# ── Campos del schema que NO son columnas ─────────────────────────────────────
DERIVADOS: Dict[str, str] = {
    "empresa_nombre": (
        "join a `empresas` embebido en el SELECT de `_empleado_row`; la columna real es "
        "`empresa_id`, y la pantalla muestra el nombre de la sociedad."
    ),
    "area_nombre": (
        "join a `areas!empleados_area_id_fkey` embebido en el mismo SELECT. La FK va NOMBRADA "
        "a propósito: hay más de una relación entre `empleados` y `areas` "
        "(`areas.responsable_id`), y sin nombrarla PostgREST responde PGRST201."
    ),
    "manager_nombre": (
        "self-join a `empleados` por la COLUMNA FK (`manager:manager_id`), no por el nombre de "
        "la constraint —que es autogenerado y difiere entre entornos—. La columna real es "
        "`manager_id`; `_empleado_row.row` arma 'Apellido, Nombre'."
    ),
}

# Guardas contra el falso verde. Hoy son 58 columnas y 56 campos; van holgadas para no ser ruido
# en cada alta o baja de una columna, pero muerden si el parseo de schema.sql se rompe.
MINIMO_COLUMNAS = 45
MINIMO_CAMPOS = 45


def columnas() -> Set[str]:
    """Las columnas reales de `empleados`, del catálogo de reconstrucción (`db/schema.sql`)."""
    return cargar_schema().columnas[TABLA]


def campos() -> Set[str]:
    """Los campos que `EmpleadoResponse` declara."""
    return set(EmpleadoResponse.model_fields)

"""
La identidad de una ausencia: (empleado, fecha_desde, fecha_hasta, tipo) — migración 089.

Es la clave de idempotencia del import mensual de novedades: subir el mismo archivo dos veces
tiene que actualizar, no duplicar.

⚠️ ESTE TEST ES ESTRUCTURAL, Y HAY QUE SABER QUÉ **NO** PRUEBA. Un índice único lo hace cumplir
Postgres, y la suite corre sin base: acá no se puede insertar dos filas y ver que la segunda
falle. Lo que sí se verifica —y es lo que se rompe en la práctica— es que la constraint esté
DECLARADA en `db/schema.sql`, que es la fuente de reconstrucción y lo que lee
`tests/_postgrest_schema.py`. Una migración que no se refleja ahí existe en producción y no en el
repo, y el próximo que reconstruya la base desde cero se queda sin ella.

La unicidad real se verificó contra el catálogo vivo antes de escribir la migración: 0 filas y
0 duplicados por esa clave, así que `CREATE UNIQUE INDEX` no puede fallar hoy.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
  · Se lee `db/schema.sql` REAL, no una copia. Si alguien corre la migración en producción y se
    olvida de reflejarla, este test lo ve.
  · Las cuatro columnas se afirman UNA POR UNA: un índice sobre tres de ellas pasaría un
    `"uq_ausencia" in texto` y dejaría entrar duplicados que difieren en la cuarta.
"""
import os

_TEST_ENV: dict[str, str] = {
    "SUPABASE_URL": "https://test-project.supabase.co",
    "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.anon",
    "SUPABASE_SERVICE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.service",
    "JWT_SECRET": "test-secret-for-unit-tests-only-minimum-32-chars!!",
    "ANTHROPIC_API_KEY": "sk-ant-test",
}
for _k, _v in _TEST_ENV.items():
    os.environ.setdefault(_k, _v)

import re
from pathlib import Path

import pytest

_SCHEMA = (Path(__file__).resolve().parent.parent / "db" / "schema.sql").read_text(encoding="utf-8")
_INDICE = next((ln for ln in _SCHEMA.splitlines()
                if "uq_ausencia_empleado_rango_tipo" in ln and ln.startswith("CREATE")), "")


def test_el_indice_esta_declarado_en_schema_sql() -> None:
    """Sin esto, la constraint viviría solo en producción y no en la fuente de reconstrucción."""
    assert _INDICE, "falta el índice de unicidad de ausencias en db/schema.sql"
    assert "UNIQUE" in _INDICE, "el índice existe pero NO es único: no impediría el duplicado"


def test_es_sobre_solicitudes_ausencia() -> None:
    assert "solicitudes_ausencia" in _INDICE


@pytest.mark.parametrize("columna", ["empleado_id", "fecha_desde", "fecha_hasta", "tipo_id"])
def test_la_clave_lleva_las_cuatro_columnas(columna: str) -> None:
    """🔴 Una por una, y no un `in` sobre el nombre del índice: con tres columnas el índice
    existiría igual y dejaría pasar duplicados que difieren en la cuarta. Sacar `tipo_id`, por
    ejemplo, prohibiría dos ausencias de TIPOS DISTINTOS en el mismo rango — que es legal."""
    columnas = re.search(r"\(([^)]*)\)\s*;?\s*$", _INDICE)
    assert columnas and columna in columnas.group(1)


def test_vacaciones_pendientes_ya_tiene_la_suya() -> None:
    """El otro import se apoya en una UNIQUE que YA existía (mig 083): no hace falta crearla.
    Verificado también contra el catálogo vivo — `vacaciones_pendientes_empleado_periodo_key`."""
    assert re.search(r"vacaciones_pendientes.*UNIQUE \(empleado_id, periodo\)", _SCHEMA)


def test_el_indice_NO_prohibe_solapamientos_parciales() -> None:
    """La clave es el rango EXACTO, no un rango que se pise. `ausencias_service` documenta que el
    solapamiento no se valida, y esta migración no lo contradice: prohíbe un subconjunto
    estricto. Si alguien cambiara el índice por uno con `daterange` y `EXCLUDE`, esto lo frena."""
    assert "EXCLUDE" not in _INDICE and "daterange" not in _INDICE

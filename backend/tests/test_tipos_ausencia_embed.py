"""
🔴 El embed de la self-FK de tipos_ausencia NO puede dar PGRST201.

El problema: desde la migración 088 hay DOS relaciones entre `tipos_ausencia` y sí misma —
`padre_id` hacia arriba y su inversa hacia abajo. Un embed `tipos_ausencia(nombre)` a secas se
lee perfecto y PostgREST lo rechaza con **300 PGRST201** (relación ambigua). El síntoma en
producción sería el catálogo de tipos devolviendo un error, o —peor— una pantalla en blanco.

Es EXACTAMENTE la clase de bug que `tests/_postgrest_schema.py` existe para atrapar: seis
reportes se entregaron "completos" y nunca funcionaron por embeds ambiguos, porque el fake de
Supabase acepta cualquier spec exista o no la relación. El validador lee `db/schema.sql` y
resuelve el embed como lo haría PostgREST.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
  · Se valida el SELECT REAL (`_tipo_ausencia_row.SELECT`), no una copia escrita en el test. Si
    alguien le saca el `!tipos_ausencia_padre_id_fkey` al SELECT de producción, este test lo ve.
    Con una copia, el test seguiría en verde sobre un string que ya no se usa.
  · El test de control afirma que la versión AMBIGUA **sí** falla: sin él, un validador que
    aceptara todo daría verde en el test de arriba sin haber comprobado nada.
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

import pytest

from repositories._tipo_ausencia_row import SELECT
from tests._postgrest_schema import SelectInvalidoError, cargar_schema

SCHEMA = cargar_schema()


def test_el_select_real_de_tipos_ausencia_es_valido() -> None:
    """El SELECT que usa el repo EN PRODUCCIÓN, validado contra schema.sql como lo haría
    PostgREST. Para que falle: sacarle el hint de FK al embed del padre."""
    SCHEMA.validar_select("tipos_ausencia", SELECT)


def test_la_columna_padre_id_existe_en_el_schema() -> None:
    """Si la 088 no estuviera reflejada en schema.sql, el validador no podría ver la self-FK y
    todo lo de acá pasaría sin comparar nada."""
    assert "padre_id" in SCHEMA.columnas["tipos_ausencia"]


def test_el_embed_SIN_hint_de_FK_es_rechazado() -> None:
    """🔴 EL CONTROL DEL CONTROL. Sin este test, un validador permisivo daría verde arriba sin
    haber verificado nada. Acá se le pasa la versión ambigua a propósito y tiene que romper."""
    with pytest.raises(SelectInvalidoError):
        SCHEMA.validar_select("tipos_ausencia", "id, nombre, tipos_ausencia(nombre)")


def test_el_embed_con_una_FK_inventada_tambien_se_rechaza() -> None:
    """Nombrar CUALQUIER cosa no alcanza: el nombre tiene que ser el de una FK real."""
    with pytest.raises(SelectInvalidoError):
        SCHEMA.validar_select("tipos_ausencia", "id, padre:tipos_ausencia!fk_inventada(nombre)")

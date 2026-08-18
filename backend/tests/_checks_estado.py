"""
Los valores que cada CHECK de una columna `estado` acepta, leídos de `db/schema.sql`.

Helper, no test. Lo consume `tests/test_procesos_estados.py`.

🔴 POR QUÉ NO VIVE EN `_postgrest_schema.py`, que es el otro lector de `schema.sql`: ese módulo
está en 194/200 y esto son ~35 líneas. El corte además cae en una costura real — aquél responde
"¿este `select` sobrevive a PostgREST?" (nombres y relaciones) y esto responde "¿qué VALORES
acepta esta columna?", que es otra pregunta sobre el mismo archivo.

## El formato no es uno solo, y por eso el regex es laxo

`schema.sql` se lee del catálogo, así que la forma del CHECK depende del tipo de la columna:

    CHECK ((estado = ANY (ARRAY['pendiente'::text, ...])))                       -- text
    CHECK (((estado)::text = ANY ((ARRAY['nueva'::character varying, ...])::text[])))  -- varchar

Un regex atado a una de las dos formas devuelve `None` para la mitad de las tablas **y eso pasa
como "no hay CHECK que contrastar"**, o sea en verde. Por eso se captura el cuerpo entero del
CHECK y se extraen los literales entrecomillados de adentro: las dos formas los escriben igual.
Se midió contra las 11 tablas con CHECK sobre `estado` y las 11 resuelven.
"""
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional, Set

_SCHEMA = Path(__file__).resolve().parent.parent / "db" / "schema.sql"

# El cuerpo entero del CHECK, sin asumir cuál de las dos formas es. Los literales salen después.
_RE_CHECK = r"ADD CONSTRAINT {tabla}_estado_check CHECK \((.*?)\);"


@lru_cache(maxsize=1)
def _sql() -> str:
    return _SCHEMA.read_text(encoding="utf-8")


def valores_check(tabla: str) -> Optional[Set[str]]:
    """Los valores que acepta `<tabla>.estado`, o None si esa tabla no tiene CHECK.

    Devolver `None` y no un set vacío es deliberado: "no hay CHECK" y "el CHECK no acepta nada"
    son cosas distintas, y quien llame tiene que poder distinguirlas para no contrastar contra
    un conjunto vacío creyendo que contrastó contra algo.
    """
    m = re.search(_RE_CHECK.format(tabla=re.escape(tabla)), _sql(), re.S)
    return set(re.findall(r"'([^']+)'", m.group(1))) if m else None

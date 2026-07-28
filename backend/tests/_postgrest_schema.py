"""
Validador de specs de PostgREST contra `db/schema.sql`.

POR QUÉ EXISTE. El fake de Supabase de la suite implementa `select(*a, **k)` ignorando el
argumento: acepta cualquier spec, exista o no la columna. Eso hace que un `select` mal escrito
pase los tests y falle recién en el primer request real — que es como seis de los once reportes
de Fase 1 llegaron a producción sin funcionar nunca. Los tests no mentían sobre la lógica; no
miraban los nombres.

Este módulo cierra ese hueco: lee la fuente de verdad de reconstrucción (`db/schema.sql`) y
valida un spec como lo haría PostgREST, detectando las dos fallas que se vieron:

  · columna inexistente        → PostgREST responde 400 42703
  · embed sin FK nombrada      → PostgREST responde 300 PGRST201, cuando hay MÁS DE UNA
                                 relación entre las dos tablas y no puede elegir

La segunda es la traicionera: `areas(nombre)` desde `empleados` se lee perfecto y es ambiguo,
porque además de `empleados.area_id → areas` existe `areas.responsable_id → empleados`. Basta
con que alguien agregue una FK para que un embed que venía andando se vuelva ambiguo, y el
único síntoma sea un reporte en blanco.

Lo que NO valida: tipos, filtros, RLS ni la existencia de filas. Solo nombres y relaciones —
que es lo que el fake no puede ver.
"""
import re
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Set

_SCHEMA = Path(__file__).resolve().parent.parent / "db" / "schema.sql"

_RE_TABLA = re.compile(r"CREATE TABLE (?:public\.)?(\w+)\s*\((.*?)\n\);", re.S)
_RE_FK = re.compile(
    r"ALTER TABLE (?:public\.)?(\w+) ADD CONSTRAINT (\w+) FOREIGN KEY \(([^)]+)\) "
    r"REFERENCES (?:public\.)?(\w+)",
)
# Una línea de columna arranca con el nombre; las de constraint arrancan con una palabra clave.
_NO_ES_COLUMNA = ("CONSTRAINT", "PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "EXCLUDE")


class SelectInvalidoError(Exception):
    """El spec no sobreviviría a PostgREST. El mensaje dice qué y por qué."""


class Relacion(NamedTuple):
    origen: str
    destino: str
    constraint: str
    columna: str


class Schema:
    def __init__(self, columnas: Dict[str, Set[str]], relaciones: List[Relacion]) -> None:
        self.columnas = columnas
        self.relaciones = relaciones

    def entre(self, a: str, b: str) -> List[Relacion]:
        """Relaciones que conectan dos tablas, en cualquiera de los dos sentidos.

        El sentido no importa para la ambigüedad: PostgREST cuenta los caminos, y tanto la FK
        de ida como la de vuelta son caminos entre las mismas dos tablas.
        """
        return [r for r in self.relaciones
                if (r.origen == a and r.destino == b) or (r.origen == b and r.destino == a)]

    def validar_select(self, tabla: str, spec: str) -> None:
        """Recorre el spec y levanta SelectInvalidoError en el primer nombre o embed que no cierre."""
        if tabla not in self.columnas:
            raise SelectInvalidoError(f"La tabla '{tabla}' no existe en schema.sql")
        for item in _partir(spec):
            if item.endswith(")"):
                self._validar_embed(tabla, item)
            else:
                self._validar_columna(tabla, item)

    def _validar_columna(self, tabla: str, item: str) -> None:
        col = _nombre_real(item)
        if col in ("*", ""):
            return
        if col not in self.columnas[tabla]:
            raise SelectInvalidoError(
                f"La columna '{col}' no existe en '{tabla}'. PostgREST responde 400 42703 y el "
                f"generador entero muere. Columnas reales: {sorted(self.columnas[tabla])}"
            )

    def _validar_embed(self, tabla: str, item: str) -> None:
        cabeza, _, cuerpo = item.partition("(")
        cuerpo = cuerpo[:-1]
        partes = cabeza.split("!")
        nombre = _nombre_real(partes[0])
        hints = [p for p in partes[1:] if p not in ("inner", "left")]
        hint: Optional[str] = hints[0] if hints else None

        destino = self._destino(tabla, nombre, hint)
        rels = self.entre(tabla, destino)
        if hint is None and len(rels) > 1:
            nombres = ", ".join(sorted(r.constraint for r in rels))
            raise SelectInvalidoError(
                f"El embed '{nombre}' desde '{tabla}' es AMBIGUO: hay {len(rels)} relaciones "
                f"entre '{tabla}' y '{destino}' ({nombres}). PostgREST responde 300 PGRST201 en "
                f"vez de datos. Nombrá la FK: '{nombre}!<constraint>(...)'."
            )
        if hint is not None and hint not in {r.constraint for r in rels} | self.columnas[tabla]:
            raise SelectInvalidoError(
                f"El embed '{nombre}' desde '{tabla}' nombra '{hint}', que no es ni una "
                f"constraint entre esas tablas ni una columna de '{tabla}'."
            )
        self.validar_select(destino, cuerpo)

    def _destino(self, tabla: str, nombre: str, hint: Optional[str]) -> str:
        """Tabla apuntada por un embed. `nombre` suele ser la tabla; en la forma
        `alias:columna_fk(...)` hay que seguir la FK de esa columna."""
        if nombre in self.columnas:
            return nombre
        por_columna = [r for r in self.relaciones if r.origen == tabla and r.columna == nombre]
        if por_columna:
            return por_columna[0].destino
        raise SelectInvalidoError(
            f"El embed '{nombre}' desde '{tabla}' no es ni una tabla de schema.sql ni una "
            f"columna con FK de '{tabla}'."
        )


def _partir(spec: str) -> List[str]:
    """Parte un spec por comas de PRIMER nivel: las de adentro de un embed son suyas."""
    items, nivel, actual = [], 0, ""
    for ch in spec:
        if ch == "(":
            nivel += 1
        elif ch == ")":
            nivel -= 1
        if ch == "," and nivel == 0:
            items.append(actual.strip())
            actual = ""
        else:
            actual += ch
    if actual.strip():
        items.append(actual.strip())
    return [i for i in items if i]


def _nombre_real(token: str) -> str:
    """Saca el alias de `alias:nombre` y el cast de `nombre::tipo`."""
    token = token.strip()
    if ":" in token:
        token = token.split(":", 1)[1]
    return token.split("::", 1)[0].strip()


def cargar_schema(path: Path = _SCHEMA) -> Schema:
    """Parsea db/schema.sql. Las FKs viven en ALTER TABLE separados, no inline en el CREATE."""
    sql = path.read_text(encoding="utf-8")
    columnas: Dict[str, Set[str]] = {}
    for tabla, cuerpo in _RE_TABLA.findall(sql):
        cols: Set[str] = set()
        for linea in cuerpo.splitlines():
            linea = linea.strip().rstrip(",")
            if not linea or linea.upper().startswith(_NO_ES_COLUMNA):
                continue
            cols.add(linea.split()[0].strip('"'))
        columnas[tabla] = cols
    relaciones = [
        Relacion(origen=o, destino=d, constraint=c, columna=cols.split(",")[0].strip())
        for o, c, cols, d in _RE_FK.findall(sql)
    ]
    return Schema(columnas, relaciones)

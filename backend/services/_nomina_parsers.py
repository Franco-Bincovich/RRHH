"""
Parsers de VALORES de un CSV de nómina: texto → tipo. Sin IO, sin estado, sin conocimiento de
qué columnas existe ni de qué archivo vienen.

Extraído de `_nomina_empleados_transforms.py`, que llegó a 164 contra un límite de 150 al sumar
el legajo y los headers opcionales. El corte separa dos cosas que se mezclaban:

  · ACÁ            → cómo se interpreta UN VALOR ("6/2/2026" → date, "SI" → True, "NO APLICA" → None)
  · en transforms  → qué COLUMNAS tiene el CSV de nómina de empleados y cuáles son obligatorias

🔴 Y no es un corte estético: **esta mitad es la reusable.** El import histórico de vacaciones e
inasistencias viene en el mismo formato (`;`, latin1, CRLF, fechas `d/m/yyyy` sin padding) con
columnas COMPLETAMENTE distintas. Va a necesitar estos parsers y nada del vocabulario de nómina.
Dejarlos en el archivo de los headers obligaría a importar el módulo de empleados desde el de
vacaciones, o —peor— a duplicar `parse_fecha`, que es exactamente la clase de divergencia
silenciosa que este repo ya pagó con el decodificador de encoding.

Se movió VERBATIM: `%d/%m/%Y` (que ya acepta entrada sin padding), el set de vacíos y los
mensajes de error son idénticos.
"""
from datetime import date, datetime
from typing import Optional

# Textos que en el CSV significan "no hay dato". Se comparan en MAYÚSCULAS.
_VACIOS = {"", "NO APLICA", "N/A", "NA", "-", "--"}


def _norm(s: Optional[str]) -> str:
    """Normaliza para comparar: trim + colapsa espacios internos + casefold."""
    return " ".join((s or "").split()).casefold()


def normalizar_nombre(s: str) -> str:
    """Clave de match/dedup para empresas y áreas (trim + espacios + case-insensitive)."""
    return _norm(s)


def limpiar(v: Optional[str]) -> Optional[str]:
    """Texto libre: trim; '' o 'NO APLICA' (y variantes) -> None."""
    t = (v or "").strip()
    return None if t.upper() in _VACIOS else t


def parse_fecha(v: Optional[str]) -> Optional[date]:
    """DD/MM/YYYY -> date. Vacío -> None. Formato inválido -> ValueError con mensaje claro.

    `strptime` acepta la entrada SIN padding, así que "6/2/2026" (6 de febrero) parsea igual que
    "06/02/2026" — verificado. No hace falta una rama aparte para los archivos que no padean.
    """
    t = (v or "").strip()
    if not t:
        return None
    try:
        return datetime.strptime(t, "%d/%m/%Y").date()
    except ValueError:
        raise ValueError(f"Fecha inválida '{t}' (se espera DD/MM/YYYY)")


def parse_bool(v: Optional[str]) -> Optional[bool]:
    """'SI'->True, 'NO'->False, vacío/otro -> None."""
    t = (v or "").strip().upper()
    if t == "SI":
        return True
    if t == "NO":
        return False
    return None


def parse_sexo(v: Optional[str]) -> Optional[str]:
    """'M'->'Masculino', 'F'->'Femenino'. Otro -> texto limpio o None (sexo es texto libre)."""
    t = (v or "").strip().upper()
    if t == "M":
        return "Masculino"
    if t == "F":
        return "Femenino"
    return limpiar(v)


def email_valido(email: Optional[str]) -> bool:
    """Email presente y con formato mínimo (para decidir si va como faltante)."""
    e = email or ""
    return "@" in e and "." in e.split("@")[-1]

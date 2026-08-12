"""
Barrido estructural: los `requirements*.txt` tienen que ser ASCII puro.

🔴 QUÉ CLASE DE BUG CIERRA
`pip install -r requirements.txt` falla en Windows con
`UnicodeDecodeError: 'charmap' codec can't decode byte 0x8f in position 841`.
No es pip roto ni el archivo corrupto: `pip._internal.utils.encoding.auto_decode`
decodifica el archivo con `locale.getpreferredencoding(False)` salvo que encuentre
un BOM o una cookie PEP-263 en las DOS primeras líneas. En Windows ese locale es
**cp1252**, y cp1252 no mapea cinco bytes: 0x81, 0x8D, 0x8F, 0x90, 0x9D.
El 0x8F venía del emoji `⚠️` en un COMENTARIO: `U+FE0F` (VARIATION SELECTOR-16)
se codifica `EF B8 8F` en UTF-8. Un comentario carteleaba el install entero.

🚨 LA TRAMPA, Y POR QUÉ LA REGLA ES ASCII Y NO "CASI ASCII"
Los acentos (`á` = `C3 A1`) y `🔴` (`F0 9F 94 B4`) **no rompen**: cp1252 los mapea a
mojibake y pip sigue de largo. Solo revientan esos cinco bytes. O sea que la regla
real —"UTF-8 menos cinco bytes"— es invisible al ojo: `⚠` (U+26A0, `E2 9A A0`) es
inofensivo y `⚠️` (U+26A0 U+FE0F) es fatal, y **en el editor se ven IGUAL**. Una
regla que nadie puede verificar mirando no es una regla. ASCII sí se verifica.

Por eso el fix tampoco fue un BOM ni una cookie `# -*- coding: utf-8 -*-`: las dos
funcionan, pero dejan el archivo dependiendo de una heurística de pip (la cookie
solo se lee en las dos primeras líneas: un comentario nuevo arriba la desactiva
EN SILENCIO) y no cubren a ninguna otra herramienta que lea el archivo con el
locale. ASCII puro no depende de pip, ni de su versión, ni del locale.

🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTE TEST PUEDA FALLAR?
No hay fake: lee los archivos REALES del repo. Falla apenas alguien pegue un emoji
o un acento en cualquier `requirements*.txt`. El riesgo no es que no falle, es que
pase **en el vacío** — que el glob no encuentre nada, o que el detector esté roto.
Contra lo primero está la guarda de mínimo; contra lo segundo, `test_el_detector_detecta`,
que ancla el detector contra los bytes históricos EXACTOS antes de creerle un verde.
"""
from pathlib import Path

import pytest

_RAIZ = Path(__file__).resolve().parents[2]

# Los cinco bytes sin mapeo en cp1252. Son los que convierten un comentario en
# un install roto; el resto del rango alto solo produce mojibake.
_SIN_MAPEO_CP1252 = {0x81, 0x8D, 0x8F, 0x90, 0x9D}

# Guarda de mínimo: hoy son requirements.txt y requirements-dev.txt. Si el glob
# deja de encontrarlos, este test pasaría sin haber mirado un solo archivo.
_MINIMO_ARCHIVOS = 2


def _requirements() -> list[Path]:
    """Descubre los requirements del repo por glob, nunca por lista escrita a mano."""
    ignorar = {"venv", ".venv", "node_modules", "site-packages", "__pycache__"}
    return sorted(
        p for p in _RAIZ.rglob("requirements*.txt")
        if not ignorar & set(p.parts)
    )


def test_hay_requirements_para_barrer():
    """Guarda de mínimo: sin esto, un glob roto daría verde sobre cero archivos."""
    encontrados = _requirements()
    assert len(encontrados) >= _MINIMO_ARCHIVOS, (
        f"El glob encontró {len(encontrados)} requirements ({[str(p) for p in encontrados]}), "
        f"esperaba >= {_MINIMO_ARCHIVOS}. Si se movieron, actualizar el barrido; "
        "si desaparecieron, este test estaba pasando sin comparar nada."
    )


@pytest.mark.parametrize("archivo", _requirements(), ids=lambda p: p.name)
def test_requirements_es_ascii_puro(archivo: Path):
    """Un solo byte no-ASCII, aunque sea en un comentario, puede romper el install."""
    data = archivo.read_bytes()
    if data.isascii():
        return

    # Reportar el PRIMER byte culpable con línea y columna: el error nativo de pip
    # solo da un offset absoluto, que no le sirve a nadie para encontrarlo.
    i = next(i for i, b in enumerate(data) if b > 127)
    linea = data[:i].count(b"\n") + 1
    inicio = data.rfind(b"\n", 0, i) + 1
    fin = data.find(b"\n", i)
    texto = data[inicio:fin if fin != -1 else len(data)].decode("utf-8", "replace")
    fatal = data[i] in _SIN_MAPEO_CP1252
    pytest.fail(
        f"{archivo.relative_to(_RAIZ)} tiene bytes no-ASCII. "
        f"Primero: 0x{data[i]:02x} en el offset {i} (línea {linea}, columna {i - inicio + 1}).\n"
        f"  {'ROMPE' if fatal else 'No rompe'} `pip install` en Windows: "
        f"0x{data[i]:02x} {'no tiene' if fatal else 'sí tiene'} mapeo en cp1252.\n"
        f"  Línea {linea}: {texto!r}\n"
        "  Igual hay que sacarlo: la regla es ASCII, no 'casi ASCII' — ver el docstring."
    )


@pytest.mark.parametrize("archivo", _requirements(), ids=lambda p: p.name)
def test_requirements_no_usa_bom_ni_cookie(archivo: Path):
    """
    El fix es ASCII, NO un BOM ni una cookie PEP-263.

    Las dos hacen andar el install y las dos son peores: dependen de que pip mire
    el BOM / las dos primeras líneas. Si mañana aparece una, es señal de que alguien
    volvió a meter no-ASCII y lo tapó en vez de sacarlo.
    """
    data = archivo.read_bytes()
    assert not data.startswith(b"\xef\xbb\xbf"), (
        f"{archivo.relative_to(_RAIZ)} arranca con BOM UTF-8. Es un parche sobre "
        "no-ASCII que no debería estar ahí: sacar el carácter, no agregar el BOM."
    )
    dos_primeras = b"\n".join(data.split(b"\n")[:2])
    assert b"coding:" not in dos_primeras and b"coding=" not in dos_primeras, (
        f"{archivo.relative_to(_RAIZ)} declara una cookie de encoding. Misma razón "
        "que el BOM, y encima frágil: un comentario nuevo arriba la desactiva en silencio."
    )


def test_el_detector_detecta():
    """
    Ancla el detector contra los bytes históricos EXACTOS antes de creerle un verde.

    Sin esto, un `isascii()` mal escrito (o un glob que devuelve rutas inexistentes)
    daría verde para siempre y el barrido no probaría nada. Es el caso #5 de
    "Un test solo prueba lo que el fake puede desmentir": la aserción vacua.
    """
    # Los bytes REALES que rompían, escritos como literal y no como texto encodeado:
    # "# ⚠️ Los PDF cifrados..." (requirements.txt L21). Escribirlos crudos ancla el test
    # a la secuencia exacta, sin depender del encoding con el que se lea ESTE archivo.
    roto = b"# \xe2\x9a\xa0\xef\xb8\x8f Los PDF cifrados con AES"
    assert roto.decode("utf-8") == "# ⚠️ Los PDF cifrados con AES"
    assert not roto.isascii(), "el detector no ve un archivo con emoji"
    assert 0x8F in roto, "U+FE0F tiene que aportar el byte 0x8F"
    assert _SIN_MAPEO_CP1252 & set(roto), "0x8F tiene que estar en la lista de fatales"
    with pytest.raises(UnicodeDecodeError) as err:
        roto.decode("cp1252")  # exactamente el error que veía el dev en la Lenovo
    assert "0x8f" in str(err.value), "el byte que reporta cp1252 tiene que ser el 0x8f"

    # Y el contraejemplo que hace visible la trampa: el MISMO signo SIN el selector
    # de variación decodifica sin error en cp1252 (mojibake, pero pip sigue de largo).
    casi = b"# \xe2\x9a\xa0 Los PDF cifrados con AES"
    assert not casi.isascii(), "sigue sin ser ASCII"
    assert not _SIN_MAPEO_CP1252 & set(casi), "sin U+FE0F no hay byte fatal"
    casi.decode("cp1252")  # no levanta: por eso la regla es ASCII y no 'casi ASCII'

    # Un archivo ASCII pasa.
    assert b"pytest==9.1.1\n# comentario sin acentos\n".isascii()

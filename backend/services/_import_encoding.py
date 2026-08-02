"""
DETECCIÓN DE ENCODING de un archivo subido. Fuente ÚNICA.

Antes había DOS detectores con políticas distintas, y uno de ellos duplicado a su vez en dos
routers. Este módulo los reemplaza. El armado del CSV (delimitador, cabeceras) vive en
`_import_csv`, que lo usa: separar el encoding del parseo es lo que permite que cada flujo
elija su política sin duplicar la detección.

## 🔴 EL ORDEN DE DETECCIÓN, Y POR QUÉ CADA PASO ESTÁ DONDE ESTÁ

    1. BOM UTF-16 (FF FE / FE FF)     → utf-16
    2. UTF-16 sin BOM (heurística)    → utf-16-le / utf-16-be
    3. utf-8-sig                      → cubre UTF-8 CON y SIN BOM
    4. latin-1                        → solo si el caller lo permite; si no, ValueError

**El paso 3 usa `utf-8-sig` y no `utf-8`, y eso es el blindaje del BOM.** El codec `utf-8-sig`
consume el BOM si está y se comporta como `utf-8` si no está, así que un solo paso cubre los dos
casos. Con `utf-8` pelado, un CSV exportado desde Excel deja el `\\ufeff` PEGADO AL PRIMER HEADER
— y ese es el peor modo de falla posible: `str.strip()` NO lo saca (no es whitespace en Python),
así que la columna existe, se ve idéntica en pantalla, y el error dice "falta la columna
Apellido" mientras Apellido está ahí. Media hora mirando un archivo correcto.

🔴 **LOS PASOS 1 Y 2 VAN ANTES QUE TODO, y ahí está el bug que esto arregla.** Los dos routers de
nómina hacían `except UnicodeDecodeError: latin-1`, y **latin-1 nunca falla**: decodifica
cualquier byte. Un archivo UTF-16 entraba como `'ÿþA\\x00p\\x00e\\x00l...'` y el import "andaba",
cargando nombres ilegibles en la base. Verificado en vivo antes de escribir esto. Con la
detección de UTF-16 delante, latin-1 solo se alcanza cuando el archivo genuinamente lo es.

## `permitir_latin1`: es una POLÍTICA, no un descuido — y difiere por los ARCHIVOS

  · **True (nómina y los imports que vengan):** los archivos reales de RRHH son latin-1 (`;`,
    CRLF, acentos). Sin este fallback el import de nómina dejaría de funcionar con el formato
    que RRHH manda todos los meses. Verificado: un latin-1 con acentos NO es UTF-8 válido.
  · **False (evaluaciones):** sus dos archivos vienen en UTF-8 y UTF-16, y su flujo prefiere
    fallar con un mensaje claro antes que adivinar. Es el comportamiento que ya tenía y no se
    cambia — hay un test que lo fija (`test_evaluacion_import.py`).

⚠️ Unificar SIN el flag habría roto uno de los dos: con latin-1 obligatorio, evaluaciones perdía
su estrictez; sin latin-1, nómina dejaba de leer los archivos de producción. La duplicación real
era la DETECCIÓN, no la política.
"""
from typing import Optional

_BOM_UTF16 = (b"\xff\xfe", b"\xfe\xff")


def decodificar(data: bytes, permitir_latin1: bool = True) -> str:
    """Bytes → texto. Ver el orden de detección y el porqué de `permitir_latin1` en el módulo.

    Raises:
        ValueError: si no se pudo determinar el encoding y `permitir_latin1` es False.
    """
    if data[:2] in _BOM_UTF16:
        return data.decode("utf-16")        # el codec lee el BOM, elige endianness y lo quita
    utf16 = _detectar_utf16_sin_bom(data)
    if utf16:
        try:
            return data.decode(utf16)
        except UnicodeDecodeError:
            pass                            # la heurística falló → seguí
    try:
        return data.decode("utf-8-sig")     # cubre UTF-8 con BOM y sin BOM
    except UnicodeDecodeError as exc:
        if permitir_latin1:
            return data.decode("latin-1")   # los archivos de RRHH; ver la política en el módulo
        raise ValueError(
            "Encoding no reconocido: sin BOM y no es UTF-8 válido. "
            "Guardá el archivo como UTF-8 o UTF-16."
        ) from exc


def _detectar_utf16_sin_bom(data: bytes) -> Optional[str]:
    """Heurística para UTF-16 SIN BOM sobre texto casi-ASCII: la mitad de los bytes son 0x00.
    LE → los 0x00 caen en posiciones IMPARES (byte alto del par); BE → en PARES. Umbral holgado
    (>30%) porque el contenido es ASCII casi puro. None si no parece UTF-16."""
    muestra = data[:2000]
    if len(muestra) < 2:
        return None
    pares, impares = muestra[0::2], muestra[1::2]
    ceros_pares = pares.count(0) / len(pares)
    ceros_impares = impares.count(0) / len(impares)
    if ceros_impares > 0.30 and ceros_impares > ceros_pares:
        return "utf-16-le"
    if ceros_pares > 0.30 and ceros_pares > ceros_impares:
        return "utf-16-be"
    return None

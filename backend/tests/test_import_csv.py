"""
El lector de CSV compartido: encoding, delimitador y cabeceras — sin red.

Antes había DOS detectores de encoding con políticas distintas, y uno duplicado a su vez en dos
routers. Lo que estos tests fijan:

  1. 🔴 BOM: un CSV exportado desde Excel se lee con el PRIMER HEADER LIMPIO. Es el peor modo de
     falla posible si se rompe — `str.strip()` NO saca el `\\ufeff` (no es whitespace en Python),
     así que la columna existe, se ve idéntica en pantalla, y el error dice que falta.
  2. 🔴 UTF-16: se detecta ANTES de latin-1. Ese es el bug que esto arregla: `latin-1` NUNCA
     falla —decodifica cualquier byte— así que un UTF-16 entraba como basura y el import "andaba".
  3. latin-1 y utf-8 sin BOM: sin regresión. Son los archivos reales de RRHH.
  4. `permitir_latin1` es una política por flujo, no un descuido.
  5. Cabeceras faltantes: el mensaje nombra la columna, con su grafía original.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
  · Los bytes se construyen con `.encode(...)` REAL, no con literales escritos a mano: un
    literal mal copiado probaría el literal, no el encoding.
  · El caso del BOM afirma sobre el PRIMER header, que es el único que el BOM toca. Afirmar
    sobre el segundo pasaría con el bug puesto.
  · El caso de UTF-16 usa un texto que en latin-1 decodifica SIN error (por eso el bug era
    silencioso): si latin-1 fallara con esos bytes, el orden de detección no importaría y el
    test no probaría nada.
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

from services._import_csv import abrir, faltantes, filas, normalizar_header
from services._import_encoding import decodificar

_CSV = "Apellido;Nombre;Fecha\r\nPérez;Ana;6/2/2026\r\n"
BOM_UTF8 = b"\xef\xbb\xbf"


def _primer_header(texto: str) -> str:
    return texto.splitlines()[0].split(";")[0]


# ── 1. 🔴 EL BOM ──────────────────────────────────────────────────────────────

class TestElBOM:
    def test_un_csv_de_excel_con_BOM_deja_el_primer_header_limpio(self) -> None:
        """🔴 EL CASO CENTRAL. Con `utf-8` pelado en vez de `utf-8-sig`, el header quedaría
        `'\\ufeffApellido'`: idéntico en pantalla, y el import diría "falta la columna Apellido"
        con Apellido presente. Media hora mirando un archivo correcto.

        Para que falle: cambiar `utf-8-sig` por `utf-8` en el paso 3 de `decodificar`."""
        texto = decodificar(BOM_UTF8 + _CSV.encode("utf-8"))
        assert _primer_header(texto) == "Apellido"
        assert "﻿" not in texto, "el BOM sobrevivió en algún lado del texto"

    def test_el_BOM_no_sobrevive_a_strip_asi_que_no_alcanza_con_trimear(self) -> None:
        """La razón por la que esto NO se puede arreglar "limpiando el header" aguas abajo:
        `strip()` no toca el `\\ufeff` porque no es whitespace. El arreglo tiene que estar en
        el decode."""
        assert "﻿Apellido".strip() == "﻿Apellido"

    def test_el_header_con_BOM_matchea_las_columnas_requeridas(self) -> None:
        """El efecto observable: con el BOM pegado, `faltantes` reportaría Apellido como
        ausente. Es el mensaje que confundiría a quien sube el archivo."""
        reader = abrir(BOM_UTF8 + _CSV.encode("utf-8"))
        assert faltantes(reader.fieldnames, ["Apellido", "Nombre"]) == []

    def test_sin_BOM_funciona_igual(self) -> None:
        """`utf-8-sig` se comporta como `utf-8` cuando no hay BOM: un solo paso cubre los dos."""
        assert _primer_header(decodificar(_CSV.encode("utf-8"))) == "Apellido"


# ── 2. 🔴 UTF-16 antes que latin-1 ────────────────────────────────────────────

class TestUTF16NoSeConfundeConLatin1:
    def test_utf16_con_BOM_se_lee_bien(self) -> None:
        """🔴 EL BUG QUE ESTO ARREGLA. Los dos routers hacían `except: latin-1`, y latin-1 NUNCA
        falla: este archivo entraba como `'ÿþA\\x00p\\x00e\\x00l...'` y el import lo cargaba.

        Para que falle: mover el fallback a latin-1 ANTES de la detección de UTF-16."""
        texto = decodificar(_CSV.encode("utf-16"))
        assert _primer_header(texto) == "Apellido"

    def test_los_bytes_utf16_SI_decodifican_como_latin1_por_eso_era_silencioso(self) -> None:
        """El control del control: si latin-1 fallara con estos bytes, el orden no importaría y
        el test de arriba no probaría nada. Falla justamente porque NO falla."""
        basura = _CSV.encode("utf-16").decode("latin-1")
        assert basura.startswith("ÿþ") and "\x00" in basura

    @pytest.mark.parametrize("enc", ["utf-16-le", "utf-16-be"], ids=["le", "be"])
    def test_utf16_SIN_bom_tambien_se_detecta(self, enc: str) -> None:
        """El caso que se escapó en evaluaciones: las notas finales venían en UTF-16LE sin BOM."""
        assert _primer_header(decodificar(_CSV.encode(enc))) == "Apellido"


# ── 3 y 4. latin-1: sin regresión, y la política por flujo ────────────────────

class TestLatin1:
    def test_latin1_con_acentos_se_lee(self) -> None:
        """El formato REAL de los archivos de RRHH (`;`, CRLF, acentos). Si esto fallara, el
        import de nómina dejaría de funcionar con lo que mandan todos los meses."""
        texto = decodificar(_CSV.encode("latin-1"))
        assert "Pérez" in texto

    def test_con_permitir_latin1_False_falla_con_mensaje_claro(self) -> None:
        """La política de evaluaciones, que NO cambia con la unificación: prefiere fallar antes
        que adivinar. Hay un test propio en test_evaluacion_import.py que también lo fija."""
        with pytest.raises(ValueError) as exc:
            decodificar(_CSV.encode("latin-1"), permitir_latin1=False)
        assert "Encoding no reconocido" in str(exc.value)

    def test_pero_utf16_se_lee_en_las_DOS_politicas(self) -> None:
        """El flag decide qué pasa cuando NO se pudo determinar, no si se detecta UTF-16."""
        for permitir in (True, False):
            assert _primer_header(decodificar(_CSV.encode("utf-16"), permitir)) == "Apellido"


# ── 5. Cabeceras ──────────────────────────────────────────────────────────────

class TestCabeceras:
    def test_una_columna_faltante_se_nombra_con_su_grafia_original(self) -> None:
        """El mensaje lo lee alguien de RRHH con el archivo abierto: tiene que poder buscarla
        tal cual está escrita en el pedido, no normalizada."""
        reader = abrir(_CSV.encode("latin-1"))
        assert faltantes(reader.fieldnames, ["Apellido", "Fecha Ingreso"]) == ["Fecha Ingreso"]

    def test_la_comparacion_ignora_mayusculas_y_espacios_de_mas(self) -> None:
        """La normalización unificada es la más tolerante de las dos que había: solo puede
        aceptar cabeceras que antes se rechazaban, nunca al revés."""
        assert normalizar_header("  NOTA   FINAL ") == normalizar_header("Nota Final")
        assert faltantes(["  NOTA   FINAL "], ["Nota Final"]) == []

    def test_un_archivo_vacio_reporta_todas_como_faltantes(self) -> None:
        assert faltantes(None, ["Apellido"]) == ["Apellido"]
        assert faltantes([], ["Apellido"]) == ["Apellido"]

    def test_el_delimitador_es_punto_y_coma(self) -> None:
        """Con `,` el archivo entero entraría como UNA columna llamada 'Apellido;Nombre;Fecha'."""
        reader = abrir(_CSV.encode("latin-1"))
        assert reader.fieldnames == ["Apellido", "Nombre", "Fecha"]


# ── El número de fila del reporte ─────────────────────────────────────────────

def test_las_filas_arrancan_en_2_porque_la_1_es_el_encabezado() -> None:
    """Es el número que ve quien abre el CSV en Excel: por eso el reporte es accionable."""
    numeros = [n for n, _ in filas(abrir(_CSV.encode("latin-1")))]
    assert numeros == [2]


def test_upper_normaliza_las_claves_para_evaluaciones() -> None:
    """Evaluaciones declara su vocabulario en mayúsculas; nómina resuelve por nombre normalizado
    y no lo usa. El flag existe para no imponerle a uno la forma del otro."""
    _, fila = next(filas(abrir(_CSV.encode("latin-1")), upper=True))
    assert fila["APELLIDO"] == "Pérez"

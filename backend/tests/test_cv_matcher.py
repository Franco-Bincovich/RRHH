"""
`_gmail_matcher.codigos_en`: del asunto escrito por un candidato al código de la vacante.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS FALLEN?

Que el reconocimiento fuera **estricto**. Casi todos los casos de acá son formas que un parser
`== "VAC-0001"` rechazaría: minúsculas, espacio en vez de guion, corchetes, texto alrededor. Cada
uno de esos rechazos NO da error — manda a revisión manual un CV que traía el código
perfectamente legible, que es justo lo que el código venía a evitar.

Los casos salieron de cómo escribe alguien que copia de un aviso de LinkedIn desde el teléfono,
no de imaginar bordes.
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

import pytest  # noqa: E402

from services._gmail_matcher import codigos_en  # noqa: E402


@pytest.mark.parametrize("asunto", [
    "[VAC-0001]",
    "vac-0001",                                  # todo en minúscula
    "Vac-0001",
    "VAC 0001",                                  # espacio en vez de guion
    "VAC0001",                                   # sin separador
    "vac_0001",
    "Postulación [VAC-0001] - Analista de Datos",  # con texto alrededor
    "RE: [vac-0001] mi cv",
    "CV para la búsqueda VAC-0001, gracias",
    "[VAC-00001]",                               # padding de más
], ids=lambda v: v)
def test_encuentra_el_codigo_escrito_de_cualquier_forma(asunto) -> None:
    """Todas estas formas son el MISMO código y tienen que resolver igual.

    ¿Qué tendría que ser distinto para que falle? Que el matcher exigiera el formato canónico:
    ahí 9 de estos 11 asuntos irían a revisión manual trayendo el código a la vista.
    """
    assert codigos_en(asunto) == ["VAC-0001"]


@pytest.mark.parametrize("asunto", [
    "",
    "Consulta sobre la búsqueda",
    "CV adjunto",
    "VAC-",                       # sin dígitos
    "VAC-1",                      # 🔴 menos de 4 dígitos NO es un código: ver abajo
    "VAC-12",
    "EVAC-0001",                  # `\\b` inicial: no engancha el sufijo de otra palabra
], ids=lambda v: v or "(vacío)")
def test_no_inventa_codigos(asunto) -> None:
    assert codigos_en(asunto) == []


def test_menos_de_cuatro_digitos_no_se_completa_solo() -> None:
    r"""🔴 LA LÍNEA DONDE LA PERMISIVIDAD SE CORTA, y es una decisión de seguridad.

    Completar `VAC-12` a `VAC-0012` haría que un código tipeado a medias resuelva **a otra
    vacante real**, que puede existir y no ser la del candidato. Un CV en la búsqueda equivocada
    no da error y no se detecta nunca; uno en revisión manual se resuelve en dos segundos.

    ¿Qué tendría que ser distinto para que falle? Que el regex aceptara `\d+` en vez de
    `\d{4,}` — el cambio de una línea que convierte un matcher permisivo en uno que adivina.
    """
    assert codigos_en("VAC-12") == []
    assert codigos_en("VAC-1") == []


def test_un_numero_de_cinco_digitos_sobrevive() -> None:
    """El contador puede pasar de 9999 (el CHECK de la 097 admite `[0-9]{4,}`). Un `VAC-10000`
    normalizado a 4 dígitos sería otro código y el CV iría a la búsqueda equivocada."""
    assert codigos_en("[VAC-10000]") == ["VAC-10000"]


class TestDosCodigos:

    def test_dos_distintos_no_resuelven(self) -> None:
        """🔴 Sin match, a revisión. Elegir el primero es una decisión invisible sobre la carrera
        de alguien: el CV entra a una búsqueda que quizás no es la suya y nadie se entera."""
        assert codigos_en("RE: [VAC-0001] y [VAC-0002]") == ["VAC-0001", "VAC-0002"]

    def test_el_mismo_repetido_NO_es_ambiguo(self) -> None:
        """`[VAC-0001] re: vac 0001` es un código solo. Tratarlo como ambiguo mandaría a revisión
        un mail perfectamente claro — el caso típico de una cadena de respuestas."""
        assert codigos_en("[VAC-0001] re: vac 0001") == ["VAC-0001"]
        assert codigos_en("VAC-1 / VAC-0001") == ["VAC-0001"], "el padding no crea un segundo código"

    def test_tres_distintos_tampoco(self) -> None:
        assert len(codigos_en("VAC-0001 VAC-0002 VAC-0003")) == 3


def test_none_no_revienta() -> None:
    """Un mail sin asunto no puede tumbar la corrida."""
    assert codigos_en(None) == []

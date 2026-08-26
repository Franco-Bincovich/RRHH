"""
`_gmail_matcher.codigos_en`: del asunto escrito por un candidato al código de la vacante.

## 🔴 CAMBIÓ LA PREMISA EL 26/8/2026 — Y ES LO QUE HAY QUE LEER ANTES DE TOCAR ESTE ARCHIVO

Hasta hoy el código lo emitía la base con formato fijo (`VAC` + 4 dígitos, mig 097) y el matcher
lo reconocía con UN regex, sin saber qué vacantes existen. Ahora lo escribe Capital Humano y
puede ser cualquier cosa (mig 122), así que `codigos_en` recibe LOS CÓDIGOS QUE EXISTEN y busca
esos. Todos los casos de acá pasan por `CONOCIDOS`.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS FALLEN?

1. **Que el reconocimiento fuera estricto.** Casi todos los casos del primer bloque son formas
   que un `== "VAC-0001"` rechazaría: minúsculas, espacio en vez de guion, corchetes, texto
   alrededor. Cada uno de esos rechazos NO da error — manda a revisión manual un CV que traía el
   código perfectamente legible, que es justo lo que el código venía a evitar.
2. **Que `CONOCIDOS` tuviera un solo código.** Con uno solo, ni el borde alfanumérico ni la regla
   de contención se pueden desmentir: hacen falta `ECO` y `ECO-2026` a la vez, que es el par que
   los rompe. Por eso la lista incluye un código corto que es prefijo de otro.
3. **Que faltara el contraste de `ECONOMIA`.** Sin él, un matcher que buscara el código como
   substring pelado —sin bordes— pasaría todo el primer bloque.

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

# Los códigos que EXISTEN. `ECO` y `ECO-2026` conviven a propósito: es el par que rompe un
# matcher sin regla de contención. `VAC-0001` sobrevive porque es el que tienen las 5 vacantes
# reales de producción — los códigos viejos siguen siendo códigos válidos.
CONOCIDOS = ["VAC-0001", "VAC-0002", "VAC-0003", "VAC-10000", "ECO", "ECO-2026"]


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
    "VAC-0001-analista",                         # el código pegado al puesto
], ids=lambda v: v)
def test_encuentra_el_codigo_escrito_de_cualquier_forma(asunto) -> None:
    """Todas estas formas son el MISMO código y tienen que resolver igual.

    ¿Qué tendría que ser distinto para que falle? Que el matcher exigiera la forma exacta
    guardada: ahí 8 de estos 10 asuntos irían a revisión manual trayendo el código a la vista.
    """
    assert codigos_en(asunto, CONOCIDOS) == ["VAC-0001"]


@pytest.mark.parametrize("asunto", [
    "",
    "Consulta sobre la búsqueda",
    "CV adjunto",
    "VAC-",                       # sin dígitos
    "VAC-1",                      # 🔴 un código que NO existe no se completa: ver abajo
    "VAC-12",
    "VAC-0009",
    "EVAC-0001",                  # el borde inicial: no engancha el sufijo de otra palabra
    "ECONOMIA aplicada",          # 🔴 el borde final, con `ECO` en CONOCIDOS
    "[VAC-00001]",                # padding de más: ver `test_el_padding_ya_no_se_normaliza`
], ids=lambda v: v or "(vacío)")
def test_no_inventa_codigos(asunto) -> None:
    assert codigos_en(asunto, CONOCIDOS) == []


def test_un_codigo_que_no_existe_no_resuelve_a_otro() -> None:
    """🔴 LA LÍNEA DONDE LA PERMISIVIDAD SE CORTA, y sigue siendo una decisión de seguridad.

    Antes la escribía el regex (mínimo 4 dígitos, para que `VAC-12` no se completara a
    `VAC-0012`). Ahora la escribe el conjunto: el matcher solo reconoce códigos que EXISTEN, así
    que un código tipeado a medias no puede resolver a otra vacante real — no matchea nada y el
    mail va a revisión, donde un humano lo resuelve en dos segundos.

    ¿Qué tendría que ser distinto para que falle? Que `codigos_en` volviera a reconocer una FORMA
    en vez de un conjunto: ahí `VAC-0009` "existiría" y el mail se reportaría como
    `vacante_desconocida` en vez de `sin_codigo`.
    """
    assert codigos_en("VAC-12", CONOCIDOS) == []
    assert codigos_en("VAC-0009", CONOCIDOS) == [], "VAC-0009 no está en CONOCIDOS"


def test_el_padding_ya_no_se_normaliza_y_esta_declarado() -> None:
    """⚠️ REGRESIÓN ACEPTADA, no un olvido. Con el formato fijo `VAC-NNNN` los ceros de la
    izquierda eran cosméticos y `[VAC-00001]` se normalizaba a `VAC-0001`. Con códigos libres eso
    no se puede sostener: `X-007` y `X-7` pueden ser dos búsquedas distintas, y decidir que los
    ceros no cuentan sería inventar una regla sobre códigos que eligió otra persona. El precio es
    que ese asunto va a revisión manual; el precio de la alternativa era mandar un CV a la
    búsqueda equivocada."""
    assert codigos_en("[VAC-00001]", CONOCIDOS) == []
    assert codigos_en("[VAC-10000]", CONOCIDOS) == ["VAC-10000"], "5 dígitos reales sí resuelven"


class TestUnCodigoQueContieneAOtro:
    """🔴 `ECO` y `ECO-2026`: el caso que la UNICIDAD NO resuelve.

    Los dos códigos son distintos, así que el índice único los deja convivir. Pero `ECO` aparece
    como texto adentro de `ECO-2026`, y sin la regla de contención todo CV de `ECO-2026` quedaría
    marcado `codigo_ambiguo` PARA SIEMPRE — o sea, la búsqueda entera dejaría de matchear sola.
    """

    @pytest.mark.parametrize("asunto", ["[ECO-2026]", "eco 2026", "Postulación ECO-2026 Analista"])
    def test_gana_el_mas_largo_porque_el_corto_es_un_pedazo_suyo(self, asunto) -> None:
        """No es "preferir el más largo": es que en el texto hay UNA sola mención."""
        assert codigos_en(asunto, CONOCIDOS) == ["ECO-2026"]

    def test_EL_CONTRASTE_el_corto_solo_sigue_resolviendo(self) -> None:
        """Sin esto, un matcher que descartara siempre el código corto pasaría el test de arriba
        y dejaría `ECO` inalcanzable."""
        assert codigos_en("[ECO] mi cv", CONOCIDOS) == ["ECO"]

    def test_EL_CONTRASTE_los_dos_por_separado_SI_son_ambiguos(self) -> None:
        """Dos menciones DISJUNTAS son dos códigos de verdad: el mail va a revisión, que es lo
        correcto. La regla de contención mira posiciones, no largos."""
        assert codigos_en("[ECO] y [ECO-2026]", CONOCIDOS) == ["ECO", "ECO-2026"]


class TestDosCodigos:

    def test_dos_distintos_no_resuelven(self) -> None:
        """🔴 Sin match, a revisión. Elegir el primero es una decisión invisible sobre la carrera
        de alguien: el CV entra a una búsqueda que quizás no es la suya y nadie se entera."""
        assert codigos_en("RE: [VAC-0001] y [VAC-0002]", CONOCIDOS) == ["VAC-0001", "VAC-0002"]

    def test_el_mismo_repetido_NO_es_ambiguo(self) -> None:
        """`[VAC-0001] re: vac 0001` es un código solo. Tratarlo como ambiguo mandaría a revisión
        un mail perfectamente claro — el caso típico de una cadena de respuestas."""
        assert codigos_en("[VAC-0001] re: vac 0001", CONOCIDOS) == ["VAC-0001"]

    def test_tres_distintos_tampoco(self) -> None:
        assert len(codigos_en("VAC-0001 VAC-0002 VAC-0003", CONOCIDOS)) == 3


def test_none_no_revienta() -> None:
    """Un mail sin asunto no puede tumbar la corrida."""
    assert codigos_en(None, CONOCIDOS) == []


def test_sin_vacantes_cargadas_no_matchea_nada() -> None:
    """El sistema recién instalado, y el contraste que prueba que la lista SE USA: con
    `CONOCIDOS` vacío no puede salir ningún código, ni siquiera de un asunto perfecto. Un matcher
    que ignorara el parámetro y siguiera reconociendo una forma pasaría todo el archivo menos
    esto."""
    assert codigos_en("[VAC-0001]", []) == []

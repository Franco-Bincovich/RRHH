"""
Los límites de subida no pueden superar el techo de la plataforma.

Es lo que hace REAL el "un solo número a tocar" de `utils/files.py`: si alguien sube un límite
por encima de `LIMITE_PLATAFORMA_MB`, la plataforma lo va a rechazar con un 413 crudo antes de
que el código lo vea y el usuario recibe un error incomprensible. El límite se leería como una
promesa que la app no puede cumplir.

El barrido es AUTOMÁTICO sobre el módulo (`MAX_SIZE_*` por introspección), así que un límite
NUEVO queda cubierto sin tocar este archivo — que es exactamente el modo en que se colaron los
tres que esta tanda vino a corregir (certificado y adjunto en 10 MB, CV en 5).

Lleva guarda de mínimo: sin ella, si la derivación de nombres se rompiera el barrido devolvería
0 constantes y el test pasaría sin haber comparado nada.
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

import pytest

from utils import files as f
from utils.errors import AppError

_TECHO_BYTES = f.LIMITE_PLATAFORMA_MB * 1024 * 1024

# Todas las constantes de tamaño del módulo, por introspección — no una lista escrita a mano.
LIMITES = {n: v for n, v in vars(f).items() if n.startswith("MAX_SIZE_") and isinstance(v, int)}


def test_hay_limites_para_barrer():
    """Guarda de mínimo: si el barrido no encuentra nada, todo lo de abajo pasa vacuo."""
    assert len(LIMITES) >= 5, f"esperaba al menos 5 constantes MAX_SIZE_*, encontré {LIMITES}"


@pytest.mark.parametrize("nombre", sorted(LIMITES))
def test_ningun_limite_supera_el_techo_de_la_plataforma(nombre):
    """🔴 Cada MAX_SIZE_* tiene que quedar DEBAJO de LIMITE_PLATAFORMA_MB.

    Para que falle: subir cualquiera de los límites por encima de 4,5 MB — que es el estado en
    el que estaban `MAX_SIZE_CERTIFICADO` y `MAX_SIZE_ADJUNTO` (10 MB) y el `_MAX_SIZE` propio de
    cv_service (5 MB) antes de esta tanda.
    """
    valor = LIMITES[nombre]
    assert valor < _TECHO_BYTES, (
        f"{nombre} = {valor / 1024 / 1024:.1f} MB supera el techo de "
        f"{f.LIMITE_PLATAFORMA_MB} MB: la plataforma lo rechazaría con 413 antes de la app"
    )


def test_los_limites_de_subida_derivan_de_uno_solo():
    """Los cuatro que salen del techo son EL MISMO valor: un cambio de hosting toca un número.

    El logo queda afuera a propósito (2 MB es criterio propio, no de la plataforma), y se afirma
    que sigue siendo distinto para que nadie lo unifique "por consistencia"."""
    assert f.MAX_SIZE_CERTIFICADO == f.MAX_SIZE_SUBIDA
    assert f.MAX_SIZE_CSV == f.MAX_SIZE_SUBIDA
    assert f.MAX_SIZE_ADJUNTO == f.MAX_SIZE_SUBIDA
    assert f.MAX_SIZE_CV == f.MAX_SIZE_SUBIDA
    assert f.MAX_SIZE_LOGO != f.MAX_SIZE_SUBIDA


def test_cv_service_no_tiene_su_propio_limite():
    """El CV usa la constante compartida, no un número propio.

    Se mira el código fuente porque el punto es que la SEGUNDA fuente no exista: un test sobre el
    comportamiento pasaría igual con `_MAX_SIZE = 4.2 MB` duplicado acá, y volvería a
    desincronizarse en el próximo cambio de techo."""
    import inspect

    from services import cv_service

    fuente = inspect.getsource(cv_service)
    assert "MAX_SIZE_CV" in fuente, "no usa la constante compartida"
    assert "_MAX_SIZE " not in fuente, "volvió a declarar su propio límite"
    # La señal de un límite CALCULADO acá: no se busca el texto "5 MB" porque el docstring
    # menciona ese número al explicar por qué se sacó, y un test no debería obligar a borrar la
    # explicación de un bug para pasar.
    assert "1024 * 1024" not in fuente, "hay un tamaño calculado en este módulo"


class TestElMensajeMuestraElLimiteCorrecto:
    """El número del mensaje sale del límite, no de un literal — en los cuatro casos."""

    @pytest.mark.parametrize("nombre", sorted(LIMITES))
    def test_validate_upload_nombra_el_limite_real(self, nombre):
        """Para que falle: volver a la división entera (`//`), que con 4,2 MB decía "4 MB"."""
        limite = LIMITES[nombre]
        with pytest.raises(AppError) as exc:
            f.validate_upload(b"x" * (limite + 1), "text/csv", ("text/csv",), limite, "archivo")
        assert exc.value.code == "FILE_TOO_LARGE"
        esperado = f"{limite / (1024 * 1024):g} MB"
        assert esperado in str(exc.value), f"{nombre}: el mensaje no dice {esperado}"

    def test_el_mensaje_no_arrastra_ceros_sobrantes(self):
        """Un límite redondo dice "2 MB", no "2.0 MB"; el de 4,2 dice "4.2 MB"."""
        assert f.mensaje_supera_tamano("logo", f.MAX_SIZE_LOGO).endswith("2 MB")
        assert f.mensaje_supera_tamano("archivo", f.MAX_SIZE_SUBIDA).endswith("4.2 MB")

    def test_el_cv_usa_el_mismo_texto_y_el_mismo_numero(self):
        """El mensaje del CV sale del helper compartido, con su code propio intacto."""
        from services.cv_service import CvService

        with pytest.raises(AppError) as exc:
            CvService().validar(b"x" * (f.MAX_SIZE_CV + 1), "cv.pdf", "application/pdf")
        assert exc.value.code == "CV_TOO_LARGE"      # contrato propio, no se cambió
        assert exc.value.status_code == 413
        assert str(exc.value) == f.mensaje_supera_tamano("CV", f.MAX_SIZE_CV)

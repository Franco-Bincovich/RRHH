"""
El texto listo para pegar en el aviso de LinkedIn (`services/_vacante_aviso.py`).

Lo que se protege acá es que **la frase sea SIEMPRE la misma**: es la instrucción que va a leer
un candidato de afuera, y si cambia entre avisos el código deja de matchear y el CV termina en
"sin asignar" sin que nada falle visiblemente. Por eso hay un test sobre la forma literal del
texto y no solo sobre "que no esté vacío".

## Los dos fakes, y qué puede desmentir cada uno

  · `_VacanteRepo` modela DOS empresas y devuelve `None` cuando la vacante es de otra: sin eso,
    la barrera de empresa no se podría desmentir (caso #1 de la regla del repo).
  · `_RemitenteRepo` se construye CON o SIN casilla. El camino sin casilla es la mitad que
    importa: un aviso que diga "Enviá tu CV a None" se publica y nadie se entera hasta que no
    llega ni un CV.
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

from datetime import datetime, timezone  # noqa: E402
from typing import Optional  # noqa: E402
from uuid import UUID, uuid4  # noqa: E402

import pytest  # noqa: E402

from schemas.vacante import VacanteResponse  # noqa: E402
from services._vacante_aviso import aviso  # noqa: E402
from utils.errors import AppError  # noqa: E402

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
PROPIA = UUID("11111111-1111-1111-1111-111111111111")
AJENA = UUID("22222222-2222-2222-2222-222222222222")
INEXISTENTE = UUID("33333333-3333-3333-3333-333333333333")

_EMPRESAS = {str(PROPIA): EMPRESA_A, str(AJENA): EMPRESA_B}
_CODIGOS = {str(PROPIA): "VAC-0007", str(AJENA): "VAC-0008"}


class _VacanteRepo:
    """HONRA `empresa_id` y devuelve None si la vacante es de otra empresa."""

    def find_by_id(self, id, empresa_id=None) -> Optional[VacanteResponse]:
        emp = _EMPRESAS.get(str(id))
        if not emp or (empresa_id and str(emp) != str(empresa_id)):
            return None
        # Construida A PARTIR del id pedido: si devolviera una constante, el test del código no
        # distinguiría "sale de la vacante" de "sale del fake".
        return VacanteResponse(id=str(id), codigo=_CODIGOS[str(id)], empresa_id=str(emp),
                               titulo="Analista", area_id=str(uuid4()), estado="nueva",
                               created_at=datetime.now(timezone.utc))


class _RemitenteRepo:
    def __init__(self, email: Optional[str] = "rrhh@karstec.com") -> None:
        self._email = email

    def get_remitente(self) -> Optional[dict]:
        # La fila ENTERA, como el repo real (`select("*")`), no solo el email.
        return {"user_id": str(uuid4()), "tipo": "google", "email_cuenta": self._email,
                "es_remitente_sistema": True} if self._email else None


def _error(fn) -> AppError:
    with pytest.raises(AppError) as exc:
        fn()
    return exc.value


# ── con casilla ───────────────────────────────────────────────────────────────

def test_el_texto_trae_la_casilla_y_el_codigo_entre_corchetes() -> None:
    """🔴 La forma LITERAL. Los corchetes son parte del token, no decoración: acotan la búsqueda
    dentro del asunto. Si alguien "limpia" la frase y los saca, el mail sigue entrando y el
    código deja de matchear.

    ¿Qué tendría que ser distinto en el fake para que falle? Que `_VacanteRepo` devolviera un
    código fijo en vez del de la fila pedida — ahí el test no vería la diferencia entre el código
    de la vacante y una constante del doble.
    """
    r = aviso(_VacanteRepo(), _RemitenteRepo(), PROPIA, EMPRESA_A)
    assert r.texto == "Enviá tu CV a rrhh@karstec.com con el asunto [VAC-0007]"
    assert (r.codigo, r.casilla) == ("VAC-0007", "rrhh@karstec.com")


def test_el_codigo_sale_de_la_vacante_pedida() -> None:
    """Dos vacantes distintas dan dos avisos distintos."""
    a = aviso(_VacanteRepo(), _RemitenteRepo(), PROPIA, EMPRESA_A)
    b = aviso(_VacanteRepo(), _RemitenteRepo(), AJENA, EMPRESA_B)
    assert (a.codigo, b.codigo) == ("VAC-0007", "VAC-0008")
    assert a.texto != b.texto


# ── sin casilla ───────────────────────────────────────────────────────────────

def test_sin_casilla_no_se_arma_un_texto_a_medias() -> None:
    """La mitad que importa: un aviso con "None" adentro se publica y no lo nota nadie."""
    r = aviso(_VacanteRepo(), _RemitenteRepo(email=None), PROPIA, EMPRESA_A)
    assert r.texto is None and r.casilla is None
    assert r.codigo == "VAC-0007", "el código no depende de la integración: sale igual"


def test_sin_casilla_el_codigo_sigue_estando() -> None:
    """RRHH puede copiar el código aunque la casilla todavía no esté designada."""
    assert aviso(_VacanteRepo(), _RemitenteRepo(email=None), AJENA, None).codigo == "VAC-0008"


# ── la barrera de empresa ─────────────────────────────────────────────────────

def test_vacante_de_otra_empresa_es_404() -> None:
    err = _error(lambda: aviso(_VacanteRepo(), _RemitenteRepo(), AJENA, EMPRESA_A))
    assert (err.code, err.status_code) == ("VACANTE_NOT_FOUND", 404)


def test_ajena_indistinguible_de_inexistente() -> None:
    """Sin oráculo de enumeración: mismo status, code y mensaje. Sale del literal canónico
    del módulo (`_vacante_write._or_404`), no de una copia."""
    ajena = _error(lambda: aviso(_VacanteRepo(), _RemitenteRepo(), AJENA, EMPRESA_A))
    inexistente = _error(lambda: aviso(_VacanteRepo(), _RemitenteRepo(), INEXISTENTE, EMPRESA_A))
    assert (ajena.code, ajena.message, ajena.status_code) == \
           (inexistente.code, inexistente.message, inexistente.status_code)


def test_consolidado_no_restringe() -> None:
    """`empresa_id=None` es 'todas las empresas', no un fallo de validación."""
    assert aviso(_VacanteRepo(), _RemitenteRepo(), AJENA, None).codigo == "VAC-0008"


def test_la_casilla_no_se_pide_antes_de_validar_la_vacante() -> None:
    """El orden de los gates: la barrera va ANTES de tocar cualquier otra cosa. Si el remitente
    se consultara primero, una vacante ajena podría responder por un fallo de la integración y
    ese código distinto delataría que el recurso existe."""
    class _Explota:
        def get_remitente(self):
            raise AssertionError("se pidió la casilla antes de validar la vacante")

    err = _error(lambda: aviso(_VacanteRepo(), _Explota(), AJENA, EMPRESA_A))
    assert err.code == "VACANTE_NOT_FOUND"

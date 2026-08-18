"""
El 23505 de `empleados` sale como 409 con su code, y no como 500.

## Qué clase de bug cierra

`empleados` tiene tres unicidades que un dato del formulario puede chocar y **sólo una tenía
pre-chequeo** (legajo). Un alta con un `email_corporativo` o un `dni` repetido llegaba al INSERT,
PostgREST devolvía 23505, la `APIError` subía sin que nadie la mapeara y `global_error_handler`
la mandaba por su rama de "error inesperado": **500 INTERNAL_ERROR** para un dato que la persona
que carga el legajo corrige en diez segundos. Mismo bug, misma causa y mismo arreglo que el de
`objetivos` (`_objetivos_duplicado`).

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?

**Que los dobles no tuvieran la FORMA de lo que imitan.** La respuesta completa vive con ellos,
en `tests/_empleado_duplicado_fakes.py`: se escribe UNA vez y al lado del código del que habla,
en vez de acá, donde se separaría del doble que describe.

Lo que sí es propio de este archivo: **`test_sin_la_traduccion_esto_seria_un_500`**. Ancla el
CONTRASTE pasando la excepción CRUDA por el handler global real y verificando que da 500. Sin ese
test, los demás afirman que sale 409 sin que nadie haya comprobado que antes salía otra cosa — o
sea que medirían una mejora contra una suposición.
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

import json  # noqa: E402
from types import SimpleNamespace  # noqa: E402

import pytest  # noqa: E402

from middleware.error_handler import global_error_handler  # noqa: E402
from schemas.empleado import EmpleadoUpdate  # noqa: E402
from tests._empleado_duplicado_fakes import (  # noqa: E402
    _CASOS, _EMPRESA, _ID, _ApiError, _create, _resp, _service,
)
from utils.errors import AppError  # noqa: E402

# ── El alta ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("constraint,code", _CASOS, ids=[c for _, c in _CASOS])
def test_el_alta_duplicada_da_409_con_su_code(constraint: str, code: str) -> None:
    """Cada constraint elige SU mensaje. Los tres son 409, ninguno es 500."""
    svc, _, _ = _service(revienta=constraint)
    with pytest.raises(AppError) as exc:
        svc.create_empleado(_create(), "user-1", _EMPRESA)
    assert exc.value.status_code == 409
    assert exc.value.code == code


@pytest.mark.parametrize("constraint,code", _CASOS, ids=[c for _, c in _CASOS])
def test_el_mensaje_no_revela_de_quien_es_el_registro(constraint: str, code: str) -> None:
    """Dice QUÉ campo se repitió y nada más: ni nombre, ni legajo, ni empresa del otro.

    ¿Qué tendría que ser distinto para que falle? Que alguien "mejore" el mensaje pegándole el
    dato del registro que ya está — que es la mejora que convierte un error en un oráculo.
    """
    svc, _, _ = _service(revienta=constraint)
    with pytest.raises(AppError) as exc:
        svc.create_empleado(_create(), "user-1", _EMPRESA)
    texto = exc.value.message.lower()
    assert not any(p in texto for p in ("ana", "garcía", "11111111", "99999999"))


def test_una_constraint_desconocida_igual_es_409() -> None:
    """Un índice único FUTURO no puede volver a subir como 500.

    Es la conclusión que se conserva del molde de objetivos: reconocer el nombre elige el
    MENSAJE, no decide si es un 409. Un 23505 es siempre un choque de unicidad.
    """
    svc, _, _ = _service(revienta="empleados_algo_que_todavia_no_existe_uq")
    with pytest.raises(AppError) as exc:
        svc.create_empleado(_create(), "user-1", _EMPRESA)
    assert exc.value.status_code == 409
    assert exc.value.code == "EMPLEADO_DUPLICADO"


def test_lo_que_no_es_23505_se_relanza_tal_cual() -> None:
    """Un timeout o un 42703 NO se convierten en "ya existe un empleado".

    Sin esta rama, el traductor mandaría a corregir un email que está perfecto. Es el mismo
    recorte que `_objetivos_duplicado` declara y que `_carga_licencia` NO tiene.
    """
    svc, _, _ = _service()
    svc._repo.revienta = None

    class _Otro(Exception):
        code = "42703"

    def _explota(data, empresa_id):
        raise _Otro("column does not exist")

    svc._repo.save = _explota
    with pytest.raises(_Otro):
        svc.create_empleado(_create(), "user-1", _EMPRESA)


# ── La edición: las MISMAS unicidades por el otro camino ──────────────────────

@pytest.mark.parametrize("constraint,code", _CASOS, ids=[c for _, c in _CASOS])
def test_la_edicion_duplicada_tambien_da_409(constraint: str, code: str) -> None:
    """Cambiarle el email o el DNI a alguien puede chocar igual que un alta.

    Es la razón por la que la traducción vive en el SERVICE y no adentro de `repo.save`.
    """
    svc, _, _ = _service(revienta=constraint)
    with pytest.raises(AppError) as exc:
        svc.update_empleado(_ID, EmpleadoUpdate(email_corporativo="otra@karstec.com"),
                            _EMPRESA, "user-1")
    assert exc.value.status_code == 409
    assert exc.value.code == code


# ── El contraste: que el camino feliz siga intacto ────────────────────────────

def test_el_alta_normal_sigue_pasando() -> None:
    """CONTRASTE. Sin esto, un traductor que rechazara TODO también pasaría los tests de arriba.

    Se afirma sobre el dato que viajó (`guardados`) y sobre el que volvió, no sobre una
    constante del test.
    """
    svc, repo, audit = _service()
    creado = svc.create_empleado(_create(email_corporativo="nueva@karstec.com"),
                                 "user-1", _EMPRESA)
    assert creado.email_corporativo == "nueva@karstec.com"
    assert len(repo.guardados) == 1
    assert len(audit.calls) == 1, "el alta feliz sigue auditando"


def test_el_prechequeo_de_legajo_sigue_cortando_antes() -> None:
    """El atajo de mensaje no se rompió: cuando el SELECT SÍ encuentra, corta sin ir al INSERT.

    Los dos caminos dan el MISMO code, así que esto verifica que el pre-chequeo sigue vivo por
    dónde corta —el repo no llega a `save`—, no por lo que responde.
    """
    svc, repo, _ = _service()
    repo.find_by_legajo = lambda legajo, empresa_id: _resp(id="otro-id")
    with pytest.raises(AppError) as exc:
        svc.create_empleado(_create(legajo="A-100"), "user-1", _EMPRESA)
    assert exc.value.code == "LEGAJO_DUPLICADO"
    assert repo.guardados == [], "cortó antes del INSERT"


# ── El contrato de la respuesta, extremo a extremo ────────────────────────────

async def _por_el_handler(exc: Exception):
    """Pasa una excepción por el handler global REAL y devuelve (status, body).

    Es `async` porque el handler lo es, y la suite corre con `asyncio_mode=auto`. Se evita a
    propósito `get_event_loop().run_until_complete(...)`: está deprecado en 3.12 y sumaría un
    DeprecationWarning a la suite entera por una comodidad de dos tests.
    """
    req = SimpleNamespace(url=SimpleNamespace(path="/api/empleados"))
    resp = await global_error_handler(req, exc)
    return resp.status_code, json.loads(bytes(resp.body).decode("utf-8"))


async def test_el_409_respeta_el_contrato_error_message_code() -> None:
    """El body sale con las tres claves que el front busca en `toApiError`."""
    svc, _, _ = _service(revienta="empleados_email_corporativo_key")
    with pytest.raises(AppError) as exc:
        svc.create_empleado(_create(), "user-1", _EMPRESA)
    status, body = await _por_el_handler(exc.value)
    assert status == 409
    assert body["error"] is True
    assert body["code"] == "EMAIL_CORPORATIVO_DUPLICADO"
    assert body["message"]


async def test_sin_la_traduccion_esto_seria_un_500() -> None:
    """🔴 EL CONTRASTE QUE HACE QUE LOS DEMÁS SIGNIFIQUEN ALGO.

    La excepción CRUDA de PostgREST —la que llegaba antes de esta tanda— pasada por el mismo
    handler real da 500 INTERNAL_ERROR. Es la medición del bug, no una suposición sobre él.
    """
    status, body = await _por_el_handler(_ApiError("empleados_email_corporativo_key"))
    assert status == 500
    assert body["code"] == "INTERNAL_ERROR"

"""
La SUPERFICIE del endpoint del puente: que la ruta exista donde dice, y el contrato de su body.

📄 El acto está en `tests/test_candidato_contratar.py` y las guardas en
`tests/test_candidato_contratar_guardas.py`. Los tres archivos espejan los tres módulos del
service (`_candidato_contratar` · `_candidato_contratar_guardas` · `_candidato_contratar_mapeo`),
así que un lector que entra por cualquiera sabe dónde está el resto.

🔴 POR QUÉ EL TEST DE LA RUTA VA SEPARADO DE TODO LO DEMÁS. Los otros dos archivos corren contra
el app MÍNIMO de `tests/_contratar_arnes.py`, que monta el router a mano — así que ninguno puede
probar que la ruta esté montada en el app REAL, con su prefijo, y que nada la capture. Eso se
verifica por introspección de `main.app.routes`, que es un tipo de aserción distinto y no
necesita ni fakes ni cliente. Molde: `test_paridad_list_export`.
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

from tests._contratar_contexto import _Contexto  # noqa: E402
from tests._contratar_padron import C_OFERTA_A  # noqa: E402


@pytest.mark.parametrize("payload,motivo", [
    ({"roles": ["A"], "fecha_ingreso": "2030-01-01"}, "sin email"),
    ({"email_corporativo": "a@b.com", "fecha_ingreso": "2030-01-01"}, "sin roles"),
    ({"email_corporativo": "a@b.com", "roles": ["A"]}, "sin fecha"),
    ({"email_corporativo": "a@b.com", "roles": [], "fecha_ingreso": "2030-01-01"}, "roles vacío"),
], ids=["sin_email", "sin_roles", "sin_fecha", "roles_vacio"])
async def test_el_body_incompleto_da_422_con_el_contrato(payload: dict, motivo: str) -> None:
    """El 422 sale por el handler del repo, con `{error, message, code}` — no con el de FastAPI.

    `roles: []` entra acá y no en las guardas del service a propósito: lo corta el validador del
    schema, que es el MISMO que usa el alta de empleado (se importa, no se duplica).
    """
    ctx = _Contexto()
    async with ctx.cliente() as c:
        r = await c.post(f"/api/candidatos/{C_OFERTA_A}/contratar", json=payload)
    assert r.status_code == 422, motivo
    assert set(r.json()) >= {"error", "message", "code"}
    assert ctx.empleados_repo.guardados == []


# ── la ruta, en el app REAL ──────────────────────────────────────────────────

def test_la_ruta_esta_montada_en_el_app_real() -> None:
    """El arnés monta el router sobre un app desnudo, así que no puede probar el montaje real.

    Esto sí: que la ruta exista en `main.app` con su prefijo, y que ninguna ruta con parámetro en
    el segundo tramo pueda capturar el literal "contratar". Molde: `test_paridad_list_export`.
    """
    import main

    rutas = [(sorted(r.methods - {"HEAD", "OPTIONS"}), r.path) for r in main.app.routes
             if getattr(r, "path", "").startswith("/api/candidatos")]
    assert (["POST"], "/api/candidatos/{id}/contratar") in rutas
    capturadoras = [p for m, p in rutas if p.count("{") >= 2]
    assert not capturadoras, f"estas rutas capturarían 'contratar' como id: {capturadoras}"

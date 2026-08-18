"""
Las CINCO guardas del puente candidato → empleado, y lo que hereda del alta — todo por HTTP.

📄 El camino feliz, el mapeo y el ciclo completo están en `tests/test_candidato_contratar.py`.
El corte es el MISMO seam que el del service (`_candidato_contratar.py` vs
`_candidato_contratar_guardas.py`): de un lado lo que el puente HACE, del otro lo que RECHAZA.
Los dos archivos comparten `tests/_contratar_contexto.py`, así que prueban el mismo cableado.

═══════════════════════════════════════════════════════════════════════════════════════════
🚨 CADA GUARDA VA CON SU CONTRASTE, Y SIN ESO NINGUNA PRUEBA NADA
═══════════════════════════════════════════════════════════════════════════════════════════
Un `raise` incondicional pasaría todos los tests de rechazo de este archivo. Lo que los vuelve
capaces de fallar es el caso que NO dispara la guarda:

  · las tres de estado          → `test_el_camino_feliz_crea_el_empleado` (el otro archivo)
  · la de fecha (`< hoy`)       → `test_fecha_de_hoy_se_acepta`, acá abajo
  · la barrera de empresa (404) → `test_un_id_inexistente_da_EL_MISMO_404`, acá abajo
  · el 409 heredado del alta    → `test_si_el_alta_falla_el_candidato_no_queda_contratado`

Y todas verifican además que **no se escribió nada**: una guarda que rechaza después de crear el
empleado sería peor que no tenerla.
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

from datetime import date  # noqa: E402

import pytest  # noqa: E402

from tests._contratar_arnes import body  # noqa: E402
from tests._contratar_contexto import _Contexto, _contratar  # noqa: E402
from tests._contratar_fakes import FakeCandidatoRepo  # noqa: E402
from tests._contratar_padron import (  # noqa: E402
    AREA_B, AYER, C_EN_TECNICA, C_FANTASMA, C_OFERTA_A, C_OFERTA_B, C_SIN_VACANTE,
    C_YA_CONTRATADO, EMPRESA_A, EMPRESA_B, VAC_B,
)


# ── (e) (f) (g) (h) las cuatro guardas de estado, cada una con su contraste ───

@pytest.mark.parametrize("cid,code", [
    (C_YA_CONTRATADO, "CANDIDATO_NO_CONTRATABLE"),
    (C_SIN_VACANTE, "CANDIDATO_SIN_VACANTE"),
    (C_EN_TECNICA, "CANDIDATO_NO_ESTA_EN_OFERTA"),
], ids=["ya_contratado", "sin_vacante", "en_tecnica"])
async def test_las_guardas_de_estado_dan_409_con_su_code(cid: str, code: str) -> None:
    """(e)(f)(g) Cada una con SU code, y ninguna escribe nada."""
    ctx = _Contexto()
    async with ctx.cliente() as c:
        r = await c.post(f"/api/candidatos/{cid}/contratar", json=body())
    assert r.status_code == 409
    assert r.json()["code"] == code
    assert ctx.empleados_repo.guardados == [], "ninguna guarda puede escribir antes de rechazar"
    assert ctx.candidatos.estados_escritos == []


async def test_contratar_dos_veces_da_409() -> None:
    """(e) La segunda vez el candidato ya está en `contratado`. Es el caso REAL del doble click.

    Va por el endpoint dos veces sobre el MISMO candidato, no sobre uno prefabricado: así se
    prueba que la primera contratación deja al candidato en un estado que la segunda rechaza.
    """
    ctx = _Contexto()
    assert (await _contratar(ctx)).status_code == 201
    r2 = await _contratar(ctx)
    assert r2.status_code == 409 and r2.json()["code"] == "CANDIDATO_NO_CONTRATABLE"
    assert len(ctx.empleados_repo.guardados) == 1, "el segundo intento NO creó un segundo legajo"


async def test_fecha_de_ayer_da_400() -> None:
    """(h) Contratar mira hacia adelante. Si la persona ya entró, el camino es el alta normal."""
    ctx = _Contexto()
    r = await _contratar(ctx, fecha=AYER)
    assert r.status_code == 400
    assert r.json()["code"] == "FECHA_INGRESO_PASADA"
    assert ctx.empleados_repo.guardados == []


async def test_fecha_de_hoy_se_acepta() -> None:
    """CONTRASTE de la anterior: el límite es `< hoy`, no `<= hoy`. Alguien puede entrar HOY.

    Sin este test, cambiar el `<` por un `<=` no rompería nada y el endpoint rechazaría el caso
    más común de todos: la contratación que se carga el mismo día que la persona arranca.
    """
    ctx = _Contexto()
    r = await _contratar(ctx, fecha=date.today())
    assert r.status_code == 201, r.text


# ── (i) la barrera de empresa, con el caso consolidado ───────────────────────

async def test_candidato_de_otra_empresa_da_404() -> None:
    """(i) El header dice A, el candidato es de B. Mismo 404 que "no existe": sin oráculo."""
    ctx = _Contexto(empresa=EMPRESA_A)
    async with ctx.cliente() as c:
        r = await c.post(f"/api/candidatos/{C_OFERTA_B}/contratar", json=body())
    assert r.status_code == 404
    assert r.json()["code"] == "CANDIDATO_NOT_FOUND"
    assert ctx.empleados_repo.guardados == []


async def test_un_id_inexistente_da_EL_MISMO_404() -> None:
    """CONTRASTE del anterior: "no existe" y "es de otra empresa" tienen que ser indistinguibles.

    Si difirieran en status, code o mensaje, el endpoint sería un oráculo de enumeración de
    candidatos ajenos — que es exactamente lo que la Fase 2 cerró en todo el repo.
    """
    ctx = _Contexto(empresa=EMPRESA_A)
    async with ctx.cliente() as c:
        ajeno = await c.post(f"/api/candidatos/{C_OFERTA_B}/contratar", json=body())
        fantasma = await c.post(f"/api/candidatos/{C_FANTASMA}/contratar", json=body())
    assert ajeno.status_code == fantasma.status_code
    assert ajeno.json() == fantasma.json()


async def test_en_consolidado_la_vacante_se_busca_con_la_empresa_del_candidato() -> None:
    """(i) 🔴 EL CASO QUE SOLO DOS EMPRESAS PUEDEN DESMENTIR.

    En consolidado el header vale `None` y no restringe: el candidato de B ES alcanzable, y eso
    está bien. Lo que NO puede pasar es que su vacante y su alta se resuelvan sin empresa — ahí
    se podría armar un empleado con el área de una búsqueda de otra sociedad.

    Se afirma sobre CON QUÉ empresa se consultó el repo de vacantes, no sobre el resultado: con
    `None` la consulta también encuentra la fila, así que el resultado no distingue nada.
    """
    ctx = _Contexto(empresa=None)
    async with ctx.cliente() as c:
        r = await c.post(f"/api/candidatos/{C_OFERTA_B}/contratar", json=body())
    assert r.status_code == 201, r.text
    assert ctx.vacantes.consultas == [(VAC_B, EMPRESA_B)], "la vacante NO se buscó con None"
    assert str(ctx.empleados_repo.guardados[0].empresa_id) == EMPRESA_B
    assert str(ctx.empleados_repo.guardados[0].area_id) == AREA_B


# ── (j) lo que se hereda del alta ────────────────────────────────────────────

async def test_email_corporativo_repetido_da_409_y_no_500() -> None:
    """(j) El puente HEREDA la traducción del 23505 de A4.1: no la reimplementa.

    ¿Qué tendría que ser distinto para que falle? Que el service atrapara la excepción del alta y
    la convirtiera en otra cosa. El fake del repo de empleados levanta la `APIError` REAL de
    PostgREST, así que lo que se mide es qué sale por HTTP del otro lado.
    """
    ctx = _Contexto(revienta="empleados_email_corporativo_key")
    r = await _contratar(ctx)
    assert r.status_code == 409
    assert r.json()["code"] == "EMAIL_CORPORATIVO_DUPLICADO"

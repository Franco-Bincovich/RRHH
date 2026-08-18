"""
EL LÍMITE CONOCIDO del puente: no hay transacción, y qué pasa exactamente cuando eso muerde.

📄 El acto está en `tests/test_candidato_contratar.py`, las guardas en
`tests/test_candidato_contratar_guardas.py` y la superficie en
`tests/test_candidato_contratar_superficie.py`.

═══════════════════════════════════════════════════════════════════════════════════════════
🔴 POR QUÉ ESTO ES UN ARCHIVO Y NO DOS TESTS SUELTOS
═══════════════════════════════════════════════════════════════════════════════════════════
El puente hace DOS escrituras contra dos tablas —crea el empleado y marca al candidato— y
**PostgREST no da transacciones**. Eso no es un bug que se arregle: es una propiedad del stack,
y lo único responsable es MEDIR qué queda cuando falla la segunda, en vez de suponerlo.

Los dos tests de acá son las dos mitades de esa medición:

  · **el fallo del paso 1** (`test_si_el_alta_falla...`) — la mitad SEGURA: el alta va primero,
    así que si rebota no se tocó nada. El orden de las dos escrituras es load-bearing y esto lo
    fija: invertirlo dejaría al candidato marcado como contratado sin legajo detrás.
  · **el fallo del paso 2** (`test_si_falla_el_paso_2...`) — la mitad PELIGROSA, y la que hay que
    leer antes de tocar el puente. Está explicada en su docstring y en `docs/DEUDA-TECNICA.md`.

⚠️ Ninguno de los dos propone una compensación, y es deliberado: borrar el empleado recién creado
sería una segunda escritura que también puede fallar, y dejaría el caso PEOR — un alta auditada y
después borrada, sin rastro del porqué.
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

from tests._contratar_contexto import _Contexto, _contratar  # noqa: E402
from tests._contratar_fakes import FakeCandidatoRepo  # noqa: E402
from tests._contratar_padron import C_OFERTA_A  # noqa: E402


async def test_si_el_alta_falla_el_candidato_no_queda_contratado() -> None:
    """CONTRASTE: el orden importa. El alta va PRIMERO, así que si rebota no se tocó nada.

    Es la mitad segura del "sin transacción": el fallo del paso 1 no deja rastro. La mitad
    peligrosa —el paso 2 fallando después del 1— está documentada en DEUDA-TECNICA.
    """
    ctx = _Contexto(revienta="empleados_email_corporativo_key")
    await _contratar(ctx)
    assert ctx.candidatos.estados_escritos == []
    assert ctx.candidatos.filas[C_OFERTA_A].estado == "activo"


# ── el límite conocido: sin transacción ──────────────────────────────────────

async def test_si_falla_el_paso_2_el_reintento_choca_por_el_email() -> None:
    """🔴 EL CASO SIN TRANSACCIÓN, MEDIDO — no razonado.

    PostgREST no da transacciones. Si el paso 2 (marcar el candidato) falla después de que el
    paso 1 (crear el empleado) tuvo éxito, queda **el empleado creado y el candidato en
    `activo`**. Este test simula exactamente eso y mide qué pasa al reintentar.

    El resultado importa y no es obvio: el reintento **NO crea un segundo empleado**. Choca
    contra `empleados_email_corporativo_key` —que es UNIQUE GLOBAL— y sale como **409
    `EMAIL_CORPORATIVO_DUPLICADO`** gracias a la traducción de A4.1. Sin esa traducción sería un
    500 y el operador no tendría forma de saber qué pasó.

    ⚠️ Lo que este test NO dice, y está en `docs/DEUDA-TECNICA.md`: el bloqueo depende de que se
    reintente con EL MISMO email corporativo. Con uno distinto, las cuatro guardas siguen pasando
    (el candidato quedó en `activo`) y se crea un SEGUNDO legajo para la misma persona. El legajo
    no protege —el puente no lo setea, y `ensure_legajo_unico` corta cuando es None— y el DNI
    tampoco, porque el puente no lo escribe.
    """
    ctx = _Contexto()
    # el paso 1 funciona; el paso 2 revienta
    def _explota(candidato_id, estado, empresa_id=None):
        raise RuntimeError("PostgREST caído entre el INSERT y el UPDATE")
    ctx.candidatos.update_estado = _explota
    with pytest.raises(RuntimeError):
        await _contratar(ctx)
    assert len(ctx.empleados_repo.guardados) == 1, "el empleado SÍ quedó creado"
    assert ctx.candidatos.filas[C_OFERTA_A].estado == "activo", "el candidato NO se marcó"

    # el reintento, con el mismo email: choca contra la UNIQUE global
    ctx.candidatos.update_estado = FakeCandidatoRepo.update_estado.__get__(ctx.candidatos)
    ctx.empleados_repo.revienta = "empleados_email_corporativo_key"
    r = await _contratar(ctx)
    assert r.status_code == 409
    assert r.json()["code"] == "EMAIL_CORPORATIVO_DUPLICADO"
    assert len(ctx.empleados_repo.guardados) == 1, "NO se creó un segundo legajo"

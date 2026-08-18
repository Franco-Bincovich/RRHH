"""
El CONTEXTO de los tests del puente: los cuatro colaboradores + el app, armados juntos.

Helper, no test. Lo comparten `tests/test_candidato_contratar.py` (camino feliz, mapeo y ciclo) y
`tests/test_candidato_contratar_guardas.py` (las cinco guardas y lo que se hereda del alta).

📄 El PADRÓN está en `tests/_contratar_padron.py`, los FAKES en `tests/_contratar_fakes.py` y el
ARNÉS HTTP en `tests/_contratar_arnes.py`.

🔴 VIVE ACÁ Y NO EN UNO DE LOS DOS ARCHIVOS DE TEST porque los dos necesitan armar el mismo
escenario, y una segunda copia podría cablear distinto —otro `EmpleadoService`, otro orden de
colaboradores— y hacer que las guardas se prueben contra un puente que no es el que corre.
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

from typing import Optional  # noqa: E402

from services.contratacion_service import ContratacionService  # noqa: E402
from services.empleado_service import EmpleadoService  # noqa: E402
from tests._contratar_arnes import app_con, body, cliente  # noqa: E402
from tests._contratar_fakes import (  # noqa: E402
    FakeAreas, FakeAudit, FakeCandidatoRepo, FakeEmpleadoRepo, FakeVacanteRepo,
)
from tests._contratar_padron import C_OFERTA_A, EMPRESA_A  # noqa: E402


class _Contexto:
    """Los cuatro colaboradores + el app, armados juntos para poder afirmar sobre cualquiera."""

    def __init__(self, empresa: Optional[str] = EMPRESA_A, revienta: Optional[str] = None) -> None:
        self.candidatos = FakeCandidatoRepo()
        self.vacantes = FakeVacanteRepo()
        self.empleados_repo = FakeEmpleadoRepo(revienta)
        self.audit = FakeAudit()
        # El alta es la REAL (`EmpleadoService`), no un doble: así el puente hereda de verdad sus
        # validaciones y su traducción del 23505, que es justo lo que el caso (j) verifica.
        self.empleados = EmpleadoService(repo=self.empleados_repo, audit=FakeAudit(),
                                         area_repo=FakeAreas())
        self.service = ContratacionService(self.candidatos, self.vacantes, self.empleados,
                                           self.audit)
        self.app = app_con(self.service, empresa)

    def cliente(self):
        return cliente(self.app)


async def _contratar(ctx: _Contexto, cid: str = C_OFERTA_A, **kw):
    async with ctx.cliente() as c:
        return await c.post(f"/api/candidatos/{cid}/contratar", json=body(**kw))

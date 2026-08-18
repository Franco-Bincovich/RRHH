"""
Los dobles del test del 23505 de `empleados`: la excepción de PostgREST y el repo que la levanta.

Helper, no test. Lo consume `tests/test_empleado_duplicado.py`, que quedó en 284 contra un tope
de 200. El corte cae donde el archivo NO crece: los 15 tests son la parte que se agrega cuando
aparece una unicidad nueva; estos dobles son estables.

Molde: `tests/_vacante_fake.py`, `tests/_columnas_candidatos.py`.

═══════════════════════════════════════════════════════════════════════════════════════════
🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO ACÁ PARA QUE LOS TESTS NO PUEDAN FALLAR?
═══════════════════════════════════════════════════════════════════════════════════════════

**Que `_ApiError` no tuviera la FORMA de la excepción real de PostgREST.** Un doble que levantara
un `AppError` ya armado probaría que el service re-lanza AppErrors —que no es lo que se persigue—
y dejaría la traducción entera sin ejercitar. Por eso copia las tres cosas que
`_es_choque_de_unicidad` y `_empleado_constraints.traducir` realmente leen: `.code` con el
SQLSTATE, `.message` con el texto de Postgres, y el nombre de la constraint adentro de ese texto.

**Y que `_FakeRepo.save` devolviera un objeto prefabricado.** Construye la respuesta A PARTIR de
lo que recibe, como manda la regla del repo: con una constante, el test del alta feliz afirmaría
algo sobre su propio fixture en vez de sobre lo que el service hizo viajar.
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
from types import SimpleNamespace  # noqa: E402
from uuid import UUID  # noqa: E402

from schemas.empleado import EmpleadoCreate, EmpleadoResponse  # noqa: E402
from services.empleado_service import EmpleadoService  # noqa: E402

_EMPRESA = UUID("99999999-9999-9999-9999-999999999999")
_AREA = UUID("22222222-2222-2222-2222-222222222222")
_ID = UUID("11111111-1111-1111-1111-111111111111")

# El texto EXACTO que Postgres pone en un unique_violation. Se escribe entero y no sólo el nombre
# de la constraint porque `_traducir` busca dentro del mensaje: un fake que pasara sólo el nombre
# suelto no ejercitaría esa búsqueda.
_MSG = 'duplicate key value violates unique constraint "{}"'

# (constraint, code esperado). Las TRES unicidades componibles de la tabla, del catálogo.
_CASOS = [
    ("empleados_email_corporativo_key", "EMAIL_CORPORATIVO_DUPLICADO"),
    ("empleados_empresa_dni_uq", "DNI_DUPLICADO"),
    ("empleados_legajo_empresa_key", "LEGAJO_DUPLICADO"),
]


class _ApiError(Exception):
    """Doble de `postgrest.exceptions.APIError` con las tres cosas que el traductor lee."""

    def __init__(self, constraint: str, code: str = "23505") -> None:
        self.message = _MSG.format(constraint)
        self.code = code
        self.details = ""
        super().__init__(self.message)


def _resp(**over) -> EmpleadoResponse:
    base = {
        "id": str(_ID), "nombre": "Ana", "apellido": "García",
        "email_corporativo": "ana@karstec.com", "empresa_id": str(_EMPRESA),
        "area_id": str(_AREA), "roles": ["Analista"], "modalidad_trabajo": "presencial",
        "tipo_contrato": "efectivo", "fecha_ingreso": "2024-01-01",
        "estado": "activo", "created_at": "2024-01-01T00:00:00Z",
    }
    base.update(over)
    return EmpleadoResponse.model_validate(base)


def _create(**over) -> EmpleadoCreate:
    base = dict(nombre="Ana", apellido="García", email_corporativo="ana@karstec.com",
                area_id=_AREA, roles=["Analista"], tipo_contrato="efectivo",
                fecha_ingreso=date(2024, 1, 1), empresa_id=_EMPRESA)
    base.update(over)
    return EmpleadoCreate(**base)


class _FakeRepo:
    """Repo que puede explotar como PostgREST. `revienta` es la constraint que rebota, o None.

    🔴 CONSTRUYE LA RESPUESTA A PARTIR DE LO QUE RECIBE en el camino feliz (el `save` devuelve un
    empleado con el email que le mandaron), como manda la regla del repo: un objeto prefabricado
    haría que el test del alta normal afirme algo sobre su propia constante.
    """

    def __init__(self, revienta=None) -> None:
        self.revienta = revienta
        self.guardados: list[EmpleadoCreate] = []

    def find_by_legajo(self, legajo, empresa_id):
        return None  # el pre-chequeo no encuentra nada: la carrera es justamente ésa

    def find_by_id(self, id, empresa_id=None):
        return _resp()

    def save(self, data: EmpleadoCreate, empresa_id):
        if self.revienta:
            raise _ApiError(self.revienta)
        self.guardados.append(data)
        return _resp(email_corporativo=data.email_corporativo, nombre=data.nombre)

    def update(self, id, data, empresa_id=None):
        if self.revienta:
            raise _ApiError(self.revienta)
        return _resp()


class _FakeAudit:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def registrar(self, **kwargs) -> None:
        self.calls.append(kwargs)


class _FakeAreas:
    def find_by_id(self, area_id, empresa_id=None):
        return SimpleNamespace(id=area_id)


def _service(revienta=None) -> tuple:
    repo, audit = _FakeRepo(revienta), _FakeAudit()
    return EmpleadoService(repo=repo, audit=audit, area_repo=_FakeAreas()), repo, audit

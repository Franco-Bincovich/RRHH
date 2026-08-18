"""
LOS FAKES del puente candidato → empleado: qué responde cada colaborador.

Helper, no test. Lo consumen `tests/_contratar_arnes.py` y `tests/test_candidato_contratar.py`.

📄 **EL PADRÓN vive en `tests/_contratar_padron.py`** (qué filas existen) y **EL ARNÉS HTTP en
`tests/_contratar_arnes.py`** (el app mínimo con el router real y el cliente). Salieron en tres
archivos porque juntos daban 215/200, y el corte responde tres preguntas distintas: qué datos
hay · qué responde cada colaborador · cómo se le pega al endpoint.

═══════════════════════════════════════════════════════════════════════════════════════════
🔴 LOS CUATRO FAKES HONRAN `empresa_id`, Y ESA ES LA CONDICIÓN PARA QUE LOS TESTS SIRVAN
═══════════════════════════════════════════════════════════════════════════════════════════
Un fake cuyo `find_by_id(id, empresa_id)` acepta el parámetro y lo ignora da **verde falso**: el
test pasa sin validar nada, y es exactamente el bug que la barrera de empresa viene a cubrir. Es
el caso #1 de la regla transversal del repo.

`FakeVacanteRepo` además **registra CON QUÉ empresa se lo consultó**. Es lo único que permite
afirmar la mitad no obvia de la barrera —que la vacante se busque con la empresa del CANDIDATO y
no con la del header— porque en modo consolidado el header vale `None`, la consulta encuentra la
fila igual, y "no restringió" es indistinguible de "restringió con None" mirando el resultado.

Y los dos repos de escritura **construyen la respuesta A PARTIR de lo que reciben**, nunca
devuelven un objeto prefabricado: si no, el test afirmaría sobre su propia constante en vez de
sobre lo que el service mandó.
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
from uuid import UUID  # noqa: E402

from schemas.empleado import EmpleadoResponse as _EmpleadoResponse  # noqa: E402
from tests._contratar_padron import _PADRON, _VACANTES  # noqa: E402


class FakeCandidatoRepo:
    """🔴 HONRA `empresa_id`: devuelve None cuando no coincide. Ver el encabezado."""

    def __init__(self) -> None:
        self.filas = {k: v.model_copy(deep=True) for k, v in _PADRON.items()}
        self.estados_escritos: list[tuple] = []

    def find_by_id(self, candidato_id: str, empresa_id: Optional[UUID] = None):
        c = self.filas.get(candidato_id)
        if not c:
            return None
        if empresa_id and str(c.empresa_id) != str(empresa_id):
            return None
        return c

    def update_estado(self, candidato_id: str, estado: str, empresa_id: Optional[UUID] = None):
        # Construye la respuesta A PARTIR de lo que recibe: un objeto prefabricado haría que el
        # test afirme sobre su propia constante en vez de sobre lo que el service mandó.
        self.estados_escritos.append((candidato_id, estado, empresa_id))
        c = self.filas[candidato_id]
        c.estado = estado
        return c


class FakeVacanteRepo:
    """Honra `empresa_id` igual que el de candidatos, y registra CON QUÉ empresa se lo consultó.

    Ese registro es lo que permite probar la mitad no obvia de la barrera: que la vacante se
    busque con la empresa DEL CANDIDATO y no con la del header (que en consolidado es None)."""

    def __init__(self) -> None:
        self.filas = {k: v.model_copy(deep=True) for k, v in _VACANTES.items()}
        self.consultas: list[tuple] = []

    def find_by_id(self, vacante_id: str, empresa_id: Optional[UUID] = None):
        self.consultas.append((vacante_id, str(empresa_id) if empresa_id else None))
        v = self.filas.get(vacante_id)
        if not v:
            return None
        if empresa_id and str(v.empresa_id) != str(empresa_id):
            return None
        return v


class FakeAudit:
    def __init__(self) -> None:
        self.eventos: list[dict] = []

    def registrar(self, **kwargs) -> None:
        self.eventos.append(kwargs)


class FakeEmpleadoRepo:
    """Repo de empleados que GUARDA y MUTA de verdad, para poder recorrer el ciclo completo.

    🔴 NO SE REUSÓ `_empleado_duplicado_fakes._FakeRepo`, que ya existe y también sabe reventar
    con un 23505. Aquel devuelve SIEMPRE la misma fila prefabricada —le alcanza, porque prueba la
    traducción del error y no el estado— y acá hace falta que `find_by_id` devuelva **el empleado
    que se acaba de crear, con el estado que tenga en ese momento**: sin eso, el paso `activar`
    del ciclo leería un `activo` prefabricado y el test pasaría sin haber activado nada.

    `revienta` es el nombre de la constraint que rebota, o None. Levanta la `APIError` REAL de
    PostgREST (misma forma: `.code` con el SQLSTATE y el nombre de la constraint en el mensaje),
    porque lo que el caso (j) mide es que el puente HEREDE la traducción de A4.1, no que la
    reimplemente.
    """

    def __init__(self, revienta: Optional[str] = None) -> None:
        self.revienta = revienta
        self.guardados: list = []
        self.filas: dict = {}

    def find_by_legajo(self, legajo, empresa_id):
        return None  # el padrón no carga legajos: el pre-chequeo no encuentra nada

    def find_by_id(self, id, empresa_id=None):
        return self.filas.get(str(id))

    def save(self, data, empresa_id):
        if self.revienta:
            raise _ApiErrorPostgrest(self.revienta)
        self.guardados.append(data)
        creado = _EmpleadoResponse.model_validate({
            "id": f"emp-{len(self.guardados)}", "nombre": data.nombre, "apellido": data.apellido,
            "email_corporativo": data.email_corporativo, "empresa_id": str(empresa_id),
            "area_id": str(data.area_id), "roles": data.roles,
            "modalidad_trabajo": data.modalidad_trabajo, "tipo_contrato": data.tipo_contrato,
            "fecha_ingreso": data.fecha_ingreso.isoformat(), "estado": data.estado,
            "created_at": "2026-01-01T00:00:00Z",
        })
        self.filas[creado.id] = creado
        return creado

    def update(self, id, data, empresa_id=None):
        fila = self.filas.get(str(id))
        if not fila:
            return None
        # Aplica el patch DE VERDAD: si devolviera la fila sin tocar, el pase a activo sería
        # indistinguible de no haber hecho nada.
        for campo, valor in data.model_dump(exclude_none=True).items():
            setattr(fila, campo, valor)
        return fila


class _ApiErrorPostgrest(Exception):
    """Doble de `postgrest.exceptions.APIError` con lo que el traductor de A4.1 lee."""

    def __init__(self, constraint: str) -> None:
        self.message = f'duplicate key value violates unique constraint "{constraint}"'
        self.code = "23505"
        self.details = ""
        super().__init__(self.message)


class FakeAreas:
    """El área siempre existe: la barrera de área tiene su propio test y acá sería ruido."""

    def find_by_id(self, area_id, empresa_id=None):
        return {"id": str(area_id)}

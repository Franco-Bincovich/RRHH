"""
Tests del superior (manager_id) CRUZADO ENTRE EMPRESAS — fakes, sin red.

🔴 ESTE ARCHIVO ESTÁ INVERTIDO RESPECTO DE SU VERSIÓN ORIGINAL, A PROPÓSITO.
Hasta el 2/8/2026 afirmaba lo contrario: que un manager de otra empresa se rechazaba con 404.
La decisión de producto del 2/8/2026 —UN EMPLEADO PUEDE TENER SUPERIOR DE OTRA EMPRESA DEL
GRUPO— convierte ese rechazo en el bug. Los tests no se borraron: se MOVIERON a afirmar lo
contrario, que es lo que deja la aserción con algo que mirar (regla del repo). El porqué de la
decisión y por qué sigue siendo seguro están en el docstring de `ensure_manager_valido`.

Lo que se sigue exigiendo, y es lo que estos tests cubren:
  - superior de OTRA empresa → se ACEPTA y se persiste (lo nuevo);
  - superior INEXISTENTE → sigue dando 404 MANAGER_NOT_FOUND (la validación no se borró, pasó
    a validar existencia en vez de pertenencia);
  - null → ok sin consultar nada;
  - anti-ciclos intra-empresa → siguen detectándose;
  - 🔴 anti-ciclo CRUZADO A(empresa 1)→B(empresa 2)→A → se detecta. Antes NO: el recorrido iba
    acotado por empresa, se cortaba en el primer salto de salida y respondía "no hay ciclo".

⚠️ EL FAKE HONRA empresa_id EN find_by_id, y es lo único que hace que estos tests puedan fallar.
Un fake que ignore el parámetro (como el de test_empleado_service.py, que devuelve siempre la
misma fila) los deja pasar en verde con la validación puesta o sacada — no distingue "busqué
global" de "busqué en la empresa", que es la única diferencia que este archivo mide.
Y por eso `empresas_recibidas` se afirma explícitamente: es la prueba de que el lookup viajó
SIN empresa. Sin esa aserción, el test de aceptación pasaría también con el filtro puesto y un
fake más permisivo.
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

from datetime import date
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from schemas.empleado import EmpleadoCreate, EmpleadoResponse, EmpleadoUpdate
from services.empleado_service import EmpleadoService
from utils.errors import AppError

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
EMPLEADO = UUID("11111111-1111-1111-1111-111111111111")
MGR_PROPIO = UUID("22222222-2222-2222-2222-222222222222")   # empresa A
MGR_AJENO = UUID("33333333-3333-3333-3333-333333333333")    # empresa B
MGR_INEXISTENTE = UUID("44444444-4444-4444-4444-444444444444")
INTERMEDIO = UUID("55555555-5555-5555-5555-555555555555")   # empresa A, para el ciclo indirecto


def _resp(id_: UUID, empresa_id: UUID, manager_id=None) -> EmpleadoResponse:
    return EmpleadoResponse.model_validate({
        "id": str(id_), "nombre": "N", "apellido": "A", "email_corporativo": "n@k.com",
        "empresa_id": str(empresa_id), "area_id": "22222222-2222-2222-2222-222222222222",
        "roles": ["Analista"], "modalidad_trabajo": "presencial", "tipo_contrato": "efectivo",
        "fecha_ingreso": "2024-01-01", "estado": "activo", "created_at": "2024-01-01T00:00:00Z",
        "manager_id": str(manager_id) if manager_id else None,
    })


def _create(**over) -> EmpleadoCreate:
    base = dict(nombre="N", apellido="A", email_corporativo="n@k.com",
                area_id=UUID("22222222-2222-2222-2222-222222222222"), roles=["Analista"],
                tipo_contrato="efectivo", fecha_ingreso=date(2024, 1, 1), empresa_id=EMPRESA_A)
    base.update(over)
    return EmpleadoCreate(**base)


class _Repo:
    """Repo fake que HONRA empresa_id: find_by_id devuelve None si el empleado es de otra
    empresa, igual que el _with_empresa real. Registra los empresa_id recibidos."""

    def __init__(self, extra: dict | None = None) -> None:
        self._emp = {
            str(EMPLEADO): _resp(EMPLEADO, EMPRESA_A),
            str(MGR_PROPIO): _resp(MGR_PROPIO, EMPRESA_A),
            str(MGR_AJENO): _resp(MGR_AJENO, EMPRESA_B),
        }
        self._emp.update(extra or {})
        self.guardado = None
        self.actualizado = None
        self.empresas_recibidas: list = []  # empresa_id de cada find_by_id

    def find_by_id(self, id, empresa_id=None):
        self.empresas_recibidas.append(empresa_id)
        emp = self._emp.get(str(id))
        if not emp or (empresa_id and str(emp.empresa_id) != str(empresa_id)):
            return None
        return emp

    def find_by_legajo(self, legajo, empresa_id):
        return None

    def save(self, data, empresa_id):
        self.guardado = (data, empresa_id)
        return _resp(EMPLEADO, empresa_id)

    def update(self, id, data, empresa_id=None):
        self.actualizado = (id, data)
        return _resp(EMPLEADO, EMPRESA_A, data.manager_id)

    def soft_delete(self, id, empresa_id=None):
        return True


class _Audit:
    def __init__(self) -> None:
        self.calls: list = []

    def registrar(self, **kw) -> None:
        self.calls.append(kw)


class _AreaRepoPermisivo:
    """area_repo fake permisivo: este archivo prueba el gate de MANAGER, no el de área
    (ese vive en test_empleado_area_empresa.py, con un fake que sí honra empresa_id)."""

    def find_by_id(self, id, empresa_id=None):
        return SimpleNamespace(id=str(id), empresa_id=empresa_id)


def _svc(repo) -> EmpleadoService:
    return EmpleadoService(repo=repo, audit=_Audit(), area_repo=_AreaRepoPermisivo())


def _error(fn) -> AppError:
    with pytest.raises(AppError) as exc:
        fn()
    return exc.value


# ── PUT /empleados/{id} ───────────────────────────────────────────────────────

def test_update_manager_de_otra_empresa_SE_ACEPTA_y_persiste():
    """🔴 INVERTIDO (2/8/2026). Antes: 404 y no persistía. Ahora el superior cruzado es válido.

    Para que este test pueda fallar hace falta que `ensure_manager_valido` vuelva a pasarle un
    `empresa_id` a `find_by_id`: el fake devuelve None cuando la empresa no coincide, así que
    con el filtro puesto MGR_AJENO (empresa B) no se encontraría y volvería el 404.
    """
    repo = _Repo()
    out = _svc(repo).update_empleado(
        EMPLEADO, EmpleadoUpdate(manager_id=MGR_AJENO), EMPRESA_A, "u1")
    assert str(out.manager_id) == str(MGR_AJENO)
    assert repo.actualizado is not None


def test_el_lookup_del_superior_viaja_SIN_empresa():
    """La búsqueda del superior es global. Es la aserción que distingue "acepté porque busqué
    global" de "acepté porque el fake es permisivo" — sin esto el test de arriba es vacuo."""
    repo = _Repo()
    _svc(repo).update_empleado(EMPLEADO, EmpleadoUpdate(manager_id=MGR_AJENO), EMPRESA_A, "u1")
    # Orden de los find_by_id en update: [0] validación del superior · [1] primer salto del
    # recorrido de ciclos · [-1] el `prior` que necesita el diff de auditoría.
    assert len(repo.empresas_recibidas) >= 3, "faltó un lookup: validación o ciclos desaparecieron"
    assert repo.empresas_recibidas[0] is None, \
        "el lookup del superior llevó empresa_id: la barrera volvió"
    assert repo.empresas_recibidas[1] is None, \
        "el recorrido de ciclos llevó empresa_id: un ciclo cruzado volvería a pasar"
    # 🔑 Lo que NO se aflojó: el `prior` sigue leyéndose acotado a la empresa del request. Aflojar
    # el superior no es aflojar la barrera de empresa sobre la fila que se edita.
    assert repo.empresas_recibidas[-1] == EMPRESA_A


def test_update_manager_INEXISTENTE_sigue_dando_404():
    """La validación no se borró: pasó de validar PERTENENCIA a validar EXISTENCIA.

    Es la mitad del test viejo `..._indistinguible_del_inexistente` que sigue teniendo sujeto:
    ahora hay un solo motivo de rechazo, así que no queda nada con qué compararlo."""
    repo = _Repo()
    err = _error(lambda: _svc(repo).update_empleado(
        EMPLEADO, EmpleadoUpdate(manager_id=MGR_INEXISTENTE), EMPRESA_A, "u1"))
    assert err.code == "MANAGER_NOT_FOUND" and err.status_code == 404
    assert repo.actualizado is None  # cortó antes de escribir


def test_update_manager_de_la_misma_empresa_ok():
    repo = _Repo()
    out = _svc(repo).update_empleado(
        EMPLEADO, EmpleadoUpdate(manager_id=MGR_PROPIO), EMPRESA_A, "u1")
    assert str(out.manager_id) == str(MGR_PROPIO)
    assert repo.actualizado is not None


def test_update_manager_null_no_valida_y_persiste():
    """manager_id=None = 'sin superior': el guard corta en ensure_manager_valido, no consulta."""
    repo = _Repo()
    _svc(repo).update_empleado(EMPLEADO, EmpleadoUpdate(manager_id=None), EMPRESA_A, "u1")
    assert repo.actualizado is not None
    # el único find_by_id es el `prior` del audit — ni validación de manager ni recorrido de ciclos
    assert len(repo.empresas_recibidas) == 1


def test_update_en_consolidado_sigue_funcionando():
    """empresa_id None ('Todas las empresas') en la fila que se EDITA — otro eje que el superior.

    Ya no prueba nada sobre el manager (cruzado o no, hoy se acepta igual): prueba que el camino
    consolidado del propio update sigue vivo, que es lo único que quedaba de este caso."""
    repo = _Repo()
    _svc(repo).update_empleado(EMPLEADO, EmpleadoUpdate(manager_id=MGR_AJENO), None, "u1")
    assert repo.actualizado is not None


# ── Anti-ciclos: siguen detectándose, y ahora TAMBIÉN los que cruzan empresas ─

def test_ciclo_directo_intra_empresa_sigue_rechazado():
    """A→B con B→A ya existente. El manager es válido (misma empresa): lo frena el ciclo, no la empresa."""
    repo = _Repo({str(MGR_PROPIO): _resp(MGR_PROPIO, EMPRESA_A, manager_id=EMPLEADO)})
    err = _error(lambda: _svc(repo).update_empleado(
        EMPLEADO, EmpleadoUpdate(manager_id=MGR_PROPIO), EMPRESA_A, "u1"))
    assert err.code == "MANAGER_CICLO" and err.status_code == 400
    assert repo.actualizado is None


def test_ciclo_indirecto_intra_empresa_sigue_rechazado():
    """A→B→C→A: la cadena se recorre entera y detecta el circuito."""
    repo = _Repo({
        str(MGR_PROPIO): _resp(MGR_PROPIO, EMPRESA_A, manager_id=INTERMEDIO),
        str(INTERMEDIO): _resp(INTERMEDIO, EMPRESA_A, manager_id=EMPLEADO),
    })
    err = _error(lambda: _svc(repo).update_empleado(
        EMPLEADO, EmpleadoUpdate(manager_id=MGR_PROPIO), EMPRESA_A, "u1"))
    assert err.code == "MANAGER_CICLO" and err.status_code == 400


def test_autorreferencia_sigue_rechazada():
    repo = _Repo()
    err = _error(lambda: _svc(repo).update_empleado(
        EMPLEADO, EmpleadoUpdate(manager_id=EMPLEADO), EMPRESA_A, "u1"))
    assert err.code == "MANAGER_CICLO" and err.status_code == 400


def test_ciclo_CRUZADO_entre_empresas_se_detecta():
    """🔴 EL BUG QUE ESTE COMMIT ARREGLA — invierte `..._va_acotado_a_la_empresa`.

    Cadena: EMPLEADO(A) → MGR_PROPIO(A) → INTERMEDIO(**B**) → EMPLEADO(A). Es un ciclo, y un
    ciclo entre empresas cuelga `ids_subordinados` exactamente igual que uno interno.

    Antes NO se detectaba: el recorrido consultaba `find_by_id(actual, EMPRESA_A)`, INTERMEDIO
    es de la empresa B, el fake devolvía None, y la función caía por la rama `nodo is None` →
    "no hay ciclo" → **pasaba en verde estando roto**. Para que este test vuelva a fallar
    alcanza con devolverle el `empresa_id` a la línea del `find_by_id` en el recorrido.
    """
    repo = _Repo({
        str(MGR_PROPIO): _resp(MGR_PROPIO, EMPRESA_A, manager_id=INTERMEDIO),
        str(INTERMEDIO): _resp(INTERMEDIO, EMPRESA_B, manager_id=EMPLEADO),   # ← salto a la B
    })
    err = _error(lambda: _svc(repo).update_empleado(
        EMPLEADO, EmpleadoUpdate(manager_id=MGR_PROPIO), EMPRESA_A, "u1"))
    assert err.code == "MANAGER_CICLO" and err.status_code == 400
    assert repo.actualizado is None


def test_cadena_cruzada_SIN_ciclo_no_molesta():
    """El contrapeso del anterior: que el recorrido sea global no puede volver todo un ciclo.
    EMPLEADO(A) → MGR_PROPIO(A) → INTERMEDIO(B) → (nadie). Cruza empresas y NO es circular."""
    repo = _Repo({str(MGR_PROPIO): _resp(MGR_PROPIO, EMPRESA_A, manager_id=INTERMEDIO),
                  str(INTERMEDIO): _resp(INTERMEDIO, EMPRESA_B)})
    _svc(repo).update_empleado(EMPLEADO, EmpleadoUpdate(manager_id=MGR_PROPIO), EMPRESA_A, "u1")
    assert repo.actualizado is not None


# ── POST /empleados ───────────────────────────────────────────────────────────

def test_create_manager_de_otra_empresa_SE_ACEPTA_y_guarda():
    """🔴 INVERTIDO (2/8/2026). Antes: 404 y no guardaba. Simétrico con el de update: la regla
    es del superior, no del verbo, así que alta y edición tienen que coincidir."""
    repo = _Repo()
    _svc(repo).create_empleado(_create(manager_id=MGR_AJENO), "u1", EMPRESA_A)
    assert repo.guardado is not None
    assert repo.empresas_recibidas == [None], "el lookup del superior llevó empresa_id"


def test_create_manager_INEXISTENTE_sigue_dando_404():
    """En el alta la validación también sigue viva: cambió de pertenencia a existencia."""
    repo = _Repo()
    err = _error(lambda: _svc(repo).create_empleado(
        _create(manager_id=MGR_INEXISTENTE), "u1", EMPRESA_A))
    assert err.code == "MANAGER_NOT_FOUND" and err.status_code == 404
    assert repo.guardado is None


def test_create_manager_de_la_misma_empresa_guarda():
    repo = _Repo()
    _svc(repo).create_empleado(_create(manager_id=MGR_PROPIO), "u1", EMPRESA_A)
    assert repo.guardado is not None and repo.guardado[1] == EMPRESA_A


def test_create_manager_null_no_valida_y_guarda():
    repo = _Repo()
    _svc(repo).create_empleado(_create(), "u1", EMPRESA_A)
    assert repo.guardado is not None
    assert repo.empresas_recibidas == []  # el guard cortó: ni una consulta

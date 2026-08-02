"""
El botón "resolver pendientes" — fakes, sin red.

Lo que cubre, que es lo que el botón promete:
  1. Resuelve contra el estado ACTUAL de empleados (el jefe que no existía cuando corrió el
     import, hoy existe) y BORRA de la tabla lo que resolvió.
  2. Lo que sigue sin resolverse queda, con el MOTIVO ACTUALIZADO — puede haber cambiado.
  3. 🔴 El `empresa_id` acota QUÉ pendientes se reintentan, NO dónde se busca al superior.
  4. Usa EL MISMO matcheo que el import (no una segunda implementación).

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?
  · `_PendRepo.listar` HONRA `empresa_id` (devuelve solo los de esa empresa) → si el service
    dejara de pasarlo, (3) falla en su primera mitad.
  · El índice de candidatos tiene al jefe en OTRA empresa → si el service le pasara el
    `empresa_id` al matcheo "por consistencia", (3) falla en su segunda mitad, que es la que
    importa: acotar la búsqueda dejaría sin resolver justo los superiores cruzados.
  · `_PendRepo` registra upserts y borrados por separado → (1) y (2) no se pueden confundir.
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

import hashlib
from types import SimpleNamespace
from uuid import UUID, uuid4

from services.superiores_pendientes_service import SuperioresPendientesService

EMPRESA_A, EMPRESA_B = str(uuid4()), str(uuid4())


def _uid(nombre: str) -> str:
    """id determinístico y válido como UUID (el cast a UUID existe en el camino de escritura)."""
    return str(UUID(hashlib.md5(nombre.encode()).hexdigest()))


def _pendiente(empleado: str, apellido_sup: str, nombre_sup=None, empresa=EMPRESA_A,
               motivo="no hay ningún empleado cargado con ese nombre") -> dict:
    """Una fila de `empleado_superior_pendiente` tal como la devuelve el repo (con el embed)."""
    return {"empleado_id": _uid(empleado), "empresa_id": empresa,
            "apellido_csv": apellido_sup, "nombre_csv": nombre_sup, "motivo": motivo,
            "empleados": {"nombre": "Nom", "apellido": empleado.upper()}}


class _PendRepo:
    """Repo de pendientes fake. HONRA empresa_id en `listar` — sin eso, (3) no puede fallar."""

    def __init__(self, filas: list) -> None:
        self._filas = filas
        self.guardados: list = []
        self.borrados: list = []

    def listar(self, empresa_id=None):
        if not empresa_id:
            return list(self._filas)
        return [f for f in self._filas if str(f["empresa_id"]) == str(empresa_id)]

    def upsert_muchos(self, filas):
        self.guardados = list(filas)
        return len(filas)

    def borrar_muchos(self, ids):
        self.borrados = list(ids)
        return len(ids)


class _EmpRepo:
    """EmpleadoRepo fake. Guarda los manager_id escritos; sin managers previos no hay ciclos."""

    def __init__(self) -> None:
        self.escritos: dict = {}

    def find_by_id(self, id, empresa_id=None):
        return SimpleNamespace(id=str(id), manager_id=None, empresa_id=EMPRESA_A)

    def update(self, id, data, empresa_id=None):
        self.escritos[str(id)] = str(data.manager_id)
        return SimpleNamespace(id=str(id))


class _Indice:
    def __init__(self, filas: list) -> None:
        self._filas = filas
        self.llamadas = 0

    def __call__(self):
        self.llamadas += 1
        return list(self._filas)


def _emp(id_: str, apellido: str, nombre: str, empresa: str = EMPRESA_A) -> dict:
    return {"id": _uid(id_), "apellido": apellido, "nombre": nombre, "empresa_id": empresa}


def _armar(monkeypatch, *, pendientes: list, index_rows: list):
    import services._superiores_matcher as core

    indice = _Indice(index_rows)
    monkeypatch.setattr(core, "indice_por_nombre", indice)
    pend, emp = _PendRepo(pendientes), _EmpRepo()
    return SuperioresPendientesService(repo=pend, empleado_repo=emp), pend, emp, indice


# ── 1. Resuelve contra el estado ACTUAL y limpia ──────────────────────────────

def test_el_jefe_que_ANTES_no_existia_ahora_se_resuelve(monkeypatch) -> None:
    """El escenario completo: el import dejó el pendiente porque el jefe no estaba cargado.
    RRHH lo da de alta. El botón lo resuelve sin volver a tocar el CSV."""
    svc, pend, emp, _ = _armar(
        monkeypatch,
        pendientes=[_pendiente("sub", "LIBERTELLI", "JUAN")],
        index_rows=[_emp("jefe", "LIBERTELLI", "JUAN"), _emp("sub", "SUB", "Nom")])

    out = svc.resolver()
    assert out.resueltos == 1 and out.pendientes == []
    assert emp.escritos == {_uid("sub"): _uid("jefe")}
    assert pend.borrados == [_uid("sub")]      # se limpió: ya no es pendiente
    assert pend.guardados == []


def test_sin_pendientes_no_toca_nada(monkeypatch) -> None:
    """Estado sano: la tabla vacía. Ni una query de índice, ni un upsert."""
    svc, pend, emp, indice = _armar(monkeypatch, pendientes=[], index_rows=[])
    out = svc.resolver()
    assert (out.resueltos, out.pendientes) == (0, [])
    assert indice.llamadas == 0 and pend.borrados == [] and emp.escritos == {}


# ── 2. Lo que sigue pendiente conserva la fila, con el motivo de AHORA ────────

def test_el_motivo_se_ACTUALIZA_si_cambio(monkeypatch) -> None:
    """🔴 El pendiente decía "no hay ningún empleado con ese nombre". Desde entonces se dieron de
    alta DOS homónimos, así que ahora el motivo real es otro. Sin este refresco, la pantalla
    mostraría para siempre el motivo del día del import, que dejó de ser cierto."""
    svc, pend, emp, _ = _armar(
        monkeypatch,
        pendientes=[_pendiente("sub", "GOMEZ", "ANA")],
        index_rows=[_emp("j1", "GOMEZ", "ANA"), _emp("j2", "GOMEZ", "ANA")])

    out = svc.resolver()
    assert out.resueltos == 0 and emp.escritos == {}
    assert len(out.pendientes) == 1 and "2 empleados" in out.pendientes[0].motivo
    assert pend.guardados[0]["motivo"] == out.pendientes[0].motivo
    assert pend.guardados[0]["apellido_csv"] == "GOMEZ"    # el nombre crudo no se pierde


def test_el_pendiente_reporta_a_quien_le_falta_el_jefe(monkeypatch) -> None:
    """La UI necesita 'de quiénes': el nombre del empleado sale del embed, no duplicado."""
    svc, _, _, _ = _armar(monkeypatch, pendientes=[_pendiente("sub", "FANTASMA")],
                          index_rows=[_emp("otro", "OTRO", "X")])
    out = svc.resolver()
    assert out.pendientes[0].empleado == "SUB, Nom"
    assert out.pendientes[0].superior == "FANTASMA"


# ── 3. 🔴 empresa_id acota QUÉ se reintenta, NO dónde se busca ────────────────

def test_la_empresa_acota_los_pendientes_a_reintentar(monkeypatch) -> None:
    svc, _, emp, _ = _armar(
        monkeypatch,
        pendientes=[_pendiente("sub_a", "JEFE", "J", empresa=EMPRESA_A),
                    _pendiente("sub_b", "JEFE", "J", empresa=EMPRESA_B)],
        index_rows=[_emp("jefe", "JEFE", "J")])

    out = svc.resolver(UUID(EMPRESA_A))
    assert out.resueltos == 1
    assert set(emp.escritos) == {_uid("sub_a")}, "se reintentó un pendiente de otra empresa"


def test_la_empresa_NO_acota_donde_se_busca_al_superior(monkeypatch) -> None:
    """🔴 El pendiente es de un empleado de la empresa A y su jefe está cargado en la B. Si el
    service le pasara el `empresa_id` al matcheo "por consistencia", esto devolvería
    'no hay ningún empleado con ese nombre' — sin error y sin aviso, justo en el caso cruzado
    que motivó todo el cambio."""
    svc, _, emp, _ = _armar(
        monkeypatch,
        pendientes=[_pendiente("sub", "JEFE", "J", empresa=EMPRESA_A)],
        index_rows=[_emp("jefe", "JEFE", "J", EMPRESA_B)])

    out = svc.resolver(UUID(EMPRESA_A))
    assert out.resueltos == 1 and emp.escritos == {_uid("sub"): _uid("jefe")}


# ── 4. Listado ────────────────────────────────────────────────────────────────

def test_el_listado_dice_cuantos_y_de_quienes(monkeypatch) -> None:
    svc, _, _, _ = _armar(monkeypatch,
                          pendientes=[_pendiente("uno", "A"), _pendiente("dos", "B")],
                          index_rows=[])
    out = svc.listar()
    assert out.total == 2
    assert [i.empleado for i in out.items] == ["UNO, Nom", "DOS, Nom"]


def test_el_listado_respeta_el_selector_de_empresa(monkeypatch) -> None:
    """Es una VISTA (filtra lo que se mira), a diferencia de la acción de resolver."""
    svc, _, _, _ = _armar(monkeypatch,
                          pendientes=[_pendiente("uno", "A", empresa=EMPRESA_A),
                                      _pendiente("dos", "B", empresa=EMPRESA_B)],
                          index_rows=[])
    assert svc.listar(UUID(EMPRESA_B)).total == 1
    assert svc.listar().total == 2      # consolidado: las dos


# ── 4b. Es EL MISMO matcheo que el import ─────────────────────────────────────

def test_usa_el_matcheo_compartido_no_uno_propio(monkeypatch) -> None:
    """Si el service tuviera su propia resolución, parchear `_superiores_matcher.resolver` no lo
    afectaría — y botón e import podrían dar veredictos distintos sobre los mismos datos."""
    import services._superiores_matcher as core

    llamado: list = []
    monkeypatch.setattr(core, "resolver", lambda anotados, repo: (llamado.append(anotados), ([], []))[1])
    svc, _, _, _ = _armar(monkeypatch, pendientes=[_pendiente("sub", "X")], index_rows=[])
    svc.resolver()
    assert len(llamado) == 1 and llamado[0][0]["apellido_csv"] == "X"

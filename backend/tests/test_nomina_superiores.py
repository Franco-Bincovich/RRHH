"""
Resolución de "Apellido Superior" + "Nombre Superior" → `manager_id` en el import — sin red.

El problema que cubren: el CSV trae las dos columnas en las 19 filas y el import las leía y las
TIRABA (`manager_id` 0/19 en producción). Sin ese campo, un `mandos_medios` no ve absolutamente
nada: su ownership se resuelve por `manager_id`.

  1. 🔴 EL ORDEN NO IMPORTA — el jefe en la ÚLTIMA fila y sus subordinados antes.
  2. Los tres estados: resuelto · ambiguo (homónimos) · sin_candidato. Cero fuzzy.
  3. 🔴 Un import CORTADO por presupuesto no resuelve superiores de filas no procesadas.
  4. Ciclos: se chequean en la segunda pasada, también los que cruzan empresas.
  5. El índice se trae en UNA query, no una por fila.
  6. El superior se busca en TODAS las empresas — incluso en una que no tiene ni una fila en el
     archivo que se está importando.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?
  · `_Indice` cuenta sus invocaciones → si el resolver volviera a consultar por fila, (5) falla.
  · Los empleados del índice están en DOS EMPRESAS y el jefe del cruzado está en la otra → si
    `indice_por_nombre` volviera a acotarse por empresa, (6) falla. Un índice de una sola empresa
    no podría desmentir nada. (Este punto no es teórico: el test de (6) encontró un recorte real
    en la primera versión del código — ver su docstring.)
  · `_Repo.update` GUARDA lo que recibe (no devuelve un objeto prefabricado) → si el resolver
    escribiera el manager equivocado, las aserciones sobre `escritos` lo verían.
  · `_Repo.find_by_id` refleja los `manager_id` ya escritos EN ESTA pasada → sin eso, el test de
    ciclos entre dos filas del mismo archivo no podría fallar.
  · Los ids son UUID DE VERDAD (`_uid`), no strings inventados: `EmpleadoUpdate.manager_id` es
    `UUID`, así que un fake con ids tipo "jefe" probaría un mundo donde ese cast no existe — y
    de hecho lo escondió: la primera versión de este archivo daba "error inesperado" en todo.
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

import pytest

EMPRESA_A, EMPRESA_B = str(uuid4()), str(uuid4())

_NOMBRES: dict = {}   # uuid → nombre corto, para leer las aserciones


def _uid(nombre: str) -> str:
    """id determinístico y VÁLIDO como UUID, a partir de un nombre corto legible."""
    u = str(UUID(hashlib.md5(nombre.encode()).hexdigest()))
    _NOMBRES[u] = nombre
    return u


def _cortos(escritos: dict) -> dict:
    """Traduce {uuid: uuid} a {nombre: nombre} para que las aserciones se lean."""
    return {_NOMBRES[k]: _NOMBRES[v] for k, v in escritos.items()}


def _fila(apellido: str, nombre: str, sup_ap=None, sup_no=None) -> dict:
    """Una fila ya parseada, con lo que `registrar` mira."""
    return {"apellido": apellido, "nombre": nombre,
            "_superior_apellido": sup_ap, "_superior_nombre": sup_no}


class _Repo:
    """Fake de EmpleadoRepo. GUARDA los updates y los REFLEJA en find_by_id.

    Reflejarlos no es un lujo: `ensure_no_ciclo_manager` consulta la base en cada salto, así que
    sin esto el recorrido nunca vería los `manager_id` que la propia pasada acaba de escribir y
    un ciclo entre dos filas del mismo archivo se colaría."""

    def __init__(self, empleados: dict) -> None:
        # id → {"manager_id": ..., "empresa_id": ...}
        self._emp = {k: dict(v) for k, v in empleados.items()}
        self.escritos: dict = {}          # id → manager_id escrito
        self.empresas_recibidas: list = []

    def find_by_id(self, id, empresa_id=None):
        self.empresas_recibidas.append(empresa_id)
        e = self._emp.get(str(id))
        if not e or (empresa_id and str(e["empresa_id"]) != str(empresa_id)):
            return None
        return SimpleNamespace(id=str(id), manager_id=e["manager_id"],
                               empresa_id=e["empresa_id"])

    def update(self, id, data, empresa_id=None):
        mgr = str(data.manager_id) if data.manager_id else None
        self.escritos[str(id)] = mgr
        self._emp[str(id)]["manager_id"] = mgr     # ← se refleja para el próximo chequeo de ciclos
        return SimpleNamespace(id=str(id))


class _Pendientes:
    """Fake del repo de pendientes. Registra lo que se persiste y lo que se limpia.

    Es lo que hace verificable la parte de "no se pierde el nombre del jefe": sin este doble,
    `_persistir` correría contra la base real y el test no podría afirmar nada sobre ella."""

    def __init__(self) -> None:
        self.guardados: list = []
        self.borrados: list = []

    def upsert_muchos(self, filas):
        self.guardados = list(filas)
        return len(filas)

    def borrar_muchos(self, ids):
        self.borrados = list(ids)
        return len(ids)


class _Indice:
    """Reemplaza a `indice_por_nombre`. Cuenta invocaciones (para probar que es UNA sola)."""

    def __init__(self, filas: list) -> None:
        self._filas = filas
        self.llamadas = 0

    def __call__(self):
        """Sin argumentos: el índice real NO acota por empresa (ver `indice_por_nombre`)."""
        self.llamadas += 1
        return list(self._filas)


def _emp(id_: str, apellido: str, nombre: str, empresa: str = EMPRESA_A) -> dict:
    """Fila del índice de candidatos. El id se convierte a UUID real acá adentro."""
    return {"id": _uid(id_), "apellido": apellido, "nombre": nombre, "empresa_id": empresa}


def _armar(monkeypatch, *, index_rows: list, empleados: dict):
    """NominaSuperiores con el repo, el índice y el repo de pendientes falsos ya inyectados.

    El índice se parchea en `_superiores_matcher` —donde vive el matcheo compartido con el botón
    "resolver pendientes"—, no en `_nomina_superiores`, que solo lo engancha."""
    import services._nomina_superiores as mod
    import services._superiores_matcher as core

    indice = _Indice(index_rows)
    monkeypatch.setattr(core, "indice_por_nombre", indice)
    repo = _Repo({_uid(k): v for k, v in empleados.items()})
    pend = _Pendientes()
    sup = mod.NominaSuperiores(repo=repo, pendientes_repo=pend)
    sup.pendientes_repo = pend          # atajo para las aserciones
    return sup, repo, indice


# ── 1. 🔴 EL ORDEN NO IMPORTA ─────────────────────────────────────────────────

class TestElOrdenDeLasFilasNoImporta:
    """El caso del archivo real: Libertelli tiene 13 subordinados y está en la fila 11, o sea
    que 10 de ellos se procesan ANTES que él. Acá se lleva al extremo: el jefe en la ÚLTIMA fila.

    Para que estos tests fallen alcanza con resolver dentro del loop en vez de en la segunda
    pasada: los subordinados anteriores al jefe quedarían sin `manager_id`."""

    def test_el_jefe_en_la_ultima_fila_igual_se_asigna_a_todos(self, monkeypatch) -> None:
        sup, repo, _ = _armar(
            monkeypatch,
            index_rows=[_emp("jefe", "LIBERTELLI", "JUAN"), _emp("s1", "A", "A"),
                        _emp("s2", "B", "B"), _emp("s3", "C", "C")],
            empleados={i: {"manager_id": None, "empresa_id": EMPRESA_A}
                       for i in ("jefe", "s1", "s2", "s3")})
        # filas 2, 3 y 4: subordinados. fila 5: el jefe (último).
        for i, sid in enumerate(("s1", "s2", "s3")):
            sup.registrar(i + 2, _uid(sid), EMPRESA_A,
                          _fila(chr(65 + i), chr(65 + i), "LIBERTELLI", "JUAN"))
        sup.registrar(5, _uid("jefe"), EMPRESA_A, _fila("LIBERTELLI", "JUAN"))

        resueltos, pendientes = sup.resolver()
        assert (resueltos, pendientes) == (3, [])
        assert _cortos(repo.escritos) == {"s1": "jefe", "s2": "jefe", "s3": "jefe"}

    def test_una_fila_sin_superior_no_es_un_pendiente(self, monkeypatch) -> None:
        """"Sin jefe" no es "no lo encontramos": no se anota y no ensucia el reporte."""
        sup, repo, _ = _armar(monkeypatch, index_rows=[_emp("jefe", "L", "J")],
                              empleados={"jefe": {"manager_id": None, "empresa_id": EMPRESA_A}})
        sup.registrar(2, _uid("jefe"), EMPRESA_A, _fila("L", "J"))
        assert sup.resolver() == (0, [])
        assert _cortos(repo.escritos) == {}


# ── 2. Los tres estados, sin fuzzy ────────────────────────────────────────────

class TestLosTresEstados:
    def test_resuelto_escribe_el_manager(self, monkeypatch) -> None:
        sup, repo, _ = _armar(monkeypatch, index_rows=[_emp("j", "GOMEZ", "ANA"), _emp("s", "P", "L")],
                              empleados={"j": {"manager_id": None, "empresa_id": EMPRESA_A},
                                         "s": {"manager_id": None, "empresa_id": EMPRESA_A}})
        sup.registrar(2, _uid("s"), EMPRESA_A, _fila("P", "L", "GOMEZ", "ANA"))
        assert sup.resolver() == (1, [])
        assert _cortos(repo.escritos) == {"s": "j"}

    def test_normaliza_acentos_mayusculas_y_espacios(self, monkeypatch) -> None:
        """Se reusa `clave_identidad` del import de evaluaciones: 'Gómez  Ana' == 'GOMEZ ANA'."""
        sup, repo, _ = _armar(monkeypatch, index_rows=[_emp("j", "Gómez", "Ana"), _emp("s", "P", "L")],
                              empleados={"j": {"manager_id": None, "empresa_id": EMPRESA_A},
                                         "s": {"manager_id": None, "empresa_id": EMPRESA_A}})
        sup.registrar(2, _uid("s"), EMPRESA_A, _fila("P", "L", "  GOMEZ ", "ANA"))
        assert sup.resolver()[0] == 1

    def test_ambiguo_NO_elige_y_reporta_el_pendiente(self, monkeypatch) -> None:
        """Dos homónimos → no se adivina. Es la regla de evaluaciones: un apellido parecido le
        daría el equipo de otra persona a un mando medio, en lectura Y escritura."""
        sup, repo, _ = _armar(
            monkeypatch,
            index_rows=[_emp("j1", "GOMEZ", "ANA"), _emp("j2", "GOMEZ", "ANA"), _emp("s", "P", "L")],
            empleados={i: {"manager_id": None, "empresa_id": EMPRESA_A} for i in ("j1", "j2", "s")})
        sup.registrar(7, _uid("s"), EMPRESA_A, _fila("Perez", "Luis", "GOMEZ", "ANA"))

        resueltos, pendientes = sup.resolver()
        assert (resueltos, _cortos(repo.escritos)) == (0, {})
        assert len(pendientes) == 1
        assert pendientes[0].fila == 7 and pendientes[0].empleado == "Perez, Luis"
        assert pendientes[0].superior == "GOMEZ, ANA"
        assert "2 empleados" in pendientes[0].motivo

    def test_sin_candidato_reporta_el_pendiente_con_el_texto_crudo(self, monkeypatch) -> None:
        """El caso más común hoy: 5 de los 6 jefes del archivo real no están cargados.
        🔴 El nombre del jefe SOBREVIVE en el pendiente — es el insumo del botón de resolver."""
        sup, repo, _ = _armar(monkeypatch, index_rows=[_emp("s", "P", "L")],
                              empleados={"s": {"manager_id": None, "empresa_id": EMPRESA_A}})
        sup.registrar(4, _uid("s"), EMPRESA_A, _fila("Perez", "Luis", "FANTASMA", "PEDRO"))

        resueltos, pendientes = sup.resolver()
        assert (resueltos, _cortos(repo.escritos)) == (0, {})
        assert pendientes[0].superior == "FANTASMA, PEDRO"
        assert "ningún colaborador" in pendientes[0].motivo

    def test_no_hay_matcheo_por_similitud(self, monkeypatch) -> None:
        """'GOMES' no matchea 'GOMEZ'. Si algún día alguien mete fuzzy, este test lo frena."""
        sup, repo, _ = _armar(monkeypatch, index_rows=[_emp("j", "GOMEZ", "ANA"), _emp("s", "P", "L")],
                              empleados={i: {"manager_id": None, "empresa_id": EMPRESA_A}
                                         for i in ("j", "s")})
        sup.registrar(2, _uid("s"), EMPRESA_A, _fila("P", "L", "GOMES", "ANA"))
        assert sup.resolver()[0] == 0 and _cortos(repo.escritos) == {}


# ── 3. 🔴 El corte por presupuesto ────────────────────────────────────────────

def test_solo_se_resuelven_las_filas_efectivamente_procesadas(monkeypatch) -> None:
    """Si el presupuesto corta el import a la mitad, las filas no procesadas nunca se
    registraron: resolverles el superior sería escribir sobre datos que no entraron.

    Se modela igual que el corte real: `registrar` solo se llama desde `_procesar_fila`, o sea
    únicamente para filas escritas. Acá se registran 2 de 4 y se verifica que las otras 2 no
    aparecen ni como resueltas ni como pendientes — no existen para esta pasada."""
    sup, repo, _ = _armar(
        monkeypatch,
        index_rows=[_emp("j", "JEFE", "J")] + [_emp(f"s{i}", "S", str(i)) for i in range(4)],
        empleados={"j": {"manager_id": None, "empresa_id": EMPRESA_A},
                   **{f"s{i}": {"manager_id": None, "empresa_id": EMPRESA_A} for i in range(4)}})
    for i in range(2):                      # solo las dos primeras se procesaron
        sup.registrar(i + 2, _uid(f"s{i}"), EMPRESA_A, _fila("S", str(i), "JEFE", "J"))

    resueltos, pendientes = sup.resolver()
    assert (resueltos, pendientes) == (2, [])
    assert set(_cortos(repo.escritos)) == {"s0", "s1"}, "se tocó una fila que el import no llegó a procesar"


def test_sin_filas_registradas_no_consulta_nada(monkeypatch) -> None:
    """Un archivo con headers inválidos, o cortado en la fila 1, no debe pagar ni una query."""
    sup, repo, indice = _armar(monkeypatch, index_rows=[], empleados={})
    assert sup.resolver() == (0, [])
    assert indice.llamadas == 0 and _cortos(repo.escritos) == {}


# ── 4. Ciclos, también los que cruzan empresas ────────────────────────────────

class TestCiclos:
    def test_la_autorreferencia_queda_pendiente_no_escrita(self, monkeypatch) -> None:
        """Una fila cuyo "superior" es ella misma (mismo nombre) no puede apuntarse a sí misma."""
        sup, repo, _ = _armar(monkeypatch, index_rows=[_emp("s", "PEREZ", "ANA")],
                              empleados={"s": {"manager_id": None, "empresa_id": EMPRESA_A}})
        sup.registrar(2, _uid("s"), EMPRESA_A, _fila("PEREZ", "ANA", "PEREZ", "ANA"))

        resueltos, pendientes = sup.resolver()
        assert (resueltos, _cortos(repo.escritos)) == (0, {})
        assert "circular" in pendientes[0].motivo

    def test_un_ciclo_CRUZADO_entre_empresas_se_detecta(self, monkeypatch) -> None:
        """🔴 A(empresa A) → B(empresa B) → A. Con el recorrido acotado por empresa —como estaba
        antes del 2/8/2026— el salto a la empresa B devolvía None y esto se escribía igual,
        dejando el organigrama colgado. Ver `ensure_no_ciclo_manager`."""
        sup, repo, _ = _armar(
            monkeypatch,
            index_rows=[_emp("b", "BEE", "B", EMPRESA_B), _emp("a", "AYE", "A", EMPRESA_A)],
            empleados={"a": {"manager_id": None, "empresa_id": EMPRESA_A},
                       "b": {"manager_id": _uid("a"), "empresa_id": EMPRESA_B}})  # B ya reporta a A
        sup.registrar(2, _uid("a"), EMPRESA_A, _fila("AYE", "A", "BEE", "B"))     # ...y A pediría a B

        resueltos, pendientes = sup.resolver()
        assert (resueltos, _cortos(repo.escritos)) == (0, {})
        assert "circular" in pendientes[0].motivo

    def test_un_ciclo_entre_dos_filas_del_MISMO_archivo_se_detecta(self, monkeypatch) -> None:
        """El primero se escribe; el segundo cerraría el circuito y queda pendiente. Exige que el
        chequeo vea lo que esta misma pasada ya escribió — por eso corre antes de CADA escritura."""
        sup, repo, _ = _armar(
            monkeypatch, index_rows=[_emp("x", "EQUIS", "X"), _emp("y", "YE", "Y")],
            empleados={"x": {"manager_id": None, "empresa_id": EMPRESA_A},
                       "y": {"manager_id": None, "empresa_id": EMPRESA_A}})
        sup.registrar(2, _uid("x"), EMPRESA_A, _fila("EQUIS", "X", "YE", "Y"))   # X → Y
        sup.registrar(3, _uid("y"), EMPRESA_A, _fila("YE", "Y", "EQUIS", "X"))   # Y → X (ciclo)

        resueltos, pendientes = sup.resolver()
        assert resueltos == 1 and len(pendientes) == 1
        assert _cortos(repo.escritos) == {"x": "y"}


# ── 5 y 6. Una sola query, y el scope del índice ──────────────────────────────

class TestElIndice:
    def test_se_trae_en_UNA_sola_query(self, monkeypatch) -> None:
        """Diez filas, una query. Si el resolver consultara por fila, `llamadas` daría 10."""
        sup, _, indice = _armar(
            monkeypatch,
            index_rows=[_emp("j", "JEFE", "J")] + [_emp(f"s{i}", "S", str(i)) for i in range(10)],
            empleados={"j": {"manager_id": None, "empresa_id": EMPRESA_A},
                       **{f"s{i}": {"manager_id": None, "empresa_id": EMPRESA_A} for i in range(10)}})
        for i in range(10):
            sup.registrar(i + 2, _uid(f"s{i}"), EMPRESA_A, _fila("S", str(i), "JEFE", "J"))
        sup.resolver()
        assert indice.llamadas == 1

    def test_el_jefe_puede_estar_en_OTRA_empresa(self, monkeypatch) -> None:
        """🔴 El caso que motivó todo: el subordinado es de A y su jefe de B. Acotar el índice a
        la empresa del empleado dejaría sin resolver justamente los superiores cruzados."""
        sup, repo, _ = _armar(
            monkeypatch, index_rows=[_emp("j", "JEFE", "J", EMPRESA_B), _emp("s", "SUB", "S", EMPRESA_A)],
            empleados={"j": {"manager_id": None, "empresa_id": EMPRESA_B},
                       "s": {"manager_id": None, "empresa_id": EMPRESA_A}})
        sup.registrar(2, _uid("s"), EMPRESA_A, _fila("SUB", "S", "JEFE", "J"))
        sup.registrar(3, _uid("j"), EMPRESA_B, _fila("JEFE", "J"))   # el jefe también viene en el archivo

        assert sup.resolver() == (1, [])
        assert _cortos(repo.escritos) == {"s": "j"}

    def test_el_jefe_puede_estar_en_una_empresa_SIN_NINGUNA_FILA_en_el_archivo(self, monkeypatch) -> None:
        """🔴 EL CASO QUE OBLIGÓ A NO ACOTAR EL ÍNDICE POR EMPRESA, y lo descubrió este test.

        Se importa la nómina de la empresa A —ninguna fila de la B— y el superior está cargado en
        la B. La primera versión acotaba el índice a "las empresas presentes en el archivo", que
        suena razonable: acá habría pedido solo la A, no habría encontrado al jefe, y habría
        reportado "no hay ningún colaborador con ese nombre". Sin error, sin aviso, y justo en el caso
        cruzado que motivó todo el cambio. Ver `indice_por_nombre`.

        Para que este test falle alcanza con volver a pasarle un scope de empresas al índice."""
        sup, repo, _ = _armar(
            monkeypatch, index_rows=[_emp("j", "JEFE", "J", EMPRESA_B), _emp("s", "SUB", "S", EMPRESA_A)],
            empleados={"j": {"manager_id": None, "empresa_id": EMPRESA_B},
                       "s": {"manager_id": None, "empresa_id": EMPRESA_A}})
        sup.registrar(2, _uid("s"), EMPRESA_A, _fila("SUB", "S", "JEFE", "J"))  # solo filas de A

        assert sup.resolver() == (1, [])
        assert _cortos(repo.escritos) == {"s": "j"}


# ── El UPDATE lleva la empresa DEL EMPLEADO ───────────────────────────────────

def test_el_update_usa_la_empresa_del_empleado(monkeypatch) -> None:
    """Vista vs Acción: la empresa del WHERE sale del empleado que el import acaba de escribir,
    no de un header. El de la empresa B se actualiza con la B, aunque su jefe sea de la A."""
    import services._nomina_superiores as mod

    capturado: list = []
    import services._superiores_matcher as core
    indice = _Indice([_emp("j", "JEFE", "J", EMPRESA_A), _emp("s", "SUB", "S", EMPRESA_B)])
    monkeypatch.setattr(core, "indice_por_nombre", indice)

    class _RepoEspia(_Repo):
        def update(self, id, data, empresa_id=None):
            capturado.append((str(id), str(empresa_id)))
            return super().update(id, data, empresa_id)

    repo = _RepoEspia({_uid("j"): {"manager_id": None, "empresa_id": EMPRESA_A},
                       _uid("s"): {"manager_id": None, "empresa_id": EMPRESA_B}})
    sup = mod.NominaSuperiores(repo=repo, pendientes_repo=_Pendientes())
    sup.registrar(2, _uid("s"), EMPRESA_B, _fila("SUB", "S", "JEFE", "J"))
    sup.resolver()
    assert capturado == [(_uid("s"), EMPRESA_B)]


@pytest.mark.parametrize("motivo_error", ["boom", "otra cosa"])
def test_un_fallo_de_escritura_no_tumba_las_demas_filas(monkeypatch, motivo_error: str) -> None:
    """Best-effort por fila, como el resto de los colaboradores del import: los empleados ya
    están cargados, y perder un `manager_id` es recuperable con el botón de pendientes; perder
    el resto del lote, no."""
    import services._nomina_superiores as mod

    import services._superiores_matcher as core
    indice = _Indice([_emp("j", "JEFE", "J"), _emp("s1", "S", "1"), _emp("s2", "S", "2")])
    monkeypatch.setattr(core, "indice_por_nombre", indice)

    class _RepoRoto(_Repo):
        def update(self, id, data, empresa_id=None):
            if str(id) == _uid("s1"):
                raise RuntimeError(motivo_error)
            return super().update(id, data, empresa_id)

    repo = _RepoRoto({_uid(i): {"manager_id": None, "empresa_id": EMPRESA_A}
                      for i in ("j", "s1", "s2")})
    sup = mod.NominaSuperiores(repo=repo, pendientes_repo=_Pendientes())
    sup.registrar(2, _uid("s1"), EMPRESA_A, _fila("S", "1", "JEFE", "J"))
    sup.registrar(3, _uid("s2"), EMPRESA_A, _fila("S", "2", "JEFE", "J"))

    resueltos, pendientes = sup.resolver()
    assert (resueltos, _cortos(repo.escritos)) == (1, {"s2": "j"})
    assert len(pendientes) == 1 and pendientes[0].fila == 2


# ── La persistencia de pendientes (migración 086) ─────────────────────────────

class TestLosPendientesSePersisten:
    """El nombre del jefe SOBREVIVE al request. Es lo que hace posible el botón de resolver:
    5 de los 6 jefes del archivo real no están cargados, y sin esto la única forma de reintentar
    sería volver a subir el CSV — que RRHH no necesariamente tiene a mano meses después."""

    def test_el_pendiente_se_guarda_con_el_nombre_crudo_del_csv(self, monkeypatch) -> None:
        sup, _, _ = _armar(monkeypatch, index_rows=[_emp("s", "SUB", "S")],
                           empleados={"s": {"manager_id": None, "empresa_id": EMPRESA_A}})
        sup.registrar(2, _uid("s"), EMPRESA_A, _fila("SUB", "S", "FANTASMA", "PEDRO"))
        sup.resolver()

        assert sup.pendientes_repo.guardados == [{
            "empleado_id": _uid("s"), "empresa_id": EMPRESA_A,
            "apellido_csv": "FANTASMA", "nombre_csv": "PEDRO",
            "motivo": "no hay ningún colaborador cargado con ese nombre",
        }]

    def test_un_resuelto_se_BORRA_de_los_pendientes(self, monkeypatch) -> None:
        """🔴 Tan importante como guardar: un empleado que quedó pendiente en un import anterior
        y AHORA se resolvió tiene que salir de la tabla, o el botón lo ofrecería para siempre."""
        sup, _, _ = _armar(monkeypatch, index_rows=[_emp("j", "JEFE", "J"), _emp("s", "SUB", "S")],
                           empleados={i: {"manager_id": None, "empresa_id": EMPRESA_A}
                                      for i in ("j", "s")})
        sup.registrar(2, _uid("s"), EMPRESA_A, _fila("SUB", "S", "JEFE", "J"))
        sup.resolver()

        assert sup.pendientes_repo.borrados == [_uid("s")]
        assert sup.pendientes_repo.guardados == []

    def test_si_la_persistencia_falla_el_import_NO_se_cae(self, monkeypatch) -> None:
        """Best-effort: los empleados ya están cargados y los manager_id escritos. Lo único que
        se pierde es poder resolverlos después sin re-subir el archivo — no justifica un 500."""
        import services._nomina_superiores as mod
        import services._superiores_matcher as core

        monkeypatch.setattr(core, "indice_por_nombre",
                            _Indice([_emp("j", "JEFE", "J"), _emp("s", "SUB", "S")]))

        class _RepoRoto:
            def upsert_muchos(self, filas):
                raise RuntimeError("la tabla no existe todavía")

            def borrar_muchos(self, ids):
                raise RuntimeError("la tabla no existe todavía")

        repo = _Repo({_uid(i): {"manager_id": None, "empresa_id": EMPRESA_A} for i in ("j", "s")})
        sup = mod.NominaSuperiores(repo=repo, pendientes_repo=_RepoRoto())
        sup.registrar(2, _uid("s"), EMPRESA_A, _fila("SUB", "S", "JEFE", "J"))

        assert sup.resolver() == (1, [])          # el manager_id igual se escribió
        assert _cortos(repo.escritos) == {"s": "j"}

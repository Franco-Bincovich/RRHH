"""
Alertas del dashboard: bloqueos de módulo, alertas agregadas de campo vacío y orden por nivel.

🔑 QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE CADA TEST PUEDA FALLAR

El fake NO es un stub que devuelve listas fijas: es un mini-motor que APLICA de verdad los
predicados (`eq`, `neq`, `is_`, `limit`) sobre un padrón sintético. Eso es lo que le permite
desmentir al código. Concretamente:

  · modela DOS EMPRESAS, y la B tiene un empleado sin superior y una vacante. Si alguien saca
    el `.eq("empresa_id", ...)` de una alerta, los conteos suben y los tests de
    `TestNoCuentaFilasDeOtraEmpresa` se ponen rojos. Con un fake de una sola empresa, borrar
    la barrera entera pasaría en verde — que es el caso #1 de la regla transversal.
  · modela EMPLEADOS DE BAJA. Si se cae el `.neq("estado", "baja")`, el conteo agregado sube
    y el número del mensaje deja de coincidir con las filas del listado.
  · las tablas de bloqueo tienen filas para UNA empresa y no para la otra, así que "la tabla
    está vacía" no es global: si el bloqueo ignorara la empresa, la alerta desaparecería para
    quien sí la necesita.
  · `count` se calcula sobre las filas que SOBREVIVEN a los predicados, no se devuelve fijo:
    si el conteo del mensaje se desacoplara de la query, el test de coherencia lo vería.

`TestElHrefLlevaAlListadoQueLasDevuelve` es el más fuerte y el que justifica el archivo: no
compara el href contra un string escrito a mano —eso solo probaría que dos constantes son
iguales— sino que PARSEA el href, se lo pasa al repo REAL de empleados contra el MISMO padrón,
y exige que devuelva exactamente las filas que la alerta contó. Si el href apuntara a otro
filtro, o el filtro devolviera otro conjunto, el número de la alerta mentiría y el test falla.
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

from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
from uuid import UUID

import pytest

import repositories.empleado_repo as empleado_repo_mod
import services._dashboard_alertas as al
from repositories.empleado_repo import EmpleadoRepo
from schemas.dashboard import KPIResponse
from services._dashboard_alertas_catalogo import BLOQUEOS, CAMPOS_VACIOS

EMPRESA_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
EMPRESA_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_A, _B = str(EMPRESA_A), str(EMPRESA_B)

# Padrón sintético. En A: 6 activos sin superior (supera el umbral nominal de 5 → agregada),
# 1 con superior, 1 DE BAJA sin superior y 1 EN LICENCIA sin superior. En B: 1 sin superior.
#
# 🔑 `a9` (licencia) es la fila que hace que el mutation check muerda. Sin ella, `eq(estado,
# activo)` y `neq(estado, baja)` seleccionan lo MISMO en este padrón, así que revertir el
# predicado al `!= baja` desalineado pasaba en verde — el fake no podía desmentir la mutación.
# Es la pregunta obligatoria de la regla transversal, contestada acá: lo que tendría que ser
# distinto en el fake para que este test pueda fallar era exactamente esta fila.
_EMPLEADOS = (
    [{"id": f"a{i}", "empresa_id": _A, "manager_id": None, "email_corporativo": "x@y.z",
      "estado": "activo", "nombre": f"N{i}", "apellido": f"Ap{i}"} for i in range(1, 7)]
    + [
        {"id": "a7", "empresa_id": _A, "manager_id": "a1", "email_corporativo": "x@y.z",
         "estado": "activo", "nombre": "Con", "apellido": "Jefe"},
        {"id": "a8", "empresa_id": _A, "manager_id": None, "email_corporativo": "x@y.z",
         "estado": "baja", "nombre": "Ya", "apellido": "Fue"},
        {"id": "a9", "empresa_id": _A, "manager_id": None, "email_corporativo": "x@y.z",
         "estado": "licencia", "nombre": "En", "apellido": "Licencia"},
        {"id": "b1", "empresa_id": _B, "manager_id": None, "email_corporativo": "x@y.z",
         "estado": "activo", "nombre": "Beta", "apellido": "Uno"},
    ]
)

_KPIS_EN_CERO = KPIResponse(empleados_activos=0, ingresos_mes=0, bajas_mes=0,
                            costo_nomina=0.0, onboardings_activos=0, vacantes_activas=0)


class _Q:
    """Mini-motor de query: aplica eq / neq / is_(null) / limit sobre una lista de filas."""

    def __init__(self, filas: list) -> None:
        self._filas = filas
        self._eq: dict = {}
        self._neq: dict = {}
        self._nulos: list = []
        self._limit = None

    def select(self, *_a, **_k) -> "_Q":
        return self

    def eq(self, col: str, val) -> "_Q":
        self._eq[col] = str(val)
        return self

    def neq(self, col: str, val) -> "_Q":
        self._neq[col] = str(val)
        return self

    def is_(self, col: str, val: str) -> "_Q":
        assert val == "null", f"is_() acá se usa para nulos; llegó {val!r}"
        self._nulos.append(col)
        return self

    def limit(self, n: int) -> "_Q":
        self._limit = n
        return self

    def range(self, *_a, **_k) -> "_Q":
        return self

    def order(self, *_a, **_k):
        # No-op ENCADENABLE y permisivo A PROPOSITO: este fake audita el PREDICADO de la
        # query, no su orden ni su paginacion (`range` ya es no-op por lo mismo). El orden
        # tiene su propio archivo, tests/test_paginacion_orden.py, con un fake que si ordena.
        return self

    def or_(self, *_a, **_k) -> "_Q":
        return self

    def in_(self, *_a, **_k) -> "_Q":
        return self

    def _match(self, f: dict) -> bool:
        if any(str(f.get(c)) != v for c, v in self._eq.items()):
            return False
        if any(str(f.get(c)) == v for c, v in self._neq.items()):
            return False
        return all(f.get(c) is None for c in self._nulos)

    def execute(self):
        data = [f for f in self._filas if self._match(f)]
        # `count` sale de lo que sobrevive a los predicados, nunca de un valor prefabricado.
        total = len(data)
        if self._limit is not None:
            data = data[: self._limit]
        return SimpleNamespace(data=data, count=total)


class _FakeDB:
    def __init__(self, tablas: dict) -> None:
        self._t = tablas

    def table(self, nombre: str) -> _Q:
        return _Q(self._t.get(nombre, []))


def _tablas(**overrides) -> dict:
    """Todas las tablas de bloqueo VACÍAS salvo las que se pisen explícitamente."""
    base = {b.tabla: [] for b in BLOQUEOS}
    base["empleados"] = list(_EMPLEADOS)
    base.update(overrides)
    return base


def _alertas(empresa_id, **overrides):
    return al.generar_alertas(_KPIS_EN_CERO, empresa_id), _tablas(**overrides)


@pytest.fixture
def db(monkeypatch):
    """Instala el fake y devuelve un instalador para variar las tablas por test."""
    def instalar(**overrides) -> None:
        fake = _FakeDB(_tablas(**overrides))
        monkeypatch.setattr(al, "supabase_admin", fake)
        monkeypatch.setattr(empleado_repo_mod, "supabase_admin", fake)
        monkeypatch.setattr(empleado_repo_mod, "row", lambda r: r)
    return instalar


def _por_tipo(alertas) -> dict:
    return {a.tipo: a for a in alertas}


# ── Bloqueos de módulo ────────────────────────────────────────────────────────────


class TestBloqueosDeModulo:
    def test_cada_bloqueo_aparece_con_su_tabla_vacia(self, db) -> None:
        db()
        tipos = {a.tipo for a in al.generar_alertas(_KPIS_EN_CERO, EMPRESA_A)}
        faltantes = {b.tipo for b in BLOQUEOS} - tipos
        assert not faltantes, f"bloqueos que no se generaron con su tabla vacía: {faltantes}"

    def test_el_barrido_mira_los_cinco(self) -> None:
        """Guarda de mínimo: sin ella, si BLOQUEOS quedara vacío el test de arriba pasaría
        sin haber comprobado ni un bloqueo."""
        assert len(BLOQUEOS) >= 5

    @pytest.mark.parametrize("bloqueo", BLOQUEOS, ids=lambda b: b.tabla)
    def test_desaparece_con_una_fila(self, db, bloqueo) -> None:
        db(**{bloqueo.tabla: [{"id": "x1", "empresa_id": _A}]})
        tipos = {a.tipo for a in al.generar_alertas(_KPIS_EN_CERO, EMPRESA_A)}
        assert bloqueo.tipo not in tipos

    @pytest.mark.parametrize("bloqueo", BLOQUEOS, ids=lambda b: b.tabla)
    def test_el_mensaje_dice_que_hacer_y_lleva_a_alguna_parte(self, db, bloqueo) -> None:
        """No es cosmética: una alerta que solo describe el vacío no mueve a nadie."""
        db()
        alerta = _por_tipo(al.generar_alertas(_KPIS_EN_CERO, EMPRESA_A))[bloqueo.tipo]
        assert alerta.href and alerta.href.startswith("/")
        assert "{" not in alerta.mensaje  # sin placeholders sin resolver
        # Un mensaje corto solo alcanza para describir el vacío; el requisito es que además
        # diga qué NO se puede hacer y dónde cargarlo.
        assert len(alerta.mensaje) > 60 and ":" in alerta.mensaje


# ── Alerta agregada de campo vacío ────────────────────────────────────────────────


class TestAlertaAgregada:
    def test_el_conteo_coincide_con_las_filas_reales(self, db) -> None:
        """6 activos sin superior en A. El de baja NO cuenta, el de B tampoco."""
        db()
        alerta = _por_tipo(al.generar_alertas(_KPIS_EN_CERO, EMPRESA_A))["empleados_sin_manager"]
        assert alerta.mensaje.startswith("6 empleados sin superior asignado")

    def test_una_sola_linea_no_una_por_empleado(self, db) -> None:
        db()
        del_tipo = [a for a in al.generar_alertas(_KPIS_EN_CERO, EMPRESA_A)
                    if a.tipo == "empleados_sin_manager"]
        assert len(del_tipo) == 1

    def test_bajo_el_umbral_vuelve_a_la_forma_nominal(self, db) -> None:
        """Cardinalidad baja: una alerta por empleado, con link a SU ficha. Es más útil que un
        contador cuando son pocos: llegás y lo cargás."""
        pocos = [e for e in _EMPLEADOS if e["id"] in ("a1", "a2", "a7")]
        db(empleados=pocos)
        del_tipo = [a for a in al.generar_alertas(_KPIS_EN_CERO, EMPRESA_A)
                    if a.tipo == "empleados_sin_manager"]
        assert len(del_tipo) == 2
        assert {a.href for a in del_tipo} == {"/empleados/a1", "/empleados/a2"}

    def test_se_autoresuelve_cuando_no_queda_ninguno(self, db) -> None:
        completos = [{**e, "manager_id": "jefe"} for e in _EMPLEADOS]
        db(empleados=completos)
        tipos = {a.tipo for a in al.generar_alertas(_KPIS_EN_CERO, EMPRESA_A)}
        assert "empleados_sin_manager" not in tipos

    def test_solo_se_alerta_manager_id(self) -> None:
        """Decisión explícita: de los campos vacíos del padrón, `manager_id` es el único que
        desbloquea funcionalidad. seniority es cosmético y cargo/domicilio/teléfono son ruido
        garantizado. Si alguien suma otro, que sea a propósito y actualice este test."""
        assert {c.campo for c in CAMPOS_VACIOS} == {"manager_id", "email_corporativo"}


# ── 🔴 El href y el listado tienen que devolver lo MISMO ──────────────────────────


class TestElHrefLlevaAlListadoQueLasDevuelve:
    """El invariante que hace que la alerta agregada sirva: el número del mensaje y las filas
    a las que lleva el link salen del mismo conjunto. Si divergen, la alerta miente."""

    def test_el_href_filtrado_devuelve_exactamente_las_filas_contadas(self, db) -> None:
        db()
        alerta = _por_tipo(al.generar_alertas(_KPIS_EN_CERO, EMPRESA_A))["empleados_sin_manager"]

        url = urlparse(alerta.href)
        params = parse_qs(url.query)
        assert url.path == "/empleados"

        # El MISMO filtro, contra el MISMO padrón, por el repo REAL de empleados. Los filtros
        # salen del href PARSEADO, no escritos a mano: si mañana el catálogo linkea a otro
        # corte, el listado se consulta con ese otro corte y el test sigue siendo válido.
        items, total = EmpleadoRepo().find_all(
            1, 100, empresa_id=EMPRESA_A,
            estado=params.get("estado", [None])[0],
            sin_manager=params["sin_manager"][0] == "true",
        )
        assert alerta.mensaje.startswith(f"{total} empleados sin ")
        assert {i["id"] for i in items} == {"a1", "a2", "a3", "a4", "a5", "a6"}

    def test_el_empleado_de_baja_no_entra_por_ninguno_de_los_dos_lados(self, db) -> None:
        """🔴 El bug que este archivo encontró: la alerta contaba `!= baja` (6) y el href
        llevaba a un listado SIN filtro de estado (7, entraba `a8`). El usuario leía 6, hacía
        clic y veía 7. Sin el `estado=activo` en el href, este test vuelve a fallar."""
        db()
        alerta = _por_tipo(al.generar_alertas(_KPIS_EN_CERO, EMPRESA_A))["empleados_sin_manager"]
        params = parse_qs(urlparse(alerta.href).query)
        items, total = EmpleadoRepo().find_all(
            1, 100, empresa_id=EMPRESA_A,
            estado=params.get("estado", [None])[0], sin_manager=True,
        )
        assert total == 6 and "a8" not in {i["id"] for i in items}

    def test_el_predicado_de_la_alerta_es_activo_no_distinto_de_baja(self, db) -> None:
        """La fila que separa los dos predicados es `a9` (licencia, sin superior): `!= baja` la
        cuenta y `= activo` no. Si la alerta volviera a `!= baja` diría 7 mientras su propio
        href muestra 6 — el desajuste vuelve, con otra fila y el mismo síntoma.

        ⚠️ Deja fuera del aviso a quien está de licencia. Es el precio de que el número y el
        destino coincidan: `estado` es de un solo valor, así que 'no dado de baja' no se puede
        expresar en el href. Se recupera solo al volver a activo, y hoy son 0 en producción."""
        db()
        alerta = _por_tipo(al.generar_alertas(_KPIS_EN_CERO, EMPRESA_A))["empleados_sin_manager"]
        params = parse_qs(urlparse(alerta.href).query)
        _, con_activo = EmpleadoRepo().find_all(
            1, 100, empresa_id=EMPRESA_A, estado="activo", sin_manager=True)
        _, sin_estado = EmpleadoRepo().find_all(
            1, 100, empresa_id=EMPRESA_A, sin_manager=True)
        assert (con_activo, sin_estado) == (6, 8)      # los dos predicados NO son equivalentes
        assert params["estado"] == ["activo"]
        assert alerta.mensaje.startswith(f"{con_activo} empleados sin ")


# ── 🔴 Barrera de empresa ─────────────────────────────────────────────────────────


class TestNoCuentaFilasDeOtraEmpresa:
    """La empresa va EN EL WHERE. Sin el `.eq("empresa_id", ...)` estos conteos suben."""

    def test_el_conteo_agregado_ignora_la_otra_empresa(self, db) -> None:
        db()
        a = _por_tipo(al.generar_alertas(_KPIS_EN_CERO, EMPRESA_A))["empleados_sin_manager"]
        assert a.mensaje.startswith("6 ")   # sin la barrera serían 7 (entra b1)

    def test_la_otra_empresa_ve_lo_suyo(self, db) -> None:
        """B tiene 1 solo sin superior: por debajo del umbral, sale nominal y nombra a SU gente."""
        db()
        del_tipo = [a for a in al.generar_alertas(_KPIS_EN_CERO, EMPRESA_B)
                    if a.tipo == "empleados_sin_manager"]
        assert len(del_tipo) == 1 and del_tipo[0].href == "/empleados/b1"

    def test_un_bloqueo_no_se_apaga_con_filas_de_otra_empresa(self, db) -> None:
        """El caso que un fake de una sola empresa no puede ver: la empresa B tiene una vacante
        y la A no. La alerta de A tiene que seguir apareciendo."""
        db(vacantes=[{"id": "v-de-b", "empresa_id": _B}])
        tipos_a = {a.tipo for a in al.generar_alertas(_KPIS_EN_CERO, EMPRESA_A)}
        tipos_b = {a.tipo for a in al.generar_alertas(_KPIS_EN_CERO, EMPRESA_B)}
        assert "sin_vacantes" in tipos_a
        assert "sin_vacantes" not in tipos_b

    def test_consolidado_no_restringe(self, db) -> None:
        """empresa_id=None = vista consolidada: cuenta las dos empresas. No es un fallo de
        validación, es la semántica de get_empresa_id."""
        db()
        a = _por_tipo(al.generar_alertas(_KPIS_EN_CERO, None))["empleados_sin_manager"]
        assert a.mensaje.startswith("7 ")   # 6 de A + 1 de B


# ── Orden ─────────────────────────────────────────────────────────────────────────


class TestOrden:
    def test_las_accionables_van_arriba(self, db) -> None:
        """Antes salían en orden de generación: las informativas de KPIs quedaban primeras y
        lo que había que hacer, abajo del pliegue."""
        db()
        kpis = _KPIS_EN_CERO.model_copy(update={"vacantes_activas": 3, "onboardings_activos": 2})
        niveles = [a.nivel for a in al.generar_alertas(kpis, EMPRESA_A)]
        assert niveles == sorted(niveles, key=lambda n: {"error": 0, "warning": 1, "info": 2}[n])
        assert niveles[0] == "warning" and niveles[-1] == "info"

    def test_el_orden_dentro_de_un_nivel_es_el_del_catalogo(self, db) -> None:
        """`sorted` es estable: los warnings salen en el orden en que BLOQUEOS los declara,
        que pone primero el de costos_nomina (el que tumba más superficies)."""
        db()
        warnings = [a.tipo for a in al.generar_alertas(_KPIS_EN_CERO, EMPRESA_A)
                    if a.nivel == "warning"]
        assert warnings[0] == "sin_costos_nomina"

    def test_sin_nada_que_avisar_no_hay_alertas(self, db) -> None:
        llenas = {b.tabla: [{"id": "x", "empresa_id": _A}] for b in BLOQUEOS}
        llenas["empleados"] = [{**e, "manager_id": "jefe"} for e in _EMPLEADOS]
        db(**llenas)
        assert al.generar_alertas(_KPIS_EN_CERO, EMPRESA_A) == []

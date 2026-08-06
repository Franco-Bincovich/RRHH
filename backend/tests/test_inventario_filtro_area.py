"""
Filtro por área en el catálogo de ítems de inventario — sin red.

`inventario_items` NO tiene columna de área: el ítem llega al área por su asignación ACTIVA
(`repositories/_inventario_scope.items_de_area`). Eso hace que el filtro tenga dos casos borde
que no son bugs sino la definición, y son los que este archivo fija:

  · un ítem SIN asignación activa no aparece bajo ninguna área;
  · un ítem DEVUELTO no aparece bajo el área de quien lo tuvo.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

  · `_Supabase` modela una base chica de verdad: DOS áreas con un empleado y un ítem cada una,
    un ítem sin asignar y un ítem devuelto. Devuelve CONJUNTOS DISTINTOS según el `area_id`
    pedido. Un fake que aceptara `area_id` y devolviera siempre lo mismo no podría desmentir
    nada — es el caso #1 de la regla del repo, y es exactamente el bug que este filtro podría
    tener sin que nadie se entere.
  · El fake HONRA `fecha_devolucion`: guarda la fila devuelta y la filtra solo si la query trae
    el `is_("fecha_devolucion", "null")`. Sin eso, sacar ese filtro del código de producción
    dejaría el test en verde y el ítem devuelto seguiría apareciendo bajo el área ajena.
  · El fake HONRA `empresa_id`, con dos empresas, como exige la regla del repo.
  · Los tests de paso-de-parámetro (router→service→repo) usan un doble que REGISTRA lo que
    recibe; sin registrar, "lo pasó" y "lo ignoró" serían indistinguibles.
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

from typing import Optional
from uuid import UUID, uuid4

import pytest

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
AREA_SIS, AREA_RRHH = uuid4(), uuid4()
EMP_SIS, EMP_RRHH, EMP_B = str(uuid4()), str(uuid4()), str(uuid4())
IT_SIS, IT_RRHH, IT_LIBRE, IT_DEVUELTO = "it-sis", "it-rrhh", "it-libre", "it-devuelto"


# ── La base falsa ─────────────────────────────────────────────────────────────

# `nombre`/`apellido` los necesita el mapper (`_inventario_items_row._build`) para resolver
# `asignado_a`; sin ellos el test fallaría en el enriquecido, no en el filtro.
_EMPLEADOS = [
    {"id": EMP_SIS,  "area_id": str(AREA_SIS),  "empresa_id": str(EMPRESA_A), "nombre": "Ana", "apellido": "Sis"},
    {"id": EMP_RRHH, "area_id": str(AREA_RRHH), "empresa_id": str(EMPRESA_A), "nombre": "Beto", "apellido": "Rrhh"},
    {"id": EMP_B,    "area_id": str(AREA_SIS),  "empresa_id": str(EMPRESA_B), "nombre": "Caro", "apellido": "Beta"},
]
# IT_DEVUELTO lo tuvo el de Sistemas y ya lo devolvió. IT_LIBRE nunca se asignó.
_ASIGNACIONES = [
    {"item_id": IT_SIS,      "empleado_id": EMP_SIS,  "fecha_devolucion": None},
    {"item_id": IT_RRHH,     "empleado_id": EMP_RRHH, "fecha_devolucion": None},
    {"item_id": IT_DEVUELTO, "empleado_id": EMP_SIS,  "fecha_devolucion": "2024-01-31"},
]
def _item(id_: str, nombre: str, estado: str) -> dict:
    """Fila con TODOS los campos que `ItemResponse` exige: si faltara uno, el mapper reventaría
    y el test fallaría por el motivo equivocado."""
    return {"id": id_, "nombre": nombre, "empresa_id": str(EMPRESA_A), "estado": estado,
            "tipo": "Equipo", "fecha_alta": "2024-01-01", "created_at": "2024-01-01T00:00:00Z"}


_ITEMS = [
    _item(IT_SIS, "Notebook", "asignado"),
    _item(IT_RRHH, "Impresora", "asignado"),
    _item(IT_LIBRE, "Monitor", "disponible"),
    _item(IT_DEVUELTO, "Teclado", "disponible"),
]


class _Query:
    """Acumula los predicados y recién al `execute()` los aplica. Es lo que permite que el fake
    distinga una query con `is_(fecha_devolucion, null)` de una sin él."""

    def __init__(self, filas: list) -> None:
        self._filas, self._pred = filas, []

    def select(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def eq(self, col, val):
        self._pred.append(lambda r: str(r.get(col)) == str(val))
        return self

    def in_(self, col, vals):
        vistos = {str(v) for v in vals}
        self._pred.append(lambda r: str(r.get(col)) in vistos)
        return self

    def is_(self, col, _null):
        self._pred.append(lambda r: r.get(col) is None)
        return self

    def execute(self):
        filas = [r for r in self._filas if all(p(r) for p in self._pred)]
        return type("Res", (), {"data": filas})()


class _Supabase:
    def __init__(self) -> None:
        self.tablas: list = []

    def table(self, nombre: str):
        self.tablas.append(nombre)
        return _Query({"empleados": _EMPLEADOS, "inventario_asignaciones": _ASIGNACIONES,
                       "inventario_items": _ITEMS, "empresas": []}[nombre])


@pytest.fixture
def base(monkeypatch):
    """Enchufa la base falsa en los TRES módulos que la consultan por su cuenta."""
    from repositories import _inventario_items_row, _inventario_scope, _scope_filtros
    from repositories import inventario_items_repo
    fake = _Supabase()
    for mod in (_scope_filtros, _inventario_scope, inventario_items_repo, _inventario_items_row):
        monkeypatch.setattr(mod, "supabase_admin", fake)
    return fake


# ── items_de_area: la resolución del área a ítems ─────────────────────────────

class TestItemsDeArea:
    def test_cada_area_devuelve_SUS_items(self, base) -> None:
        """🔴 Los dos conjuntos en el mismo test. Con una sola área, un helper que devolviera
        siempre la lista completa —o siempre vacía— pasaría."""
        from repositories._inventario_scope import items_de_area
        assert items_de_area(AREA_SIS, EMPRESA_A) == [IT_SIS]
        assert items_de_area(AREA_RRHH, EMPRESA_A) == [IT_RRHH]

    def test_el_item_sin_asignar_no_cae_en_ninguna_area(self, base) -> None:
        """Es la definición: no hay área que pueda reclamarlo. Para que falle: que el salto
        partiera de `inventario_items` en vez de las asignaciones."""
        from repositories._inventario_scope import items_de_area
        assert IT_LIBRE not in items_de_area(AREA_SIS, EMPRESA_A)
        assert IT_LIBRE not in items_de_area(AREA_RRHH, EMPRESA_A)

    def test_el_item_DEVUELTO_no_cae_bajo_el_area_de_quien_lo_tuvo(self, base) -> None:
        """🔴 EL TEST QUE JUSTIFICA LA DEFINICIÓN. IT_DEVUELTO lo tuvo el empleado de Sistemas.
        Para que falle: sacar el `is_("fecha_devolucion", "null")` de `items_de_area` — sin este
        caso, ese filtro se puede borrar y toda la suite sigue en verde."""
        from repositories._inventario_scope import items_de_area
        assert items_de_area(AREA_SIS, EMPRESA_A) == [IT_SIS]

    def test_un_area_sin_empleados_devuelve_vacio(self, base) -> None:
        from repositories._inventario_scope import items_de_area
        assert items_de_area(uuid4(), EMPRESA_A) == []

    def test_acota_por_empresa(self, base) -> None:
        """EMP_B está en Sistemas pero es de otra empresa: no aporta sus ítems."""
        from repositories._inventario_scope import items_de_area
        assert items_de_area(AREA_SIS, EMPRESA_B) == []


# ── El repo: Forma A (el filtro en el WHERE) ──────────────────────────────────

class TestFindAll:
    @staticmethod
    def _nombres(**kw):
        from repositories.inventario_items_repo import InventarioItemsRepo
        return sorted(i.id for i in InventarioItemsRepo().find_all(**kw))

    def test_sin_area_trae_todo_el_catalogo(self, base) -> None:
        """Contrapeso: sin esto, un filtro que devolviera siempre vacío pasaría los de abajo."""
        assert self._nombres(empresa_id=EMPRESA_A) == sorted([IT_SIS, IT_RRHH, IT_LIBRE, IT_DEVUELTO])

    def test_filtrar_por_area_acota_a_sus_items(self, base) -> None:
        assert self._nombres(empresa_id=EMPRESA_A, area_id=AREA_SIS) == [IT_SIS]
        assert self._nombres(empresa_id=EMPRESA_A, area_id=AREA_RRHH) == [IT_RRHH]

    def test_area_y_estado_componen_por_AND(self, base) -> None:
        """🔴 El ítem de Sistemas está 'asignado'. Pedir área=Sistemas + estado=disponible tiene
        que dar VACÍO, no el ítem del área ni todos los disponibles. Para que falle: que un
        filtro pisara al otro en vez de sumarse."""
        assert self._nombres(empresa_id=EMPRESA_A, area_id=AREA_SIS, estado="asignado") == [IT_SIS]
        assert self._nombres(empresa_id=EMPRESA_A, area_id=AREA_SIS, estado="disponible") == []

    def test_area_sin_gente_corta_ANTES_de_ir_a_la_base(self, base) -> None:
        """El early return del molde: un `.in_([])` no es un WHERE válido. Se verifica que la
        tabla de ítems NO se haya consultado, no solo que el resultado sea []."""
        from repositories.inventario_items_repo import InventarioItemsRepo
        assert InventarioItemsRepo().find_all(empresa_id=EMPRESA_A, area_id=uuid4()) == []
        assert "inventario_items" not in base.tablas

    def test_el_devuelto_y_el_libre_estan_en_el_catalogo_pero_no_bajo_un_area(self, base) -> None:
        """Los dos siguen siendo ítems válidos del catálogo: lo que no tienen es área."""
        todos = self._nombres(empresa_id=EMPRESA_A)
        assert IT_LIBRE in todos and IT_DEVUELTO in todos
        conArea = self._nombres(empresa_id=EMPRESA_A, area_id=AREA_SIS)
        assert IT_LIBRE not in conArea and IT_DEVUELTO not in conArea


# ── El parámetro llega del router al repo ─────────────────────────────────────

class _RepoEspia:
    """Registra los argumentos con que lo llamaron. Sin registrar, "lo pasó" y "lo ignoró"
    serían indistinguibles — que es el falso positivo que la Fase 2 encontró 3 veces."""

    def __init__(self) -> None:
        self.args: dict = {}

    def find_all(self, empresa_id=None, estado=None, area_id=None):
        self.args = {"empresa_id": empresa_id, "estado": estado, "area_id": area_id}
        return []


class TestElParametroViajaEnteroHastaElRepo:
    @staticmethod
    def _svc(espia):
        from services.inventario_items_service import InventarioItemsService
        return InventarioItemsService(repo=espia)

    def test_el_listado_lo_pasa(self) -> None:
        espia = _RepoEspia()
        self._svc(espia).get_all(EMPRESA_A, "disponible", AREA_SIS)
        assert espia.args == {"empresa_id": EMPRESA_A, "estado": "disponible", "area_id": AREA_SIS}

    def test_el_export_lo_pasa(self) -> None:
        """La invariante list↔export: si el export no lo pasara, el archivo saldría con MÁS
        filas de las que se ven en pantalla, sin error y sin aviso."""
        espia = _RepoEspia()
        self._svc(espia).exportar(EMPRESA_A, "excel", "disponible", AREA_SIS)
        assert espia.args["area_id"] == AREA_SIS and espia.args["estado"] == "disponible"

    def test_sin_area_llega_None_y_no_un_string_vacio(self) -> None:
        espia = _RepoEspia()
        self._svc(espia).get_all(EMPRESA_A)
        assert espia.args["area_id"] is None

    @pytest.mark.parametrize("ruta", ["/api/inventario/items", "/api/inventario/items/exportar"])
    def test_el_router_declara_area_id_en_LAS_DOS(self, ruta: str) -> None:
        """Introspección de las rutas montadas: el nombre del Query tiene que ser el mismo en
        listado y export. `test_paridad_list_export` barre esto para todos los módulos; acá se
        fija el caso concreto con el tipo esperado."""
        import main
        r = next(x for x in main.app.routes if getattr(x, "path", "") == ruta)
        params = {p.name: p for p in r.dependant.query_params}
        assert "area_id" in params, f"{ruta} no acepta area_id"
        assert params["area_id"].type_ == Optional[UUID]

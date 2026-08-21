"""
Los DOS datos de la baja salen por la API: `fecha_egreso` y `motivo_baja`.

⚠️ EL NOMBRE DEL ARCHIVO DICE SOLO EL PRIMERO, y se dejó así a propósito: son el mismo módulo
(`EmpleadoResponse` + `_empleado_row.row`), la misma pregunta ("¿el dato de la baja llega a
quien lo muestra?") y el mismo padrón de fakes. Partirlo por campo daría dos archivos con el
mismo motor y la mitad de las aserciones cada uno — el criterio del repo es un archivo por
MÓDULO, no por campo.

## Por qué existe este archivo

La columna está en la base desde la migración 003 y la escribe `dar_de_baja` en el MISMO UPDATE
que `estado='baja'` (offboarding e import de nómina, los dos caminos). La leían tres agregados
—`bajas_mes` del dashboard, `generate_headcount` y el listado nominal de `_reporte_movimientos`—
pero **ningún consumidor de `EmpleadoResponse` podía verla**: ni la ficha, ni el listado, ni el
export. Una pantalla de Bajas no podía decir cuándo se fue cada persona teniendo el dato guardado.

## 🔴 QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR

  1. **El fake devuelve DICTS, no `EmpleadoResponse` prefabricados, y se faltea el CLIENTE de
     Supabase — un escalón por debajo del repo.** Es lo que hace que `_empleado_row.row()` corra
     de verdad. Con un fake de repo que devolviera el Response ya armado, el mapper no se
     ejecutaría y el test afirmaría sobre su propia constante: pasaría igual con `row()` borrado.
     Hoy `row()` reenvía TODAS las claves de la fila (`{k: v for k, v in r.items() ...}`), así
     que el campo viaja sin tocar el mapper — y justamente por eso hace falta el test: el día que
     alguien convierta ese reenvío en una lista explícita de columnas, esto rojea.

  2. **El padrón tiene las DOS filas que se comparan**: una de baja CON fecha y una activa SIN
     ella. Con una sola de las dos, la mitad de la aserción no puede fallar — un mapper que
     inventara una fecha para todos pasaría el caso de la baja, y uno que devolviera siempre
     `None` pasaría el del activo.

  3. **Las dos fechas del padrón son DISTINTAS entre sí** (`fecha_ingreso` != `fecha_egreso`): si
     fueran iguales, un mapper que copiara la de ingreso en el campo nuevo pasaría en verde.
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

from datetime import date, datetime  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from typing import List  # noqa: E402

import pytest  # noqa: E402

EMPRESA = "11111111-1111-1111-1111-111111111111"

# 🔑 Las dos fechas son distintas entre sí a propósito (ver el punto 3 del encabezado): si
# `fecha_egreso` coincidiera con `fecha_ingreso`, un mapper que copiara la columna equivocada
# pasaría el test.
INGRESO = date(2020, 3, 15)
EGRESO = date(2026, 5, 31)
MOTIVO = "renuncia"


def _fila(idx: int, apellido: str, estado: str, fecha_egreso, motivo=None) -> dict:
    """Una fila CRUDA de Supabase, con las claves tal como las devuelve el SELECT."""
    return {
        # 🔑 La clave va SIEMPRE, con `None` cuando no hay motivo, porque así llega del SELECT
        # `*`: la columna es nullable y PostgREST la devuelve igual. Un padrón que la omitiera
        # para el caso sin motivo estaría probando "la clave no está" en vez de "el valor es
        # nulo", que es lo que pasa de verdad y lo que la pantalla tiene que sobrevivir.
        "motivo_baja": motivo,
        "id": f"{idx:08d}-0000-0000-0000-000000000000",
        "nombre": "Nom",
        "apellido": apellido,
        "area_id": "22222222-2222-2222-2222-222222222222",
        "empresa_id": EMPRESA,
        "roles": ["Analista"],
        "modalidad_trabajo": "presencial",
        "tipo_contrato": "permanente",
        "fecha_ingreso": INGRESO,
        "fecha_egreso": fecha_egreso,
        "estado": estado,
        "created_at": datetime(2020, 3, 15, 12, 0, 0),
    }


def _padron() -> List[dict]:
    """Las dos filas que se comparan: una que se fue y una que sigue."""
    return [
        _fila(1, "Baja", "baja", EGRESO, MOTIVO),
        _fila(2, "Sigue", "activo", None),
        # La tercera es la que el import de nómina produce: se fue, con fecha, y sin motivo
        # porque el CSV no traía la columna `Motivo Baja`. Sin esta fila, un mapper que
        # devolviera el motivo de la primera para todos pasaría en verde.
        _fila(3, "SinMotivo", "baja", EGRESO),
    ]


class _FakeTabla:
    """Motor mínimo en memoria. Devuelve DICTS: el mapper del repo corre de verdad."""

    def __init__(self, filas: List[dict]) -> None:
        self._filas = list(filas)

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        self._filas = [r for r in self._filas if str(r.get(col)) == str(val)]
        return self

    def neq(self, col, val):
        self._filas = [r for r in self._filas if str(r.get(col)) != str(val)]
        return self

    def in_(self, col, vals):
        self._filas = [r for r in self._filas if str(r.get(col)) in {str(v) for v in vals}]
        return self

    def order(self, col, desc=False):
        self._filas = sorted(self._filas, key=lambda r: (r[col] is None, r[col]), reverse=desc)
        return self

    def range(self, start, end):
        self._filas = self._filas[start:end + 1]
        return self

    def execute(self):
        return SimpleNamespace(data=list(self._filas), count=len(self._filas))


@pytest.fixture
def repo(monkeypatch):
    """EmpleadoRepo contra el motor en memoria, con el mapper real en el camino."""
    import repositories.empleado_repo as mod

    padron = _padron()
    monkeypatch.setattr(
        mod, "supabase_admin",
        type("C", (), {"table": lambda s, t: _FakeTabla(padron)})(),
    )
    return mod.EmpleadoRepo()


def _por_apellido(items) -> dict:
    return {e.apellido: e for e in items}


class TestLaFechaDeEgresoLlegaAlResponse:
    def test_el_de_baja_sale_con_su_fecha(self, repo) -> None:
        """La fila de quien se fue trae la fecha real, no None y no la de ingreso."""
        items, _total = repo.find_all(1, 20, EMPRESA)
        baja = _por_apellido(items)["Baja"]
        assert baja.fecha_egreso == EGRESO
        assert baja.fecha_egreso != baja.fecha_ingreso, (
            "la fecha de egreso salió igual a la de ingreso: el mapper está copiando la columna "
            "equivocada"
        )

    def test_el_activo_la_trae_en_null(self, repo) -> None:
        """Quien sigue trabajando no tiene fecha de egreso, y eso NO es un faltante."""
        items, _total = repo.find_all(1, 20, EMPRESA)
        assert _por_apellido(items)["Sigue"].fecha_egreso is None

    def test_el_campo_existe_en_el_schema(self) -> None:
        """Contracara barata: si el campo no estuviera declarado, Pydantic lo descartaría en
        silencio y los dos tests de arriba dirían `None` para los dos casos — el de la baja
        rojearía, pero por un motivo que no se lee. Esto lo dice de frente."""
        from schemas.empleado import EmpleadoResponse

        assert "fecha_egreso" in EmpleadoResponse.model_fields

    def test_el_mapper_la_deja_pasar_en_los_dos_casos(self) -> None:
        """`row()` es el ÚNICO mapper de empleados: lo comparten el listado y la ficha
        (`_empleado_lookup_repo.por_id`). Ejercitarlo directo cubre las dos superficies —
        sin esto, el listado podría traerla y la ficha no."""
        from repositories._empleado_row import row

        assert row(_padron()[0]).fecha_egreso == EGRESO
        assert row(_padron()[1]).fecha_egreso is None


class TestLaFechaDeEgresoLlegaAlExport:
    """El archivo tiene que decir lo mismo que la pantalla. Un export al que le falta la columna
    es el caso que el repo ya documenta: el archivo y la pantalla divergen sin ningún error."""

    def _filas(self, repo):
        from services._empleados_export import construir_filas_export

        items, _total = repo.find_all(1, 20, EMPRESA)
        return {f["Apellido"]: f for f in construir_filas_export(items)}

    def test_la_columna_esta(self, repo) -> None:
        filas = self._filas(repo)
        assert "Fecha de egreso" in filas["Baja"], (
            "el export no tiene la columna: el archivo dice menos que la pantalla"
        )

    def test_el_de_baja_sale_con_la_fecha_formateada(self, repo) -> None:
        """dd/mm/aaaa, como el resto de las fechas del archivo."""
        assert self._filas(repo)["Baja"]["Fecha de egreso"] == "31/05/2026"

    def test_el_activo_sale_con_la_celda_VACIA_no_con_None(self, repo) -> None:
        """🔴 La celda vacía y el string "None" son cosas distintas en una planilla que abre una
        persona: la segunda se lee como un dato cargado que dice "None"."""
        assert self._filas(repo)["Sigue"]["Fecha de egreso"] == ""

    def test_la_de_ingreso_sigue_estando(self, repo) -> None:
        """Contracara: agregar una columna no puede haber pisado la de al lado."""
        assert self._filas(repo)["Baja"]["Fecha de ingreso"] == "15/03/2020"


class TestElMotivoDeLaBajaLlegaAlResponse:
    """Hermano exacto de la clase de arriba, sobre `motivo_baja`.

    🔴 LOS TRES CASOS DEL PADRÓN SON DISTINTOS ENTRE SÍ y hacen falta los tres: con solo la baja
    CON motivo, un mapper que devolviera un literal fijo pasaría; con solo la baja SIN motivo o
    el activo, uno que devolviera siempre `None` también. Es el punto 2 del encabezado, aplicado
    a un campo que se puebla en el 50% de las filas que importan.
    """

    def test_la_baja_con_motivo_lo_trae(self, repo) -> None:
        items, _total = repo.find_all(1, 20, EMPRESA)
        assert _por_apellido(items)["Baja"].motivo_baja == MOTIVO

    def test_la_baja_sin_motivo_lo_trae_en_null(self, repo) -> None:
        """🔴 `None`, NO el string "Sin especificar". Una baja del import de nómina sin la
        columna `Motivo Baja` no tiene motivo, y traducirlo acá convertiría "no sabemos" en un
        motivo cargado — la pantalla no podría distinguir uno del otro."""
        items, _total = repo.find_all(1, 20, EMPRESA)
        assert _por_apellido(items)["SinMotivo"].motivo_baja is None

    def test_el_activo_tampoco_lo_tiene(self, repo) -> None:
        items, _total = repo.find_all(1, 20, EMPRESA)
        assert _por_apellido(items)["Sigue"].motivo_baja is None

    def test_el_campo_existe_en_el_schema(self) -> None:
        """Contracara barata: sin el campo declarado, Pydantic lo descarta en silencio y los
        tres de arriba dirían `None` — el primero rojearía por un motivo que no se lee."""
        from schemas.empleado import EmpleadoResponse

        assert "motivo_baja" in EmpleadoResponse.model_fields

    def test_el_mapper_lo_deja_pasar(self) -> None:
        """`row()` lo comparten el listado y la ficha: ejercitarlo directo cubre las dos."""
        from repositories._empleado_row import row

        assert row(_padron()[0]).motivo_baja == MOTIVO
        assert row(_padron()[2]).motivo_baja is None

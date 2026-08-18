"""
`candidatos.estado` sale por la API con su valor real, en los CUATRO estados del CHECK.

## Qué clase de bug cierra

La columna existe en la tabla desde siempre (`estado varchar(20) NOT NULL DEFAULT 'activo'`, con
CHECK `activo | descartado | contratado | en_espera`), el repo la lee —`candidato_repo` consulta
con `select("*")`, así que viaja en TODAS las filas— y **se descartaba en silencio**: `_crow` no
la mapeaba y `CandidatoResponse` no la declaraba. Nadie del lado de la app podía saber que un
candidato estaba descartado o contratado; la única forma de leerlo era abrir el dashboard de
Supabase.

Es exactamente el modo de falla que `_candidato_row.py` documenta en su propio comentario para
`screening_warning` ("si esta línea faltara, el `select("*")` traería la columna y el schema la
descartaría EN SILENCIO — el bug que ya pasó tres veces en este repo"). Pasó una cuarta, en la
columna de al lado, y con el comentario mirándola.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?

**Que `_crow` dejara de mapear `estado`, o que `CandidatoResponse` dejara de declararlo.** Los
tests van contra el mapper REAL y contra el schema REAL — no hay un doble en el medio que pueda
mentir. Es el molde de `test_cv_texto::test_el_warning_llega_al_schema`, que ancló esta misma
propiedad para `screening_warning` y es la razón por la que aquella columna sí sobrevivió.

Se ejercitan **los cuatro valores** y no uno solo a propósito: con un único estado, un mapper que
devolviera la constante `"activo"` en vez de leer la fila pasaría igual. Cuatro valores distintos
lo desmienten.

⚠️ ACÁ NO SE PRUEBA NINGUNA ESCRITURA, y no es un olvido: **hoy ningún endpoint escribe
`candidatos.estado`**. El único que va a escribirlo es el puente candidato→empleado (A4.2), y su
test va con él. Esta tanda revive la LECTURA, que es lo que estaba roto.
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

from datetime import datetime, timezone  # noqa: E402
from typing import Optional  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402

import repositories.candidato_repo as repo_mod  # noqa: E402
from repositories._candidato_row import _crow  # noqa: E402
from schemas.candidato import CandidatoResponse  # noqa: E402

# Los cuatro valores del CHECK `candidatos_estado_check`, escritos acá como literales y NO
# importados del schema: si se importaran del mismo `Literal` que se quiere verificar, el test
# afirmaría que el schema coincide consigo mismo. El espejo del CHECK se ancla con literales.
ESTADOS = ["activo", "descartado", "contratado", "en_espera"]

EMPRESA_A = str(uuid4())
EMPRESA_B = str(uuid4())
AHORA = datetime.now(timezone.utc)


def _fila(estado: str, empresa: str = EMPRESA_A, cid: Optional[str] = None) -> dict:
    """Una fila cruda de `candidatos` como la devuelve `select("*")`, con el estado pedido."""
    return {
        "id": cid or str(uuid4()), "vacante_id": None, "empresa_id": empresa,
        "nombre": "Ana", "apellido": "Pérez", "email": "ana@ejemplo.com",
        "etapa": "oferta", "estado": estado, "created_at": AHORA,
    }


# ── El mapper real ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("estado", ESTADOS)
def test_los_cuatro_estados_sobreviven_al_mapper(estado: str) -> None:
    """Cada valor del CHECK entra por la fila y sale por el schema, sin traducción ni pérdida.

    ¿Qué tendría que ser distinto para que falle? Que `_crow` no leyera `estado` de la fila. Con
    el código anterior a esta tanda, `CandidatoResponse` ni siquiera acepta el campo.
    """
    assert _crow(_fila(estado)).estado == estado


def test_el_estado_esta_declarado_en_el_schema() -> None:
    """La declaración, aparte del mapeo: son las DOS mitades y cada una se rompe sola.

    Un mapper que pase `estado=...` a un schema que no lo declara **no explota**: Pydantic
    descarta el extra en silencio (es el default de `model_config`), que es la mitad exacta del
    bug original. Por eso se afirma sobre `model_fields` y no sólo sobre una instancia.
    """
    assert "estado" in CandidatoResponse.model_fields


@pytest.mark.parametrize("invalido", ["", "contratada", "ACTIVO", "baja"])
def test_un_estado_fuera_del_check_no_entra(invalido: str) -> None:
    """El `Literal` es el espejo del CHECK y corta en la frontera, no en Postgres.

    Sin tipar, un valor cualquiera viajaría hasta la base, chocaría contra
    `candidatos_estado_check` y volvería como un 23514 que ningún `except` mapea — un 500 por un
    dato del request. Mismo criterio que `EstadoEmpleado` en `utils/estados_empleado.py`.

    ¿Qué tendría que ser distinto para que falle? Que el campo se tipara `str`. Con `str`, los
    cuatro valores de acá entran sin una queja.
    """
    with pytest.raises(Exception):
        CandidatoResponse(**{**_fila("activo"), "estado": invalido,
                             "etapa_pipeline": "oferta"})


# ── El camino de lectura completo, con la barrera de empresa puesta ───────────

class _FakeQuery:
    """Doble de la query de PostgREST que HONRA el `.eq("empresa_id", ...)`.

    🔴 MODELA DOS EMPRESAS Y DEVUELVE `None` CUANDO NO COINCIDEN, como manda la regla
    transversal del repo: un doble que aceptara `empresa_id` y lo ignorara daría verde sin
    validar nada. Acá además tiene una función concreta — probar que el estado viaja por el
    camino REAL de lectura (`find_by_id`), no sólo por el mapper suelto.
    """

    def __init__(self, filas: list[dict]) -> None:
        self._filas = filas

    def select(self, *a, **k) -> "_FakeQuery":
        return self

    def eq(self, columna: str, valor) -> "_FakeQuery":
        return _FakeQuery([f for f in self._filas if str(f.get(columna)) == str(valor)])

    def maybe_single(self) -> "_FakeQuery":
        return self

    def execute(self):
        class _Res:
            data = self._filas[0] if self._filas else None
        return _Res()


class _FakeSupabase:
    def __init__(self, filas: list[dict]) -> None:
        self._filas = filas

    def table(self, nombre: str) -> _FakeQuery:
        return _FakeQuery(self._filas)


@pytest.mark.parametrize("estado", ESTADOS)
def test_find_by_id_devuelve_el_estado(monkeypatch, estado: str) -> None:
    """El estado llega hasta el service por el camino real, no sólo por el mapper aislado."""
    cid = str(uuid4())
    monkeypatch.setattr(repo_mod, "supabase_admin",
                        _FakeSupabase([_fila(estado, EMPRESA_A, cid)]))
    encontrado = repo_mod.CandidatoRepo().find_by_id(cid, EMPRESA_A)
    assert encontrado is not None and encontrado.estado == estado


def test_la_barrera_de_empresa_sigue_cerrada(monkeypatch) -> None:
    """La contracara del anterior: sin ella, el fake podría estar devolviendo la fila siempre.

    ¿Qué tendría que ser distinto para que falle? Que `_FakeQuery.eq` ignorara la columna — o sea
    el caso #1 de "un test solo prueba lo que el fake puede desmentir".
    """
    cid = str(uuid4())
    monkeypatch.setattr(repo_mod, "supabase_admin",
                        _FakeSupabase([_fila("contratado", EMPRESA_A, cid)]))
    assert repo_mod.CandidatoRepo().find_by_id(cid, EMPRESA_B) is None

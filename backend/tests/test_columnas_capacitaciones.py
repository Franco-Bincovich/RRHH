"""
BARRIDO ESTRUCTURAL — toda columna de `capacitaciones` y de `empleado_capacitacion` está
EXPUESTA, o DECLARADA como no expuesta con su razón, o es un DERIVADO declarado. Ninguna puede
quedarse en el medio.

Molde: `tests/test_columnas_candidatos.py`, que explica por qué los otros tres barridos
estructurales no pueden ver este bug (los tres viajan código → base; este vive en la dirección
contraria). Acá no se repite ese encabezado: leerlo allá.

## El caso que lo trajo a estas dos tablas

Las 7 columnas de formación de la migración 116 (`entidad_capacitadora`, `modalidad`, `tipo` en
el catálogo; `proyecto`, `anio`, `mes`, `nombre_libre` en las asignaciones) existieron en la base
con el `select("*")` trayéndolas y Pydantic descartándolas en silencio — el bug de
`candidatos.estado`, dos tablas más allá. Se cablearon el 19/8/2026; este barrido es lo que
impide que la próxima columna nazca igual.

## El inventario del patrón (actualizado el 19/8/2026)

Con estas dos tablas, el patrón columna-vs-schema cubre **3 tablas** (candidatos + estas dos),
o sea **4 de los 30 archivos de `repositories/` que leen con `select("*")`** (candidato_repo y
su satélite `_candidato_row`, `capacitacion_repo`, `asignacion_repo`). Quedan **26 archivos sin
barrido de columnas** — el número era 32 cuando se escribió el de candidatos; se remide acá cada
vez que el patrón crece. Generalizarlo sigue anotado en `docs/DEUDA-TECNICA.md`.

## Qué agrega este runner sobre el de candidatos

El concepto `DERIVADOS`: estos Responses publican campos que no son columnas (joins resueltos
por `_build`). La dirección inversa del barrido los permite SOLO si están declarados con razón —
sin eso, o el barrido rojea sobre campos legítimos, o se afloja y deja pasar el campo-fantasma
que siempre vale su default. El porqué de no retrofitear esto en candidatos está en el
encabezado de `tests/_columnas_capacitaciones.py`.
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

import inspect  # noqa: E402

import pytest  # noqa: E402

import repositories.asignacion_repo as asignacion_repo_mod  # noqa: E402
import repositories.capacitacion_repo as capacitacion_repo_mod  # noqa: E402
from tests._columnas_capacitaciones import INVENTARIOS, campos, columnas  # noqa: E402

_TABLAS = sorted(INVENTARIOS)


# ── Guardas ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("tabla", _TABLAS)
def test_la_derivacion_encuentra_algo(tabla: str) -> None:
    """GUARDA CONTRA EL FALSO VERDE: sin esto, dos conjuntos vacíos pasarían todo.

    ¿Qué tendría que ser distinto para que falle? Que `cargar_schema` dejara de parsear la tabla
    (un cambio de formato en schema.sql) o que `model_fields` dejara de resolverse — que es
    exactamente cuando los tests de abajo dejan de mirar nada.
    """
    inv = INVENTARIOS[tabla]
    assert len(columnas(tabla)) >= inv["minimo_columnas"], (
        f"Sólo {len(columnas(tabla))} columnas de '{tabla}' (mínimo {inv['minimo_columnas']}). "
        "El parseo de schema.sql se rompió: sin esto el barrido pasa en el vacío."
    )
    assert len(campos(tabla)) >= inv["minimo_campos"], (
        f"Sólo {len(campos(tabla))} campos en {inv['schema'].__name__} "
        f"(mínimo {inv['minimo_campos']})."
    )


@pytest.mark.parametrize("repo_mod", [capacitacion_repo_mod, asignacion_repo_mod],
                         ids=["capacitacion_repo", "asignacion_repo"])
def test_el_select_sigue_siendo_estrella(repo_mod) -> None:
    """La PREMISA del barrido, anclada: los dos repos leen con `select("*")`, así que la fila
    llega entera y lo único que puede perder una columna es el mapper o el schema.

    Si alguien angostara el select a una lista de columnas, este barrido seguiría en verde
    mientras el dato deja de viajar. En ese caso lo correcto es cambiar la fuente de columnas
    por el select, no borrar este test.
    """
    fuente = inspect.getsource(repo_mod)
    assert 'select("*"' in fuente, (
        f"{repo_mod.__name__} dejó de leer con select(\"*\"): la premisa del barrido cambió."
    )


# ── El barrido, en las dos direcciones ────────────────────────────────────────

@pytest.mark.parametrize("tabla", _TABLAS)
def test_toda_columna_esta_expuesta_o_declarada(tabla: str) -> None:
    """🔴 EL BARRIDO. Ninguna columna puede quedar sin decisión.

    ¿Qué tendría que ser distinto para que falle? Nada del test: falla sola en cuanto una
    columna nueva aparece sin exponerse ni declararse. Contra el código anterior al 19/8/2026
    rojeaba con exactamente las 6 columnas huérfanas de la migración 116.
    """
    inv = INVENTARIOS[tabla]
    huerfanas = sorted(
        col for col in columnas(tabla)
        if col not in campos(tabla) and col not in inv["no_expuestas"]
    )
    assert not huerfanas, (
        f"Columnas de '{tabla}' que el select TRAE y nadie usa ni declaró:\n  "
        + "\n  ".join(huerfanas)
        + f"\nExponela en {inv['schema'].__name__}, o declarala en el inventario "
          "de tests/_columnas_capacitaciones.py CON su razón."
    )


@pytest.mark.parametrize("tabla", _TABLAS)
def test_todo_campo_corresponde_a_una_columna_o_derivado(tabla: str) -> None:
    """La dirección contraria: un campo sin columna ni derivación detrás vale su default para
    siempre — la API lo devuelve, el front lo pinta, y muestra vacío sin error ni aviso.

    Los DERIVADOS pasan solo por estar declarados: es lo que mantiene la distinción entre "lo
    resuelve `_build`" y "nadie lo llena".
    """
    inv = INVENTARIOS[tabla]
    sin_respaldo = sorted(
        c for c in campos(tabla) if c not in columnas(tabla) and c not in inv["derivados"]
    )
    assert not sin_respaldo, (
        f"Campos de {inv['schema'].__name__} que no corresponden a ninguna columna de "
        f"'{tabla}' ni a un derivado declarado:\n  " + "\n  ".join(sin_respaldo)
    )


@pytest.mark.parametrize("tabla", _TABLAS)
def test_ninguna_declaracion_esta_muerta(tabla: str) -> None:
    """Una declaración que apunta a algo que ya no existe es ruido que tapa el próximo caso.

    Tres formas de morirse, las tres cubiertas: una NO_EXPUESTA cuya columna se borró; un
    DERIVADO cuyo campo se borró del schema; y un DERIVADO que pasó a ser columna real (la
    declaración diría "lo resuelve un join" sobre un dato que ahora viaja en la fila).
    """
    inv = INVENTARIOS[tabla]
    muertas = sorted(set(inv["no_expuestas"]) - columnas(tabla))
    assert not muertas, f"NO_EXPUESTAS de '{tabla}' sin columna detrás: {muertas}"
    sin_campo = sorted(set(inv["derivados"]) - campos(tabla))
    assert not sin_campo, f"DERIVADOS de '{tabla}' que ya no son campos del schema: {sin_campo}"
    ascendidos = sorted(set(inv["derivados"]) & columnas(tabla))
    assert not ascendidos, (
        f"DERIVADOS de '{tabla}' que ahora son columnas reales: {ascendidos}. "
        "Sacarlos del inventario: ya no los resuelve un join."
    )


@pytest.mark.parametrize("tabla", _TABLAS)
def test_toda_declaracion_tiene_razon_de_verdad(tabla: str) -> None:
    """La razón es el contenido del inventario, no un campo a completar con cualquier cosa.

    Sin el porqué, la próxima persona borra una entrada porque "no se usa" y revive el bug que
    este barrido existe para impedir.
    """
    inv = INVENTARIOS[tabla]
    flojas = sorted(
        c for c, r in {**inv["no_expuestas"], **inv["derivados"]}.items()
        if len(r.strip()) < 40
    )
    assert not flojas, f"Estas declaraciones de '{tabla}' no explican nada: {flojas}"

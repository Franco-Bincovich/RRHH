"""
BARRIDO ESTRUCTURAL nº 53 — toda columna de `empleados` está EXPUESTA, o DECLARADA como no
expuesta con su razón, o es un DERIVADO declarado. Ninguna puede quedarse en el medio.

Molde: `tests/test_columnas_capacitaciones.py` (que introdujo `DERIVADOS`) y, detrás,
`tests/test_columnas_candidatos.py`, que explica por qué los otros barridos estructurales **no
pueden ver este bug**: los tres viajan código → base (validan que lo que el código pide exista);
éste viaja base → código, y es la única dirección en la que se ve una columna que el `select("*")`
TRAE y nadie usa. Ese encabezado no se repite acá: leerlo allá.

## El caso que lo trajo a ESTA tabla, que es la central del producto

El 25/8/2026 se midió `empleados` contra `EmpleadoResponse` y aparecieron **DOCE columnas que la
base tenía y el schema descartaba en silencio**, siete de ellas con dato en producción:
`fecha_ingreso_reconocida` (10/41), `potencial` y `desempeno` (41/41), `liderazgo` y
`product_owner` (31/41), más `equipo` y `co_sourcing`. La más cara es la primera: **decide el cupo
de vacaciones** —la regla por antigüedad la usa en lugar de `fecha_ingreso` cuando está cargada— y
no se mostraba en ninguna pantalla, así que un cupo que no coincidía con la fecha de ingreso no
tenía explicación posible desde la UI.

**Es la sexta vez que aparece el mismo bug** (`candidatos.estado`, las 6 columnas de la migración
116 en formación, `fecha_egreso`, `motivo_baja`, `kpis_extra.errores` del dashboard, y ahora
estas doce). Las tres primeras se cerraron con este patrón; la tabla central se había quedado
afuera. Sin este archivo, la séptima ya estaba comprada.

## Qué NO puede ver, dicho de frente

Una columna que el schema SÍ expone y que **nadie escribe nunca**. `organismo`, `sector` y
`perfil` estuvieron 0/41 durante meses con la ficha mostrando un guion, y este barrido las habría
dado por buenas: el schema y la tabla coinciden perfecto. Ese es otro bug y otro barrido (haría
falta cruzar contra los ESCRITORES, no contra el schema). Está anotado en `_columnas_empleados.py`.
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

import pytest  # noqa: E402

import repositories._empleado_row as empleado_row_mod  # noqa: E402
from tests._columnas_empleados import (  # noqa: E402
    DERIVADOS, MINIMO_CAMPOS, MINIMO_COLUMNAS, NO_EXPUESTAS, TABLA, campos, columnas,
)


# ── Guardas ───────────────────────────────────────────────────────────────────

def test_la_derivacion_encuentra_algo() -> None:
    """GUARDA CONTRA EL FALSO VERDE: sin esto, dos conjuntos vacíos pasarían todo lo de abajo.

    ¿Qué tendría que ser distinto para que falle? Que `cargar_schema` dejara de parsear
    `empleados` (un cambio de formato en schema.sql) o que `model_fields` dejara de resolverse —
    que es exactamente cuando los tests de abajo dejan de mirar nada.
    """
    assert len(columnas()) >= MINIMO_COLUMNAS, (
        f"Sólo {len(columnas())} columnas de '{TABLA}' (mínimo {MINIMO_COLUMNAS}). El parseo de "
        "schema.sql se rompió: sin esto el barrido pasa en el vacío."
    )
    assert len(campos()) >= MINIMO_CAMPOS, (
        f"Sólo {len(campos())} campos en EmpleadoResponse (mínimo {MINIMO_CAMPOS})."
    )


def test_el_select_sigue_trayendo_la_fila_entera() -> None:
    """La PREMISA del barrido, anclada.

    🔴 ACÁ EL SELECT NO ES `select("*")` PELADO como en los otros tres módulos: es la constante
    `_empleado_row.SELECT`, que arranca con `*` y le suma los tres embeds de joins. Por eso el
    test mira la CONSTANTE y no el texto del repo — buscar el literal `select("*")` daría verde
    sobre un archivo que no lo contiene.

    Si alguien angostara ese `*` a una lista de columnas, este barrido seguiría en verde mientras
    el dato deja de viajar. En ese caso lo correcto es cambiar la fuente de columnas por el
    select, no borrar este test.
    """
    assert empleado_row_mod.SELECT.lstrip().startswith("*"), (
        "`_empleado_row.SELECT` dejó de empezar con `*`: la premisa del barrido cambió."
    )


# ── El barrido, en las dos direcciones ────────────────────────────────────────

def test_toda_columna_esta_expuesta_o_declarada() -> None:
    """🔴 EL BARRIDO. Ninguna columna puede quedar sin decisión.

    ¿Qué tendría que ser distinto para que falle? Nada del test: falla sola en cuanto una columna
    nueva aparece sin exponerse ni declararse. Contra el código anterior al 25/8/2026 rojeaba con
    exactamente las 12 columnas huérfanas, siete de ellas con dato en producción.
    """
    huerfanas = sorted(c for c in columnas() if c not in campos() and c not in NO_EXPUESTAS)
    assert not huerfanas, (
        f"Columnas de '{TABLA}' que el select TRAE y nadie usa ni declaró:\n  "
        + "\n  ".join(huerfanas)
        + "\nExponela en EmpleadoResponse (schemas/empleado_out.py), o declarala en "
          "tests/_columnas_empleados.py CON su razón."
    )


def test_todo_campo_corresponde_a_una_columna_o_derivado() -> None:
    """La dirección contraria: un campo sin columna ni derivación detrás vale su default para
    siempre — la API lo devuelve, el front lo pinta, y muestra vacío sin error ni aviso.

    Los DERIVADOS pasan sólo por estar declarados: es lo que mantiene la distinción entre "lo
    resuelve un join del SELECT" y "nadie lo llena".
    """
    sin_respaldo = sorted(c for c in campos() if c not in columnas() and c not in DERIVADOS)
    assert not sin_respaldo, (
        "Campos de EmpleadoResponse que no corresponden a ninguna columna de "
        f"'{TABLA}' ni a un derivado declarado:\n  " + "\n  ".join(sin_respaldo)
    )


def test_ninguna_declaracion_esta_muerta() -> None:
    """Una declaración que apunta a algo que ya no existe es ruido que tapa el próximo caso.

    Tres formas de morirse, las tres cubiertas: una NO_EXPUESTA cuya columna se borró; un DERIVADO
    cuyo campo se borró del schema; y un DERIVADO que pasó a ser columna real (la declaración
    diría "lo resuelve un join" sobre un dato que ahora viaja en la fila).
    """
    muertas = sorted(set(NO_EXPUESTAS) - columnas())
    assert not muertas, f"NO_EXPUESTAS de '{TABLA}' sin columna detrás: {muertas}"
    sin_campo = sorted(set(DERIVADOS) - campos())
    assert not sin_campo, f"DERIVADOS de '{TABLA}' que ya no son campos del schema: {sin_campo}"
    ascendidos = sorted(set(DERIVADOS) & columnas())
    assert not ascendidos, (
        f"DERIVADOS de '{TABLA}' que ahora son columnas reales: {ascendidos}. "
        "Sacarlos del inventario: ya no los resuelve un join."
    )


def test_una_declaracion_no_puede_estar_de_los_dos_lados() -> None:
    """Una columna declarada NO_EXPUESTA que además figura como campo del schema es una
    contradicción: el inventario diría que no viaja y estaría viajando. Es la forma exacta en que
    quedaría el archivo si alguien expone una columna y se olvida de sacarla de la lista."""
    contradictorias = sorted(set(NO_EXPUESTAS) & campos())
    assert not contradictorias, (
        f"Declaradas NO_EXPUESTAS y expuestas a la vez: {contradictorias}. "
        "Si se decidió exponerlas, sacalas del inventario."
    )


@pytest.mark.parametrize("campo", sorted({**NO_EXPUESTAS, **DERIVADOS}))
def test_toda_declaracion_tiene_razon_de_verdad(campo: str) -> None:
    """La razón es el contenido del inventario, no un campo a completar con cualquier cosa.

    Sin el porqué, la próxima persona borra una entrada porque "no se usa" y revive el bug que
    este barrido existe para impedir. Se parametriza por campo (y no se junta en una lista) para
    que el rojo nombre CUÁL declaración está floja.
    """
    razon = {**NO_EXPUESTAS, **DERIVADOS}[campo]
    assert len(razon.strip()) >= 60, f"la declaración de `{campo}` no explica nada"

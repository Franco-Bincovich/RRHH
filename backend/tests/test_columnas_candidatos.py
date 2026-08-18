"""
BARRIDO ESTRUCTURAL — toda columna de `candidatos` está EXPUESTA o está DECLARADA como no
expuesta, con su razón. Ninguna puede quedarse en el medio.

## 🔴 POR QUÉ HACÍA FALTA UN BARRIDO NUEVO, Y NO ALCANZABA CON NINGUNO DE LOS TRES QUE YA HAY

`candidatos.estado` existió durante meses con el `select("*")` trayéndola y el mapper
descartándola, con **tres barridos estructurales mirando este mismo módulo** y los tres en
verde. No es que fallaran: es que **los tres viajan en la dirección código → base**, y este bug
vive en la dirección contraria.

  · **`test_selects_repos`** valida cada `select` contra `db/schema.sql`: pregunta *¿existe en la
    tabla todo lo que el select PIDE?*. `candidato_repo` pide `select("*")`, y `_validar_columna`
    de `_postgrest_schema` corta con un `return` en cuanto ve `*`. Un select que pide todo no
    puede pedir de más: **la aserción es vacua por construcción**, no rota. Nunca tuvo forma de
    preguntar qué hace el código con lo que recibe.
  · **`test_mappers_ejercitados` / `test_mappers_con_datos`** persiguen otra cosa: mappers que
    abren con `if not rows: return []` y se llaman siempre con `[]`, o sea cuyo cuerpo no se
    ejecuta nunca. `_crow` recibe **un dict, no una lista**, y no tiene ese early-return, así que
    `_mappers_early_return.descubrir()` ni siquiera lo lista. Y aunque lo listara: ejercitar un
    mapper prueba que su cuerpo CORRE, no que mapee todas las columnas. Un `_crow` al que le
    falta una línea corre perfecto.
  · **`test_contrato_repos`** compara `self.<attr>.<metodo>()` contra los métodos que la clase
    colaboradora declara. Es sobre MÉTODOS entre capas; no sabe qué es una columna.

**La conclusión que deja: `select("*")` es un punto ciego estructural.** Hace que la única
pregunta que el repo sabía hacer ("¿el select pide algo que no existe?") sea imposible de
contestar que no, y deja la pregunta que importa ("¿el código usa todo lo que el select trae?")
sin nadie que la haga. Hoy hay **32 repos** que leen con `select("*")`; este barrido cubre uno.
Generalizarlo a los 32 está anotado en `docs/DEUDA-TECNICA.md`, **sin adelantarlo acá**: los
otros 31 todavía no se midieron, y una maquinaria parametrizada escrita contra un solo caso fija
una forma que no se probó contra ningún segundo.

## Cómo funciona

Las columnas salen del catálogo de `db/schema.sql` (vía `_postgrest_schema.cargar_schema`, el
mismo loader que ya usan los otros dos barridos) y los campos salen de `CandidatoResponse`. Lo
ÚNICO escrito a mano son las dos tablas declarativas, que viven en `tests/_columnas_candidatos.py`
junto con la razón de cada columna no expuesta. Una columna nueva en la tabla rompe el test hasta
que alguien decida qué hacer con ella — que es justamente la decisión que con `estado` nadie tomó.

Se verifica en las DOS direcciones, y la segunda no es simetría de adorno: un campo del schema
que no corresponde a ninguna columna es un campo que siempre vale su default, o sea una promesa
que la pantalla muestra vacía para siempre.

## Guarda contra el falso verde

`MINIMO_COLUMNAS` y `MINIMO_CAMPOS`: si `cargar_schema` dejara de parsear la tabla o el schema
dejara de introspectarse, los dos conjuntos quedarían vacíos y **todas las comparaciones pasarían
sin haber comparado nada**. Y `test_ninguna_excepcion_esta_muerta` cierra la contracara: una
declaración que apunta a una columna borrada es ruido que tapa el próximo caso.
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

import repositories.candidato_repo as repo_mod  # noqa: E402
from tests._columnas_candidatos import (  # noqa: E402
    MINIMO_CAMPOS, MINIMO_COLUMNAS, NO_EXPUESTAS, RENOMBRADAS, TABLA, campos, columnas,
)


# ── Guardas ───────────────────────────────────────────────────────────────────

def test_la_derivacion_encuentra_algo() -> None:
    """GUARDA CONTRA EL FALSO VERDE: sin esto, dos conjuntos vacíos pasarían todo.

    ¿Qué tendría que ser distinto para que falle? Que `cargar_schema` dejara de parsear la tabla
    (un cambio de formato en schema.sql) o que `model_fields` dejara de resolverse — que es
    exactamente cuando los dos tests de abajo dejan de mirar nada.
    """
    assert len(columnas()) >= MINIMO_COLUMNAS, (
        f"Sólo {len(columnas())} columnas de '{TABLA}' (mínimo {MINIMO_COLUMNAS}). "
        "El parseo de schema.sql se rompió: sin esto el barrido pasa en el vacío."
    )
    assert len(campos()) >= MINIMO_CAMPOS, (
        f"Sólo {len(campos())} campos en CandidatoResponse (mínimo {MINIMO_CAMPOS})."
    )


def test_el_select_sigue_siendo_estrella() -> None:
    """La PREMISA del barrido, anclada: el repo lee con `select("*")`, así que la fila llega
    entera y lo único que puede perder una columna es el mapper o el schema.

    Si alguien angostara el select a una lista de columnas, este barrido seguiría en verde
    mientras el dato deja de viajar — y estaría midiendo contra una tabla que ya no es lo que
    el repo trae. En ese caso lo correcto es cambiar la fuente de columnas por el select, no
    borrar este test.
    """
    fuente = inspect.getsource(repo_mod)
    assert 'select("*")' in fuente, (
        "candidato_repo dejó de leer con select(\"*\"): la premisa de este barrido cambió."
    )


# ── El barrido, en las dos direcciones ────────────────────────────────────────

def test_toda_columna_esta_expuesta_o_declarada() -> None:
    """🔴 EL BARRIDO. Ninguna columna puede quedar sin decisión.

    Es la generalización del bug de `estado`: la columna viajaba en cada fila, el mapper la
    tiraba, y no había un solo lugar del repo donde eso fuera visible.

    ¿Qué tendría que ser distinto para que falle? Nada del test: falla sola en cuanto una
    columna nueva aparece sin exponerse ni declararse. Con `estado` sacada del schema, rojea acá.
    """
    declarados = campos()
    huerfanas = sorted(
        col for col in columnas()
        if RENOMBRADAS.get(col, col) not in declarados and col not in NO_EXPUESTAS
    )
    assert not huerfanas, (
        f"Columnas de '{TABLA}' que el select TRAE y nadie usa ni declaró:\n  "
        + "\n  ".join(huerfanas)
        + "\nExponela en CandidatoResponse (y mapeala en _crow), o declarala en "
          "NO_EXPUESTAS CON su razón."
    )


def test_todo_campo_corresponde_a_una_columna() -> None:
    """La dirección contraria: un campo sin columna detrás siempre vale su default.

    No es simetría de adorno. Un campo así se ve igual que uno que funciona —la API lo devuelve,
    el front lo pinta— y muestra vacío para siempre, sin error. Es el mismo modo de falla que el
    de la columna descartada, con el signo cambiado.
    """
    reales = columnas() | set(RENOMBRADAS.values())
    sin_respaldo = sorted(c for c in campos() if c not in reales)
    assert not sin_respaldo, (
        f"Campos de CandidatoResponse que no corresponden a ninguna columna de '{TABLA}':\n  "
        + "\n  ".join(sin_respaldo)
        + "\nUn campo así devuelve su default para siempre, sin error y sin aviso."
    )


def test_ninguna_excepcion_esta_muerta() -> None:
    """Una declaración que apunta a una columna borrada es ruido que tapa el próximo caso.

    Molde: la misma guarda de `test_paridad_list_export` sobre `_EXPORTS_SIN_LISTADO`.

    ¿Qué tendría que ser distinto para que falle? Que se borre una columna de la tabla y nadie
    saque su línea del helper.
    """
    muertas = sorted((set(NO_EXPUESTAS) | set(RENOMBRADAS)) - columnas())
    assert not muertas, (
        f"Declaraciones que apuntan a columnas inexistentes en '{TABLA}': {muertas}"
    )


def test_toda_no_expuesta_tiene_razon_de_verdad() -> None:
    """La razón es el contenido del inventario, no un campo a completar con cualquier cosa.

    Sin el porqué, la próxima persona borra una entrada porque "no se usa" y revive el bug que
    este barrido existe para impedir.
    """
    flojas = sorted(c for c, r in NO_EXPUESTAS.items() if len(r.strip()) < 40)
    assert not flojas, f"Estas declaraciones no explican nada: {flojas}"

"""
Las listas de estado del Panel de Procesos son el CHECK completo de su tabla, ni de más ni de
menos.

## Qué clase de bug cierra

`procesos_service._ESTADOS` declaraba `("en_revision", "En revisión")` para `vacantes`, y
`en_revision` **no existe en `vacantes_estado_check`** (`nueva | en_proceso | con_candidatos |
cerrada`). No es una fila de más que molesta a la vista: `_build_proceso` calcula
`total = sum(...)` sobre los estados DECLARADOS, así que la categoría inventada aportaba 0 para
siempre y —peor— las dos que faltaban, `en_proceso` y `con_candidatos`, dejaban fuera del total
justo las búsquedas vivas. El panel decía que había menos vacantes de las que hay.

Medido contra el catálogo el 18/8/2026, estaba mal en **TRES de las cinco tablas**:
`vacantes` (una inventada + dos faltantes), `onboarding_instancias` (faltaba `pendiente`) y
`offboarding_instancias` (faltaba `en_proceso`).

## 🔴 POR QUÉ NINGÚN BARRIDO LO CAZÓ, Y POR QUÉ ESTE TEST NO ES UNA EXTENSIÓN DE AQUÉL

`_barrido_estado.py` no mira este módulo — y su línea 176 lo dice al revés de como se lee: nombra
`el == "cerrada" de vacantes` como ejemplo de lo que su filtro **descarta**, porque ese barrido
cubre `empleados.estado` y nada más (`ESTADOS_CHECK` son los cinco valores de
`empleados_estado_check`).

Pero aunque cubriera todas las tablas, **seguiría sin ver esto**: busca COMPARACIONES —
`.eq/.neq/.in_("estado", X)` sobre el builder, `==`/`!=` en Python, kwargs `estado=`— y acá no
hay ninguna. `_ESTADOS` es una estructura de datos de nivel de módulo; el valor llega a la query
como una VARIABLE (`.eq("estado", estado)` dentro de un for), así que del lado del AST no hay
literal que mirar y del lado de la tabla `_tabla_de` devuelve `INDETERMINADA`.

**¿Se puede generalizar a "toda lista de literales de estado contra su CHECK"? Se midió, y no.**
El problema no es detectar las listas: es saber a qué TABLA pertenece cada una. Un barrido que
contraste contra la UNIÓN de los 11 CHECK da **5 falsos positivos sobre 6 estructuras**, porque
en la misma estructura conviven el valor y su etiqueta humana (`_ESTADO_LABEL` mapea
`"cerrada" → "Cerrada"`, y "Cerrada" no está en ningún CHECK ni tiene por qué estar). Distinguir
uno de otro exige conocer la forma de cada estructura, que difiere por módulo — o sea, escribir
un test por módulo, que es exactamente esto.

**Acá sí se puede, y por un motivo que no se generaliza: `_ESTADOS` está indexado POR NOMBRE DE
TABLA.** La tabla no hay que adivinarla, es la clave del dict. Eso convierte un problema
indecidible en una comparación directa, y por eso este test cubre las CINCO tablas del panel y
no sólo la que estaba rota. La generalización queda anotada en `docs/DEUDA-TECNICA.md`.
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

import services.procesos_service as proc_mod  # noqa: E402
from services.procesos_service import _ESTADOS, ProcesosService  # noqa: E402
from tests._checks_estado import valores_check  # noqa: E402

# Guarda contra el falso verde: hoy el panel cubre 5 tablas.
_MINIMO_TABLAS = 5

# 🔴 PADRÓN. Estos dos estados NO tenían fixture en ningún test del repo antes de esta tanda —
# es el mismo agujero de padrón que A2 y A3—, y no es casualidad: eran justamente los que el
# panel no declaraba. Un estado que nadie cuenta es un estado que nadie testea.
_FILAS = {
    ("vacantes", "nueva"): 2,
    ("vacantes", "en_proceso"): 3,
    ("vacantes", "con_candidatos"): 4,
    ("vacantes", "cerrada"): 1,
}


# ── El barrido: las cinco listas contra los CHECK reales ──────────────────────

def test_la_derivacion_encuentra_algo() -> None:
    """GUARDA CONTRA EL FALSO VERDE, y acá tiene una razón concreta.

    `valores_check` devuelve `None` cuando el regex no matchea, y el CHECK viene en DOS formatos
    distintos según el tipo de la columna. Si el lector se rompiera para un formato, esas tablas
    saldrían como "sin CHECK que contrastar" y el barrido las saltearía EN VERDE.
    """
    assert len(_ESTADOS) >= _MINIMO_TABLAS
    sin_check = sorted(t for t in _ESTADOS if valores_check(t) is None)
    assert not sin_check, (
        f"No se pudo leer el CHECK de {sin_check} — el barrido las estaría salteando en verde."
    )


@pytest.mark.parametrize("tabla", sorted(_ESTADOS))
def test_ningun_estado_declarado_es_inventado(tabla: str) -> None:
    """🔴 EL BARRIDO, dirección 1. Un estado que no está en el CHECK cuenta 0 para siempre.

    Con `en_revision` reinstalado en `vacantes`, rojea acá.
    """
    declarados = {e for e, _ in _ESTADOS[tabla]}
    inventados = sorted(declarados - valores_check(tabla))
    assert not inventados, (
        f"'{tabla}' declara estados que su CHECK no acepta: {inventados}. "
        "Cuentan 0 para siempre y el panel muestra una fila que no puede tener datos."
    )


@pytest.mark.parametrize("tabla", sorted(_ESTADOS))
def test_no_falta_ningun_estado_del_check(tabla: str) -> None:
    """🔴 EL BARRIDO, dirección 2 — y es la que más caro salía.

    Un estado que falta no deja un hueco visible: **se cae del `total` del proceso**, porque el
    total es la suma de los declarados. El panel dice un número más chico y nada avisa.
    """
    declarados = {e for e, _ in _ESTADOS[tabla]}
    faltantes = sorted(valores_check(tabla) - declarados)
    assert not faltantes, (
        f"'{tabla}' no declara {faltantes}: esas filas no se cuentan en NINGÚN bucket y "
        "quedan fuera del total del proceso."
    )


@pytest.mark.parametrize("tabla", sorted(_ESTADOS))
def test_cada_estado_tiene_su_etiqueta_en_castellano(tabla: str) -> None:
    """La etiqueta es lo que se ve en pantalla: no puede ser el valor crudo ni estar vacía."""
    crudos = sorted(e for e, lbl in _ESTADOS[tabla] if not lbl.strip() or lbl == e)
    assert not crudos, f"'{tabla}' muestra el valor crudo en vez de una etiqueta: {crudos}"


# ── El panel, funcionando ─────────────────────────────────────────────────────

class _FakeQuery:
    """Cuenta según `_FILAS`. Honra `.eq()` — si ignorara el estado, todos los buckets darían
    el mismo número y el test no podría desmentir que cada uno cuenta lo suyo."""

    def __init__(self, tabla: str) -> None:
        self._tabla, self._estado = tabla, None

    def select(self, *a, **k) -> "_FakeQuery":
        return self

    def eq(self, columna: str, valor) -> "_FakeQuery":
        if columna == "estado":
            self._estado = valor
        return self

    def is_(self, *a) -> "_FakeQuery":
        return self

    def execute(self):
        class _Res:
            count = _FILAS.get((self._tabla, self._estado), 0)
        return _Res()


class _FakeSupabase:
    def table(self, nombre: str) -> _FakeQuery:
        return _FakeQuery(nombre)


@pytest.fixture
def panel(monkeypatch):
    monkeypatch.setattr(proc_mod, "supabase_admin", _FakeSupabase())
    resumenes = ProcesosService().get_procesos().procesos
    return {r.tabla: r for r in resumenes}


def test_vacantes_devuelve_las_cuatro_categorias(panel) -> None:
    """Las cuatro del CHECK, en el orden del pipeline. Antes eran tres, y una no existía."""
    assert [e.estado for e in panel["vacantes"].estados] == [
        "nueva", "en_proceso", "con_candidatos", "cerrada",
    ]


def test_una_vacante_con_candidatos_aparece_en_su_grupo(panel) -> None:
    """El caso que el panel no podía mostrar: `con_candidatos` ni siquiera era una categoría."""
    por_estado = {e.estado: e.total for e in panel["vacantes"].estados}
    assert por_estado["con_candidatos"] == 4
    assert por_estado["en_proceso"] == 3


def test_el_total_incluye_las_dos_etapas_que_faltaban(panel) -> None:
    """🔴 LA MEDICIÓN DEL BUG. Con las tres categorías viejas el total daba 3 (2 nuevas + 1
    cerrada, porque `en_revision` siempre cuenta 0). Con el CHECK completo da 10.

    Es la diferencia entre "el panel muestra una fila vacía" y "el panel miente sobre cuántas
    búsquedas hay", que es lo que en realidad estaba pasando.
    """
    assert panel["vacantes"].total == 10

"""
🔴 BARRIDO ESTRUCTURAL — CLAUDE.md no puede afirmar un número que el repo desmiente.

## Por qué existe

CLAUDE.md se lee al empezar cada sesión y **ninguna lo corrige**: actualizarlo compite con la
tarea real y siempre pierde. Nadie abre un documento de 1100 líneas a mitad de un bugfix para
remedir quince conteos que no tienen que ver con lo que está arreglando. El resultado, medido:
la suite del front decía **746 tests en 63 archivos** cuando eran **889 en 73**, la cantidad de
migraciones decía 121 cuando `migrations/` tiene 119 archivos, y la de archivos de test apareció
escrita de tres formas distintas **dentro del mismo documento**.

Es la cuarta corrección a mano de los mismos números en un mes. Este barrido no corrige nada:
**hace imposible cerrar en verde una sesión que dejó un número mintiendo.**

## 🔴 El diseño: falla por DIVERGENCIA, y también por NO PODER MEDIR

El modo de falla que este repo ya pagó cuatro veces este mes (el grep de `model_dump`, el de
`_validar_columna`, el barrido de estado, el de escrituras) es siempre el mismo: **el control
no encuentra lo que buscaba y pasa en verde**, porque "cero coincidencias" y "cero problemas"
se escriben igual. Acá eso está cerrado por construcción:

  · Si una frase ancla NO se encuentra, el test **falla diciendo qué ancla no pudo medir** — no
    la saltea. Reescribir la oración que contiene el número es legítimo; hacerlo sin que el
    barrido la vuelva a encontrar, no.
  · Si la misma afirmación aparece **varias veces con valores distintos**, falla nombrando los
    valores. Es literalmente lo que pasó con los archivos de test: tres cifras conviviendo.
  · Las anclas son una TABLA con guarda de mínimo. Si el parseo se rompiera entero, el barrido
    encontraría 0 anclas y la guarda lo caza antes de comparar nada.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
  · Cambiar un número de CLAUDE.md sin tocar el repo → rojo, nombrando el ancla, el valor
    declarado y el medido. Verificado en las dos direcciones al escribirlo.
  · Romper la frase que contiene el número → rojo por "no encontré ninguna afirmación".
  · Agregar un barrido nuevo sin anotarlo en la lista de CLAUDE.md → rojo (ver la última clase).

## Tolerancias, y por qué no son cero en todos lados

Un conteo de archivos se mide exacto y se escribe exacto: tolerancia 0. Los totales de la suite
suben en cada sesión que agrega tests, y exigir igualdad exacta convertiría este barrido en un
peaje de cada commit — que es como se muere un control. Llevan una tolerancia declarada, holgada
para el ruido de una sesión y estrecha para una mentira: la brecha real que motivó esto (746 vs
889, 143 tests) rojea por cinco veces la tolerancia.
"""

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pytest

RAIZ = Path(__file__).resolve().parents[2]
BACKEND = RAIZ / "backend"
FRONTEND = RAIZ / "frontend"
CLAUDE_MD = (RAIZ / "CLAUDE.md").read_text(encoding="utf-8")


def _py(carpeta: str) -> int:
    return len(list((BACKEND / carpeta).glob("*.py")))


def _tests_front() -> int:
    return len([p for p in FRONTEND.rglob("*.test.ts*") if "node_modules" not in p.parts])


@dataclass(frozen=True)
class Ancla:
    """Una afirmación numérica de CLAUDE.md, con cómo encontrarla y cómo medirla de verdad.

    patrones: se buscan TODOS. La unión de sus coincidencias es lo que el documento afirma; si
    la unión queda vacía, el ancla no se pudo medir y eso es un fallo, no un salteo.
    """

    nombre: str
    patrones: tuple[str, ...]
    medir: Callable[[], int]
    porque: str
    tolerancia: int = 0
    grupo: int = 1


ANCLAS: tuple[Ancla, ...] = (
    Ancla("archivos en backend/routers/", (r"routers/[^\n]{0,40}?(\d+) archivos",),
          lambda: _py("routers"), "el árbol de la sección Estructura"),
    Ancla("archivos en backend/services/ (nivel 1)", (r"services/[^\n]{0,60}?(\d+) archivos de lógica",),
          lambda: _py("services"), "el árbol de la sección Estructura"),
    Ancla("archivos en backend/services/ con submódulos", (r"\((\d+) con submódulos",),
          lambda: len(list((BACKEND / "services").rglob("*.py"))), "export/, mailer/ y reportes/ incluidos"),
    Ancla("archivos en backend/repositories/", (r"repositories/[^\n]{0,40}?(\d+) archivos",),
          lambda: _py("repositories"), "el árbol de la sección Estructura"),
    Ancla("archivos .sql en backend/migrations/", (r"migrations/[^\n]{0,40}?(\d+) archivos SQL",
                                                   r"Migraciones y salud de base\.\*{0,2}\s*(\d+) archivos SQL"),
          lambda: len(list((BACKEND / "migrations").glob("*.sql"))),
          "🔴 NO es el número de la última migración: 075-077 viven en migracionAWS/ y 000_run_all "
          "existe, así que 'la última es la 121' y 'hay 121 archivos' son dos cosas distintas"),
    Ancla("CREATE TABLE en backend/db/schema.sql", (r"schema\.sql[^\n]{0,80}?\((\d+) tablas",),
          lambda: len(re.findall(r"(?mi)^CREATE TABLE", (BACKEND / "db" / "schema.sql").read_text(encoding="utf-8"))),
          "el documento de reconstrucción; producción puede driftear y eso se verifica aparte"),
    Ancla("archivos .py en backend/tests/", (r"(\d+) archivos \.py:", r"(\d+) archivos `\.py` en total"),
          lambda: len(list((BACKEND / "tests").glob("*.py"))), "tests + helpers"),
    Ancla("archivos test_*.py en backend/tests/", (r"(\d+)\s+(?:archivos\s+)?`test_\*\.py`",),
          lambda: len(list((BACKEND / "tests").glob("test_*.py"))), "los que pytest colecta"),
    Ancla("helpers _*.py en backend/tests/", (r"(\d+) helpers",),
          lambda: len(list((BACKEND / "tests").glob("_*.py"))),
          "código de apoyo: NO están exentos del límite de 200"),
    Ancla("archivos de test del front", (r"(\d+) tests en (\d+) archivos",),
          _tests_front, "*.test.ts y *.test.tsx fuera de node_modules", grupo=2),
)


def _declarado(ancla: Ancla) -> list[int]:
    """Todos los valores que CLAUDE.md afirma para este ancla, en orden de aparición."""
    vistos: list[int] = []
    for patron in ancla.patrones:
        for m in re.finditer(patron, CLAUDE_MD):
            vistos.append(int(m.group(ancla.grupo)))
    return vistos


class TestLasAnclasSeEncuentran:
    def test_hay_anclas(self):
        # Guarda contra el falso verde: con la tabla vacía todo lo de abajo pasaría sin comparar.
        assert len(ANCLAS) >= 10

    @pytest.mark.parametrize("ancla", ANCLAS, ids=lambda a: a.nombre)
    def test_la_afirmacion_sigue_estando(self, ancla: Ancla):
        """Si nadie encuentra el número, el barrido NO puede pasar: diría 'todo bien' sin mirar."""
        assert _declarado(ancla), (
            f"No encontré en CLAUDE.md ninguna afirmación sobre «{ancla.nombre}».\n"
            f"Patrones probados: {ancla.patrones}\n"
            f"Medido hoy en el repo: {ancla.medir()} ({ancla.porque}).\n"
            "Si reescribiste la frase, actualizá el patrón de este ancla en la MISMA sesión: "
            "un ancla que no matchea es un control apagado, no un control que pasa."
        )

    @pytest.mark.parametrize("ancla", ANCLAS, ids=lambda a: a.nombre)
    def test_el_documento_no_se_contradice_a_si_mismo(self, ancla: Ancla):
        """Tres cifras distintas para lo mismo dentro del mismo archivo: pasó de verdad."""
        valores = set(_declarado(ancla))
        assert len(valores) <= 1, (
            f"CLAUDE.md afirma «{ancla.nombre}» con valores distintos en distintos lugares: "
            f"{sorted(valores)}. Elegí uno (el medido: {ancla.medir()}) y corregí TODOS."
        )


class TestLoDeclaradoCoincideConLoMedido:
    @pytest.mark.parametrize("ancla", ANCLAS, ids=lambda a: a.nombre)
    def test_el_numero_es_el_real(self, ancla: Ancla):
        declarado = _declarado(ancla)
        assert declarado, f"«{ancla.nombre}» no se pudo medir (ver el test de arriba)"
        real = ancla.medir()
        assert abs(declarado[0] - real) <= ancla.tolerancia, (
            f"CLAUDE.md dice {declarado[0]} para «{ancla.nombre}» y el repo tiene {real} "
            f"(tolerancia {ancla.tolerancia}). {ancla.porque}. Corregilo en CLAUDE.md."
        )


class TestLaSuiteDelBackend:
    """El total de la suite se mide con la sesión de pytest que está corriendo. Gratis y exacto."""

    def test_el_total_declarado_es_el_real(self, request):
        recolectados = len(request.session.items)
        if recolectados < 1000:
            # Corrida parcial (`pytest tests/test_x.py`). Fallar acá haría que trabajar sobre un
            # solo archivo esté siempre en rojo, y un control que grita se apaga. El skip es
            # VISIBLE en la salida de pytest; la corrida completa —la que se usa para cerrar una
            # sesión— siempre lo evalúa.
            pytest.skip(f"corrida parcial ({recolectados} tests): el total solo se mide entero")
        declarados = [int(m.group(1)) for m in re.finditer(r"Backend: \*{0,2}(\d+) passed", CLAUDE_MD)]
        assert declarados, "No encontré 'Backend: N passed' en CLAUDE.md"
        assert len(set(declarados)) == 1, f"CLAUDE.md declara varios totales de backend: {declarados}"
        assert abs(declarados[0] - recolectados) <= 80, (
            f"CLAUDE.md dice {declarados[0]} tests de backend y pytest colectó {recolectados}."
        )


# ─── La lista de barridos ─────────────────────────────────────────────────────
# Se parsea la lista numerada de la sección "Tests" de CLAUDE.md. Tres comprobaciones, y la
# tercera es la que más rinde: un barrido nuevo que nadie anotó sale a la luz solo.
_LISTA = re.search(r"Son \*{0,2}(\d+) barridos estructurales.*?(?=\n> ⚠️)", CLAUDE_MD, re.S)
_RE_ARCHIVO = re.compile(r"`((?:tests/|frontend/)[\w/\.\-]+\.(?:py|tsx?))`")


def _archivos_listados() -> list[str]:
    return [] if _LISTA is None else _RE_ARCHIVO.findall(_LISTA.group(0))


def _con_marcador() -> list[Path]:
    salida = []
    for base, patrones in ((BACKEND / "tests", ("test_*.py",)), (FRONTEND, ("*.test.ts", "*.test.tsx"))):
        for patron in patrones:
            for p in base.rglob(patron):
                if "node_modules" in p.parts:
                    continue
                if "barrido estructural" in p.read_text(encoding="utf-8").lower():
                    salida.append(p)
    return salida


class TestLaListaDeBarridos:
    def test_la_lista_existe(self):
        assert _LISTA is not None, "No encontré la lista numerada de barridos en CLAUDE.md"
        assert len(_archivos_listados()) >= 15, "La lista se encontró pero no se pudo parsear"

    def test_el_total_declarado_coincide_con_la_lista(self):
        """Y la numeración tiene que ser 1..N corrida: la lista ya convivió con dos numeraciones."""
        assert _LISTA is not None
        declarado = int(_LISTA.group(1))
        # Los ítems 6-10 viven en una sola línea separados por "·", así que no alcanza con
        # buscar principio de línea. Se compara el CONJUNTO contra 1..N, no la cantidad: así
        # un número repetido o salteado también rojea.
        numeros = {int(n) for n in re.findall(r"(?m)(?:^\s{0,4}|·\s+)(\d{1,2})\.\s", _LISTA.group(0))}
        assert numeros == set(range(1, declarado + 1)), (
            f"CLAUDE.md dice {declarado} barridos y su lista enumera {sorted(numeros)}."
        )

    def test_todo_archivo_nombrado_existe(self):
        faltan = [a for a in _archivos_listados()
                  if not (RAIZ / ("backend/" + a if a.startswith("tests/") else a)).exists()]
        assert faltan == [], f"La lista de barridos nombra archivos que ya no existen: {faltan}"

    def test_todo_barrido_del_repo_esta_en_la_lista(self):
        """🔑 La dirección que más rinde: un barrido nuevo sin anotar queda a la vista."""
        listados = {a.split("/")[-1] for a in _archivos_listados()}
        sueltos = sorted(p.name for p in _con_marcador() if p.name not in listados)
        assert sueltos == [], (
            "Estos archivos se declaran BARRIDO ESTRUCTURAL y no están en la lista de CLAUDE.md: "
            f"{sueltos}. Agregalos a la lista (y corregí el total) en la MISMA sesión."
        )

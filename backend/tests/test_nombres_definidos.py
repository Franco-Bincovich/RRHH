"""
BARRIDO ESTRUCTURAL — ningún nombre usado en el backend puede estar sin definir.

## La clase de error que cierra, y por qué la suite sola no la ve

Un nombre libre —usado y nunca definido ni importado— **no falla al importar el módulo**: falla
recién cuando esa línea se ejecuta. Si el camino que la ejecuta no está cubierto, la suite entera
puede estar en verde con un `NameError` esperando.

Pasó DOS veces en la misma sesión (8/8/2026), y ninguna la vio ningún test:

  1. `repositories/_ausencia_row.py` usaba `_TA`, que al dividir el repo (mig 088) quedó en
     `ausencias_repo`. `_build` reventaba con **cualquier lista de filas no vacía** — pero
     `solicitudes_ausencia` tiene 0 filas en producción y la suite solo lo llamaba con `[]`, así
     que el `if not rows: return []` cortaba antes de llegar. Ver `test_ausencia_row.py`.
  2. `services/gmail_service.py` conservaba `user_id` en un `logger.error` después de que el
     parámetro se sacara de la firma: un `NameError` **dentro del handler de error**, o sea en el
     único camino que se recorre cuando ya algo salió mal.

Los dos son el mismo error y el mismo modo de falla: código correcto a la vista, inalcanzable
para los tests, y una bomba con temporizador puesto en "cuando haya datos reales".

## 🔴 POR QUÉ ESTE BARRIDO LLAMA A RUFF EN VEZ DE REIMPLEMENTARLO

Resolver "¿este nombre está definido?" bien exige un análisis de scopes completo —comprensiones,
closures, `global`/`nonlocal`, imports condicionales, `TYPE_CHECKING`—. Ruff ya lo hace y lo hace
mejor de lo que saldría acá; una segunda implementación tendría falsos positivos que alguien
terminaría silenciando, y un barrido que se silencia deja de barrer.

Lo que este archivo agrega NO es la detección: es que **corra sola**. `ruff check` es un comando
aparte que hay que acordarse de tipear; los otros seis barridos del repo valen porque están en
`pytest -q`. Esto los iguala.

## 🔴 LAS DOS GUARDAS CONTRA EL FALSO VERDE

**(1) Si ruff falta, esto FALLA — no se saltea.** `requirements-dev.txt` documenta con nombre y
apellido lo que cuesta lo contrario: sin `pytest-asyncio`, 61 tests `async def` se salteaban **en
silencio** y la suite dependía de qué tenía instalado cada máquina. Un `pytest.skip` acá
reproduciría exactamente eso: verde en la máquina sin ruff, y nadie mirando. Por eso ruff está
pineado en `requirements-dev.txt` y la ausencia es un rojo con instrucciones.

**(2) Se verifica CUÁNTOS archivos miró.** `ruff check ./ruta_que_no_existe` responde
**"All checks passed!" y sale con 0** — comprobado. O sea: un barrido mal apuntado, un `exclude`
nuevo o un cambio de layout darían verde sin haber leído un solo archivo. `_MINIMO_ARCHIVOS` es lo
que convierte ese silencio en un rojo.

## Alcance

`F821` (nombre no definido) · `F822` (nombre inexistente en `__all__`) · `F823` (local usada antes
de asignarse). Las tres son la misma familia: **el nombre no existe cuando la línea corre**.
No se seleccionan más reglas a propósito — este barrido es sobre corrección, no sobre estilo, y
el repo NO está formateado con ruff (ver CLAUDE.md). Mezclar estilo acá lo volvería inmantenible.
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

import importlib.util  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
from functools import lru_cache  # noqa: E402
from pathlib import Path  # noqa: E402

_BACKEND = Path(__file__).resolve().parent.parent

# El nombre existe cuando la línea corre: las tres reglas de esa familia y ninguna de estilo.
_REGLAS = "F821,F822,F823"

# Guarda contra el falso verde. El backend ronda los 540 `.py` (sin venv, que ruff ya excluye por
# .gitignore). El mínimo va holgado: detecta "no miró nada" y "miró una carpeta", no un archivo
# de más o de menos. Subirlo a un número pegado al real haría fallar el barrido cada vez que
# alguien borra un módulo, que es ruido, no señal.
_MINIMO_ARCHIVOS = 400


def _ruff(*args: str) -> subprocess.CompletedProcess:
    """Corre ruff por `-m` y no por su binario: es lo único portable entre el venv de la Mac y
    el de Windows, donde el ejecutable vive en `Scripts/` y no en `bin/`."""
    return subprocess.run([sys.executable, "-m", "ruff", *args],
                          cwd=_BACKEND, capture_output=True, text=True)


@lru_cache(maxsize=1)
def _archivos_vistos() -> int:
    salida = _ruff("check", ".", "--show-files").stdout
    return len([ln for ln in salida.splitlines() if ln.strip().endswith(".py")])


def test_ruff_esta_instalado() -> None:
    """🔴 FALLA, NO SE SALTEA. Ver la guarda (1) del encabezado.

    ¿Qué tendría que ser distinto para que este test no sirva? Que fuera un `pytest.skip`: ahí
    la máquina sin ruff quedaría en verde sin haber barrido nada, que es el bug de los 61 tests
    `async def` con otra cara.
    """
    assert importlib.util.find_spec("ruff") is not None, (
        "ruff no está instalado en este venv y este barrido no puede correr.\n"
        "  pip install -r requirements-dev.txt\n"
        "NO se saltea a propósito: un skip acá dejaría pasar nombres sin definir sin que nadie "
        "se entere, que es exactamente lo que este archivo existe para impedir.")


def test_el_barrido_miro_los_archivos() -> None:
    """🔴 GUARDA CONTRA EL FALSO VERDE. `ruff check ./ruta_inexistente` dice "All checks passed!"
    y sale con 0: sin este conteo, un barrido apuntado a la nada pasaría igual."""
    vistos = _archivos_vistos()
    assert vistos >= _MINIMO_ARCHIVOS, (
        f"ruff solo vio {vistos} archivos (mínimo {_MINIMO_ARCHIVOS}). El barrido está mal "
        "apuntado o hay un exclude nuevo: sin esto, 'sin hallazgos' no significa nada.")


def test_no_hay_nombres_sin_definir() -> None:
    """EL BARRIDO. Un nombre libre es un `NameError` esperando a que alguien recorra esa línea.

    ¿Qué tendría que ser distinto para que falle? Nada del test: falla solo en cuanto aparezca un
    nombre sin definir en cualquier archivo del backend. Verificado por mutación devolviendo
    `_TA` a su estado de nombre libre.
    """
    proceso = _ruff("check", ".", "--select", _REGLAS, "--output-format=concise")
    hallazgos = [ln for ln in proceso.stdout.splitlines()
                 if any(f" {r} " in f" {ln} " for r in _REGLAS.split(","))]
    assert not hallazgos, (
        "Hay nombres usados y nunca definidos. NO fallan al importar: revientan cuando esa línea "
        "se ejecuta, y si el camino no está cubierto la suite no los ve.\n  "
        + "\n  ".join(hallazgos))

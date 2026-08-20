"""
🔴 EL CLIENTE REAL DE SUPABASE NO PUEDE CORRER BAJO TESTS. Falla ruidoso al primer uso.

## Qué problema resuelve, y por qué no alcanzaba con tener cuidado

La suite falsea la base **módulo por módulo**: cada test hace
`monkeypatch.setattr(<modulo>, "supabase_admin", fake)` sobre los módulos que consultan. Son
**71 archivos de test y ~172 sitios de parcheo**, y 22 de ellos parchean una LISTA A MANO de tres
o más módulos. Esa lista no puede saber que apareció un módulo nuevo.

**El día que se movió `dar_de_baja` de `_empleado_write_repo.py` a `_empleado_baja_repo.py`
(20/8/2026), su módulo quedó fuera de la lista de `test_offboarding_baja_efectiva.py`.** El
efecto no fue un fake incompleto ni un `AttributeError`: fue el **cliente real**, con `httpx`
saliendo a la red. Murió en `getaddrinfo failed` por casualidad — la máquina no resuelve el host.

🔴 **En una máquina con red y el `.env` cargado, ese test escribe `estado='baja'` en la base de
producción.** No es hipotético: los archivos de test llenan las credenciales con
`os.environ.setdefault(...)`, o sea **solo si nadie las puso antes**. En una sesión con el `.env`
exportado, ganan las reales, y `supabase_admin` usa la `service_key`, que bypasea RLS.

## Qué hace esto

Convierte ese modo de falla —silencioso, dependiente del DNS y potencialmente destructivo— en un
**error inmediato que nombra el archivo y la línea que pidieron el cliente**, para que quien lo
vea sepa exactamente qué sumarle al fixture. La lista a mano sigue existiendo; lo que cambia es
que desactualizarla ya no puede terminar en la base.

## Cómo detecta que está bajo tests

Dos condiciones, cualquiera alcanza:

  · **`settings.app_env == "test"`** — el interruptor explícito.
  · **`"pytest" in sys.modules`** — el que NO depende de que nadie se acuerde de nada, y por eso
    es el que importa. `pytest` vive en `requirements-dev.txt` y **no está en
    `requirements.txt`**, así que en producción nunca está importado. Verificado el 20/8/2026.

Un solo criterio no alcanzaba: con `APP_ENV` solo, la protección se apaga si alguien no exporta
la variable —que es exactamente la clase de olvido que este archivo existe para cubrir—, y con
`pytest` solo quedaría afuera cualquier arnés que no sea pytest.

## La salida de emergencia

`SUPABASE_REAL_EN_TESTS=1` desactiva el guard. Existe para un E2E real contra un proyecto de
prueba (el de adjuntos está anotado como pendiente desde hace meses), y es a propósito una
variable de entorno y no un flag de código: tiene que costar ponerla y tiene que verse en el
comando que la usa.

⚠️ **Límite conocido, escrito para no venderlo de más:** esto levanta una excepción, así que
**un caller que se trague todo error se la traga también**. El caso vivo es
`utils/empresas_cache.py`, que es fail-open por diseño. Ahí el guard no avisa — pero tampoco
escribe nada, que es lo que este archivo viene a impedir.
"""
import os
import sys
from pathlib import Path
from typing import Optional

from config.settings import settings

_BACKEND = Path(__file__).resolve().parent.parent
_ESCAPE = "SUPABASE_REAL_EN_TESTS"


# La decisión se toma UNA VEZ por proceso y se cachea: el guard corre en cada eslabón de cada
# cadena (`table`, `select`, `eq`, `execute`…), o sea varias veces por query, y ni `app_env` ni la
# presencia de pytest cambian a mitad de un proceso. Bajo pytest la primera evaluación ocurre
# durante un test, con pytest importado desde mucho antes; en producción da False y no se
# vuelve a mirar.
_decision: Optional[bool] = None


def bajo_tests() -> bool:
    """¿Este proceso es una corrida de tests? Ver las dos condiciones en el encabezado."""
    global _decision
    if _decision is None:
        _decision = (not os.environ.get(_ESCAPE)
                     and (settings.app_env == "test" or "pytest" in sys.modules))
    return _decision


def _quien_lo_pidio() -> str:
    """El primer frame FUERA de `integrations/`, como `carpeta/archivo.py:linea`.

    Se saltea `integrations/` entero y no solo este archivo: entre el caller y acá está el
    `__call__` de `_MethodProxy`, que no le dice nada a nadie. Si no se encuentra
    ninguno —no debería—, devuelve un texto que lo diga en vez de mentir con una ruta.
    """
    frame = sys._getframe(1)
    while frame is not None:
        ruta = Path(frame.f_code.co_filename).resolve()
        if ruta.parent.name != "integrations":
            try:
                rel = ruta.relative_to(_BACKEND).as_posix()
            except ValueError:
                rel = ruta.as_posix()
            return f"{rel}:{frame.f_lineno}"
        frame = frame.f_back
    return "<no se pudo determinar el módulo>"


def abortar(atributo: str) -> None:
    """Levanta `RuntimeError` nombrando quién pidió el cliente real. Solo bajo tests.

    Args:
        atributo: la cadena de atributos que se estaba invocando (`table.insert.execute`,
            `storage.from_.upload`). Va en el mensaje porque distingue de un vistazo una
            consulta a una tabla de una subida a Storage.

    Raises:
        RuntimeError: siempre que `bajo_tests()`. Nunca en producción.
    """
    if not bajo_tests():
        return
    raise RuntimeError(
        f"🔴 CLIENTE REAL DE SUPABASE USADO BAJO TESTS — lo pidió {_quien_lo_pidio()} "
        f"(.{atributo}).\n"
        f"    Ese módulo NO está falseado: el test lo dejó fuera de su lista de "
        f"`monkeypatch.setattr(<modulo>, \"supabase_admin\", ...)`.\n"
        f"    Suele pasar cuando una función se MUEVE de archivo y la lista del fixture queda "
        f"vieja.\n"
        f"    Arreglo: sumá ese módulo al fixture del test que estás corriendo.\n"
        f"    (Si de verdad querés pegarle a la base real, corré con {_ESCAPE}=1 — pero mirá "
        f"antes a qué proyecto apunta SUPABASE_URL.)"
    )

"""
Maquinaria de introspección del barrido de IDs tipados. **Helper, no test.**

Lo consume `tests/test_ids_tipados.py`, donde viven el inventario declarado y las aserciones.

🔴 **EL CORTE ESTÁ AL REVÉS QUE EN `_columnas_candidatos.py`, Y ES A PROPÓSITO.** Allá el helper
se quedó con la tabla declarativa y el test con las aserciones. Acá no se puede: el inventario
son **92 entradas** y los helpers `tests/_*.py` **no están exentos del límite de 200 líneas**
(los `test_*.py` sí). Así que acá el helper se queda con la MAQUINARIA —que es estable y corta— y
la lista declarada se va al test, que es el archivo que puede crecer. Si algún día el inventario
baja a un tamaño que entre holgado, el corte puede volver a la forma del molde.

## Qué mide

Todo campo de un schema Pydantic cuyo nombre sea `id` o termine en `_id` y esté tipado `str`
(directo, `Optional[str]`, `List[str]` o cualquier anidado que resuelva a `str` sin `UUID`).

## Por qué la introspección y no un grep

Porque el grep no puede contestar la única pregunta que decide la gravedad: **¿es de entrada o de
salida?** Un `*Response` mal tipado no rompe el porteo —el mapper castea el `UUID` que devuelve
asyncpg y sigue—, pero un payload de escritura sí: asyncpg es estricto y un `str` contra una
columna `uuid` es un error de query, no una coerción. Esa distinción vive en el TIPO de la clase,
no en el texto de la línea, y por eso el control tiene que importar los módulos y mirar los
modelos, no leerlos como archivo. (El grep además no veía ni `Optional[str]` ni el `id` pelado —
ver `VERIFICACION-BACKEND.md` §11.)
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

import importlib  # noqa: E402
import pkgutil  # noqa: E402
import typing  # noqa: E402
from dataclasses import dataclass  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import List, Tuple  # noqa: E402
from uuid import UUID  # noqa: E402

from pydantic import BaseModel  # noqa: E402

import schemas  # noqa: E402

# Sufijos de clase que denotan un payload que VIAJA HACIA el backend. Todo lo demás se considera
# salida. `Filtros` entra acá aunque no escriba: sus valores también terminan en un WHERE.
ENTRADA_SUFIJOS: Tuple[str, ...] = ("Create", "Update", "Request", "Filtros", "Payload", "In")


@dataclass(frozen=True)
class Campo:
    """Un campo id tipado `str`, con de dónde salió y hacia dónde viaja."""

    modulo: str
    clase: str
    campo: str
    direccion: str  # "entrada" | "salida"

    @property
    def clave(self) -> str:
        """La forma canónica con la que el inventario lo declara: `modulo.Clase.campo`."""
        return f"{self.modulo}.{self.clase}.{self.campo}"


def _tipos_concretos(anotacion: object) -> List[object]:
    """Aplana una anotación a la lista de tipos concretos que la componen.

    `Optional[str]` → `[str]` · `List[str]` → `[str]` · `Optional[UUID]` → `[UUID]`.
    Se descarta `NoneType`: que un campo admita nulo no dice nada sobre si el id está bien tipado.
    """
    args = typing.get_args(anotacion)
    if not args:
        return [anotacion]
    out: List[object] = []
    for a in args:
        if a is type(None):
            continue
        out.extend(_tipos_concretos(a))
    return out


def es_id_str(anotacion: object) -> bool:
    """¿Este campo resuelve a `str` sin que aparezca `UUID` por ningún lado?

    La condición es "hay `str` y NO hay `UUID`" y no simplemente "hay `str`", para que un
    `Union[UUID, str]` —si algún día aparece— no se cuente como deuda: ahí el `UUID` ya viaja.
    """
    tipos = _tipos_concretos(anotacion)
    return str in tipos and UUID not in tipos


def _es_campo_id(nombre: str) -> bool:
    """`id` pelado o cualquier `*_id`. El `id` pelado es el que el grep viejo no veía."""
    return nombre == "id" or nombre.endswith("_id")


def direccion_de(clase: str) -> str:
    """Entrada si el nombre de la clase la delata como payload; salida en cualquier otro caso.

    El default es "salida" a propósito: equivocarse hacia salida subestima la gravedad de UNA
    entrada nueva, pero equivocarse hacia entrada llenaría la lista crítica de ruido y nadie la
    miraría. Si aparece un payload con un nombre que no termina en ninguno de los sufijos, lo
    correcto es agregar el sufijo acá, no declarar el campo como salida.
    """
    return "entrada" if clase.endswith(ENTRADA_SUFIJOS) else "salida"


def inventario() -> List[Campo]:
    """Todos los campos id tipados `str` de `schemas/`, por introspección de los modelos.

    Sólo se miran las clases DEFINIDAS en el módulo (`cls.__module__ == nombre`): sin ese filtro,
    un schema reimportado se contaría una vez por cada módulo que lo importa y el inventario
    dependería del orden de los imports.
    """
    filas: List[Campo] = []
    raiz = Path(schemas.__file__).parent
    for mod in pkgutil.iter_modules([str(raiz)]):
        nombre = f"schemas.{mod.name}"
        modulo = importlib.import_module(nombre)
        for attr in dir(modulo):
            cls = getattr(modulo, attr)
            if not (isinstance(cls, type) and issubclass(cls, BaseModel) and cls is not BaseModel):
                continue
            if cls.__module__ != nombre:
                continue
            for campo, info in cls.model_fields.items():
                if _es_campo_id(campo) and es_id_str(info.annotation):
                    filas.append(Campo(mod.name, cls.__name__, campo, direccion_de(cls.__name__)))
    return filas

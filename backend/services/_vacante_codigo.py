"""
El código de la búsqueda: normalizarlo y garantizar que no se repita.

## 🔴 LO ESCRIBE CAPITAL HUMANO — ANTES LO EMITÍA UNA SECUENCIA

Hasta la migración 122 el código era `VAC-0001` y lo ponía un DEFAULT de la base, así que era
único por construcción y nadie podía tipearlo mal. Ahora es un campo del formulario, y con eso
aparecen los dos modos de falla que este módulo cierra:

  1. **Dos búsquedas con el mismo código.** No falla con un error: hace que un CV entre a la
     búsqueda equivocada, o que el matcher no pueda desempatar y lo mande a revisión para
     siempre. **Es el único bug que rompe el matcher de CVs de forma irreparable**, porque el
     mail ya salió publicado con ese código.
  2. **Un código que el matcher no puede leer.** Espacios, tildes, `%`. El detalle de por qué
     cada carácter queda afuera está en `migrations/122_vacantes_codigo_manual.sql`.

## 🔴 DOS BARRERAS CONTRA LA REPETICIÓN, Y HACEN FALTA LAS DOS

  · **`asegurar_unico`** consulta antes de escribir. Existe para poder decir CUÁL es la búsqueda
    que ya tiene ese código: es lo único que le permite a Capital Humano resolverlo (ir a esa
    búsqueda y cambiarle el código, o elegir otro). Un "código duplicado" pelado los deja
    adivinando entre 5 búsquedas hoy y entre 200 el año que viene.
  · **`choque_de_codigo`** traduce el error del ÍNDICE ÚNICO de la base. Es la que realmente
    garantiza: entre el `SELECT` de la primera y el `INSERT`, otra sesión puede insertar el mismo
    código. Con una sola persona cargando búsquedas casi nunca se ve; con dos, aparece el día
    menos pensado. El chequeo previo es para el MENSAJE, el índice es para la GARANTÍA.

## ⚠️ EL MENSAJE NOMBRA LA VACANTE DUEÑA, INCLUSO SI ES DE OTRA EMPRESA

Y no es una fuga: la unicidad es GLOBAL (una sola casilla para todo el sistema, ver la 122), así
que el choque con otra sociedad del grupo es un caso normal y no poder nombrarlo dejaría al
usuario sin salida. Además, en este producto **todo usuario accede a todas las empresas** —
decisión de producto cerrada—, así que no hay nadie para quien ese nombre sea información nueva.
Por eso el mensaje incluye la empresa: es lo que dice a qué sociedad hay que cambiar de vista.
"""
import re
from typing import Optional

from utils.errors import AppError

CODIGO_DUPLICADO = "CODIGO_VACANTE_DUPLICADO"
CODIGO_INVALIDO = "CODIGO_VACANTE_INVALIDO"

# Espejo del CHECK `vacantes_codigo_formato` (migración 122). Si divergen, la base rechaza lo que
# la app aceptó y el alta muere con un 500 en vez de con el mensaje de acá.
_FORMA = re.compile(r"^[A-Z0-9]+(-[A-Z0-9]+)*$")
_SEPARADORES = re.compile(r"[\s._\-]+")
MIN_LARGO, MAX_LARGO = 3, 30

_AYUDA = ("Usá letras, números y guiones —por ejemplo ECO-2026—, entre "
          f"{MIN_LARGO} y {MAX_LARGO} caracteres y con al menos una letra.")


def normalizar(codigo: Optional[str]) -> str:
    """El código en su forma canónica: MAYÚSCULAS y un guion como único separador.

    `ECO 2026`, `eco_2026` y ` eco-2026 ` son la misma búsqueda y tienen que quedar guardados
    igual: el índice único ya es sobre `upper(codigo)`, así que no podían coexistir, pero sin
    normalizar la pantalla, el aviso y el export mostrarían la variante que le salió a quien lo
    cargó primero.

    Raises: CODIGO_VACANTE_INVALIDO (422) si queda vacío o no pasa la forma del CHECK.
    """
    limpio = _SEPARADORES.sub("-", (codigo or "").strip().upper()).strip("-")
    if not limpio:
        raise AppError(f"La búsqueda necesita un código de postulación. {_AYUDA}",
                       CODIGO_INVALIDO, 422)
    if not (MIN_LARGO <= len(limpio) <= MAX_LARGO) or not _FORMA.match(limpio) \
            or not re.search(r"[A-Z]", limpio):
        raise AppError(f"El código «{limpio}» no se puede usar. {_AYUDA}", CODIGO_INVALIDO, 422)
    return limpio


def _duplicado(codigo: str, dueña) -> AppError:
    """El error que dice QUÉ HACER: cuál es la búsqueda que ya tiene ese código y dónde está."""
    donde = f" de {dueña.empresa_nombre}" if getattr(dueña, "empresa_nombre", None) else ""
    return AppError(
        f"El código «{codigo}» ya lo usa la búsqueda «{dueña.titulo}»{donde}. "
        "Abrí esa búsqueda y cambiale el código, o elegí otro para ésta. "
        "Dos búsquedas con el mismo código harían que un CV entre a la equivocada.",
        CODIGO_DUPLICADO, 409)


def asegurar_unico(repo, codigo: str, *, excepto_id: Optional[str] = None) -> None:
    """Falla si otra búsqueda ya tiene ese código. `excepto_id` = la que se está editando.

    Sin `excepto_id`, guardar una vacante sin tocarle el código chocaría consigo misma.

    Raises: CODIGO_VACANTE_DUPLICADO (409).
    """
    dueña = repo.find_by_codigo(codigo)
    if dueña and str(dueña.id) != str(excepto_id or ""):
        raise _duplicado(codigo, dueña)


def choque_de_codigo(exc: BaseException, repo, codigo: str) -> Optional[AppError]:
    """El mismo 409 de arriba si `exc` es el índice único; `None` si el fallo fue otro.

    🔴 Devuelve en vez de levantar para que el caller pueda RELANZAR EL ORIGINAL cuando no es
    este caso: tragarse un fallo de base cualquiera detrás de "código duplicado" mandaría a
    Capital Humano a cambiar un código que estaba perfecto.

    El nombre del índice viene de la migración 097 y se busca en el texto del error porque es lo
    único que PostgREST devuelve del lado del cliente. Se vuelve a consultar quién es la dueña:
    en una carrera, la fila la acaba de escribir otra sesión.
    """
    if "vacantes_codigo_uq" not in str(exc):
        return None
    dueña = repo.find_by_codigo(codigo)
    if not dueña:
        # La ganó otra sesión y ya no está (o el lookup falló). Sin dueña no se puede nombrar,
        # pero el rechazo tiene que salir igual: lo que no se puede es crear la segunda.
        return AppError(f"El código «{codigo}» ya lo usa otra búsqueda. Elegí otro.",
                        CODIGO_DUPLICADO, 409)
    return _duplicado(codigo, dueña)

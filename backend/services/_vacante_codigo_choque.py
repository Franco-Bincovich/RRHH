"""
LA UNICIDAD del código de la búsqueda: que no haya dos iguales, y que el rechazo diga cuál es la
otra. La conversión a la forma canónica vive en `_vacante_codigo.py`.

## 🔴 LA UNICIDAD SE VERIFICA SOBRE EL CANÓNICO, NO SOBRE LO QUE TIPEARON

`_vacante_write` normaliza ANTES de llamar acá, así que `Lider de equipo` y `LIDER DE EQUIPO` son
el mismo código y el segundo se rechaza nombrando la búsqueda que ya lo tiene. La garantía final
no es ese chequeo sino el índice `vacantes_codigo_uq ON vacantes (upper(codigo))`, que ve lo
mismo: la columna guarda SIEMPRE el canónico, nunca el texto crudo. Verificado contra el catálogo
vivo el 26/8/2026 — el índice existe, es funcional sobre `upper(codigo)` y no lleva `empresa_id`.

## 🔴 DOS BARRERAS, Y HACEN FALTA LAS DOS

  · **`asegurar_unico`** consulta antes de escribir. Existe para poder decir CUÁL es la búsqueda
    que ya tiene ese código: es lo único que le permite a Capital Humano resolverlo. Un "código
    duplicado" pelado los deja adivinando entre 5 búsquedas hoy y entre 200 el año que viene.
  · **`choque_de_codigo`** traduce el error del ÍNDICE ÚNICO. Es la que realmente garantiza:
    entre el `SELECT` de la primera y el `INSERT` otra sesión puede escribir el mismo código. Con
    una sola persona cargando búsquedas casi nunca se ve; con dos, aparece el día menos pensado.
    **El chequeo previo es para el MENSAJE, el índice es para la GARANTÍA.**

## ⚠️ EL MENSAJE NOMBRA LA VACANTE DUEÑA, INCLUSO SI ES DE OTRA EMPRESA

Y no es una fuga: la unicidad es GLOBAL (una sola casilla de mails para todo el sistema, ver la
migración 122), así que el choque con otra sociedad del grupo es un caso normal y no poder
nombrarlo dejaría al usuario sin salida. Además, en este producto **todo usuario accede a todas
las empresas** —decisión de producto cerrada—, así que no hay nadie para quien ese nombre sea
información nueva. Por eso el mensaje incluye la empresa: es lo que dice a qué sociedad hay que
cambiar de vista para llegar a esa búsqueda.
"""
from typing import Optional

from utils.errors import AppError

CODIGO_DUPLICADO = "CODIGO_VACANTE_DUPLICADO"


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

    🔴 RECIBE EL CANÓNICO, no lo que tipearon. Consultar con el texto crudo dejaría entrar
    `LIDER DE EQUIPO` teniendo `LIDER-DE-EQUIPO` guardado: el `ilike` no encontraría nada y el
    choque lo cazaría recién el índice, sin poder nombrar a la dueña.

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

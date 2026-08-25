"""
Las validaciones de campo del módulo de objetivos: el responsable y la prioridad.

⚠️ La UNICIDAD no está acá: la hace el índice y su traducción a un 409 vive en
`_objetivos_duplicado.py`. Es otra clase de cosa —esto corre ANTES de escribir y mira un valor;
aquello traduce el error que la base devuelve DESPUÉS— y además no entraba: con ese bloque adentro
este archivo quedaba en 168 contra un tope de 150.

🔴 POR QUÉ NO HAY UN `ensure_tipo_valido`, y no es un olvido. `prioridad` es `str` en el schema,
así que sin `ensure_prioridad_valida` un valor fuera del enum llegaría al CHECK de la base y el
422 legible se convertiría en un 500 de Postgres. `tipo`, en cambio, es un `Literal` en
`ObjetivoCreate`/`ObjetivoUpdate`: **Pydantic lo rechaza antes de que exista el objeto**, y FastAPI
lo devuelve como 422 con el detalle del campo. Un validador acá sería código que no puede fallar
—el caso que cubriría es inalcanzable— y aparentaría una defensa que ya está una capa más arriba.
La asimetría es entre los dos SCHEMAS, no entre las dos validaciones.

Salió de `objetivo_service.py`, que estaba en 143/150 contra su límite. Molde:
`_objetivos_jerarquia.py`, que ya se había separado de ese mismo service por el mismo motivo y
con el mismo criterio — funciones `ensure_*` libres, que reciben lo que necesitan y levantan
`AppError`, sin estado ni `self`.

🔴 POR QUÉ SALIERON ESTAS DOS Y NO `exportar`, QUE ERA LA OTRA OPCIÓN.
`tests/test_limite_export.py::TestTodosLosExportsChequean::test_lo_invoca_en_el_export` lee el
CUERPO de `ObjetivoService.exportar` con `inspect.getsource` y exige encontrar ahí la llamada a
`verificar_limite_export(`. Un `exportar` convertido en delegador de una línea deja de contener
ese literal y **rojea el barrido**, que es exactamente lo que ese barrido existe para atrapar (un
export que nace sin control de filas). Mover la validación no toca ningún barrido.

📌 QUÉ CRECE ACÁ Y QUÉ NO. La `periodicidad` que viene es otro campo con vocabulario cerrado:
su `ensure_periodicidad_valida` entra en este archivo, en la forma exacta de la de prioridad, y
suma CERO líneas al service — que es el punto del corte. El service se queda con la orquestación
(qué se valida y en qué orden) y acá vive el cómo.
"""
from typing import Optional

from repositories.usuario_repo import UsuarioRepo
from schemas.objetivo import PRIORIDADES
from utils.errors import AppError


def ensure_responsable_valido(responsable_id: str) -> None:
    """Verifica que el responsable sea un user ACTIVO en `users` (no en `empleados`).

    🔴 Contra `users` y no contra `empleados`: este tablero es de tareas del equipo de RRHH, no
    de los 31 empleados. Es decisión de producto cerrada — es la razón por la que la migración de
    `responsable_id` a empleados se canceló.

    Reusa `UsuarioRepo.get_estado`, que trae dos columnas de más; recortarlas tocaría a su otro
    caller. Los dos motivos de rechazo salen con codes DISTINTOS a propósito: acá no hay oráculo
    de enumeración que cuidar —los usuarios del sistema se ven todos en el selector—, así que
    decir cuál de las dos cosas pasó es información útil y no una fuga.

    Args:
        responsable_id: user id a validar, ya como string.

    Raises:
        AppError: RESPONSABLE_NO_VALIDO (422) si el id no existe en `users`.
        AppError: RESPONSABLE_NO_ACTIVO (422) si existe pero está dado de baja.
    """
    estado = UsuarioRepo().get_estado(responsable_id)
    if not estado:
        raise AppError("Responsable no encontrado en users", "RESPONSABLE_NO_VALIDO", 422)
    if not estado.get("activo"):
        raise AppError("El responsable no está activo", "RESPONSABLE_NO_ACTIVO", 422)


def ensure_responsables_validos(extras) -> None:
    """Valida la lista de responsables ADICIONALES con la MISMA función que el dueño.

    Existe porque `create` y `update` tenían este bucle escrito verbatim cada uno. No es
    deduplicación cosmética: la regla que sostiene —"un responsable inactivo se rechaza igual
    venga como dueño o como acompañante"— está declarada en el encabezado de `objetivo_service`,
    y dos copias del bucle son dos lugares donde esa regla puede dejar de cumplirse por separado.

    Args:
        extras: lista de user ids (UUID o str), o None. `None` y `[]` son ambos "nada que validar".

    Raises:
        AppError: RESPONSABLE_NO_VALIDO / RESPONSABLE_NO_ACTIVO (422), por cada id que falle.
    """
    for extra in (extras or []):
        ensure_responsable_valido(str(extra))


def ensure_prioridad_valida(prioridad: Optional[str], *, opcional: bool = False) -> None:
    """Verifica que la prioridad esté en el vocabulario cerrado `PRIORIDADES`.

    ⚠️ `opcional` NO es azúcar: distingue los dos call sites, que hoy se comportan distinto y
    tienen que seguir haciéndolo. En el ALTA la prioridad siempre tiene valor (el schema le pone
    `"media"` por default), así que un `""` explícito del cliente es un error y sale 422. En la
    EDICIÓN, en cambio, `None` significa "no la toques" y no se valida nada. Sin este parámetro,
    una versión única y tolerante dejaría pasar un `""` en el alta hasta el CHECK de la base, y
    ahí el 422 legible se convierte en un 500 de Postgres.

    Args:
        prioridad: valor a validar.
        opcional: True = un valor vacío o None se acepta como "sin cambio" (camino de update).

    Raises:
        AppError: PRIORIDAD_INVALIDA (422).
    """
    if opcional and not prioridad:
        return
    if prioridad not in PRIORIDADES:
        raise AppError(
            f"Prioridad inválida. Valores: {sorted(PRIORIDADES)}", "PRIORIDAD_INVALIDA", 422)

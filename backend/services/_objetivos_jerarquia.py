"""
La guarda de profundidad de los subobjetivos: máximo 2 niveles, padre → hijo, sin nietos.

Molde: `services/_tipos_jerarquia.py`, que resuelve exactamente el mismo problema para los
subtipos de ausencia (migración 088). Se copia el criterio, no el código: acá el "padre" es un
`ObjetivoResponse` con atributos, allá es un dict.

## 🔴 POR QUÉ LA GUARDA VIVE ACÁ Y NO EN UN CHECK DE LA BASE

Un CHECK de Postgres solo puede mirar LA FILA que se está escribiendo: no puede consultar el
`parent_id` del padre para saber si ese padre ya es hijo de otro. La única forma de hacerlo en
la base sería un trigger, y se descartó por dos razones: el error le llegaría al usuario como
texto crudo de Postgres en vez de un AppError legible, y este repo dropeó todos sus triggers de
lógica en la migración 058 justamente para no tener reglas de negocio escondidas en la base.

🚩 CONSECUENCIA ASUMIDA Y DICHA: alguien con acceso directo a la base PUEDE crear un nieto. No
es un agujero de seguridad —hace falta ser admin de la base— pero está escrito para que nadie
suponga que el modelo lo impide por construcción. Es la misma limitación declarada que arrastra
`_tipos_jerarquia.py`.

## Por qué profundidad 2 y no un árbol

Decisión de producto cerrada. Lo que cuesta permitir más: el kanban tendría que renderizar un
árbol con expandir/colapsar y estado por nodo en vez de una tarjeta con un badge, el listado
necesitaría indentación variable, y el borrado en cascada tendría que razonarse por niveles. Se
limita acá, en un solo lugar, y todo lo demás se escribe asumiendo dos niveles — incluido
`_objetivos_arbol.armar_arbol`, que por eso no recursiona.
"""
from typing import Optional

from utils.errors import AppError


def ensure_padre_valido(repo, parent_id, empresa_id=None, objetivo_id: Optional[str] = None):
    """Valida que `parent_id` pueda ser padre. Devuelve la fila del padre para reusarla.

    Se devuelve la fila (y no un bool) para que el caller no la consulte dos veces — mismo
    criterio que `ensure_empleado_de_empresa` y que `_tipos_jerarquia.ensure_padre_valido`.

    Args:
        repo: ObjetivoRepo (o doble) con `find_by_id`.
        parent_id: candidato a padre. None = objetivo raíz, no hay nada que validar.
        empresa_id: empresa del request. El padre se busca DENTRO de ella: colgar un objetivo
            de un padre de otra empresa cruzaría la frontera multiempresa por referencia.
        objetivo_id: el objetivo que se está creando o editando. None en un alta.

    Returns:
        La fila del padre, o None si `parent_id` es None.

    Raises:
        AppError: OBJETIVO_PADRE_NOT_FOUND (404) si el padre no existe o es de otra empresa.
        AppError: OBJETIVO_PADRE_ES_SI_MISMO (422) si un objetivo se apunta a sí mismo.
        AppError: OBJETIVO_JERARQUIA_PROFUNDA (422) si el padre YA es hijo de otro.
    """
    if parent_id is None:
        return None
    if objetivo_id and str(parent_id) == str(objetivo_id):
        raise AppError("Un objetivo no puede ser su propio padre",
                       "OBJETIVO_PADRE_ES_SI_MISMO", 422)

    padre = repo.find_by_id(str(parent_id), empresa_id)
    if not padre:
        # Mismo 404 para "no existe" y "es de otra empresa": un código distinto confirmaría
        # que el objetivo existe y es de otro (oráculo de enumeración).
        raise AppError("Objetivo padre no encontrado", "OBJETIVO_PADRE_NOT_FOUND", 404)

    # 🔴 LA GUARDA DE PROFUNDIDAD, en una línea: si el padre YA tiene padre, esto sería un
    # nieto. Con profundidad máxima 2 alcanza con mirar UN nivel; no hace falta recorrer nada.
    if padre.parent_id:
        raise AppError(
            "Ese objetivo ya es un subobjetivo: no se le pueden colgar otros. La jerarquía "
            "admite dos niveles (objetivo y subobjetivo).",
            "OBJETIVO_JERARQUIA_PROFUNDA", 422)
    return padre


def ensure_no_tiene_hijos(repo, objetivo_id, empresa_id=None) -> None:
    """Impide convertir en hijo a un objetivo que YA es padre de otros.

    Es la otra mitad de la profundidad 2, y `_tipos_jerarquia` no la necesita porque allá la
    edición de jerarquía no existe. Acá sí: sin esta guarda, editar un padre para colgarlo de
    otro convertiría a sus hijos en nietos DE UNA, sin pasar por `ensure_padre_valido` — la
    invariante se rompería desde el lado que nadie mira.

    Raises:
        AppError: OBJETIVO_JERARQUIA_PROFUNDA (422) si el objetivo tiene subobjetivos.
    """
    if repo.tiene_hijos(str(objetivo_id), empresa_id):
        raise AppError(
            "Ese objetivo tiene subobjetivos: no se puede colgar de otro. La jerarquía "
            "admite dos niveles (objetivo y subobjetivo).",
            "OBJETIVO_JERARQUIA_PROFUNDA", 422)

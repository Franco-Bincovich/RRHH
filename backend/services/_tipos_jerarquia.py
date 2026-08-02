"""
Las dos guardas de la jerarquía de tipos de ausencia: profundidad máxima 2 y anti-ciclos.

Molde: `services/_empleados_manager.ensure_no_ciclo_manager`, que resuelve el mismo problema
para el organigrama — y que en la sesión del 2/8/2026 se arregló para caminar SIN filtro de
empresa, porque acotar el recorrido hacía que un ciclo cruzado se colara. Acá el recorrido nunca
tuvo filtro, pero el molde de la caminata (subir por la cadena, `max_saltos` como red contra
datos ya corruptos, mismo tipo de AppError) es el mismo.

## 🔴 POR QUÉ LAS GUARDAS VIVEN ACÁ Y NO EN UN CHECK DE LA BASE

Un CHECK de Postgres solo puede mirar LA FILA que se está escribiendo: no puede consultar el
`padre_id` del padre para saber si ese padre ya es hijo de otro. La única forma de hacerlo en la
base sería un trigger, y se descartó por dos razones: el error le llegaría al usuario como texto
crudo de Postgres en vez de un AppError legible, y este repo dropeó todos sus triggers de lógica
en la migración 058 justamente para no tener reglas de negocio escondidas en la base.

Lo que SÍ quedó en la base es lo único que un CHECK puede expresar:
`tipos_ausencia_padre_no_es_si_mismo` (padre_id <> id), la autorreferencia directa.

🚩 Consecuencia asumida y dicha: alguien con acceso directo a la base PUEDE crear un nieto. No es
un agujero de seguridad —hace falta ser admin de la base— pero está escrito para que nadie
suponga que el modelo lo impide por construcción.

## Por qué profundidad 2 y no un árbol

Los archivos reales de RRHH tienen exactamente dos niveles ("ENFERMEDAD FAMILIAR → Madre/padre").
Permitir más profundidad no agrega nada y sí cuesta: la pantalla de configuración tendría que ser
un árbol con expandir/colapsar y estado por nodo, y el filtro por padre tendría que resolver
descendencia recursiva en vez de un solo `IN`. Se limita acá, en un solo lugar, y todo lo demás
se puede escribir asumiendo dos niveles.
"""
from typing import Optional

from utils.errors import AppError


def ensure_padre_valido(repo, padre_id, tipo_id: Optional[str] = None) -> Optional[dict]:
    """Valida que `padre_id` pueda ser padre. Devuelve la fila del padre para reusarla.

    Se devuelve la fila (y no un bool) para que el caller no la consulte dos veces: la necesita
    para precargar `cuenta_ausentismo` — mismo criterio que `ensure_empleado_de_empresa`.

    Args:
        repo: TiposAusenciaRepo (o doble) con `find_by_id`.
        padre_id: candidato a padre. None = tipo de primer nivel, no hay nada que validar.
        tipo_id: el tipo que se está creando o editando. None en un alta (todavía no tiene id).

    Returns:
        La fila del padre, o None si `padre_id` es None.

    Raises:
        AppError: TIPO_PADRE_NOT_FOUND (404) si el padre no existe.
        AppError: TIPO_JERARQUIA_PROFUNDA (422) si el padre YA es hijo de otro (sería un nieto).
        AppError: TIPO_PADRE_ES_SI_MISMO (422) si un tipo se apunta a sí mismo.
    """
    if padre_id is None:
        return None
    if tipo_id and str(padre_id) == str(tipo_id):
        raise AppError("Un tipo no puede ser su propio padre", "TIPO_PADRE_ES_SI_MISMO", 422)

    padre = repo.find_by_id(str(padre_id))
    if not padre:
        raise AppError("Tipo padre no encontrado", "TIPO_PADRE_NOT_FOUND", 404)

    # 🔴 LA GUARDA DE PROFUNDIDAD, en una línea: si el padre YA tiene padre, esto sería un nieto.
    # Con profundidad máxima 2 alcanza con mirar UN nivel; no hace falta recorrer nada.
    if padre.get("padre_id"):
        raise AppError(
            "Ese tipo ya es un subtipo: no se le pueden colgar otros. La jerarquía admite "
            "dos niveles (tipo y subtipo).",
            "TIPO_JERARQUIA_PROFUNDA", 422)
    return padre


def ensure_no_ciclo_tipo(repo, tipo_id, padre_id, max_saltos: int = 20) -> None:
    """Lanza TIPO_CICLO (400) si asignar `padre_id` a `tipo_id` cierra un circuito.

    Sube por la cadena de padres del candidato; si en algún salto se llega al propio tipo, hay
    ciclo. Molde exacto de `ensure_no_ciclo_manager`.

    ⚠️ CON PROFUNDIDAD 2 ESTO ES CASI IMPOSIBLE, y aun así se escribe. Dos motivos:
      · `ensure_padre_valido` protege el camino de la app, pero la base admite un nieto escrito
        a mano (ver el encabezado del módulo). Si ese dato existe, esta guarda es la que evita
        que el recorrido del filtro por padre entre en un bucle infinito.
      · Es de diez líneas y el molde ya estaba escrito. El costo de no tenerla se paga una sola
        vez, colgando un proceso.

    `max_saltos` es la red contra datos ya corruptos: si la cadena no termina, se asume ciclo.
    Es 20 y no 50 (el del organigrama) porque acá la profundidad legítima es 2: cualquier cadena
    más larga que un puñado de saltos ya es dato roto.
    """
    if padre_id is None:
        return
    actual: Optional[str] = str(padre_id)
    objetivo = str(tipo_id)
    for _ in range(max_saltos):
        if actual == objetivo:
            raise AppError("La jerarquía de tipos quedaría circular", "TIPO_CICLO", 400)
        nodo = repo.find_by_id(actual)
        if nodo is None or not nodo.get("padre_id"):
            return
        actual = str(nodo["padre_id"])
    raise AppError("La jerarquía de tipos quedaría circular", "TIPO_CICLO", 400)

"""
Schema → fila de la base: el payload del alta y el patch de la edición.

🔑 ES EL ESPEJO DE `_objetivo_row.py`. Aquél traduce fila de la base → `ObjetivoResponse`
(y por eso resuelve nombres con lookups batch); éste traduce `ObjetivoCreate`/`ObjetivoUpdate` →
las columnas que viajan en el INSERT/UPDATE. Las dos direcciones de la misma correspondencia, una
en cada archivo, para que no haya que buscarlas en el medio del repo.

Salió de `objetivo_repo.py`, que con las tres columnas de la migración 119 quedaba en 106 contra
un tope de 100.

🔴 ACÁ NO SE TOCA LA BASE, y no es casualidad: son funciones PURAS que devuelven un dict. Es lo
que las deja fuera del problema que el encabezado de `_objetivo_filtros` documenta —el espía de
los tests parchea `supabase_admin` módulo por módulo, así que un satélite que importara el cliente
por su cuenta quedaría sin parchear y pegaría a la red de verdad—. El `.insert()` y el `.update()`
se quedan en el repo.
"""
from schemas.objetivo import ObjetivoCreate, ObjetivoUpdate

# Campos que en el schema son UUID o date y en el patch tienen que viajar como texto.
_A_TEXTO = ("responsable_id", "parent_id", "fecha_entrega")


def payload_alta(data: ObjetivoCreate) -> dict:
    """Columnas del INSERT. Los opcionales sin valor NO se mandan: que los ponga el default.

    🔴 LOS TRES DE LA MIGRACIÓN 119 VAN SIEMPRE, no bajo un `if` como `descripcion`. Las tres
    columnas son NOT NULL con default y el schema ya les puso el valor vacío correcto (`""` y
    `[]`), así que mandarlos condicionalmente delegaría el default en la BASE — y ahí `tipo`
    caería en `'anual'`, que es el default de la COLUMNA (existe para el backfill de la migración)
    y NO el de producto, que es `'operativo'`. Los dos defaults conviven a propósito; el porqué
    está en `schemas/objetivo.TIPO_POR_DEFECTO`.

    🔑 `periodicidad` se manda con `.strip()`. El índice único usa `lower(periodicidad)` y
    `lower()` NO recorta: sin el strip, `" anual"` y `"anual"` son dos claves distintas y el
    duplicado entra igual. Lo dejó anotado la migración 114 y es la misma razón por la que
    `titulo` ya venía con `.strip()`.

    Args:
        data: El alta validada.

    Returns:
        dict listo para `.insert()`.
    """
    payload: dict = {
        "empresa_id":         str(data.empresa_id),
        "responsable_id":     str(data.responsable_id),
        "titulo":             data.titulo.strip(),
        "prioridad":          data.prioridad,
        "tipo":               data.tipo,
        "periodicidad":       data.periodicidad.strip(),
        "areas_involucradas": data.areas_involucradas,
    }
    if data.descripcion:   payload["descripcion"]   = data.descripcion
    if data.fecha_entrega: payload["fecha_entrega"] = str(data.fecha_entrega)
    if data.parent_id:     payload["parent_id"]     = str(data.parent_id)
    return payload


def patch_edicion(data: ObjetivoUpdate) -> dict:
    """Columnas del UPDATE. `None` = no se toca; el vacío (`""`, `[]`) SÍ se escribe.

    Esa distinción es lo que hace `exclude_none=True` y es la que permite BORRAR la periodicidad
    o las áreas de un objetivo que ya las tiene: con `exclude_defaults` o con un `if valor`, el
    vacío se caería del patch y la columna quedaría con el valor viejo, sin error.

    🔴 `responsables` NO es columna de `objetivos`: va a la tabla puente y por eso se saca del
    patch. En el UPDATE, ese campo fallaría con "column does not exist" y el fake de Supabase de
    la suite —que acepta cualquier cosa en `select`/`update`— no lo podría desmentir.

    ⚠️ `areas_involucradas` NO entra en `_A_TEXTO`: es una lista y tiene que viajar como lista.
    PostgREST la serializa a un array JSON y Postgres la recibe como `text[]`. Un `str()` acá la
    convertiría en la representación de Python (`"['Sistemas']"`) y entraría como UN elemento con
    corchetes adentro.

    Args:
        data: La edición parcial.

    Returns:
        dict listo para `.update()`; vacío si no hay ninguna columna que tocar.
    """
    return {
        k: (str(v) if k in _A_TEXTO else v)
        for k, v in data.model_dump(exclude_none=True).items()
        if k != "responsables"
    }

"""
QUÉ FORMA TIENE UN OBJETIVO DENTRO DEL LOG DE AUDITORÍA: qué campos entran, cuáles no, y cómo se
comparan dos versiones. Sin un solo evento — los cuatro eventos viven en
`services/_audit_payloads_objetivos.py`, que importa de acá.

🔴 POR QUÉ ESTÁ SEPARADO DEL ARCHIVO DE PAYLOADS, Y POR QUÉ EL CORTE ES ÉSTE.
`_audit_payloads_objetivos.py` nació el 24/8/2026 con todo junto y quedó en **157/150 líneas**, o
sea sobre el límite de un service. La salida NO podía ser condensar los comentarios: son el
registro de bugs ya pagados (los 93 eventos fantasma de empleados, el CASCADE de subobjetivos), y
un archivo que respeta su límite a costa de borrar por qué existe cada exclusión no arregla nada.
Se dividió, que es lo que manda la regla del repo.

El seam es real y no un corte por líneas: acá vive **qué de un objetivo es un dato de la fila**
—una pregunta sobre el MODELO, que cambia cuando cambia la tabla— y allá **qué evento se emite**
—una pregunta sobre el PRODUCTO, que cambia cuando cambia lo que RRHH quiere poder buscar en
`/auditoria`—. Las dos se movían por motivos distintos y ahora se tocan por separado.

⚠️ EL NOMBRE NO EMPIEZA CON `_audit_payloads_` A PROPÓSITO. Los diecinueve archivos con ese
prefijo son módulos de EVENTOS y el patrón vale por eso; este no emite ninguno, y llamarlo igual
haría que el próximo que busque "dónde está el payload de X" abra el archivo equivocado.

`sin_derivados` se IMPORTA de `_audit_payloads.py`; `subset` se define acá. No es inconsistencia:
es la regla escrita en aquel encabezado. `sin_derivados` DEFINE QUÉ ENTRA EN UN DIFF y dos copias
que se separen darían dos criterios distintos sobre lo mismo; `subset` es una proyección trivial.
"""
from typing import List

from services._audit_payloads import sin_derivados
from services.audit_service import AuditService, _jsonable

# Campos de negocio del alta y de la baja: la FOTO del objetivo. Un alta o una baja fotografían
# un estado y ahí una lista curada alcanza — se elige qué vale la pena guardar. Un UPDATE es otra
# pregunta y por eso usa `sin_derivados`; ver el encabezado de `_audit_payloads.py`.
CAMPOS_OBJETIVO = (
    "empresa_id", "responsable_id", "titulo", "descripcion", "prioridad", "estado",
    "fecha_entrega", "parent_id", "tipo", "periodicidad", "areas_involucradas",
)

# 🔴 LO QUE NO ES UNA COLUMNA DE `objetivos`, y por qué cada uno.
#   · `empresa_nombre`, `responsable_nombre`, `parent_titulo` — nombres resueltos por JOIN. Son
#     resultado de CÓMO se leyó la fila, no datos de la fila. Es la clase exacta que generó los
#     93 eventos fantasma de empleados ("area_nombre: SALUD → null").
#   · `hijos` — el SUBÁRBOL entero, anidado. Sin excluirlo, editarle el título a un padre
#     grabaría en el diff los objetos completos de todos sus hijos, dos veces.
#   · `responsables` — vive en la tabla PUENTE, no en `objetivos`, y además llega con los nombres
#     ya resueltos. Su cambio SÍ se audita, pero por los ids: ver `_ids_responsables`.
#   · `created_at` / `updated_at` — los escribe la base. `updated_at` cambia en TODO update, así
#     que dejarlo adentro haría que ningún update pudiera ser "sin cambios" y el descarte de
#     `_es_update_sin_cambios` no funcionaría nunca.
#
# ⚠️ Hoy los dos lados del diff se leen IGUAL —`save`, `update` y `set_estado` de `objetivo_repo`
# terminan los tres en `find_by_id`, o sea con los joins resueltos—, así que estos campos no
# producirían un fantasma HOY. Se excluyen igual: la simetría es una casualidad del repo actual y
# alcanza con que alguien deje de releer después de escribir para que vuelva el bug de 2026.
DERIVADOS_OBJETIVO = frozenset({
    "empresa_nombre", "responsable_nombre", "parent_titulo", "hijos", "responsables",
    "created_at", "updated_at",
})


def subset(obj: object, campos: tuple) -> dict:
    """Extrae `campos` de un modelo Pydantic (o dict) como dict JSON-serializable."""
    data = obj.model_dump() if hasattr(obj, "model_dump") else dict(obj)  # type: ignore[arg-type]
    return {k: _jsonable(data.get(k)) for k in campos}


def _ids_responsables(obj) -> List[str]:
    """Los ids de la tabla puente, ordenados. NUNCA los nombres.

    La lista de responsables es un dato de negocio real —cambiarla es una edición que hay que
    registrar— pero llega como `[{id, nombre}]`, con el nombre resuelto desde `users`. Guardar el
    objeto entero metería texto derivado de un join en el diff; guardar solo los ids registra el
    cambio de membresía, que es lo que ocurrió, y con el dato que la base realmente tiene.
    Ordenados porque el ORDEN en el que la puente devuelve las filas no es una decisión de nadie:
    sin ordenar, dos lecturas iguales podrían diffear.
    """
    return sorted(str(r.id) for r in (getattr(obj, "responsables", None) or []))


def diff_objetivo(prior, nuevo) -> tuple:
    """El diff de un objetivo: columnas reales + la membresía de la puente, sin nada derivado."""
    antes = sin_derivados(prior, DERIVADOS_OBJETIVO)
    despues = sin_derivados(nuevo, DERIVADOS_OBJETIVO)
    antes["responsables"] = _ids_responsables(prior)
    despues["responsables"] = _ids_responsables(nuevo)
    return AuditService._diff(antes, despues)

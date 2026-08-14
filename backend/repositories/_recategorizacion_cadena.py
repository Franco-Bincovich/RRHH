"""
Las DOS consultas que sostienen las reglas de la fecha retroactiva. Satélite de
`recategorizacion_repo`.

No son "dos lecturas más": son las que contestan las dos preguntas de las que depende todo el
módulo — **de dónde salen los `*_anterior`** (REGLA 1) y **si corresponde pisar al empleado**
(REGLA 2). Viven aparte de las dos VISTAS (planilla e historial) porque responden a otra cosa:
las vistas muestran, estas deciden. La regla que aplican está escrita en
`services/_recategorizacion_anteriores.py`; acá está solo cómo se traen las filas.

🔴 LAS DOS VAN SIN FILTRO DE EMPRESA, A PROPÓSITO. La barrera ya la aplicó el service sobre el
EMPLEADO (`ensure_empleado_de_empresa`), y el histórico de una persona es suyo: acotarlo por el
header dejaría afuera filas propias cuando se mira en modo consolidado y armaría una cadena de
`*_anterior` INCOMPLETA — o sea, un histórico que se contradice, sin ningún error. Es el mismo
criterio que `ids_subordinados`, que también es ciego a la empresa.

⚠️ Un satélite de `repositories/` NO tiene límite propio de 200: es un repositorio, límite 100.
"""
from datetime import date
from typing import Optional

from integrations.supabase_client import supabase_admin
from repositories._recategorizacion_row import SELECT, TABLE, build
from schemas.recategorizacion import RecategorizacionResponse


def _primera(q) -> Optional[RecategorizacionResponse]:
    """Ejecuta la query ordenada por fecha efectiva descendente y devuelve la primera fila."""
    filas = build(q.order("fecha_efectiva", desc=True).limit(1).execute().data or [])
    return filas[0] if filas else None


def previa(empleado_id: str, fecha: date,
           excepto_id: Optional[str] = None) -> Optional[RecategorizacionResponse]:
    """La última recategorización ANTERIOR a `fecha` — de ahí salen los `*_anterior`.

    🔴 `lt` y NO `lte`: una fila de la MISMA fecha no es "anterior" a esta. Con `lte`, dos
    cargas del mismo día se tomarían de anterior una a la otra y el histórico diría que hubo dos
    cambios donde hubo una corrección.

    `excepto_id` excluye la propia fila al EDITAR: sin eso, una recategorización que se edita
    sin moverle la fecha se tomaría a sí misma de previa y se copiaría sus propios valores
    nuevos como anteriores.

    Args:
        empleado_id: la persona cuyo histórico se recorre.
        fecha: fecha efectiva de la recategorización que se está cargando o editando.
        excepto_id: id a excluir (la propia fila, en una edición).

    Returns:
        La recategorización previa, o None si es la primera de esa persona.
    """
    q = (supabase_admin.table(TABLE).select(SELECT)
         .eq("empleado_id", empleado_id).lt("fecha_efectiva", str(fecha)))
    if excepto_id:
        q = q.neq("id", excepto_id)
    return _primera(q)


def ultima(empleado_id: str,
           excepto_id: Optional[str] = None) -> Optional[RecategorizacionResponse]:
    """La de fecha efectiva MÁS ALTA de esa persona — decide si se pisa al empleado.

    `excepto_id` excluye la propia fila al editar: si no, una recategorización nunca sería "más
    reciente que" sí misma y editarla no actualizaría jamás al colaborador.

    Args:
        empleado_id: la persona cuyo histórico se recorre.
        excepto_id: id a excluir (la propia fila, en una edición).

    Returns:
        La recategorización más reciente, o None si la persona no tiene ninguna.
    """
    q = supabase_admin.table(TABLE).select(SELECT).eq("empleado_id", empleado_id)
    if excepto_id:
        q = q.neq("id", excepto_id)
    return _primera(q)

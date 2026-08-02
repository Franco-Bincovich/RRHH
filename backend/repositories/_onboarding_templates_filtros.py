"""
Los dos filtros de lectura de templates de onboarding: empresa y visibilidad.

Separados de `_onboarding_templates_row.py` (mappers y SELECT) porque responden otra pregunta
—QUÉ FILAS se pueden ver, no cómo se leen— y porque `with_visibilidad` lo usan DOS repos
(`onboarding_templates_repo` y `onboarding_repo`): tenerlo en un módulo propio deja claro que es
regla compartida y no una primitiva del repo de templates. El corte se hizo además porque el
satélite había llegado a 159 líneas contra el límite de 100.
"""
from typing import Optional
from uuid import UUID


def with_empresa(query, empresa_id: Optional[UUID]):
    """Aplica filtro de empresa a una query de Supabase si empresa_id no es None."""
    return query.eq("empresa_id", str(empresa_id)) if empresa_id else query


# Rol que ve TODAS las plantillas, incluidas las privadas de los demás. Ver with_visibilidad.
ROL_VE_TODO = "gerencia_lectura"


def with_visibilidad(query, user_id: Optional[str], rol: Optional[str] = None):
    """Acota la query a las plantillas que `user_id` puede ver. LA REGLA VIVE SOLO ACÁ.

        es_publica = true  OR  created_by = user_id  OR  created_by IS NULL

    Va en el WHERE (Forma A) y no en Python: es una sola ida a la base, no trae filas que el
    usuario no puede ver, y el listado no puede "olvidarse" de filtrar. La misma expresión la
    usan el listado, el detalle y la plantilla por defecto, así que no hay dos criterios que
    puedan separarse.

    `created_by IS NULL` cuenta como pública: la FK del autor es ON DELETE SET NULL, así que
    borrar un usuario dejaría sus privadas sin dueño y un filtro por autor las volvería
    inalcanzables para siempre. Ver la migración 082.

    🔴 `gerencia_lectura` NO SE FILTRA: ve todas, incluidas las privadas ajenas. No es una
    excepción al modelo de roles — es lo que ese rol YA significa en todo el sistema ("lectura
    en todo"), y respetarlo acá es lo que evita abrir la PRIMERA excepción row-level. "Privada"
    en este módulo es privacidad ENTRE PARES DE RRHH (un borrador que no quiero que aparezca en
    la lista de mis compañeros), no confidencialidad frente a la dirección. Si algún día hace
    falta ocultárselas también a gerencia, se agrega acá; al revés no se puede.

    ⚠️ `user_id=None` NO restringe, igual que `empresa_id=None`. No es un modo de acceso: es
    para la relectura posterior a una escritura ya gateada (`update_template`), donde volver a
    filtrar podría devolver None sobre una fila que el caller acaba de editar legítimamente.
    Ningún camino que venga del router llega acá sin user_id — AuthMiddleware es fail-closed.

    Args:
        query: Query de Supabase en construcción.
        user_id: UUID en texto del usuario que mira. None = sin restricción.
        rol: Rol del usuario. `gerencia_lectura` no se filtra.

    Returns:
        La query con el filtro aplicado.
    """
    if user_id is None or rol == ROL_VE_TODO:
        return query
    return query.or_(f"es_publica.eq.true,created_by.is.null,created_by.eq.{user_id}")

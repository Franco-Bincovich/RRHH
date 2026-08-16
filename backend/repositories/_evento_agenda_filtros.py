"""
Los tres filtros de lectura de la agenda: empresa, visibilidad y estado de resuelta.

Módulo aparte de `_evento_agenda_row.py` (mappers y SELECT) por el mismo motivo que en
onboarding: responden otra pregunta —QUÉ FILAS se pueden ver, no cómo se leen— y las usan las
TRES lecturas del repo (la agenda paginada, el detalle por id y los pendientes del dashboard).
Con una copia por lectura, la que se olvide de un filtro no da error: devuelve de más.
"""
from typing import Optional
from uuid import UUID

from utils.permisos import ROL_VE_PRIVADAS_AJENAS


def con_empresa(query, empresa_id: Optional[UUID]):
    """Aplica el filtro de empresa si viene. None = consolidado, no restringe.

    `eventos_agenda.empresa_id` es NOT NULL y con FK a `empresas`: un evento pertenece siempre a
    una sociedad concreta (decisión de la migración 113 — un feriado nacional se carga una vez
    por empresa, a cambio de que el filtro sea un `.eq()` como en todo el resto del sistema).
    """
    return query.eq("empresa_id", str(empresa_id)) if empresa_id else query


def con_visibilidad(query, user_id: Optional[str], rol: Optional[str] = None):
    """Acota la query a los eventos que `user_id` puede ver. LA REGLA VIVE SOLO ACÁ.

        es_publica = true  OR  created_by = user_id

    Va en el WHERE (Forma A) y no en Python: una sola ida a la base, no trae filas que el usuario
    no puede ver, y ninguna de las tres lecturas puede "olvidarse" de filtrar.

    🔴 NO LLEVA LA RAMA `created_by IS NULL`, y la diferencia con el precedente
    (`_onboarding_templates_filtros.with_visibilidad`) es de la BASE, no de criterio. Allá la FK
    del autor es ON DELETE SET NULL, así que borrar un usuario deja plantillas sin dueño y sin
    esa rama quedarían invisibles para siempre. Acá `created_by` es **NOT NULL y su FK no lleva
    ON DELETE**: borrar un usuario con eventos se BLOQUEA, la fila huérfana no puede existir, y
    escribir la condición igual sería código muerto que aparenta cubrir un caso.

    🔴 `gerencia_lectura` NO SE FILTRA: ve las privadas ajenas. Es la misma decisión de producto
    que en plantillas, y por eso el literal es el MISMO —`utils.permisos.ROL_VE_PRIVADAS_AJENAS`,
    no una copia—: "privada" acá es privacidad entre pares de RRHH, no confidencialidad frente a
    la dirección.

    ⚠️ `user_id=None` NO restringe, igual que `empresa_id=None`. No es un modo de acceso: es para
    la relectura posterior a una escritura ya gateada, donde volver a filtrar podría devolver
    None sobre una fila que el caller acaba de editar legítimamente. Ningún camino que venga del
    router llega acá sin user_id — AuthMiddleware es fail-closed.

    Args:
        query: Query de Supabase en construcción.
        user_id: UUID en texto del usuario que mira. None = sin restricción.
        rol: Rol del usuario. `gerencia_lectura` no se filtra.

    Returns:
        La query con el filtro aplicado.
    """
    if user_id is None or rol == ROL_VE_PRIVADAS_AJENAS:
        return query
    return query.or_(f"es_publica.eq.true,created_by.eq.{user_id}")


def con_pendientes(query, incluir_resueltas: bool):
    """Deja fuera los resueltos salvo que se pidan explícitamente.

    El default es OCULTARLOS: un evento resuelto es uno que alguien ya atendió, y la lista se
    llenaría de ruido histórico que nadie mira. En la pantalla eso es un toggle (el mismo patrón
    que "Ver bajas" del catálogo de clientes); en el dashboard no hay toggle y NUNCA se piden.
    """
    return query if incluir_resueltas else query.eq("resuelta", False)

"""
Escrituras de la agenda de eventos: alta, edición, baja y el toggle de resuelta. Satélite de
`evento_agenda_repo`.

Se parte DESDE EL PRINCIPIO, no cuando el archivo reviente: el repo tiene tres lecturas (la
agenda paginada, el detalle y los pendientes del dashboard) y no entran con las cuatro escrituras
adentro. El corte lectura/escritura es el mismo de `_recategorizacion_write_repo.py`.

⚠️ Un satélite de `repositories/` NO tiene límite propio de 200 por llamarse `_algo.py`: es un
repositorio y su límite sigue siendo 100.

🔴 LAS ESCRITURAS DUMPEAN CON `mode="json"`. Sin él un `date` viaja como objeto de Python y el
cliente HTTP no lo serializa. Acá `fecha` es `date` en las dos, alta y edición.

🔴 SÍ HAY `borrar`, al revés que recategorizaciones — y es la diferencia de fondo entre los dos
módulos. Una recategorización es un HECHO histórico del que cuelga la cadena de `*_anterior`;
un evento es un RECORDATORIO del que no cuelga nada. Uno cargado por error no tiene por qué
quedar, y la auditoría guarda su snapshot antes de que desaparezca.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.evento_agenda import EventoCreate, EventoUpdate
from utils.errors import AppError

_T = "eventos_agenda"

# Lo que el cliente NUNCA manda y el sistema completa. Se descarta explícitamente del dump por si
# el schema de entrada gana alguno de estos campos en el futuro: un `empresa_id` colado desde el
# body pisaría la del header y un `resuelta` colado dejaría la fila en un estado que el CHECK
# `eventos_agenda_resuelta_coherente_check` rechaza con un 500 en vez de un 422.
_DEL_SISTEMA = ("empresa_id", "created_by", "resuelta", "resuelta_at", "resuelta_por")


def guardar(data: EventoCreate, empresa_id: UUID, dias_aviso: int, created_by: str) -> dict:
    """Alta. `empresa_id` sale del header y `created_by` del usuario del request.

    Ninguno de los dos se toma del body: la empresa la decide el selector (es una elección
    explícita de quien carga) y el autor, el token. Aceptar `created_by` permitiría cargar un
    evento privado a nombre de otro, que es la fila que ese otro no puede ver ni borrar.

    Args:
        data: campos cargados por el usuario, ya validados.
        empresa_id: la del header, ya exigida por `require_empresa_id`.
        dias_aviso: ya resuelto por el service (el del evento o el default de la empresa).
        created_by: id del usuario autenticado.

    Returns:
        La fila creada, cruda (sin los nombres de join). El repo la vuelve a leer para eso.

    Raises:
        AppError: DB_ERROR (500) si el INSERT no devuelve la fila.
    """
    payload = data.model_dump(mode="json", exclude=set(_DEL_SISTEMA))
    payload.update({"empresa_id": str(empresa_id), "created_by": str(created_by),
                    "dias_aviso": dias_aviso})
    res = supabase_admin.table(_T).insert(payload).execute()
    if not res.data:
        raise AppError("Error al crear el evento", "DB_ERROR", 500)
    return res.data[0]


def actualizar(id: str, data: EventoUpdate) -> None:
    """Aplica los campos NO nulos. No relee: eso lo hace el repo.

    `exclude_none` hace que `None` signifique "no lo toques". Un patch vacío no ejecuta nada: sin
    ese `if`, PostgREST recibiría un UPDATE sin columnas y respondería un error de sintaxis por
    una edición que simplemente no cambiaba nada.
    """
    patch = data.model_dump(mode="json", exclude_none=True, exclude=set(_DEL_SISTEMA))
    if patch:
        supabase_admin.table(_T).update(patch).eq("id", id).execute()


def marcar_resuelta(id: str, resuelta: bool, usuario_id: Optional[str]) -> None:
    """Escribe las TRES columnas del estado de resuelta, siempre juntas.

    🔴 DESRESOLVER LIMPIA `resuelta_at` Y `resuelta_por`, no solo baja el flag. El CHECK de la
    base solo exige "resuelta ⇒ hay fecha", así que dejar los valores viejos no fallaría: el
    evento volvería a la lista de pendientes diciendo que lo resolvió alguien el martes pasado, y
    la pantalla no tendría cómo saber que eso ya no es cierto. Resolver es reversible (decisión
    de producto) justamente para corregir un click equivocado; la corrección tiene que borrar
    también su rastro.
    """
    ahora = datetime.now(timezone.utc).isoformat() if resuelta else None
    supabase_admin.table(_T).update({
        "resuelta": resuelta, "resuelta_at": ahora,
        "resuelta_por": str(usuario_id) if (resuelta and usuario_id) else None,
    }).eq("id", id).execute()


def borrar(id: str) -> None:
    """Baja FÍSICA. No hay baja lógica acá: un evento borrado no tiene que sobrevivir en ningún
    listado, y su rastro queda en la auditoría con el snapshot previo."""
    supabase_admin.table(_T).delete().eq("id", id).execute()

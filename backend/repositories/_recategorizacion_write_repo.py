"""
Escrituras de recategorizaciones: alta y edición. Satélite de `recategorizacion_repo`.

Se parte DESDE EL PRINCIPIO, no cuando el archivo reviente: el repo tiene cinco lecturas (dos
vistas + las dos consultas que sostienen las reglas de fecha retroactiva) y no entran con las
escrituras adentro. El corte lectura/escritura es el mismo de `_empleado_write_repo.py`.

⚠️ Un satélite de `repositories/` NO tiene límite propio de 200 por llamarse `_algo.py`: es un
repositorio y su límite sigue siendo 100.

🔴 LAS DOS ESCRITURAS DUMPEAN CON `mode="json"`. Sin él, un `UUID`, un `date` o un `Decimal`
viajan como objeto de Python y el cliente HTTP no los serializa. Acá pesa más que en otros
módulos: `impacto_salarial` es `Decimal` y `fecha_efectiva` es `date`, o sea DOS tipos que no
son JSON nativo en la misma tabla. Faltó exactamente en un update de áreas y no lo vio ningún
test: apareció ejecutándolo.

🔴 NO HAY `borrar`, y no es un olvido: se puede editar, no borrar (ver `schemas/recategorizacion`).
"""
from datetime import date
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.recategorizacion import RecategorizacionCreate, RecategorizacionUpdate
from utils.errors import AppError

_T = "recategorizaciones"

# Lo que el cliente NUNCA manda y el sistema completa. Se descarta explícitamente del dump por
# si el schema de entrada gana alguno de estos campos en el futuro: un `empresa_id` colado desde
# el body pisaría la del empleado y rompería la FK compuesta con un 500 en vez de un 422.
_DEL_SISTEMA = ("empleado_id", "fecha_efectiva", "empresa_id", "registrado_por")


def guardar(data: RecategorizacionCreate, empresa_id: UUID, anteriores: dict, fecha: date,
            registrado_por: Optional[str]):
    """Alta. `empresa_id` sale del EMPLEADO y `registrado_por` del usuario del request.

    Ninguno de los dos se toma del body: la empresa la decide la entidad padre (Vista vs
    Acción) y el autor, el token. Aceptarlos permitiría escribir una fila a nombre de otra
    sociedad o de otro usuario.

    Args:
        data: campos cargados por el usuario, ya validados.
        empresa_id: la del empleado, resuelta por el service.
        anteriores: los tres `*_anterior` que calculó `_recategorizacion_anteriores`.
        fecha: fecha efectiva ya resuelta (el default "hoy" lo pone el service).
        registrado_por: id del usuario autenticado, o None.

    Returns:
        La fila creada, ya enriquecida con los nombres.

    Raises:
        AppError: DB_ERROR (500) si el INSERT no devuelve la fila.
    """
    from repositories._recategorizacion_row import build  # tardío: evita el ciclo con el mapper

    payload = data.model_dump(mode="json", exclude=set(_DEL_SISTEMA))
    payload.update(anteriores)
    payload["empleado_id"] = str(data.empleado_id)
    payload["empresa_id"] = str(empresa_id)
    payload["fecha_efectiva"] = str(fecha)
    if registrado_por:
        payload["registrado_por"] = str(registrado_por)
    res = supabase_admin.table(_T).insert(payload).execute()
    if not res.data:
        raise AppError("Error al registrar la recategorización", "DB_ERROR", 500)
    return build(res.data)[0]


def actualizar(id: str, data: RecategorizacionUpdate, anteriores: dict) -> None:
    """Aplica los campos NO nulos + los `*_anterior` recalculados. No relee: eso lo hace el repo.

    Los `*_anterior` se pisan SIEMPRE, incluso si la edición no movió la fecha: el service los
    recalcula en cada edición porque cambiar `fecha_efectiva` cambia cuál es la recategorización
    previa, y dejarlos como estaban dejaría el histórico contradiciéndose sin ninguna señal.

    `exclude_none` hace que `None` signifique "no lo toques". Para vaciar un valor nuevo (p. ej.
    corregir una que decía que cambiaba el rol y no cambiaba) hoy no hay forma por esta vía —
    limitación conocida y compartida con el resto de los `*Update` del repo.
    """
    patch = data.model_dump(mode="json", exclude_none=True)
    patch.update(anteriores)
    if patch:
        supabase_admin.table(_T).update(patch).eq("id", id).execute()

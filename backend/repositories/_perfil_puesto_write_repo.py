"""
Escrituras del catálogo de perfiles de puesto: alta y edición. Satélite de `perfil_puesto_repo`.

Se parte DESDE EL PRINCIPIO y no cuando el archivo reviente: junto todo daba 114 contra el
límite de 100. El corte es lectura / escritura, que es el mismo que ya usa
`_empleado_write_repo.py`, y no uno inventado para esta tanda.

⚠️ UN SATÉLITE DE `repositories/` NO TIENE LÍMITE PROPIO DE 200 POR LLAMARSE `_algo.py`: es un
repositorio y su límite sigue siendo 100. Está escrito acá porque el repo ya se equivocó dos
veces con eso (dos archivos `_row` llegaron a declarar "acá el límite es 200", y uno tocó 159).

🔴 LAS DOS ESCRITURAS DUMPEAN CON `mode="json"`, Y NO ES DECORATIVO. Sin él un `Literal` o un
`UUID` viajan como objeto de Python y el cliente HTTP no los serializa. Faltó exactamente en un
update de áreas y no lo vio ningún test: solo apareció ejecutándolo. Que las dos funciones
estén en el mismo archivo hace que la próxima escritura se escriba al lado de las dos que ya lo
hacen bien.
"""
from typing import Optional

from integrations.supabase_client import supabase_admin
from schemas.perfil_puesto import (
    PerfilPuestoCreate, PerfilPuestoResponse, PerfilPuestoUpdate,
)
from utils.errors import AppError

_T = "perfiles_puesto"


def guardar(data: PerfilPuestoCreate, created_by: Optional[str]) -> PerfilPuestoResponse:
    """Alta de un perfil. `created_by` sale del usuario del request, NUNCA del body.

    Aceptarlo del cliente permitiría atribuirle el alta a cualquier otro usuario, que es
    justamente lo que la columna existe para impedir. Si no hay usuario resuelto, la columna
    queda NULL (es nullable, con FK `ON DELETE SET NULL`).

    Args:
        data: Campos del perfil ya validados por Pydantic.
        created_by: Id del usuario autenticado, o None.

    Returns:
        El perfil creado, tal como quedó en la base.

    Raises:
        AppError: DB_ERROR (500) si el INSERT no devuelve la fila.
    """
    payload = data.model_dump(mode="json")
    payload["nombre"] = data.nombre.strip()
    if created_by:
        payload["created_by"] = str(created_by)
    res = supabase_admin.table(_T).insert(payload).execute()
    if not res.data:
        raise AppError("Error al crear el perfil de puesto", "DB_ERROR", 500)
    return PerfilPuestoResponse.model_validate(res.data[0])


def actualizar(id: str, data: PerfilPuestoUpdate) -> None:
    """Aplica los campos NO nulos de `data`. No relee: eso lo hace el repo con `find_by_id`.

    Recibe el SCHEMA y no un dict ya armado, para que el `model_dump(mode="json")` ocurra en un
    solo lugar y no en cada caller — dos serializaciones distintas de la misma escritura es
    exactamente cómo se cuela un `mode="json"` faltante.

    `exclude_none` es lo que hace que `None` signifique "no lo toques"; para VACIAR un campo de
    texto se manda `""`, que sí viaja. Ver el docstring de `PerfilPuestoUpdate`.

    Args:
        id: Id del perfil a modificar.
        data: Campos a pisar. Si no trae ninguno no nulo, no se emite el UPDATE.
    """
    patch = data.model_dump(mode="json", exclude_none=True)
    if patch:
        supabase_admin.table(_T).update(patch).eq("id", id).execute()

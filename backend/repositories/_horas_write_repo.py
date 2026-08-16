"""
El INSERT de `horas_proyecto`, con sus dos caminos de escritura.

SALIÓ DE `horas_repo.py`, que estaba en 102/100 después de restaurar el comentario del desempate.
Molde: `_empleado_write_repo.py`, `_vacante_write_repo.py`, `_nomina_write_repo.py`.

🔴 UNA SOLA TABLA, DOS CAMINOS DE ESCRITURA. `guardar` acepta los campos de los dos y manda solo
los que recibe: el camino viejo (asignación + proyecto + snapshot) y la carga directa (cliente +
empleado + modalidad + textos). Ninguno de los dos ve los campos del otro en el payload — por eso
hay UNA función con `**opcionales` y no dos: dos inserts sobre la misma tabla que se separaran
darían dos formas distintas de armar la misma fila, y el índice único parcial de idempotencia
sólo protege a uno de los dos caminos si el otro se olvida de mandar la clave.
"""
from typing import Optional

from integrations.supabase_client import supabase_admin
from repositories._hora_row import build
from schemas.horas import HoraResponse
from utils.errors import AppError

TABLE = "horas_proyecto"

# Campos que solo van al INSERT si el caller los trae. `descripcion` y `cargado_por` estaban
# antes con un `if <valor>:` (truthiness); acá el criterio es `is not None` para los nuevos, que
# es lo correcto para textos: `proyecto_texto=""` es un dato que el usuario escribió, no un
# campo ausente. Se dejan los dos viejos con su comportamiento original.
_OPCIONALES = ("asignacion_id", "proyecto_id", "valor_hora_snapshot",
               "cliente_id", "empleado_id", "modalidad", "proyecto_texto", "tarea_texto",
               "idempotencia")


def guardar(
    empresa_id: str, empleado_empresa_id: str, fecha: str, horas: float,
    descripcion: Optional[str] = None, cargado_por: Optional[str] = None, **opcionales,
) -> HoraResponse:
    """Inserta un registro. Los campos de cada camino llegan por `opcionales`.

    Obligatorios en los DOS caminos: empresa, empresa del empleado, fecha y horas.
    `valor_hora_snapshot` ya viene congelado por el service (camino viejo).
    """
    payload: dict = {
        "empresa_id": empresa_id, "empleado_empresa_id": empleado_empresa_id,
        "fecha": fecha, "horas": horas,
    }
    payload.update({k: v for k, v in opcionales.items()
                    if k in _OPCIONALES and v is not None})
    if descripcion:
        payload["descripcion"] = descripcion
    if cargado_por:
        payload["cargado_por"] = cargado_por
    res = supabase_admin.table(TABLE).insert(payload).execute()
    if not res.data:
        raise AppError("Error al registrar las horas", "DB_ERROR", 500)
    rows = supabase_admin.table(TABLE).select("*").eq("id", str(res.data[0]["id"])).execute().data or []
    return build(rows)[0]

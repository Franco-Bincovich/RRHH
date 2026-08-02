"""
Repositorio de tipos_ausencia.

Desde la migración 085 el catálogo dejó de ser puramente global: `empresa_id NULL` es un tipo
global (las 4 filas base lo son) y con valor es un tipo propio de esa empresa. Las lecturas
traen SIEMPRE los globales MÁS los de la empresa activa — un tipo global le sirve a todas.
"""
from typing import Any, Dict, List, Optional

from integrations.supabase_client import supabase_admin
from schemas.ausencias import TipoAusenciaResponse
from utils.errors import AppError

_TA = "tipos_ausencia"
_COLS = "id, nombre, es_base, activo, empresa_id, cuenta_ausentismo"


class TiposAusenciaRepo:
    def find_all(
        self, empresa_id: Optional[str] = None, incluir_inactivos: bool = False,
    ) -> List[TipoAusenciaResponse]:
        """
        Tipos visibles para una empresa: los globales más los suyos, ordenados por nombre.

        🔴 El filtro `empresa_id IS NULL OR empresa_id = <mía>` va EN LA QUERY (`.or_`), no
        filtrando en Python la lista completa: traer todos los tipos de todas las empresas para
        descartar después expone los ajenos a cualquiera que mire la respuesta cruda.

        `incluir_inactivos` es False por defecto porque el consumidor normal es el select del
        formulario de ausencias, que no debe ofrecer un tipo dado de baja. La pantalla de
        configuración lo pide en True: ahí hay que verlos para poder reactivarlos.
        """
        q = supabase_admin.table(_TA).select(_COLS)
        if empresa_id:
            q = q.or_(f"empresa_id.is.null,empresa_id.eq.{empresa_id}")
        else:
            q = q.is_("empresa_id", "null")
        if not incluir_inactivos:
            q = q.eq("activo", True)
        data = q.order("nombre").execute().data or []
        return [TipoAusenciaResponse.model_validate(t) for t in data]

    def find_by_id(self, tipo_id: str) -> Optional[Dict[str, Any]]:
        """Fila cruda del tipo, o None. Cruda y no schema: el service necesita `empresa_id`
        y `es_base` para decidir si se puede tocar, y la respuesta se arma después."""
        res = supabase_admin.table(_TA).select(_COLS).eq("id", tipo_id).maybe_single().execute()
        return res.data if res and res.data else None

    def create(self, nombre: str, empresa_id: Optional[str] = None) -> TipoAusenciaResponse:
        """Inserta un tipo nuevo. `empresa_id=None` lo crea global. Lanza AppError si falla."""
        fila = {"nombre": nombre, "es_base": False, "empresa_id": empresa_id}
        res = supabase_admin.table(_TA).insert(fila).execute()
        if not res.data:
            raise AppError("Error al crear el tipo de ausencia", "DB_ERROR", 500)
        return TipoAusenciaResponse.model_validate(res.data[0])

    def update(self, tipo_id: str, cambios: Dict[str, Any]) -> TipoAusenciaResponse:
        """
        Aplica los campos presentes en `cambios`. NO hay un delete en este repo y no es un
        olvido: solicitudes_ausencia.tipo_id es una FK sin ON DELETE, así que borrar un tipo
        usado fallaría — y si no fallara, se llevaría puesto el historial. La baja es
        `activo=False`, que lo saca de los selects y deja las ausencias viejas intactas.
        """
        res = supabase_admin.table(_TA).update(cambios).eq("id", tipo_id).execute()
        if not res.data:
            raise AppError("Error al actualizar el tipo de ausencia", "DB_ERROR", 500)
        return TipoAusenciaResponse.model_validate(res.data[0])

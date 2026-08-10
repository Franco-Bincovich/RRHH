"""
Repositorio del catálogo de clientes (migración 102). Acceso a Supabase con supabase_admin.

🔒 BARRERA DE EMPRESA — FORMA A: el `empresa_id` viaja EN EL WHERE de la query, nunca se compara
en Python después de traer la fila. Una sola ida a la base e imposible de saltear. Es lo que
`find_by_id` y `update` hacen con `_con_empresa`.

`empresa_id=None` NO restringe: es la vista consolidada ("Todas las empresas"), y cualquier
cliente existente pasa. No es un fallo de validación — la barrera limita CUÁL recurso podés
elegir cuando hay una empresa activa, no de dónde sale la empresa que se escribe.

Quien no encuentra devuelve `None`, y el 404 lo arma el service con un mensaje idéntico al de
"no existe": "no existe" y "es de otra empresa" no se pueden distinguir desde afuera, o el
código se vuelve un oráculo de enumeración.

🔴 NO HAY `delete`, Y NO ES UN OLVIDO. `horas_proyecto.cliente_id` es una FK sin ON DELETE
(migración 103), así que borrar un cliente con horas cargadas fallaría contra la base — y si no
fallara, se llevaría puesto el historial de imputación. La baja es `activo=False`, que lo saca
de los selects y deja las horas viejas intactas. Es el mismo razonamiento, escrito en el mismo
lugar, que `tipos_ausencia_repo.update`.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.cliente import ClienteCreate, ClienteResponse
from utils.errors import AppError

_T = "clientes"


def _con_empresa(q, empresa_id: Optional[UUID]):
    """Aplica la barrera de empresa a la query. None = consolidado, sin filtro."""
    return q.eq("empresa_id", str(empresa_id)) if empresa_id else q


class ClienteRepo:
    def find_all(self, empresa_id: Optional[UUID] = None,
                 incluir_inactivos: bool = False) -> List[ClienteResponse]:
        """Clientes de la empresa (None = todas), por nombre.

        `incluir_inactivos` es False por defecto porque el consumidor normal es el select de la
        carga de horas, que no debe ofrecer un cliente dado de baja. La pantalla de ABM lo pide
        en True: ahí hay que verlos para poder reactivarlos. Mismo criterio que TiposAusenciaRepo.
        """
        q = _con_empresa(supabase_admin.table(_T).select("*"), empresa_id)
        if not incluir_inactivos:
            q = q.eq("activo", True)
        return [ClienteResponse.model_validate(r) for r in (q.order("nombre").execute().data or [])]

    def find_by_id(self, id: str, empresa_id: Optional[UUID] = None) -> Optional[ClienteResponse]:
        """El cliente, o None si no existe O es de otra empresa. Los dos casos son el mismo."""
        res = _con_empresa(supabase_admin.table(_T).select("*").eq("id", id), empresa_id) \
            .maybe_single().execute()
        return ClienteResponse.model_validate(res.data) if (res and res.data) else None

    def existe_nombre(self, nombre: str, empresa_id: UUID,
                      excepto_id: Optional[str] = None) -> bool:
        """¿Ya hay un cliente con ese nombre en la empresa? Comparación CASE-INSENSITIVE.

        🔴 LA GARANTÍA REAL ES EL ÍNDICE `ux_clientes_nombre_por_empresa (empresa_id,
        lower(nombre))`. Esto es para poder devolver un 409 legible en vez del error crudo de
        una constraint, y para que el rechazo exista incluso antes de que la migración 102
        corra. Queda una ventana de carrera entre el chequeo y el INSERT que solo el índice
        cierra — por eso el índice no es opcional.

        🔴 SE COMPARA EN PYTHON Y NO CON `.ilike()`, a propósito. PostgREST interpreta `*` como
        comodín dentro de `ilike`, así que un cliente llamado "Acme*" haría matchear a
        "AcmeSA" y el alta se rechazaría por un duplicado que no existe. `casefold()` no tiene
        semántica de patrón. Es barato: el catálogo de una empresa son decenas de filas, y ya
        se traen enteras para el listado.

        Incluye los INACTIVOS: el índice único tampoco los excluye, así que dejarlos afuera
        daría un 409 de base después de haber dicho que el nombre estaba libre.
        """
        objetivo = nombre.strip().casefold()
        return any(
            c.nombre.strip().casefold() == objetivo and str(c.id) != str(excepto_id or "")
            for c in self.find_all(empresa_id, incluir_inactivos=True)
        )

    def save(self, data: ClienteCreate) -> ClienteResponse:
        """Alta. `empresa_id` sale del body (empresa dueña), no del header: crear es una ACCIÓN."""
        res = supabase_admin.table(_T).insert(
            {"empresa_id": str(data.empresa_id), "nombre": data.nombre.strip()}
        ).execute()
        if not res.data:
            raise AppError("Error al crear el cliente", "DB_ERROR", 500)
        return ClienteResponse.model_validate(res.data[0])

    def update(self, id: str, patch: Dict[str, Any],
               empresa_id: Optional[UUID] = None) -> Optional[ClienteResponse]:
        """Aplica los campos de `patch`. La barrera va en el UPDATE, no solo en la relectura: sin
        el `.eq` acá, un id de otra empresa se escribiría igual y recién el SELECT posterior
        devolvería None — la escritura ya habría ocurrido."""
        if patch:
            _con_empresa(supabase_admin.table(_T).update(patch).eq("id", id), empresa_id).execute()
        return self.find_by_id(id, empresa_id)

"""
Repositorio del catálogo de clientes (migración 102). Acceso a Supabase con supabase_admin.

🔴 NO HAY BARRERA DE EMPRESA, Y NO ES UN OLVIDO (migración 108). Un cliente no pertenece a
ninguna empresa: el catálogo es GLOBAL, como `tipos_ausencia`. Ninguna query de este archivo
filtra ni escribe `empresa_id`, y no hay que "agregárselo por consistencia" con los otros repos —
sería un filtro que dejaría el catálogo vacío o parcial sin ningún error, que es el modo de falla
más caro del repo.

⚠️ La columna `clientes.empresa_id` TODAVÍA EXISTE en la base (la 108 solo le saca el NOT NULL;
se dropea en la 109). Que exista no la vuelve utilizable: las filas nuevas la dejan en NULL.

Quien no encuentra devuelve `None`, y el 404 lo arma el service. Sigue siendo el mismo 404 para
"no existe" que para cualquier otro motivo: eso no dependía de la empresa.

🔴 NO HAY `delete`, Y NO ES UN OLVIDO. `horas_proyecto.cliente_id` es una FK sin ON DELETE
(migración 103), así que borrar un cliente con horas cargadas fallaría contra la base — y si no
fallara, se llevaría puesto el historial de imputación. La baja es `activo=False`, que lo saca
de los selects y deja las horas viejas intactas. Es el mismo razonamiento, escrito en el mismo
lugar, que `tipos_ausencia_repo.update`.
"""
from typing import Any, Dict, List, Optional

from integrations.supabase_client import supabase_admin
from schemas.cliente import ClienteCreate, ClienteResponse
from utils.errors import AppError

_T = "clientes"


class ClienteRepo:
    def find_all(self, incluir_inactivos: bool = False) -> List[ClienteResponse]:
        """Todo el catálogo, por nombre. No hay filtro de empresa: el catálogo es global.

        `incluir_inactivos` es False por defecto porque el consumidor normal es el select de la
        carga de horas, que no debe ofrecer un cliente dado de baja. La pantalla de ABM lo pide
        en True: ahí hay que verlos para poder reactivarlos. Mismo criterio que TiposAusenciaRepo.
        """
        q = supabase_admin.table(_T).select("*")
        if not incluir_inactivos:
            q = q.eq("activo", True)
        return [ClienteResponse.model_validate(r) for r in (q.order("nombre").execute().data or [])]

    def find_by_id(self, id: str) -> Optional[ClienteResponse]:
        """El cliente, o None si no existe."""
        res = supabase_admin.table(_T).select("*").eq("id", id).maybe_single().execute()
        return ClienteResponse.model_validate(res.data) if (res and res.data) else None

    def existe_nombre(self, nombre: str, excepto_id: Optional[str] = None) -> bool:
        """¿Ya hay un cliente con ese nombre? Comparación CASE-INSENSITIVE y GLOBAL.

        🔴 LA GARANTÍA REAL ES EL ÍNDICE `ux_clientes_nombre_global (lower(nombre))` (migración
        108). Esto es para poder devolver un 409 legible en vez del error crudo de una
        constraint. Queda una ventana de carrera entre el chequeo y el INSERT que solo el índice
        cierra — por eso el índice no es opcional.

        ⚠️ Es MÁS ESTRICTO que antes: hasta la 108 dos empresas podían tener cada una su "Acme"
        y eran dos filas legítimas. Ahora "Acme" es uno solo para todo el sistema, que es la
        consecuencia directa de que el cliente no cuelgue de ninguna empresa.

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
            for c in self.find_all(incluir_inactivos=True)
        )

    def save(self, data: ClienteCreate) -> ClienteResponse:
        """Alta. NO manda `empresa_id`: el cliente no cuelga de ninguna empresa (migración 108).

        🔴 Contra la columna todavía NOT NULL este INSERT falla con 23502. Por eso la 108 tiene
        que correr ANTES del deploy de este código — está escrito en el encabezado de esa
        migración."""
        res = supabase_admin.table(_T).insert({"nombre": data.nombre.strip()}).execute()
        if not res.data:
            raise AppError("Error al crear el cliente", "DB_ERROR", 500)
        return ClienteResponse.model_validate(res.data[0])

    def update(self, id: str, patch: Dict[str, Any]) -> Optional[ClienteResponse]:
        """Aplica los campos de `patch` y devuelve la fila resultante."""
        if patch:
            supabase_admin.table(_T).update(patch).eq("id", id).execute()
        return self.find_by_id(id)

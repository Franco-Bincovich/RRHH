"""
Repositorio del catálogo de perfiles de puesto (migraciones 113/116). Acceso con supabase_admin.

Las ESCRITURAS viven en `_perfil_puesto_write_repo.py` y se delegan desde acá: la clase sigue
siendo la única puerta del service, así que ningún caller se entera del corte. El porqué de la
división está en el encabezado de ese archivo.

🔴 NO HAY BARRERA DE EMPRESA, Y NO ES UN OLVIDO. Un perfil no pertenece a ninguna empresa: el
catálogo es GLOBAL, como `clientes`. Ninguna query de este archivo filtra ni escribe
`empresa_id` —la columna no existe— y no hay que "agregarlo por consistencia" con los otros
repos: sería un filtro que dejaría el catálogo vacío sin ningún error.

🔴 NACE PAGINADO, Y ES LO ÚNICO QUE NO SE PUEDE AGREGAR DESPUÉS. Regla (d) de
`docs/DIAGNOSTICO-ESCALA.md`: sumarle paginación a un listado ya entregado obliga a tocar el
front, el export y el hook de filtros a la vez, y por eso hay 47 listados sin ella. El total
viaja por `count="exact"` en la MISMA query, así que no cuesta un round trip extra y el export
puede chequear su tope ANTES de traer nada grande.

🔴 NO HAY `delete`, Y TAMPOCO ES UN OLVIDO. `vacantes.perfil_puesto_id` es una FK
`ON DELETE SET NULL`: un borrado físico no falla, pero le arranca en silencio la trazabilidad a
toda vacante creada desde ese perfil. La baja es `activo=False`, que lo saca de los selects y
deja el vínculo intacto. Mismo criterio que `cliente_repo` y `tipos_ausencia_repo`.

Quien no encuentra devuelve `None`; el 404 lo arma el service.
"""
from typing import List, Optional, Tuple

from integrations.supabase_client import supabase_admin
from repositories._perfil_puesto_write_repo import actualizar, guardar
from schemas.perfil_puesto import (
    PerfilPuestoCreate, PerfilPuestoResponse, PerfilPuestoUpdate,
)

_T = "perfiles_puesto"


class PerfilPuestoRepo:
    def find_all(self, page: int = 1, page_size: int = 20, search: Optional[str] = None,
                 incluir_inactivos: bool = False) -> Tuple[List[PerfilPuestoResponse], int]:
        """Página del catálogo ordenada por nombre + el total REAL del filtro (sin paginar).

        `incluir_inactivos` es False por defecto porque el consumidor normal es el selector de
        la vacante, que no debe ofrecer un perfil dado de baja. La pantalla de ABM lo pide en
        True: ahí hay que verlos para poder reactivarlos. Mismo criterio que `ClienteRepo`.

        `search` va con `ilike` y comodines a los dos lados — es una BÚSQUEDA parcial, no una
        igualdad. Molde: `empleado_repo.find_all`. (Para el chequeo de duplicado, que sí es una
        igualdad, ver `existe_nombre`: ahí `ilike` sería un bug.)
        """
        q = supabase_admin.table(_T).select("*", count="exact")
        if not incluir_inactivos:
            q = q.eq("activo", True)
        if search:
            q = q.ilike("nombre", f"%{search}%")
        res = q.order("nombre").range((page - 1) * page_size, page * page_size - 1).execute()
        return ([PerfilPuestoResponse.model_validate(r) for r in (res.data or [])],
                res.count or 0)

    def find_by_id(self, id: str) -> Optional[PerfilPuestoResponse]:
        """El perfil, o None si no existe. El catálogo es global: no hay perfiles ajenos."""
        res = supabase_admin.table(_T).select("*").eq("id", id).maybe_single().execute()
        return PerfilPuestoResponse.model_validate(res.data) if (res and res.data) else None

    def existe_nombre(self, nombre: str, excepto_id: Optional[str] = None) -> bool:
        """¿Ya hay un perfil con ese nombre? Comparación CASE-INSENSITIVE y GLOBAL.

        🔴 LA GARANTÍA REAL ES EL ÍNDICE `ux_perfiles_puesto_nombre_global (lower(nombre))`.
        Esto existe para devolver un 409 legible en vez del error crudo de la constraint; queda
        una ventana de carrera entre el chequeo y el INSERT que solo el índice cierra.

        🔴 SE COMPARA EN PYTHON Y NO CON `.ilike()`, igual que en `cliente_repo` y por el mismo
        motivo: PostgREST interpreta `*` como comodín dentro de `ilike`, así que un perfil
        llamado "Analista*" haría matchear a "AnalistaSQL" y el alta se rechazaría por un
        duplicado que no existe. `casefold()` no tiene semántica de patrón.

        ⚠️ TRAE TODO EL CATÁLOGO, pero proyectando SOLO `id, nombre` — no `*`. Es un camino de
        escritura, no de lectura, y el catálogo son plantillas de puesto (decenas). Incluye los
        INACTIVOS: el índice único tampoco los excluye, así que dejarlos afuera daría un 409 de
        base después de haber dicho que el nombre estaba libre.
        """
        objetivo = nombre.strip().casefold()
        filas = supabase_admin.table(_T).select("id, nombre").execute().data or []
        return any(
            (f.get("nombre") or "").strip().casefold() == objetivo
            and str(f.get("id")) != str(excepto_id or "")
            for f in filas
        )

    def save(self, data: PerfilPuestoCreate,
             created_by: Optional[str] = None) -> PerfilPuestoResponse:
        """Alta. Delega en `_perfil_puesto_write_repo.guardar`."""
        return guardar(data, created_by)

    def update(self, id: str, data: PerfilPuestoUpdate) -> Optional[PerfilPuestoResponse]:
        """Edición parcial. Escribe y devuelve la fila resultante (o None si no existe)."""
        actualizar(id, data)
        return self.find_by_id(id)

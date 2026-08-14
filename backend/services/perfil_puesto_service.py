"""
Servicio del catálogo de perfiles de puesto (migraciones 113/116).
Flujo: router → service → repository → DB

QUÉ ES UN PERFIL. Una PLANTILLA para armar búsquedas: Capital Humano la carga a mano y la reusa.
Al crear una vacante se elige un perfil y los campos se COPIAN — editar el perfil después NO
cambia las vacantes ya creadas. Ese puente es una sesión aparte; acá vive solo el CRUD.

🔴 ES DEL GRUPO: NO HAY BARRERA DE EMPRESA EN NINGÚN MÉTODO, y no es un olvido. La tabla no
tiene `empresa_id` (ni `area_id`) a propósito; el área se elige al crear la vacante. Buscar acá
un `ensure_*_de_empresa` es buscar algo que no corresponde: no existen perfiles ajenos que
ocultar, así que el 404 de "no existe" no tiene un gemelo del que ser indistinguible.

🔴 LA BAJA ES LÓGICA (`activo=False`), NO HAY DELETE FÍSICO. `vacantes.perfil_puesto_id` es una
FK `ON DELETE SET NULL`: un borrado físico no falla —y por eso es peligroso— pero le arranca en
silencio la trazabilidad a toda vacante creada desde ese perfil. La baja lo saca de los selects
y deja el vínculo intacto. Es reversible desde la pantalla.

🔴 AUDITA LAS TRES ESCRITURAS, Y ES TODO O NADA. `tests/test_auditoria_coherente.py` barre por
AST y exige que un módulo que audita ALGUNA operación las audite TODAS. Los tres eventos van con
`empresa_id` NULL: un perfil es del grupo y no tiene empresa que declarar — ver
`_audit_payloads_perfiles`.

Los literales de error viven en `schemas/_perfil_puesto_campos` y se IMPORTAN: son texto que ve
alguien de Capital Humano, y el front sirve el mismo catálogo por endpoint.
"""
from math import ceil
from typing import Optional
from uuid import UUID

from repositories.perfil_puesto_repo import PerfilPuestoRepo
from schemas._perfil_puesto_campos import (
    MSG_NO_ENCONTRADO, MSG_NOMBRE_DUPLICADO, MSG_NOMBRE_REQUERIDO,
)
from schemas.perfil_puesto import (
    PerfilPuestoCreate, PerfilPuestoListResponse, PerfilPuestoResponse, PerfilPuestoUpdate,
)
from services._audit_payloads_perfiles import (
    payload_alta_perfil, payload_baja_perfil, payload_update_perfil,
)
from services._limite_export import LIMITE_FILAS_EXPORT, verificar_limite_export
from services._perfiles_puesto_export import construir_filas_export
from services.audit_service import AuditService
from services.export import Descarga, build_export
from utils.errors import AppError
from utils.logger import logger

_NO_ENCONTRADO = (MSG_NO_ENCONTRADO, "PERFIL_PUESTO_NOT_FOUND", 404)


class PerfilPuestoService:
    def __init__(self, repo: Optional[PerfilPuestoRepo] = None,
                 audit: Optional[AuditService] = None) -> None:
        self._repo = repo or PerfilPuestoRepo()
        self._audit = audit or AuditService()

    def get_perfiles(self, page: int = 1, page_size: int = 20, search: Optional[str] = None,
                     incluir_inactivos: bool = False) -> PerfilPuestoListResponse:
        """Página del catálogo, por nombre. Es GLOBAL: el sidebar de empresa no lo acota.

        `total_pages` se deriva del total REAL del filtro, no del largo de la página: con 0
        filas devuelve 1 (hay una página, y está vacía), que es lo que el paginador necesita
        para no dibujar "página 1 de 0".
        """
        items, total = self._repo.find_all(page, page_size, search, incluir_inactivos)
        return PerfilPuestoListResponse(
            items=items, total=total, page=page, page_size=page_size,
            total_pages=max(1, ceil(total / page_size)) if page_size else 1,
        )

    def exportar(self, formato: str = "excel", search: Optional[str] = None,
                 incluir_inactivos: bool = False) -> Descarga:
        """Exporta el catálogo con los MISMOS filtros que el listado, SIN paginar.

        Pide una sola página del tamaño del tope, así el control actúa antes de cargar nada más
        grande que eso: el total viene por `count="exact"` y respeta los filtros, o sea que
        `verificar_limite_export` mira el número real y no el largo de lo que ya se trajo.
        """
        items, total = self._repo.find_all(1, LIMITE_FILAS_EXPORT, search, incluir_inactivos)
        verificar_limite_export(total)
        datos = {"Perfiles de puesto": construir_filas_export(items)}
        return build_export(nombre="Perfiles de puesto", datos=datos,
                            filename_base="perfiles_puesto", formato=formato)

    def get_perfil(self, id: UUID) -> PerfilPuestoResponse:
        """Detalle. El catálogo es global: no hay perfiles ajenos que ocultar."""
        perfil = self._repo.find_by_id(str(id))
        if not perfil:
            raise AppError(*_NO_ENCONTRADO)
        return perfil

    def create_perfil(self, data: PerfilPuestoCreate,
                      usuario_id: Optional[str]) -> PerfilPuestoResponse:
        """Alta. Sin empresa: el perfil es del grupo.

        Raises:
            AppError: NOMBRE_REQUERIDO (422) si el nombre es solo espacios —Pydantic ya rechaza
                la cadena vacía, pero `"   "` pasa `min_length` y strippea a nada—,
                PERFIL_DUPLICADO (409) si el nombre ya existe en el sistema.
        """
        self._validar_nombre(data.nombre)
        perfil = self._repo.save(data, usuario_id)
        self._audit.registrar(**payload_alta_perfil(perfil, usuario_id))
        logger.info("Perfil de puesto creado", extra={"perfil_id": str(perfil.id)})
        return perfil

    def update_perfil(self, id: UUID, data: PerfilPuestoUpdate,
                      usuario_id: Optional[str] = None) -> PerfilPuestoResponse:
        """Edición parcial. Lee el PRIOR antes de escribir: sin él no hay diff que auditar."""
        prior = self._repo.find_by_id(str(id))
        if not prior:
            raise AppError(*_NO_ENCONTRADO)
        if data.nombre is not None:
            self._validar_nombre(data.nombre, excepto_id=str(id))
            data = data.model_copy(update={"nombre": data.nombre.strip()})
        nuevo = self._repo.update(str(id), data)
        if not nuevo:
            raise AppError(*_NO_ENCONTRADO)
        self._audit.registrar(**payload_update_perfil(prior, nuevo, usuario_id))
        logger.info("Perfil de puesto actualizado", extra={"perfil_id": str(id)})
        return nuevo

    def delete_perfil(self, id: UUID, usuario_id: Optional[str] = None) -> None:
        """Baja LÓGICA. Ver el encabezado del módulo: no hay borrado físico."""
        prior = self._repo.find_by_id(str(id))
        if not prior:
            raise AppError(*_NO_ENCONTRADO)
        if not self._repo.update(str(id), PerfilPuestoUpdate(activo=False)):
            raise AppError(*_NO_ENCONTRADO)
        self._audit.registrar(**payload_baja_perfil(prior, usuario_id))
        logger.info("Perfil de puesto dado de baja", extra={"perfil_id": str(id)})

    def _validar_nombre(self, nombre: str, excepto_id: Optional[str] = None) -> None:
        """Nombre no vacío y único en TODO el sistema (el catálogo es global).

        Raises:
            AppError: NOMBRE_REQUERIDO (422) · PERFIL_DUPLICADO (409).
        """
        if not nombre.strip():
            raise AppError(MSG_NOMBRE_REQUERIDO, "NOMBRE_REQUERIDO", 422)
        if self._repo.existe_nombre(nombre, excepto_id=excepto_id):
            raise AppError(MSG_NOMBRE_DUPLICADO, "PERFIL_DUPLICADO", 409)

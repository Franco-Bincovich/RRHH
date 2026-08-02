"""
Servicio del catálogo de tipos de ausencia.
Flujo: router → service → repository → DB

Desde la migración 085 el catálogo es global + por empresa: los 4 tipos base son globales y
cada empresa puede sumar los suyos. Las lecturas devuelven los globales más los propios.

🔴 NO EXISTE BAJA FÍSICA, Y NO ES UN DESCUIDO. solicitudes_ausencia.tipo_id es una FK sin
ON DELETE: borrar un tipo en uso falla, y si algún día no fallara se llevaría el historial de
ausencias con él. La baja es `activo=False`: saca el tipo de los selects y deja intactas las
ausencias que ya lo usan, que siguen mostrando su nombre. Por eso el router expone PATCH y
NO expone DELETE.
"""
from typing import Optional
from uuid import UUID

from repositories.tipos_ausencia_repo import TiposAusenciaRepo
from schemas.ausencias import (
    TipoAusenciaCreate, TipoAusenciaListResponse, TipoAusenciaResponse,
)
from schemas.configuracion import TipoAusenciaUpdate
from utils.errors import AppError


class TiposAusenciaService:
    def __init__(self, repo: Optional[TiposAusenciaRepo] = None) -> None:
        self._repo = repo or TiposAusenciaRepo()

    def get_tipos(
        self, empresa_id: Optional[UUID] = None, incluir_inactivos: bool = False,
    ) -> TipoAusenciaListResponse:
        """Tipos visibles para la empresa activa: los globales más los suyos."""
        items = self._repo.find_all(str(empresa_id) if empresa_id else None, incluir_inactivos)
        return TipoAusenciaListResponse(items=items, total=len(items))

    def create_tipo(
        self, data: TipoAusenciaCreate, empresa_id: Optional[UUID] = None,
    ) -> TipoAusenciaResponse:
        """
        Crea un tipo para la empresa activa (o global si no hay empresa en el contexto).

        Raises:
            AppError: TIPO_NOMBRE_VACIO (422) si el nombre está en blanco.
            AppError: TIPO_DUPLICADO (422) si el nombre ya existe en ese alcance.
        """
        if not data.nombre.strip():
            raise AppError("El nombre del tipo no puede estar vacío", "TIPO_NOMBRE_VACIO", 422)
        try:
            return self._repo.create(data.nombre.strip(), str(empresa_id) if empresa_id else None)
        except AppError:
            raise
        except Exception:
            raise AppError("El tipo de ausencia ya existe", "TIPO_DUPLICADO", 422)

    def update_tipo(
        self, tipo_id: UUID, data: TipoAusenciaUpdate, empresa_id: Optional[UUID],
    ) -> TipoAusenciaResponse:
        """
        Edita un tipo: nombre, alta/baja lógica y si computa como ausentismo.

        Barrera de empresa: un tipo PROPIO de otra empresa da el mismo 404 que uno inexistente.
        Los globales sí se pueden editar desde cualquier empresa — son de todas, y esa es la
        decisión: hoy hay un solo equipo de RRHH operando todas las empresas.

        Raises:
            AppError: TIPO_NOT_FOUND (404) si no existe o es de otra empresa.
            AppError: TIPO_BASE_NO_DESACTIVABLE (422) al intentar dar de baja un tipo base.
            AppError: TIPO_NOMBRE_VACIO (422) si el nombre nuevo está en blanco.
        """
        actual = self._repo.find_by_id(str(tipo_id))
        propietaria = actual.get("empresa_id") if actual else None
        if not actual or (propietaria and propietaria != str(empresa_id)):
            raise AppError("Tipo de ausencia no encontrado", "TIPO_NOT_FOUND", 404)

        cambios = data.model_dump(exclude_unset=True)
        if cambios.get("activo") is False and actual.get("es_base"):
            # Los 4 base son el vocabulario mínimo con el que se cargó todo el histórico.
            # Sin ellos el formulario de ausencias podría quedar sin una sola opción.
            raise AppError(
                "Los tipos base no se pueden desactivar", "TIPO_BASE_NO_DESACTIVABLE", 422,
            )
        if "nombre" in cambios:
            if not cambios["nombre"].strip():
                raise AppError("El nombre del tipo no puede estar vacío", "TIPO_NOMBRE_VACIO", 422)
            cambios["nombre"] = cambios["nombre"].strip()
        if not cambios:
            return TipoAusenciaResponse.model_validate(actual)
        return self._repo.update(str(tipo_id), cambios)

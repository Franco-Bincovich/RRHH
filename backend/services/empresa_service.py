"""
Servicio de empresas. Lógica de negocio del módulo de Empresas.
Flujo: router → service → repository → DB
Validación de CUIT aquí (no en Pydantic) para devolver AppError 400 en lugar de 422.
"""
import re
from typing import Optional

from repositories.empresa_repo import EmpresaRepo
from schemas.empresa import EmpresaCreate, EmpresaListResponse, EmpresaResponse, EmpresaUpdate
from services._audit_payloads_rrhh import payload_alta_empresa, payload_toggle_empresa
from services._empresa_logo import subir_logo as _subir_logo
from services._empresas_export import construir_filas_export
from services._limite_export import verificar_limite_export
from services.audit_service import AuditService
from services.export import Descarga, build_export
from utils.errors import AppError
from utils.logger import logger

_CUIT_RE = re.compile(r"^\d{2}-\d{8}-\d{1}$")


def _validate_cuit(cuit: Optional[str]) -> None:
    if cuit is not None and not _CUIT_RE.match(cuit):
        raise AppError(
            "Formato de CUIT inválido — debe ser XX-XXXXXXXX-X",
            "CUIT_INVALIDO",
            400,
        )


class EmpresaService:
    def __init__(self, repo: Optional[EmpresaRepo] = None, audit: Optional[AuditService] = None) -> None:
        self._repo = repo or EmpresaRepo()
        self._audit = audit or AuditService()

    def list_empresas(self) -> EmpresaListResponse:
        """Retorna todas las empresas ordenadas por nombre."""
        items = self._repo.find_all()
        return EmpresaListResponse(items=items, total=len(items))

    def exportar(self, formato: str = "excel") -> Descarga:
        """Exporta el listado de empresas con columnas legibles (sin UUIDs).

        Va por el MISMO `find_all` que el listado, así que el archivo no puede traer filas que
        la pantalla no muestre. El listado no tiene filtros: no hay ninguno que se pueda perder
        entre las dos puntas. Qué columnas salen y por qué, en _empresas_export.
        """
        items = self._repo.find_all()
        verificar_limite_export(len(items))
        datos = {"Empresas": construir_filas_export(items)}
        return build_export(nombre="Empresas", datos=datos, filename_base="empresas", formato=formato)

    def get_empresa(self, id: str) -> EmpresaResponse:
        """Retorna una empresa por ID. Lanza 404 si no existe."""
        empresa = self._repo.find_by_id(id)
        if not empresa:
            raise AppError("Empresa no encontrada", "EMPRESA_NOT_FOUND", 404)
        return empresa

    def create_empresa(self, data: EmpresaCreate, created_by: str) -> EmpresaResponse:
        """
        Crea una nueva empresa.

        Args:
            data: Datos de la empresa (nombre requerido, resto opcional).
            created_by: ID del usuario que realiza la operación.

        Returns:
            EmpresaResponse con el registro creado.

        Raises:
            AppError: CUIT_INVALIDO (400) si el CUIT no cumple el formato.
        """
        _validate_cuit(data.cuit)
        empresa = self._repo.save(data)
        self._audit.registrar(**payload_alta_empresa(empresa, created_by))
        logger.info("Empresa creada", extra={"empresa_id": empresa.id, "created_by": created_by})
        return empresa

    def update_empresa(self, id: str, data: EmpresaUpdate) -> EmpresaResponse:
        """
        Actualiza los datos de una empresa existente (actualización parcial).

        Args:
            id: UUID de la empresa.
            data: Campos a actualizar — solo los no-None se aplican.

        Returns:
            EmpresaResponse actualizado.

        Raises:
            AppError: EMPRESA_NOT_FOUND (404) o CUIT_INVALIDO (400).
        """
        _validate_cuit(data.cuit)
        empresa = self._repo.update(id, data)
        if not empresa:
            raise AppError("Empresa no encontrada", "EMPRESA_NOT_FOUND", 404)
        logger.info("Empresa actualizada", extra={"empresa_id": id})
        return empresa

    def toggle_activa(self, id: str, activa: bool, usuario_id: Optional[str] = None) -> EmpresaResponse:
        """
        Activa/desactiva una empresa y registra el evento de auditoría.
        Camino dedicado (no el PUT genérico) para auditar solo el toggle de estado.

        Raises:
            AppError: EMPRESA_NOT_FOUND (404) si la empresa no existe.
        """
        empresa = self._repo.update(id, EmpresaUpdate(activa=activa))
        if not empresa:
            raise AppError("Empresa no encontrada", "EMPRESA_NOT_FOUND", 404)
        self._audit.registrar(**payload_toggle_empresa(empresa.id, activa, usuario_id))
        logger.info("Empresa activa cambiada", extra={"empresa_id": id, "activa": activa})
        return empresa

    def upload_logo(
        self, id: str, content: bytes, filename: str, content_type: str,
        usuario_id: Optional[str] = None,
    ) -> EmpresaResponse:
        """Sube el logo al bucket 'avatars' y actualiza logo_url.
        Ver services/_empresa_logo.subir_logo (extraído por límite de líneas)."""
        return _subir_logo(self._repo, self._audit, id, content, filename, content_type, usuario_id)

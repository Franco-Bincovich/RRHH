"""
Servicio de empresas. Lógica de negocio del módulo de Empresas.
Flujo: router → service → repository → DB
Validación de CUIT aquí (no en Pydantic) para devolver AppError 400 en lugar de 422.
"""
import re
import uuid
from typing import Optional

from integrations.supabase_client import supabase_admin
from repositories.empresa_repo import EmpresaRepo
from schemas.empresa import EmpresaCreate, EmpresaListResponse, EmpresaResponse, EmpresaUpdate
from services._audit_payloads_rrhh import (
    payload_alta_empresa, payload_logo_empresa, payload_toggle_empresa,
)
from services.audit_service import AuditService
from utils.errors import AppError
from utils.logger import logger

_CUIT_RE = re.compile(r"^\d{2}-\d{8}-\d{1}$")
_BUCKET = "avatars"


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
        """
        Sube el logo al bucket 'avatars' de Supabase Storage y actualiza logo_url.
        Genera una ruta única con UUID para evitar colisiones. Audita el cambio.

        Args:
            id: UUID de la empresa.
            content: Bytes del archivo de imagen.
            filename: Nombre original del archivo (para extraer extensión).
            content_type: MIME type del archivo (debe empezar con 'image/').
            usuario_id: quién hizo el cambio (trazabilidad del evento de auditoría).

        Returns:
            EmpresaResponse con logo_url actualizado.

        Raises:
            AppError: 404 si la empresa no existe, 400 si el archivo no es imagen.
        """
        # El find_by_id ya existía como guarda del 404; ahora además se CONSERVA, porque el
        # logo anterior solo se puede leer antes del UPDATE. Cero queries nuevas.
        previa = self._repo.find_by_id(id)
        if not previa:
            raise AppError("Empresa no encontrada", "EMPRESA_NOT_FOUND", 404)
        if not content_type.startswith("image/"):
            raise AppError("El archivo debe ser una imagen", "INVALID_FILE_TYPE", 400)
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
        path = f"logos/{id}/{uuid.uuid4()}.{ext}"
        supabase_admin.storage.from_(_BUCKET).upload(
            path=path,
            file=content,
            file_options={"content-type": content_type},
        )
        logo_url = supabase_admin.storage.from_(_BUCKET).get_public_url(path)
        empresa = self._repo.set_logo_url(id, logo_url)
        if not empresa:
            raise AppError("Error al actualizar el logo", "LOGO_UPDATE_ERROR", 500)
        self._audit.registrar(**payload_logo_empresa(empresa, previa.logo_url, usuario_id))
        logger.info("Logo de empresa actualizado", extra={"empresa_id": id, "path": path})
        return empresa

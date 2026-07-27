"""
Servicio de adjuntos genéricos (polimórficos). Flujo: router → service → repository.

Solo almacena/descarga; NO lee el contenido del archivo. Sube al bucket privado
'documentos' (patrón del certificado de capacitación) y guarda el storage_path;
la descarga se resuelve con signed URL temporal. Delete SOFT (el objeto queda en Storage).

Gating APP-LEVEL dinámico: el permiso depende de la ENTIDAD del adjunto (empleado→EMPLEADOS,
vacacion→VACACIONES, …). Como el permiso depende del dato (no es estático), no puede usarse
la dependency require_permission; se resuelve acá con puede(rol, seccion, accion) y el mapeo
_ENTIDAD_SECCION. Nada de RLS del modelo viejo. La auditoría nunca rompe la operación.
"""
import uuid as _uuid
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories.adjunto_repo import AdjuntoRepo
from schemas.adjunto import Adjunto
from services._adjunto_padres import ensure_padre_de_empresa
from services._audit_payloads_rrhh import payload_alta_adjunto, payload_baja_adjunto
from services.audit_service import AuditService
from utils.errors import AppError
from utils.files import ALLOWED_TYPES_ADJUNTO, MAX_SIZE_ADJUNTO, validate_upload
from utils.logger import logger
from utils.permisos import Accion, Seccion, puede

_BUCKET = "documentos"

# Mapeo entidad→Seccion: de dónde hereda el permiso cada adjunto. Ampliar al sumar entidades.
_ENTIDAD_SECCION = {
    "empleado": Seccion.EMPLEADOS,
    "vacacion": Seccion.VACACIONES,
    "ausencia": Seccion.AUSENCIAS,
    "evaluacion": Seccion.EVALUACIONES,
    "offboarding": Seccion.OFFBOARDING,
    "vacante": Seccion.VACANTES,
}


class AdjuntoService:
    def __init__(self, repo: Optional[AdjuntoRepo] = None, audit: Optional[AuditService] = None, padre_resolvers: Optional[dict] = None) -> None:
        self._repo = repo or AdjuntoRepo()
        self._audit = audit or AuditService()
        self._padres = padre_resolvers  # None = RESOLVERS reales; dobles en test

    def _seccion(self, entidad: str) -> Seccion:
        """Resuelve la sección de una entidad. Raises ENTIDAD_INVALIDA (400) si no está mapeada."""
        seccion = _ENTIDAD_SECCION.get(entidad)
        if seccion is None:
            raise AppError(f"Entidad no soportada para adjuntos: {entidad}", "ENTIDAD_INVALIDA", 400)
        return seccion

    def _gate(self, rol: Optional[str], entidad: str, accion: Accion) -> None:
        """Gatea por la sección de la entidad. Raises FORBIDDEN (403) si el rol no alcanza."""
        if not puede(rol, self._seccion(entidad), accion):
            raise AppError("No tenés permiso para realizar esta acción", "FORBIDDEN", 403)

    def _get_owned(self, id: str, empresa_id: Optional[UUID]) -> Adjunto:
        """Carga el adjunto validando pertenencia a la empresa. Raises ADJUNTO_NOT_FOUND (404)."""
        adj = self._repo.find_by_id(id)
        # empresa_id NULL = fila legacy sin empresa asignada (las nuevas la heredan del padre):
        # se bloquea SIEMPRE, no solo en modo empresa. Antes era visible en consolidado.
        if not adj or not adj.empresa_id or (empresa_id and str(adj.empresa_id) != str(empresa_id)):
            raise AppError("Adjunto no encontrado", "ADJUNTO_NOT_FOUND", 404)
        return adj

    def subir(
        self, entidad: str, entidad_id: UUID, empresa_id: Optional[UUID], content: bytes,
        filename: str, content_type: str, categoria: Optional[str], descripcion: Optional[str],
        rol: Optional[str], usuario_id: Optional[str],
    ) -> Adjunto:
        """Valida (permiso → PADRE → archivo), sube al bucket privado y persiste. Audita alta.
        La empresa del adjunto sale del PADRE, no del header: así no depende del selector del
        sidebar y no se generan filas con empresa_id NULL (ver _adjunto_padres).
        Raises: ENTIDAD_INVALIDA (400), FORBIDDEN (403), PADRE_NOT_FOUND (404),
        INVALID_FILE_TYPE/FILE_TOO_LARGE (400)."""
        self._gate(rol, entidad, Accion.WRITE)
        empresa_padre = ensure_padre_de_empresa(entidad, entidad_id, empresa_id, self._padres)
        validate_upload(content, content_type, ALLOWED_TYPES_ADJUNTO, MAX_SIZE_ADJUNTO, "archivo")
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
        path = f"adjuntos/{entidad}/{entidad_id}/{_uuid.uuid4()}.{ext}"
        supabase_admin.storage.from_(_BUCKET).upload(
            path=path, file=content, file_options={"content-type": content_type}
        )
        adj = self._repo.crear({
            "entidad": entidad, "entidad_id": str(entidad_id),
            "empresa_id": empresa_padre,
            "bucket": _BUCKET, "storage_path": path, "nombre_archivo": filename,
            "mime_type": content_type, "tamano_bytes": len(content),
            "categoria": categoria, "descripcion": descripcion, "subido_por": usuario_id,
        })
        self._audit.registrar(**payload_alta_adjunto(adj, usuario_id))
        logger.info("Adjunto subido", extra={"adjunto_id": adj.id, "entidad": entidad})
        return adj

    def listar(
        self, entidad: str, entidad_id: UUID, empresa_id: Optional[UUID], rol: Optional[str]
    ) -> List[Adjunto]:
        """Lista los adjuntos activos de una entidad. Raises ENTIDAD_INVALIDA (400), FORBIDDEN (403)."""
        self._gate(rol, entidad, Accion.READ)
        return self._repo.find_by_entidad(entidad, str(entidad_id), empresa_id)

    def url_descarga(self, id: str, empresa_id: Optional[UUID], rol: Optional[str]) -> str:
        """Genera signed URL (3600 s) para descargar el adjunto. Raises ADJUNTO_NOT_FOUND (404), FORBIDDEN (403)."""
        adj = self._get_owned(id, empresa_id)
        self._gate(rol, adj.entidad, Accion.READ)
        res = supabase_admin.storage.from_(adj.bucket).create_signed_url(path=adj.storage_path, expires_in=3600)
        return res["signedURL"]

    def marcar_principal(
        self, id: str, principal: bool, empresa_id: Optional[UUID], rol: Optional[str]
    ) -> Adjunto:
        """Marca (o desmarca) un adjunto como principal de su entidad. Al marcar, desmarca los
        hermanos para garantizar UNA sola principal por entidad. Raises ADJUNTO_NOT_FOUND (404),
        FORBIDDEN (403)."""
        adj = self._get_owned(id, empresa_id)
        self._gate(rol, adj.entidad, Accion.WRITE)
        if principal:
            self._repo.desmarcar_principales(adj.entidad, adj.entidad_id)
        self._repo.set_principal(id, principal)
        logger.info("Adjunto principal", extra={"adjunto_id": id, "principal": principal})
        return self._repo.find_by_id(id)  # type: ignore[return-value]

    def eliminar(self, id: str, empresa_id: Optional[UUID], rol: Optional[str], usuario_id: Optional[str]) -> None:
        """Soft delete (estado='eliminado') + audita baja_adjunto. NO borra el objeto de Storage.
        Raises ADJUNTO_NOT_FOUND (404), FORBIDDEN (403)."""
        adj = self._get_owned(id, empresa_id)
        self._gate(rol, adj.entidad, Accion.WRITE)
        self._repo.marcar_eliminado(id)
        self._audit.registrar(**payload_baja_adjunto(adj, usuario_id))
        logger.info("Adjunto eliminado", extra={"adjunto_id": id})

    def eliminar_todos_por_entidad(
        self, entidad: str, entidad_id: str, empresa_id: Optional[UUID],
        rol: Optional[str], usuario_id: Optional[str],
    ) -> None:
        """Borra FÍSICAMENTE del Storage + soft-delete de TODOS los adjuntos activos de una entidad
        (al eliminar la entidad dueña, ej. vacante). Si el remove físico falla → log y sigue: nunca
        deja la fila colgada por un fallo de Storage. Raises FORBIDDEN (403)."""
        self._gate(rol, entidad, Accion.WRITE)
        for adj in self._repo.find_by_entidad(entidad, entidad_id, empresa_id):
            if adj.storage_path:  # guard: nunca remove sobre key vacía; usa la key de la DB tal cual
                try:
                    supabase_admin.storage.from_(adj.bucket).remove([adj.storage_path])
                except Exception as exc:  # storage falló: se conserva el flujo, objeto huérfano
                    logger.error("Storage remove falló (adjunto)", extra={"adjunto_id": adj.id, "error": str(exc)})
            self._repo.marcar_eliminado(adj.id)
            self._audit.registrar(**payload_baja_adjunto(adj, usuario_id))

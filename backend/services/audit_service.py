"""
Servicio de auditoría (T18). Captura app-level de eventos de negocio.
Flujo: service de negocio → AuditService.registrar → AuditRepo → DB.

registrar() NUNCA propaga: la auditoría es secundaria a la operación de negocio.
Un evento de audit perdido es mejor que tirar abajo una alta de empleado.
"""
from datetime import date, datetime
from typing import Optional, Tuple
from uuid import UUID

from repositories.audit_repo import AuditRepo
from schemas.auditoria import ACCIONES, AuditLogListResponse
from services._auditoria_export import construir_filas_export
from services._limite_export import LIMITE_FILAS_EXPORT, verificar_limite_export
from services.export import Descarga, build_export
from utils.logger import logger


def _jsonable(value: object) -> object:
    """Convierte recursivamente UUID→str y date/datetime→isoformat para que el
    payload sea JSON-serializable antes de ir a las columnas JSONB."""
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


class AuditService:
    def __init__(self, repo: Optional[AuditRepo] = None) -> None:
        self._repo = repo or AuditRepo()

    def registrar(
        self,
        *,
        usuario_id: Optional[str],
        entidad: str,
        registro_id: str,
        accion: str,
        evento: str,
        empresa_id: Optional[str] = None,
        datos_anteriores: Optional[dict] = None,
        datos_nuevos: Optional[dict] = None,
    ) -> None:
        """Registra un evento de auditoría. NUNCA propaga: ante fallo loguea y retorna.

        accion debe ser un verbo CRUD válido (INSERT/UPDATE/DELETE); evento lleva la
        semántica de negocio. tabla se setea = entidad (columna legacy del trigger).
        Todo lo que va al payload se vuelve JSON-serializable (UUID/fechas → str)."""
        try:
            if accion not in ACCIONES:
                logger.error("audit_accion_invalida", extra={"accion": accion, "evento": evento})
                return
            payload = {
                "tabla": entidad,
                "entidad": entidad,
                "evento": evento,
                "accion": accion,
                "registro_id": str(registro_id),
                "usuario_id": str(usuario_id) if usuario_id else None,
                "empresa_id": str(empresa_id) if empresa_id else None,
                "datos_anteriores": _jsonable(datos_anteriores) if datos_anteriores else None,
                "datos_nuevos": _jsonable(datos_nuevos) if datos_nuevos else None,
            }
            self._repo.registrar(payload)
        except Exception as e:
            logger.error("audit_registrar_fallo", extra={"error": str(e), "evento": evento})
            return

    def listar(
        self,
        empresa_id: Optional[UUID] = None,
        usuario_id: Optional[UUID] = None,
        entidad: Optional[str] = None,
        evento: Optional[str] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
        registro_id: Optional[str] = None,
    ) -> AuditLogListResponse:
        """Retorna una página de eventos de auditoría filtrada. total = count real del filtro."""
        items, total = self._repo.listar(
            empresa_id, usuario_id, entidad, evento, fecha_desde, fecha_hasta, page, page_size,
            registro_id=registro_id,
        )
        return AuditLogListResponse(items=items, total=total)

    def exportar(
        self,
        empresa_id: Optional[UUID] = None,
        usuario_id: Optional[UUID] = None,
        entidad: Optional[str] = None,
        evento: Optional[str] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        registro_id: Optional[str] = None,
        formato: str = "excel",
    ) -> Descarga:
        """Exporta el listado de auditoría con los MISMOS filtros que `listar` — lo que se ve
        en la pantalla es lo que sale en el archivo.

        No se pagina (invariante del repo), pero se pide una sola página del tamaño del tope:
        así el `count` exacto llega para decidir, sin traerse de más si el pedido es enorme.
        """
        items, total = self._repo.listar(
            empresa_id, usuario_id, entidad, evento, fecha_desde, fecha_hasta,
            page=1, page_size=LIMITE_FILAS_EXPORT, registro_id=registro_id,
        )
        verificar_limite_export(total)
        return build_export(
            nombre="Auditoría", datos={"Auditoría": construir_filas_export(items)},
            filename_base="auditoria", formato=formato,
        )

    @staticmethod
    def _diff(antes: dict, despues: dict) -> Tuple[dict, dict]:
        """Devuelve solo los campos que cambiaron como (antes, despues), JSON-serializable.

        Helper para los call-sites de instrumentación (18.4): evita guardar el row
        entero cuando solo cambió un campo."""
        cambios_antes: dict = {}
        cambios_despues: dict = {}
        for key in set(antes) | set(despues):
            a = antes.get(key)
            d = despues.get(key)
            if a != d:
                cambios_antes[key] = _jsonable(a)
                cambios_despues[key] = _jsonable(d)
        return cambios_antes, cambios_despues

"""
Servicio de horas de proyecto (carga interna por RRHH).
Flujo: router → service → repository → DB

Reglas:
  - valor_hora_snapshot se congela desde proyecto_asignaciones.valor_hora al insertar.
  - empresa_id (dueña) y empleado_empresa_id se denormalizan desde la asignación.
  - Registros inmutables: no hay update, solo delete + re-insert para corregir.
"""
from typing import Optional
from uuid import UUID

from repositories.horas_repo import HorasRepo
from repositories.proyecto_asignaciones_repo import AsignacionesRepo
from repositories.proyectos_repo import ProyectosRepo
from schemas.proyectos import HoraCreate, HoraListResponse, HoraResponse
from utils.errors import AppError
from utils.logger import logger


class HorasService:
    def __init__(
        self,
        repo: Optional[HorasRepo] = None,
        asig_repo: Optional[AsignacionesRepo] = None,
        proyectos_repo: Optional[ProyectosRepo] = None,
    ) -> None:
        self._repo = repo or HorasRepo()
        self._asig = asig_repo or AsignacionesRepo()
        self._proyectos = proyectos_repo or ProyectosRepo()

    def get_by_proyecto(self, proyecto_id: UUID, page: int = 1, page_size: int = 20,
                        empresa_id: Optional[UUID] = None) -> HoraListResponse:
        """Una página de horas del proyecto, más reciente primero. total = count real.

        Valida el proyecto contra la empresa activa antes de leer (mismo patrón que cargar/delete
        de este service): las horas se alcanzan por proyecto_id, así que gatear el proyecto cubre
        la cadena. 404 idéntico al de proyecto inexistente.
        """
        if not self._proyectos.find_by_id(str(proyecto_id), empresa_id):
            raise AppError("Proyecto no encontrado", "PROYECTO_NOT_FOUND", 404)
        rows, total = self._repo.find_by_proyecto(str(proyecto_id), page, page_size)
        return HoraListResponse(items=rows, total=total)

    def get_by_asignacion(self, asignacion_id: UUID) -> HoraListResponse:
        """Horas de una asignación específica."""
        items = self._repo.find_by_asignacion(str(asignacion_id))
        return HoraListResponse(items=items, total=len(items))

    def cargar(self, proyecto_id: UUID, data: HoraCreate, cargado_por: Optional[str] = None, empresa_id: Optional[UUID] = None) -> HoraResponse:
        """
        Registra horas en una asignación del proyecto.
        Congela valor_hora_snapshot copiándolo de la asignación en el momento del INSERT.
        empresa_id (dueña) se toma del proyecto. empleado_empresa_id de la asignación.

        Raises:
            AppError: PROYECTO_NOT_FOUND (404), ASIGNACION_NOT_FOUND (404),
                      ASIGNACION_DE_OTRO_PROYECTO (422), ASIGNACION_INACTIVA (422).
        """
        # Ownership: el proyecto debe pertenecer a la empresa del contexto (None = todas)
        if not self._proyectos.find_by_id(str(proyecto_id), empresa_id):
            raise AppError("Proyecto no encontrado", "PROYECTO_NOT_FOUND", 404)
        asig = self._asig.find_by_id(str(data.asignacion_id))
        if not asig:
            raise AppError("Asignación no encontrada", "ASIGNACION_NOT_FOUND", 404)
        if str(asig.proyecto_id) != str(proyecto_id):
            raise AppError("La asignación no pertenece a este proyecto", "ASIGNACION_DE_OTRO_PROYECTO", 422)
        if not asig.activo:
            raise AppError("La asignación está inactiva", "ASIGNACION_INACTIVA", 422)

        empresa_id = self._proyectos.find_empresa_for(str(proyecto_id)) or str(asig.empleado_empresa_id)

        row = self._repo.save(
            asignacion_id=str(data.asignacion_id),
            proyecto_id=str(proyecto_id),
            empresa_id=empresa_id,
            empleado_empresa_id=str(asig.empleado_empresa_id),
            fecha=str(data.fecha),
            horas=data.horas,
            valor_hora_snapshot=asig.valor_hora,   # ← snapshot congelado al insertar
            descripcion=data.descripcion,
            cargado_por=cargado_por,
        )
        logger.info("Horas registradas", extra={
            "proyecto_id": str(proyecto_id),
            "asignacion_id": str(data.asignacion_id),
            "horas": data.horas,
            "snapshot": asig.valor_hora,
        })
        return row

    def delete(self, hora_id: UUID, empresa_id: Optional[UUID] = None) -> None:
        """Elimina un registro de horas (única forma de corregir un error). Valida ownership: proyecto dueño debe coincidir con empresa_id."""
        # Resolver el proyecto padre para validar ownership antes de borrar
        proyecto_id = self._repo.find_proyecto_id(str(hora_id))
        if not proyecto_id:
            raise AppError("Registro de horas no encontrado", "HORA_NOT_FOUND", 404)
        # 404 (no 403) — no revelar que el recurso existe en otra empresa
        if not self._proyectos.find_by_id(proyecto_id, empresa_id):
            raise AppError("Registro de horas no encontrado", "HORA_NOT_FOUND", 404)
        if not self._repo.delete(str(hora_id)):
            raise AppError("Registro de horas no encontrado", "HORA_NOT_FOUND", 404)
        logger.info("Horas eliminadas", extra={"hora_id": str(hora_id)})

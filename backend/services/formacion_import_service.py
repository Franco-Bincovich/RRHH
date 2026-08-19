"""
Import de Formación por Excel: preview → confirmar. Cierra A5.

El PREVIEW vive en `formacion_import_preview.py` (mismo corte que objetivos y que las dos
mitades del Flujo 2 de nómina). Molde del conjunto: `objetivos_import_service.py` — la forma del
reporte por filas viene del Flujo 1: cada fila cae en un grupo y **el lote no aborta por una
fila**.

🔴 EL CONFIRMAR REVALIDA: el body viajó por la red y el cliente lo pudo alterar. Lo que se
rehace acá es lo que autoriza una escritura: que el `empleado_id` de cada fila pertenezca a la
EMPRESA del lote (un id ajeno entra al reporte como error de fila, nunca a la base — la FK
compuesta lo rebotaría igual, pero con un 500 en vez de un renglón legible), y que una fila sin
empleado traiga `nombre_libre`. El estado ya no puede venir alterado: el schema lo tipa Literal
y un valor fuera del CHECK muere en el 422 de FastAPI.

🔴 EL CATÁLOGO SE RESUELVE POR LOTE, no por fila: un lookup de las capacitaciones de la empresa
al entrar y un cache que se completa con cada creación — N filas del mismo título crean UNA
capacitación (decisión 6).

AUDITORÍA: UN evento por lote, emitido SIEMPRE, también con 0 filas o todas fallidas — es el
ÚNICO registro de que alguien importó formación, y este módulo no auditaba nada hasta hoy.
Ver `_audit_payloads_formacion`.
"""
from typing import Dict, List, Optional
from uuid import UUID

from repositories.asignacion_repo import AsignacionRepo
from repositories.capacitacion_repo import CapacitacionRepo
from schemas.capacitacion import CapacitacionCreate
from schemas.importacion_formacion import (
    FilaFormacionError, FilaFormacionPreview, ImportacionFormacionConfirmarRequest,
    ImportacionFormacionConfirmarResponse, ImportacionFormacionPreviewResponse,
)
from services._audit_payloads_formacion import payload_importacion_formacion
from services._formacion_duplicado import duplicado_legible
from services.audit_service import AuditService
from services.formacion_import_preview import preview as _preview
from utils.errors import AppError
from utils.logger import logger


class FormacionImportService:
    def __init__(self, asig_repo: Optional[AsignacionRepo] = None,
                 cap_repo: Optional[CapacitacionRepo] = None,
                 audit: Optional[AuditService] = None) -> None:
        self._asig = asig_repo or AsignacionRepo()
        self._cap = cap_repo or CapacitacionRepo()
        self._audit = audit or AuditService()

    def preview(self, data: bytes, empresa_id) -> ImportacionFormacionPreviewResponse:
        """Lee el Excel y clasifica cada fila. Ver `formacion_import_preview.preview`."""
        return _preview(data, empresa_id)

    def confirmar(self, body: ImportacionFormacionConfirmarRequest,
                  usuario_id: Optional[str] = None,
                  archivo: str = "formacion.xlsx") -> ImportacionFormacionConfirmarResponse:
        """Escribe el lote (catálogo + asignaciones) y emite UN evento de auditoría."""
        empresa = str(body.empresa_id)
        padron = {str(e["id"]) for e in self._asig.empleados_por_empresa(empresa)}
        catalogo: Dict[str, str] = {c.nombre.strip(): c.id
                                    for c in self._cap.find_all(body.empresa_id, solo_activos=False)}
        creadas: List[str] = []
        ids: List[str] = []
        errores: List[FilaFormacionError] = []
        for f in body.filas:
            try:
                ids.append(self._confirmar_fila(f, empresa, padron, catalogo, creadas))
            except AppError as exc:
                errores.append(FilaFormacionError(
                    fila=f.fila, identificador=f"{f.colaborador} — {f.titulo}", motivo=exc.message))
            except Exception as exc:  # noqa: BLE001 — el lote no aborta por una fila
                # Mismo alcance declarado que objetivos: un error inesperado deja rastro para
                # quien administra el import, a costa de mostrar texto crudo en ESA fila.
                errores.append(FilaFormacionError(
                    fila=f.fila, identificador=f"{f.colaborador} — {f.titulo}", motivo=str(exc)))

        self._audit.registrar(**payload_importacion_formacion(
            empresa, archivo, len(body.filas), len(ids), len(errores), usuario_id, ids, creadas))
        logger.info("Import formación confirmado", extra={
            "archivo": archivo, "enviadas": len(body.filas), "creadas": len(ids),
            "errores": len(errores), "capacitaciones_creadas": len(creadas)})
        return ImportacionFormacionConfirmarResponse(
            importados=len(ids), errores=errores, capacitaciones_creadas=creadas)

    def _confirmar_fila(self, f: FilaFormacionPreview, empresa: str, padron: set,
                        catalogo: Dict[str, str], creadas: List[str]) -> str:
        """Una fila → una asignación escrita. Devuelve su id; ante cualquier rechazo, AppError."""
        if f.empleado_id is not None and str(f.empleado_id) not in padron:
            # El mismo renglón para "no existe" y "es de otra empresa": distinguirlos sería el
            # oráculo que la barrera de empresa prohíbe, versión reporte de import.
            raise AppError("el colaborador no existe en la empresa del lote",
                           "EMPLEADO_FUERA_DEL_LOTE", 422)
        if f.empleado_id is None and not (f.nombre_libre or "").strip():
            raise AppError("la fila no trae colaborador vinculado ni nombre suelto",
                           "FILA_SIN_PERSONA", 422)
        titulo = f.titulo.strip()
        cap_id = catalogo.get(titulo)
        if cap_id is None:
            creada = self._cap.save(CapacitacionCreate(
                empresa_id=UUID(empresa), nombre=titulo, tipo=f.tipo,
                entidad_capacitadora=f.entidad_capacitadora, modalidad=f.modalidad,
                duracion_horas=f.duracion_horas))
            cap_id = creada.id
            catalogo[titulo] = cap_id
            creadas.append(titulo)
        with duplicado_legible():
            fila = self._asig.save(
                str(cap_id), str(f.empleado_id) if f.empleado_id else None, empresa,
                f.fecha_asignacion, None,  # type: ignore[arg-type]  # ISO str: el repo lo pasa tal cual
                proyecto=f.proyecto, anio=f.anio, mes=f.mes, nombre_libre=f.nombre_libre,
                estado=f.estado, fecha_completado=f.fecha_completado)
        return fila.id

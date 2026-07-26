"""
R17 — Trazabilidad/auditoría. Export del log de auditoría a PDF/Excel. Reusa AuditRepo.listar
(resuelve nombre de usuario y empresa, sin N+1). Columnas legibles: fecha, usuario, entidad,
evento, acción. NO incluye datos_anteriores/datos_nuevos (JSONB ilegible en export).
Filtra por período (created_at), empresa y —opcional a nivel generador— entidad/evento.
La auditoría no tiene área (no aplica el filtro de área del catálogo).
"""
from datetime import date
from typing import Any, Dict, Optional
from uuid import UUID

from repositories.audit_repo import AuditRepo
from services.reportes._common import periodo_str, rango_mes

_PAGE_SIZE = 100000  # el export no pagina; traemos todo el período de una


def generate_auditoria(mes: int, anio: int, empresa_id: Optional[UUID] = None,
                       entidad: Optional[str] = None, evento: Optional[str] = None,
                       repo: Optional[AuditRepo] = None) -> Dict[str, Any]:
    """Log de auditoría del período proyectado a columnas legibles. Filtra por empresa_id y,
    opcionalmente, entidad/evento. Marca truncamiento si el total supera lo traído."""
    ini, fin = rango_mes(mes, anio)
    repo = repo or AuditRepo()
    items, total = repo.listar(
        empresa_id=empresa_id, entidad=entidad, evento=evento,
        fecha_desde=date.fromisoformat(ini), fecha_hasta=date.fromisoformat(fin),
        page=1, page_size=_PAGE_SIZE,
    )

    eventos = [
        {
            "fecha": e.created_at.strftime("%d/%m/%Y %H:%M") if e.created_at else "",
            "usuario": e.usuario_nombre or "—",
            "entidad": e.entidad,
            "evento": e.evento,
            "accion": e.accion,
        }
        for e in items
    ]

    datos: Dict[str, Any] = {
        "titulo": f"Auditoría — {periodo_str(mes, anio)}",
        "periodo": {"mes": mes, "anio": anio},
        "total_eventos": total,
        "eventos": eventos,
    }
    if total > len(eventos):
        datos["nota"] = f"Se exportan los primeros {len(eventos)} de {total} eventos del período."
    return datos

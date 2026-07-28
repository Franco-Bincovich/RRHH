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
from services._limite_export import LIMITE_FILAS_EXPORT
from services.reportes._common import periodo_str, rango_mes

# ⚠️ AUDITORÍA ES LA EXCEPCIÓN DELIBERADA al corte duro de _limite_export, y no es un olvido.
# El resto de los exports falla con EXPORT_DEMASIADAS_FILAS y le pide al usuario que acote con
# los filtros. Acá eso no se puede: este reporte YA está acotado a un mes por construcción
# (rango_mes) y la pantalla de reportes no ofrece otro filtro con el que angostarlo. Fallar
# dejaría al usuario sin forma alguna de obtener la auditoría de un mes cargado.
# Por eso conserva su comportamiento previo: entrega el archivo con las primeras filas Y una
# nota que dice cuántas quedaron afuera — truncado, pero DECLARADO, que es lo que el bloque B
# vino a arreglar. Lo que sí se unificó es el número: sale de la constante compartida.
_PAGE_SIZE = LIMITE_FILAS_EXPORT


def generate_auditoria(mes: int, anio: int, empresa_id: Optional[UUID] = None,
                       entidad: Optional[str] = None, evento: Optional[str] = None,
                       repo: Optional[AuditRepo] = None) -> Dict[str, Any]:
    """Log de auditoría del período proyectado a columnas legibles. Filtra por empresa_id y,
    opcionalmente, entidad/evento. Si el total supera el tope, entrega lo que entra CON una nota
    que lo declara (ver la excepción arriba: acá no hay filtro con el que acotar)."""
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

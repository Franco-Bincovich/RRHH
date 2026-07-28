"""
Proyección de columnas legibles para el export del LISTADO de auditoría.

⚠️ No confundir con services/reportes/_reporte_auditoria.py. Son dos cosas distintas:
  · aquel es un REPORTE del catálogo de Fase 1 — acotado a un mes por construcción, sin más
    filtros, y con truncado declarado;
  · este es el export del listado del módulo /auditoria, que sale con los SEIS filtros de la
    pantalla aplicados y falla ruidoso si el resultado no entra (verificar_limite_export).
Lo que se ve en la pantalla es lo que sale en el archivo.

NO vuelca `datos_anteriores` / `datos_nuevos`: son JSONB y en un Excel se leen como un muro de
llaves. Quien necesita el detalle de un evento lo abre en la pantalla, que sí lo muestra
formateado. El export existe para el recorrido y el cruce (quién tocó qué y cuándo).
"""
from typing import List

from schemas.auditoria import AuditLogResponse


def _fecha_hora(v) -> str:
    """Formatea datetime a dd/mm/aaaa hh:mm; '' si es None. En auditoría la HORA importa:
    es lo que permite ordenar dos eventos del mismo día."""
    return v.strftime("%d/%m/%Y %H:%M") if v else ""


def construir_filas_export(items: List[AuditLogResponse]) -> List[dict]:
    """Proyecta los eventos de auditoría a columnas legibles (sin UUIDs crudos).

    `Usuario` cae al id solo si el nombre no se pudo resolver (usuario borrado): preferimos un
    identificador feo a una celda vacía, porque en una auditoría "no sé quién" no es aceptable.
    """
    return [
        {
            "Fecha": _fecha_hora(ev.created_at),
            "Usuario": ev.usuario_nombre or ev.usuario_id or "Sin usuario",
            "Empresa": ev.empresa_nombre,
            "Entidad": ev.entidad,
            "Evento": ev.evento,
            "Acción": ev.accion,
            "Registro": ev.registro_id,
        }
        for ev in items
    ]

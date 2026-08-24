"""Payload de auditoría de la GENERACIÓN de un reporte.

🔴 POR QUÉ EXISTE. `POST /api/reportes/generar` no dejaba **ningún** evento: medido el
23/8/2026, `auditoria` tenía CERO eventos de reportes en toda su historia, con 11 filas en
`reportes_generados`. Y `generado_por` decía "Sistema" en las 11 (ver `middleware/auth.py`),
así que un reporte de costos o de masa salarial —que lista sueldos por persona— era
**completamente inatribuible**: no se podía saber quién lo pidió ni cuándo.

⚠️ El evento NO guarda los DATOS del reporte, sólo qué se pidió: tipo, período, empresa y área.
El contenido ya vive en `reportes_generados.datos` y duplicar un volcado de sueldos dentro de
`auditoria` —que es inmutable y no se purga— sería sembrar el mismo dato sensible en dos tablas
con políticas distintas.

⚠️ `registro_id` es el id del REPORTE, que acá sí es una fila real con id propio. No hace falta
el `uuid4()` de evento que usan los imports de nómina, donde el lote no persiste como fila.
"""
from typing import Any, Dict, Optional
from uuid import UUID


def payload_generacion_reporte(reporte, usuario_id: Optional[str],
                               area_id: Optional[UUID] = None) -> Dict[str, Any]:
    """Evento de auditoría de un reporte generado. UN evento por reporte.

    Args:
        reporte: la fila persistida (`ReporteResponse`), de donde salen id, tipo y empresa.
        usuario_id: quién lo pidió.
        area_id: el recorte por área, si el formulario lo mandó.

    Returns:
        kwargs listos para `AuditService.registrar`.
    """
    return dict(
        usuario_id=usuario_id,
        entidad="reporte",
        registro_id=str(reporte.id),
        accion="INSERT",
        evento="generacion_reporte",
        # La empresa sale del REPORTE, no del header: es una ACCIÓN y su empresa la eligió el
        # formulario (Vista vs Acción). `None` = consolidado, y es un valor legítimo.
        empresa_id=reporte.empresa_id,
        datos_anteriores=None,
        datos_nuevos={
            "tipo": reporte.tipo,
            "nombre": reporte.nombre,
            "area_id": str(area_id) if area_id else None,
        },
    )

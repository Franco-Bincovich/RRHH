"""
Payloads de auditoría del módulo de evaluaciones (import de resultados por CSV).

Entidad "evaluacion", con registro_id = id del LOTE. Un import audita UN evento por lote,
nunca fila por fila — es la regla del repo para toda importación.

⚠️ Este archivo llegó a tener también los payloads del scoring instancia-por-instancia
(`payload_carga_resultado_evaluacion` y `payload_finalizar_evaluacion`). Se borraron el
2026-08-11 con el módulo `ev_*` (bloque J5a): eran los únicos consumidores de
`_resultado_de` y de `_CAMPOS_RESULTADO`, que se fueron con ellos. Lo que queda sirve al
módulo VIVO (`evaluacion_lotes`/`_evaluados`/`_resultados`), que es otro.
"""
from typing import Optional


def payload_importacion_evaluaciones(lote_id: str, periodo: str, empresa_id: str, evaluados: int,
                                     resultados: int, equivalencias: int, piso: bool,
                                     usuario_id: Optional[str]) -> dict:
    """Evento de auditoría de un LOTE de import de resultados de evaluaciones (UN evento por lote,
    nunca fila por fila). registro_id = UUID del lote (la columna es uuid; un sentinel de texto como
    'lote_evaluaciones' rompe el insert y AuditService lo traga → evento perdido en silencio).
    A diferencia de nómina, el lote es de UNA empresa (la del import), así que empresa_id va seteada."""
    return {
        "usuario_id": usuario_id, "entidad": "evaluacion", "registro_id": lote_id,
        "accion": "INSERT", "evento": "importacion_evaluaciones", "empresa_id": empresa_id,
        "datos_anteriores": None,
        "datos_nuevos": {
            "periodo": periodo, "evaluados": evaluados, "resultados": resultados,
            "equivalencias_confirmadas": equivalencias, "piso_periodo_anterior": piso,
        },
    }


def payload_baja_lote_evaluaciones(lote_id: str, periodo: str, empresa_id: str, evaluados: int,
                                   usuario_id: Optional[str]) -> dict:
    """Evento de auditoría de la BAJA de un lote importado (UN evento por lote, espejo del alta).

    El snapshot de datos_anteriores se toma ANTES de borrar: el CASCADE se lleva evaluados y
    resultados, así que después del delete no hay forma de reconstruir qué se perdió. Mismo
    registro_id que el alta (UUID del lote, nunca un sentinel de texto: la columna es uuid),
    así el historial completo de una importación queda agrupado bajo el mismo registro."""
    return {
        "usuario_id": usuario_id, "entidad": "evaluacion", "registro_id": lote_id,
        "accion": "DELETE", "evento": "baja_lote_evaluaciones", "empresa_id": empresa_id,
        "datos_anteriores": {"periodo": periodo, "evaluados": evaluados},
        "datos_nuevos": None,
    }

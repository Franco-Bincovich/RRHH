"""
Payload de auditoría del import de Formación. UN evento por lote, nunca fila por fila.

Molde: `_audit_payloads_objetivos_import.py` — archivo por dominio, misma forma.

🔴 ESTE ES EL PRIMER EVENTO DE AUDITORÍA DEL MÓDULO DE CAPACITACIONES/FORMACIÓN. Hasta hoy el
módulo no auditaba nada (ni el catálogo ni las asignaciones emiten eventos; solo logs). Igual
que con objetivos, `test_auditoria_coherente` toma como alcance los ARCHIVOS que emiten al menos
un evento: el que entra al alcance es `formacion_import_service.py` —cuyas escrituras son las
del lote y quedan cubiertas por este evento—, no el CRUD de capacitaciones, que sigue sin
auditar igual que antes.
"""
from typing import List, Optional
from uuid import uuid4


def payload_importacion_formacion(
    empresa_id: str, archivo: str, filas_enviadas: int, filas_creadas: int,
    filas_con_error: int, usuario_id: Optional[str], ids_creados: List[str],
    capacitaciones_creadas: List[str],
) -> dict:
    """Evento de un lote de import de formación.

    🔴 `registro_id` es un id DE EVENTO (uuid4), no de recurso: el import no persiste un "lote"
    con id propio. Mismo criterio que `payload_importacion_objetivos` y los dos de nómina. NO
    "corregir" a un id real — no existe.

    🔴 `empresa_id` VA SETEADA: el body trae la empresa explícita y todo el lote se escribe en
    ella (decisión 1), así que el evento puede afirmarla y entra al filtro por empresa de
    `/auditoria`.

    🔴 `capacitaciones_creadas` va en el payload porque este lote escribe DOS tablas: además de
    las asignaciones puede crear filas del catálogo, y un evento que solo contara asignaciones
    dejaría esas altas sin ningún rastro (el catálogo no audita su alta manual tampoco).
    """
    return {
        "usuario_id": usuario_id,
        "entidad": "capacitacion",
        "registro_id": str(uuid4()),
        "accion": "INSERT",
        "evento": "importacion_formacion",
        "empresa_id": empresa_id,
        "datos_anteriores": None,
        "datos_nuevos": {
            "archivo": archivo,
            "filas_enviadas": filas_enviadas,
            "filas_creadas": filas_creadas,
            "filas_con_error": filas_con_error,
            "ids_creados": ids_creados,
            "capacitaciones_creadas": capacitaciones_creadas,
        },
    }

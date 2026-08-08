"""
Payload de auditoría del import de objetivos. UN evento por lote, nunca fila por fila.

Archivo propio y no dentro de `_audit_payloads_import.py` porque ese está en 135/150 y esto no
entraba. Es además la familia que el repo ya usa (`_audit_payloads_{rrhh,costos,usuarios,ev,
cesion,import,offboarding}`): un archivo por dominio.

🔴 ESTE ES EL PRIMER EVENTO DE AUDITORÍA DEL MÓDULO DE OBJETIVOS. Hasta hoy el módulo no
auditaba nada —está nombrado en `test_auditoria_coherente` entre los que tienen cero eventos— y
eso tiene una consecuencia que hay que mirar: ese barrido toma como ALCANCE los ARCHIVOS que
emiten al menos un evento, y le exige a cada uno que TODAS sus escrituras estén cubiertas. Como
este payload lo consume `objetivos_import_service.py` y no `objetivo_service.py`, el que entra
al alcance es el import —cuya única escritura es este mismo lote—, no el CRUD. El CRUD de
objetivos sigue sin auditar, igual que antes.
"""
from typing import List, Optional
from uuid import uuid4


def payload_importacion_objetivos(
    empresa_id: str, archivo: str, filas_enviadas: int, filas_creadas: int,
    filas_con_error: int, usuario_id: Optional[str], ids_creados: List[str],
) -> dict:
    """Evento de un lote de import de objetivos.

    🔴 `registro_id` es un id DE EVENTO (uuid4), no de recurso: el import de objetivos no
    persiste un "lote" con id propio (a diferencia de evaluaciones, donde el lote ES una fila).
    Mismo criterio que `payload_importacion_costos` y `payload_importacion_nomina`. NO
    "corregir" a un id real — no existe.

    🔴 `empresa_id` VA SETEADA. El body trae una empresa explícita y todos los objetivos del
    lote se crean en ella, así que el evento puede afirmarla. Copiarle el `None` a
    `payload_importacion_nomina` —que sí lo tiene, porque ESE lote crea gente en varias empresas
    derivadas del archivo— dejaría este evento fuera del filtro por empresa de `/auditoria`,
    que es la pantalla donde esto se mira.

    🔴 `ids_creados` va en el payload y es lo que hace reconstruible el lote. Un alta es una
    FOTOGRAFÍA y el id alcanza para reconstruirla; por eso las filas no emiten evento propio.
    Sin los ids, "se importaron 12 objetivos" no permitiría saber cuáles.

    ⚠️ `filas_con_error` cuenta las que NO se cargaron. Va en el evento aunque no haya nada que
    reconstruir de ellas: un import de 40 filas que cargó 3 es un hecho que la auditoría tiene
    que poder contar sin abrir la pantalla.
    """
    return {
        "usuario_id": usuario_id,
        "entidad": "objetivo",
        "registro_id": str(uuid4()),
        "accion": "INSERT",
        "evento": "importacion_objetivos",
        "empresa_id": empresa_id,
        "datos_anteriores": None,
        "datos_nuevos": {
            "archivo": archivo,
            "filas_enviadas": filas_enviadas,
            "filas_creadas": filas_creadas,
            "filas_con_error": filas_con_error,
            "ids_creados": ids_creados,
        },
    }

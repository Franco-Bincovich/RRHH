"""
Payloads de auditoría de los IMPORTS (hoy: nómina de empleados).

Archivo propio y no dentro de `_audit_payloads_rrhh.py`, que estaba en 149/150 líneas. Mismo
criterio y mismo molde que `_audit_payloads_cesion.py` y `_audit_payloads_vacaciones.py`, que
existen por la misma razón y lo dicen en su encabezado.

Se movió VERBATIM desde `_audit_payloads_rrhh.payload_importacion_nomina`: forma del dict,
entidad, acción y comentarios son idénticos. Vive acá porque es el payload que la
consolidación de auditoría del import va a extender, y hacerlo en el archivo viejo no entraba.
"""
from typing import List, Optional
from uuid import uuid4


def payload_importacion_nomina(
    archivo: str, creados: int, actualizados: int, con_faltantes: int, no_cargados: int,
    usuario_id: Optional[str], empleado_ids_creados: Optional[List[str]] = None,
    parcial: bool = False, superiores_resueltos: int = 0, superiores_pendientes: int = 0,
) -> dict:
    """Evento de auditoría de un lote de import de nómina de empleados (UN evento por lote).
    Refleja el resumen: nuevos, actualizados (dedup DNI), con faltantes y no cargados.
    empresa_id None: el lote puede crear empleados en varias empresas (columna Organismo).

    🔴 `empleado_ids_creados` es lo que hace que consolidar las ALTAS no pierda trazabilidad.
    Antes cada alta emitía su propio evento INSERT: con 120 filas eran 120 eventos + este,
    o sea duplicación (este ya traía el resumen) contra la regla del repo de "un evento por
    lote". Ahora las altas viven acá, nominadas por id: se puede reconstruir exactamente qué
    empleados creó el import, que es la pregunta que un log de auditoría tiene que responder.
    Un alta es una FOTOGRAFÍA y el registro creado es su propia evidencia — por eso alcanza con
    el id. Un UPDATE responde "¿qué cambió?" y eso NO se puede reconstruir desde un id, así que
    los updates conservan su evento individual con diff (ver `_empleados_write.actualizar`).

    Es Optional con default None para no romper a quien lo llame sin la lista (el evento sale
    igual, solo sin el detalle nominal).

    🔴 `parcial=True` marca que el import se cortó por PRESUPUESTO DE TIEMPO y el archivo no se
    terminó de procesar. El evento se emite igual —y tiene que emitirse— porque es el ÚNICO
    rastro de las altas: se consolidaron acá y ya no emiten evento individual. Un corte sin este
    evento dejaría empleados creados sin una línea en `auditoria`.
    El flag va DENTRO de `datos_nuevos` y no como un `evento` distinto (`importacion_nomina_parcial`)
    a propósito: quien filtre por `evento="importacion_nomina"` tiene que ver los dos casos, o un
    corte quedaría invisible en la pantalla de auditoría justo cuando es lo que más importa mirar.

    🔴 Los `superiores_*` viajan EN ESTE MISMO EVENTO y no en uno propio: la resolución de
    superiores es una segunda pasada DEL MISMO LOTE, no otra operación. Un evento aparte partiría
    en dos el rastro de un solo import y obligaría a cruzarlos por timestamp para saber qué pasó.
    Van como CONTEO y no con el detalle de los pendientes: el detalle sale en la respuesta que ve
    quien importa, y `auditoria` responde "qué se hizo", no "qué falta hacer".
    """
    datos = {
        "archivo": archivo, "creados": creados, "actualizados": actualizados,
        "con_faltantes": con_faltantes, "no_cargados": no_cargados, "parcial": parcial,
        "superiores_resueltos": superiores_resueltos,
        "superiores_pendientes": superiores_pendientes,
    }
    if empleado_ids_creados is not None:
        datos["empleado_ids_creados"] = empleado_ids_creados
    return {
        # registro_id = id DE EVENTO (uuid4 generado), no de recurso: el import de nómina no
        # persiste un lote con id propio (a diferencia de evaluaciones). NO "corregir" a un id real.
        "usuario_id": usuario_id, "entidad": "empleado", "registro_id": str(uuid4()),
        "accion": "INSERT", "evento": "importacion_nomina", "empresa_id": None,
        "datos_anteriores": None,
        "datos_nuevos": datos,
    }

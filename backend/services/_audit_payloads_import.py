"""
Payloads de auditoría de los IMPORTS: nómina de EMPLEADOS (roster) y nómina de COSTOS (sueldos).

Archivo propio y no dentro de `_audit_payloads_rrhh.py`, que estaba en 149/150 líneas. Mismo
criterio y mismo molde que `_audit_payloads_cesion.py` y `_audit_payloads_vacaciones.py`, que
existen por la misma razón y lo dicen en su encabezado.

`payload_importacion_nomina` se movió VERBATIM desde `_audit_payloads_rrhh`: forma del dict,
entidad, acción y comentarios son idénticos. Vive acá porque es el payload que la
consolidación de auditoría del import va a extender, y hacerlo en el archivo viejo no entraba.

🔴 LOS DOS EVENTOS SE LLAMAN DISTINTO Y NO ES UN DESCUIDO. `importacion_nomina` es el del
roster (crea EMPLEADOS) e `importacion_costos` el de sueldos (escribe `costos_nomina`). El
nombre del primero quedó pegado a "nómina" cuando era el único import, y **no se puede
renombrar**: hay eventos en producción con ese `evento` y `auditoria` es inmutable — renombrarlo
partiría el historial en dos nombres para la misma operación. Al agregar el segundo, el que se
elige distinto es el nuevo. Los dos usan entidades distintas (`empleado` vs `nomina`), así que
en `/auditoria` tampoco se mezclan al filtrar.
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


def payload_importacion_costos(
    empresa_id: str, periodos: List[str], filas_enviadas: int, filas_persistidas: int,
    usuario_id: Optional[str],
) -> dict:
    """Evento de auditoría de un lote de import de nómina de COSTOS (UN evento por lote).

    🔴 `empresa_id` VA SETEADA, al revés que en `payload_importacion_nomina`. Ese lote crea
    empleados en varias empresas (las deriva de la columna Organismo del archivo) y por eso no
    puede tener una sola; este recibe una empresa explícita en el body y escribe `costos_nomina`
    solo para ella. En eso se parece a `payload_importacion_evaluaciones`, no a su hermano de
    acá arriba. Copiarle el `None` al hermano dejaría el evento fuera del filtro por empresa de
    `/auditoria`, que es la pantalla donde esto se mira.

    🔴 `registro_id` es un id DE EVENTO (uuid4), no de recurso: `costos_nomina` no persiste un
    lote con id propio (a diferencia de evaluaciones, donde el lote ES una fila). Mismo criterio
    que el hermano. NO "corregir" a un id real — no existe.

    🔴 `filas_persistidas` SALE DEL RETORNO DEL REPO, no de los flags del body. El body trae un
    `es_actualizacion` por fila que se calculó en el PREVIEW y viajó de vuelta por la red: el
    cliente lo puede alterar, así que contar sobre él es auditar lo que el cliente DICE que pasó.
    `batch_upsert_nomina` devuelve las filas que la base efectivamente escribió, y ese es el
    único dato autoritativo del que se dispone acá.

    ⚠️ POR ESO NO HAY `importados` / `actualizados` EN EL EVENTO, y es una omisión deliberada.
    El upsert de PostgREST devuelve las filas resultantes pero NO dice cuáles fueron INSERT y
    cuáles UPDATE — esa distinción solo existe en el `es_actualizacion` del body, que es
    justamente el dato no confiable. Separarlas de verdad exigiría releer el estado previo
    (una query más por import) y es una decisión aparte. Preferir un número honesto y menos
    detallado a dos números detallados que el log no puede sostener: la respuesta HTTP sigue
    devolviendo el desglose para la pantalla, pero la auditoría no lo afirma.

    `parcial` marca que se escribió menos de lo enviado. No puede afirmar POR QUÉ (el repo hace
    una sola query y no reporta fila por fila), solo que los números no cierran — que es
    exactamente la señal que amerita ir a mirar.

    Args:
        empresa_id: empresa del lote (del body, no del header — es una ACCIÓN).
        periodos: períodos "AAAA-MM" tocados por el lote, ordenados y sin repetir. Es una LISTA
            SIEMPRE, incluso con un solo período: un archivo de nómina normalmente trae un mes,
            pero nada lo impide, y una forma que cambia de string a lista según el contenido
            obliga a quien lee el log a manejar los dos casos. Con lote vacío es `[]`.
        filas_enviadas: filas que mandó el cliente (`len(body.filas)`).
        filas_persistidas: filas que devolvió la base (autoritativo).
        usuario_id: operador que confirmó el import.

    El nombre del ARCHIVO no viaja: se sube en `/preview` y el `confirmar` recibe JSON, así que
    para cuando se persiste ya no existe. Se omite en vez de inventarlo o de agregarlo al schema
    solo para el log.
    """
    return {
        "usuario_id": usuario_id, "entidad": "nomina", "registro_id": str(uuid4()),
        "accion": "INSERT", "evento": "importacion_costos", "empresa_id": empresa_id,
        "datos_anteriores": None,
        "datos_nuevos": {
            "periodos": periodos, "filas_enviadas": filas_enviadas,
            "filas_persistidas": filas_persistidas,
            "parcial": filas_persistidas < filas_enviadas,
        },
    }

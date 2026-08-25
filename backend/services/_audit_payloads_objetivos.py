"""
Payloads canónicos de los eventos de auditoría del módulo de Objetivos.

🔴 POR QUÉ ESTE ARCHIVO EXISTE RECIÉN AHORA, Y QUÉ COSTÓ NO TENERLO.
`/objetivos` era el único módulo del sistema con **borrado desde la UI y CERO eventos de
auditoría**. Un objetivo real de Karstec desapareció entre el 17/8 y el 24/8/2026 y no hay forma
de saber quién lo borró ni cuándo: `auditoria` no tiene una sola fila de esta entidad. El borrado
además es FÍSICO y arrastra los subobjetivos por CASCADE (`_objetivos_write.eliminar`), así que
no hay ni siquiera una fila con `activo=False` de la que reconstruir el dato.

`tests/test_auditoria_coherente.py` NO lo cazó, y eso no es un fallo del barrido: su alcance son
los módulos que YA emiten al menos un evento, y objetivos no emitía ninguno, así que quedaba
fuera POR CONSTRUCCIÓN. El barrido que sí lo hubiera cazado se agrega en esta misma tanda
(`tests/test_auditoria_destructivas.py`).

ARCHIVO PROPIO Y NO `_audit_payloads.py`: ese está en 119/150 y su encabezado deja escrita la
regla —"si supera ~150 líneas al crecer, partirlo POR MÓDULO"—, cosa que ya se hizo siete veces
(`_rrhh`, `_costos`, `_usuarios`, `_ev`, `_cesion`, `_offboarding`, `_clientes`). Molde directo:
`_audit_payloads_clientes.py`, el ABM más parecido.

🔴 ACÁ VIVEN LOS CUATRO EVENTOS Y NADA MÁS. Qué campos de un objetivo entran en el log, cuáles
se excluyen por derivados y cómo se comparan dos versiones está en
`services/_audit_objetivo_forma.py`, de donde este archivo importa `CAMPOS_OBJETIVO`, `subset` y
`diff_objetivo`. La división es del 25/8/2026: todo junto daba **157/150 líneas**, y comprimir
los comentarios habría sido pagar el límite con lo único que explica por qué se excluye cada
campo. El seam está justificado en el encabezado de aquel archivo — leerlo antes de mover algo
de un lado al otro.
"""
from typing import Optional

from services._audit_objetivo_forma import CAMPOS_OBJETIVO, diff_objetivo, subset

_ENTIDAD = "objetivo"


def payload_alta_objetivo(row, usuario_id: Optional[str]) -> dict:
    """Evento INSERT del alta de un objetivo.

    `empresa_id` va con la del OBJETIVO y no con la del header: el alta lo recibe explícito en el
    body (`ObjetivoCreate.empresa_id`), así que la entidad sabe de quién es. Es Vista vs Acción —
    el selector del sidebar decide qué se MIRA, el form decide sobre qué se HACE.
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": row.id,
        "accion": "INSERT", "evento": "alta_objetivo", "empresa_id": row.empresa_id,
        "datos_anteriores": None, "datos_nuevos": subset(row, CAMPOS_OBJETIVO),
    }


def payload_update_objetivo(prior, nuevo, usuario_id: Optional[str]) -> dict:
    """Evento UPDATE de la edición de un objetivo (diff antes/después)."""
    antes, despues = diff_objetivo(prior, nuevo)
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": prior.id,
        "accion": "UPDATE", "evento": "update_objetivo", "empresa_id": prior.empresa_id,
        "datos_anteriores": antes, "datos_nuevos": despues,
    }


def payload_estado_objetivo(prior, nuevo, usuario_id: Optional[str]) -> dict:
    """Evento UPDATE del movimiento en el kanban (por_hacer → haciendo → terminado).

    EVENTO PROPIO Y NO `update_objetivo`, aunque los dos sean UPDATE sobre la misma tabla: mover
    una tarjeta es el acto más frecuente del tablero y tiene endpoint propio
    (`PUT /{id}/estado`). Con un evento compartido, el filtro por evento de `/auditoria` mezclaría
    "alguien reescribió el objetivo" con "alguien lo movió de columna", que es justo el corte que
    RRHH va a querer hacer. Mismo criterio que `cancelacion_vacacion` contra `update_vacacion`.

    Va por el mismo `diff_objetivo` que la edición y no por un dict a mano con `{"estado": ...}`:
    si el día de mañana mover una tarjeta tocara otra columna, el diff lo registra solo.
    """
    antes, despues = diff_objetivo(prior, nuevo)
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": prior.id,
        "accion": "UPDATE", "evento": "cambio_estado_objetivo", "empresa_id": prior.empresa_id,
        "datos_anteriores": antes, "datos_nuevos": despues,
    }


def payload_baja_objetivo(prior, tenia_hijos: bool, usuario_id: Optional[str]) -> dict:
    """Evento DELETE de la baja de un objetivo. Borrado FÍSICO: esta foto es lo único que queda.

    🔴 `tenia_hijos` VIAJA EN EL PAYLOAD Y NO ES DECORATIVO. La FK `parent_id` es ON DELETE
    CASCADE (migración 095): borrar un padre se lleva a los subobjetivos, y de ESOS no queda ni un
    evento —el CASCADE lo ejecuta la base, donde este repo no tiene triggers de auditoría desde la
    migración 058—. Sin este dato, el log diría que se borró UN objetivo cuando desaparecieron
    cuatro, y nadie podría saberlo después. Es exactamente lo que el incidente del 17/8 no tuvo.

    ⚠️ ES UN BOOLEANO Y NO UN CONTEO, a propósito. El repo ya expone `tiene_hijos` —una query
    dirigida con `limit 1`— y no un `contar_hijos`; agregarlo pasaba `objetivo_repo.py` de su
    límite de 100 líneas, y el conteo exacto no cambia ninguna decisión que alguien vaya a tomar
    leyendo el log. Lo que hay que poder responder es "¿esta baja se llevó otras cosas?", y eso
    lo contesta el booleano. 🚩 Disparador para volver sobre esto: que alguien tenga que
    reconstruir QUÉ subobjetivos se perdieron, que es una pregunta que ni el conteo contesta —
    esa pide fotografiarlos, y eso es otra tanda.
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": prior.id,
        "accion": "DELETE", "evento": "baja_objetivo", "empresa_id": prior.empresa_id,
        "datos_anteriores": {**subset(prior, CAMPOS_OBJETIVO),
                             "arrastro_subobjetivos_por_cascade": tenia_hijos},
        "datos_nuevos": None,
    }

"""
Payloads canónicos de los eventos de auditoría de Proyectos y de sus ASIGNACIONES.

Los dos módulos comparten archivo porque comparten la pregunta que el log tiene que contestar
—*¿quién sacó a esta persona del proyecto, y con qué condiciones estaba?*— y porque `proyectos`
y `proyecto_asignaciones` son padre e hija: leer los seis payloads juntos es lo que hace evidente
que la baja del padre está bloqueada mientras la hija exista.

🔴 QUÉ HACE ÚTIL AL EVENTO DE BAJA DE UN PROYECTO: `sin_horas_ni_asignaciones`.
`ProyectosService.delete` tiene DOS guardas —`has_horas` y `has_asignaciones`, las dos ON DELETE
RESTRICT— así que un proyecto solo se puede borrar cuando no arrastra nada. Ese hecho es
justamente lo que el log tiene que dejar por escrito: sin él, quien lea el evento dentro de seis
meses no puede distinguir "se borró un proyecto vacío" de "se borró un proyecto con 400 horas
cargadas y la base se las llevó". El campo afirma lo primero, que es lo que el código garantiza.

🔴 QUÉ HACE ÚTIL AL EVENTO DE BAJA DE UNA ASIGNACIÓN: `valor_hora` Y `rol`.
Quitar a alguien de un proyecto es un borrado FÍSICO de la fila que dice a qué tarifa se le
imputaban las horas. El servicio rechaza la baja si la asignación tiene horas cargadas
(`ASIGNACION_CON_HORAS`, 409), así que no se pierde plata ya imputada — pero sí se pierde la
condición pactada, y volver a asignar a la persona no la recupera. `valor_hora` y `rol` son lo
que permite rehacerla igual.

🔴 `empresa_id` SALE DE LA ENTIDAD, Y EN LA ASIGNACIÓN ES LA DEL **EMPLEADO**, NO LA DEL PROYECTO.
Es una decisión y tiene dos motivos. El primero es que un proyecto de la empresa A puede tener
gente de la B —el modelo lo soporta y por eso `proyecto_asignaciones` lleva `empleado_empresa_id`
aparte—, así que "la empresa de la asignación" no es una sola cosa; de las dos, la que le importa
a quien filtra `/auditoria` por empresa es la de la PERSONA, porque asignar a alguien es una
decisión sobre esa persona. El segundo es que `empleado_empresa_id` está EN LA FILA que devuelve
el insert, mientras que la del proyecto exigiría una query más **por cada asignación** — y el alta
por área entera hace 13 de una. Los dos ids viajan igual dentro del payload, así que el evento
sigue diciendo a qué proyecto era.
"""
from typing import Optional

from services._audit_payloads import sin_derivados
from services.audit_service import AuditService, _jsonable

_ENTIDAD_PROYECTO = "proyecto"
_ENTIDAD_ASIGNACION = "proyecto_asignacion"

_CAMPOS_PROYECTO = ("empresa_id", "nombre", "descripcion", "estado",
                    "fecha_inicio", "fecha_fin", "presupuesto")
# `costeo` es un agregado calculado sobre `horas_proyecto` y los dos nombres salen de joins: los
# tres cambian sin que nadie edite el proyecto, así que en un diff serían ediciones fantasma.
_DERIVADOS_PROYECTO = frozenset({"empresa_nombre", "costeo", "created_at", "updated_at", "id"})

_CAMPOS_ASIGNACION = ("proyecto_id", "empleado_id", "empleado_empresa_id",
                      "rol", "valor_hora", "fecha_desde", "fecha_hasta", "activo")
_DERIVADOS_ASIGNACION = frozenset({"empleado_nombre", "empleado_empresa_nombre",
                                   "created_at", "id"})


def _subset(obj: object, campos: tuple) -> dict:
    """Extrae `campos` de un modelo Pydantic (o dict) como dict JSON-serializable."""
    data = obj.model_dump() if hasattr(obj, "model_dump") else dict(obj)  # type: ignore[arg-type]
    return {k: _jsonable(data.get(k)) for k in campos}


def payload_alta_proyecto(row, usuario_id: Optional[str]) -> dict:
    """Evento INSERT del alta de un proyecto. `empresa_id` sale del body, no del header."""
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD_PROYECTO, "registro_id": str(row.id),
        "accion": "INSERT", "evento": "alta_proyecto", "empresa_id": str(row.empresa_id),
        "datos_anteriores": None, "datos_nuevos": _subset(row, _CAMPOS_PROYECTO),
    }


def payload_update_proyecto(prior, nuevo, usuario_id: Optional[str]) -> dict:
    """Evento UPDATE de la edición de un proyecto (diff antes/después).

    El presupuesto está entre los campos que el diff mira, y es el que más va a importar: es el
    número contra el que `costeo.pct_consumido` compara, así que moverlo cambia la lectura de
    todos los reportes del proyecto sin tocar una sola hora.
    """
    antes, despues = AuditService._diff(
        sin_derivados(prior, _DERIVADOS_PROYECTO), sin_derivados(nuevo, _DERIVADOS_PROYECTO))
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD_PROYECTO, "registro_id": str(prior.id),
        "accion": "UPDATE", "evento": "update_proyecto", "empresa_id": str(prior.empresa_id),
        "datos_anteriores": antes, "datos_nuevos": despues,
    }


def payload_baja_proyecto(prior, usuario_id: Optional[str]) -> dict:
    """Evento DELETE de la baja de un proyecto. Borrado FÍSICO: esta foto es lo único que queda.

    🔴 `sin_horas_ni_asignaciones` va SIEMPRE en True y no es redundante — ver el encabezado. Es
    la afirmación de que las dos guardas se cumplieron, o sea que este borrado NO se llevó nada
    más. El día que alguien relaje una de las dos guardas, este campo tiene que dejar de ser una
    constante o el log empieza a mentir; está escrito acá para que ese día se vea.
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD_PROYECTO, "registro_id": str(prior.id),
        "accion": "DELETE", "evento": "baja_proyecto", "empresa_id": str(prior.empresa_id),
        "datos_anteriores": {**_subset(prior, _CAMPOS_PROYECTO),
                             "sin_horas_ni_asignaciones": True},
        "datos_nuevos": None,
    }


def payload_alta_asignacion_proyecto(row, usuario_id: Optional[str],
                                     empresa_id: Optional[str]) -> dict:
    """Evento INSERT de asignar a alguien a un proyecto.

    `empresa_id` es la del EMPLEADO y sale de la propia fila — ver el encabezado. Los tres caminos
    de alta —single, bulk y área entera— pasan por acá, así que asignar un área de 13 personas
    emite 13 eventos. Es correcto y NO contradice la regla de "un evento por lote": esa regla es
    para IMPORTACIONES, donde el lote es la unidad de negocio. Acá cada asignación es una decisión
    sobre una persona y se puede deshacer de a una.
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD_ASIGNACION, "registro_id": str(row.id),
        "accion": "INSERT", "evento": "alta_asignacion_proyecto", "empresa_id": empresa_id,
        "datos_anteriores": None, "datos_nuevos": _subset(row, _CAMPOS_ASIGNACION),
    }


def payload_update_asignacion_proyecto(prior, nuevo, usuario_id: Optional[str],
                                       empresa_id: Optional[str]) -> dict:
    """Evento UPDATE de editar una asignación (diff antes/después).

    ⚠️ Cambiar `valor_hora` acá NO reprecia las horas ya cargadas: el snapshot se congela al
    insertar cada hora. El diff deja ver desde cuándo rige la tarifa nueva, que es lo que hace
    falta para explicar por qué dos horas del mismo proyecto costaron distinto.
    """
    antes, despues = AuditService._diff(
        sin_derivados(prior, _DERIVADOS_ASIGNACION), sin_derivados(nuevo, _DERIVADOS_ASIGNACION))
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD_ASIGNACION, "registro_id": str(prior.id),
        "accion": "UPDATE", "evento": "update_asignacion_proyecto", "empresa_id": empresa_id,
        "datos_anteriores": antes, "datos_nuevos": despues,
    }


def payload_baja_asignacion_proyecto(prior, usuario_id: Optional[str],
                                     empresa_id: Optional[str]) -> dict:
    """Evento DELETE de quitar a alguien de un proyecto. Borrado FÍSICO de la fila.

    `sin_horas_cargadas` afirma que la guarda `ASIGNACION_CON_HORAS` (409) se cumplió: no se
    perdió ninguna hora imputada. Lo que sí se perdió es la condición pactada — ver el encabezado.
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD_ASIGNACION, "registro_id": str(prior.id),
        "accion": "DELETE", "evento": "baja_asignacion_proyecto", "empresa_id": empresa_id,
        "datos_anteriores": {**_subset(prior, _CAMPOS_ASIGNACION), "sin_horas_cargadas": True},
        "datos_nuevos": None,
    }

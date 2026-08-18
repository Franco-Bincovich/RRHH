"""
Efectivización de la baja: el HECHO de que el empleado se fue.

Es la contracara de `_offboarding_iniciar.py`, y existe por el mismo criterio con el que aquel se
separó: **es el único método del módulo que toca DOS agregados** —el empleado y la instancia— y el
que concentra las guardas de estado. Los demás operan sobre una instancia ya creada.

🔴 POR QUÉ ESTE ENDPOINT EXISTE: ANTES LA BAJA LA DISPARABA EL ALTA DEL TRÁMITE.
`_offboarding_iniciar` llamaba a `dar_de_baja(...)` con la fecha PREVISTA (o `hoy + 30 días`), así
que abrir el trámite ponía `estado='baja'` con la persona todavía trabajando, y desde ese segundo
desaparecía de todo lo que pregunta `estado = 'activo'`: headcount, organigrama, denominador de
las dos tasas de ausentismo, saldo de vacaciones, selector de superior y el gate del link público
de horas. Ahora la baja la escribe ESTE módulo, y solo cuando alguien la confirma.

🔑 PREVISIÓN Y HECHO SON DOS DATOS DISTINTOS, Y SE GUARDAN EN DOS LUGARES DISTINTOS.
`offboarding_instancias.fecha_ultimo_dia` es lo que se creía al abrir el trámite;
`empleados.fecha_egreso` es lo que pasó. **Que difieran NO es un error y acá no se sincronizan**:
pisar la previsión con el hecho borraría la única evidencia de cuánto se desvió una de la otra,
que es justamente la pregunta que el módulo permite responder.

## El orden de los gates es load-bearing

1. **Barrera de EMPRESA primero** (`find_instancia_min` con `empresa_id`, 404). Va antes que
   cualquier chequeo de estado: al revés, un 409 sobre una instancia de otra empresa confirmaría
   que existe, que es el oráculo de enumeración que el 404 único viene a cerrar. Es el mismo caso
   real que ya se corrigió en `_onboarding_iniciar.py`.
2. Estado de la instancia (409), después identidad del empleado (404), después su estado —los DOS
   chequeos, ya de baja y todavía sin ingresar (409)— y recién al final la forma de la fecha (400).
3. **Ninguna escritura ocurre hasta que pasaron TODAS las guardas.** Primero se valida entero,
   después se escribe: un rechazo no puede dejar al empleado de baja con la instancia abierta.

## El empleado se busca con la empresa de la INSTANCIA, no con la del header

Aplicación directa de "Vista vs Acción": la instancia ya se validó contra el header, y su
`empresa_id` es el dato autoritativo de a qué empresa pertenece esta baja. Usar el header acá
significaría que en modo consolidado (`None`) el lookup del empleado quedaría sin acotar.
"""
from datetime import date
from typing import Optional
from uuid import UUID

from services._audit_payloads_offboarding import payload_efectivizacion_baja
from utils.errors import AppError
from utils.estados_empleado import ESTADO_PREINGRESO
from utils.logger import logger

_CERRADOS = ("completado", "cancelado")
_NO_ENCONTRADO = ("Proceso de offboarding no encontrado", "OFFBOARDING_NO_ENCONTRADO", 404)


def efectivizar(repo, empleado_repo, audit, instancia_id: UUID, fecha_egreso: date,
                empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None) -> None:
    """
    Da de baja al empleado con su fecha real de egreso y cierra la instancia de offboarding.

    Args:
        repo: OffboardingRepo (o doble de test).
        empleado_repo: EmpleadoRepo (o doble de test).
        audit: AuditService (o doble de test).
        instancia_id: UUID de la instancia a cerrar.
        fecha_egreso: el día que la persona efectivamente dejó de trabajar.
        empresa_id: empresa activa del request. Acota A QUÉ INSTANCIA se puede apuntar
            (None = consolidado). La empresa en la que se escribe sale de la instancia.
        usuario_id: operador, para la trazabilidad de auditoría.

    Raises:
        AppError: OFFBOARDING_NO_ENCONTRADO (404) si la instancia no existe o es de otra empresa,
            y también si su empleado no aparece — el mismo 404, para no delatar la diferencia.
        AppError: OFFBOARDING_YA_CERRADO (409) si la instancia ya está completada o cancelada.
        AppError: EMPLEADO_YA_DE_BAJA (409) si el empleado ya fue dado de baja.
        AppError: EMPLEADO_PREINGRESO (409) si todavía no ingresó (ver la guarda, abajo).
        AppError: FECHA_EGRESO_INVALIDA (400) si la fecha es anterior al ingreso.
        AppError: FECHA_EGRESO_FUTURA (400) si la fecha todavía no ocurrió.
    """
    instancia = repo.find_instancia_min(str(instancia_id), empresa_id)
    if not instancia:
        raise AppError(*_NO_ENCONTRADO)
    if instancia.get("estado") in _CERRADOS:
        raise AppError(
            "El proceso de offboarding ya está cerrado", "OFFBOARDING_YA_CERRADO", 409,
        )

    empresa_instancia = instancia.get("empresa_id")
    empleado = empleado_repo.find_by_id(
        str(instancia["empleado_id"]),
        UUID(empresa_instancia) if empresa_instancia else None,
    )
    if not empleado:
        raise AppError(*_NO_ENCONTRADO)
    if empleado.estado == "baja":
        raise AppError("El empleado ya está dado de baja", "EMPLEADO_YA_DE_BAJA", 409)

    # 🔴 GUARDA EXPLÍCITA PARA EL PREINGRESO, Y VA ANTES DE `_validar_fecha` A PROPÓSITO.
    # Hasta el 18/8/2026 este caso lo cortaba `_validar_fecha` POR ACCIDENTE: un preingreso tiene
    # `fecha_ingreso` futura, así que cualquier `fecha_egreso` real caía en
    # `fecha_egreso < fecha_ingreso` y salía **FECHA_EGRESO_INVALIDA**, que MIENTE sobre el
    # motivo — le dice a RRHH que corrija la fecha cuando el problema es que esa persona nunca
    # entró. Y no siempre cortaba: con una fecha de egreso posterior a la de ingreso prevista, el
    # offboarding se completaba y dejaba a alguien que no trabajó nunca contando como una BAJA
    # del mes, o sea como rotación inventada.
    # Va antes de la fecha porque el estado es la pregunta anterior: si la persona no entró, qué
    # día se fue no tiene sentido. Mismo criterio de orden que la barrera de empresa.
    if empleado.estado == ESTADO_PREINGRESO:
        raise AppError(
            "Este empleado todavía no ingresó, así que no puede tener una baja. Si el ingreso "
            "no se concretó, corregí su ficha en vez de darlo de baja.",
            "EMPLEADO_PREINGRESO", 409,
        )

    _validar_fecha(fecha_egreso, empleado.fecha_ingreso)

    # El ORDEN de las dos escrituras importa: primero el empleado, después la instancia. Si
    # fallara la segunda, queda un empleado de baja con su offboarding todavía abierto — visible y
    # reintentable. Al revés quedaría la instancia cerrada con la persona contando como activa, o
    # sea el bug original de vuelta y sin ninguna pantalla que lo muestre.
    if not empleado_repo.dar_de_baja(str(instancia["empleado_id"]), fecha_egreso,
                                     UUID(empresa_instancia) if empresa_instancia else None):
        raise AppError(*_NO_ENCONTRADO)
    repo.marcar_completado(str(instancia_id), empresa_id)

    audit.registrar(**payload_efectivizacion_baja(
        instancia_id, str(instancia["empleado_id"]), fecha_egreso, usuario_id, empresa_instancia,
    ))
    logger.info(
        "Baja efectivizada",
        extra={"instancia_id": str(instancia_id), "empleado_id": str(instancia["empleado_id"])},
    )


def _validar_fecha(fecha_egreso: date, fecha_ingreso: date) -> None:
    """Las dos guardas de fecha. Separadas del cuerpo solo por largo; el orden no importa entre sí.

    🔴 LA DE FECHA FUTURA NO ES UNA VALIDACIÓN DE FORMA — ES EL BUG QUE ESTE MÓDULO ARREGLA.
    Aceptar una fecha que todavía no ocurrió reinstala exactamente el comportamiento viejo: alguien
    cargaría el egreso previsto para dentro de un mes, el empleado quedaría `estado='baja'` hoy, y
    volveríamos a tener gente trabajando que no cuenta en el headcount. La baja se efectiviza
    cuando ocurrió, no cuando se sabe que va a ocurrir; para lo segundo está `fecha_ultimo_dia`,
    que se carga al abrir el trámite y no toca el estado de nadie.
    """
    if fecha_egreso < fecha_ingreso:
        raise AppError(
            "La fecha de egreso no puede ser anterior a la fecha de ingreso",
            "FECHA_EGRESO_INVALIDA", 400,
        )
    if fecha_egreso > date.today():
        raise AppError(
            "La fecha de egreso no puede ser futura: la baja se efectiviza cuando ocurrió",
            "FECHA_EGRESO_FUTURA", 400,
        )

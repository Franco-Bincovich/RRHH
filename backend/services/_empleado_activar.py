"""
El pase de PREINGRESO a ACTIVO: el HECHO de que la persona efectivamente entró.

Es el espejo de `_offboarding_efectivizar.py` en el otro extremo del ciclo, y existe por el
mismo criterio con el que aquel se separó: **es un ACTO con consecuencia, no la edición de un
campo**. La consecuencia es que desde ese segundo la persona empieza a contar en todo lo que
pregunta `estado = 'activo'` —headcount, organigrama, los dos denominadores de ausentismo, la
base de la tasa de rotación, saldos de vacaciones, selector de superior, gate del link público
de horas— y en el conteo de altas del mes.

🔴 POR QUÉ UN ENDPOINT PROPIO Y NO `PUT /api/empleados/{id}` CON `estado: "activo"`.
Ese PUT existe y desde el 18/8 acepta el valor (el Literal lo permite), así que técnicamente
alcanzaría. Pero un PUT es una edición de campos: no puede exigir precondiciones sin volverse
un endpoint que a veces valida y a veces no, según qué campo venga en el body. Las tres guardas
de acá —que la persona SEA un preingreso, y sobre todo que su fecha de ingreso YA HAYA
OCURRIDO— no son validaciones de forma: son la definición del acto. Metidas en el PUT
quedarían como un caso especial escondido adentro de un update genérico, que es exactamente
donde nadie las busca cuando fallan.

## 🔴 LA GUARDA DE FECHA ES EL CORAZÓN DEL MÓDULO, no una validación de forma

Activar a alguien cuya `fecha_ingreso` todavía no llegó **reinstala el bug de la efectivización
de bajas por el eje contrario**. Aquel escribía `estado='baja'` con una `fecha_egreso` futura y
la persona desaparecía del headcount treinta días antes de irse; éste escribiría
`estado='activo'` con una `fecha_ingreso` futura y la persona aparecería en el headcount, en el
organigrama y en los denominadores de ausentismo **antes de haber trabajado un solo día**.

Es el mismo error con el signo cambiado, y la misma respuesta: **el estado se cambia cuando el
hecho ocurrió, no cuando se sabe que va a ocurrir.** Para lo segundo está el preingreso, que es
justamente la ficha cargada con la fecha prevista y sin efecto sobre ningún contador.

## EL PASE NO TOCA `fecha_ingreso`

La fecha prevista es la que se cumplió. Si la persona entró un día distinto del acordado, eso
se corrige por el PUT del legajo **antes** de activar, y recién después se activa — así el
cambio de fecha queda en el diff de auditoría del update, como cualquier corrección de dato, y
el evento de activación dice solo lo que pasó: cambió el estado.

Escribirla acá tendría el problema inverso al de `_offboarding_efectivizar`: allá se explica que
previsión y hecho son dos datos distintos que no se sincronizan. Acá son el MISMO dato —no hay
dos columnas—, así que pisarlo con `date.today()` borraría la fecha acordada sin dejar rastro.

## El orden de los gates

1. **Empresa/existencia primero** (`find_by_id` con `empresa_id`, 404). Va antes que cualquier
   chequeo de estado: al revés, un 409 sobre un empleado de otra empresa confirmaría que existe
   — el oráculo de enumeración que el 404 único cierra. Mismo caso que ya se corrigió en
   `_onboarding_iniciar` y en `_offboarding_efectivizar`.
2. Estado (409), y recién después la fecha (400).
3. **Ninguna escritura ocurre hasta que pasaron TODAS las guardas.**
"""
from datetime import date
from typing import Optional
from uuid import UUID

from schemas.empleado import EmpleadoResponse, EmpleadoUpdate
from services._audit_payloads_rrhh import payload_activacion_empleado
from services._empleados_utils import empleado_or_404
from utils.errors import AppError
from utils.estados_empleado import ESTADO_PREINGRESO
from utils.logger import logger


def activar(repo, audit, empleado_id: UUID, empresa_id: Optional[UUID] = None,
            usuario_id: Optional[str] = None) -> EmpleadoResponse:
    """
    Pasa un empleado de `preingreso` a `activo`: la persona entró.

    Args:
        repo: EmpleadoRepo (o doble de test).
        audit: AuditService (o doble de test).
        empleado_id: UUID del preingreso a activar.
        empresa_id: empresa activa del request. Acota A QUIÉN se puede apuntar (None =
            consolidado). La empresa que se audita sale del EMPLEADO, no de acá.
        usuario_id: operador, para la trazabilidad de auditoría.

    Returns:
        El empleado ya activo.

    Raises:
        AppError: EMPLEADO_NOT_FOUND (404) si no existe o es de otra empresa.
        AppError: EMPLEADO_NO_ES_PREINGRESO (409) si su estado no es `preingreso`.
        AppError: INGRESO_AUN_NO_OCURRIO (400) si su `fecha_ingreso` es futura.
    """
    empleado = empleado_or_404(repo.find_by_id(str(empleado_id), empresa_id))

    if empleado.estado != ESTADO_PREINGRESO:
        # El mensaje nombra el estado actual: quien lo lee está mirando una ficha y necesita
        # saber por qué el botón no hizo nada. No es un oráculo — ya pasó la barrera de empresa,
        # así que a esta altura el empleado es suyo y su estado ya se lo muestra la pantalla.
        raise AppError(
            f"Solo se puede activar un preingreso, y este colaborador está en '{empleado.estado}'",
            "EMPLEADO_NO_ES_PREINGRESO", 409,
        )

    if empleado.fecha_ingreso > date.today():
        # Ver el encabezado: esta guarda ES el módulo. El mensaje es para alguien de RRHH y dice
        # el paso siguiente, no el nombre del campo (mismo criterio que `require_empresa_id`).
        raise AppError(
            f"Todavía no llegó la fecha de ingreso ({empleado.fecha_ingreso}). Si la persona "
            f"entró antes de lo previsto, corregí la fecha en el legajo y después activala.",
            "INGRESO_AUN_NO_OCURRIO", 400,
        )

    # 🔑 Se reusa `repo.update` con un patch de UN campo en vez de agregarle un método propio al
    # repo: `_empleado_write_repo.py` estaba en 99/100 y un método nuevo lo pasaba de largo (hoy
    # está en 71: `dar_de_baja` se mudó a `_empleado_baja_repo.py` el 20/8). No es
    # una concesión al límite — `actualizar` ya hace exactamente esto (patch parcial con el
    # WHERE de empresa puesto) y un `activar` en el repo sería la misma query con otro nombre.
    actualizado = repo.update(str(empleado_id), EmpleadoUpdate(estado="activo"), empresa_id)
    if not actualizado:
        # El UPDATE no tocó ninguna fila pese a que el SELECT la encontró: se la llevaron entre
        # las dos queries. Mismo 404 que arriba, para no inventar un estado intermedio.
        raise AppError("Colaborador no encontrado", "EMPLEADO_NOT_FOUND", 404)

    audit.registrar(**payload_activacion_empleado(
        actualizado, usuario_id, empleado.empresa_id,
    ))
    logger.info("Preingreso activado", extra={"empleado_id": str(empleado_id)})
    return actualizado

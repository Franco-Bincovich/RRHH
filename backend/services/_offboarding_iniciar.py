"""
Alta de un proceso de offboarding.

Extraído de `offboarding_service.py`, que estaba en 149/150 y no admitía el endpoint de export.
Molde: `_onboarding_iniciar.py` —el hermano simétrico del módulo de entrada— y
`_offboarding_entrevista.py`, que ya se había separado de este mismo service.

POR QUÉ SALIÓ ESTE MÉTODO: era el único que tocaba DOS agregados (la instancia de offboarding y
la baja del empleado) y el único con una guarda de estado propia. Los otros son operaciones sobre
una instancia ya creada. **Hoy ya no toca dos agregados** —ver abajo— pero se queda separado: la
guarda de estado y el orden de los gates siguen siendo suyos, y volver a fusionarlo pasaría el
service de su límite.

🔴 ACÁ VIVÍA EL BUG: INICIAR EL TRÁMITE DABA DE BAJA AL EMPLEADO EN EL ACTO.
Esta función llamaba a `empleado_repo.dar_de_baja(...)` con `fecha_ultimo_dia` —o, si no venía,
con `hoy + 30 días`—, o sea escribía `estado='baja'` y una `fecha_egreso` EN EL FUTURO. Desde ese
mismo segundo la persona desaparecía de todo lo que pregunta `estado = 'activo'`, aunque le
quedaran treinta días trabajando: **headcount, organigrama, denominador de las dos tasas de
ausentismo, saldo de vacaciones, selector de superior y el gate del link público de horas.**

**La fecha prevista NO cambia el estado.** Un colaborador que sigue trabajando tiene que seguir
contando en todas esas superficies hasta el día que efectivamente se va. La previsión vive donde
siempre vivió —`offboarding_instancias.fecha_ultimo_dia`, que esta función sigue escribiendo a
través del repo— y el HECHO lo escribe `_offboarding_efectivizar.py`, en un endpoint aparte que
alguien tiene que apretar. Son dos datos distintos y ahora se guardan en dos momentos distintos.

⚠️ Al sacar la llamada se fue con ella un cálculo duplicado: el `fecha_ultimo_dia or hoy+30` que
había acá era una SEGUNDA copia del que hace `OffboardingRepo.create_offboarding`. La que manda
es la del repo, que es la que termina en la columna; la de acá solo alimentaba la baja. No queda
ningún default de fecha en este archivo, y eso es correcto.

🔴 EL ORDEN DE LOS GATES ES LOAD-BEARING, y por eso viaja completo: la barrera de EMPRESA va
ANTES del chequeo de "ya tiene un offboarding activo". Al revés, un empleado de otra empresa con
un proceso abierto respondería 409 `OFFBOARDING_ALREADY_ACTIVE` en vez de 404 — y ese 409
confirmaría que el empleado existe y que tiene un proceso, que es justo lo que el 404 único
viene a esconder. Es el mismo caso real que ya se corrigió en `_onboarding_iniciar.py`.

⚠️ Vive en `services/`, así que su límite es 150 líneas, como cualquier service. No hereda un
límite más alto por ser un satélite.
"""
from typing import Optional
from uuid import UUID

from schemas.offboarding import OffboardingCreate, OffboardingResponse
from services._audit_payloads_offboarding import payload_inicio_offboarding
from services._empleado_scope import ensure_empleado_de_empresa
from utils.errors import AppError
from utils.logger import logger


def iniciar(repo, empleado_repo, audit, data: OffboardingCreate,
            empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None) -> OffboardingResponse:
    """
    Inicia el proceso de offboarding para un empleado.

    La empresa en la que se escribe se hereda del empleado (es un dato del empleado, no del
    contexto de sesión). `empresa_id` del header se usa solo como barrera de a qué empleado se
    puede apuntar; validado eso, ambas coinciden por construcción.

    Crea la instancia y los activos corporativos por defecto a devolver, y audita el alta.
    🔴 NO toca al empleado: sigue `activo` y sin `fecha_egreso` hasta que alguien efectivice la
    baja por `POST /api/offboarding/{id}/efectivizar`. El porqué está en el encabezado.

    Args:
        repo: OffboardingRepo (o doble de test).
        empleado_repo: EmpleadoRepo (o doble de test).
        audit: AuditService (o doble de test).
        data: Datos del offboarding — empleado_id, motivo y fecha_ultimo_dia opcional.
        empresa_id: empresa activa del request. Acota A QUÉ EMPLEADO se puede apuntar (no la
            empresa en la que se escribe, que se deriva del empleado). None = todas.

    Returns:
        OffboardingResponse con la instancia creada y activos por defecto.

    Raises:
        AppError: EMPLEADO_NOT_FOUND (404) si el empleado no existe o es de otra empresa.
        AppError: OFFBOARDING_ALREADY_ACTIVE (409) si el empleado ya tiene uno activo.
    """
    empleado = ensure_empleado_de_empresa(empleado_repo, data.empleado_id, empresa_id)

    existente = repo.find_by_empleado(str(data.empleado_id))
    if existente:
        raise AppError(
            "El colaborador ya tiene un proceso de offboarding activo",
            "OFFBOARDING_ALREADY_ACTIVE",
            409,
        )

    empresa_id_str = empleado.empresa_id or ""
    offboarding = repo.create_offboarding(data, empresa_id_str)
    audit.registrar(**payload_inicio_offboarding(offboarding, usuario_id, empresa_id_str or None))

    logger.info(
        "Offboarding iniciado",
        extra={
            "empleado_id": str(data.empleado_id),
            "motivo": data.motivo,
            "instancia_id": str(offboarding.id),
        },
    )
    return offboarding

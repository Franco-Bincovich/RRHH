"""
Schemas Pydantic de recategorizaciones (migraciones 113, 116 y 117).

QUÉ ES. Capital Humano registra el cambio de rol, seniority o categoría de una persona. Carga
lo mínimo —colaborador, valores nuevos, motivo, impacto salarial opcional— y el sistema completa
el resto: los `*_anterior`, la empresa y quién lo registró. **Registro puro: no hay flujo de
aprobación.**

🔴 LOS `*_anterior` NO ENTRAN EN NINGÚN SCHEMA DE ENTRADA, Y ES LA DECISIÓN CENTRAL DEL MÓDULO.
Los completa el backend leyendo la última recategorización PREVIA a `fecha_efectiva` (y solo si
no hay ninguna, al empleado). Aceptarlos del cliente permitiría escribir un histórico que no
concuerda con el anterior, que es justo lo que la tabla existe para impedir. El porqué completo
está en `services/_recategorizacion_anteriores.py`.

🔴 NO HAY `RecategorizacionDelete` NI DELETE EN EL REPO. Se puede EDITAR, no borrar: se cargan a
mano y alguien se va a equivocar de fecha o de motivo, pero borrar rompe el histórico —y la
cadena de `*_anterior` que cuelga de él— y la auditoría ya registra quién editó qué.

⚠️ `empresa_id` NO viaja en el body y tampoco sale del header: se deriva del EMPLEADO. Es lo
contrario de `perfiles_puesto` (que es del grupo y va con NULL) y es Vista vs Acción: el sidebar
decide qué se MIRA, la entidad padre decide de quién ES la fila. La FK compuesta
`(empleado_id, empresa_id) → empleados(id, empresa_id)` lo respalda a nivel base.

⚠️ `impacto_salarial` SALE de `RecategorizacionResponse` en `None` cuando el rol no tiene
`COSTOS + READ`. El campo existe siempre en el schema —quitarlo cambiaría la forma de la
respuesta según el rol— y lo que cambia es el valor. Ver `recategorizacion_service`.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from schemas._legajo_normalizado import RecategorizacionNormalizada

# `motivo` es `text` sin límite en la base: este tope es de PRODUCTO. Es una línea de
# explicación ("paso de categoría 3 a 4 por antigüedad"), no un campo de notas.
MAX_MOTIVO = 500


class RecategorizacionCreate(RecategorizacionNormalizada):
    """Alta. Lo MÍNIMO que carga Capital Humano; el resto lo completa el sistema.

    🔴 El CHECK `recategorizaciones_algo_cambia_check` (migración 117) exige que al menos uno de
    los tres valores NUEVOS venga cargado. Se valida también en el service para devolver un 422
    legible en vez del 23514 crudo de la base — la base sigue siendo la garantía, esto es el
    mensaje.
    """

    empleado_id: UUID
    # Sin default acá: lo pone el service con `date.today()` si no viene. Un `default_factory`
    # en el schema haría que "hoy" se fije al importar el módulo en algunos escenarios de test.
    fecha_efectiva: Optional[date] = None
    rol_nuevo: Optional[str] = None
    seniority_nueva: Optional[str] = None
    categoria_nueva: Optional[str] = None
    motivo: str = Field(..., min_length=1, max_length=MAX_MOTIVO)
    impacto_salarial: Optional[Decimal] = None


class RecategorizacionUpdate(RecategorizacionNormalizada):
    """Edición. Todo opcional; `None` = "no lo toques".

    ⚠️ `empleado_id` NO se puede cambiar, y no es un olvido: mover una recategorización de
    persona invalidaría los `*_anterior` de las dos —la cadena de la que salía y la de la que
    pasa a formar parte— sin ninguna señal. Si se cargó sobre quien no era, se corrige el motivo
    y se registra la buena.
    """

    fecha_efectiva: Optional[date] = None
    rol_nuevo: Optional[str] = None
    seniority_nueva: Optional[str] = None
    categoria_nueva: Optional[str] = None
    motivo: Optional[str] = Field(default=None, min_length=1, max_length=MAX_MOTIVO)
    impacto_salarial: Optional[Decimal] = None


class RecategorizacionResponse(BaseModel):
    """Lo que sale. Los ids van tipados `UUID`, nunca `str` (error #1 del porteo a asyncpg).

    Los tres nombres resueltos por join (`empleado_nombre`, `empresa_nombre`,
    `registrado_por_nombre`) son DERIVADOS: no son datos de la fila sino resultado de cómo se la
    leyó. Por eso quedan fuera del diff de auditoría — ver `_audit_payloads_recategorizaciones`.
    """

    id: UUID
    empleado_id: UUID
    empresa_id: UUID
    fecha_efectiva: date
    rol_anterior: Optional[str] = None
    rol_nuevo: Optional[str] = None
    seniority_anterior: Optional[str] = None
    seniority_nueva: Optional[str] = None
    categoria_anterior: Optional[str] = None
    categoria_nueva: Optional[str] = None
    motivo: str
    # None puede significar DOS cosas distintas: "no se cargó" o "no tenés permiso de costos".
    # Es deliberado que no se distingan: un campo que dijera "oculto" confirmaría que hay un
    # monto cargado, que es la mitad del dato. Ver el encabezado del módulo.
    impacto_salarial: Optional[Decimal] = None
    registrado_por: Optional[UUID] = None
    registrado_por_nombre: Optional[str] = None
    empleado_nombre: Optional[str] = None
    empresa_nombre: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class RecategorizacionListResponse(BaseModel):
    """Página de la planilla. NACE PAGINADA.

    El historial de la ficha NO usa este schema: devuelve una lista plana. Son dos vistas de la
    misma tabla con formas distintas a propósito — ver el router.
    """

    items: List[RecategorizacionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

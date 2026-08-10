"""
Schemas Pydantic del registro de horas (`horas_proyecto`).

SALIÓ DE `schemas/proyectos.py`, que llegó a 208 contra un límite de 200 al sumarle los campos
de la migración 103. El corte no es solo por el límite: desde la 103 el registro de horas dejó
de ser una hija de `proyectos`. Una carga directa no tiene proyecto ni asignación, así que estos
schemas ya no describen "las horas DE UN PROYECTO" sino "las horas trabajadas", que es otra
entidad. Lo que quedó en `proyectos.py` —Proyecto, Asignación, Costeo— sí forma un bloque.

🔴 UN SOLO REGISTRO DE HORAS, DOS CAMINOS DE ESCRITURA:
  · CAMINO VIEJO — POST /api/proyectos/{id}/horas: cuelga de una `proyecto_asignaciones`,
    congela su `valor_hora` en `valor_hora_snapshot` y costea el proyecto. No se tocó.
  · CAMINO NUEVO — carga directa: NO pasa por ninguna asignación. Lleva cliente, modalidad del
    día y, si el empleado los escribe, proyecto y tarea como TEXTO LIBRE (no hay tabla de
    tareas, no hay cascada, y `proyectos` no participa).
Por eso los campos de ambos caminos son Optional: cada fila tiene los de UNO SOLO.
"""
from datetime import date, datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# Vocabulario cerrado, espejo exacto del CHECK `horas_proyecto_modalidad_check` (migración 103).
# Se guardan SLUGS; las etiquetas que ve el usuario ("Home Office" / "On site") las pone la UI.
# Es el criterio de todo vocabulario cerrado del repo (`proyectos.estado`,
# `empleados.modalidad_trabajo`): guardar el texto de pantalla convierte un cambio de redacción
# en una migración de datos.
Modalidad = Literal["home_office", "on_site"]


class HoraCreate(BaseModel):
    """Body del CAMINO VIEJO.

    `asignacion_id` sigue siendo REQUERIDO acá a propósito, aunque la columna ya sea nullable:
    es el contrato publicado de `POST /api/proyectos/{id}/horas`, y aflojarlo convertiría un 422
    de validación en un 404 de asignación inexistente. El camino nuevo va a traer su propio
    Create junto con su service.
    """
    asignacion_id: UUID
    fecha: date
    horas: float = Field(..., gt=0)
    descripcion: Optional[str] = None
    # Los cuatro de la 103, todos Optional: el camino viejo no los manda y no puede romperse.
    cliente_id: Optional[UUID] = None
    modalidad: Optional[Modalidad] = None
    proyecto_texto: Optional[str] = None
    tarea_texto: Optional[str] = None


class HoraResponse(BaseModel):
    id: UUID
    # Empresa DUEÑA de la carga. Viaja porque la baja desde la vista interna audita con la
    # empresa de la ENTIDAD y no con la del header (Vista vs Acción): sin este campo el service
    # tendría que volver a la base a buscar algo que la fila ya trajo. NO es un dato derivado de
    # un join —es columna NOT NULL de la tabla— así que sí puede entrar en un diff de auditoría.
    empresa_id: Optional[UUID] = None
    # Los tres que la 103 pasó a NULLABLE. Una carga directa no tiene ninguno de los tres.
    asignacion_id: Optional[UUID] = None
    proyecto_id: Optional[UUID] = None
    valor_hora_snapshot: Optional[float] = None
    # De quién son las horas. En el camino nuevo sale de la columna propia; en el viejo se
    # resuelve por la asignación (ver `_hora_row.build`).
    empleado_id: Optional[UUID] = None
    empleado_nombre: Optional[str] = None
    empleado_empresa_nombre: Optional[str] = None
    fecha: date
    horas: float
    # horas × valor_hora_snapshot, calculado en `_hora_row.build`. None —y NO 0.0— cuando no hay
    # snapshot: "no se puede costear" y "costó cero" son cosas distintas. Mismo criterio que
    # `CosteoResumen.pct_consumido`, que es None con presupuesto 0 por esa misma razón.
    costo: Optional[float] = None
    descripcion: Optional[str] = None
    # Los cuatro de la 103. `cliente_nombre` viaja RESUELTO para que la vista interna agrupe por
    # cliente sin una segunda vuelta al catálogo (molde: `padre_nombre` de TipoAusenciaResponse).
    # Es DERIVADO de un join: no entra en ningún diff de auditoría.
    cliente_id: Optional[UUID] = None
    cliente_nombre: Optional[str] = None
    modalidad: Optional[Modalidad] = None
    proyecto_texto: Optional[str] = None
    tarea_texto: Optional[str] = None
    created_at: datetime


class HoraListResponse(BaseModel):
    items: List[HoraResponse]
    total: int

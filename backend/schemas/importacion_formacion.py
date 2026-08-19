"""
Schemas del import de Formación por Excel (preview → confirmar).

Molde: `schemas/importacion_objetivos.py`. Mismo contrato de fondo: el preview devuelve la fila
YA RESUELTA (empleado matcheado o nombre_libre, estado traducido, fechas derivadas) y el
confirmar recibe esas filas de vuelta — resolver para MOSTRAR, revalidar para ESCRIBIR, porque
el body viaja por la red y el cliente lo puede alterar.

🔴 `estado` es Literal y no str: la traducción del Excel ("Finalizado"→completado) ya ocurrió en
el preview, así que si al confirmar llega otra cosa es el CLIENTE alterando el body — eso muere
en el 422, no entra a chocar contra el CHECK de la base. Mismo criterio que el `tipo` de
objetivos.

🔴 La empresa viaja en el BODY del confirmar Y como Form en el preview, nunca en el header:
importar es una ACCIÓN y la empresa es un dato del formulario (Vista vs Acción). El Excel no
menciona sociedades — todo el lote va a la empresa elegida (decisión 1 del 19/8).
"""
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class FilaFormacionError(BaseModel):
    """Una fila que NO se carga, con el motivo en texto para quien tiene el Excel abierto."""
    fila: int
    identificador: str
    motivo: str


class FilaFormacionPreview(BaseModel):
    fila: int
    titulo: str
    colaborador: str                      # lo que decía la celda, para que el usuario lo reconozca
    # Uno de los dos, nunca ninguno: o matcheó contra el padrón o entra como nombre suelto.
    empleado_id: Optional[UUID] = None
    empleado_nombre: Optional[str] = None  # el nombre del padrón, para que se vea QUÉ matcheó
    nombre_libre: Optional[str] = None
    estado: Literal["pendiente", "en_curso", "completado"]
    fecha_asignacion: Optional[str] = None   # "YYYY-MM-DD", primer día del mes derivado
    fecha_completado: Optional[str] = None
    proyecto: Optional[str] = None
    anio: Optional[str] = None               # TEXT en la base, "2026"
    mes: Optional[str] = None                # tal cual la celda ("marzo"/"Marzo")
    # Atributos del catálogo que esta fila aporta si su capacitación hay que crearla.
    tipo: Optional[str] = None
    entidad_capacitadora: Optional[str] = None
    modalidad: Optional[str] = None
    duracion_horas: Optional[float] = None
    avisos: List[str] = []                   # p. ej. "sin fecha derivable", "ambiguo en el padrón"


class CapacitacionACrear(BaseModel):
    """Un título que no existe en el catálogo de la empresa y el confirmar va a crear."""
    nombre: str
    tipo: Optional[str] = None
    entidad_capacitadora: Optional[str] = None
    modalidad: Optional[str] = None
    duracion_horas: Optional[float] = None
    avisos: List[str] = []                   # p. ej. la duración conflictiva entre filas


class ParParecido(BaseModel):
    """Dos nombres crudos distintos que probablemente sean la misma persona. RRHH decide."""
    nombre_a: str
    nombre_b: str
    motivo: str


class ImportacionFormacionPreviewResponse(BaseModel):
    filas_validas: List[FilaFormacionPreview]
    errores: List[FilaFormacionError]
    capacitaciones_a_crear: List[CapacitacionACrear]
    sin_match: List[str]                     # nombres que van a entrar como nombre_libre
    pares_parecidos: List[ParParecido]
    hoja_leida: Optional[str] = None
    total_hojas: int = 1


class ImportacionFormacionConfirmarRequest(BaseModel):
    empresa_id: UUID
    filas: List[FilaFormacionPreview]


class ImportacionFormacionConfirmarResponse(BaseModel):
    importados: int
    errores: List[FilaFormacionError]
    capacitaciones_creadas: List[str]        # nombres creados en el catálogo por este lote

"""
Schemas del import de objetivos por Excel (preview → confirmar).

Molde: `schemas/importacion.py` (el import de costos, que es el flujo con preview del repo).
Se separa en archivo propio por la misma razón que `importacion_nomina_empleados.py`: son dos
vocabularios distintos y mezclarlos obliga a leer el doble para entender uno.

🔴 EL PREVIEW DEVUELVE EL `responsable_id` YA RESUELTO, y eso es lo que hace que el confirmar no
tenga que volver a mirar `users`. Es el mismo contrato que `FilaNominaPreview.empleado_id`.
⚠️ Consecuencia asumida, igual que en costos: el cliente podría alterar ese id antes de
confirmar. El confirmar **revalida igual** (ver `objetivos_import_service.confirmar`): el
preview resuelve para MOSTRAR, no para autorizar.
"""
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class FilaObjetivoError(BaseModel):
    """Una fila que NO se va a cargar, con el motivo en texto para quien tiene el Excel abierto."""
    fila: int
    identificador: str
    motivo: str


class FilaObjetivoPreview(BaseModel):
    fila: int
    titulo: str
    responsable: str            # lo que decía la celda, para que el usuario lo reconozca
    # 🔴 Igual que `FilaNominaPreview.empleado_id`: viaja de ida y de vuelta, y el front reenvía
    # la fila tal cual la recibió. UUID acá hace que un id alterado o vacío muera en el 422.
    responsable_id: UUID        # resuelto contra users en el preview
    responsable_nombre: str
    prioridad: str
    fecha_entrega: Optional[str] = None     # "YYYY-MM-DD"
    descripcion: Optional[str] = None
    # ⚠️ Sigue siendo List[str] a propósito: NO entró en el inventario de los 5 de la sesión 0.6.
    # Tiene el mismo problema de fondo y su conversión (`UUID(u)` en `_a_create`) sigue viva y
    # funcionando. Cambiarlo pide el mismo rastreo completo; queda anotado, no hecho a medias.
    responsables_ids: List[str] = []        # acompañantes ya resueltos (sin el dueño)
    # Lo que se cargó de menos y el usuario tiene que saber: hoy solo "fecha" (celda ilegible).
    faltantes: List[str] = []


class ImportacionObjetivosPreviewResponse(BaseModel):
    filas_validas: List[FilaObjetivoPreview]
    errores: List[FilaObjetivoError]
    hoja_leida: Optional[str] = None        # cuál de las hojas se usó, para que no sorprenda
    total_hojas: int = 1


class ImportacionObjetivosConfirmarRequest(BaseModel):
    # 🔴 La empresa viaja en el BODY, no en el header: confirmar un import es una ACCIÓN y la
    # empresa es un dato del formulario (principio Vista vs Acción).
    empresa_id: UUID
    filas: List[FilaObjetivoPreview]


class ImportacionObjetivosConfirmarResponse(BaseModel):
    importados: int
    errores: List[FilaObjetivoError]

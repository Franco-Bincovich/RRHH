"""
Resolución de "qué entidades caen bajo un área". Compartido por los módulos que filtran por
área sin tener la columna: el área vive en `empleados`, y los listados llegan a ella por el
empleado. Un lookup batch por dimensión, nunca uno por fila.

Existe como módulo aparte porque la decisión de si el lookup se acota o no por empresa
DIFIERE entre módulos y no es obvia — está explicada en cada función. Ver también
`asignacion_repo.py` (capacitaciones), que hace lo mismo inline y puede migrar acá.
"""
from uuid import UUID

from integrations.supabase_client import supabase_admin


def empleados_de_area(area_id: UUID, empresa_id: UUID | None = None) -> list[str]:
    """Ids de los empleados del área. Con `empresa_id`, además acota a esa empresa.

    Acotar por empresa es correcto cuando la entidad filtrada pertenece a UNA empresa y sus
    empleados también (capacitaciones, inventario): el `.eq` extra es una barandilla barata.
    NO lo es cuando la entidad puede cruzar empresas — ver `proyecto_ids_con_area`.
    """
    q = supabase_admin.table("empleados").select("id").eq("area_id", str(area_id))
    if empresa_id:
        q = q.eq("empresa_id", str(empresa_id))
    return [e["id"] for e in (q.execute().data or [])]


def proyecto_ids_con_area(area_id: UUID) -> list[str]:
    """Ids de los proyectos con AL MENOS UN empleado asignado del área dada.

    🔴 QUÉ SIGNIFICA EL FILTRO — decisión de producto, no detalle de implementación.
    `proyectos` NO tiene columna de área: un proyecto no pertenece a un área, tiene gente
    asignada y esa gente sí tiene área. Así que "proyectos del área X" solo puede querer decir
    "proyectos donde trabaja al menos alguien de X", y eso es lo que hace esta función.

    Cuenta asignaciones ACTIVAS E INACTIVAS. Que un proyecto haya involucrado a alguien de
    Sistemas es un hecho histórico que conviene poder encontrar, y es además consistente con el
    resto del módulo, que tampoco filtra por `activo` en ningún listado. Si alguna vez hace
    falta "solo los que están hoy", eso es un filtro `activo` propio — no un cambio de este.

    ⚠️ CASO BORDE, ES LA DEFINICIÓN Y NO UN BUG: un proyecto SIN ningún empleado asignado no
    aparece bajo ninguna área. No hay área que pueda reclamarlo.

    🔴 POR QUÉ ACÁ NO SE ACOTA POR EMPRESA, a diferencia del resto.
    Un proyecto de la empresa A puede tener asignada gente de la empresa B — el modelo lo
    soporta a propósito, y por eso `proyecto_asignaciones` lleva `empleado_empresa_id`. Acotar
    la búsqueda de empleados por la empresa activa dejaría el conjunto vacío y el filtro
    devolvería CERO proyectos sin ningún error. No agregar ese `.eq` "por consistencia" con
    capacitaciones: los dos módulos no tienen el mismo modelo.

    Dos queries batch fijas, ambas con `.in_()`: no escala con la cantidad de proyectos.
    """
    empleados = empleados_de_area(area_id)
    if not empleados:
        return []
    filas = (supabase_admin.table("proyecto_asignaciones").select("proyecto_id")
             .in_("empleado_id", empleados).execute().data or [])
    return list({f["proyecto_id"] for f in filas})

"""
Contrato de datos de una asignación cuyo contexto ya se resolvió (sin lógica, sin IO).

Extraído de `asignaciones_service.py`, que llegó a 155 contra un límite de 150 al sumar este
tipo y sus ramas. Es un contrato, no lógica de servicio, y lo consumen dos módulos —el service
que lo recibe y el import de nómina que lo construye—, así que tener su propio archivo también
lo deja importable sin arrastrar el service entero.

Se movió VERBATIM: los campos, el orden y la explicación son idénticos.
"""
from typing import NamedTuple


class AsignacionPrecargada(NamedTuple):
    """Los tres datos que `asignar` normalmente resuelve con tres queries, cuando el caller YA
    los tiene de la misma operación.

    Lo usa el import de nómina: acaba de crear/actualizar al empleado (sabe su empresa y si lo
    dio de baja) y el proyecto sale del cache de `NominaCatalogos`/`NominaProyectos`, que solo
    contiene proyectos de esa empresa por construcción. Sin esto paga 3 queries por fila del CSV.

    🔴 Es un NamedTuple y no tres parámetros sueltos ni un booleano a propósito: los tres valores
    van juntos o no van, así que no se puede llenar a medias ni "apagar la validación" sin
    aportar el dato que la reemplaza. `asignar` sin este argumento se comporta IDÉNTICO a antes.
    """
    proyecto_existe_en_empresa: bool   # el caller ya probó que el proyecto es de esa empresa
    empleado_empresa_id: str           # empresa del empleado (NO la del proyecto — pueden diferir)
    empleado_estado: str               # 'activo' | 'baja' | ...

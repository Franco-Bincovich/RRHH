"""
Helper del export de empleados: proyecta el legajo a columnas legibles (sin UUIDs crudos).

Molde de _ausencias_export.construir_filas_export. Los headers del Excel son las keys de
cada dict. **Cero N+1**: usa SOLO campos que EmpleadoResponse ya trae resueltos por el
listado (area_nombre, empresa_nombre y manager_nombre vienen de los joins embebidos del
repo — ninguna columna dispara una query por fila).
"""

from typing import List

from schemas.empleado import EmpleadoResponse


def _fecha(v) -> str:
    """Formatea date/datetime a dd/mm/aaaa (descarta hora); '' si es None."""
    return v.strftime("%d/%m/%Y") if v else ""


def construir_filas_export(items: List[EmpleadoResponse]) -> List[dict]:
    """Proyecta empleados a las columnas legibles del legajo (sin UUIDs crudos). None → celda vacía."""
    return [
        {
            "Legajo": e.legajo,
            "Nombre": e.nombre,
            "Apellido": e.apellido,
            "DNI": e.dni,
            "CUIL": e.cuil,
            "Email corporativo": e.email_corporativo,
            "Teléfono": e.telefono,
            "Empresa": e.empresa_nombre,
            "Área": e.area_nombre,
            "Rol principal": e.roles[0] if e.roles else "",
            "Roles": ", ".join(e.roles) if e.roles else "",
            "Seniority": e.seniority,
            "Gerencia": e.gerencia,
            "Sector": e.sector,
            "Categoría": e.categoria,
            "Manager": e.manager_nombre,
            "Tipo de contrato": e.tipo_contrato,
            "Modalidad": e.modalidad_trabajo,
            "Horas de contrato": e.horas_contrato,
            "Fecha de ingreso": _fecha(e.fecha_ingreso),
            # Del domicilio salen SOLO las dos agregables: en un listado, calle/número/piso
            # no responden ninguna pregunta, y agregarlas por completitud infla el archivo.
            "Localidad": e.domicilio_localidad,
            "Provincia": e.domicilio_provincia,
            "Estado": e.estado,
            "Es líder": "Sí" if e.es_lider else "No",
            "Días de vacaciones": e.dias_vacaciones_asignados,
        }
        for e in items
    ]

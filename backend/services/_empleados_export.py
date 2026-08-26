"""
Helper del export de empleados: proyecta el legajo a columnas legibles (sin UUIDs crudos).

Molde de _ausencias_export.construir_filas_export. Los headers del Excel son las keys de
cada dict. **Cero N+1**: usa SOLO campos que EmpleadoResponse ya trae resueltos por el
listado (area_nombre, empresa_nombre y manager_nombre vienen de los joins embebidos del
repo — ninguna columna dispara una query por fila).

🔴 LA FUENTE DE VERDAD DE QUÉ COLUMNAS SALEN ES **LA FICHA**, no esta lista (bloque N7).
Hasta el 25/8/2026 los dos lados divergían en **11 campos**: la ficha mostraba tipo de
documento, sexo, fecha de nacimiento, teléfono alternativo, email alternativo, domicilio,
estudios, ubicación, turno, organismo y perfil, y **ninguno de los once estaba en el archivo**.
(Los dos últimos ya no están en ninguno de los dos lados: salieron del legajo en el bloque N2.)
Alguien de Capital Humano que exportaba para trabajar afuera perdía la mitad del legajo sin
que nada se lo dijera. La regla que queda: **el export es un superconjunto de la ficha** —
todo lo que la ficha muestra sale acá, más lo que solo tiene sentido en un listado (la baja y
el cupo de vacaciones, que la ficha resuelve en secciones propias).

⚠️ El caso al revés —una columna acá que la ficha no muestre— es el que hay que mirar con
cuidado: significa que el archivo afirma algo que la pantalla no. Las tres que quedan
(`Fecha de egreso`, `Motivo de baja`, `Días de vacaciones`) están declaradas arriba y tienen
su lugar propio en la ficha; cualquier cuarta es un desalineamiento nuevo.
"""

from typing import List, Optional

from schemas.empleado import EmpleadoResponse


def _fecha(v) -> str:
    """Formatea date/datetime a dd/mm/aaaa (descarta hora); '' si es None."""
    return v.strftime("%d/%m/%Y") if v else ""


def _si_no(v: Optional[bool]) -> str:
    """Booleano nullable a texto. None → '' y NO 'No': la columna vacía dice 'nadie lo declaró',
    que es distinto de una negativa. `es_lider` es el único que no pasa por acá (no es nullable)."""
    return "" if v is None else ("Sí" if v else "No")


def _domicilio(e: EmpleadoResponse) -> str:
    """El domicilio desglosado en UNA línea legible; cae al texto libre si no hay desglose.

    Espejo de `components/features/empleados/ficha/_domicilio.ts::domicilioLegible`, que es lo
    que la ficha muestra. Localidad y provincia salen ADEMÁS en columnas propias: son las dos
    agregables de un listado (cuánta gente hay en cada provincia), y esta columna es la
    dirección para leer, no para agrupar.
    """
    calle = " ".join(x for x in (e.domicilio_calle, e.domicilio_numero) if x)
    partes = [x for x in (calle, e.domicilio_piso_depto, e.domicilio_localidad,
                          e.domicilio_provincia, e.domicilio_cp) if x]
    return ", ".join(partes) or (e.domicilio or "")


def construir_filas_export(items: List[EmpleadoResponse]) -> List[dict]:
    """Proyecta empleados a las columnas legibles del legajo (sin UUIDs crudos). None → celda vacía."""
    return [
        {
            # Identidad
            "Legajo": e.legajo,
            "Nombre": e.nombre,
            "Apellido": e.apellido,
            "Tipo de documento": e.tipo_documento,
            "Documento": e.dni,
            "CUIT/CUIL": e.cuil,
            "Sexo": e.sexo,
            "Fecha de nacimiento": _fecha(e.fecha_nacimiento),
            # Contacto
            "Email corporativo": e.email_corporativo,
            "Email alternativo": e.email_personal,
            "Teléfono": e.telefono,
            "Teléfono alternativo": e.telefono_alternativo,
            "Domicilio": _domicilio(e),
            # Del domicilio salen ADEMÁS las dos agregables: en un listado, calle/número/piso
            # no responden ninguna pregunta que no responda ya la columna "Domicilio".
            "Localidad": e.domicilio_localidad,
            "Provincia": e.domicilio_provincia,
            "Estudios": e.estudios,
            # Organización
            "Empresa": e.empresa_nombre,
            "Área": e.area_nombre,
            "Superior inmediato": e.manager_nombre,
            "Rol principal": e.roles[0] if e.roles else "",
            "Roles": ", ".join(e.roles) if e.roles else "",
            "Equipo": e.equipo,
            "Ubicación": e.ubicacion,
            # Contrato
            "Seniority": e.seniority,
            "Categoría": e.categoria,
            "Turno": e.turno,
            "Horas de contrato": e.horas_contrato,
            "Modalidad": e.modalidad_trabajo,
            "Tipo de contrato": e.tipo_contrato,
            "Fecha de ingreso": _fecha(e.fecha_ingreso),
            # La fecha con la que se reconoce la ANTIGÜEDAD, que puede no ser la de ingreso
            # (una cesión, un pase entre sociedades del grupo) y es la que decide el cupo de
            # vacaciones. Va al lado de la de ingreso justamente para que la diferencia se vea.
            "Fecha de ingreso reconocida": _fecha(e.fecha_ingreso_reconocida),
            "Estado": e.estado,
            # Al lado de la de ingreso y no al final: se leen juntas, y una baja sin fecha en
            # la columna de al lado es la que se nota. Sale VACÍA para quien sigue trabajando
            # —que es la mayoría de las filas— y eso es correcto: la columna dice "cuándo se
            # fue", y de la gente activa la respuesta es "todavía no".
            "Fecha de egreso": _fecha(e.fecha_egreso),
            "Motivo de baja": e.motivo_baja,
            # Rol dentro de la estructura
            "Es líder": "Sí" if e.es_lider else "No",
            "Liderazgo (declarado)": e.liderazgo,
            "Product owner": _si_no(e.product_owner),
            "Co-sourcing": _si_no(e.co_sourcing),
            # Los dos ejes del 9-box de sucesión. ⚠️ Hoy salen "medio" para TODA la plantilla
            # (41/41 medido en producción el 25/8/2026) porque son el DEFAULT de la columna y
            # nadie los cargó nunca: el único escritor es el assessment, que está apagado. Es el
            # valor real del registro, no un promedio calculado — leer esa columna como una
            # calificación de Capital Humano sería leer mal.
            "Potencial (9-box)": e.potencial,
            "Desempeño (9-box)": e.desempeno,
            "Días de vacaciones": e.dias_vacaciones_asignados,
        }
        for e in items
    ]

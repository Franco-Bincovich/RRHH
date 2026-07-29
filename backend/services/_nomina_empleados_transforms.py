"""
VOCABULARIO DE COLUMNAS del CSV de nómina de empleados (27 requeridas + opcionales, ';', latin1).
Sin IO ni acceso a DB: qué columnas existen, cuáles son obligatorias, cómo leer una celda por
nombre tolerando variaciones de caso/espacios, y cómo armar el dict de una fila.

La interpretación de los VALORES (fechas, SI/NO, M/F, "NO APLICA") vive en `_nomina_parsers.py`,
que es la mitad reusable por otros imports del mismo formato — ver su encabezado.
"""
from typing import Optional

from services._nomina_parsers import _norm, limpiar, parse_bool, parse_fecha, parse_sexo

# Headers exactos del archivo real. El match se hace por nombre NORMALIZADO (case/espacios).
HEADERS = [
    "Apellido", "Nombre", "DNI", "CUIT", "Sexo", "Edad", "Email",
    "Fecha Nacimiento", "Fecha Ingreso", "Fecha Ingreso Reconocida",
    "Organismo", "Gerencia", "Sector", "Equipo", "Rol", "Seniority",
    "Categoria", "Modalidad Contratacion", "Co-sourcing", "Apellido Superior",
    "Nombre Superior", "Liderazgo", "Ubicación Física", "Carga Horaria",
    "Product Owner", "Fecha Baja", "Motivo Baja",
]

# Columnas que el parser LEE si están, y cuya ausencia NO invalida el archivo.
#
# 🔴 "Legajo" es opcional a propósito. `validar_headers` rechaza el archivo entero si falta una
# columna requerida, así que sumarlo a HEADERS haría que todo CSV histórico —ninguno lo trae—
# se caiga completo en la fila 1, con cero empleados cargados, por una columna que la mayoría
# de los flujos no necesita. Y el legajo importa: es el ancla del import de vacaciones, que no
# trae DNI ni CUIT. Optativo es la única forma de pedirlo sin romper lo que ya funciona.
#
# `_get` ya devuelve "" para una columna ausente, y `limpiar("")` da None, así que el parseo de
# una columna opcional no necesita ninguna rama especial.
HEADERS_OPCIONALES = ["Legajo"]


def validar_headers(fieldnames: Optional[list]) -> Optional[str]:
    """Devuelve un mensaje si faltan columnas REQUERIDAS; None si están todas.

    Solo mira `HEADERS`. Las de `HEADERS_OPCIONALES` se leen si vienen y se ignoran si no —
    un archivo sin ellas es válido y se importa completo.
    """
    if not fieldnames:
        return "El archivo está vacío o no tiene encabezados"
    presentes = {_norm(f) for f in fieldnames if f}
    faltan = [h for h in HEADERS if _norm(h) not in presentes]
    if faltan:
        return f"Faltan columnas: {', '.join(faltan)}"
    return None


def _get(row: dict, header: str) -> str:
    """Lee una celda por header normalizado (tolera variaciones de espacios/caso)."""
    objetivo = _norm(header)
    for k, v in row.items():
        if k and _norm(k) == objetivo:
            return (v or "").strip()
    return ""


def identificador(row: dict) -> str:
    """'APELLIDO, NOMBRE' desde la fila cruda (para el reporte, aun si el parseo falló)."""
    partes = [x for x in (_get(row, "Apellido"), _get(row, "Nombre")) if x]
    return ", ".join(partes) or "(sin nombre)"


def obligatorios_faltantes(f: dict) -> list:
    """Campos sin los que NO se puede crear el empleado (bloqueantes). Devuelve etiquetas.
    Los 3 del negocio (nombre/apellido/DNI) + los que exige el schema/DB para poder crear."""
    checks = [
        ("nombre", f["nombre"]), ("apellido", f["apellido"]), ("DNI", f["dni"]),
        ("Organismo (empresa)", f["_empresa"]), ("Sector (área)", f["_area"]),
        ("Rol", f["roles"]), ("Fecha Ingreso", f["fecha_ingreso"]),
    ]
    return [etiqueta for etiqueta, valor in checks if not valor]


def parsear_fila(row: dict) -> dict:
    """Extrae y tipa los campos de una fila. Lanza ValueError si una fecha es inválida.
    Devuelve los campos del empleado + empresa/área/superior aparte (claves con '_')."""
    rol = limpiar(_get(row, "Rol"))
    reconocida = parse_fecha(_get(row, "Fecha Ingreso Reconocida"))
    return {
        "apellido": _get(row, "Apellido"),
        "nombre": _get(row, "Nombre"),
        # Columna OPCIONAL (ver HEADERS_OPCIONALES): si el archivo no la trae, `_get` devuelve
        # "" y `limpiar` lo pasa a None, que es "sin legajo" — igual que hoy.
        "legajo": limpiar(_get(row, "Legajo")),
        "dni": limpiar(_get(row, "DNI")),
        "cuil": limpiar(_get(row, "CUIT")),
        "sexo": parse_sexo(_get(row, "Sexo")),
        "email_corporativo": _get(row, "Email").lower(),
        "fecha_nacimiento": parse_fecha(_get(row, "Fecha Nacimiento")),
        "fecha_ingreso": parse_fecha(_get(row, "Fecha Ingreso")),
        "fecha_ingreso_reconocida": reconocida.isoformat() if reconocida else None,
        "gerencia": limpiar(_get(row, "Gerencia")),
        "equipo": limpiar(_get(row, "Equipo")),
        "roles": [rol] if rol else [],
        "seniority": limpiar(_get(row, "Seniority")),
        "categoria": limpiar(_get(row, "Categoria")),
        "tipo_contrato": _get(row, "Modalidad Contratacion"),  # texto libre tal cual
        "co_sourcing": parse_bool(_get(row, "Co-sourcing")),
        "liderazgo": limpiar(_get(row, "Liderazgo")),
        "ubicacion": limpiar(_get(row, "Ubicación Física")),
        "turno": limpiar(_get(row, "Carga Horaria")),
        "product_owner": parse_bool(_get(row, "Product Owner")),
        "fecha_baja": parse_fecha(_get(row, "Fecha Baja")),
        "motivo_baja": limpiar(_get(row, "Motivo Baja")),
        # No se persisten en empleados: se usan para crear empresa/área y para el reporte.
        "_empresa": _get(row, "Organismo"),
        "_area": _get(row, "Sector"),
        "_superior_apellido": limpiar(_get(row, "Apellido Superior")),
        "_superior_nombre": limpiar(_get(row, "Nombre Superior")),
    }

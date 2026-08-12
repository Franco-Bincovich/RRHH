"""
Servicio de importación masiva de nómina via CSV.
parse_nomina_csv: parsea, valida, resuelve DNI→empleado y detecta duplicados (anio, mes).
"""
import csv
import io
from uuid import UUID

from repositories.empleado_repo import EmpleadoRepo
from repositories.nomina_repo import NominaRepo
from utils.logger import logger

REQUIRED_FIELDS_NOMINA = {"dni", "anio", "mes", "salario_bruto", "neto"}


def _existing_nomina(empresa_id: str) -> set[tuple]:
    """Retorna el conjunto de (empleado_id, anio, mes) ya registrados en la empresa."""
    return NominaRepo().periodos_cargados(empresa_id)


def parse_nomina_csv(content: str, empresa_id: str) -> tuple[list[dict], list[dict]]:
    """
    Parsea y valida el CSV de nómina para la empresa indicada.

    Args:
        content: Contenido del CSV (header + filas de datos).
        empresa_id: ID de la empresa — filtra el lookup de empleados por DNI y
                    determina qué registros ya existen en costos_nomina.

    Returns:
        Tupla (filas_validas, errores). Cada fila válida incluye empleado_id resuelto,
        nombre_empleado y es_actualizacion=True si ya existe nómina para (empleado_id, anio, mes).
        Los errores de DNI no encontrado también van en la lista de errores.
    """
    existing = _existing_nomina(empresa_id)
    repo = EmpleadoRepo()

    try:
        reader = csv.DictReader(io.StringIO(content))
        if not reader.fieldnames:
            return [], [{"fila": 0, "campo": "archivo", "error": "El archivo está vacío o no tiene encabezados"}]

        fieldnames_lower = {f.strip().lower() for f in reader.fieldnames if f}
        missing = REQUIRED_FIELDS_NOMINA - fieldnames_lower
        if missing:
            return [], [{"fila": 0, "campo": "encabezados", "error": f"Faltan columnas: {', '.join(sorted(missing))}"}]

        validas: list[dict] = []
        errores: list[dict] = []

        for fila_num, raw_row in enumerate(reader, start=2):
            row = {k.strip().lower(): (v.strip() if v else "") for k, v in raw_row.items() if k}

            missing_values = [f for f in REQUIRED_FIELDS_NOMINA if not row.get(f)]
            if missing_values:
                errores.append({"fila": fila_num, "campo": "múltiples", "error": f"Vacíos: {', '.join(sorted(missing_values))}"})
                continue

            # anio
            try:
                anio = int(row["anio"])
                if not (2000 <= anio <= 2100):
                    raise ValueError
            except ValueError:
                errores.append({"fila": fila_num, "campo": "anio", "error": f"Año inválido '{row['anio']}'. Rango: 2000–2100"})
                continue

            # mes
            try:
                mes = int(row["mes"])
                if not (1 <= mes <= 12):
                    raise ValueError
            except ValueError:
                errores.append({"fila": fila_num, "campo": "mes", "error": f"Mes inválido '{row['mes']}'. Rango: 1–12"})
                continue

            # salario_bruto
            try:
                bruto = float(row["salario_bruto"])
                if bruto < 0:
                    raise ValueError
            except ValueError:
                errores.append({"fila": fila_num, "campo": "salario_bruto", "error": f"Valor inválido '{row['salario_bruto']}'. Debe ser un número ≥ 0"})
                continue

            # neto
            try:
                neto = float(row["neto"])
                if neto < 0:
                    raise ValueError
            except ValueError:
                errores.append({"fila": fila_num, "campo": "neto", "error": f"Valor inválido '{row['neto']}'. Debe ser un número ≥ 0"})
                continue

            # DNI → empleado (dentro de la empresa)
            dni = row["dni"]
            empleado = repo.find_by_dni(dni, UUID(empresa_id))
            if not empleado:
                errores.append({"fila": fila_num, "campo": "dni", "error": f"DNI {dni} no encontrado en la empresa seleccionada"})
                continue

            validas.append({
                "fila": fila_num,
                "dni": dni,
                "nombre_empleado": f"{empleado.nombre} {empleado.apellido}".strip(),
                "empleado_id": empleado.id,
                "anio": anio,
                "mes": mes,
                "salario_bruto": bruto,
                "neto": neto,
                "es_actualizacion": (empleado.id, anio, mes) in existing,
            })

        logger.info("CSV de nómina parseado", extra={"validas": len(validas), "errores": len(errores), "empresa_id": empresa_id})
        return validas, errores

    except Exception as exc:
        logger.error("Error al parsear CSV de nómina", extra={"error": str(exc)})
        # 🔴 El detalle NO va al usuario: este `except` envuelve TODO el loop, incluidos los
        # lookups a la base, así que `str(exc)` puede traer un error de httpx/Supabase — texto en
        # inglés y detalle de infraestructura en la pantalla de RRHH. El crudo está en el log de
        # arriba, que es donde sirve. Mismo criterio que `_error_ia` y que el handler global.
        return [], [{"fila": 0, "campo": "archivo",
                     "error": "No se pudo procesar el archivo. Revisá que sea el CSV de nómina "
                              "con el formato esperado y volvé a intentar."}]

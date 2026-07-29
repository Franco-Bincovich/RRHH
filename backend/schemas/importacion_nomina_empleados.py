"""
Schemas del import de nómina de empleados (CSV 27 columnas).

EmpleadoCreateNomina / EmpleadoUpdateNomina extienden los schemas compartidos de empleados
con los campos del legajo-nómina (migración 064), para NO tocar el schema base. El resultado
clasifica cada fila en 3 grupos (OK · con faltantes · no cargados) y distingue nuevos vs
actualizados (dedup por DNI). Preserva el superior sin resolver el manager (pieza posterior).
"""
from typing import List, Optional

from pydantic import BaseModel

from schemas.empleado import EmpleadoCreate, EmpleadoUpdate

# fecha_ingreso_reconocida va como string ISO (repo.save/update solo str-ifica
# fecha_ingreso/fecha_nacimiento; un date crudo no serializa a JSON).


class EmpleadoCreateNomina(EmpleadoCreate):
    """EmpleadoCreate + campos de nómina. email opcional (se permite crear sin email)."""
    email_corporativo: Optional[str] = None  # tolerante: si falta, se crea con email null
    fecha_ingreso_reconocida: Optional[str] = None
    equipo: Optional[str] = None
    co_sourcing: Optional[bool] = None
    product_owner: Optional[bool] = None
    liderazgo: Optional[str] = None
    motivo_baja: Optional[str] = None


class EmpleadoUpdateNomina(EmpleadoUpdate):
    """EmpleadoUpdate + campos de nómina (para actualizar un empleado ya existente por DNI)."""
    fecha_ingreso_reconocida: Optional[str] = None
    equipo: Optional[str] = None
    co_sourcing: Optional[bool] = None
    product_owner: Optional[bool] = None
    liderazgo: Optional[str] = None
    motivo_baja: Optional[str] = None


class FilaConFaltantes(BaseModel):
    """Fila cargada a la que le faltan datos no-bloqueantes (por ahora, solo email)."""
    fila: int
    empleado: str
    faltan: List[str]


class FilaNoCargada(BaseModel):
    """Fila que NO se pudo cargar (falta un obligatorio o falló la creación)."""
    fila: int
    empleado: str
    motivo: str


class ImportacionNominaEmpleadosResult(BaseModel):
    """Reporte de un import. `parcial=True` significa que el archivo NO se terminó de procesar.

    El corte parcial NO es un error: las filas procesadas quedaron cargadas y el reintento con
    el MISMO archivo continúa donde quedó, porque el dedup por (empresa_id, dni) manda las ya
    cargadas por la rama de update. No hay estado de progreso que limpiar.
    """
    total: int
    creados: int          # altas nuevas (DNI no existía)
    actualizados: int     # updates (DNI ya existía) — dedup
    cargados_ok: int      # cargados sin faltantes (nuevos + actualizados)
    con_faltantes: List[FilaConFaltantes]
    no_cargados: List[FilaNoCargada]
    parcial: bool = False                      # se agotó el presupuesto de tiempo
    ultima_fila_procesada: Optional[int] = None  # nº de fila del CSV (el encabezado es la 1)
    filas_sin_procesar: int = 0                # las que quedaron en el archivo, sin tocar
    segundos: Optional[float] = None           # tiempo consumido, para calibrar el presupuesto


def _base_nomina(f: dict, email: Optional[str]) -> dict:
    """Campos comunes CSV→empleado (sin empresa/area, que se resuelven en el service)."""
    return {
        "nombre": f["nombre"], "apellido": f["apellido"], "email_corporativo": email,
        "legajo": f["legajo"],
        "roles": f["roles"], "tipo_contrato": f["tipo_contrato"], "fecha_ingreso": f["fecha_ingreso"],
        "dni": f["dni"], "cuil": f["cuil"], "sexo": f["sexo"], "fecha_nacimiento": f["fecha_nacimiento"],
        "gerencia": f["gerencia"], "seniority": f["seniority"], "categoria": f["categoria"],
        "ubicacion": f["ubicacion"], "turno": f["turno"],
        "fecha_ingreso_reconocida": f["fecha_ingreso_reconocida"], "equipo": f["equipo"],
        "co_sourcing": f["co_sourcing"], "product_owner": f["product_owner"],
        "liderazgo": f["liderazgo"], "motivo_baja": f["motivo_baja"],
    }


def build_create(f: dict, empresa_id, area_id, email: Optional[str]) -> EmpleadoCreateNomina:
    """Arma el EmpleadoCreateNomina de una fila (alta nueva)."""
    return EmpleadoCreateNomina(empresa_id=empresa_id, area_id=area_id, **_base_nomina(f, email))


def build_update(f: dict, area_id, email: Optional[str]) -> EmpleadoUpdateNomina:
    """Arma el EmpleadoUpdateNomina de una fila (actualización de un DNI existente).
    email None se descarta en el update (exclude_none) → no pisa el email ya cargado."""
    return EmpleadoUpdateNomina(area_id=area_id, **_base_nomina(f, email))

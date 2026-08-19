"""
PREVIEW del import de Formación: lee el Excel, traduce estado y fechas, matchea colaboradores
contra el padrón de la empresa y clasifica cada fila. NO persiste nada y NO autoriza nada — el
confirmar revalida, porque el body viaja por la red. Molde: `objetivos_import_preview.py`.

🔴 LA EMPRESA ES PARÁMETRO DEL PREVIEW, a diferencia de objetivos (que resuelve contra `users`,
globales): acá el padrón y el catálogo son POR empresa, y el Excel no menciona sociedades — todo
el lote va a la empresa del formulario (decisión 1 del 19/8/2026).
"""
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from repositories.asignacion_repo import AsignacionRepo
from repositories.capacitacion_repo import CapacitacionRepo
from schemas.importacion_formacion import (
    CapacitacionACrear, FilaFormacionError, FilaFormacionPreview,
    ImportacionFormacionPreviewResponse, ParParecido,
)
from services import _formacion_import_transforms as tx
from services._formacion_import_valores import derivar_fechas
from services._formacion_matcheo import IndiceEmpleados, pares_parecidos
from services._import_excel import abrir, filas, hojas
from utils.errors import AppError


def _evaluar_fila(n: int, fila: dict, indice: IndiceEmpleados
                  ) -> Tuple[Optional[FilaFormacionPreview], Optional[FilaFormacionError]]:
    """Una fila → válida o error. Nunca las dos, nunca ninguna."""
    f = tx.parsear_fila(fila)
    motivo = tx.clasificar(f)
    if motivo:
        return None, FilaFormacionError(fila=n, identificador=tx.identificador(f), motivo=motivo)
    estado = tx.traducir_estado(f["estado_crudo"])  # clasificar ya garantizó que no es None
    fecha_asignacion, fecha_completado, aviso_fecha = derivar_fechas(f["anio"], f["mes"], estado)
    avisos = [aviso_fecha] if aviso_fecha else []
    empleado_id, motivo_match = indice.resolver(f["colaborador"])
    nombre_libre = None
    if empleado_id is None:
        # Decisión 4: lo que no matchea entra igual, con nombre_libre, y SALE EN EL REPORTE.
        nombre_libre = f["colaborador"]
        avisos.append(f"no matchea el padrón ({motivo_match}): entra como nombre suelto")
    return FilaFormacionPreview(
        fila=n, titulo=f["titulo"], colaborador=f["colaborador"],
        empleado_id=empleado_id,
        empleado_nombre=indice.nombre_visible(empleado_id) if empleado_id else None,
        nombre_libre=nombre_libre, estado=estado,
        fecha_asignacion=fecha_asignacion, fecha_completado=fecha_completado,
        proyecto=f["proyecto"], anio=f["anio"] or None, mes=f["mes"] or None,
        tipo=f["tipo"], entidad_capacitadora=f["entidad"], modalidad=f["modalidad"],
        duracion_horas=f["duracion"], avisos=avisos,
    ), None


def _capacitaciones_a_crear(validas: List[FilaFormacionPreview],
                            existentes: set) -> List[CapacitacionACrear]:
    """Los títulos que no están en el catálogo, con los atributos que el lote les da.

    Decisión 6: por atributo gana LA PRIMERA fila que lo trae; una posterior con duración
    DISTINTA no pisa nada y se reporta — nunca en silencio, porque la duración alimenta las
    horas totales del reporte de formación y dos filas en desacuerdo son un dato que RRHH
    tiene que ver antes de confirmar.
    """
    por_nombre: Dict[str, CapacitacionACrear] = {}
    for v in validas:
        if v.titulo in existentes:
            continue
        actual = por_nombre.get(v.titulo)
        if actual is None:
            por_nombre[v.titulo] = CapacitacionACrear(
                nombre=v.titulo, tipo=v.tipo, entidad_capacitadora=v.entidad_capacitadora,
                modalidad=v.modalidad, duracion_horas=v.duracion_horas)
            continue
        for campo in ("tipo", "entidad_capacitadora", "modalidad"):
            if getattr(actual, campo) is None and getattr(v, campo) is not None:
                setattr(actual, campo, getattr(v, campo))
        if actual.duracion_horas is None:
            actual.duracion_horas = v.duracion_horas
        elif v.duracion_horas is not None and v.duracion_horas != actual.duracion_horas:
            actual.avisos.append(
                f"la fila {v.fila} trae duración {v.duracion_horas:g} h; gana la primera "
                f"({actual.duracion_horas:g} h)")
    return list(por_nombre.values())


def preview(data: bytes, empresa_id: UUID) -> ImportacionFormacionPreviewResponse:
    """Lee el Excel y clasifica cada fila contra el padrón y el catálogo de la empresa.

    Raises:
        AppError: EXCEL_ILEGIBLE (422) si el archivo no se puede abrir.
        AppError: COLUMNAS_FALTANTES (422) si falta una requerida — rechaza el archivo ENTERO.
    """
    try:
        headers, crudas = abrir(data)
    except ValueError as exc:
        raise AppError(str(exc), "EXCEL_ILEGIBLE", 422) from exc

    faltan = tx.faltantes(headers)
    if faltan:
        raise AppError(f"Faltan columnas obligatorias en el archivo: {', '.join(faltan)}.",
                       "COLUMNAS_FALTANTES", 422)

    indice = IndiceEmpleados(AsignacionRepo().empleados_por_empresa(str(empresa_id)))
    # `solo_activos=False`: una formación desactivada del catálogo sigue siendo ESA formación —
    # crear una segunda con el mismo nombre porque la primera está inactiva duplicaría el título.
    existentes = {c.nombre.strip() for c in CapacitacionRepo().find_all(empresa_id, solo_activos=False)}

    validas: List[FilaFormacionPreview] = []
    errores: List[FilaFormacionError] = []
    for n, fila in filas(headers, crudas):
        ok, err = _evaluar_fila(n, fila, indice)
        if ok:
            validas.append(ok)
        else:
            errores.append(err)  # type: ignore[arg-type]

    resueltos = {v.colaborador: (str(v.empleado_id) if v.empleado_id else None) for v in validas}
    pares = [ParParecido(nombre_a=a, nombre_b=b, motivo=m)
             for a, b, m in pares_parecidos(list(resueltos), resueltos)]
    nombres = hojas(data)
    return ImportacionFormacionPreviewResponse(
        filas_validas=validas, errores=errores,
        capacitaciones_a_crear=_capacitaciones_a_crear(validas, existentes),
        sin_match=sorted({v.nombre_libre for v in validas if v.nombre_libre}),
        pares_parecidos=pares,
        hoja_leida=nombres[0] if nombres else None, total_hojas=len(nombres) or 1)

"""
PREVIEW del import de objetivos: lee el Excel, resuelve responsables y clasifica cada fila.

Vive aparte del `confirmar` por la MISMA razón que en el Flujo 2 de nómina, donde el preview es
`nomina_csv_service.parse_nomina_csv` y la confirmación `nomina_import_service.confirmar`: son
las dos mitades de un flujo, se tocan en momentos distintos y juntas no entran en un service
(este quedaba en 191 contra un límite de 150).

🔴 EL RESPONSABLE SE RESUELVE CONTRA `users`, NO CONTRA `empleados`. Este es el tablero de tareas
del equipo de RRHH, no de los 31 empleados — decisión de producto cerrada, y la razón por la que
la migración de `responsable_id` a empleados se canceló. Una fila cuyo responsable no existe o
está inactivo **no se carga y se reporta**: nunca se carga con un responsable nulo.

⚠️ Acá NO se persiste nada y NO se autoriza nada: el preview resuelve para MOSTRAR. La
revalidación la hace el confirmar, porque el body viaja por la red y el cliente lo puede
alterar. Mismo criterio que el `es_actualizacion` de costos.
"""
from typing import List, Optional, Tuple

from repositories.usuario_repo import UsuarioRepo
from schemas.importacion_objetivos import (
    FilaObjetivoError, FilaObjetivoPreview, ImportacionObjetivosPreviewResponse,
)
from services import _objetivos_import_transforms as tx
from services._import_excel import abrir, faltantes, filas, hojas
from services._objetivos_import_valores import parse_fecha
from utils.errors import AppError


def usuarios_activos() -> dict:
    """Índice de usuarios ACTIVOS por email, username y "nombre apellido", todo casefold.

    Las tres claves porque el archivo lo escribe una persona y no hay forma de saber cuál va a
    usar. Una sola consulta: resolver usuario por usuario serían N consultas para una tabla de
    4 filas.
    """
    # `listar_activos` ya existía para el listado y su export. Trae `rol` de más —que acá se
    # ignora— y viene ordenado por apellido, orden que este índice no usa: la clave es el
    # email/username/nombre casefold, no la posición.
    filas_users = UsuarioRepo().listar_activos()
    idx: dict = {}
    for u in filas_users:
        entrada = {"id": u["id"], "nombre": f"{u['nombre']} {u['apellido']}"}
        for clave in (u.get("email"), u.get("username"), entrada["nombre"]):
            if clave:
                idx[str(clave).casefold()] = entrada
    return idx


def _resolver_acompanantes(valores: List[str], usuarios: dict, dueno_id: str
                           ) -> Tuple[List[str], Optional[str]]:
    """Resuelve los acompañantes; devuelve `(ids, primer_desconocido)`.

    Se corta en el PRIMERO que no resuelve en vez de acumular: el reporte muestra un motivo por
    fila, y "no existe ana@x.com" es accionable mientras que una lista de tres nombres en una
    sola línea no se lee. El usuario corrige y vuelve a subir.
    """
    ids: List[str] = []
    for v in valores:
        u = usuarios.get(v.casefold())
        if not u:
            return [], v
        if u["id"] != dueno_id:      # el dueño entra por su propio camino, no se duplica
            ids.append(u["id"])
    return ids, None


def evaluar_fila(n: int, fila: dict, usuarios: dict
                 ) -> Tuple[Optional[FilaObjetivoPreview], Optional[FilaObjetivoError]]:
    """Una fila → válida o error. Nunca las dos, nunca ninguna."""
    f = tx.parsear_fila(fila)
    ident = tx.identificador(fila)
    if not f["titulo"]:
        return None, FilaObjetivoError(fila=n, identificador=ident,
                                       motivo="Falta el título, que es obligatorio.")
    dueno = usuarios.get(f["responsable"].casefold())
    if not dueno:
        return None, FilaObjetivoError(
            fila=n, identificador=ident,
            motivo=f"El responsable «{f['responsable']}» no existe o no está activo.")
    acompanantes, desconocido = _resolver_acompanantes(f["responsables"], usuarios, dueno["id"])
    if desconocido:
        return None, FilaObjetivoError(
            fila=n, identificador=ident,
            motivo=f"El responsable «{desconocido}» no existe o no está activo.")
    fecha = parse_fecha(f["fecha_entrega"])
    # Los tres de la migración 119 viajan al preview YA NORMALIZADOS por `parsear_fila` (el tipo
    # caído al default si venía mal, las áreas partidas). El preview los muestra y el confirmar
    # los persiste: no se vuelven a tocar en el medio.
    return FilaObjetivoPreview(
        fila=n, titulo=f["titulo"], responsable=f["responsable"], responsable_id=dueno["id"],
        responsable_nombre=dueno["nombre"], prioridad=f["prioridad"], fecha_entrega=fecha,
        descripcion=f["descripcion"], responsables_ids=acompanantes,
        tipo=f["tipo"], periodicidad=f["periodicidad"], areas_involucradas=f["areas"],
        faltantes=[] if fecha or not f["fecha_entrega"] else ["fecha"],
    ), None


def preview(data: bytes) -> ImportacionObjetivosPreviewResponse:
    """Lee el Excel y clasifica cada fila. NO persiste nada.

    Raises:
        AppError: EXCEL_ILEGIBLE (422) si el archivo no se puede abrir.
        AppError: COLUMNAS_FALTANTES (422) si falta una requerida — rechaza el archivo ENTERO,
            sin procesar una sola fila.
        AppError: JERARQUIA_NO_SOPORTADA (422) si trae columna de objetivo padre.
    """
    try:
        headers, crudas = abrir(data)
    except ValueError as exc:
        raise AppError(str(exc), "EXCEL_ILEGIBLE", 422) from exc

    faltan = faltantes(headers, tx.REQUERIDAS)
    if faltan:
        raise AppError(
            f"Faltan columnas obligatorias en el archivo: {', '.join(faltan)}.",
            "COLUMNAS_FALTANTES", 422)
    if tx.trae_columna_de_jerarquia(headers):
        raise AppError(tx.MENSAJE_JERARQUIA, "JERARQUIA_NO_SOPORTADA", 422)

    usuarios = usuarios_activos()
    validas: List[FilaObjetivoPreview] = []
    errores: List[FilaObjetivoError] = []
    for n, fila in filas(headers, crudas):
        ok, err = evaluar_fila(n, fila, usuarios)
        if ok:
            validas.append(ok)
        else:
            errores.append(err)  # type: ignore[arg-type]

    nombres = hojas(data)
    return ImportacionObjetivosPreviewResponse(
        filas_validas=validas, errores=errores,
        hoja_leida=nombres[0] if nombres else None, total_hojas=len(nombres) or 1)

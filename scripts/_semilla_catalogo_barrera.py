"""
LOS NOMBRES de la fase `barrera` y las tres búsquedas que comparte. Hermano de
`_semilla_catalogo.py`, y por el mismo motivo: **quién los lee no es sólo quien los siembra**.

🔴 LOS NOMBRES SON LA CLAVE NATURAL, ASÍ QUE VIVEN DONDE LOS PUEDEN LEER LOS DOS LADOS.
`_semilla_fases_barrera.py` los usa para crear y `_semilla_plan_barrera.py` para reconocer qué
borrar; si el sembrador fuera el dueño del literal, el limpiador importaría del sembrador —una
dependencia al revés, porque el borrado tiene que poder correr aunque la siembra cambie. El
prefijo `SMK ·` no es decorativo: es lo único que separa estas filas de las de RRHH cuando el
manifiesto se perdió.

⚠️ CAMBIAR UN NOMBRE ACÁ HUÉRFANA LAS FILAS YA SEMBRADAS. Sobreviven por el manifiesto, pero la
segunda capa —la clave natural— deja de encontrarlas. Si hay que renombrar, limpiar primero.
"""
from typing import Optional

AREA = "SMK · Área de barrera"
PROYECTO = "SMK · Proyecto de barrera"
TEMPLATE = "SMK · Template de barrera"
TAREA = "SMK · Tarea de barrera"
ITEM = "SMK · Notebook de barrera"
TIPO_AUSENCIA = "SMK · Licencia de barrera"
PLANTILLA_CLAVE = "SMK · Plantilla de barrera"
EMPRESA_CESION = "SMK · Empresa cedida"
ROL_PROYECTO = "SMK · Rol de barrera"

# 🔴 EN 2019 A PROPÓSITO. `periodos_cerrados` BLOQUEA las escrituras de licencias que se solapen
# con su rango, así que un período sembrado sobre el año en curso rompería la fase de vacaciones
# y ausencias de esta misma semilla — y el síntoma sería un 422 en una fase que nadie tocó.
# Además es la clave natural del período, que es el único recurso de la fase sin nombre propio:
# un período es un rango de fechas y nada más.
PERIODO = ("2019-01-01", "2019-01-31")


def clave(nombre: str, empresa: str) -> str:
    """La clave del manifiesto lleva la empresa: el MISMO nombre se siembra dos veces, una por
    sociedad, y sin esto la segunda corrida adoptaría la fila de la primera para las dos."""
    return f"{nombre}@{empresa}"


def titular(cli, empresa: str) -> Optional[dict]:
    """Un colaborador SEMBRADO y ACTIVO de esta empresa: el dueño de la cesión, la asignación al
    proyecto, la asignación de inventario y el onboarding.

    Activo y no cualquiera: un preingreso todavía no entró y una baja ya salió, y los cuatro
    endpoints que lo reciben tienen guardas de estado. Se filtra por el dominio de la semilla —la
    misma marca de agua que usa la limpieza— para no colgarle nada a un legajo real.
    """
    from _semilla_padron import DOMINIO

    pagina = cli.get("/api/empleados", params={"page_size": 100, "estado": "activo"},
                     empresa=empresa) or {}
    for e in pagina.get("items", []):
        if DOMINIO in (e.get("email_corporativo") or ""):
            return e
    return None


def buscar(cli, ruta: str, campo: str, valor: str, empresa: Optional[str] = None,
           params: Optional[dict] = None) -> Optional[str]:
    """La clave natural: busca la fila por su nombre en el listado real del sistema.

    🔴 EL LISTADO DE ÁREAS ES EL ÚNICO QUE NO SE ACOTA CON EL HEADER, y por eso el llamador le
    pasa `{"empresa_id": ...}` explícito. `GET /api/areas` devuelve las 13 áreas de las dos
    sociedades y el corte lo hace ese Query; escribir `empresa` —el nombre que usa
    `docs/MATRIZ-FILTROS.md`— no da error, porque FastAPI descarta el parámetro desconocido, y
    entonces esta función encuentra el área de la OTRA empresa y la adopta. Pasó en la primera
    corrida (23/8/2026): quedó UNA área para las dos, que es justo el estado en el que la barrera
    no se puede probar.
    """
    datos = cli.get(ruta, params={"page_size": 100, **(params or {})}, empresa=empresa) or {}
    for fila in (datos.get("items", datos) if isinstance(datos, dict) else datos):
        if isinstance(fila, dict) and fila.get(campo) == valor:
            return str(fila["id"])
    return None

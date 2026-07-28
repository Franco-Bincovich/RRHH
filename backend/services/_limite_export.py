"""
Tope de filas de los exports: si el pedido lo supera, se avisa en vez de entregar un archivo
cortado.

EL PROBLEMA QUE CIERRA. Antes cada export pedía `page_size=100000` (o directamente todo, sin
tope) y armaba el archivo con lo que entrara. Un pedido más grande salía **incompleto y sin
ninguna señal**: el usuario recibía un Excel que parecía correcto y no lo era. Es la misma
familia de bug que el resto del bloque B — un resultado plausible pero falso.

🔴 POR QUÉ 5.000 Y NO 100.000. Porque el techo real de un export NO es la cantidad de filas,
es el TIEMPO, y el 100.000 nunca se alcanzaba:
  · 30 s — timeout httpx del cliente de Supabase (settings.supabase_timeout). Es el más bajo
    de los techos del backend y el que corta primero.
  · posiblemente 8 s — statement_timeout del rol `authenticator` con el que PostgREST se
    conecta (`service_role` no tiene override propio, así que hereda de la sesión).
  · 120 s — statement_timeout de la instancia. Nunca llega a regir, los de arriba pegan antes.
  · el límite de Vercel, que además puede no ser el declarado (ver la bitácora).
5.000 filas es 250× el padrón actual (19 empleados) y queda cómodo debajo de todos ellos. Un
número alto "por las dudas" reproduciría el mismo bug con otra cara: en vez de un archivo
truncado, un timeout sin mensaje.

CONSTANTE DE MÓDULO, NO variable de entorno: no es algo que se deba poder subir sin pensar.
Subirlo exige revisar los techos de tiempo de arriba, y eso es una decisión, no configuración.

⚠️ ALCANCE REAL DE LA PROTECCIÓN, para no venderla de más. En los exports paginados
(empleados, vacaciones, ausencias, auditoría) el total llega por `count="exact"` y solo se
traen las filas del tope: ahí el control actúa ANTES de cargar nada grande. En los cinco que
no paginan (capacitaciones, inventario ítems, inventario asignaciones, objetivos,
ev_instancias) el repo no expone un conteo y sus archivos están en o sobre su límite de
líneas, así que el chequeo corre sobre la lista ya traída — **igual que hoy**: no hay
regresión, pero un volumen que muera por timeout muere antes de llegar acá. Cerrarlo del todo
pide un `contar()` por repo, y eso es una tanda propia.
"""
from utils.errors import AppError

LIMITE_FILAS_EXPORT = 5000

_CODE = "EXPORT_DEMASIADAS_FILAS"


def verificar_limite_export(total: int) -> None:
    """Corta el export si `total` supera el tope. Dentro del tope no hace nada.

    El mensaje es para alguien de RRHH, no para un desarrollador: dice cuántas filas dio la
    consulta, cuál es el máximo, y qué hacer. NO nombra un filtro concreto ("acotá por
    fechas") porque no todos los módulos tienen los mismos: empleados, por ejemplo, no filtra
    por fecha, y sugerirlo sería un consejo imposible de seguir.

    Args:
        total: Filas que devolvería el export con los filtros aplicados.

    Raises:
        AppError: EXPORT_DEMASIADAS_FILAS (422) si `total` supera LIMITE_FILAS_EXPORT.
    """
    if total <= LIMITE_FILAS_EXPORT:
        return
    raise AppError(
        f"La consulta devuelve {_miles(total)} filas y el máximo por archivo es "
        f"{_miles(LIMITE_FILAS_EXPORT)}. Usá los filtros de la pantalla para acotar el "
        "resultado y volvé a exportar.",
        _CODE,
        422,
    )


def _miles(n: int) -> str:
    """5000 → '5.000'. Separador de miles con punto, como se lee en Argentina."""
    return f"{n:,}".replace(",", ".")

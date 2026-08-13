"""
Tope de filas de los exports: si el pedido lo supera, se avisa en vez de entregar un archivo
cortado.

EL PROBLEMA QUE CIERRA. Antes cada export pedía `page_size=100000` (o directamente todo, sin
tope) y armaba el archivo con lo que entrara. Un pedido más grande salía **incompleto y sin
ninguna señal**: el usuario recibía un Excel que parecía correcto y no lo era. Es la misma
familia de bug que el resto del bloque B — un resultado plausible pero falso.

🔴 EL TECHO REAL DE UN EXPORT NO ES LA CANTIDAD DE FILAS, ES EL TIEMPO. Eso sigue siendo
cierto y es la razón de que exista esta constante. Lo que cambió el 13/8/2026 es CUÁL de los
techos de tiempo es el que corta, porque se midió en vez de suponerse.

⚠️ CORRECCIÓN DE LO QUE ESTE MISMO ARCHIVO AFIRMABA. Decía que el techo más bajo era el
**timeout httpx de 30 s** del cliente de Supabase. **No es cierto en este camino, y por
bastante.** Medido sobre 27.597 filas de auditoría (base local de escala, 10 empresas):
  · traer las filas de la base ........  4,2 s   ← el fetch, o sea lo que ese timeout cubre
  · export completo en CSV ............  4,1 s   ← construir el CSV es gratis
  · export completo en Excel .......... 39-53 s  ← openpyxl: ~35-49 s de CPU en Python
  · export completo en PDF ............  126 s   ← ~122 s de CPU en Python
O sea: **la base aporta el 8% del tiempo y el 92% es construir el archivo.** El timeout httpx
nunca llega a dispararse. El techo que de verdad rige es **el de la función de Vercel: 300 s**
(ver `settings.import_presupuesto_segundos`, donde está verificado contra la doc de la
plataforma), y el de la paciencia de quien aprieta el botón, que es más bajo todavía.

🔴 DE DÓNDE SALE EL 20.000. De la tasa REAL de eventos, no de un número redondo:
  · Producción, medida el 13/8/2026: 156 eventos de auditoría en 29 días con 31 empleados.
    = 5,38 eventos/día = **0,174 eventos por empleado por día**.
  · Proyectado a 1.005 colaboradores: ~175 eventos/día → **~16.000 por trimestre**.
  · 20.000 cubre el trimestre con margen, y a ese volumen el export tarda ~3 s en CSV,
    ~28-38 s en Excel y ~91 s en PDF: por debajo de los 300 s de Vercel en los tres formatos.
  · El 5.000 anterior ya no alcanzaba ni para UN MES a esa escala (5.250 proyectados). Ese es
    el bug que esto cierra: el módulo del que RRHH exporta el histórico era el único que a
    escala no se podía exportar nunca.

🔴 LO QUE 20.000 **NO** CUBRE, Y HAY QUE DECIRLO: EL AÑO ENTERO. Son ~64.000 eventos
proyectados, que en Excel darían ~2 minutos y en PDF pasarían los 300 s de Vercel. **Un export
anual de auditoría no se arregla subiendo este número**: pide otra cosa (export asíncrono con
link de descarga, o paginado por trimestre desde la UI). Mientras tanto, RRHH exporta por
trimestre — cuatro archivos por año.

⚠️ Y OJO CON EL FORMATO, que pesa más que las filas: entre CSV y PDF hay **31×** de
diferencia sobre el MISMO conjunto de filas. Este límite es uno solo para los tres, así que
está calibrado para que el más lento entre; si el export en PDF de listados largos se vuelve
un caso de uso real, el límite tiene que pasar a depender del formato. Hoy no lo hace a
propósito: un límite por formato es una decisión de producto, no un ajuste.

CONSTANTE DE MÓDULO, NO variable de entorno: no es algo que se deba poder subir sin pensar.
Subirlo exige revisar los techos de tiempo de arriba, y eso es una decisión, no configuración.

⚠️ ALCANCE REAL DE LA PROTECCIÓN, para no venderla de más. En los exports paginados
(empleados, vacaciones, ausencias, auditoría) el total llega por `count="exact"` y solo se
traen las filas del tope: ahí el control actúa ANTES de cargar nada grande. En los cuatro que
no paginan (capacitaciones, inventario ítems, inventario asignaciones, objetivos) el repo no
expone un conteo y sus archivos están en o sobre su límite de líneas, así que el chequeo corre
sobre la lista ya traída — **igual que hoy**: no hay
regresión, pero un volumen que muera por timeout muere antes de llegar acá. Cerrarlo del todo
pide un `contar()` por repo, y eso es una tanda propia.
"""
from utils.errors import AppError

LIMITE_FILAS_EXPORT = 20000

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

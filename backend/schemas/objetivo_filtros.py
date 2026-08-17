"""
Los filtros de LECTURA del módulo de objetivos, en un objeto único.

Salió de `schemas/objetivo.py`, que con este bloque quedaba en 207 contra un tope de 200. El
corte no es sólo por líneas: separa los filtros de LECTURA de los DTO del RECURSO
(`ObjetivoCreate` / `ObjetivoUpdate` / `ObjetivoResponse`), que son dos caminos distintos —éste
lo consumen el router de lecturas, el service y el repo; aquéllos, las escrituras y la respuesta.
Simetría deliberada con `repositories/_objetivo_filtros.py`, que es quien los APLICA sobre la
query: el objeto acá, el predicado allá, y el mismo nombre para que se encuentren.

La dependencia va en UNA sola dirección —este archivo importa `TipoObjetivo` de `objetivo.py` y
`objetivo.py` no importa nada de acá—, así que no hay ciclo posible.
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict

from schemas.objetivo import TipoObjetivo


class ObjetivosFiltros(BaseModel):
    """Los filtros del LISTADO y del EXPORT, en un objeto único que viaja entero.

    🔴 POR QUÉ UN OBJETO Y NO TRES PARÁMETROS MÁS. `find_all` tenía CUATRO posicionales
    (`empresa_id, estado, responsable_id, prioridad`) y con los tres nuevos pasaba a SIETE, todos
    `Optional[str]`. Siete strings opcionales en fila es la trampa que el bloque B ya pagó en
    vacaciones y ausencias: un argumento corrido entre hermanas **no da error, da el conjunto
    equivocado**, y el test que lo cubría lo verificaba con un espía posicional, o sea que pasaba
    en verde. Acá el filtro se nombra o no existe.

    LAS TRES COSAS QUE HACEN IMPOSIBLE EL ARGUMENTO CORRIDO, en orden de fuerza:

      1. **No hay construcción posicional.** Un `BaseModel` de Pydantic sólo acepta keywords:
         `ObjetivosFiltros("anual")` es un `TypeError`, no un filtro mal puesto. Toda la cadena
         —router → service → repo → `aplicar_filtros`— pasa este objeto entero, así que el
         corrimiento no tiene dónde ocurrir: ya no quedan posicionales que correr.
      2. **`extra="forbid"`.** Un nombre de campo mal escrito (`tipoo=`, `area_id=`) **revienta al
         construir** en vez de perderse en silencio. Sin esto, un filtro con el nombre cambiado se
         evapora y el listado devuelve de más — que es exactamente cómo se ve el bug que este
         objeto viene a impedir.
      3. **`tipo` es un `Literal`, no un `str`.** Es el único de los seis con vocabulario cerrado,
         así que es el único cuyo VALOR puede desmentir un cruce: pasarle un estado
         (`tipo="por_hacer"`) es un `ValidationError`, no una consulta que devuelve cero.

    ⚠️ **Y LO QUE ESTO *NO* RESUELVE, dicho de frente:** `periodicidad` y `area` son los dos texto
    libre, así que intercambiarlos ENTRE SÍ sigue siendo construible
    —`ObjetivosFiltros(area="mensual")` es un filtro válido por un área que se llama "mensual"—.
    Ningún tipo puede distinguir dos textos libres. Lo que sí desaparece es el corrimiento
    SILENCIOSO por posición: para equivocarse ahora hay que escribir mal el NOMBRE del filtro, que
    se ve en el diff y se encuentra con un grep.

    🔴 `empresa_id` NO ESTÁ ACÁ, A PROPÓSITO. No es un filtro del usuario: es la barrera
    multiempresa, sale del header y se aplica en el WHERE (Forma A del patrón de barrera). Dejarlo
    afuera y explícito en cada firma hace que **no se pueda perder pasando un objeto vacío**, y
    mantiene la forma que tienen todos los repos del sistema. Meterlo adentro ahorraría un
    parámetro a cambio de que la barrera viaje mezclada con los filtros de pantalla.

    `frozen=True`: una vez construido no se toca. El service no puede reescribir un filtro que le
    llegó del router, así que lo que se ve en la URL es lo que llega a la query.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    estado:         Optional[str] = None
    responsable_id: Optional[str] = None
    prioridad:      Optional[str] = None
    tipo:           Optional[TipoObjetivo] = None
    periodicidad:   Optional[str] = None
    # SINGULAR: se filtra por UN área y la query pregunta si el array la CONTIENE. Ver
    # `_objetivo_filtros.aplicar_filtros` — el nombre en singular es lo que hace legible que
    # `?area=Sistemas` traiga los objetivos cuyas `areas_involucradas` incluyen "Sistemas".
    area:           Optional[str] = None


# El objeto vacío: ningún filtro puesto. Se usa como default para no construir uno nuevo en cada
# llamada sin filtros — es `frozen`, así que compartirlo no puede tener efectos cruzados.
SIN_FILTROS = ObjetivosFiltros()

"""
Doble de `supabase_admin` para ejercitar los mappers de fila de `repositories/` CON FILAS.

Helper, no test. Lo comparten `test_objetivo_row`, `test_proyectos_enrich` y
`test_ev_row_mappers`, que hasta el 9/8/2026 no existían: los cinco mappers que usan este doble
se llamaban SIEMPRE con listas vacías, y como todos abren con `if not rows: return []`, su cuerpo
nunca se ejecutó. Ver el encabezado de `test_mappers_ejercitados.py`.

## 🔴 DEVUELVE DATOS, Y FILTRA POR LA COLUMNA QUE SE LE PIDIÓ

Las dos cosas importan para que los tests puedan desmentir algo:

  · **Devuelve filas de verdad.** Un doble que respondiera `[]` a todo dejaría todos los nombres
    resueltos en `None`, y las aserciones no distinguirían "el mapper resolvió el nombre" de "el
    mapper no hizo nada". Es la mitad del molde de `test_ausencia_row`.
  · **Honra la columna del `in_`.** `_objetivo_row` consulta la puente por `objetivo_id`, no por
    `id`. Un doble que filtrara siempre por `id` devolvería vacío ahí y el fallback al dueño
    parecería correcto por el motivo equivocado.

Registra cada consulta en `consultas` como `(tabla, columna, ids)` para poder afirmar que los
lookups son BATCH —una query por dimensión— y no uno por fila, que es la invariante que los
cuatro módulos declaran en su docstring.

## 🔴 `.order()` SE REGISTRA PERO NO ORDENA, A PROPÓSITO

Un doble que ordenara dejaría pasar un repo que se olvidó del `.order(...)`: el test vería las
filas ordenadas igual y no podría desmentir nada. Es el caso #3 de la regla del repo ("el fake
ordena en Python" → sacarle el `.order(..., desc=True)` real dejaba todo en verde). Acá el orden
se afirma sobre `ordenes`, o sea sobre lo que VIAJA EN LA QUERY. Molde:
`test_historial_salarial::TestElOrdenLoPoneLaQuery`.

## 🔴 `.contains()` SÍ FILTRA DE VERDAD, Y POR ELEMENTO — al revés que `.order()` y `.range()`

La asimetría con los dos de abajo es deliberada y sale de la misma pregunta: *¿qué tendría que
ser distinto en el fake para que el test pueda fallar?*

  · Con `.order()` y `.range()`, lo que se quiere probar es que el predicado VIAJE en la query.
    Un doble que los ejecutara taparía al repo que se los olvidó, así que se registran y no se
    aplican.
  · Con `.contains()` lo que se quiere probar es **cuál es la semántica de la comparación**: que
    "Sistemas" encuentre `{Sistemas, Legales}` y **NO** encuentre `{Sistemas Corporativos}`. Un
    doble que sólo registrara la llamada no podría desmentir nada — un repo que cambiara el `@>`
    por un `ILIKE '%Sistemas%'` seguiría "llamando al filtro" y el test seguiría en verde,
    mientras en producción el prefijo matchea. Ese es EL bug por el que la migración 119 pasó
    `areas_involucradas` de `text` a `text[]`, así que el fake tiene que poder atraparlo.

Se registra igual en `contenciones`, para poder afirmar además QUÉ viajó.

🔑 El literal lo parsea `utils.postgrest_array.elementos_de`, **la contracara del mismo módulo que
lo escribe**. No se reimplementa el parseo acá a propósito: serían dos interpretaciones del mismo
formato, y el día que el encoder cambie el fake seguiría entendiendo el viejo y los tests del
filtro pasarían sin ejercitar nada. Hay un test de ida y vuelta que ata las dos puntas.

## 🔴 `.range()` TAMPOCO RECORTA, POR EL MISMO MOTIVO

Se registra en `rangos` y devuelve las filas enteras. Un doble que recortara dejaría pasar un
repo que se olvidó del `.range(...)`: el test vería la página del tamaño correcto sin que el
LIMIT haya viajado nunca, y en producción ese repo se traería la tabla completa por la red.

⚠️ CONSECUENCIA A TENER PRESENTE: acá `data` es el conjunto filtrado ENTERO, así que un repo
paginado devuelve `total == len(items)` contra este doble. Es correcto —el `count="exact"` de
PostgREST cuenta el filtro, no la página—, pero significa que **este doble no sirve para
verificar que el recorte funcione**. Para eso hace falta un fake que rebane, y esos viven en los
tests de paginación de cada módulo (`test_paginacion_mecanicos`, `test_paginacion_areas`).
"""
from typing import Dict, List, Optional, Tuple

from utils.postgrest_array import como_lo_manda_la_libreria, elementos_de


class _Query:
    def __init__(self, fake: "FakeSupabase", tabla: str) -> None:
        self._fake, self._tabla = fake, tabla
        self._columna: Optional[str] = None
        self._ids: Optional[list] = None
        self._contar = False
        # Aparte de `_columna`/`_ids` para que COMPONGA con ellos por AND, como PostgREST. Si
        # compartiera esos dos, un `.eq(empresa).contains(areas)` se pisaría a sí mismo y el
        # test de "empresa + área juntos" mediría un solo filtro creyendo que mide dos.
        self._contiene: Optional[Tuple[str, List[str]]] = None

    def select(self, *a, **k) -> "_Query":
        self._contar = k.get("count") == "exact"
        return self

    def in_(self, columna: str, ids) -> "_Query":
        self._columna, self._ids = columna, list(ids)
        return self

    def eq(self, columna: str, valor) -> "_Query":
        self._columna, self._ids = columna, [valor]
        return self

    def contains(self, columna: str, valores) -> "_Query":
        """Contención de array (`@>`): filtra DE VERDAD y por elemento. Ver el encabezado.

        Acepta las dos formas que acepta la librería: el literal de PostgREST
        (`'{"Sistemas"}'`, que es lo que manda el repo) o una lista.

        🔴 UNA LISTA SE CONVIERTE PRIMERO CON `como_lo_manda_la_libreria`, o sea con el
        `",".join` SIN comillar de `postgrest`, y recién después se parsea. **Es lo que hace que
        este doble no sea más indulgente que PostgREST.** Si la lista se usara tal cual, un repo
        que mandara `["Legales, Compliance"]` —la forma rota— encontraría su fila acá y fallaría
        sólo en producción, partido en dos elementos. Modelar esa pérdida es la única razón por
        la que el fake puede desmentir esa mutación.
        """
        crudo = valores if isinstance(valores, str) else como_lo_manda_la_libreria(valores)
        self._contiene = (columna, elementos_de(crudo))
        return self

    def order(self, columna: str, **k) -> "_Query":
        """Registra el orden pedido y NO ordena. Ver el encabezado del módulo."""
        self._fake.ordenes.append((self._tabla, columna, bool(k.get("desc", False))))
        return self

    def range(self, desde: int, hasta: int) -> "_Query":
        """Registra el recorte pedido y NO recorta. Ver el encabezado del módulo."""
        self._fake.rangos.append((self._tabla, desde, hasta))
        return self

    def execute(self):
        filas = self._fake.catalogo.get(self._tabla, [])
        if self._ids is not None:
            self._fake.consultas.append((self._tabla, self._columna, list(self._ids)))
            filas = [f for f in filas if f.get(self._columna) in self._ids]
        else:
            self._fake.consultas.append((self._tabla, None, []))
        if self._contiene is not None:
            col, requeridos = self._contiene
            self._fake.contenciones.append((self._tabla, col, list(requeridos)))
            # 🔴 `set(requeridos) <= set(...)` es CONTENCIÓN POR ELEMENTO, que es lo que hace `@>`
            # en Postgres — y es lo único que puede desmentir un ILIKE: "Sistemas" no está
            # incluido en {"Sistemas Corporativos"} porque son dos strings distintos, aunque uno
            # sea prefijo del otro. Con varios elementos pide TODOS (AND), igual que `@>`.
            # `or []` porque la columna es NOT NULL DEFAULT '{}' pero una fila de test puede
            # omitirla: sin áreas no contiene nada, que es la respuesta correcta.
            filas = [f for f in filas if set(requeridos) <= set(f.get(col) or [])]
        # `count` sale sólo si el repo pidió `count="exact"`, y vale el largo del conjunto
        # FILTRADO. Devolverlo siempre taparía a un repo que se olvidó de pedirlo: leería
        # `res.count` y encontraría un número, cuando PostgREST le habría devuelto None.
        return type("Respuesta", (), {"data": list(filas),
                                      "count": len(filas) if self._contar else None})()


class FakeSupabase:
    """`catalogo` es {tabla: [filas]}. `consultas` acumula (tabla, columna, ids) por llamada;
    `ordenes`, (tabla, columna, desc) de cada `.order()` pedido; `rangos`, (tabla, desde, hasta)
    de cada `.range()`; `contenciones`, (tabla, columna, elementos) de cada `.contains()`."""

    def __init__(self, catalogo: Dict[str, List[dict]]) -> None:
        self.catalogo = catalogo
        self.consultas: List[tuple] = []
        self.ordenes: List[tuple] = []
        self.rangos: List[tuple] = []
        self.contenciones: List[tuple] = []

    def table(self, tabla: str) -> _Query:
        return _Query(self, tabla)

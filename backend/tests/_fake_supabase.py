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
from typing import Dict, List, Optional


class _Query:
    def __init__(self, fake: "FakeSupabase", tabla: str) -> None:
        self._fake, self._tabla = fake, tabla
        self._columna: Optional[str] = None
        self._ids: Optional[list] = None
        self._contar = False

    def select(self, *a, **k) -> "_Query":
        self._contar = k.get("count") == "exact"
        return self

    def in_(self, columna: str, ids) -> "_Query":
        self._columna, self._ids = columna, list(ids)
        return self

    def eq(self, columna: str, valor) -> "_Query":
        self._columna, self._ids = columna, [valor]
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
        # `count` sale sólo si el repo pidió `count="exact"`, y vale el largo del conjunto
        # FILTRADO. Devolverlo siempre taparía a un repo que se olvidó de pedirlo: leería
        # `res.count` y encontraría un número, cuando PostgREST le habría devuelto None.
        return type("Respuesta", (), {"data": list(filas),
                                      "count": len(filas) if self._contar else None})()


class FakeSupabase:
    """`catalogo` es {tabla: [filas]}. `consultas` acumula (tabla, columna, ids) por llamada;
    `ordenes`, (tabla, columna, desc) de cada `.order()` pedido; `rangos`, (tabla, desde, hasta)
    de cada `.range()`."""

    def __init__(self, catalogo: Dict[str, List[dict]]) -> None:
        self.catalogo = catalogo
        self.consultas: List[tuple] = []
        self.ordenes: List[tuple] = []
        self.rangos: List[tuple] = []

    def table(self, tabla: str) -> _Query:
        return _Query(self, tabla)

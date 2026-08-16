"""
El contrato de `sin_paginar`: el listado que TODAVÍA no pagina, y el helper compartido.

🔄 ESTE ARCHIVO SE ACHICÓ EN LA SESIÓN 2 DE PAGINACIÓN (14/8/2026), Y ES LO ESPERADO. Cubría los
CINCO wrappers que devolvían todo con `sin_paginar`; cuatro de ellos —inventario/ítems,
inventario/asignaciones, capacitaciones/asignaciones y proyectos— ya paginan de verdad, así que
su contrato pasó a `tests/test_paginacion_mecanicos.py`, donde se lo prueba con páginas reales.
Acá queda **objetivos**, el único que sigue sin paginar, más el helper que los cinco comparten.

La RELACIÓN entre los cuatro números es la misma antes y después de la migración; lo que cambia
es de dónde sale `total`.

🔴 QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR

  · **La cantidad de items NO es 1.** Con un solo item, `total`, `page` y `total_pages` valen
    todos 1 y se vuelven indistinguibles entre sí: cualquier permutación del constructor daría
    verde. Con 6, `total` y `page_size` valen 6 y `page`/`total_pages` valen 1.

  · **`total_pages` NO se compara contra `cantidad_paginas(...)`**, que es la función que el
    service usa: eso sería preguntarle a la implementación si hace lo que hace. Se compara contra
    la DEFINICIÓN del techo, escrita como dos desigualdades
    (`(p-1) * page_size < total <= p * page_size`). Si alguien cambia el redondeo a `floor`, la
    igualdad contra la función seguiría pasando y estas desigualdades no.

  · **Los fakes de repo devuelven la lista que se les pide**, así que la longitud es un dato del
    test y no del código: un service que ignorara `items` y respondiera un total fijo rojea.

¿EL FAKE ES LO QUE ESTOY PROBANDO? No: lo falseado son los REPOS. El service, el wrapper Pydantic
y el helper `_paginacion` son los reales.
"""
from typing import List

import pytest

from schemas.inventario import ItemResponse
from schemas.objetivo import ObjetivoResponse
from services._paginacion import cantidad_paginas, sin_paginar


def _items(modelo, n: int) -> List:
    """`n` filas del tipo que el wrapper exige. El CONTENIDO no importa: se mide la CANTIDAD.

    `model_construct` arma la instancia sin correr validación: acá no se prueba el mapeo de una
    fila —eso tiene sus propios tests— y llenar 20 campos obligatorios por wrapper sólo agregaría
    ruido que se desactualiza con cada columna nueva. Lo que el wrapper sí exige es que sean
    instancias de la clase correcta, y eso `model_construct` lo cumple.
    """
    return [modelo.model_construct(id=str(i)) for i in range(n)]


class _RepoLista:
    """Repo genérico: devuelve la lista que se le dio, ignorando los filtros."""

    def __init__(self, items) -> None:
        self._items = items

    def find_all(self, *_a, **_k):
        return self._items


# (nombre, cantidad, constructor del ListResponse ya armado por el SERVICE real)
def _objetivos(n):
    from services.objetivo_service import ObjetivoService
    return ObjetivoService(repo=_RepoLista(_items(ObjetivoResponse, n))).get_all()


# Un solo caso: es el último listado que devuelve todo. Cuando objetivos pagine (queda con una
# vuelta propia: `items` son raíces con hijos anidados), este bloque se muda igual que los otros
# cuatro y lo que sobrevive de este archivo es el helper.
CASOS = [
    ("objetivos", 6, _objetivos),
]


@pytest.mark.parametrize("nombre,n,armar", CASOS, ids=[c[0] for c in CASOS])
class TestElContratoDeCadaWrapper:
    def test_total_es_la_cantidad_real_y_no_una_constante(self, nombre, n, armar) -> None:
        r = armar(n)
        assert r.total == n, f"{nombre}: total {r.total} no coincide con las {n} filas devueltas"

    def test_los_cuatro_campos_estan(self, nombre, n, armar) -> None:
        r = armar(n)
        assert (r.page, r.page_size, r.total_pages) == (1, n, 1)

    def test_total_pages_cumple_la_definicion_de_techo(self, nombre, n, armar) -> None:
        """La relación, sin preguntarle a la función que la calcula.

        `p` páginas de `page_size` tienen que ALCANZAR para `total` (`p * page_size >= total`) y
        `p - 1` tienen que quedarse cortas (`(p-1) * page_size < total`). Las dos juntas definen
        el techo; con `floor` la segunda falla.
        """
        r = armar(n)
        assert r.total_pages * r.page_size >= r.total
        assert (r.total_pages - 1) * r.page_size < r.total

    def test_items_y_total_coinciden_mientras_no_pagine(self, nombre, n, armar) -> None:
        """Hoy son lo mismo. El día que este test falle es porque el listado empezó a recortar —
        y ahí hay que revisar que `total` venga de `count="exact"` y no de `len(items)`."""
        r = armar(n)
        assert len(r.items) == r.total


class TestElListadoVacio:
    """El borde que rompe la división. Se prueba en los cuatro parametrizables."""

    @pytest.mark.parametrize("nombre,_n,armar", CASOS, ids=[c[0] for c in CASOS])
    def test_sin_filas_no_revienta_y_reporta_cero_paginas(self, nombre, _n, armar) -> None:
        r = armar(0)
        assert (r.total, r.page_size, r.total_pages) == (0, 0, 0)


class TestCantidadPaginas:
    """El helper, directo. Es la única definición de la división en todo el backend."""

    @pytest.mark.parametrize("total,page_size,esperado", [
        (0, 20, 0),      # vacío
        (1, 20, 1),      # una fila ocupa una página entera
        (20, 20, 1),     # exacto: NO son 2
        (21, 20, 2),     # una de más abre la siguiente
        (1042, 12, 87),  # el caso del pie "Mostrando 1–12 de 1.042"
        (5, 0, 0),       # page_size 0 → 0 y no ZeroDivisionError
    ])
    def test_casos(self, total, page_size, esperado) -> None:
        assert cantidad_paginas(total, page_size) == esperado

    def test_nunca_deja_filas_afuera(self) -> None:
        """Propiedad, no casos: las páginas siempre alcanzan para el total."""
        for total in range(0, 200):
            for page_size in (1, 7, 20, 50):
                p = cantidad_paginas(total, page_size)
                assert p * page_size >= total
                assert (p - 1) * page_size < total or total == 0


class TestSinPaginar:
    def test_describe_una_sola_pagina_con_todo(self) -> None:
        assert sin_paginar(_items(ItemResponse, 9)) == {"total": 9, "page": 1, "page_size": 9, "total_pages": 1}

    def test_con_la_lista_vacia_no_divide_por_cero(self) -> None:
        assert sin_paginar([]) == {"total": 0, "page": 1, "page_size": 0, "total_pages": 0}


class TestTodosLosWrappersDeclaranLosCuatroCampos:
    """Barrido: los cinco wrappers de los listados que van a paginar tienen los cuatro campos.

    🔑 Si alguno los pierde en un merge, el service sigue compilando —Pydantic ignora los kwargs
    de más sólo si el modelo lo permite, y si no revienta en runtime, no en import— así que el
    fallo aparecería recién al pegarle al endpoint.
    """

    WRAPPERS = [
        ("schemas.inventario", "ItemListResponse"),
        ("schemas.inventario", "AsignacionListResponse"),
        ("schemas.capacitacion", "AsignacionListResponse"),
        ("schemas.objetivo", "ObjetivoListResponse"),
        ("schemas.proyectos", "ProyectoListResponse"),
        # El que ya paginaba, como control: si el barrido se rompiera, este también fallaría.
        ("schemas.empleado_out", "EmpleadoListResponse"),
    ]

    @pytest.mark.parametrize("modulo,clase", WRAPPERS, ids=[f"{m.split('.')[-1]}.{c}" for m, c in WRAPPERS])
    def test_tiene_los_cuatro(self, modulo, clase) -> None:
        import importlib
        campos = importlib.import_module(modulo).__dict__[clase].model_fields
        faltan = {"items", "total", "page", "page_size", "total_pages"} - set(campos)
        assert not faltan, f"{modulo}.{clase} no declara {sorted(faltan)}"

    def test_el_barrido_no_esta_vacio(self) -> None:
        assert len(self.WRAPPERS) >= 6

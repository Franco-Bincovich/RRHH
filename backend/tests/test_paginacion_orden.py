"""
Orden TOTAL de los listados paginados: sin desempate, paginar puede repetir o perder filas.

🔴 QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR
(la pregunta obligatoria de la regla transversal del repo, contestada acá y no en la cabeza):

  1. **El fake tiene que ORDENAR DE VERDAD, no devolver una lista fija.** Un fake que devuelve
     `[a, b, c]` pase lo que pase deja el `.order()` sin efecto observable: se le puede sacar el
     desempate —o el orden entero— y el test sigue verde. Por eso `_FakeTabla.execute()` aplica
     las claves que capturó, en el orden en que se encadenaron, con sort estable.

  2. **Tiene que haber EMPATES.** Con 30 apellidos distintos, `(apellido, nombre)` ya es un orden
     total y el `.order("id")` no cambia nada: el test pasaría con y sin él. Por eso 10 de las 30
     filas comparten apellido Y nombre.

  3. **Y los empatados tienen que llegar en OTRO ORDEN en cada consulta**, que es exactamente la
     libertad que se toma Postgres: sin `ORDER BY` total, dos ejecuciones con OFFSET distinto no
     tienen por qué resolver los empates igual. Es el punto que hace que esto sea un test y no
     una tautología — `_FakeTabla` invierte la lista base en las llamadas pares.

  Con las tres cosas puestas, sacarle `.order("id")` a `empleado_repo` hace que la página 1 y la
  página 2 devuelvan las MISMAS cinco personas empatadas y que las otras cinco no aparezcan en
  ninguna. El test rojea con un mensaje que dice quién se repitió y quién falta.

⚠️ Se faltea el CLIENTE DE SUPABASE, un escalón por debajo del repo, no el repo. Es la regla del
repo para todo lo que tiene que viajar EN LA QUERY (molde: `TestElOrdenLoPoneLaQuery` en
test_historial_salarial.py). Un fake de repo que ordenara en Python probaría el contrato del
service, no que el orden esté en la consulta — y ordenar en Python exige haberse traído todas las
filas, que es justo lo que la paginación deja de hacer.
"""
from datetime import date, datetime
from types import SimpleNamespace
from typing import List

import pytest

EMPRESA = "11111111-1111-1111-1111-111111111111"

# 20 personas con apellido único + 10 que comparten apellido Y nombre. Las empatadas caen en las
# posiciones 5..14 del orden por (apellido, nombre), o sea CRUZANDO el corte de la página 1 con
# `page_size=10`. Si el bloque de empates cupiera entero en una página, el bug no se vería.
TOTAL = 30
PAGE_SIZE = 10
APELLIDO_EMPATADO = "Ape05"
NOMBRE_EMPATADO = "Empatada"


def _fila(idx: int, apellido: str, nombre: str) -> dict:
    return {
        "id": f"{idx:08d}-0000-0000-0000-000000000000",
        "nombre": nombre,
        "apellido": apellido,
        "area_id": "22222222-2222-2222-2222-222222222222",
        "empresa_id": EMPRESA,
        "roles": ["Analista"],
        "modalidad_trabajo": "presencial",
        "tipo_contrato": "permanente",
        "fecha_ingreso": date(2024, 1, 1),
        "estado": "activo",
        "created_at": datetime(2024, 1, 1, 12, 0, 0),
    }


def _padron() -> List[dict]:
    filas = [_fila(i, f"Ape{i:02d}", f"Nom{i:02d}") for i in range(20)]
    # `id` 100..109: distintos entre sí, así que el desempate SIEMPRE puede resolverlos.
    filas += [_fila(100 + i, APELLIDO_EMPATADO, NOMBRE_EMPATADO) for i in range(10)]
    return filas


class _FakeTabla:
    """Motor mínimo en memoria: filtra, ORDENA con las claves que le pidieron, y pagina."""

    def __init__(self, filas: List[dict], estado: dict) -> None:
        self._filas = list(filas)
        self._estado = estado
        self._ordenes: List[tuple] = []
        self._rango = None

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        self._filas = [r for r in self._filas if str(r.get(col)) == str(val)]
        return self

    def in_(self, col, vals):
        self._filas = [r for r in self._filas if str(r.get(col)) in {str(v) for v in vals}]
        return self

    def neq(self, col, val):
        # FILTRA DE VERDAD, como sus hermanos. Lo pide el default de estado del listado
        # (`.neq("estado","preingreso")` cuando no viene `estado`).
        self._filas = [r for r in self._filas if str(r.get(col)) != str(val)]
        return self

    def order(self, col, desc=False):
        self._ordenes.append((col, desc))
        return self

    def range(self, start, end):
        self._rango = (start, end)
        return self

    def execute(self):
        self._estado["llamadas"] += 1
        filas = list(self._filas)
        # 🔴 ACÁ ESTÁ LO QUE HACE FALSABLE AL TEST. Postgres no promete resolver los empates igual
        # en dos consultas distintas; el fake lo modela devolviendo la base al revés una de cada
        # dos veces. Sin esto, los empatados llegarían siempre en el mismo orden y un listado sin
        # desempate se vería perfectamente estable.
        if self._estado["llamadas"] % 2 == 0:
            filas.reverse()
        # Multi-clave con sort estable: se aplica de la última a la primera, como cualquier
        # ORDER BY de varias columnas.
        for col, desc in reversed(self._ordenes):
            filas = sorted(filas, key=lambda r: r[col], reverse=desc)
        total = len(filas)
        if self._rango is not None:
            start, end = self._rango
            filas = filas[start:end + 1]
        return SimpleNamespace(data=filas, count=total)


@pytest.fixture
def repo_paginado(monkeypatch):
    """EmpleadoRepo contra el motor en memoria. Devuelve (repo, estado)."""
    import repositories._empleado_row as row_mod
    import repositories.empleado_repo as mod

    estado = {"llamadas": 0}
    padron = _padron()

    class _Cliente:
        def table(self, _t):
            return _FakeTabla(padron, estado)

    monkeypatch.setattr(mod, "supabase_admin", _Cliente())
    monkeypatch.setattr(row_mod, "supabase_admin", _Cliente(), raising=False)
    return mod.EmpleadoRepo(), estado


class TestLasTresPaginasCubrenElPadronUnaVez:
    """El test que el desempate tiene que sostener."""

    def test_las_30_filas_aparecen_exactamente_una_vez(self, repo_paginado) -> None:
        """🔴 Sin `.order("id")` en empleado_repo, este test ROJEA: la página 1 y la 2 traen las
        mismas cinco personas empatadas y las otras cinco no salen en ninguna."""
        repo, _ = repo_paginado
        vistos: List[str] = []
        for page in (1, 2, 3):
            items, _total = repo.find_all(page, PAGE_SIZE, EMPRESA)
            vistos += [e.id for e in items]

        repetidos = sorted({i for i in vistos if vistos.count(i) > 1})
        faltantes = sorted({r["id"] for r in _padron()} - set(vistos))
        assert not repetidos, f"filas repetidas entre páginas: {repetidos}"
        assert not faltantes, f"filas que no aparecieron en ninguna página: {faltantes}"
        assert len(vistos) == TOTAL

    def test_ninguna_pagina_se_solapa_con_la_siguiente(self, repo_paginado) -> None:
        """Formulación complementaria: el corte entre páginas tiene que ser limpio."""
        repo, _ = repo_paginado
        p1 = {e.id for e in repo.find_all(1, PAGE_SIZE, EMPRESA)[0]}
        p2 = {e.id for e in repo.find_all(2, PAGE_SIZE, EMPRESA)[0]}
        assert not (p1 & p2), f"la página 2 repite {sorted(p1 & p2)} de la página 1"

    def test_el_fake_de_verdad_desordena(self, repo_paginado) -> None:
        """🔴 CONTRACARA OBLIGATORIA: si el fake dejara de reordenar, los tests de arriba pasarían
        sin desempate y serían tautologías. Acá se verifica que el mecanismo que los hace falsables
        siga vivo — pidiendo la MISMA página dos veces SIN ningún orden, el resultado cambia."""
        _repo, estado = repo_paginado
        crudo_1 = _FakeTabla(_padron(), estado).range(0, 9).execute().data
        crudo_2 = _FakeTabla(_padron(), estado).range(0, 9).execute().data
        assert [r["id"] for r in crudo_1] != [r["id"] for r in crudo_2]


class TestElTotalNoDependeDeLaPagina:
    def test_el_total_es_el_mismo_en_las_tres_paginas(self, repo_paginado) -> None:
        """El total sale del `count` de la consulta, no del largo de la página: si se derivara de
        `items` diría 10 en vez de 30, y cambiaría al llegar a la última página incompleta."""
        repo, _ = repo_paginado
        totales = [repo.find_all(p, PAGE_SIZE, EMPRESA)[1] for p in (1, 2, 3)]
        assert totales == [TOTAL, TOTAL, TOTAL]

    def test_el_total_no_es_el_largo_de_la_pagina(self, repo_paginado) -> None:
        repo, _ = repo_paginado
        items, total = repo.find_all(1, PAGE_SIZE, EMPRESA)
        assert len(items) == PAGE_SIZE and total == TOTAL


class TestElDesempateViajaEnLaQuery:
    """El orden tiene que estar EN LA CONSULTA, y el `id` ASCENDENTE.

    Molde: TestElOrdenLoPoneLaQuery (test_historial_salarial.py). Un `id` descendente ordenaría
    igual de bien pero NO lo puede servir `idx_empleados_empresa_apellido` (migración 118, creado
    como `(empresa_id, apellido, nombre, id)`): el plan volvería a necesitar un nodo de sort.
    """

    def _espia(self, monkeypatch):
        import repositories.empleado_repo as mod

        ordenes: List[tuple] = []

        class _Q:
            def select(self, *a, **k):
                return self

            def eq(self, *a, **k):
                return self

            # No-op encadenable: este espía captura SOLO los `.order()`, y el default de estado
            # del listado (`.neq("estado","preingreso")`) es un predicado, no un orden.
            def neq(self, *a, **k):
                return self

            def order(self, col, desc=False):
                ordenes.append((col, desc))
                return self

            def range(self, *a, **k):
                return self

            def execute(self):
                return SimpleNamespace(data=[], count=0)

        monkeypatch.setattr(mod, "supabase_admin", type("C", (), {"table": lambda s, t: _Q()})())
        return mod.EmpleadoRepo(), ordenes

    def test_ordena_por_apellido_nombre_y_desempata_por_id(self, monkeypatch) -> None:
        repo, ordenes = self._espia(monkeypatch)
        repo.find_all(1, 20, EMPRESA)
        assert ordenes == [("apellido", False), ("nombre", False), ("id", False)]

    def test_el_id_va_ultimo(self, monkeypatch) -> None:
        """Primero, ordenaría el listado por id y el apellido pasaría a ser el desempate."""
        repo, ordenes = self._espia(monkeypatch)
        repo.find_all(1, 20, EMPRESA)
        assert ordenes[-1][0] == "id"


def _llama(nodo, metodo: str, primer_arg=None) -> bool:
    """¿Este cuerpo EJECUTA `x.<metodo>(<primer_arg>, ...)`? Por AST, nunca por texto.

    🔴 QUE SEA POR AST NO ES ELEGANCIA: ES LA CONDICIÓN PARA QUE EL BARRIDO PUEDA FALLAR.
    Hasta el 15/8/2026 preguntaba `'.order("id")' in fuente`. El docstring de
    `_candidato_listado_repo.pagina()` EXPLICA el desempate y para eso escribe `.order("id")` en
    prosa — así que sacarle la llamada real no rojeaba nada: la explicación de por qué el
    desempate tiene que estar sostenía sola al test que verifica que esté. Es la misma trampa
    que `test_storage_punto_unico` ya había desactivado en su momento, en otro barrido.
    """
    import ast

    return any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == metodo
        and (primer_arg is None
             or (n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == primer_arg))
        for n in ast.walk(nodo)
    )


def _sin_desempate(fuentes: dict) -> list:
    """Las funciones que llaman a `.range()` sin que su desempate por `id` esté al alcance.

    🔴 EL ALCANCE ES LA FUNCIÓN, NO EL ARCHIVO, Y ESO ES LA MITAD DEL PUNTO DE ESTE HELPER.
    Hasta el 15/8/2026 el barrido miraba el archivo entero. Un repo con DOS lectores —uno
    paginado y otro que trae todo, que es la forma normal de estos módulos— pasaba con que
    CUALQUIERA de los dos desempatara. Se descubrió al mutar `_candidato_listado_repo.pagina()`:
    sacarle el desempate no rojeó, porque el `todos()` de tres líneas más arriba conservaba el
    suyo. La otra mitad del punto es `_llama`: por qué el chequeo dejó de ser textual.

    Resuelve UN nivel de delegación por nombre de función: `find_all` de `empleado_repo` arma el
    orden con `_ordenado(query)`, definido en `_empleado_row`. Buscar sólo en el cuerpo literal
    obligaría a elegir entre dividir un archivo y conservar el test — dos reglas del proyecto
    peleándose. ⚠️ Lo que se amplía es DÓNDE se busca, no qué se acepta: una función que no
    tenga el desempate ni en su cuerpo ni en los helpers que llama sigue rojeando.

    @param fuentes {nombre_de_archivo: código}. Se lo pasa así, y no una ruta, para que la
        contracara pueda correrlo sobre fuentes sintéticas — sin eso, el guard del barrido no
        recorrería el camino que recorre el barrido, que es la lección de la sesión 4.
    @return [(archivo, funcion)] de las que paginan sin desempate al alcance.
    """
    import ast

    arboles = {n: ast.parse(src) for n, src in fuentes.items()}

    # Índice de funciones por NOMBRE, para resolver los helpers importados de un satélite. El
    # nombre alcanza: los repos no tienen dos funciones distintas que se llamen igual.
    defs: dict = {n.name: n for arbol in arboles.values() for n in ast.walk(arbol)
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

    # ⚠️ Y el ALIAS del import, porque el call site puede no usar el nombre de la definición:
    # `empleado_repo` importa `ordenado as _ordenado` y llama `_ordenado(query)`. Sin esto el
    # índice no lo encuentra y el repo aparece como "pagina sin desempate" — falso positivo que
    # empujaría a alguien a agregar un desempate que ya está.
    alias = {a.asname: a.name for arbol in arboles.values() for n in ast.walk(arbol)
             if isinstance(n, ast.ImportFrom) for a in n.names if a.asname}

    def _llamadas_planas(nodo) -> set:
        """Nombres de lo que este cuerpo invoca como `f(...)`, no como `x.f(...)`."""
        nombres = {n.func.id for n in ast.walk(nodo)
                   if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        return nombres | {alias[n] for n in nombres if n in alias}

    fallas = []
    for nombre, arbol in arboles.items():
        for funcion in _defs_que_paginan(arbol):
            alcance = [funcion] + [defs[f] for f in _llamadas_planas(funcion) if f in defs]
            if not any(_llama(n, "order", "id") for n in alcance):
                fallas.append((nombre, funcion.name))
    return fallas


def _defs_que_paginan(arbol):
    """Las funciones del árbol que llaman a `.range(...)`. El universo que se barre."""
    import ast

    return [n for n in ast.walk(arbol)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and _llama(n, "range")]


def _fuentes_de_repositories() -> dict:
    from pathlib import Path
    raiz = Path(__file__).resolve().parent.parent / "repositories"
    return {p.name: p.read_text(encoding="utf-8") for p in raiz.glob("*.py")}


def _funciones_que_paginan(fuentes: dict) -> list:
    import ast

    return [(nombre, f.name) for nombre, src in fuentes.items()
            for f in _defs_que_paginan(ast.parse(src))]


class TestLosOtrosListadosPaginadosTambienDesempatan:
    """Barrido: toda FUNCIÓN que combine `.range()` con un listado lleva el desempate por `id`.

    🔑 DESCUBRE POR AST, no por una lista escrita a mano: un listado paginado nuevo entra solo.
    La guarda de mínimo evita el falso verde de un barrido que no encuentra nada.
    """

    PAGINADOS = {
        "empleado_repo.py", "vacaciones_repo.py", "ausencias_repo.py",
        "vacaciones_pendientes_repo.py", "audit_repo.py", "perfil_puesto_repo.py",
        "recategorizacion_repo.py", "horas_repo.py",
        # Sesión 5. Están nombrados acá además de descubrirse solos porque son los dos que
        # motivaron el cambio de alcance de archivo a función.
        "_candidato_listado_repo.py", "_evaluacion_evaluados_repo.py",
    }

    def test_todos_los_paginados_ordenan_por_id(self) -> None:
        fuentes = _fuentes_de_repositories()
        universo = _funciones_que_paginan(fuentes)
        assert len(universo) >= 15, (
            f"el barrido encontró {len(universo)} funciones que paginan; esperaba al menos 15. "
            "Si bajó, la detección se rompió y este test estaría pasando en el vacío."
        )
        fallas = _sin_desempate(fuentes)
        assert not fallas, (
            f"funciones que paginan sin desempate por id: {fallas}. Paginar sin orden total "
            "puede repetir o perder filas entre páginas."
        )

    def test_el_barrido_cubre_los_paginados_conocidos(self) -> None:
        """Contracara: si el descubrimiento dejara de ver alguno de los conocidos, el test de
        arriba lo dejaría de vigilar sin que nadie se entere."""
        vistos = {archivo for archivo, _f in _funciones_que_paginan(_fuentes_de_repositories())}
        faltan = self.PAGINADOS - vistos
        assert not faltan, f"el barrido no ve estos repos paginados: {sorted(faltan)}"

    def test_EL_ALCANCE_ES_LA_FUNCION_no_el_archivo(self) -> None:
        """🔴 LA CONTRACARA QUE HABRÍA CAZADO EL AGUJERO DEL 15/8/2026, corrida sobre fuentes
        sintéticas por el MISMO helper que usa el barrido real.

        El archivo tiene dos lectores: uno que trae todo y desempata, y uno paginado que no. Con
        el chequeo viejo —`'.order("id")' in src`— esto pasaba, porque el desempate del primero
        tapaba la falta del segundo. Si alguien vuelve a aflojar el alcance a nivel archivo,
        este test rojea."""
        fuente = (
            'def todos():\n'
            '    return base().order("created_at", desc=True).order("id").execute()\n'
            '\n'
            'def pagina(page, page_size):\n'
            '    return base().order("created_at", desc=True).range(0, page_size).execute()\n'
        )
        assert '.order("id")' in fuente, "la premisa: el archivo SÍ contiene el desempate"
        assert _sin_desempate({"x_repo.py": fuente}) == [("x_repo.py", "pagina")]

    def test_EL_DOCSTRING_QUE_EXPLICA_EL_DESEMPATE_NO_CUENTA(self) -> None:
        """🔴 LA OTRA MITAD DEL AGUJERO DEL 15/8/2026, y la más traicionera de las dos.

        `pagina()` de `_candidato_listado_repo` documenta POR QUÉ desempata, y para eso su
        docstring escribe la llamada. Con un chequeo textual, esa explicación satisfacía sola al
        barrido: se podía borrar la llamada real y el test seguía verde porque el comentario que
        dice que tiene que estar seguía estando. Acá se reproduce exacto — la función NO
        desempata y su docstring dice que sí.

        ⚠️ Y el arreglo NO es borrar la prosa: la prosa es correcta y hace falta. El arreglo es
        que el barrido mire el AST. Mismo criterio que `test_storage_punto_unico`.
        """
        fuente = (
            'def pagina(page, page_size):\n'
            '    """Una página. `.order("id")` = desempate, porque el orden no es único."""\n'
            '    return base().order("created_at", desc=True).range(0, page_size).execute()\n'
        )
        assert '.order("id")' in fuente, "la premisa: la prosa SÍ menciona el desempate"
        assert _sin_desempate({"x_repo.py": fuente}) == [("x_repo.py", "pagina")]

    def test_y_con_el_desempate_en_la_funcion_paginada_pasa(self) -> None:
        """La otra mitad: el helper no rechaza todo. Sin esto, `_sin_desempate` podría estar
        devolviendo siempre una falla y el test de arriba pasaría por el motivo equivocado."""
        fuente = ('def pagina(page, page_size):\n'
                  '    return base().order("x").order("id").range(0, page_size).execute()\n')
        assert _sin_desempate({"x_repo.py": fuente}) == []

    def test_resuelve_un_nivel_de_delegacion(self) -> None:
        """`find_all` de `empleado_repo` desempata dentro de `ordenado()`, que vive en otro
        archivo. Sin la resolución del helper, el barrido lo marcaría como falla."""
        fuentes = {
            "x_repo.py": 'def find_all(p, ps):\n    return _ordenado(q).range(0, ps).execute()\n',
            "_x_row.py": 'def _ordenado(q):\n    return q.order("apellido").order("id")\n',
        }
        assert _sin_desempate(fuentes) == []
        # Y si el helper NO desempata, sigue rojeando: se amplió dónde se busca, no qué se acepta.
        fuentes["_x_row.py"] = 'def _ordenado(q):\n    return q.order("apellido")\n'
        assert _sin_desempate(fuentes) == [("x_repo.py", "find_all")]

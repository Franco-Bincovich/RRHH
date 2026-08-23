"""
🔴 BARRIDO ESTRUCTURAL — falla cuando aparece un endpoint, una pantalla o una acción de escritura
que `docs/INVENTARIO-SMOKE.md` no lista, y también cuando el documento lista algo que ya no existe.

POR QUÉ EXISTE. El inventario se generó una vez y a partir de ahí compite con la tarea real de
cada sesión: nadie regenera un documento de 600 líneas a mitad de un bugfix. Este repo ya vio
cómo termina eso cinco veces este mes —`MODELO_DATOS.md` se declaraba "fuente de verdad única"
describiendo 13 tablas que no existían, y se borró—, y la respuesta que sí funcionó fue siempre
la misma: que el documento no se pueda quedar atrás en verde. Sin este test, el inventario
promete "nada quedó sin listar" y a la tercera tanda esa promesa es falsa, que es peor que no
tenerla: se lee como cobertura.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTE TEST PUEDA FALLAR?
  · Los tres lados se DESCUBREN (introspección de `app.routes`, recorrido de `app/`, grafo de
    imports del front). No hay ninguna lista escrita a mano de qué mirar, ni acá ni en el
    generador: los dos leen el mismo código y el test compara sus resultados con el archivo.
  · Verificado en las DOS direcciones. La dirección fácil (falta una fila) es la que uno escribe
    sola; la que evita que el documento se vuelva basura es la otra — una fila que apunta a un
    endpoint borrado o a un componente que ya no existe no es inofensiva: es una prueba que
    alguien va a intentar correr contra algo que no está.
  · Guardas de mínimo ANTES de comparar. Si el parseo del markdown se rompiera, los tres
    conjuntos del documento saldrían vacíos y "no falta nada" pasaría **sin haber comparado una
    sola fila**. Es el falso verde exacto que `barridoFront.test.ts` ya pagó en Windows.

🔑 SE PARSEA POR SECCIÓN, Y HOY ESO NO CAMBIA NADA — está medido, no supuesto. Se corrieron los
tres extractores contra el archivo ENTERO y contra su sección: **265 / 46 / 139 en los dos
casos, cero filas de más**. Los patrones ya son bastante específicos (un endpoint pide
`| nº | MÉTODO | \\`path\\``, una acción pide dos columnas con backticks seguidas) y la prosa de
la sección 5 —que sí cita `/api/empleados/{id}` y `POST /api/recategorizaciones`— no los matchea.
Se acota igual, y por una razón que no es la de hoy: **el día que una tabla gane una columna o la
sección 5 gane una tabla con la misma forma, el parseo global empieza a contar filas que no son
de esa lista, y el síntoma sería un fantasma inexplicable en la dirección 2.** Es una precaución
barata contra un cambio de formato, no la pieza que sostiene el barrido — decirlo al revés sería
inventarle un mérito a tres líneas de código.

🚩 LO QUE NO CUBRE: que el CONTENIDO de una fila sea correcto (que el gate escrito sea el gate
real, que el veredicto de automatizable esté bien elegido). Compara CLAVES: qué filas hay. El
contenido lo sostiene el generador, que es el único que las escribe — el modo de falla que este
test cierra es el documento viejo, no el documento equivocado.
"""
import re
import sys
from pathlib import Path
from typing import Set, Tuple

_RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_RAIZ / "scripts"))

from _inv_acciones import acciones                        # noqa: E402
from _inv_backend import endpoints                        # noqa: E402
from _inv_pantallas import pantallas                      # noqa: E402

DOC = _RAIZ / "docs" / "INVENTARIO-SMOKE.md"

# Criterio: bien por debajo de lo medido hoy (265 / 46 / 139), porque tiene que morder una ROTURA
# del parseo o del descubrimiento —que no baja un 20%, colapsa— y no el alta o baja normal de un
# endpoint. Si el documento entero se vaciara, estas tres guardas fallan antes que las demás.
_MINIMO_ENDPOINTS = 200
_MINIMO_PANTALLAS = 40
_MINIMO_ACCIONES = 100


def _seccion(titulo: str) -> str:
    """El texto entre `## titulo` y el siguiente `## `. Ver la nota del encabezado."""
    texto = DOC.read_text(encoding="utf-8")
    inicio = texto.index(f"## {titulo}")
    resto = texto[inicio + 3:]
    corte = resto.find("\n## ")
    return resto if corte < 0 else resto[:corte]


def _endpoints_del_doc() -> Set[Tuple[str, str]]:
    return {(m.group(1), m.group(2)) for m in re.finditer(
        r"^\|\s*\d+\s*\|\s*(\w+)\s*\|\s*`([^`]+)`", _seccion("1 — Endpoints"), re.M)}


def _pantallas_del_doc() -> Set[str]:
    return {m.group(1) for m in re.finditer(
        r"^\|\s*`(/[^`]*)`\s*\|", _seccion("2 — Pantallas"), re.M)}


def _acciones_del_doc() -> Set[Tuple[str, str]]:
    return {(m.group(1), m.group(2)) for m in re.finditer(
        r"^\|[^|]*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|", _seccion("3 — Acciones de escritura"),
        re.M)}


class TestElBarridoEstaMirandoAlgo:
    """Sin esto, todo lo de abajo compara conjuntos vacíos y pasa sin haber mirado nada."""

    def test_el_documento_existe(self) -> None:
        assert DOC.exists(), (
            "falta docs/INVENTARIO-SMOKE.md. Generalo: "
            "backend\\venv\\Scripts\\python.exe scripts/inventario_smoke.py")

    def test_parsea_las_tres_tablas(self) -> None:
        assert len(_endpoints_del_doc()) >= _MINIMO_ENDPOINTS, "el parseo de la tabla 1 se rompió"
        assert len(_pantallas_del_doc()) >= _MINIMO_PANTALLAS, "el parseo de la tabla 2 se rompió"
        assert len(_acciones_del_doc()) >= _MINIMO_ACCIONES, "el parseo de la tabla 3 se rompió"

    def test_el_descubrimiento_encuentra_algo(self) -> None:
        assert len(endpoints()) >= _MINIMO_ENDPOINTS
        assert len(pantallas()) >= _MINIMO_PANTALLAS
        assert len(acciones()) >= _MINIMO_ACCIONES


class TestNadaQuedaSinListar:
    """Dirección 1: algo existe en el código y el documento no lo tiene."""

    def test_todo_endpoint_esta_en_el_inventario(self) -> None:
        faltan = sorted({(e.metodo, e.path) for e in endpoints()} - _endpoints_del_doc())
        assert not faltan, (
            f"Endpoints montados que el inventario no lista: {faltan}. Es una superficie que "
            "nadie sabe que tiene que probar. Regeneralo: "
            "backend\\venv\\Scripts\\python.exe scripts/inventario_smoke.py")

    def test_toda_pantalla_esta_en_el_inventario(self) -> None:
        faltan = sorted({p.ruta for p in pantallas()} - _pantallas_del_doc())
        assert not faltan, f"Pantallas que el inventario no lista: {faltan}. Regeneralo."

    def test_toda_accion_de_escritura_esta_en_el_inventario(self) -> None:
        faltan = sorted({(a.componente, a.funcion) for a in acciones()} - _acciones_del_doc())
        assert not faltan, (
            f"Controles que escriben y el inventario no lista: {faltan}. Regeneralo.")


class TestElInventarioNoNombraFantasmas:
    """Dirección 2, la que evita que el documento se pudra: lista algo que ya no existe.

    No es inofensivo. Una fila que apunta a un endpoint borrado o a un componente que se renombró
    es una prueba que alguien va a intentar correr contra algo que no está, y va a leer el fallo
    como un bug del sistema. Es el mismo criterio con el que `test_callers_huerfanos.py` mata sus
    propias excepciones cuando dejan de corresponder.
    """

    def test_ningun_endpoint_del_documento_desapareció(self) -> None:
        sobran = sorted(_endpoints_del_doc() - {(e.metodo, e.path) for e in endpoints()})
        assert not sobran, f"El inventario lista endpoints que ya no existen: {sobran}."

    def test_ninguna_pantalla_del_documento_desapareció(self) -> None:
        sobran = sorted(_pantallas_del_doc() - {p.ruta for p in pantallas()})
        assert not sobran, f"El inventario lista pantallas que ya no existen: {sobran}."

    def test_ninguna_accion_del_documento_desapareció(self) -> None:
        sobran = sorted(_acciones_del_doc() - {(a.componente, a.funcion) for a in acciones()})
        assert not sobran, f"El inventario lista acciones que ya no existen: {sobran}."


class TestLoDeclaradoAManoSigueEnPie:
    """La única parte del inventario que no se deriva: la baja lógica y los 8 sin barrera.

    Las dos son declaraciones de PRODUCTO que no se leen del código (que `empresas/{id}` no valide
    empresa es que la empresa ES el recurso, no un descuido). Por eso llevan evidencia y por eso
    se verifica que la evidencia siga diciendo lo que dice: una excepción que sobrevive a su
    propio motivo es un permiso abierto que nadie vuelve a mirar.
    """

    def test_la_evidencia_de_baja_logica_sigue_en_el_codigo(self) -> None:
        from _inv_destructivo import evidencia_baja_logica
        rotas = evidencia_baja_logica()
        assert not rotas, (
            f"Declaraciones de baja LÓGICA que ya no se sostienen: {rotas}. O el service dejó de "
            "hacer soft-delete (y entonces el DELETE pasó a ser destructivo y hay que sacar la "
            "entrada), o la ruta se borró.")

    def test_los_endpoints_sin_barrera_de_empresa_siguen_existiendo(self) -> None:
        from _inv_casos import SIN_BARRERA
        montadas = {(e.metodo, e.path) for e in endpoints()}
        muertas = sorted(k for k in SIN_BARRERA if k not in montadas)
        assert not muertas, (
            f"Excepciones a la barrera de empresa que apuntan a rutas borradas: {muertas}.")

    def test_toda_declaracion_a_mano_tiene_razon_escrita(self) -> None:
        from _inv_casos import SIN_BARRERA
        from _inv_destructivo import IRREVERSIBLES
        flacas = [k for k, v in {**SIN_BARRERA, **IRREVERSIBLES}.items() if len(v.strip()) < 20]
        assert not flacas, f"Declaraciones sin razón escrita: {flacas}"


class TestElDocumentoEstaAlDia:
    """El chequeo entero: el archivo del repo es byte a byte lo que el código dice hoy.

    Los tests de arriba comparan CLAVES y son los que dan un mensaje útil (nombran la fila que
    falta). Éste compara el documento COMPLETO y es el que caza lo demás: un gate que cambió de
    sección, un veredicto que se movió, un conteo del resumen que quedó viejo. Va último a
    propósito — si falla sólo éste, ya se sabe que no falta ninguna fila, sólo su contenido.
    """

    def test_regenerarlo_no_lo_cambiaria(self) -> None:
        from inventario_smoke import generar
        esperado = generar()
        actual = DOC.read_text(encoding="utf-8")
        if actual == esperado:
            return
        viejas = [l for l in actual.splitlines() if l not in set(esperado.splitlines())]
        assert False, (
            "docs/INVENTARIO-SMOKE.md quedó atrás respecto del código. Regeneralo:\n"
            "  backend\\venv\\Scripts\\python.exe scripts/inventario_smoke.py\n"
            f"Primeras líneas que ya no corresponden: {viejas[:5]}")

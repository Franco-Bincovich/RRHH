"""
🔴 BARRIDO ESTRUCTURAL — `integrations/storage.py` es el ÚNICO que habla con Storage.

## Por qué existe

Los tres buckets estaban hardcodeados en 6 services y el SDK se llamaba desde 7. El día que esto
pase a S3, cada uno de esos archivos sería una edición en la capa de negocio. La recomendación #2
de las tres migraciones anteriores es exactamente lo contrario: un wrapper simétrico, para que el
código de negocio no cambie.

Centralizar una vez no sirve de nada si el próximo módulo vuelve a llamar al SDK — y nadie se
entera hasta el cutover. Este barrido es lo que hace que no vuelva.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS FALLEN?

**1. 🔴 SE LEE EL AST, NO EL TEXTO.** Un `grep` de `"documentos"` marcaría los DOCSTRINGS que
dicen "bucket privado 'documentos'" —que son prosa correcta y no código— y el barrido nacería con
falsos positivos. Un barrido que grita se apaga. Ya mordió dos veces en este repo (los
comentarios de `services/clientes.ts` y de `ClienteModal`), y está anotado en
`docs/ORDEN-SESIONES-CODIGO.md`. Acá se parsea con `ast` y se ignoran explícitamente los
docstrings y los comentarios.

**2. 🔴 GUARDA DE MÍNIMO.** Si el descubrimiento se rompe —cambia una ruta, falla el parseo— el
barrido encuentra 0 archivos y "nadie viola la regla" pasaría sobre un conjunto vacío. Es
exactamente lo que pasó con `barridoFront.test.ts` en Windows, donde un separador de path dejó el
escaneo en cero y las guardas fueron lo único que lo cazó.

**3. El test tendría que mirar solo los buckets, o solo el SDK.** Son dos fugas distintas: un
service puede dejar de nombrar el bucket pero seguir llamando al SDK con un valor que viene de una
fila (era el caso de `_adjuntos_masivo`, que por eso no estaba en el inventario original de 6).
Se verifican las dos.

⚠️ Lo que este barrido NO cubre: que el módulo haga lo correcto. Eso lo cubren los tests
funcionales de adjuntos, CVs y logo, que ejercitan el camino real contra un fake del SDK.
"""
import ast
from pathlib import Path
from typing import List, Tuple

_BACKEND = Path(__file__).resolve().parent.parent
_MODULO = "integrations/storage.py"          # el único que puede
_BUCKETS = {"documentos", "cvs", "avatars"}

# Criterio: ~25% por debajo del valor real de hoy (203 archivos en services/), el mismo que usan
# los otros barridos. El margen absorbe la baja normal del repo sin absorber una ROTURA del
# escaneo, que no baja un 25%: colapsa a cero.
_MINIMO_ARCHIVOS = 150


def _fuentes() -> List[Tuple[Path, ast.Module]]:
    """Todos los .py de services/ y repositories/, parseados. Descubrimiento por árbol: un
    módulo nuevo entra solo, sin tocar este archivo."""
    salida = []
    for carpeta in ("services", "repositories"):
        for py in sorted((_BACKEND / carpeta).rglob("*.py")):
            if py.name == "__init__.py":
                continue
            salida.append((py, ast.parse(py.read_text(encoding="utf-8"), filename=str(py))))
    return salida


def _es_docstring(nodo: ast.AST) -> bool:
    """Un `ast.Expr` cuyo valor es un str suelto: docstring o string de adorno, no código."""
    return isinstance(nodo, ast.Expr) and isinstance(nodo.value, ast.Constant) \
        and isinstance(nodo.value.value, str)


def _literales_de_codigo(arbol: ast.Module) -> List[str]:
    """Strings que son CÓDIGO. Excluye docstrings; los comentarios el AST ya no los ve."""
    docstrings = {id(n.value) for n in ast.walk(arbol) if _es_docstring(n)}
    return [n.value for n in ast.walk(arbol)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in docstrings]


def _usa_sdk_de_storage(arbol: ast.Module) -> bool:
    """Busca la cadena `<algo>.storage.<lo que sea>`, que es como se llama al SDK."""
    for n in ast.walk(arbol):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Attribute) \
                and n.value.attr == "storage":
            return True
    return False


ARCHIVOS = _fuentes()


class TestElBarridoEstaMirandoAlgo:
    def test_descubre_los_modulos(self) -> None:
        """Sin esto, todo lo de abajo pasaría sobre una lista vacía."""
        assert len(ARCHIVOS) >= _MINIMO_ARCHIVOS

    def test_el_modulo_de_storage_existe_y_usa_el_sdk(self) -> None:
        """La contracara: si el módulo NO llamara al SDK, el barrido pasaría porque no hay
        Storage en ningún lado — verde por vacío, que es el modo de falla que perseguimos."""
        modulo = _BACKEND / _MODULO
        assert modulo.exists(), f"falta {_MODULO}"
        arbol = ast.parse(modulo.read_text(encoding="utf-8"))
        assert _usa_sdk_de_storage(arbol), "el módulo dejó de hablar con el SDK"
        assert _BUCKETS.issubset(set(_literales_de_codigo(arbol))), \
            "el módulo dejó de declarar los tres buckets"


class TestNadieMasHablaConStorage:
    def test_ningun_service_ni_repo_llama_al_sdk(self) -> None:
        """El SDK de Storage se llama desde UN solo archivo. Si aparece otro, el cutover a S3
        pasa de tocar 1 archivo a tocar 2 — y el segundo no se va a acordar nadie."""
        culpables = [str(p.relative_to(_BACKEND)).replace("\\", "/")
                     for p, arbol in ARCHIVOS if _usa_sdk_de_storage(arbol)]
        assert culpables == [], (
            f"llaman al SDK de Storage fuera de {_MODULO}: {culpables}. "
            "Usá integrations/storage.py (subir / url_firmada / url_publica / borrar)."
        )

    def test_ningun_service_ni_repo_nombra_un_bucket(self) -> None:
        """Los nombres de bucket son del proveedor, no del negocio. El día que un bucket se
        renombre o se mapee a otra cosa en S3, tiene que haber UN lugar donde cambiarlo."""
        culpables = [
            (str(p.relative_to(_BACKEND)).replace("\\", "/"), b)
            for p, arbol in ARCHIVOS
            for b in _BUCKETS & set(_literales_de_codigo(arbol))
        ]
        assert culpables == [], (
            f"nombran un bucket a mano: {culpables}. "
            "Usá storage.DOCUMENTOS / storage.CVS / storage.AVATARS."
        )


class TestLosDocstringsNoCuentan:
    """🔴 El test del test: si el escaneo leyera prosa, esto rojearía.

    Varios services documentan "bucket privado 'documentos'" en su docstring, y eso está BIEN —
    es la explicación de qué hace el método. Este test fija que el barrido de arriba los ignora,
    para que nadie "arregle" un falso positivo borrando documentación correcta.
    """

    def test_hay_docstrings_que_nombran_un_bucket(self) -> None:
        con_prosa = []
        for p, arbol in ARCHIVOS:
            docs = [n.value.value for n in ast.walk(arbol) if _es_docstring(n)]
            if any(b in d for d in docs for b in _BUCKETS):
                con_prosa.append(p.name)
        assert con_prosa, "ya no hay prosa que nombre buckets: el test perdió su objeto"

"""
🔴 BARRIDO ESTRUCTURAL — solo `repositories/` habla con la base.

## Por qué existe

El trabajo del dev de infra es reescribir la capa de acceso a datos de Supabase SDK a asyncpg.
Cuanto más contenido esté ese acceso en `repositories/`, menos superficie tiene que tocar. La
arquitectura del repo ya lo declara —`repositories/` es el único punto de acceso a la DB— pero
hasta hoy nadie lo verificaba: era una aspiración, y un service nuevo podía meter una query
mañana sin que ningún barrido lo viera.

Los dos barridos que ya existen NO cubren esto: `test_selects_repos` valida que las COLUMNAS de
cada `select` existan (y de hecho normaliza la fuga, declarando excepciones para services), y
`test_contrato_repos` verifica que un service no llame un método que su colaborador no tiene.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTE TEST FALLE?

**1. 🔴 SE LEE EL AST, NO EL TEXTO.** Varios docstrings nombran tablas ("la tabla `users`",
"`costos_nomina`") y un grep los marcaría, con lo que el barrido nacería con falsos positivos y
se apagaría. Ya mordió dos veces en este repo. Acá se buscan llamadas `<algo>.table(...)` /
`.rpc(...)` en el árbol sintáctico: un comentario no es una llamada.

**2. 🔴 GUARDA DE MÍNIMO.** Si el descubrimiento se rompe —cambia una ruta, falla el parseo— el
barrido encuentra 0 archivos y "nadie viola la regla" pasaría sobre un conjunto vacío. Es lo que
pasó con `barridoFront.test.ts` en Windows, donde un separador de path dejó el escaneo en cero.

**3. 🔴 LAS EXCEPCIONES SON POR FAMILIA, NO POR ARCHIVO.** Hay 58 llamadas fuera de
`repositories/` y declararlas una por una daría una lista de 23 entradas — la lista que nadie
mira, el defecto ya anotado en K2 y K7. Se declaran **4 familias** con su motivo, y el barrido
falla ante cualquier archivo que no caiga en ninguna.

⚠️ Lo que este barrido NO dice: que las 58 declaradas estén BIEN. Dice que son conocidas. El
inventario con archivo:línea y el plan sobre ellas viven en `docs/handoff-aws/ACCESO-A-DATOS.md`.
"""
import ast
from pathlib import Path
from typing import List, Tuple

_BACKEND = Path(__file__).resolve().parent.parent
_CARPETAS = ("services", "routers", "utils", "middleware", "scripts", "config", "schemas")

# ── Las 4 familias declaradas, con su motivo ──────────────────────────────────
# 🔴 La clave es un SUBSTRING del path, no un archivo, y eso es el punto: declarar 23 archivos
# uno por uno da la lista que nadie mira (K2, K7). Si mañana nace `_reporte_headcount.py`,
# entra solo en su familia sin tocar esta lista — lo que se declara es la DECISIÓN de dónde
# vive el acceso analítico, no un inventario que hay que mantener.
# Son CUATRO, y el techo es 5: una quinta familia significa que la regla dejó de valer.
_FAMILIAS: dict[str, str] = {
    "reporte": (
        "REPORTES (12 archivos, 35 llamadas: `services/reportes/`, `_reporte_anual_metricas`, "
        "`reporte_anual`, `reporte_adhoc`). Agregaciones de los 14 reportes: counts, sumas y "
        "embeds armados por f-string según haya o no filtro de área. Ningún repo las modela, y "
        "meterlas en los repos de entidad daría repos con métodos que solo sirven a un reporte. "
        "CANDIDATAS a moverse si el trabajo de features termina antes del 6/9 — ver ACCESO-A-DATOS.md."
    ),
    "dashboard": (
        "DASHBOARD (4 archivos, 13 llamadas). Los 9 KPIs y las alertas: counts con filtro de "
        "empresa. Mismo criterio y mismo destino que reportes. 🔴 `_dashboard_alertas` resuelve "
        "la tabla desde el catálogo `BLOQUEOS`: nombre DINÁMICO, no se portea por búsqueda y "
        "reemplazo. Ver ACCESO-A-DATOS.md."
    ),
    "organigrama": (
        "ORGANIGRAMA (2 archivos, 9 llamadas). Arma el árbol de empleados/áreas/empresas y la "
        "vista por proyectos. 🔴 Es la única familia SIN motivo de diseño: no existe repo de "
        "organigrama y la lectura nació en el service. Decisión pendiente, no decisión tomada."
    ),
    "procesos": (
        "PROCESOS (1 llamada). Count por (tabla, estado) sobre el catálogo `_META`. 🔴 El nombre "
        "de tabla es DINÁMICO: vive en una estructura de datos, no en el sitio de la query. Es el "
        "que produjo el 500 del Panel de Procesos cuando J5a borró las tablas `ev_*`."
    ),
}

# Criterio: ~25% por debajo del valor real (219 archivos en services/ + 67 en routers/ + el
# resto). El margen absorbe la baja normal sin absorber una ROTURA del escaneo, que no baja un
# 25%: colapsa a cero.
_MINIMO_ARCHIVOS = 250


def _fuentes() -> List[Tuple[str, ast.Module]]:
    """Todos los .py de las capas que NO son repositories/, parseados."""
    salida = []
    for carpeta in _CARPETAS:
        base = _BACKEND / carpeta
        if not base.exists():
            continue
        for py in sorted(base.rglob("*.py")):
            if py.name == "__init__.py" or "__pycache__" in str(py):
                continue
            rel = str(py.relative_to(_BACKEND)).replace("\\", "/")
            salida.append((rel, ast.parse(py.read_text(encoding="utf-8"), filename=str(py))))
    return salida


def _llama_a_la_base(arbol: ast.Module) -> List[int]:
    """Líneas con `<algo>.table(...)` o `<algo>.rpc(...)`.

    ⚠️ `.from_()` NO cuenta: en este repo es de Storage (`supabase_admin.storage.from_(...)`),
    y su punto único es `integrations/storage.py`, con barrido propio.
    """
    return sorted({
        n.lineno for n in ast.walk(arbol)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr in ("table", "rpc")
    })


def _familia(archivo: str) -> str:
    """La familia de un archivo, o "" si no cae en ninguna (= infractor)."""
    for clave, motivo in _FAMILIAS.items():
        if clave in archivo:
            return motivo
    return ""


ARCHIVOS = _fuentes()


class TestElBarridoEstaMirandoAlgo:
    def test_descubre_los_modulos(self) -> None:
        """Sin esto, lo de abajo pasaría sobre una lista vacía."""
        assert len(ARCHIVOS) >= _MINIMO_ARCHIVOS

    def test_repositories_si_habla_con_la_base(self) -> None:
        """La contracara: si `repositories/` dejara de consultar, el barrido pasaría porque no
        hay acceso a datos en ningún lado — verde por vacío, el modo de falla que perseguimos."""
        repos = [p for p in (_BACKEND / "repositories").rglob("*.py") if p.name != "__init__.py"]
        con_query = [p for p in repos
                     if _llama_a_la_base(ast.parse(p.read_text(encoding="utf-8")))]
        assert len(con_query) >= 60, f"solo {len(con_query)} repos consultan: ¿se rompió el escaneo?"


class TestNadieMasHablaConLaBase:
    def test_ninguna_capa_fuera_de_repositories_consulta_sin_declarar(self) -> None:
        """Routers, utils, middleware, scripts, config y schemas están en CERO y tienen que
        seguir así. En services solo pasan las 4 familias declaradas arriba."""
        infractores = [
            f"{archivo}:{','.join(str(n) for n in lineas)}"
            for archivo, arbol in ARCHIVOS
            if (lineas := _llama_a_la_base(arbol)) and not _familia(archivo)
        ]
        assert infractores == [], (
            f"acceso a la base fuera de repositories/ sin declarar: {infractores}. "
            "El acceso a datos va en un repo — es lo que el dev de infra tiene que portear. "
            "Si es una familia nueva, declarala en _FAMILIAS CON su motivo."
        )

    def test_las_familias_declaradas_siguen_teniendo_queries(self) -> None:
        """Dirección inversa: una familia que ya no consulta es ruido que oculta el próximo caso.
        Si una se mudó a repositories/, hay que borrar su entrada."""
        vivas = {_familia(a) for a, arbol in ARCHIVOS if _llama_a_la_base(arbol)}
        muertas = [p for p, motivo in _FAMILIAS.items() if motivo not in vivas]
        assert muertas == [], f"familias declaradas que ya no consultan: {muertas}"

    def test_toda_familia_tiene_motivo_escrito(self) -> None:
        """Una lista pelada no se puede auditar: en seis meses nadie sabe por qué está cada una."""
        flacas = [p for p, motivo in _FAMILIAS.items() if len(motivo.strip()) < 20]
        assert flacas == []

    def test_no_hay_mas_de_cinco_familias(self) -> None:
        """🔴 El techo que hace que esta lista siga siendo legible. Una lista de 23 entradas no
        la mira nadie — es el defecto de K2 y K7, y el motivo por el que acá se declara por
        familia. Si hacen falta seis, el problema no es la lista: es que la regla dejó de valer."""
        assert len(_FAMILIAS) <= 5

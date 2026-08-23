"""
🔴 BARRIDO ESTRUCTURAL — todo 401 del backend está DECIDIDO del lado del front.

## Por qué existe

`frontend/services/authRefresh.ts` es el único lugar del front que puede destruir una sesión sin
que el usuario apriete nada. Hasta el 23/8/2026 decidía por `res.status`: **cualquier** 401
deslogueaba. `/vacantes` pedía los mails pendientes al montar, la casilla del sistema había
perdido el acceso a Google, el backend contestaba 401 `GMAIL_TOKEN_EXPIRED` y un usuario
perfectamente autenticado terminaba en /login — en cada carga de la pantalla. Buscando ese bug
apareció el segundo, idéntico: equivocarse de contraseña actual en /cambiar-password devuelve
401 `INVALID_CREDENTIALS`, y también te echaba.

El arreglo fue pasar a una **allowlist de `code`**. Una allowlist escrita a mano tiene un modo de
falla propio y peor que el bug que cierra: si mañana el backend agrega un 401 de autenticación
de verdad y nadie lo anota en el front, el usuario se queda con un token muerto y la app le
responde errores para siempre **sin mandarlo nunca al login**. Este barrido es lo que impide que
esa lista se pudra.

## Qué compara, en las DOS direcciones

  · **backend → front**: cada `code` de 401 que el backend puede emitir está en la allowlist del
    front, o declarado acá en `AJENOS` con su razón. Un 401 nuevo que nadie clasificó rojea.
  · **front → backend**: cada `code` de la allowlist existe de verdad en el backend. Una entrada
    muerta es ruido que tapa al próximo caso — el mismo criterio que
    `test_paridad_list_export.py` aplica a sus excepciones.

## 🔴 Por AST, y no por grep

`utils/errors.py:19` contiene `raise AppError("No autorizado", "UNAUTHORIZED", 401)` **adentro
del docstring de la clase**, como ejemplo de uso. Un grep lo levantaría como un 401 real y
empujaría a declarar un code que nadie emite — o peor, a borrar la línea que explica cómo se usa
`AppError`. Es la misma trampa que ya documentan `test_storage_punto_unico.py` (docstrings que
nombran un bucket) y `barridoSelect.test.ts` (comentarios que nombran `<select>`).

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTE BARRIDO PUEDA FALLAR?
  · Los codes se DESCUBREN recorriendo el árbol, no se listan acá. Si se listaran, este archivo
    sería una tercera copia de la misma lista y no podría desmentir a ninguna de las otras dos.
  · **Un 401 cuyo `code` no se puede resolver es un FALLO, no un salteo.** Es la regla que este
    repo pagó cuatro veces: "cero coincidencias" y "cero problemas" no pueden escribirse igual.
  · Guardas de mínimo en las dos puntas: si la extracción se rompiera, encontraría 0 codes y 0
    entradas en el front, y todo pasaría en el vacío.
"""

import ast
import re
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
FRONT_INTERCEPTOR = BACKEND.parent / "frontend" / "services" / "authRefresh.ts"

# Las carpetas de código propio. `tests/` queda afuera: un fake que devuelva 401 no es un 401
# que el backend emita, y meterlos obligaría a declarar cada doble de test.
CARPETAS = ("routers", "services", "repositories", "middleware", "utils", "integrations")


# ─── Los 401 que NO son de nuestra sesión ─────────────────────────────────────
# Cada uno con la razón por la que un front que lo reciba NO tiene que deslogear. Agregar acá es
# una decisión, y por eso pide escribirla.
# 🔴 `GMAIL_TOKEN_EXPIRED` ESTUVO ACÁ Y YA NO HACE FALTA, y esa ausencia es el registro del
# arreglo: era el 401 que originó todo este barrido —/vacantes lo recibía al montar y mandaba al
# login a alguien perfectamente autenticado— y desde el mismo día dejó de ser un 401: la
# renovación fallida sale **502** (`services/_google_token_fallo.py`). El front igual lo conoce y
# lo ignora, porque no puede apoyarse en que ningún backend futuro mande un 401 ajeno.
AJENOS: dict[str, str] = {
    "INVALID_CREDENTIALS":
        "Dos usos, ninguno es 'tu sesión venció'. En `auth_service` es el login (que además no "
        "pasa por el interceptor: está en RUTAS_SIN_REFRESH). En `usuario_service.cambiar_password` "
        "es 'la contraseña ACTUAL que escribiste está mal', y ESA ruta sí pasa por el interceptor: "
        "hasta el 23/8/2026 equivocarse de contraseña al cambiarla te deslogueaba.",
    "IDENTIFICACION_INVALIDA":
        "Link público de horas: el DNI no identificó a nadie. No hay ninguna sesión de dashboard "
        "involucrada. Hoy ni siquiera llega al interceptor (`services/horasPublico.ts` hace fetch "
        "directo, a propósito), pero el precedente de decidir por `code` sale justo de acá: ver "
        "`esSesionMuerta` en `components/features/horasPublico/logica.ts`.",
    "SESION_INVALIDA":
        "Link público de horas: venció el token OPACO del link, que no es el JWT del dashboard. "
        "Deslogear por esto le vaciaría la sesión de otro usuario del mismo navegador.",
}


# ─── Descubrimiento ───────────────────────────────────────────────────────────


def _constantes_de_modulo(arbol: ast.Module) -> dict[str, str]:
    """`NOMBRE = "literal"` a nivel módulo. Hace falta porque no todo `AppError` trae el code
    escrito en la llamada: `_sesion_horas.py` lo pasa por nombre (`_CODE_RECHAZO`)."""
    salida: dict[str, str] = {}
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and isinstance(nodo.value, ast.Constant) and isinstance(nodo.value.value, str):
            for destino in nodo.targets:
                if isinstance(destino, ast.Name):
                    salida[destino.id] = nodo.value.value
    return salida


def _texto(nodo: ast.AST | None, constantes: dict[str, str]) -> str | None:
    """El valor de un nodo que se espera string: literal, o un nombre de módulo ya resuelto."""
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
        return nodo.value
    if isinstance(nodo, ast.Name):
        return constantes.get(nodo.id)
    return None


def _es_401(nodo: ast.AST | None) -> bool:
    return isinstance(nodo, ast.Constant) and nodo.value == 401


def _del_json_response(llamada: ast.Call) -> str | None:
    """El `code` de un `JSONResponse(status_code=401, content={... "code": "X"})`."""
    contenido = next((k.value for k in llamada.keywords if k.arg == "content"), None)
    if not isinstance(contenido, ast.Dict):
        return None
    for clave, valor in zip(contenido.keys, contenido.values):
        if isinstance(clave, ast.Constant) and clave.value == "code" and isinstance(valor, ast.Constant):
            return str(valor.value)
    return None


def _codes_del_archivo(ruta: Path) -> list[tuple[str | None, int]]:
    """Todo 401 del archivo, con su `code` (o None si no se pudo resolver) y su línea.

    Las tres formas que el repo usa hoy, y no hay una cuarta:
      1. `AppError(mensaje, code, 401)` — el 99% de los casos.
      2. `NOMBRE = (mensaje, code, 401)` a nivel módulo, invocado después con `AppError(*NOMBRE)`
         (`identificacion_service.py`). El literal 401 vive en la tupla, no en la llamada, así
         que mirar solo `AppError(...)` lo perdería en silencio.
      3. `JSONResponse(status_code=401, content={...})` — el middleware, que responde sin pasar
         por `AppError` porque corta ANTES de que haya handler.
    """
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    constantes = _constantes_de_modulo(arbol)
    salida: list[tuple[str | None, int]] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name) and nodo.func.id == "AppError":
            if len(nodo.args) >= 3 and _es_401(nodo.args[2]):
                salida.append((_texto(nodo.args[1], constantes), nodo.lineno))
        elif isinstance(nodo, ast.Call) and any(k.arg == "status_code" and _es_401(k.value) for k in nodo.keywords):
            salida.append((_del_json_response(nodo), nodo.lineno))
        elif isinstance(nodo, ast.Tuple) and nodo.elts and _es_401(nodo.elts[-1]):
            codes = [c for c in (_texto(e, constantes) for e in nodo.elts[:-1]) if c]
            # El code es el ÚLTIMO string antes del 401: la firma de AppError es (mensaje, code,
            # status), y el mensaje es prosa mientras el code es SCREAMING_SNAKE.
            salida.append((codes[-1] if codes else None, nodo.lineno))
    return salida


def _todos_los_401() -> list[tuple[str, str | None, int]]:
    salida = []
    for carpeta in CARPETAS:
        for ruta in (BACKEND / carpeta).rglob("*.py"):
            for code, linea in _codes_del_archivo(ruta):
                salida.append((str(ruta.relative_to(BACKEND)).replace("\\", "/"), code, linea))
    return salida


def _allowlist_del_front() -> set[str]:
    """Los codes de `CODES_SESION_MUERTA`, leídos del archivo REAL del front.

    Se recorta al bloque del `new Set([...])` a propósito: el docstring de arriba nombra en prosa
    los codes AJENOS (para explicar por qué no están), y tomarlos también daría una lista que
    contiene justo lo que la lista excluye.
    """
    fuente = FRONT_INTERCEPTOR.read_text(encoding="utf-8")
    bloque = re.search(r"CODES_SESION_MUERTA[^=]*=\s*new Set\(\[(.*?)\]\)", fuente, re.S)
    return set(re.findall(r'"([A-Z_]+)"', bloque.group(1))) if bloque else set()


CODES_401 = _todos_los_401()
DESLOGUEAN = _allowlist_del_front()


class TestSePudoMedir:
    """Guardas contra el falso verde: sin ellas, una extracción rota pasa sin comparar nada."""

    def test_hay_401_en_el_backend(self):
        assert len(CODES_401) >= 8, f"Solo encontré {len(CODES_401)} 401 en el backend; la extracción está rota"

    def test_el_front_declara_una_allowlist(self):
        assert len(DESLOGUEAN) >= 3, (
            f"No pude leer CODES_SESION_MUERTA de {FRONT_INTERCEPTOR.name} (encontré {DESLOGUEAN}). "
            "Si el nombre o la forma de la constante cambió, actualizá este barrido en la MISMA "
            "sesión: un ancla que no matchea es un control apagado, no un control que pasa."
        )

    @pytest.mark.parametrize("archivo,code,linea", CODES_401, ids=lambda v: str(v))
    def test_todo_401_tiene_code_resoluble(self, archivo: str, code: str | None, linea: int):
        """No poder determinar el code es un FALLO. Un 401 sin code identificable es, del lado
        del front, indistinguible de un 401 de un proxy — y no se puede decidir sobre él."""
        assert code is not None, (
            f"{archivo}:{linea} emite un 401 y no pude resolver su `code`. Escribilo como literal "
            "en la llamada, o como constante de módulo, para que este barrido pueda clasificarlo."
        )


class TestTodo401EstaClasificado:
    @pytest.mark.parametrize("archivo,code,linea", CODES_401, ids=lambda v: str(v))
    def test_desloguea_o_esta_declarado_ajeno(self, archivo: str, code: str | None, linea: int):
        assert code in DESLOGUEAN or code in AJENOS, (
            f"{archivo}:{linea} emite 401 `{code}` y nadie decidió qué hace el front con él.\n"
            "  · Si significa QUE LA SESIÓN DEL NAVEGADOR DEJÓ DE VALER → agregalo a "
            "CODES_SESION_MUERTA en frontend/services/authRefresh.ts.\n"
            "  · Si no (una integración caída, una credencial de formulario, un token que no es "
            "el JWT del dashboard) → agregalo a AJENOS acá, CON su razón.\n"
            "Un 401 sin clasificar hereda el bug que este barrido cierra: o desloguea de más, o "
            "deja al usuario con un token muerto y sin salida."
        )


class TestLaAllowlistNoTieneEntradasMuertas:
    """Un code que el backend ya no emite es ruido que tapa el próximo caso real."""

    @pytest.mark.parametrize("code", sorted(DESLOGUEAN))
    def test_el_code_existe_en_el_backend(self, code: str):
        assert code in {c for _, c, _ in CODES_401}, (
            f"El front desloguea ante 401 `{code}` y el backend ya no lo emite en ningún lado. "
            "Sacalo de CODES_SESION_MUERTA."
        )

    @pytest.mark.parametrize("code", sorted(AJENOS))
    def test_el_ajeno_declarado_existe(self, code: str):
        assert code in {c for _, c, _ in CODES_401}, (
            f"AJENOS declara `{code}` y el backend ya no lo emite. Sacá la excepción: una "
            "excepción muerta es exactamente lo que oculta el próximo caso."
        )

    def test_ningun_code_esta_en_las_dos_listas(self):
        cruce = DESLOGUEAN & set(AJENOS)
        assert cruce == set(), f"Estos codes están declarados como sesión Y como ajenos: {sorted(cruce)}"

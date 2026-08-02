"""
🔴 BARRIDO ESTRUCTURAL — `frontend/services/permisos.ts` es un ESPEJO MANUAL de
`backend/utils/permisos.py`, y hasta hoy nada lo verificaba.

QUÉ PASA CUANDO DIVERGEN. El backend es la autoridad: responde 403 y la seguridad no se pierde.
Lo que se pierde es la UX, y de las dos formas posibles:
  · Sección en el backend y NO en el front → el ítem no aparece en el menú y la ruta redirige.
    La feature existe, está permitida, y para el usuario no está. Nadie abre un ticket por algo
    que no ve.
  · Sección en el front y NO en el backend → el menú la ofrece y al entrar da 403. Se lee como
    un bug del sistema, no como un permiso.
Las dos son silenciosas en el deploy y en la suite: por eso este test.

POR QUÉ SE COMPARA EL TEXTO DEL `.ts` Y NO SE EJECUTA. No hay runtime de TypeScript acá y montar
uno para leer tres listas sería más frágil que el regex. Lo que se extrae son declaraciones
literales (una unión de strings, un `new Set([...])`, tres comparaciones `rol === "..."`), que es
lo más estable que tiene ese archivo. Si alguien las escribe de otra forma, el test FALLA por la
guarda de mínimo — no pasa en el vacío.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
  · Cada extracción tiene su **guarda de mínimo** ANTES de comparar. Sin ella, un regex que deja
    de matchear devolvería el conjunto vacío y `set() == set()` daría verde habiendo comparado
    nada — exactamente el falso verde que los otros tres barridos del repo ya evitan así.
  · Se compara en LAS DOS DIRECCIONES (`==` de conjuntos, no `<=`): sobra y falta son fallos
    distintos y los dos importan.
  · El archivo se resuelve por ruta y se verifica que exista: si el front se mueve o se renombra,
    esto falla en vez de saltearse.

🚩 LO QUE ESTE TEST **NO** CUBRE: que las dos implementaciones de `puede()` se comporten igual.
Verifica el VOCABULARIO (qué secciones, qué acciones, qué roles, qué secciones opera
mandos_medios), que es donde la divergencia es real —una sección nueva se agrega de a un lado—.
La lógica de las tres ramas son cuatro líneas por lado y no cambia hace meses.
"""
import os

_TEST_ENV: dict[str, str] = {
    "SUPABASE_URL": "https://test-project.supabase.co",
    "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.anon",
    "SUPABASE_SERVICE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.service",
    "JWT_SECRET": "test-secret-for-unit-tests-only-minimum-32-chars!!",
    "ANTHROPIC_API_KEY": "sk-ant-test",
    "RESEND_API_KEY": "re_test",
}
for _k, _v in _TEST_ENV.items():
    os.environ.setdefault(_k, _v)

import re
from pathlib import Path

from utils.permisos import MANDOS_MEDIOS_SECCIONES, ROLES_VALIDOS, Accion, Seccion

_PERMISOS_TS = Path(__file__).resolve().parent.parent.parent / "frontend" / "services" / "permisos.ts"

# Mínimos: no son "la cantidad correcta" sino el piso por debajo del cual la EXTRACCIÓN se rompió.
# Muy por debajo de los valores reales de hoy (27 · 2 · 3 · 2), para que agregar o sacar una
# sección legítima no toque este archivo.
_MIN_SECCIONES, _MIN_MANDOS, _MIN_ROLES, _MIN_ACCIONES = 20, 2, 3, 2


def _fuente() -> str:
    assert _PERMISOS_TS.exists(), (
        f"No existe {_PERMISOS_TS}. El espejo del front se movió o se renombró: este barrido "
        "tiene que fallar, no saltearse.")
    return _PERMISOS_TS.read_text(encoding="utf-8")


def _union(nombre: str, texto: str) -> set[str]:
    """Extrae los literales de `export type <nombre> = "a" | "b" | ...` (una o varias líneas)."""
    m = re.search(rf"export type {nombre}\s*=\s*((?:[^=;]|\n)*?)\n\n", texto)
    return set(re.findall(r'"([a-z_]+)"', m.group(1))) if m else set()


def _set_literal(nombre: str, texto: str) -> set[str]:
    """Extrae los literales de `const <nombre>... = new Set<...>([ "a", "b" ])`."""
    m = re.search(rf"const {nombre}\b[^=]*=\s*new Set<[^>]*>\(\[(.*?)\]\)", texto, re.S)
    return set(re.findall(r'"([a-z_]+)"', m.group(1))) if m else set()


class TestLasSecciones:
    """El vocabulario grande: 27 secciones que se escriben a mano en los dos lados."""

    def test_la_extraccion_encontro_secciones(self) -> None:
        """🔴 GUARDA DE MÍNIMO. Va PRIMERO y en su propio test: si el regex deja de matchear,
        el conjunto queda vacío y la comparación de abajo pasaría sin haber comparado nada."""
        assert len(_union("Seccion", _fuente())) >= _MIN_SECCIONES

    def test_son_exactamente_las_mismas_que_en_el_backend(self) -> None:
        ts = _union("Seccion", _fuente())
        py = {s.value for s in Seccion}
        assert ts == py, (
            f"El espejo de permisos divergió.\n"
            f"  Solo en el backend (el menú no las va a mostrar): {sorted(py - ts)}\n"
            f"  Solo en el front (el menú las ofrece y dan 403): {sorted(ts - py)}\n"
            "Se agregan en los DOS lados: utils/permisos.py y frontend/services/permisos.ts.")


class TestLasAcciones:
    def test_la_extraccion_encontro_acciones(self) -> None:
        assert len(_union("Accion", _fuente())) >= _MIN_ACCIONES

    def test_son_read_y_write_de_los_dos_lados(self) -> None:
        """Una tercera acción (p. ej. 'delete') agregada de un solo lado dejaría al front
        decidiendo sobre una acción que el backend no conoce, o al revés."""
        assert _union("Accion", _fuente()) == {a.value for a in Accion}


class TestMandosMedios:
    """La regla más cara de que divergía: define QUÉ VE un rol entero."""

    def test_la_extraccion_encontro_el_set(self) -> None:
        assert len(_set_literal("MANDOS_MEDIOS_SECCIONES", _fuente())) >= _MIN_MANDOS

    def test_son_las_mismas_secciones_que_en_el_backend(self) -> None:
        ts = _set_literal("MANDOS_MEDIOS_SECCIONES", _fuente())
        py = {s.value for s in MANDOS_MEDIOS_SECCIONES}
        assert ts == py, (
            f"MANDOS_MEDIOS_SECCIONES divergió: backend={sorted(py)} front={sorted(ts)}. "
            "De más en el front = menú que da 403; de menos = sección invisible para el rol.")

    def test_las_secciones_de_mandos_medios_existen_en_el_vocabulario(self) -> None:
        """Un typo acá no rompe nada visible: el rol simplemente deja de tener esa sección."""
        assert _set_literal("MANDOS_MEDIOS_SECCIONES", _fuente()) <= _union("Seccion", _fuente())


class TestLosRoles:
    def test_la_extraccion_encontro_roles(self) -> None:
        assert len(set(re.findall(r'rol === "([a-z_]+)"', _fuente()))) >= _MIN_ROLES

    def test_puede_contempla_exactamente_los_roles_validos(self) -> None:
        """Un cuarto rol en el backend sin rama en el front cae en el `return false` final:
        el usuario entra al sistema y no ve NADA, sin ningún error que lo explique."""
        ts = set(re.findall(r'rol === "([a-z_]+)"', _fuente()))
        assert ts == set(ROLES_VALIDOS), (
            f"Los roles de puede() divergieron: backend={sorted(ROLES_VALIDOS)} front={sorted(ts)}.")

    def test_el_front_es_fail_closed(self) -> None:
        """La última línea de `puede` en el front tiene que ser un `return false` pelado: sin
        él, un rol desconocido caería en `undefined` (falsy hoy, pero por accidente)."""
        cuerpo = re.search(r"export function puede\([^)]*\)[^{]*\{(.*?)\n\}", _fuente(), re.S)
        assert cuerpo and cuerpo.group(1).strip().splitlines()[-1].strip() == "return false"

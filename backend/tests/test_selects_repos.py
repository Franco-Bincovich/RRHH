"""
🔴 BARRIDO ESTRUCTURAL — todos los `select` con embed del repo, validados contra `db/schema.sql`.

ES LA TERCERA VEZ QUE LA MISMA CLASE DE BUG LLEGA A PRODUCCIÓN:
  1. Los 6 reportes de Fase 1 — columnas inexistentes y embeds ambiguos (400 / PGRST201).
  2. El listado de plantillas de onboarding.
  3. `planes_carrera_repo` pidiendo `planes_carrera_hitos!planes_carrera_hitos_plan_emp_fkey`
     cuando la constraint se llama `pc_hitos_plan_emp_fkey` → `GET /api/sucesion/planes` en 500
     durante meses, encontrado por el smoke test y no por los 1117 tests.

`tests/_postgrest_schema.py` se construyó para cerrarla y validaba SOLO los generadores de
reportes (`test_reportes_columnas.py`). Los repos quedaron afuera, y por ahí entraron los casos 2
y 3. Este barrido cierra el hueco: valida TODO lo que se pueda resolver estáticamente.

POR QUÉ NO ALCANZA LA SUITE NORMAL: el fake de Supabase implementa `select(*a, **k)` IGNORANDO el
argumento, así que acepta cualquier spec —exista o no la columna, resuelva o no el embed—. Ningún
test que pase por el fake puede desmentir un nombre mal escrito. Este barrido no usa el fake: lee
el código con AST y compara contra el schema.

🔴 DESCUBRIMIENTO POR INTROSPECCIÓN, NUNCA UNA LISTA. Un repo nuevo queda cubierto solo. Los tres
casos de arriba se colaron justamente por no estar en una lista.
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

import pytest

from tests._postgrest_schema import SelectInvalidoError, cargar_schema
from tests._selects_descubiertos import descubrir

DIRECTORIOS = ("repositories", "services")

TODOS = descubrir(*DIRECTORIOS)
CON_EMBED = [s for s in TODOS if s.tiene_embed]
SIN_RESOLVER = [s for s in TODOS if not s.resuelto]

# 🔴 Mínimos contra el falso verde. Sin estas guardas, una detección rota (un cambio de AST, un
# `.select(` que se escribe distinto, un directorio mal armado) devolvería 0 hallazgos y el
# barrido pasaría sin haber comparado NADA — que es peor que no tenerlo, porque da confianza.
MINIMO_SELECTS = 150      # al 30/7/2026 hay 189 en repositories/ + los de services/
MINIMO_EMBEDS = 40        # al 30/7/2026 hay 46 solo en repositories/

# Selects que NO se pueden resolver estáticamente. Se DECLARAN, no se sacan del barrido.
#
# La clave es el ARCHIVO y el valor es (cuántos hay, por qué). Se declara por archivo y no por
# `archivo:línea` a propósito: un número de línea se desactualiza con cualquier edición y la
# excepción quedaría apuntando al vacío. El CONTEO cubre el hueco que eso deja — si aparece un
# select dinámico NUEVO en un archivo ya declarado, el conteo no coincide y el test falla.
SIN_RESOLVER_DECLARADOS = {
    # Helpers genéricos que reciben tabla y columnas por parámetro. Verificado CALLER POR CALLER
    # que ninguno recibe un embed, solo listas de columnas planas.
    "repositories/asignacion_repo.py": (1, "_q(table, cols, ids): sus 4 callers pasan columnas planas"),
    # `_q` se mudó de ausencias_repo a _ausencia_row al dividirlo (mig 088). La excepción se
    # MUEVE con el código: dejarla apuntando al archivo viejo la volvía una excepción muerta,
    # que es justo lo que la segunda mitad de este barrido detecta.
    "repositories/_ausencia_row.py": (1, "_q(table, cols, ids): sus 4 callers pasan columnas planas"),
    "repositories/empleado_roles_repo.py": (1, "select(campo): UNA columna de la whitelist CAMPOS_AUTOCOMPLETABLES"),
    "repositories/_evaluacion_lotes_enrich.py": (1, "tabla por parámetro, spec literal 'id, nombre' — sin embed"),
    "repositories/dashboard_equipo_repo.py": (1, "tabla por parámetro, spec literal 'id' — sin embed"),
    # Counts genéricos con la tabla por parámetro y spec literal sin embed.
    "services/dashboard_service.py": (1, "_count(table, **filtros): select('id', count='exact') — sin embed"),
    "services/_dashboard_alertas.py": (1, "_alerta_de_bloqueo(b): tabla del catálogo, spec literal 'id' — sin embed"),
    "services/procesos_service.py": (1, "count por (tabla, estado): select('id') — sin embed"),
    "services/reporte_anual.py": (1, "_count_rango(tabla, ...): select('id') — sin embed"),
    # 🔴 Los generadores de reportes SÍ arman embeds dinámicamente (f-strings que cambian según
    # `area_id`), pero NO son un punto ciego: `tests/test_reportes_columnas.py` los valida MEJOR
    # que esto — ejecuta cada generador con un Supabase falso que captura el select real y lo pasa
    # por el mismo validador, DOS veces, con y sin `area_id`. Un barrido estático solo vería una
    # de las dos ramas, que es justo donde vivía el bug de ausentismo.
    "services/reportes/_reporte_ausentismo.py": (1, "embed dinámico — cubierto por test_reportes_columnas"),
    "services/reportes/_reporte_capacitacion.py": (1, "embed dinámico — cubierto por test_reportes_columnas"),
    "services/reportes/_reporte_costos.py": (1, "embed dinámico — cubierto por test_reportes_columnas"),
    "services/reportes/_reporte_dotacion.py": (1, "embed dinámico — cubierto por test_reportes_columnas"),
    "services/reportes/_reporte_seleccion.py": (1, "embed dinámico — cubierto por test_reportes_columnas"),
    "services/reportes/_reporte_vacaciones.py": (2, "embeds dinámicos — cubiertos por test_reportes_columnas"),
}


def test_el_barrido_encontro_selects():
    """Guarda de mínimo. Ver la nota de MINIMO_SELECTS."""
    assert len(TODOS) >= MINIMO_SELECTS, (
        f"el barrido encontró {len(TODOS)} selects y el mínimo es {MINIMO_SELECTS}: "
        "la DETECCIÓN se rompió, no es que hayan desaparecido los selects")


def test_el_barrido_encontro_embeds():
    """🔴 La guarda que más importa: sin embeds detectados, validarlos pasa en el vacío."""
    assert len(CON_EMBED) >= MINIMO_EMBEDS, (
        f"el barrido encontró {len(CON_EMBED)} selects con embed y el mínimo es {MINIMO_EMBEDS}. "
        "Con 0 embeds el test de validación pasaría sin comparar nada.")


def _sin_resolver_por_archivo() -> dict:
    from collections import Counter
    return Counter(s.archivo for s in SIN_RESOLVER)


def test_no_hay_selects_sin_resolver_no_declarados():
    """Un select dinámico nuevo tiene que declararse, con el motivo, no aparecer en silencio.

    Es lo que evita que el barrido se degrade solo: sin este test alguien podría agregar un
    `.select(variable)` y el embed que arma quedaría sin validar sin que nadie se enterara.
    """
    nuevos = set(_sin_resolver_por_archivo()) - set(SIN_RESOLVER_DECLARADOS)
    assert not nuevos, (
        f"archivos con selects sin resolver NO declarados: {sorted(nuevos)}.\n"
        "Si el spec es dinámico, verificá caller por caller que no lleve embeds y agregalo a "
        "SIN_RESOLVER_DECLARADOS con el motivo.")


def test_no_aparecieron_selects_dinamicos_nuevos():
    """El conteo por archivo tiene que coincidir con lo declarado.

    Es lo que hace que declarar por ARCHIVO no debilite la guarda: un `.select(variable)` nuevo en
    un archivo ya declarado cambia el conteo y falla acá, en vez de colarse bajo una excepción
    escrita para otro select.
    """
    real = _sin_resolver_por_archivo()
    for archivo, (esperados, motivo) in SIN_RESOLVER_DECLARADOS.items():
        assert real.get(archivo, 0) == esperados, (
            f"{archivo}: declarados {esperados} selects sin resolver ({motivo}) pero hay "
            f"{real.get(archivo, 0)}. Si el nuevo lleva un embed, hay que validarlo.")


def test_las_excepciones_declaradas_siguen_existiendo():
    """Una excepción que apunta a un archivo sin selects dinámicos es ruido que tapa el próximo
    caso. Mismo criterio que `_EXPORTS_SIN_LISTADO` en test_paridad_list_export."""
    muertas = set(SIN_RESOLVER_DECLARADOS) - set(_sin_resolver_por_archivo())
    assert not muertas, f"excepciones declaradas que ya no corresponden a ningún select: {sorted(muertas)}"


@pytest.mark.parametrize("sel", CON_EMBED, ids=lambda s: s.ubicacion)
def test_cada_embed_resuelve_contra_el_schema(sel):
    """🔴 EL TEST QUE CIERRA LA CLASE.

    Valida el spec como lo haría PostgREST: que cada columna exista, que cada tabla embebida
    exista, que la FK nombrada sea real, y que un embed sin nombrar no sea ambiguo.

    Para que falle: escribir mal el nombre de una constraint. Verificado por mutación con el caso
    real —`pc_hitos_plan_emp_fkey` → `planes_carrera_hitos_plan_emp_fkey`— que es el que estuvo
    roto en producción.
    """
    schema = cargar_schema()
    try:
        schema.validar_select(sel.tabla, sel.spec)
    except SelectInvalidoError as exc:
        pytest.fail(f"{sel.ubicacion} — select inválido sobre '{sel.tabla}':\n  {exc}")


def test_el_embed_de_sucesion_esta_bien_nombrado():
    """El caso concreto que motivó este barrido, fijado aparte para que no se pierda de vista.

    `planes_carrera_hitos` tiene DOS FKs a `planes_carrera`, así que el embed DEBE nombrarla o
    PostgREST responde 300 PGRST201. Y el nombre tiene que ser el real: Postgres la creó como
    `pc_hitos_plan_emp_fkey`, no con el nombre largo que uno esperaría.
    """
    from repositories import planes_carrera_repo as pc

    assert "pc_hitos_plan_emp_fkey" in pc._PC_SELECT
    assert "planes_carrera_hitos_plan_emp_fkey" not in pc._PC_SELECT
    cargar_schema().validar_select("planes_carrera", pc._PC_SELECT)   # no debe levantar

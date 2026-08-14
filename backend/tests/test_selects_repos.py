"""
🔴 BARRIDO ESTRUCTURAL — todos los `select` del repo, validados contra `db/schema.sql`.

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

🔴 EL CUARTO CASO, Y POR QUÉ HAY DOS TESTS DE VALIDACIÓN Y NO UNO. Hasta el 7/8/2026 este archivo
DESCUBRÍA todos los selects pero validaba solo los que tenían embed: la parametrización iba sobre
`CON_EMBED`, así que **188 selects de columnas planas se descubrían y se tiraban**. Por ese hueco
pasó `organigrama_proyectos_service.py` —6 selects, 0 embeds— con tres columnas que nunca salieron
de Postgres. El directorio NO era el problema: `services/` ya estaba barrido. El problema era el
predicado.
Los dos tests conviven porque cubren fallas DISTINTAS y ninguno implica al otro:
  · columnas planas → 400 42703, la columna no existe.
  · embeds          → 300 PGRST201, la relación es ambigua o la FK nombrada no existe.
Un select sin embed no puede dar PGRST201, y uno con embed puede tener las columnas bien y la FK
mal. Fundirlos en un test dejaría el mensaje de error sin decir cuál de las dos cosas pasó.
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

# `repositories` y `services` son donde vive el 100% de los selects. Los otros seis son
# PREVENCIÓN y hay que leerlos así: entre los cinco de infraestructura —middleware, utils,
# scripts, integrations, config— hay CERO selects hoy, y agregarlos no cierra nada. Están para
# que el día que alguien escriba el primero ahí, nazca adentro del barrido en vez de afuera.
# `routers` es el único que aporta algo: 1 select (`routers/usuarios.py`, sobre `users`), que
# hasta hoy era el ÚNICO select del backend fuera de repos+services y no lo validaba nadie.
DIRECTORIOS = ("repositories", "services", "routers",
               "middleware", "utils", "scripts", "integrations", "config")

TODOS = descubrir(*DIRECTORIOS)
RESUELTOS = [s for s in TODOS if s.resuelto]
CON_EMBED = [s for s in TODOS if s.tiene_embed]
SIN_RESOLVER = [s for s in TODOS if not s.resuelto]
ARCHIVOS = {s.archivo for s in TODOS}

# 🔴 Mínimos contra el falso verde. Sin estas guardas, una detección rota (un cambio de AST, un
# `.select(` que se escribe distinto, un directorio mal armado) devolvería 0 hallazgos y el
# barrido pasaría sin haber comparado NADA — que es peor que no tenerlo, porque da confianza.
#
# Es LA guarda que más importa de este archivo: el modo de falla que cubre no es hipotético, es
# el que dejó 6 reportes rotos en producción durante meses CON LA SUITE EN VERDE. Un barrido que
# mira cero selects y pasa es indistinguible de uno que los miró todos.
#
# Criterio de los dos mínimos nuevos: ~25% por debajo del real del 7/8/2026 (238 resueltos, 81
# archivos), igual que las guardas de `test_callers_huerfanos`. El margen absorbe la baja normal
# —este repo borra código muerto y parte archivos seguido— pero no una ROTURA del descubrimiento,
# que no baja un 25%: colapsa a cero o a una fracción.
MINIMO_SELECTS = 150      # al 30/7/2026 hay 189 en repositories/ + los de services/
MINIMO_EMBEDS = 40        # al 30/7/2026 hay 46 solo en repositories/
MINIMO_RESUELTOS = 178    # al 7/8/2026 hay 238
MINIMO_ARCHIVOS = 60      # al 7/8/2026 hay 81 archivos con al menos un select

# Selects que NO se pueden resolver estáticamente. Se DECLARAN, no se sacan del barrido.
#
# La clave es el ARCHIVO y el valor es (cuántos hay, por qué). Se declara por archivo y no por
# `archivo:línea` a propósito: un número de línea se desactualiza con cualquier edición y la
# excepción quedaría apuntando al vacío. El CONTEO cubre el hueco que eso deja — si aparece un
# select dinámico NUEVO en un archivo ya declarado, el conteo no coincide y el test falla.
SIN_RESOLVER_DECLARADOS = {
    # Helpers genéricos que reciben tabla y columnas por parámetro. Verificado CALLER POR CALLER
    # que ninguno recibe un embed, solo listas de columnas planas.
    # `_q` se mudó de ausencias_repo a _ausencia_row al dividirlo (mig 088), y de asignacion_repo
    # a _asignacion_row al dividir ESE (mig 116). La excepción se MUEVE con el código: dejarla
    # apuntando al archivo viejo la volvía una excepción muerta, que es justo lo que la segunda
    # mitad de este barrido detecta.
    "repositories/_ausencia_row.py": (1, "_q(table, cols, ids): sus 4 callers pasan columnas planas"),
    "repositories/_asignacion_row.py": (1, "_q(table, cols, ids): sus 4 callers pasan columnas planas"),
    "repositories/empleado_roles_repo.py": (1, "select(campo): UNA columna de la whitelist CAMPOS_AUTOCOMPLETABLES"),
    "repositories/_evaluacion_lotes_enrich.py": (1, "tabla por parámetro, spec literal 'id, nombre' — sin embed"),
    # `_mapa(tabla, ids, campos, armar)`: los TRES callers de `build` verificados uno por uno —
    # "id, nombre, apellido" (empleados), "id, nombre" (empresas) y "id, nombre, apellido"
    # (users). Columnas planas, ningún embed. Existe justamente PARA no usar embeds: la FK a
    # `empleados` es COMPUESTA y un embed sobre ella es la clase de spec que termina en PGRST201.
    "repositories/_recategorizacion_row.py": (1, "_mapa(tabla, ids, campos): 3 callers con columnas planas"),
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


def test_el_barrido_resolvio_selects():
    """Guarda del test de columnas planas: sin specs RESUELTOS no hay nada que validar.

    Distinta de `test_el_barrido_encontro_selects`: aquella cuenta los `.select(` detectados,
    esta cuenta los que además se pudieron resolver a un (tabla, spec) concreto. Si la resolución
    de constantes se rompe, el conteo total no se mueve y la parametrización se vacía igual.
    """
    assert len(RESUELTOS) >= MINIMO_RESUELTOS, (
        f"el barrido resolvió {len(RESUELTOS)} selects y el mínimo es {MINIMO_RESUELTOS}: se "
        "rompió la RESOLUCIÓN (constantes, f-strings o imports), no desaparecieron los selects")


def test_el_barrido_recorrio_los_archivos():
    """Guarda sobre la superficie: detecta que un directorio entero deje de barrerse.

    Los conteos de selects no la cubren: si `repositories/` sale de DIRECTORIOS, los de
    `services/` solos podrían todavía superar un mínimo mal elegido. El conteo de ARCHIVOS cae
    de una forma que no se puede compensar.
    """
    assert len(ARCHIVOS) >= MINIMO_ARCHIVOS, (
        f"el barrido recorrió {len(ARCHIVOS)} archivos con selects y el mínimo es "
        f"{MINIMO_ARCHIVOS}: probablemente un directorio de DIRECTORIOS dejó de existir o de "
        "matchear. Un directorio que no se lee no da error, da cero.")


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


@pytest.mark.parametrize("sel", RESUELTOS, ids=lambda s: s.ubicacion)
def test_cada_select_pide_columnas_que_existen(sel):
    """🔴 EL TEST QUE CIERRA EL HUECO DE LAS COLUMNAS PLANAS (ver el cuarto caso, arriba).

    Valida TODO select resuelto —con embed y sin él— contra `db/schema.sql`. Una columna que no
    existe hace que PostgREST responda 400 42703 y la consulta entera muera: no faltan tres
    campos en la respuesta, no hay respuesta. Y como el fake de la suite acepta cualquier spec,
    el único síntoma es una pantalla vacía en producción.

    ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE PUEDA FALLAR? Que un select nombre una columna
    inexistente. Verificado por mutación en las tres superficies —`services/`, `repositories/` y
    los directorios de prevención— y, sobre todo, con un select SIN EMBED: esa mutación pasaba en
    verde con el predicado viejo (`CON_EMBED`) y es la que justifica este test.
    """
    schema = cargar_schema()
    try:
        schema.validar_select(sel.tabla, sel.spec)
    except SelectInvalidoError as exc:
        pytest.fail(f"{sel.ubicacion} — select inválido sobre '{sel.tabla}':\n  {exc}")


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

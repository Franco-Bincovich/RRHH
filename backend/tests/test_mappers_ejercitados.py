"""
BARRIDO ESTRUCTURAL — todo mapper que se corta con `if not <x>: return []` tiene que estar
declarado: o lo ejercita un test CON elementos, o se dice por qué no.

## La clase de error que cierra

Un mapper que abre con `if not rows: return []` y solo se llama con `[]` **no ejecuta una sola
línea de su cuerpo**. Tiene tests, aparece en verde, y está sin probar. Ahí vivió el `NameError`
de `_TA` en `_ausencia_row`, que iba a reventar el listado entero con la primera ausencia cargada
(`solicitudes_ausencia` está en 0 y por eso nunca se vio).

Medido instrumentando la suite el 9/8/2026: de los **22** mappers con este patrón, 9 seguían sin
ejercitarse. Se cubrieron los **5 que importaban** —los 3 con datos HOY en producción
(`evaluacion_resultados` 307, `auditoria` 143, `proyecto_asignaciones` 31) y los 2 del bloque I
(vacaciones e inventario)—. **Quedan 4, todos con su tabla en 0 y declarados abajo con el
disparador que los volvería urgentes.**

🔴 **La tabla de abajo ya tuvo un error que costó caro y conviene no repetir:**
`evaluacion_repo.find_resultados_por_evaluados` estaba declarado como *"módulo ev_* congelado"*.
Es falso. `evaluacion_repo` es el módulo NUEVO de resultados importados
(`evaluacion_lotes`/`_evaluados`/`_resultados`), completo y en producción; el congelado es `ev_*`
(`ev_ciclos`, `ev_plantillas`, `ev_instancias`), que son OTRAS tablas y están en 0. La confusión
dejó al mapper con más datos de todo el sistema declarado como intocable. **Antes de declarar algo
como congelado, mirar la tabla que lee, no el prefijo del módulo.**

## 🔴 QUÉ PRUEBA ESTE BARRIDO Y QUÉ NO — leerlo antes de confiar

**Prueba** que ningún mapper con el patrón puede aparecer sin que alguien decida qué hacer con él:
el descubrimiento es por AST sobre `repositories/` entero, así que uno nuevo rompe el test hasta
que se lo declare. También prueba que la declaración no miente sobre su existencia — un test
declarado que no menciona al mapper, o un mapper declarado que ya no existe, rojean.

**NO prueba** que la lista con que se lo llamó fuera no vacía: eso es dinámico y no se puede leer
del código. Lo garantizan los tests de cada mapper con su propio
`test_la_lista_vacia_no_prueba_nada`, que es exactamente el molde que este barrido obliga a
escribir. Es la misma clase de proxy que acepta `test_limite_export`, que verifica con
`inspect.getsource` que `verificar_limite_export` se INVOQUE, no que se invoque bien.

**Por qué no se hizo dinámico**, que sería la medición real: exigiría envolver los 22 mappers
durante toda la sesión de pytest y afirmar al final, y entonces `pytest tests/un_archivo.py`
fallaría siempre —ningún subconjunto ejercita los 22—. Un barrido que solo sirve corriendo la
suite entera se termina desactivando. La medición dinámica queda como diagnóstico reproducible:
un plugin que envuelve lo que devuelve `descubrir()` y reporta el largo máximo por mapper.
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

from pathlib import Path  # noqa: E402

from tests._mappers_early_return import descubrir  # noqa: E402

_TESTS = Path(__file__).resolve().parent

# Guarda contra el falso verde: si la detección por AST se rompiera, `descubrir()` devolvería {}
# y TODO pasaría sin haber mirado nada. Hoy son 22; el mínimo va holgado para que no sea ruido
# cada vez que alguien borra un repo.
_MINIMO_MAPPERS = 18


# ── mapper → módulo de test que lo ejercita CON elementos ─────────────────────
_EJERCITADOS: dict[str, str] = {
    "_ausencia_row._build":                     "test_ausencia_row",
    "_objetivo_row._build":                     "test_objetivo_row",
    "_proyectos_enrich.enriquecer":             "test_proyectos_enrich",
    "_proyectos_enrich.batch_costos":           "test_proyectos_enrich",
    "_inventario_items_row._build":             "test_inventario_filtro_area",
    "_evaluacion_lotes_enrich.enriquecer_lotes": "test_evaluacion_lotes_historial",
    # Los tres de abajo se ejercitan TRANSITIVAMENTE, por su caller: `_nombres` y
    # `_nombres_usuarios` desde `enriquecer_lotes`; `_insert_completo` desde
    # `crear_evaluados`/`crear_resultados`; `_scores_por_empleado` desde el análisis batch.
    # Por eso el vínculo se verifica contra el MÓDULO del mapper y no solo contra su nombre.
    "_evaluacion_lotes_enrich._nombres":        "test_evaluacion_lotes_historial",
    "_evaluacion_lotes_enrich._nombres_usuarios": "test_evaluacion_lotes_historial",
    "evaluacion_repo._insert_completo":         "test_evaluacion_repo_inserts",
    "nomina_import_repo.batch_upsert_nomina":   "test_import_costos_auditoria",
    "sucesion_repo._scores_por_empleado":       "test_sucesion_analisis_batch",
    # Los tres con DATOS HOY en producción (307 / 143 / 31 filas), cubiertos el 9/8/2026.
    "evaluacion_repo.find_resultados_por_evaluados": "test_mappers_con_datos",
    "audit_repo._build":                        "test_mappers_con_datos",
    "proyecto_asignaciones_repo._build":        "test_mappers_con_datos",
    # Los dos que van a tener datos en el BLOQUE I (vacaciones / inventario de prueba). Se
    # cubren ANTES de que haya datos a propósito: es la situación exacta en la que estaba
    # `_ausencia_row` cuando se le encontró el NameError.
    "_vacaciones_utils.enriquecer":             "test_mappers_bloque_i",
    "inventario_asignaciones_repo._build":      "test_mappers_bloque_i",
    # 🚩 Su declaración decía "se mueve a urgente con la primera vacante con candidatos". Esa
    # sesión llegó el 9/8/2026 con la ingesta de CVs por mail: la declaración se borró y el test
    # se escribió. Es el ciclo que la lista pretende — cada entrada que se va es un cuerpo probado.
    "vacante_repo.find_by_ids":                 "test_mappers_con_datos",
    # 🚩 Su declaración estaba en _SIN_EJERCITAR como `horas_repo._build`, con el motivo "depende
    # del link público de carga de horas (E4), EN PAUSA esperando la reunión de definición". Esa
    # reunión llegó: la migración 103 abrió la carga directa y el mapper se mudó a `_hora_row.py`
    # (horas_repo quedaba en 118/100). La entrada NO se borró — se MOVIÓ acá, que es lo que la
    # doctrina del repo pide para que la aserción restante no se quede sin nada que mirar.
    # `_mapa` se ejercita TRANSITIVAMENTE desde `build`, igual que los `_nombres` de arriba.
    "_hora_row.build":                          "test_horas_carga_directa",
    "_hora_row._mapa":                          "test_horas_carga_directa",
}

# ── mapper → por qué NO se ejercita todavía ───────────────────────────────────
# 🚩 Esto NO es una lista de excepciones permanentes: es la deuda, visible. Cada entrada que se
# borra es un cuerpo de mapper que pasó a estar probado. El orden de prioridad lo da si la tabla
# tiene datos en producción — un mapper con datos reales es una bomba con la mecha encendida.
# Los DOS que quedan tienen su tabla en 0 filas Y no entran en el bloque I. Cada razón dice
# QUÉ los movería a urgente, para que la decisión no haya que rehacerla desde cero.
_SIN_EJERCITAR: dict[str, str] = {
    "capacitacion_repo._build":
        "capacitaciones: 0 filas y NO entra en el bloque I (que es vacaciones, ausencias e "
        "inventario). Disparador: que RRHH cargue el primer catálogo de capacitaciones.",
    "asignacion_repo._build":
        "empleado_capacitacion: 0 filas. Cuelga de capacitaciones, así que se mueve con ella.",
}


def _declarados() -> dict:
    return {**_EJERCITADOS, **_SIN_EJERCITAR}


def test_el_barrido_encontro_mappers() -> None:
    """GUARDA CONTRA EL FALSO VERDE: sin esto, una detección rota pasaría en el vacío."""
    encontrados = descubrir()
    assert len(encontrados) >= _MINIMO_MAPPERS, (
        f"la detección por AST encontró {len(encontrados)} mappers (mínimo {_MINIMO_MAPPERS}): "
        "se rompió, no es que hayan desaparecido.")


def test_ningun_mapper_sin_declarar() -> None:
    """🔴 EL BARRIDO. Un mapper nuevo con el patrón no puede pasar inadvertido.

    ¿Qué tendría que ser distinto para que falle? Nada del test: falla sola en cuanto alguien
    agregue un `if not rows: return []` en `repositories/` sin decidir si lo prueba o no.
    """
    nuevos = sorted(set(descubrir()) - set(_declarados()))
    assert not nuevos, (
        f"Mappers con early-return sin declarar: {nuevos}.\n"
        "Su cuerpo NO se ejecuta si se los llama con una lista vacía: un test que solo haga eso "
        "los deja sin probar. Escribile un test con elementos (molde: test_ausencia_row.py) y "
        "declaralo en _EJERCITADOS, o declaralo en _SIN_EJERCITAR CON su razón.")


def test_ninguna_declaracion_apunta_a_un_mapper_que_ya_no_existe() -> None:
    """Dirección inversa: una declaración muerta es ruido que esconde el próximo caso.
    Mismo criterio que `test_las_excepciones_siguen_sin_caller`."""
    muertas = sorted(set(_declarados()) - set(descubrir()))
    assert not muertas, (
        f"Declaraciones que ya no corresponden a ningún mapper: {muertas}. Se borraron o "
        "perdieron su early-return: sacá la entrada.")


def test_un_mapper_no_puede_estar_en_las_dos_listas() -> None:
    solapados = sorted(set(_EJERCITADOS) & set(_SIN_EJERCITAR))
    assert not solapados, f"declarados como ejercitados Y sin ejercitar: {solapados}"


def test_los_tests_declarados_existen_y_mencionan_su_mapper() -> None:
    """La declaración no puede ser una promesa vacía: se verifica el vínculo.

    No prueba que la lista fuera no vacía —eso es dinámico, ver el encabezado—, pero sí que el
    test exista y hable de ese mapper. Un copy-paste que apunte al módulo equivocado rojea.

    ⚠️ Acepta la mención del MÓDULO además de la de la función: varios mappers se ejercitan
    transitivamente por su caller (`_nombres` vía `enriquecer_lotes`, `_insert_completo` vía
    `crear_resultados`), y exigir el nombre exacto obligaría a declarar el caller en vez de la
    cosa — menos informativo y más frágil.
    """
    faltantes = []
    for mapper, modulo in sorted(_EJERCITADOS.items()):
        archivo = _TESTS / f"{modulo}.py"
        if not archivo.exists():
            faltantes.append(f"{mapper} → {modulo}.py NO EXISTE")
            continue
        origen, funcion = mapper.split(".", 1)
        texto = archivo.read_text(encoding="utf-8")
        if funcion not in texto and origen not in texto:
            faltantes.append(f"{mapper} → {modulo}.py no menciona ni `{funcion}` ni `{origen}`")
    assert not faltantes, "Declaraciones que no se sostienen:\n  " + "\n  ".join(faltantes)

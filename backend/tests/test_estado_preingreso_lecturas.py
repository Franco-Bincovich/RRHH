"""
🔴 BARRIDO ESTRUCTURAL — el inventario declarado de TODA comparación sobre `empleados.estado`.

## ¿Qué tendría que ser distinto para que este barrido rojee?

**Que alguien agregue, borre o cambie de criterio una comparación sobre `empleados.estado`.**
No hace falta que la escriba mal: alcanza con que no la declare acá. Se verificó a mano
agregando un `.eq("estado", "activo")` temporal en un service y confirmando el rojo (el
experimento está en la bitácora de la sesión). Las comparaciones se DESCUBREN por AST
(`tests/_barrido_estado.py`), nunca de una lista escrita a mano, así que un archivo nuevo entra
al barrido solo.

## Por qué hace falta un barrido y no alcanzaba con arreglar los sitios

Con los 31 empleados de producción en `activo`, `= 'activo'`, `!= 'baja'` y "sin filtro" daban
**el mismo conjunto**. La migración 120 rompió esa coincidencia y el diagnóstico encontró **23
comparaciones** repartidas en cuatro criterios distintos, dos de ellas mal. Arreglar esas dos no
cierra nada: la próxima lectura nace con el mismo problema, y el modo de falla no es una
excepción sino **un número más grande**, que nadie puede verificar a ojo.

## Los tres criterios que conviven, y por qué NO se unifican

| criterio | pregunta | dónde |
|---|---|---|
| `= 'activo'` | "¿está disponible HOY?" | 15 sitios — KPIs, denominadores, organigrama, saldos |
| `in_(ESTADOS_EN_PLANTILLA)` | "¿pertenece a la dotación?" | 2 sitios — conteo por área, sucesión |
| `!= 'preingreso'` | "¿este HECHO ocurrió?" | 4 contadores de altas + el default del listado |

Son tres preguntas distintas y **unificarlas sería el bug**. El caso que lo prueba: quien entró
en marzo y se fue en julio sale de `ESTADOS_EN_PLANTILLA` pero **sigue siendo un alta de marzo**.
Ver `utils/estados_empleado.py`, que es donde vive el razonamiento completo.

## Lo que este barrido NO cubre (declarado, no olvidado)

· **Las ESCRITURAS** de `estado` (`_empleado_write_repo.guardar` fuerza `'activo'`,
  `dar_de_baja` escribe `'baja'`). Son asignaciones, no comparaciones; las cubre
  `tests/test_offboarding_baja_efectiva.py`.
· **`EmpleadoUpdate.estado`**, que es `Optional[str]` sin validar y hoy acepta cualquier valor
  del CHECK. Es el único camino que puede producir un preingreso, y habilitarlo es A3.2.
"""
from collections import Counter

from tests._barrido_estado import (
    INDETERMINADA, RAIZ, TABLA_EMPLEADOS, archivos, hallazgos_python, hallazgos_query,
)

# ── Inventario declarado: (archivo, método, valor) → (cantidad, criterio) ───────────────────
# El VALOR es el literal comparado, o el NOMBRE de la constante cuando se usa una compartida:
# "usa ESTADOS_EN_PLANTILLA" es un criterio distinto de "enumera tres strings a mano".
_A = "¿está disponible HOY? — grupo A, correcto sin tocar: un preingreso no es 'activo'"
_PLANTILLA = "¿pertenece a la dotación? — licencia SÍ, preingreso NO, baja NO"
_ALTA = "¿este HECHO ocurrió? — complemento: 'baja' queda del lado que cuenta"
_BAJA = "¿esta persona se fue? — la fecha sola no alcanza para ser una baja"

_DECLARADAS: dict = {
    ("repositories/_area_row.py", "in_", "ESTADOS_EN_PLANTILLA"): (1, _PLANTILLA),
    ("repositories/empleado_roles_repo.py", "eq", "activo"): (1, _A),
    ("repositories/sucesion_repo.py", "eq", "activo"): (1, _A),
    ("repositories/sucesion_repo.py", "in_", "ESTADOS_EN_PLANTILLA"): (1, _PLANTILLA),
    ("services/_dashboard_alertas.py", "eq", "activo"): (1, _A),
    ("services/_dashboard_headcount.py", "eq", "activo"): (1, _A),
    ("services/_dashboard_kpis.py", "eq", "activo"): (2, _A),
    ("services/_reporte_anual_metricas.py", "eq", "activo"): (1, _A),
    ("services/dashboard_service.py", "kwarg", "activo"): (1, _A),
    ("services/dashboard_service.py", "neq", "ESTADO_PREINGRESO"): (1, _ALTA),
    ("services/dashboard_service.py", "eq", "baja"): (1, _BAJA),
    ("services/organigrama_service.py", "eq", "activo"): (1, _A),
    ("services/reporte_adhoc.py", "eq", "activo"): (1, _A),
    ("services/reportes/_reporte_ausentismo.py", "eq", "activo"): (1, _A),
    ("services/reportes/_reporte_distribucion.py", "eq", "activo"): (1, _A),
    ("services/reportes/_reporte_dotacion.py", "eq", "activo"): (2, _A),
    ("services/reportes/_reporte_dotacion.py", "neq", "ESTADO_PREINGRESO"): (2, _ALTA),
    ("services/reportes/_reporte_dotacion.py", "eq", "baja"): (1, _BAJA),
    ("services/reportes/_reporte_movimientos.py", "neq", "ESTADO_PREINGRESO"): (1, _ALTA),
    ("services/reportes/_reporte_movimientos.py", "eq", "baja"): (1, _BAJA),
    ("services/reportes/_reporte_saldos.py", "eq", "activo"): (1, _A),
}

# ── Las que el AST no puede atribuir a una tabla, con la tabla REAL de cada una ─────────────
# No se filtran por "no pude resolver": eso perdería en silencio las más indirectas, que son las
# que más fácil se escapan. Cada una se declara a mano. Ver el encabezado de `_barrido_estado`.
_INDETERMINADAS: dict = {
    # Recibe la query por parámetro (`filtro_estado(q, estado)`) → la cadena no llega al .table().
    ("repositories/_empleado_row.py", "neq", "ESTADO_PREINGRESO"): (1, "empleados"),
    ("repositories/_empleado_row.py", "eq", "estado"): (1, "empleados"),
    # Todo lo de abajo es de OTRA tabla: ruido conocido, no empleados.
    ("repositories/_objetivo_filtros.py", "eq", "<expr>"): (1, "objetivos"),
    ("repositories/asignacion_repo.py", "eq", "estado"): (1, "empleado_capacitacion"),
    ("repositories/inventario_items_repo.py", "eq", "estado"): (1, "inventario_items"),
    ("repositories/mail_enviado_repo.py", "eq", "estado"): (1, "mail_enviado"),
    ("repositories/offboarding_repo.py", "in_", "_EXCL"): (2, "offboarding_instancias"),
    ("repositories/onboarding_repo.py", "in_", "EXCLUIDOS"): (2, "onboarding_instancias"),
    ("repositories/planes_carrera_repo.py", "eq", "activo"): (2, "planes_carrera"),
    ("repositories/proyectos_repo.py", "eq", "estado"): (1, "proyectos"),
    ("repositories/vacante_repo.py", "eq", "estado"): (1, "vacantes"),
    # Recibe la tabla como ARGUMENTO: sirve a objetivos y a otras familias.
    ("services/procesos_service.py", "eq", "estado"): (1, "parámetro en runtime"),
    # ESCRITURA, no lectura: `EmpleadoUpdate(estado="activo")` del pase de preingreso a activo.
    # Cae acá porque el kwarg no cuelga de ningún `.table()`. El barrido de ESCRITURAS
    # (`test_estado_preingreso_escrituras.py`) la declara además como uno de los 5 caminos.
    ("services/_empleado_activar.py", "kwarg", "activo"): (1, "empleados"),
}

# ── Comparaciones en Python contra un literal del CHECK ─────────────────────────────────────
_PYTHON: dict = {
    ("services/_identificacion_resolver.py", "activo"):
        (1, "link público de horas: != 'activo' → rechaza también al preingreso. 🔴 El motivo "
            "que loguea sigue siendo 'inactivo' y NO distingue al preingreso: darle uno propio "
            "exige ensanchar el CHECK de intentos_identificacion.resultado (migración 121, "
            "pendiente). Ver DEUDA-TECNICA."),
    ("services/_offboarding_efectivizar.py", "baja"):
        (1, "¿ya se fue? — 409 EMPLEADO_YA_DE_BAJA"),
    ("services/_offboarding_efectivizar.py", "ESTADO_PREINGRESO"):
        (1, "¿todavía no entró? — 409 EMPLEADO_PREINGRESO, ANTES de _validar_fecha (A3.2)"),
    ("services/asignaciones_service.py", "ESTADOS_EN_PLANTILLA"):
        (1, "¿puedo asignarlo a un proyecto? — pasó de '¿es baja?' a '¿está en plantilla?'"),
    ("services/asignaciones_service.py", "ESTADO_PREINGRESO"):
        (1, "desempate del anterior: código propio EMPLEADO_PREINGRESO, no el de baja"),
    ("services/_empleado_activar.py", "ESTADO_PREINGRESO"):
        (1, "solo se activa un preingreso — 409 EMPLEADO_NO_ES_PREINGRESO"),
}


def _conteo(hallazgos, filtro) -> Counter:
    return Counter((h.archivo, h.metodo, h.valor) for h in hallazgos if filtro(h))


class TestElInventarioEstaCompleto:
    """Las dos direcciones: nada sin declarar, y ninguna declaración muerta."""

    def test_no_hay_comparaciones_de_empleados_sin_declarar(self) -> None:
        hallado = _conteo(hallazgos_query(), lambda h: h.tabla == TABLA_EMPLEADOS)
        esperado = Counter({k: v[0] for k, v in _DECLARADAS.items()})
        assert hallado == esperado, (
            "Cambió el mapa de comparaciones sobre `empleados.estado`.\n"
            f"  de más (sin declarar): {hallado - esperado}\n"
            f"  de menos (declaradas y ausentes): {esperado - hallado}\n"
            "Si agregaste una lectura, declarala acá CON su criterio. Si la sacaste, sacá la "
            "entrada. Una declaración muerta oculta el próximo caso."
        )

    def test_no_hay_indeterminadas_sin_declarar(self) -> None:
        hallado = _conteo(hallazgos_query(), lambda h: h.tabla == INDETERMINADA)
        esperado = Counter({k: v[0] for k, v in _INDETERMINADAS.items()})
        assert hallado == esperado, (
            "Apareció una comparación cuya tabla el AST no puede resolver y que nadie declaró. "
            "Averiguá a qué tabla apunta y declarala: si es `empleados`, además hay que decidir "
            "su criterio.\n"
            f"  de más: {hallado - esperado}\n  de menos: {esperado - hallado}"
        )

    def test_no_hay_comparaciones_python_sin_declarar(self) -> None:
        hallado = _conteo(hallazgos_python(), lambda _h: True)
        esperado = Counter({(a, "python", v): c for (a, v), (c, _m) in _PYTHON.items()})
        assert hallado == esperado, (
            f"de más: {hallado - esperado}\nde menos: {esperado - hallado}"
        )


class TestLasGuardasDeMinimo:
    """Sin esto, una extracción rota devolvería 0 hallazgos y TODO pasaría en el vacío."""

    def test_el_barrido_recorre_el_backend_de_verdad(self) -> None:
        assert len(archivos()) >= 250

    def test_encuentra_comparaciones(self) -> None:
        assert len(hallazgos_query()) >= 40
        assert len(hallazgos_python()) >= 3

    def test_hay_comparaciones_de_otras_tablas_y_se_ignoran(self) -> None:
        """La contracara: si el barrido dejara de ver las otras tablas, el filtro por tabla
        estaría descartando de más y las de `empleados` podrían caerse con él."""
        otras = [h for h in hallazgos_query()
                 if h.tabla not in (TABLA_EMPLEADOS, INDETERMINADA)]
        assert len(otras) >= 8, "el resolvedor de tabla dejó de resolver: revisá `_tabla_de`"


class TestLosCriteriosSiguenSiendoLosQueSon:
    """Ancla SEMÁNTICA, no de conteo: qué pregunta hace cada grupo. Un cambio de criterio que
    conservara la cantidad de comparaciones pasaría los tests de arriba y rojearía acá."""

    def test_el_grupo_a_son_quince_y_preguntan_por_activo(self) -> None:
        """Los 15 quedaron correctos GRATIS con la migración 120 (un preingreso no es 'activo').
        Que sigan siendo 15 es lo que dice que nadie los "arregló" de más."""
        grupo_a = sum(c for (_f, _m, v), (c, cr) in _DECLARADAS.items() if cr is _A)
        assert grupo_a == 15
        assert all(v == "activo" for (_f, _m, v), (_c, cr) in _DECLARADAS.items() if cr is _A)

    def test_los_dos_sitios_de_plantilla_usan_la_constante_compartida(self) -> None:
        """Enumerar los tres strings a mano acá volvería a dejar el conjunto definido por
        omisión en dos lugares distintos, que es de donde salió el bug."""
        plantilla = [(f, v) for (f, _m, v), (_c, cr) in _DECLARADAS.items() if cr is _PLANTILLA]
        assert sorted(f for f, _v in plantilla) == [
            "repositories/_area_row.py", "repositories/sucesion_repo.py",
        ]
        assert all(v == "ESTADOS_EN_PLANTILLA" for _f, v in plantilla)

    def test_los_cuatro_contadores_de_altas_excluyen_preingreso(self) -> None:
        """Cuatro y no cinco: el quinto contador por fecha es el de BAJAS, que va por el eje
        contrario y lleva `= 'baja'` (criterio `_BAJA`), no el complemento."""
        altas = sum(c for (_f, _m, _v), (c, cr) in _DECLARADAS.items() if cr is _ALTA)
        assert altas == 4
        assert all(v == "ESTADO_PREINGRESO"
                   for (_f, _m, v), (_c, cr) in _DECLARADAS.items() if cr is _ALTA)

    def test_el_default_del_listado_vive_en_un_solo_lugar(self) -> None:
        """Listado y export comparten `filtro_estado`; dos copias divergirían sin avisar."""
        assert ("repositories/_empleado_row.py", "neq", "ESTADO_PREINGRESO") in _INDETERMINADAS
        assert _INDETERMINADAS[("repositories/_empleado_row.py", "neq",
                                "ESTADO_PREINGRESO")][1] == "empleados"


class TestLaProsaNoCuenta:
    """Molde: `test_storage_punto_unico.py`. Media docena de docstrings escriben `estado='baja'`
    para explicar el bug que ese módulo arregló. Si el barrido los contara, la reacción sería
    BORRARLOS para limpiar el rojo — y son justo los comentarios que no hay que perder."""

    def test_un_docstring_que_nombra_un_estado_no_es_un_hallazgo(self) -> None:
        con_prosa = "repositories/_empleado_write_repo.py"
        fuente = (RAIZ / con_prosa).read_text(encoding="utf-8")
        # La guarda va primero: sin ella, el día que ese docstring se reescriba este test
        # afirmaría "no hay hallazgos" sobre un archivo que ya no tiene la prosa que motivaba
        # la pregunta, y pasaría sin haber comparado nada.
        assert "estado='baja'" in fuente, \
            "cambió el archivo de referencia; elegí otro que nombre un estado en prosa"
        assert not [h for h in hallazgos_query() + hallazgos_python() if h.archivo == con_prosa]

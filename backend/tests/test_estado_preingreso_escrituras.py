"""
🔴 BARRIDO ESTRUCTURAL — el inventario declarado de TODA escritura de `empleados.estado`.

Hermano de `test_estado_preingreso_lecturas.py`, que cubre las COMPARACIONES. Ese barrido
declara en su propio encabezado que **no cubre escrituras**; esto lo cierra.

## ¿Qué tendría que ser distinto para que este barrido rojee?

**Que aparezca, desaparezca o cambie de forma un camino que escribe `empleados.estado`.** Se
verificó en las dos direcciones —agregando una escritura temporal y borrando una declarada— y
las dos rojean; el experimento está en la bitácora de la sesión.

## Por qué importa tener el inventario, y no solo los tests de comportamiento

`estado` es el campo que decide si una persona existe para el sistema: entra o no en el
headcount, en los denominadores de ausentismo, en el organigrama, en los saldos de vacaciones y
en el gate del link público de horas. **Cada camino que lo escribe es un lugar donde puede
nacer un estado sin las guardas que le corresponden**, y el modo de falla no es una excepción:
es un número que sale distinto y que nadie puede verificar a ojo.

## Los CINCO caminos, y las dos piezas de infraestructura que los sostienen

| camino | forma | guardas |
|---|---|---|
| **alta** | `EmpleadoCreate.estado` (default) | el propio Literal: solo `activo`/`preingreso` |
| **PUT** | `EmpleadoUpdate.estado` | el Literal de los 5 del CHECK — **y NADA más** |
| **activar** | `EmpleadoUpdate(estado="activo")` | es preingreso · la fecha de ingreso ya ocurrió |
| **efectivizar** | `dar_de_baja(...)` | instancia abierta · no es baja · no es preingreso · fecha |
| **nómina** | `dar_de_baja(...)` | 🔴 **NINGUNA** — ver la nota abajo |

🔴 **EL PUT NO TIENE MÁS GUARDA QUE EL TIPO, Y ESO ES DELIBERADO PERO NO GRATIS.** Puede llevar
a cualquiera a cualquier estado del CHECK sin verificar nada: puede volver un `activo` a
`preingreso`, o pasar un `preingreso` a `activo` **salteándose la guarda de fecha que
`_empleado_activar` existe para aplicar**. Es la corrección manual de un dato mal cargado, y por
eso existe; pero mientras el botón de activar no esté en la UI (bloque B), es también el único
camino disponible, que es exactamente lo que no queremos que se vuelva costumbre.

🔴 **NÓMINA ESCRIBE `baja` SIN NINGUNA GUARDA DE ESTADO.** `nomina_empleados_service` llama a
`dar_de_baja` con solo mirar si la fila del CSV trae `Fecha Baja`. Un preingreso que aparezca en
el archivo con esa columna cargada pasa a `baja` sin pasar por ninguna de las guardas de
`_offboarding_efectivizar`. Está declarado acá, con su razón, **y NO se arregló en A3.2 a
propósito**: cambiarlo altera el comportamiento de un import que RRHH corre todos los meses, y
esa es una decisión de producto, no un bug de tipos. Ver `docs/DEUDA-TECNICA.md`.
"""


from tests._barrido_escrituras_estado import escrituras

# ── Los CINCO caminos ───────────────────────────────────────────────────────────────────────
_CAMINOS: dict = {
    ("schemas/empleado.py", "campo", "EmpleadoCreate.estado = 'activo'"):
        "ALTA — POST /api/empleados. El Literal acota a activo|preingreso.",
    ("schemas/empleado.py", "campo", "EmpleadoUpdate.estado = None"):
        "PUT — edición del legajo. El Literal acota a los 5 del CHECK y no valida NADA más.",
    ("services/_empleado_activar.py", "kwarg", "EmpleadoUpdate(estado='activo')"):
        "ACTIVAR — POST /api/empleados/{id}/activar. Tres guardas, la de fecha es el corazón.",
    ("services/_offboarding_efectivizar.py", "dar_de_baja", "empleado_repo.dar_de_baja"):
        "EFECTIVIZAR — POST /api/offboarding/{id}/efectivizar. Cuatro guardas.",
    ("services/nomina_empleados_service.py", "dar_de_baja", "self._emp_repo.dar_de_baja"):
        "NÓMINA — import mensual. 🔴 SIN guarda de estado (ver el encabezado).",
}

# ── Las dos piezas de infraestructura que los caminos atraviesan ────────────────────────────
# No son caminos: no los dispara nadie de afuera. Se declaran igual porque son donde la
# escritura OCURRE, y borrarlas o cambiarlas afecta a los cinco de arriba a la vez.
_INFRAESTRUCTURA: dict = {
    ("repositories/_empleado_write_repo.py", "dict",
     "{'estado': 'baja', 'fecha_egreso': str(fecha_egreso)}"):
        "la ÚNICA escritura física de 'baja', y por eso siempre lleva la fecha.",
    ("repositories/empleado_repo.py", "dar_de_baja", "dar_de_baja"):
        "el delegador del repo hacia _empleado_write_repo. No es un caller de negocio.",
}

# ── Ruido conocido: escriben `estado` de OTRA tabla ─────────────────────────────────────────
# Llegan acá porque su `.table(X)` toma la constante de un import y el resolvedor no la puede
# atribuir. Se declaran una por una en vez de filtrarlas por heurística: una regla que las
# descartara sola podría descartar también una de `empleados` sin que nadie lo note.
_OTRAS_TABLAS: dict = {
    ("repositories/assessment_campanas_repo.py", "dict", "{'estado': 'completado'}"):
        "assessment_links",
    ("repositories/assessment_resultados_repo.py", "dict", "{'estado': 'completado'}"):
        "assessment_links",
    ("repositories/offboarding_repo.py", "dict", None): "offboarding_instancias",
    ("repositories/onboarding_repo.py", "dict", None): "onboarding_instancias / _progreso",
    ("repositories/planes_carrera_repo.py", "dict", None): "planes_carrera_hitos",
}


def _declarado(archivo: str, forma: str, detalle: str) -> bool:
    """`detalle=None` en las declaraciones de otras tablas: ahí el contenido del dict no aporta
    y ataría el test al formato exacto que devuelve `ast.unparse`."""
    if (archivo, forma, detalle) in _CAMINOS or (archivo, forma, detalle) in _INFRAESTRUCTURA:
        return True
    return (archivo, forma, detalle) in _OTRAS_TABLAS or (archivo, forma, None) in _OTRAS_TABLAS


class TestElInventarioDeEscriturasEstaCompleto:

    def test_ninguna_escritura_sin_declarar(self) -> None:
        sin_declarar = sorted({(e.archivo, e.forma, e.detalle) for e in escrituras()
                               if not _declarado(e.archivo, e.forma, e.detalle)})
        assert not sin_declarar, (
            "Apareció un camino que escribe `empleados.estado` y que nadie declaró:\n  "
            + "\n  ".join(map(str, sin_declarar))
            + "\nSi es de `empleados`, declaralo en _CAMINOS CON sus guardas. Si es de otra "
              "tabla, en _OTRAS_TABLAS con el nombre real de la tabla."
        )

    def test_ninguna_declaracion_muerta(self) -> None:
        """La otra dirección: una entrada que ya no apunta a nada es ruido que tapa el próximo
        caso. Se comprueba solo sobre _CAMINOS e _INFRAESTRUCTURA, que son exactos."""
        presentes = {(e.archivo, e.forma, e.detalle) for e in escrituras()}
        muertas = sorted((set(_CAMINOS) | set(_INFRAESTRUCTURA)) - presentes)
        assert not muertas, f"Declaradas y ausentes del código: {muertas}"


class TestSonExactamenteCincoCaminos:

    def test_hay_cinco_y_son_los_declarados(self) -> None:
        """El número es el ancla. Un sexto camino —un endpoint nuevo, otro import, un script—
        entra por acá y obliga a decidir qué guardas le tocan ANTES de estar en producción."""
        assert len(_CAMINOS) == 5

    def test_cada_camino_existe_en_el_codigo(self) -> None:
        presentes = {(e.archivo, e.forma, e.detalle) for e in escrituras()}
        faltan = sorted(set(_CAMINOS) - presentes)
        assert not faltan, f"Caminos declarados que ya no están en el código: {faltan}"

    def test_los_dos_caminos_de_baja_pasan_por_la_misma_escritura(self) -> None:
        """Efectivizar y nómina llaman a `dar_de_baja`, que es el único sitio que escribe
        'baja'. Es lo que garantiza que una baja SIEMPRE lleve `fecha_egreso`: una segunda
        escritura por su cuenta podría poner el estado sin la fecha, y esa persona se caería
        del headcount y del conteo de bajas de todos los meses a la vez."""
        callers = {e.archivo for e in escrituras()
                   if e.forma == "dar_de_baja" and "repositories/" not in e.archivo}
        assert callers == {
            "services/_offboarding_efectivizar.py", "services/nomina_empleados_service.py",
        }


class TestLasGuardasDeMinimo:
    """Sin esto, una extracción rota devolvería 0 escrituras y todo pasaría en el vacío."""

    def test_el_barrido_encuentra_escrituras(self) -> None:
        assert len(escrituras()) >= 12

    def test_encuentra_las_cuatro_formas(self) -> None:
        """Si una forma dejara de detectarse, su camino desaparecería en silencio — y el de
        `campo` es el que más fácil se pierde: no contiene el string "estado" como valor."""
        assert {e.forma for e in escrituras()} == {"dict", "campo", "kwarg", "dar_de_baja"}

    def test_hay_ruido_de_otras_tablas_y_se_declara(self) -> None:
        """Contracara: si dejaran de aparecer, el filtro por tabla estaría descartando de más."""
        otras = [e for e in escrituras()
                 if (e.archivo, e.forma, None) in _OTRAS_TABLAS
                 or (e.archivo, e.forma, e.detalle) in _OTRAS_TABLAS]
        assert len(otras) >= 5

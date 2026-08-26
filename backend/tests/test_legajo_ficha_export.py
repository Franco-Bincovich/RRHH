"""
BARRIDO ESTRUCTURAL nº 51 — **el export de empleados es un SUPERCONJUNTO de la ficha**.

🔴 QUÉ CIERRA. Hasta el 25/8/2026 la ficha y el archivo divergían en **11 campos** y nada lo
vigilaba: la ficha mostraba tipo de documento, sexo, fecha de nacimiento, teléfono alternativo,
email alternativo, domicilio, estudios, ubicación, turno, organismo y perfil, y **ninguno de los
once salía en el export**. Alguien de Capital Humano que exporta para trabajar afuera perdía la
mitad del legajo sin que nada se lo dijera — que es el peor modo de falla de un export: el
archivo se abre, tiene filas, y le faltan columnas.

🔑 EL EJE ES EL **NOMBRE DEL CAMPO**, NO LA ETIQUETA, y por eso esto no es un espejo manual más.
Comparar "Tipo de documento" (la ficha) con "Tipo de documento" (el header del Excel) obligaría a
mantener una tabla de traducción a mano, que es exactamente la clase de artefacto que se pudre.
Los dos lados leen el MISMO objeto —`empleado.<campo>` en el TSX, `e.<campo>` en el dict del
export— así que el atributo es un hecho compartido y se puede comparar sin intermediarios.

⚠️ QUÉ **NO** PUEDE VER: si la etiqueta de una columna miente, o si el valor está mal formateado.
Ve presencia de campo, que es la mitad que se rompió. La otra la cubren los tests de la ficha.
"""
import ast
import re
from pathlib import Path

import pytest

_DIR_FICHA = (Path(__file__).resolve().parents[2] / "frontend" / "components" / "features"
              / "empleados" / "ficha")
# 🔴 LA UNIDAD "FICHA" SON CUATRO ARCHIVOS, NO UNO, y elegir mal la unidad daba siete falsos
# positivos medidos: `nombre`, `apellido` y `estado` viven en la BARRA DE IDENTIDAD (§3 del
# sistema de diseño los saca del panel a propósito), y las cuatro piezas del domicilio las
# consume `domicilioLegible`. Declararlos como excepciones habría escondido el hecho de que la
# ficha SÍ los muestra — una excepción que miente es peor que una que falta.
# No se barre la carpeta entera porque ahí también viven secciones auto-abastecidas (historial
# salarial, vacaciones, inventario, cesiones) que leen del empleado cosas que un export de
# legajo no tiene por qué traer: `id` para pedir sus propios datos, entre otras.
_FICHA = [
    _DIR_FICHA / "DatosEmpleadoSection.tsx",  # el panel: información personal + laboral
    _DIR_FICHA / "BarraIdentidad.tsx",        # nombre, apellido, rol y el chip de estado
    _DIR_FICHA / "_datosClave.ts",            # los cuatro datos clave de la barra
    _DIR_FICHA / "_domicilio.ts",             # arma el domicilio legible del panel
]
_EXPORT = Path(__file__).resolve().parents[1] / "services" / "_empleados_export.py"

# Campos que la ficha lee y que NO tienen columna propia en el export, cada uno con su razón.
# Una excepción sin razón es la que nadie revisa; una que apunte a un campo que la ficha ya no
# lee es ruido que tapa el próximo caso — el último test verifica las dos cosas.
FICHA_SIN_COLUMNA = {
    "cargo": "DEPRECADO (se dropea en S6). El export saca `Rol principal` de `roles[0]`, que es "
             "el reemplazo; sacar además la columna vieja sería exportar dos veces lo mismo.",
}

# Columnas del export que la ficha NO muestra. Al revés que las de arriba, éstas son las que hay
# que mirar con cuidado: el archivo afirma algo que la pantalla no.
EXPORT_SIN_FICHA = {
    "fecha_egreso": "La ficha resuelve la baja en su propia sección (AccionesFicha/Offboarding), "
                    "no como un campo más del panel laboral. En un listado sí es una columna.",
    "motivo_baja": "Ídem `fecha_egreso`.",
    "dias_vacaciones_asignados": "La ficha lo muestra en VacacionesSection, con el saldo al lado, "
                                 "que es donde el número significa algo.",
}


def _campos_ficha() -> set:
    """Los `empleado.<campo>` que el TSX de la ficha lee, con los comentarios enmascarados.

    Enmascarar no es opcional: el archivo explica EN PROSA por qué `potencial`/`desempeno` van en
    una sección propia y por qué salió `organismo`, y un barrido por texto plano contaría esas
    menciones como campos renderizados. Es el mismo cuidado que toman los barridos 20, 30 y 34.
    """
    campos = set()
    for archivo in _FICHA:
        src = archivo.read_text(encoding="utf-8")
        src = re.sub(r"\{/\*.*?\*/\}", "", src, flags=re.S)
        src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
        src = re.sub(r"//[^\n]*", "", src)
        # `empleado.` en el panel y la barra; `e.` en los dos helpers, que reciben el empleado
        # con ese nombre. Los dos patrones son el MISMO hecho: leer un campo del legajo.
        campos |= set(re.findall(r"\bempleado\.(\w+)", src))
        campos |= set(re.findall(r"\be\.(\w+)", src))
    return campos


def _campos_export() -> set:
    """Los `e.<campo>` del dict de `construir_filas_export`, por AST y no por grep."""
    arbol = ast.parse(_EXPORT.read_text(encoding="utf-8"))
    return {
        n.attr for n in ast.walk(arbol)
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "e"
    }


FICHA = _campos_ficha()
EXPORT = _campos_export()


def test_hay_algo_que_barrer_de_los_dos_lados():
    """Guarda de mínimo. Sin ella, un regex que deje de matchear devuelve dos conjuntos vacíos y
    todo lo de abajo pasa sin haber comparado nada — el modo de falla que este repo ya pagó."""
    assert len(FICHA) >= 25, f"la ficha solo dio {len(FICHA)} campos: el extractor se rompió"
    assert len(EXPORT) >= 30, f"el export solo dio {len(EXPORT)} campos: el extractor se rompió"


@pytest.mark.parametrize("campo", sorted(FICHA))
def test_todo_campo_de_la_ficha_sale_en_el_export(campo: str):
    """La dirección que importa: lo que la pantalla muestra, el archivo lo tiene."""
    if campo in FICHA_SIN_COLUMNA:
        pytest.skip(FICHA_SIN_COLUMNA[campo])
    assert campo in EXPORT, (
        f"la ficha muestra `{campo}` y el export no lo trae. Agregá la columna en "
        f"services/_empleados_export.py, o declaralo en FICHA_SIN_COLUMNA con su razón."
    )


@pytest.mark.parametrize("campo", sorted(EXPORT))
def test_toda_columna_del_export_esta_en_la_ficha(campo: str):
    """La dirección de vuelta: el archivo no afirma nada que la pantalla no muestre."""
    if campo in EXPORT_SIN_FICHA:
        pytest.skip(EXPORT_SIN_FICHA[campo])
    if campo == "roles":
        pytest.skip("la ficha lo muestra unido por comas en el campo `Rol`.")
    assert campo in FICHA, (
        f"el export trae `{campo}` y la ficha no lo muestra. Agregalo a la ficha, o declaralo "
        f"en EXPORT_SIN_FICHA con su razón."
    )


@pytest.mark.parametrize("campo", sorted(FICHA_SIN_COLUMNA) + sorted(EXPORT_SIN_FICHA))
def test_ninguna_excepcion_apunta_a_un_campo_que_ya_no_existe(campo: str):
    """Una excepción muerta es ruido que oculta el próximo caso real."""
    assert campo in FICHA or campo in EXPORT, (
        f"`{campo}` está declarado como excepción y no lo lee ni la ficha ni el export. Borralo."
    )


@pytest.mark.parametrize("campo", ["organismo", "sector", "perfil", "gerencia"])
def test_los_cuatro_campos_que_salieron_del_legajo_no_volvieron(campo: str):
    """🔴 BLOQUE N2. Capital Humano los sacó del legajo el 25/8/2026. Las COLUMNAS siguen
    existiendo en la tabla —sacarlas es DDL y va en su propia tanda—, así que nada impide que
    alguien vuelva a pintarlas 'porque el dato está'. Esto es lo que lo impide.

    🔴 SALIERON POR DOS MOTIVOS DISTINTOS y el test los cubre juntos porque la regla resultante es
    la misma, pero **la razón no se puede unificar**: `organismo`, `sector` y `perfil` están en
    CERO filas (el import los desvía a empresa/área y nunca escribe las columnas); `gerencia`
    tiene 31 de 41 y salió por lo contrario — dejó de ser un campo del legajo para ser la
    agrupación del organigrama, alimentada sólo por el archivo de nómina. Si alguien lee esta
    lista como "las cuatro estaban vacías" va a sacar la conclusión equivocada sobre la cuarta.
    El porqué de cada una está en `db/schema.sql`, sobre las columnas."""
    assert campo not in FICHA, f"`{campo}` volvió a la ficha; salió del legajo por decisión."
    assert campo not in EXPORT, f"`{campo}` volvió al export; salió del legajo por decisión."


def test_los_campos_que_SI_estan_siguen_estando():
    """🔴 LA CONTRACARA, Y NO ES DECORATIVA. Ninguna de las dos direcciones del barrido se rompe
    cuando un campo desaparece de la ficha **y** del export a la vez — se van los dos lados y el
    par sigue coincidiendo. Sin este test, vaciar el legajo entero pasaría en verde.

    Los cuatro elegidos son los que esta tanda tocó y podrían irse por arrastre: los dos que la
    ficha ganó en el bloque N6 y los dos que ya estaban."""
    for campo in ("fecha_ingreso_reconocida", "liderazgo", "seniority", "turno"):
        assert campo in FICHA, f"`{campo}` desapareció de la ficha"
        assert campo in EXPORT, f"`{campo}` desapareció del export"

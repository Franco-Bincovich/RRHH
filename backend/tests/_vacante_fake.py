"""
La vacante falsa que usan los tests del clasificador. Helper, no test.

🔴 POR QUÉ EXISTE, Y POR QUÉ CADA CAMPO TIENE UN VALOR ÚNICO Y RECONOCIBLE

Los fakes de vacante de este repo se construían con `SimpleNamespace(titulo=..., descripcion=...)`
— o sea, **reproducían el bug**: el prompt leía dos campos y los tests le pasaban exactamente esos
dos. Sacar `funciones` o `requisitos` del prompt no rompía nada porque no había ningún test que
supiera que existían.

Acá los SIETE campos vienen cargados con frases **distintas entre sí y buscables** (`SENTINELAS`).
Eso es lo que permite afirmar "los siete llegaron al prompt" de una forma que puede fallar: con un
único valor repetido, o con campos vacíos, quitar seis de los siete pasaría en verde.

⚠️ Los valores no son lorem ipsum a propósito: leen como una búsqueda real, así que un prompt
renderizado en un fallo de test se puede leer y entender.
"""
from types import SimpleNamespace

EMPRESA = "11111111-1111-1111-1111-111111111111"
VACANTE_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

#: atributo → fragmento único que el test busca en el prompt. Uno por campo, sin repetir.
SENTINELAS = {
    "titulo": "Analista Contable Semisenior",
    "area_nombre": "Administración y Finanzas",
    "funciones": "conciliaciones bancarias y cierre mensual",
    "requisitos": "disponibilidad para trabajar de manera presencial",
    "formacion": "graduado de Contador Público",
    "experiencia": "tres años en estudios contables",
    "conocimientos_tecnicos": "Tango Gestión y planillas de cálculo",
}


def vacante_completa(**overrides) -> SimpleNamespace:
    """Una vacante con los siete campos cargados. `descripcion` va vacía por defecto.

    `descripcion` arranca vacía porque así está la única vacante de producción: es un campo
    legacy sin UI para cargarlo. Los tests que quieren probarlo lo pasan explícito.
    """
    campos = {"id": VACANTE_ID, "empresa_id": EMPRESA, "descripcion": "", **SENTINELAS}
    campos.update(overrides)
    return SimpleNamespace(**campos)


def vacante_solo_titulo(**overrides) -> SimpleNamespace:
    """El caso que hace que la corrida se saltee: nada evaluable más allá del título y el área."""
    campos = {"id": VACANTE_ID, "empresa_id": EMPRESA, "titulo": "Analista Contable",
              "area_nombre": "Administración", "descripcion": "", "funciones": None,
              "requisitos": None, "formacion": "", "experiencia": None,
              "conocimientos_tecnicos": ""}
    campos.update(overrides)
    return SimpleNamespace(**campos)

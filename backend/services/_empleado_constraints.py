"""
Qué significa, para quien carga un alta, cada unicidad de `empleados` que rebota.

Extraído de `services/_empleado_duplicado.py`, que quedó en 155 contra un tope de 150 al sumarle
la tabla de las tres constraints. El corte NO es por tamaño: cae en una costura real. Aquel
módulo responde **cómo se detecta un choque y dónde se envuelve** (el SQLSTATE, el context
manager, por qué en el service y no en el repo); éste responde **qué constraint significa qué
para el usuario**, que es lo único que crece — una unicidad nueva en la tabla es una entrada más
acá y ni una línea allá.

Molde del corte: `tests/_columnas_candidatos.py` separándose de su barrido, y
`_barrido_escrituras_estado.py` de `_barrido_estado.py`.

⚠️ Vive en `services/`, así que su límite es 150 líneas, como cualquier service. No hereda un
límite más alto por ser un satélite.
"""
from utils.errors import AppError

# Nombre de la constraint → (mensaje, code). Los nombres salen de `db/schema.sql` y son los que
# PostgREST devuelve en el cuerpo del error.
#
# 🔴 LOS MENSAJES NO DICEN DE QUIÉN ES EL REGISTRO QUE YA ESTÁ: ni nombre, ni legajo, ni empresa.
# Quien carga un alta necesita saber QUÉ campo repitió para corregirlo, y nada más.
#
# ⚠️ El de email no puede decir "en esta empresa" y sería un error escribirlo así: la constraint
# es GLOBAL, así que el choque puede ser contra un empleado de OTRA empresa y el mensaje tiene que
# poder explicar por qué falla un alta que en esta empresa se ve libre. Eso no abre ningún oráculo
# nuevo: todo usuario de esta app accede a todas las empresas (decisión de producto cerrada, ver
# CLAUDE.md), así que no hay frontera que cruzar — al revés que con la barrera de empresa, donde
# el 404 idéntico existe justamente porque ahí sí la hay.
_POR_CONSTRAINT = {
    "empleados_email_corporativo_key": (
        "Ya existe un colaborador con ese email corporativo. El email corporativo es único en todo "
        "el sistema, así que puede estar tomado por un colaborador de otra empresa.",
        "EMAIL_CORPORATIVO_DUPLICADO",
    ),
    "empleados_empresa_dni_uq": (
        "Ya existe un colaborador con ese DNI en esta empresa.",
        "DNI_DUPLICADO",
    ),
    # 🔑 MISMO code que el del pre-chequeo de `_empleados_utils.ensure_legajo_unico`, a propósito:
    # es el mismo hecho contado por el otro camino (su carrera). Dos codes distintos obligarían al
    # front a manejar dos casos para una sola cosa.
    "empleados_legajo_empresa_key": (
        "Ya existe un colaborador con ese legajo en esta empresa.",
        "LEGAJO_DUPLICADO",
    ),
}

# 🔴 EL FALLBACK ES LO QUE CONSERVA LA CONCLUSIÓN DEL MOLDE DE OBJETIVOS: un índice único FUTURO
# no puede volver a subir como 500. Reconocer el nombre elige el MENSAJE; no decide si es un 409.
_GENERICO = (
    "Ya existe un colaborador con esos datos: alguno de los campos únicos está repetido.",
    "EMPLEADO_DUPLICADO",
)


def traducir(exc: Exception) -> AppError:
    """El `AppError` 409 que le corresponde a esta violación de unicidad.

    Busca el nombre de la constraint DENTRO del texto del error, y no compara contra un campo
    exacto, porque PostgREST lo entrega en distintos lugares según cómo haya podido parsear la
    respuesta: `.message`, `.details`, o sólo el `str(exc)`. Se miran los tres concatenados por
    eso, no por las dudas.

    Args:
        exc: La excepción de PostgREST, ya confirmada como un 23505 por el caller.

    Returns:
        AppError con el mensaje y el code de la constraint que rebotó, o el genérico si es una
        que este módulo todavía no conoce.
    """
    texto = f"{getattr(exc, 'message', '')} {getattr(exc, 'details', '')} {exc}"
    for constraint, (mensaje, code) in _POR_CONSTRAINT.items():
        if constraint in texto:
            return AppError(mensaje, code, 409)
    return AppError(*_GENERICO, 409)

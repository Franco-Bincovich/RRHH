"""
`_gmail_mensaje._parse_from_header`: de quién es un mail.

Los casos se movieron VERBATIM desde `test_gmail_candidatos.py`, que se borró al reemplazar el
botón viejo (`crear_candidato_desde_email`) por la ingesta por código. **La función NO se fue con
él**: sigue siendo cómo la ingesta saca el nombre y el mail del candidato, así que sus casos
raros valen más que antes — ahora corren sobre TODOS los mails de la casilla, no sobre los que
alguien eligió a mano.

⚠️ Es un parser de un header escrito por un cliente de mail cualquiera. Los casos de acá salieron
de las formas reales que produce Outlook, iPhone y el webmail; ninguno es hipotético.
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

import pytest  # noqa: E402

from services._gmail_mensaje import _parse_from_header  # noqa: E402


@pytest.mark.parametrize("header,esperado,caso", [
    ("Juan Perez <juan@correo.com>", ("juan@correo.com", "Juan", "Perez"), "nombre y apellido"),
    ("juan@correo.com", ("juan@correo.com", "juan", ""), "sin nombre: cae al usuario del mail"),
    ("<juan@correo.com>", ("juan@correo.com", "juan", ""), "solo corchetes"),
    ('"Perez, Juan" <juan@correo.com>', ("juan@correo.com", "Perez,", "Juan"), "con coma"),
    ("José Ñáñez <jose@correo.com>", ("jose@correo.com", "José", "Ñáñez"), "no ASCII"),
    ("Cher <cher@correo.com>", ("cher@correo.com", "Cher", ""), "un solo nombre"),
    ("Ana Maria De Luca <a@b.com>", ("a@b.com", "Ana", "Maria De Luca"), "apellido compuesto"),
    ("  Juan Perez  <juan@correo.com>  ", ("juan@correo.com", "Juan", "Perez"), "con espacios"),
], ids=lambda v: v if isinstance(v, str) and " " in str(v) else None)
def test_parseo_del_header_from(header, esperado, caso):
    """Casos raros del `From`, fijados como comportamiento.

    🔴 "Perez, Juan" deja la coma pegada al nombre: es lo que el parser hace HOY. Se fija tal
    cual —no se maquilla— porque el formato `Apellido, Nombre` es común en Outlook corporativo y
    esta es la evidencia de que hay que decidir qué hacer con él, no una aprobación.
    """
    assert _parse_from_header(header) == esperado


def test_header_from_vacio_no_revienta():
    """Un mail sin `From` no puede tumbar una corrida entera de la casilla."""
    email, nombre, apellido = _parse_from_header("")
    assert (email, apellido) == ("", "")
    assert isinstance(nombre, str)


def test_pendiente_conocido_rfc2047_llega_sin_decodificar():
    """PENDIENTE CONOCIDO, fijado para que se vea: Gmail devuelve el `From` con codificación
    RFC 2047 cuando el nombre trae acentos, y el parser lo copia crudo al candidato.

    Este test NO arregla nada: documenta que un candidato puede quedar con el nombre
    `=?UTF-8?Q?Jos=C3=A9?=`. Cuando se decodifique, tiene que ROMPERSE y moverse —no borrarse—
    al que verifique lo contrario.
    """
    _, nombre, _ = _parse_from_header("=?UTF-8?Q?Jos=C3=A9?= <jose@correo.com>")
    assert nombre.startswith("=?UTF-8?"), "¿Se decodifica RFC 2047? Mové este test."

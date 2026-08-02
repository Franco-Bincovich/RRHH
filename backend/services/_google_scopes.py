"""
Vocabulario de scopes de Google: qué se pide, y cómo se lee lo que el usuario concedió.

Módulo propio y no una constante dentro de `_google_oauth.py` por dos razones: aquel llegó a
152 contra un límite de 150 al documentar el scope de envío, y —de fondo— *pedir* scopes y
*verificar* los concedidos son dos preguntas distintas con dos consumidores distintos (el flow
OAuth y la pantalla de integraciones). Molde: `_nomina_empleados_transforms`, que también es un
módulo de vocabulario sin lógica de negocio.

## 🔴 AGREGAR `gmail.send` OBLIGA A RECONECTAR — no es negociable ni evitable

Google **NO amplía retroactivamente un grant ya otorgado**. La integración que RRHH tiene
conectada hoy se pidió solo con `gmail.readonly`:

  · su `refresh_token` sigue siendo válido y sigue sirviendo para LEER — no se rompe nada;
  · pero el grant al que está atado no incluye `gmail.send`, y los access tokens que se deriven
    de él tampoco;
  · ⇒ el primer intento de envío devuelve **403 `ACCESS_TOKEN_SCOPE_INSUFFICIENT`**. No un 401:
    el token es válido, lo que falta es el permiso.

Por eso se persisten los scopes REALMENTE concedidos y `puede_enviar()` los lee: la pantalla de
integraciones avisa ANTES, en vez de que alguien se entere por un 403 en medio de un envío.

`gmail.send` es lo MÍNIMO que permite enviar: solo mandar, no leer ni borrar. Se prefiere a
`gmail.modify` o `mail.google.com`, que dan acceso al buzón entero para la misma tarea.
"""
from typing import Iterable, Optional

SCOPE_LECTURA = "https://www.googleapis.com/auth/gmail.readonly"
SCOPE_ENVIO = "https://www.googleapis.com/auth/gmail.send"

SCOPES_PEDIDOS = [
    SCOPE_LECTURA,
    SCOPE_ENVIO,
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


def puede_enviar(scopes: Optional[Iterable[str]]) -> bool:
    """¿La cuenta conectada tiene permiso para ENVIAR mails?

    ⚠️ `None` (o vacío) devuelve False, y es lo correcto aunque parezca duro: son las
    integraciones conectadas ANTES de que existiera esta columna, que por definición se
    autorizaron sin el scope de envío. Tratarlas como capaces de enviar sería exactamente el
    403-en-el-peor-momento que este módulo existe para evitar.

    Args:
        scopes: los scopes concedidos, tal como los guardó `procesar_callback`.

    Returns:
        True solo si `gmail.send` está entre los concedidos.
    """
    return SCOPE_ENVIO in set(scopes or ())

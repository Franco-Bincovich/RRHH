"""
DE DÓNDE SALE LA CREDENCIAL de la semilla. Un archivo propio, como `_semilla_guarda.py`, porque
lo que decide no es una comodidad de CLI sino dónde termina escrito un secreto.

🔴 NO HAY `--token` NI `--password`, Y ES DELIBERADO. Todo argumento de la línea de comandos
queda en el historial de PowerShell (`ConsoleHost_history.txt`: texto plano, en disco, sin
vencimiento y fuera de cualquier rotación). Un token de Supabase dura una hora, pero el archivo
que lo guarda no caduca nunca; y una contraseña de `admin_rrhh` ahí es peor todavía. El entorno
de un proceso, en cambio, muere con la consola.
"""
import os
from pathlib import Path

from _semilla_cliente import login


def credencial(base: str) -> str:
    """El token, SIEMPRE del entorno. Ver el encabezado del módulo.

    Dos formas, en orden: `SEMILLA_TOKEN` (un JWT ya obtenido) o el par `SEMILLA_USUARIO` /
    `SEMILLA_PASSWORD`, con el que el script hace el login él mismo. `scripts/.semilla.env`
    —fuera de git— sirve para no tener que exportarlas en cada sesión.
    """
    archivo = Path(__file__).resolve().parent / ".semilla.env"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            if "=" in linea and not linea.lstrip().startswith("#"):
                clave, _, valor = linea.partition("=")
                os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))
    token = os.environ.get("SEMILLA_TOKEN", "").strip()
    usuario = os.environ.get("SEMILLA_USUARIO", "").strip()
    clave = os.environ.get("SEMILLA_PASSWORD", "").strip()
    if not token and usuario and clave:
        token = login(base, usuario, clave)
    if not token:
        raise SystemExit(
            "ABORTADO: falta credencial, y NO se pasa por la línea de comandos (queda en el "
            "historial de PowerShell). Seteá en el entorno:\n"
            '  $env:SEMILLA_TOKEN = "eyJ..."        # ver docs/SMOKE-TEST.md\n'
            "  — o —\n"
            '  $env:SEMILLA_USUARIO = "..."; $env:SEMILLA_PASSWORD = "..."\n'
            f"También sirve un archivo `{archivo.name}` en scripts/ (ignorado por git).")
    return token

"""
Proyección de columnas legibles para el export de usuarios del sistema.

Mismo molde que los otros exports (`_proyectos_export.py`, `_areas_export.py`): no vuelca el
dict crudo del repo, que traería el `id`. Los headers del Excel son las keys de cada dict. El
armado del archivo y el chequeo de límite viven en el service — `test_limite_export.py` los
verifica en `UsuarioService.exportar`.

🔴 QUÉ NO SALE EN EL ARCHIVO, y por qué está escrito acá y no confiado a la memoria de nadie:
este export lista PERSONAS CON ACCESO AL SISTEMA, así que cada columna de más es una pista de
más para quien reciba el Excel. Quedan afuera a propósito:

  · **credenciales de cualquier tipo** — hash, contraseña temporal, tokens. `public.users` ni
    siquiera las tiene (viven en `auth.users`, gestionadas por Supabase Auth), y la temporal
    del alta se muestra UNA vez y no se persiste en claro. No hay de dónde sacarlas, y el día
    que alguien agregue una columna a `users` esta lista dice que no entra sola.
  · **el ban de Auth y `must_change_password`** — estado del ciclo de vida de la credencial.
    Saber que a alguien le vence la clave, o que está baneado, no le sirve a RRHH y sí a quien
    quiera elegir a quién atacar.
  · **`ultimo_acceso`** — es telemetría de sesión, no un dato del usuario.
  · **el `id`** — como en todos los exports del repo, nada de UUIDs crudos.

Las columnas son EXACTAMENTE las cinco que muestra `UsuariosTable.tsx`, más "Activo". El
archivo no puede decir más que la pantalla de la que sale.
"""
from typing import List

_ROL_LABEL = {
    "admin_rrhh": "Administrador RRHH",
    "gerencia_lectura": "Gerencia (solo lectura)",
    "mandos_medios": "Mando medio",
}


def _rol(valor) -> str:
    """Traduce el rol al mismo texto que muestra la UI (ROL_LABEL de types/auth).

    Cae al valor crudo si aparece un rol desconocido: un archivo que dice `rol_nuevo` es
    peor que uno que dice nada, pero mucho mejor que uno que dice '' y esconde que existe.
    """
    return _ROL_LABEL.get(valor, valor or "")


def construir_filas_export(items: List[dict]) -> List[dict]:
    """Proyecta los usuarios a columnas legibles (sin UUIDs, sin nada de credenciales)."""
    return [
        {
            "Nombre": u.get("nombre"),
            "Apellido": u.get("apellido"),
            "Email": u.get("email"),
            "Usuario": u.get("username"),
            "Rol": _rol(u.get("rol")),
            # Constante "Sí" por construcción: el listado —y por lo tanto el archivo— trae
            # SOLO activos. Va igual, y no es relleno: sin ella, el que recibe el Excel no
            # tiene forma de saber que los usuarios dados de baja no están. La baja de un
            # usuario es blanda (`activo=false`), así que esas filas existen en la tabla.
            "Activo": "Sí" if u.get("activo", True) else "No",
        }
        for u in items
    ]

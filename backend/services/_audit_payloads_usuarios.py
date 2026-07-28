"""
Payloads de auditoría de los usuarios del sistema: alta, baja y cambio de contraseña.

Extraído de _audit_payloads_rrhh.py, que estaba en 189 líneas contra un límite de 150. Los
usuarios ni siquiera figuraban entre los dominios que aquel módulo declaraba cubrir
(empleados, costos, empresa, adjuntos, períodos): habían quedado ahí por acumulación. El
movimiento es puro — las tres funciones son idénticas a las que estaban allá.

🔒 NINGUNA de las tres incluye jamás una contraseña, ni la temporal del alta ni la nueva del
cambio. El audit log lo lee el equipo de RRHH entero; una credencial ahí adentro sobrevive a
cualquier rotación posterior. Se registra QUE la clave cambió, nunca a qué.
"""
from typing import Optional


def payload_alta_usuario(user_id: str, username: str, rol: str, usuario_id: Optional[str]) -> dict:
    """Evento INSERT de alta de un usuario del sistema. NUNCA incluye la contraseña temporal.
    empresa_id = None: los usuarios son globales, no pertenecen a una empresa."""
    return {
        "usuario_id": usuario_id, "entidad": "usuario", "registro_id": user_id,
        "accion": "INSERT", "evento": "alta_usuario", "empresa_id": None,
        "datos_anteriores": None, "datos_nuevos": {"username": username, "rol": rol},
    }


def payload_baja_usuario(user_id: str, username: Optional[str], usuario_id: Optional[str]) -> dict:
    """Evento DELETE de baja de un usuario del sistema. NUNCA incluye contraseñas.
    empresa_id = None: los usuarios son globales, no pertenecen a una empresa."""
    return {
        "usuario_id": usuario_id, "entidad": "usuario", "registro_id": user_id,
        "accion": "DELETE", "evento": "baja_usuario", "empresa_id": None,
        "datos_anteriores": {"username": username}, "datos_nuevos": None,
    }


def payload_cambio_password(user_id: str) -> dict:
    """Evento UPDATE de cambio de contraseña propia (self-service). NUNCA incluye
    contraseñas: registra solo que el usuario cambió su clave. usuario_id = registro_id
    (el usuario se audita a sí mismo). empresa_id = None (los usuarios son globales)."""
    return {
        "usuario_id": user_id, "entidad": "usuario", "registro_id": user_id,
        "accion": "UPDATE", "evento": "cambio_password", "empresa_id": None,
        "datos_anteriores": None, "datos_nuevos": None,
    }

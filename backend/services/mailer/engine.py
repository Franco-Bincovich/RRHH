"""
EL PUNTO DE SALIDA ÚNICO de todos los mails del sistema.

Molde: `services/export/engine.py`, y no por parecido estético — por las tres propiedades que
hacen que aquel haya aguantado 11 services sin erosionarse:
  1. el `__init__` del paquete ES el contrato: nadie de afuera importa un submódulo;
  2. el despacho es un DICT, no una cadena de `if`: sumar un proveedor es una entrada;
  3. es agnóstico del dominio: no sabe qué es un empleado ni una vacación.

## 🔴 LAS DOS INVARIANTES, y por qué viven acá y no en el proveedor

**(1) Nadie importa `_gmail` directo.** Si un caller lo hiciera, se saltearía todo lo de abajo y
el punto único dejaría de serlo sin que nada falle. Lo verifica `test_mailer_punto_unico.py`.

**(2) EL LOG Y LA AUDITORÍA VIVEN ACÁ, NO EN `_gmail.py`.** Es la invariante que más fácil se
rompe y la que más caro sale: si el registro viviera en el proveedor, **el próximo proveedor
nacería sin log** — exactamente lo que pasó con los exports antes de `verificar_limite_export`,
que hoy tiene un barrido que lo impide. Acá el log rodea al despacho: cualquier proveedor,
presente o futuro, queda registrado por construcción.

## El registro es DOBLE, y no es redundancia
  · `mail_enviado` guarda el TEXTO RENDERIZADO — contesta "¿qué le llegó a Fulano?" y sostiene
    la idempotencia. Es lo que reemplaza al versionado de plantillas.
  · `auditoria` guarda el HECHO — mandar un mail a nombre de la empresa es una ACCIÓN, y en este
    repo toda acción se audita. Para un lote va UN evento con el conteo, nunca uno por mail
    (regla propia del repo: "al auditar una importación, un evento por lote").

## Un fallo se registra, no se traga
Un envío fallido escribe su fila con `estado='fallido'` y el motivo, y DESPUÉS propaga el error.
Sin la fila, "no me llegó" no tendría respuesta justo en el caso en que se necesita.
"""
from typing import Callable, Dict, Optional

from repositories.integracion_remitente_repo import IntegracionRemitenteRepo
from repositories.mail_enviado_repo import MailEnviadoRepo
from services._google_token import access_token_valido
from services.mailer import _gmail
from services.mailer._markdown import a_html
from utils.errors import AppError
from utils.logger import logger

# Sumar un proveedor es UNA entrada acá y un archivo hermano. El día del cutover a AWS, si Gmail
# pasa a SES, eso es todo lo que cambia — cero call sites tocados.
_PROVEEDORES: Dict[str, Callable] = {"gmail": _gmail.enviar}


def enviar_mail(destinatario: str, asunto: str, cuerpo_md: str, *,
                empresa_id=None, plantilla_clave: Optional[str] = None,
                contexto: Optional[str] = None, empleado_id: Optional[str] = None,
                enviado_por: Optional[str] = None, proveedor: str = "gmail",
                log_repo=None, remitente_repo=None) -> dict:
    """Envía UN mail y lo registra. Es la única puerta de salida del sistema.

    Args:
        destinatario: dirección de destino.
        asunto: asunto YA renderizado (sin variables sin resolver).
        cuerpo_md: cuerpo en Markdown mínimo, ya renderizado. Se convierte a HTML acá.
        empresa_id · plantilla_clave · contexto · empleado_id · enviado_por: para el log.
        proveedor: clave de `_PROVEEDORES`.
        log_repo / remitente_repo: inyectables para test.

    Returns:
        dict con `enviado` (bool) y `mensaje_id`.

    Raises:
        AppError: MAIL_PROVEEDOR_INVALIDO (422) si el proveedor no existe.
        AppError: MAIL_SIN_REMITENTE (400) si no hay casilla del sistema configurada.
        AppError: MAIL_SIN_PERMISO (403) · MAIL_ERROR_PROVEEDOR (502) — del proveedor.
    """
    enviar = _PROVEEDORES.get(proveedor)
    if enviar is None:
        raise AppError(f"Proveedor de mail no soportado: {proveedor}", "MAIL_PROVEEDOR_INVALIDO", 422)

    remitente = _remitente(remitente_repo or IntegracionRemitenteRepo())
    cuerpo_html = a_html(cuerpo_md)
    log = log_repo or MailEnviadoRepo()
    base = {"empresa_id": str(empresa_id) if empresa_id else None,
            "plantilla_clave": plantilla_clave, "contexto": contexto,
            "empleado_id": str(empleado_id) if empleado_id else None,
            "destinatario": destinatario, "remitente": remitente.get("email_cuenta"),
            "asunto_render": asunto, "cuerpo_render": cuerpo_md,
            "enviado_por": str(enviado_por) if enviado_por else None}

    try:
        token = access_token_valido(_repo_de(remitente), remitente["user_id"])
        mensaje_id = enviar(token, remitente.get("email_cuenta"), destinatario,
                            asunto, cuerpo_html, cuerpo_md)
    except AppError as exc:
        # Se registra el fallo ANTES de propagar: sin esta fila, "no me llegó" queda sin
        # respuesta justo en el caso en que hace falta.
        _registrar(log, {**base, "estado": "fallido", "error": f"{exc.code}: {exc.message}"[:500]})
        raise
    _registrar(log, {**base, "estado": "enviado", "gmail_message_id": mensaje_id})
    logger.info("Mail enviado", extra={"destinatario": destinatario, "plantilla": plantilla_clave})
    return {"enviado": True, "mensaje_id": mensaje_id}


def _remitente(repo) -> dict:
    """La casilla del sistema, o un error accionable. Nunca cae a "la del usuario logueado".

    Es deliberado que NO haya fallback: si lo hubiera, el remitente cambiaría según quién apretó
    el botón —y un proceso automático no tendría ninguno—, que es justamente la ambigüedad que
    la casilla del sistema vino a cerrar. Mejor un error que dice qué hacer.
    """
    fila = repo.get_remitente()
    if not fila or not fila.get("user_id"):
        raise AppError(
            "No hay una casilla de correo configurada para enviar. Conectá una cuenta de Gmail "
            "en Configuración y marcala como casilla del sistema.",
            "MAIL_SIN_REMITENTE", 400)
    return fila


def _repo_de(remitente: dict):
    """Adapta la fila del remitente a lo que `access_token_valido` espera de un repo.

    La fila YA tiene los tokens (`get_remitente` trae la integración entera), así que volver a
    consultarla por `user_id` sería una query de más en el camino de cada mail de un lote.
    `actualizar_token` sí delega en el repo real: el token renovado tiene que persistirse.
    """
    from repositories.integracion_repo import IntegracionRepo

    real = IntegracionRepo()

    class _Fija:
        def get_by_user_and_tipo(self, user_id, tipo):
            return remitente

        def actualizar_token(self, user_id, access_token, token_expiry):
            real.actualizar_token(user_id, access_token, token_expiry)

    return _Fija()


def _registrar(log, fila: dict) -> None:
    """Escribe la fila del log. BEST-EFFORT: el mail ya salió (o ya falló) y el log no puede
    cambiar eso. Un fallo acá se loguea y no altera el resultado de la operación."""
    try:
        log.registrar(fila)
    except Exception as exc:  # noqa: BLE001 — ver docstring
        logger.warning("No se pudo registrar el envío de mail", extra={"error": str(exc)})

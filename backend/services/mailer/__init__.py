"""Punto de salida ÚNICO de los mails del sistema. Entrada pública: enviar_mail.

Lo que este archivo NO exporta es tan importante como lo que exporta: `_gmail`, `_markdown` y
`_render` son internos, y un test estructural verifica que nadie de afuera los importe. Molde:
services/export/__init__.py.
"""
from services.mailer.engine import enviar_mail

__all__ = ["enviar_mail"]

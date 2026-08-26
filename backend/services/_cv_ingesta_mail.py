"""
Procesar UN mail de la casilla: matchear la vacante, bajar los CVs y crear un candidato por cada
uno. Funciones libres que reciben sus colaboradores — molde `_vacante_write.crear(repo, ...)`.

## Qué queda acá y qué se fue

Acá vive el MATCHEO: del asunto al código, del código a la vacante, y la clasificación de lo que
no resuelve. El alta en sí —validar, crear, subir, `set_cv`— se fue a `services/_cv_alta.py`
cuando la asignación manual de la fase 6 pasó a necesitar exactamente la misma, con la única
diferencia de que la vacante la elige RRHH en vez del código.

## 🔴 UN CANDIDATO POR CV, NO POR MAIL

Un mail con tres adjuntos de tres personas distintas son tres candidatos: es el caso del
referente que reenvía varios CVs juntos. Por eso la unidad de idempotencia es el ADJUNTO
(`gmail_message_id` + `sha256` del contenido), no el mensaje.

## 🔴 SIN MATCH NO SE CREA NADA

`candidatos.empresa_id` es NOT NULL y sin vacante no hay de dónde heredarla — el remitente es
alguien de afuera que no aporta ninguna empresa. El mail se reporta como PENDIENTE y RRHH lo
asigna a mano; recién ahí se crea el candidato, con la empresa de la vacante elegida. Inventar
una empresa acá sería adivinar a qué sociedad pertenece una postulación.
"""
from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from services._cv_alta import crear_de_un_cv
from services._gmail_adjuntos import descargar_cvs
from services._gmail_matcher import codigos_en


@dataclass
class ResultadoMail:
    """Qué pasó con UN mail. `motivo` solo cuando no se creó nada."""
    message_id: str
    asunto: str = ""
    remitente: str = ""
    codigo: Optional[str] = None
    candidatos_creados: List[str] = field(default_factory=list)
    ya_existian: int = 0
    descartados: List[str] = field(default_factory=list)
    motivo: Optional[str] = None          # sin_codigo | codigo_ambiguo | vacante_desconocida
                                          # | sin_adjuntos | sin_cv_valido | error

    @property
    def pendiente(self) -> bool:
        """¿Necesita que un humano lo mire? Todo lo que no generó ni reconoció nada."""
        return bool(self.motivo)


def _headers(mensaje: dict) -> dict:
    payload = mensaje.get("payload") or {}
    return {h.get("name", ""): h.get("value", "") for h in (payload.get("headers") or [])}


def procesar_mail(client, access_token: str, mensaje: dict, *, vacante_repo, candidato_repo,
                  cv_service, codigos_conocidos: Iterable[str],
                  empresa_id_por_defecto=None) -> ResultadoMail:
    """Matchea, baja y crea. NUNCA levanta por un mail: lo que falla vuelve en `motivo`.

    Args:
        client: cliente httpx abierto, compartido por toda la corrida.
        access_token: token de la casilla del SISTEMA.
        mensaje: dict de `messages.get?format=full`.
        vacante_repo: con `find_by_codigo` (case-insensitive, sin filtro de empresa).
        codigos_conocidos: los códigos de las vacantes que existen. 🔴 ES OBLIGATORIO Y VIENE DE
            AFUERA: desde la migración 122 el código lo escribe Capital Humano y no tiene forma
            que adivinar, así que el matcher busca los que EXISTEN. Se resuelve UNA vez por
            corrida (`CvIngestaService.revisar_casilla`); pedirlo acá sería una query por mail.
        candidato_repo: con `existe_cv_de_gmail`, `save_candidato` y `set_cv`.
        cv_service: con `validar` y `subir`.
        empresa_id_por_defecto: NO se usa para crear; se acepta para no romper la firma si algún
            día se decide un destino por defecto. Hoy sin match no se crea nada.
    """
    hmap = _headers(mensaje)
    res = ResultadoMail(message_id=str(mensaje.get("id") or ""),
                        asunto=hmap.get("Subject", ""), remitente=hmap.get("From", ""))

    encontrados = codigos_en(res.asunto, codigos_conocidos)
    if not encontrados:
        res.motivo = "sin_codigo"
        return res
    if len(encontrados) > 1:
        # Elegir el primero sería una decisión invisible sobre la carrera de alguien.
        res.motivo = "codigo_ambiguo"
        return res
    res.codigo = encontrados[0]

    vacante = vacante_repo.find_by_codigo(res.codigo)
    if not vacante:
        res.motivo = "vacante_desconocida"
        return res

    adjuntos = descargar_cvs(client, access_token, mensaje, cv_service)
    res.descartados = [d.filename for d in adjuntos.descartados]
    if not adjuntos.tenia_adjuntos:
        res.motivo = "sin_adjuntos"
        return res
    if not adjuntos.cvs:
        # Traía adjuntos y ninguno era un CV: distinto de "no adjuntó nada", y por eso se
        # reporta distinto. Ver `_gmail_adjuntos.sin_cv_util`.
        res.motivo = "sin_cv_valido"
        return res

    for cv in adjuntos.cvs:
        crear_de_un_cv(res, cv, vacante, hmap, candidato_repo=candidato_repo,
                       cv_service=cv_service)
    return res

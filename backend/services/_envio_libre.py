"""
Envío a una DIRECCIÓN ESCRITA A MANO, no a un empleado del sistema.

Satélite de `mail_envio_service.py`, que estaba en 130/150: la validación de formato, la regla de
las variables y el camino de envío no entraban ahí. El corte cae solo — todo lo que sabe de
"destinatario que no es un empleado" vive acá y nada más vive acá.

## 🔴 UNA PLANTILLA CON VARIABLES NO SE PUEDE MANDAR A UNA DIRECCIÓN LIBRE

Decisión de producto. `{{nombre_empleado}}` se resuelve contra un empleado; sin empleado, el
render lo deja en "" (por diseño: una variable sin valor es un dato faltante, no un error) y el
mail sale con un hueco donde iba el nombre de la persona. Un mail así es peor que no poder
mandarlo: llega a alguien de afuera, no se puede deshacer, y se lee como un sistema roto.

La barrera va ANTES de mandar y la UI la refleja deshabilitando el modo libre con el motivo a la
vista. Igual se verifica acá: la UI no es la frontera.

⚠️ **EL PREDICADO ES "USA ALGUNA VARIABLE", NO "USA VARIABLES DEL EMPLEADO", Y ES A PROPÓSITO.**
`{{empresa_nombre}}`, `{{fecha_hoy}}` y `{{hora_ahora}}` SÍ resolverían sin empleado, así que la
regla es más restrictiva de lo estrictamente necesario. Se eligió así porque el costo de los dos
errores no es simétrico: de más, alguien no puede mandar un mail y se entera en el momento; de
menos, sale un mail con un hueco a una persona de afuera. Si RRHH pide aflojarlo, la perilla es
esta única función — y ahí habría que distinguir por entidad de origen, no por variable.

## El formato se valida en las DOS puntas
El front para no frustrar (deshabilita antes de apretar) y acá porque es la frontera: el endpoint
se puede llamar sin pasar por la pantalla.
"""
import re
from typing import List, Optional

from services._lote_mails import LoteMails
from services.mailer import enviar_mail
from services.mailer._render import render, variables_usadas
from utils.errors import AppError

# Formato de dirección: deliberadamente CONSERVADOR, no RFC 5322. La gramática completa acepta
# cosas que ningún proveedor entrega y su regex es imposible de revisar; lo que se quiere acá es
# atajar el typo (`ana@`, `ana k.com`, `ana@k`), no certificar direcciones exóticas. Lo que pase
# este filtro y no exista igual va a fallar en el envío y quedar registrado como `fallido`.
_EMAIL = re.compile(r"^[^@\s,;]+@[^@\s,;]+\.[A-Za-z]{2,}$")

MAX_LIBRES = 50


def email_valido(direccion: str) -> bool:
    """¿Tiene forma de dirección de mail? Ver por qué el patrón es conservador, arriba."""
    return bool(_EMAIL.match((direccion or "").strip()))


def normalizar(direcciones: List[str]) -> List[str]:
    """Trimea, saca vacíos y deduplica preservando el orden.

    Dedup porque la lista la escribe una persona: pegar dos veces la misma dirección es normal, y
    mandar dos mails idénticos a alguien de afuera no lo es. El orden se preserva para que el
    reporte de fallidos se lea en el mismo orden en que se escribió.
    """
    vistas: dict = {}
    for d in direcciones or []:
        limpia = (d or "").strip()
        if limpia:
            vistas.setdefault(limpia.lower(), limpia)
    return list(vistas.values())


def plantilla_usa_variables(plantilla: dict) -> bool:
    """¿El asunto o el cuerpo tienen alguna `{{variable}}`?

    Reusa `variables_usadas` del renderer en vez de un regex propio: si fueran dos, un cambio de
    sintaxis dejaría a esta barrera mirando la sintaxis vieja y el mail saldría con el hueco.
    """
    return bool(variables_usadas(plantilla.get("asunto") or "")
                or variables_usadas(plantilla.get("cuerpo") or ""))


def validar(plantilla: dict, direcciones: List[str]) -> List[str]:
    """Aplica las tres barreras y devuelve la lista lista para enviar.

    Raises:
        AppError: PLANTILLA_CON_VARIABLES (422) — no se puede mandar a una dirección libre.
        AppError: EMAIL_INVALIDO (422) con las direcciones mal escritas.
        AppError: DEMASIADOS_DESTINATARIOS (422) por encima de MAX_LIBRES.
    """
    if plantilla_usa_variables(plantilla):
        raise AppError(
            "Esta plantilla usa datos del colaborador, así que solo se puede enviar a colaboradores "
            "del sistema. Para mandarla a una dirección suelta, sacale las variables.",
            "PLANTILLA_CON_VARIABLES", 422)
    limpias = normalizar(direcciones)
    malas = [d for d in limpias if not email_valido(d)]
    if malas:
        raise AppError("Estas direcciones no son válidas: " + ", ".join(malas), "EMAIL_INVALIDO", 422)
    if len(limpias) > MAX_LIBRES:
        raise AppError(
            f"Máximo {MAX_LIBRES} direcciones por envío; recibimos {len(limpias)}.",
            "DEMASIADOS_DESTINATARIOS", 422)
    return limpias


def enviar_a_direccion(lote: LoteMails, plantilla: dict, direccion: str, empresa_id,
                       usuario_id: Optional[str], log) -> None:
    """Manda UN mail a una dirección suelta. Best-effort, igual que el camino de empleados.

    🔴 LA IDEMPOTENCIA TAMBIÉN VALE ACÁ, y por eso el log se consulta por DESTINATARIO: sin
    empleado no hay `empleado_id` con el que preguntar. Sin esto, un lote cortado por presupuesto
    reenviaría a las direcciones que ya habían recibido el mail al reintentarlo — el daño visible
    para gente de afuera que toda esta parte del módulo existe para evitar.

    El render corre igual aunque no haya variables: es el MISMO camino que el de empleados, así
    que un cambio en el renderer no puede afectar a uno solo de los dos.
    """
    if log.ya_enviado(plantilla["clave"], destinatario=direccion):
        lote.registrar_omitido()
        return
    asunto, cuerpo, _ = render(plantilla["contexto"], plantilla["asunto"], plantilla["cuerpo"],
                               {"empresa": {}})
    try:
        enviar_mail(direccion, asunto, cuerpo, empresa_id=empresa_id,
                    plantilla_clave=plantilla["clave"], contexto=plantilla["contexto"],
                    empleado_id=None, enviado_por=usuario_id)
        lote.registrar_envio()
    except AppError as exc:
        lote.registrar_fallo(direccion, exc.message)

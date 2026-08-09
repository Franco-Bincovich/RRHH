"""
Las dos lecturas de `candidatos` que sostienen la ingesta de CVs por mail.

Extraído de `candidato_repo.py`, que estaba en 100/100 exacto. Van juntas y aparte porque las dos
contestan la MISMA pregunta a dos granularidades distintas —"¿esto ya se procesó?"— y la
diferencia entre ellas es sutil y load-bearing: ver el docstring de `message_ids_procesados`.
"""
from typing import Iterable, Set

from integrations.supabase_client import supabase_admin

_C = "candidatos"


def existe_cv(empresa_id: str, message_id: str, sha256: str) -> bool:
    """¿Este adjunto de este mail ya generó un candidato? Idempotencia de la ingesta AUTOMÁTICA.

    🔴 La clave es el HASH del contenido, no el `attachmentId`: ese id está scopeado a UNA
    lectura del mensaje, así que una constraint sobre él compilaría sin proteger nada (ver
    migración 098). ⚠️ Camino RÁPIDO, no garantía —entre el SELECT y el INSERT hay ventana—: la
    garantía es el índice único, y si dos corridas chocan la segunda falla el insert y la ingesta
    lo cuenta como fallo de ESE CV, sin cortar el lote.
    """
    res = (supabase_admin.table(_C).select("id").eq("empresa_id", empresa_id)
           .eq("gmail_message_id", message_id).eq("cv_sha256", sha256).limit(1).execute())
    return bool(res.data)


def message_ids_procesados(message_ids: Iterable[str]) -> Set[str]:
    """De una tanda de ids de Gmail, cuáles YA generaron algún candidato. UNA sola query.

    🔴 ES LO QUE HACE VIABLE LA PANTALLA DE PENDIENTES. Los mails sin match no se persisten: se
    releen de la casilla cada vez. Sin esto, saber si un mail ya se había procesado exigiría
    BAJAR sus adjuntos y hashearlos —`existe_cv` necesita el contenido—, o sea re-descargar todo
    lo ya resuelto en cada apertura de la pantalla. Acá la pregunta es a nivel MENSAJE y se
    contesta contra `idx_candidatos_gmail_message` (mig 098) antes de tocar la red.

    ⚠️ NO reemplaza a `existe_cv` en la ingesta automática, y la diferencia importa: un mail puede
    quedar procesado A MEDIAS (un CV creado y otro fallado), y saltearlo entero por mensaje
    perdería el segundo para siempre. Acá es exacto porque un PENDIENTE es, por construcción, un
    mail que creó CERO candidatos.
    """
    ids = [i for i in message_ids if i]
    if not ids:
        return set()
    res = (supabase_admin.table(_C).select("gmail_message_id")
           .in_("gmail_message_id", ids).execute())
    return {r["gmail_message_id"] for r in (res.data or []) if r.get("gmail_message_id")}

"""
De UN CV bajado a UN candidato. Es lo que comparten los dos caminos de la fase 5 y la 6.

Extraído de `_cv_ingesta_mail.py` cuando la asignación manual pasó a necesitar exactamente el
mismo alta: la ingesta automática elige la vacante por el código del asunto y la manual la recibe
de RRHH, pero **desde que hay vacante para adelante no hay una sola diferencia**. Dos copias de
esto habrían divergido en el orden o en el manejo del fallo de Storage, que es justo lo que
importa acá.

## 🔴 EL ORDEN ES EL DE `_vacante_candidatos.agregar`, COPIADO A PROPÓSITO

    validar el CV → crear el candidato → subir a Storage → set_cv

Y el criterio que va con él: **si Storage falla DESPUÉS de crear, el candidato se conserva sin
CV**. Son dos mutaciones que fallan por separado, y revertir el candidato perdería la postulación
entera por un problema de almacenamiento. Lo único que cambia respecto del hermano manual de la
ficha es de dónde salen los bytes.

⚠️ No emite eventos de auditoría: los dos callers auditan UN evento POR LOTE / por asignación,
que es la regla del repo para importaciones. Uno por CV convertiría un click en decenas de filas.
"""
import hashlib

from schemas.candidato import CandidatoCreate
from services._cv_texto import extraer
from services._gmail_mensaje import _parse_from_header
from utils.logger import logger


def crear_de_un_cv(res, cv, vacante, hmap: dict, *, candidato_repo, cv_service) -> None:
    """Un CV → un candidato. El orden y el criterio son los de `_vacante_candidatos.agregar`."""
    sha = hashlib.sha256(cv.contenido).hexdigest()
    empresa_id = str(vacante.empresa_id or "")
    if candidato_repo.existe_cv_de_gmail(empresa_id, res.message_id, sha):
        # Idempotencia: reprocesar la casilla no duplica. No es un error ni una creación, así
        # que se cuenta aparte — un reintento que dijera "0 creados" parecería no haber hecho nada.
        res.ya_existian += 1
        return

    email_addr, nombre, apellido = _parse_from_header(hmap.get("From", ""))
    # 🔴 El texto se extrae ANTES del INSERT y viaja en el MISMO write, no en un update posterior.
    # Los bytes ya están en memoria (se acaban de bajar y validar), así que no cuesta una lectura
    # más; y el candidato nace con su warning aunque Storage falle después. `extraer` nunca
    # levanta: un archivo ilegible devuelve el motivo, no una excepción. Ver `_cv_texto`.
    leido = extraer(cv.contenido, cv.filename)
    candidato = candidato_repo.save_candidato(
        str(vacante.id), CandidatoCreate(nombre=nombre, apellido=apellido, email=email_addr),
        empresa_id,
        {"fuente": "gmail", "gmail_message_id": res.message_id, "cv_sha256": sha,
         "cv_texto": leido.texto, "screening_warning": leido.warning},
    )
    res.candidatos_creados.append(candidato.id)

    try:
        path = cv_service.subir(empresa_id, candidato.id, cv.contenido, cv.filename, cv.mime)
        candidato_repo.set_cv(candidato.id, path)
    except Exception as exc:  # noqa: BLE001 — el candidato YA existe y no se revierte
        # Mismo criterio que el alta manual: perder la postulación entera por un fallo de
        # Storage es peor que un candidato sin archivo, que se puede recuperar pidiéndoselo.
        logger.error("CV no adjuntado tras crear candidato desde Gmail",
                     extra={"candidato_id": candidato.id, "error": str(exc)})

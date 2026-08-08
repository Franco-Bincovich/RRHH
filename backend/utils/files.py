"""
Validación centralizada de archivos subidos (tamaño + MIME type), post-read.
Usar en todo endpoint que reciba un UploadFile, antes de procesar el contenido.
"""
from utils.errors import AppError

# ─────────────────────────────────────────────────────────────────────────────────────────
# 🔴 TECHO DE LA PLATAFORMA — ES EL ÚNICO NÚMERO A REVISAR CUANDO CAMBIE EL HOSTING
# ─────────────────────────────────────────────────────────────────────────────────────────
# Vercel rechaza cualquier request con body > 4,5 MB (docs al 1/7/2026), y lo hace ANTES de
# invocar la función: nuestro código nunca lo ve. Un límite propio POR ENCIMA de este número no
# protege nada — solo cambia quién produce el error, y la plataforma produce un 413 crudo que
# para el usuario es incomprensible.
#
# Por eso ninguno de los límites de abajo puede superarlo. No es una preferencia: un adjunto de
# 6 MB HOY NO SE PUEDE SUBIR, con nuestro límite en 10 MB o en 4,2. Lo único que decide el
# número es si el usuario entiende por qué.
#
# EN AWS ESTE TECHO CAMBIA (lo define API Gateway / ALB, no la app) → se toca ACÁ, una sola vez,
# y los cuatro límites derivados se mueven con él. `tests/test_limites_subida.py` falla si algún
# límite queda por encima del techo.
LIMITE_PLATAFORMA_MB = 4.5

# Límite propio de TODA subida: el techo menos ~0,3 MB de margen. El margen no es paranoia —
# el request pesa MÁS que el archivo: un multipart lleva boundaries, headers por parte y el
# nombre del archivo, así que un archivo de exactamente 4,5 MB ya se pasa del techo.
MAX_SIZE_SUBIDA = int(4.2 * 1024 * 1024)

# Los cuatro derivan del mismo valor. Se conservan como nombres separados a propósito: cada uno
# marca la semántica de su endpoint, y si alguna vez uno tiene que ser más chico que el resto,
# el lugar donde bajarlo ya existe.
MAX_SIZE_CERTIFICADO = MAX_SIZE_SUBIDA
MAX_SIZE_CSV = MAX_SIZE_SUBIDA
MAX_SIZE_ADJUNTO = MAX_SIZE_SUBIDA
MAX_SIZE_CV = MAX_SIZE_SUBIDA

# El logo es el único que NO sale del techo: 2 MB es criterio propio (un logo institucional no
# pesa 4 MB, y aceptarlo así solo infla el bundle de toda pantalla que lo muestre). Si el techo
# de la plataforma subiera, este NO tiene por qué acompañarlo.
MAX_SIZE_LOGO = 2 * 1024 * 1024  # 2 MB

ALLOWED_TYPES_CERTIFICADO = ("application/pdf", "image/jpeg", "image/png", "image/webp")
ALLOWED_TYPES_IMAGEN = ("image/jpeg", "image/png", "image/webp")
ALLOWED_TYPES_CSV = ("text/csv", "text/plain", "application/vnd.ms-excel", "application/octet-stream")
# .xlsx es un ZIP: algunos navegadores mandan el MIME largo de OOXML, otros `octet-stream`, y
# `vnd.ms-excel` aparece cuando el sistema lo asocia al Excel viejo. Los tres se aceptan porque
# el MIME lo declara el CLIENTE y no es verificable; quien de verdad valida el formato es
# `_import_excel.abrir`, que falla con un mensaje claro si el archivo no es un Excel legible.
ALLOWED_TYPES_EXCEL = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/octet-stream",
)
# Adjuntos genéricos: PDF, Word (.docx), Excel (.xlsx) e imágenes.
ALLOWED_TYPES_ADJUNTO = (
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/jpeg",
    "image/png",
    "image/webp",
)


def mensaje_supera_tamano(field_name: str, max_size: int) -> str:
    """Mensaje único de "archivo demasiado grande", para que el número no se escriba dos veces.

    Lo usan `validate_upload` y `CvService.validar` — este último no puede usar `validate_upload`
    entero porque tiene su propio code/status (`CV_TOO_LARGE`, 413) y cambiarlos sería alterar el
    contrato HTTP sin motivo. Lo que sí comparte es de dónde sale el texto y el límite.

    `:g` en vez de división entera: con un límite de 4,2 MB, `//` mostraba "4 MB" y le mentía al
    usuario sobre cuánto puede subir. `:g` saca los ceros sobrantes, así que un límite redondo
    sigue diciendo "2 MB" y el de 4,2 dice "4.2 MB".
    """
    return f"El {field_name} supera el tamaño máximo de {max_size / (1024 * 1024):g} MB"


def validate_upload(
    content: bytes,
    content_type: str | None,
    allowed_types: tuple[str, ...],
    max_size: int,
    field_name: str,
) -> None:
    """
    Valida tamaño y MIME type de un archivo ya leído en memoria (post-read).

    Args:
        content: Bytes del archivo (resultado de `await file.read()`).
        content_type: MIME declarado por el cliente (`file.content_type`); puede ser None.
        allowed_types: MIME types permitidos para este endpoint.
        max_size: Tamaño máximo permitido, en bytes.
        field_name: Nombre legible del campo, usado en los mensajes de error.

    Raises:
        AppError: FILE_TOO_LARGE (400) si supera max_size; MISSING_CONTENT_TYPE (400)
                  si content_type es None; INVALID_FILE_TYPE (400) si el MIME no está permitido.
    """
    if len(content) > max_size:
        raise AppError(mensaje_supera_tamano(field_name, max_size), "FILE_TOO_LARGE", 400)
    if content_type is None:
        raise AppError(f"No se pudo determinar el tipo del {field_name}", "MISSING_CONTENT_TYPE", 400)
    if content_type not in allowed_types:
        raise AppError(f"Tipo de {field_name} no permitido. Permitidos: {', '.join(allowed_types)}", "INVALID_FILE_TYPE", 400)

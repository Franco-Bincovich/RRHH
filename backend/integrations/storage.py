"""
Punto de contacto ÚNICO con el almacenamiento de archivos.

Hoy adentro hay Supabase Storage; mañana hay S3. **Ese cambio tiene que ocurrir SOLO en este
archivo.** Es la recomendación #2 de las tres migraciones anteriores: un wrapper simétrico, para
que el código de negocio no se toque el día del cutover.

## Por qué vive en `integrations/` y no en `services/`

Es la convención del repo: `integrations/` son los wrappers de servicios externos
(`supabase_client.py`, `anthropic_client.py`), y este archivo **no tiene una sola línea de
negocio** — no valida tamaños ni tipos, no arma paths, no audita, no decide permisos. Todo eso
se queda en los services, donde ya estaba.

⚠️ El contraejemplo aparente es `services/mailer/`, que también es punto de salida único y también
habla con un proveedor externo (Gmail). La diferencia es qué OWNEA cada uno: `mailer` es dueño de
las plantillas, el render de Markdown y la allowlist de variables —negocio— y apenas CONTIENE un
`_gmail.py` como submódulo privado. Acá no hay nada que ownear: son cuatro llamadas.

Y hay una razón práctica que decide el empate: el día del cutover, el archivo que cambia de
proveedor conviene que esté al lado del otro que cambia por lo mismo (`supabase_client.py`), no
en medio de la capa de negocio.

## Qué API expone, y por qué esta

Cuatro verbos y tres constantes. La API es **neutral al proveedor a propósito**: afuera no se ve
`from_()`, ni `file_options`, ni la clave `signedURL` del dict que devuelve Supabase. Todo eso es
vocabulario de ESTE proveedor, y si se filtrara a los services, el cutover los tocaría a los seis.

🔴 **`bucket` se recibe como `str`, no como Enum, y es deliberado.** `adjuntos.bucket` es una
COLUMNA con `DEFAULT 'documentos'`: el nombre está grabado en filas de producción, no solo en el
código. Dos caminos leen el bucket DE LA FILA y no de una constante —la descarga de un adjunto y
el borrado masivo—, así que el módulo tiene que poder operar sobre un valor que llega de la base.
Un Enum obligaría a validar ahí, y un valor viejo o inesperado pasaría de "fallar en el proveedor"
a "fallar en la conversión": otro error, en otro lugar. Esta sesión no cambia comportamiento.

## Lo que este módulo NO hace, y no es olvido

- **No atrapa errores.** El borrado de un adjunto y el de un CV envuelven su llamada en
  `try/except` con un log propio, porque los dos deciden "si Storage falla, seguí igual y dejá el
  objeto huérfano". Esa decisión es de negocio y se queda en el service. Traerla acá unificaría
  dos criterios que hoy son iguales por casualidad, no por diseño.
- **No arma paths.** Cada módulo tiene su convención (`adjuntos/{entidad}/{id}/...`,
  `logos/{id}/...`, `{empresa}/{candidato}/...`) y son parte de su dominio.
- **No valida tipo ni tamaño.** Eso ya vive en `utils/validacion_archivos.py` y en cada service.
"""
from typing import List

from integrations.supabase_client import supabase_admin

# Los tres buckets del sistema. Son los nombres REALES en el proveedor: cambiarlos acá no los
# renombra allá, y `adjuntos.bucket` además los tiene grabados en filas ya escritas.
DOCUMENTOS = "documentos"   # adjuntos polimórficos + certificados de capacitación (privado)
CVS = "cvs"                 # CVs de candidatos (privado)
AVATARS = "avatars"         # logos de empresa (PÚBLICO: es el único con URL pública)


def subir(bucket: str, path: str, content: bytes, content_type: str) -> None:
    """Sube un archivo. `content_type` viaja como metadato del objeto.

    Args:
        bucket: uno de DOCUMENTOS/CVS/AVATARS.
        path: la key dentro del bucket. La arma el service, que conoce su convención.
        content: bytes ya validados (tipo y tamaño) por el llamador.
        content_type: MIME. El llamador resuelve el default si puede venir vacío.
    """
    supabase_admin.storage.from_(bucket).upload(
        path=path, file=content, file_options={"content-type": content_type}
    )


def url_firmada(bucket: str, path: str, expires_in: int = 3600) -> str:
    """URL temporal de descarga para un objeto privado.

    🔑 Devuelve el STRING, no el dict del proveedor. Supabase responde `{"signedURL": ...}` y S3
    devuelve la URL pelada; que esa diferencia muera acá adentro es la mitad del valor de este
    módulo. Los tres services que la usaban hacían `res["signedURL"]` cada uno por su lado.
    """
    res = supabase_admin.storage.from_(bucket).create_signed_url(path=path, expires_in=expires_in)
    return res["signedURL"]


def url_publica(bucket: str, path: str) -> str:
    """URL permanente de un objeto en un bucket público. Hoy solo la usa el logo de empresa."""
    return supabase_admin.storage.from_(bucket).get_public_url(path)


def borrar(bucket: str, paths: List[str]) -> None:
    """Borra objetos FÍSICAMENTE. Recibe lista porque el proveedor borra en lote.

    ⚠️ No atrapa nada: los dos llamadores tienen su propio `try/except` con el log que les
    corresponde, y esa decisión es de ellos. Ver el encabezado.
    """
    supabase_admin.storage.from_(bucket).remove(paths)

"""Schemas de plantillas de mail y de envío (migración 087)."""
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class PlantillaBase(BaseModel):
    clave: str
    contexto: str
    asunto: str
    cuerpo: str          # Markdown mínimo, NO HTML — ver services/mailer/_markdown.py
    activa: bool = True


class PlantillaUpsert(PlantillaBase):
    """Alta o edición. `id` presente = edición."""
    id: Optional[UUID] = None


class PlantillaResponse(PlantillaBase):
    id: UUID
    empresa_id: Optional[UUID] = None
    # True = es la plantilla GLOBAL, no una propia de la empresa. El front lo usa para avisar
    # que editarla crea una copia de la empresa en vez de pisar la que ven todas.
    es_global: bool = False
    # 🔴 Lo CALCULA el backend (no lo detecta el front con su propio regex): la regla "una
    # plantilla con variables no se manda a una dirección suelta" tiene que ser UNA sola, y el
    # front solo lee este booleano para deshabilitar el modo libre. Dos regex que se separen
    # darían una pantalla que habilita lo que el backend después rechaza.
    usa_variables: bool = False


class PlantillasListResponse(BaseModel):
    items: List[PlantillaResponse]
    # El catálogo de contextos y sus variables, para que la UI ofrezca solo las válidas y RRHH
    # no las escriba a mano. Viaja con el listado para no pagar un request más.
    contextos: dict


class PreviewRequest(BaseModel):
    contexto: str
    asunto: str
    cuerpo: str
    # None = usar datos de ejemplo. Con datos REALES se ven los huecos reales, que es el punto.
    empleado_id: Optional[UUID] = None


class PreviewResponse(BaseModel):
    asunto: str
    cuerpo_html: str
    # Variables válidas que quedaron SIN VALOR con estos datos. La UI las marca en amarillo:
    # es el momento (3) de los tres, donde RRHH se entera ANTES de mandar.
    faltantes: List[str]
    con_datos_reales: bool


class EnvioRequest(BaseModel):
    """Destinatarios del envío: empleados del sistema O direcciones escritas a mano.

    🔴 `destinatarios_libres` se suma con DEFAULT `[]`, no como campo requerido, y `empleado_ids`
    queda igual: el caller que ya existe sigue compilando y sigue mandando lo mismo. Extender un
    contrato con un campo opcional es lo único que no rompe a nadie — cambiar `empleado_ids` por
    un `destinatarios` polimórfico habría obligado a tocar el front, el service y los 26 tests
    del envío para ganar nada.

    🔴 LOS DOS MODOS NO SE MEZCLAN, y lo rechaza el service (ENVIO_MODO_MIXTO, 422). No es una
    limitación técnica: la regla de las variables aplica a UN modo y no al otro, así que un lote
    mixto sería mitad permitido y mitad no. Y la confirmación de la UI dice "vas a enviar a N
    personas" — con dos fuentes, ese N deja de decir a quién.
    """
    plantilla_clave: str
    empleado_ids: List[UUID] = []
    destinatarios_libres: List[str] = []


class MailEnviadoItem(BaseModel):
    """Una línea del historial. NO incluye `cuerpo_render` a propósito: el texto completo que
    recibió una persona no viaja a una pantalla de listado (ver `mail_enviado_repo`)."""
    id: UUID
    plantilla_clave: Optional[str] = None
    destinatario: str
    asunto_render: str
    estado: str                    # 'enviado' | 'fallido'
    error: Optional[str] = None    # el motivo, solo cuando falló
    created_at: str


class MailHistorialResponse(BaseModel):
    """El historial NO se pagina y NO expone un total: `limite` viaja de vuelta para que la
    pantalla pueda avisar que está viendo un recorte y no el universo."""
    items: List[MailEnviadoItem]
    limite: int


class EnvioResponse(BaseModel):
    enviados: int
    omitidos: int         # ya se les había mandado hoy (idempotencia)
    fallidos: List[dict]
    parcial: bool = False  # se agotó el presupuesto de tiempo
    sin_procesar: int = 0
    segundos: Optional[float] = None

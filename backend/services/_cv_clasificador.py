"""
La llamada al modelo y la validación de su salida. Un CV, una clasificación.

Flujo: `cv_screening_service` (el lote) → acá (uno) → `_clasificador_prompt` (el texto).

## Modelo: Claude Haiku

`claude-haiku-4-5` — alias SIN fecha, como manda CLAUDE.md: los strings con fecha se retiran y
devuelven 404 (ya pasó con `claude-sonnet-4-20250514` el 15/6/2026). Haiku y no Sonnet porque
esto es una clasificación de tres valores sobre un texto corto, que es exactamente lo que un
modelo chico hace bien y barato: se paga una llamada POR CANDIDATO, así que la diferencia de
precio se multiplica por el tamaño del lote.

⚠️ El SDK fijado es `anthropic==0.34.2`, anterior a los structured outputs (`output_config`). Se
pide JSON por prompt y se valida acá. Cuando se actualice el SDK, `output_config` haría el
formato imposible de violar — la validación de abajo **igual se queda**, porque garantizar la
FORMA no garantiza que el valor sea una de las tres categorías.

## 🔴 UNA SALIDA FUERA DE LAS TRES CATEGORÍAS ES UN FALLO, NO UN VALOR

No se interpreta, no se busca la categoría "más parecida", no se cae a `dudoso` por las dudas.
Se levanta, el lote lo cuenta como error y ese candidato queda sin clasificar (NULL) para que
un humano lo mire.

Caer a `dudoso` sería tentador y está mal: convertiría un clasificador roto —un prompt que se
degradó, un modelo que cambió, una inyección que funcionó— en un sistema que parece andar y
manda todo a revisión manual. Nadie miraría los logs y el modo de falla sería invisible durante
meses. Un contador de errores en la respuesta se ve en la primera corrida.
"""
import json
import re
from dataclasses import dataclass
from typing import Any

from integrations.anthropic_client import anthropic_client
from services import _clasificador_prompt as prompt
from utils.errors import AppError

MODELO = "claude-haiku-4-5"

# El motivo es una frase. 300 tokens dan margen de sobra y ponen un techo duro al costo de
# salida de una llamada que se hace una vez por candidato.
MAX_TOKENS = 300

# Tope del motivo al persistir: la columna es TEXT sin límite y esto es salida de un modelo.
MAX_MOTIVO = 400

_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class Clasificacion:
    clasificacion: str
    motivo: str


def clasificar(cv_texto: str, vacante, criterio, cliente: Any = None) -> Clasificacion:
    """Clasifica UN CV contra UNA búsqueda.

    Args:
        vacante: la `VacanteResponse` ENTERA — los SIETE campos de la búsqueda entran al prompt.
            Ver `_busqueda_prompt`: esta firma tomaba dos strings y por eso los otros cinco no
            llegaban al modelo.
        cliente: cliente Anthropic. Inyectable para test — el fake tiene que registrar `system`
            y `messages` por separado, o no se puede desmentir que el CV haya viajado en el
            system prompt.

    Raises:
        AppError: CLASIFICACION_INVALIDA (502) si el modelo devolvió algo que no es una de las
            tres categorías. Ver el encabezado: es un fallo, no un valor.
    """
    cli = cliente or anthropic_client
    respuesta = cli.messages.create(
        model=MODELO,
        max_tokens=MAX_TOKENS,
        # 🔴 SIEMPRE separado del contenido no confiable. El CV y el criterio configurable van
        # en `messages`; en `system` no se concatena nada que venga de afuera.
        system=prompt.system_prompt(),
        messages=[{
            "role": "user",
            "content": prompt.armar_user(cv_texto, vacante, criterio),
        }],
    )
    return _validar(_texto_de(respuesta))


def _texto_de(respuesta: Any) -> str:
    bloques = getattr(respuesta, "content", None) or []
    return "".join(getattr(b, "text", "") for b in bloques)


def _validar(crudo: str) -> Clasificacion:
    """Del texto del modelo a una Clasificacion, o AppError. No interpreta: valida."""
    try:
        datos = json.loads(_FENCE.sub("", crudo).strip())
    except (ValueError, TypeError):
        raise AppError("El clasificador devolvió una respuesta que no se pudo leer.",
                       "CLASIFICACION_INVALIDA", 502)
    if not isinstance(datos, dict):
        raise AppError("El clasificador devolvió una respuesta con forma inesperada.",
                       "CLASIFICACION_INVALIDA", 502)
    etiqueta = datos.get("clasificacion")
    # Igualdad exacta contra el conjunto cerrado. Nada de `in` sobre el string ni de normalizar
    # variantes: "no es relevante" contiene "relevante" y significa lo contrario.
    if etiqueta not in prompt.CATEGORIAS:
        raise AppError(f"El clasificador devolvió una categoría desconocida: {etiqueta!r}.",
                       "CLASIFICACION_INVALIDA", 502)
    motivo = datos.get("motivo")
    if not isinstance(motivo, str) or not motivo.strip():
        raise AppError("El clasificador no devolvió un motivo.", "CLASIFICACION_INVALIDA", 502)
    return Clasificacion(clasificacion=etiqueta, motivo=motivo.strip()[:MAX_MOTIVO])

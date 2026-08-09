"""
El texto que RRHH pega en el aviso de LinkedIn: a qué casilla mandar el CV y con qué asunto.

Función libre que recibe sus colaboradores — molde `_vacante_write.crear(repo, audit, ...)`.

## 🔴 POR QUÉ LA FRASE LA ARMA EL BACKEND Y NO LA PANTALLA

Es la instrucción que va a leer un candidato de afuera, y **de que la escriba igual todas las
veces depende que el matcher encuentre el código**. Si la arma el front —o peor, si RRHH la
tipea— cada aviso sale con una variante: "asunto VAC-0001", "ref. VAC 0001", "poner el código
en el asunto". Con los corchetes perdidos o el guion cambiado, el mail entra igual pero el
código no matchea, y el CV termina en "sin asignar" sin que nada haya fallado visiblemente.

Los corchetes son parte del token, no decoración: acotan la búsqueda dentro del asunto y evitan
que `VAC-0001` matchee dentro de otra palabra. Por eso viajan en la plantilla y no se dejan al
criterio de quien copia.

## La casilla

Sale de `get_remitente()` —la casilla del SISTEMA, no la del usuario que está mirando la
pantalla—, que es la misma de la que salen los mails y la misma que va a leer el CV screening.
Ver `repositories/integracion_remitente_repo.py`.

⚠️ **Sin casilla designada NO se inventa un texto a medias.** Un aviso que diga "Enviá tu CV a
None" es peor que no ofrecer nada: se publica y nadie se entera hasta que no llega ni un CV.
`texto` sale en None y la pantalla muestra qué falta configurar. El `codigo` se devuelve igual
—existe, es de la vacante y no depende de ninguna integración—, así que RRHH puede copiarlo
aunque la casilla todavía no esté puesta.
"""
from typing import Optional
from uuid import UUID

from schemas.vacante import AvisoPostulacionResponse
from services._vacante_write import _or_404

# El literal ÚNICO de la instrucción. Cambiar acá cambia todos los avisos futuros a la vez.
_PLANTILLA = "Enviá tu CV a {casilla} con el asunto [{codigo}]"


def aviso(repo, remitente_repo, vacante_id: UUID,
          empresa_id: Optional[UUID] = None) -> AvisoPostulacionResponse:
    """Arma el texto para el aviso de una vacante.

    Args:
        repo: VacanteRepo (o doble de test).
        remitente_repo: IntegracionRemitenteRepo (o doble) con `get_remitente()`.
        vacante_id: UUID de la vacante.
        empresa_id: barrera de empresa; None = consolidado (no restringe).

    Returns:
        AvisoPostulacionResponse con el código siempre, y casilla/texto solo si hay casilla.

    Raises:
        AppError: VACANTE_NOT_FOUND (404) si no existe o es de otra empresa — mismo literal que
            el resto del módulo, vía `_or_404`.
    """
    vacante = _or_404(repo.find_by_id(str(vacante_id), empresa_id))
    fila = remitente_repo.get_remitente()
    # `get_remitente()` devuelve la fila ENTERA o None. `.get()` sobre el dict, no un atributo:
    # es un dict crudo de Supabase, no un schema.
    casilla: Optional[str] = (fila or {}).get("email_cuenta")
    return AvisoPostulacionResponse(
        codigo=vacante.codigo,
        casilla=casilla,
        texto=_PLANTILLA.format(casilla=casilla, codigo=vacante.codigo) if casilla else None,
    )

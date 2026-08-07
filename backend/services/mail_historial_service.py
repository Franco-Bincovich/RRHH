"""
Historial de mails enviados: qué salió, a quién, cuándo y —si falló— por qué.

El dato se venía escribiendo desde la migración 087 y **no lo veía nadie**: `mail_enviado` tenía
el log completo y ni endpoint ni pantalla. Cuando alguien decía "no me llegó", la única forma de
contestar era abrir la base.

## 🔴 ESTE MÓDULO NO EXPORTA, Y NO ES UN OLVIDO
`mail_enviado` guarda datos personales por definición: nombre, dirección y el cuerpo entero del
mail. Un Excel con eso es exactamente el archivo que no se quiere que circule, así que no hay
`exportar()` ni lo va a haber — la decisión está escrita en `repositories/mail_enviado_repo.py` y
esto la respeta en vez de reabrirla. Consecuencia práctica: este listado **no aparece** en
`tests/test_paridad_list_export.py`, que solo empareja listados que TIENEN export.

## Y NO PAGINA
Por el mismo motivo. Se devuelven los últimos N (techo duro de 200 en el repo) y `limite` viaja
en la respuesta para que la pantalla pueda decir que está viendo un recorte. Paginar convertiría
un diagnóstico acotado en un volcado de la tabla, que es justo lo que se evita.
"""
from datetime import datetime, time, timezone
from typing import Optional
from uuid import UUID

from repositories.mail_enviado_repo import MailEnviadoRepo
from schemas.plantillas import MailEnviadoItem, MailHistorialResponse
from utils.errors import AppError

ESTADOS_VALIDOS = frozenset({"enviado", "fallido"})
LIMITE_DEFAULT = 100


class MailHistorialService:
    def __init__(self, repo: Optional[MailEnviadoRepo] = None) -> None:
        self._repo = repo or MailEnviadoRepo()

    def listar(self, empresa_id: Optional[UUID] = None, estado: Optional[str] = None,
               desde: Optional[str] = None, hasta: Optional[str] = None,
               limite: int = LIMITE_DEFAULT) -> MailHistorialResponse:
        """Los últimos envíos que cumplen el filtro, del más reciente al más viejo.

        Args:
            empresa_id: la del request. None = consolidado.
            estado: 'enviado' | 'fallido'. None = los dos.
            desde / hasta: fechas `YYYY-MM-DD` del filtro de rango.
            limite: techo pedido; el repo lo capa en 200.

        Returns:
            MailHistorialResponse con los ítems y el límite efectivo.

        Raises:
            AppError: ESTADO_INVALIDO (422) si `estado` no es uno de los dos conocidos.
        """
        if estado and estado not in ESTADOS_VALIDOS:
            raise AppError(f"Estado desconocido: {estado}", "ESTADO_INVALIDO", 422)
        filas = self._repo.ultimos(empresa_id=empresa_id, limite=limite, estado=estado,
                                   desde=_desde(desde), hasta=_hasta(hasta))
        return MailHistorialResponse(items=[MailEnviadoItem(**f) for f in filas], limite=limite)


def _desde(fecha: Optional[str]) -> Optional[str]:
    """`YYYY-MM-DD` → comienzo de ese día en UTC."""
    return _borde(fecha, time.min)


def _hasta(fecha: Optional[str]) -> Optional[str]:
    """`YYYY-MM-DD` → FIN de ese día en UTC.

    🔴 El borde superior se estira al final del día a propósito. `created_at` es un timestamp:
    comparar contra la fecha pelada equivale a las 00:00, así que "hasta el 7/8" dejaría afuera
    TODO lo enviado el 7/8. Es el error clásico de los filtros por rango, y acá el síntoma sería
    "el mail que mandé hoy no aparece en el historial" — que se lee como que el envío falló.
    """
    return _borde(fecha, time.max)


def _borde(fecha: Optional[str], hora: time) -> Optional[str]:
    """Compone fecha + hora en UTC. Una fecha ilegible se ignora en vez de romper: el filtro lo
    arma la UI con un `<input type="date">`, y perder el filtro es mejor que perder la pantalla."""
    if not fecha:
        return None
    try:
        dia = datetime.strptime(fecha[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
    return datetime.combine(dia, hora, tzinfo=timezone.utc).isoformat()

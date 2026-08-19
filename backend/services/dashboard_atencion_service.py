"""
El panel "Requiere tu atención" (A6): UNA lista con las alertas calculadas y las manuales,
distinguibles por `origen`. Las calculadas viven en `_dashboard_atencion_calculadas.py` — el
prefijo `_dashboard` no es cosmético: lo mete en la familia "dashboard" de
`tests/test_acceso_a_datos.py`, que es la que puede consultar supabase directo; las manuales son
los eventos de agenda en su ventana de aviso, vía `EventoAgendaService.pendientes` — que desde
esta sesión tiene este único caller: su endpoint HTTP (`GET /api/eventos/pendientes`) se BORRÓ
porque este panel lo reemplaza y dos endpoints vivos para lo mismo es lo que el barrido de
huérfanos existe para impedir.

🔴 DOS CICLOS DE VIDA DISTINTOS, Y NO SE MEZCLAN:
  · una MANUAL nace de una fila (`eventos_agenda`), se marca resuelta —estado PERSISTIDO, con
    fecha y autor— y ahí desaparece del panel.
  · una CALCULADA no tiene fila ni estado: desaparece cuando desaparece SU CAUSA (la persona se
    activó, el período de prueba venció). NO se puede resolver a mano, y no es una limitación
    sino la única semántica consistente: "resolverla" exigiría persistir ese resuelto en algún
    lado, y como la lista se DERIVA al leer, la misma causa la volvería a levantar al día
    siguiente — una alerta zombi que reaparece ya "resuelta". Por eso `resolver` la rechaza con
    código propio (`ALERTA_NO_RESOLUBLE`) en vez de fingir que la resolvió.

🔴 TODO SE RESUELVE AL LEER. Nada depende de un job ni de un precálculo (no existen en este
deploy): cada GET evalúa las ventanas contra `hoy`.
"""
from datetime import date
from typing import List, Optional
from uuid import UUID

from schemas.dashboard_atencion import (
    AlertaAtencion, AtencionResponse, ResolverAtencionRequest,
)
from schemas.evento_agenda import EventoResponse
from services._dashboard_atencion_calculadas import fin_de_prueba, ingresos_proximos
from services.configuracion_service import ConfiguracionService
from services.evento_agenda_service import EventoAgendaService
from utils.errors import AppError


class DashboardAtencionService:
    def __init__(self, eventos: Optional[EventoAgendaService] = None,
                 configuracion: Optional[ConfiguracionService] = None) -> None:
        self._eventos = eventos or EventoAgendaService()
        self._configuracion = configuracion or ConfiguracionService()

    def listar(self, empresa_id: Optional[UUID] = None, user_id: Optional[str] = None,
               rol: Optional[str] = None, hoy: Optional[date] = None) -> AtencionResponse:
        """Las dos clases en una sola lista, ordenadas por la fecha del hecho.

        `user_id`/`rol` solo los usan las manuales (un evento privado ajeno no aparece — la
        visibilidad la aplica el WHERE del repo de eventos); las calculadas se derivan del
        padrón, que no tiene eje de visibilidad. `hoy` entra como parámetro para que un test
        fije la fecha, igual que en `EventoAgendaService.pendientes`.
        """
        hoy = hoy or date.today()
        alertas = (ingresos_proximos(empresa_id, hoy)
                   + fin_de_prueba(empresa_id, hoy, self._configuracion)
                   + self._manuales(empresa_id, user_id, rol, hoy))
        # Un solo orden para las dos clases: la fecha del hecho, lo urgente arriba. Las sin
        # fecha van al final — sin fecha no hay urgencia que estimar, pero no desaparecen.
        return AtencionResponse(alertas=sorted(alertas, key=lambda a: a.fecha or date.max))

    def _manuales(self, empresa_id: Optional[UUID], user_id: Optional[str],
                  rol: Optional[str], hoy: date) -> List[AlertaAtencion]:
        """Los eventos en ventana de aviso, como alertas con autor (pedido del sistema de
        diseño: "las manuales llevan el nombre de quien las creó")."""
        return [
            AlertaAtencion(origen="manual", tipo="evento_manual", mensaje=e.nombre,
                           fecha=e.fecha, href="/eventos", evento_id=e.id,
                           creado_por_nombre=e.created_by_nombre)
            for e in self._eventos.pendientes(empresa_id, user_id, rol, hoy)
        ]

    def resolver(self, body: ResolverAtencionRequest, empresa_id: Optional[UUID],
                 user_id: Optional[str], rol: Optional[str]) -> EventoResponse:
        """Resuelve una alerta MANUAL delegando en el write path de eventos (mismas tres
        columnas coherentes, misma auditoría, mismo 404 único).

        Raises:
            AppError: ALERTA_NO_RESOLUBLE (409) si es una calculada — ver el encabezado.
            AppError: EVENTO_REQUERIDO (422) si es manual y no trae `evento_id`.
        """
        if body.origen == "calculada":
            raise AppError(
                "Una alerta calculada no se resuelve a mano: desaparece sola cuando desaparece "
                "su causa (la persona ingresó, el período de prueba terminó).",
                "ALERTA_NO_RESOLUBLE", 409)
        if body.evento_id is None:
            raise AppError("Falta el evento a resolver", "EVENTO_REQUERIDO", 422)
        return self._eventos.resolver(body.evento_id, True, empresa_id, user_id, rol)

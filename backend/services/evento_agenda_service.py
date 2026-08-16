"""
Servicio de la agenda de eventos (migración 113).
Flujo: router → service → repository → DB

QUÉ ES. Recordatorios manuales con fecha, que el dashboard levanta cuando se acercan. Registro
simple: no hay flujo de aprobación, y **se puede editar y borrar** (decisión de producto: un
evento no es un registro histórico, es un aviso, y uno cargado por error no tiene por qué quedar).

🔴 LOS DOS EJES DE ACCESO VAN SIEMPRE JUNTOS Y SE COMPONEN POR INTERSECCIÓN — empresa ∩
visibilidad —, y los aplica el WHERE del repo, no este archivo. La única razón por la que el
service los toca es para PASARLOS: el router que recibe `user_id` y no lo pasa hacia abajo se lee
igual de seguro y publica las privadas de todo el mundo. Es el falso positivo que apareció tres
veces en el barrido de Fase 2, con `empresa_id` en vez de `user_id`.

🔴 EL DEFAULT DE `dias_aviso` SE RESUELVE ACÁ Y NO EN EL SCHEMA. Sale de
`parametros_empresa.dias_aviso_evento` (migración 114), que es lo que la pantalla de
Configuración edita. Un literal en el schema sería una tercera definición del mismo número y
además la que gana, dejando esa pantalla sin efecto sobre los eventos nuevos.

⚠️ LA EMPRESA DEL EVENTO SALE DEL HEADER, y es correcto pese a "Vista vs Acción": esa regla dice
que la empresa de una acción sale del FORMULARIO o de la ENTIDAD PADRE, nunca del sidebar. Un
evento de agenda no tiene padre, así que su empresa la elige quien lo carga — y elegirla ES
mover el selector. Por eso el router usa `require_empresa_id`: en modo consolidado no hay a qué
empresa cargarlo, y el error se lo dice al usuario en vez de adivinar.
"""
from datetime import date
from math import ceil
from typing import List, Optional
from uuid import UUID

from repositories.evento_agenda_repo import EventoAgendaRepo
from schemas.evento_agenda import (
    EventoCreate, EventoListResponse, EventoResponse, EventoUpdate,
)
from services import _eventos_pendientes as pendientes_mod
from services._eventos_write import NO_ENCONTRADO, borrar, crear, editar, resolver
from services.audit_service import AuditService
from services.configuracion_service import ConfiguracionService
from utils.errors import AppError


class EventoAgendaService:
    def __init__(self, repo: Optional[EventoAgendaRepo] = None,
                 configuracion: Optional[ConfiguracionService] = None,
                 audit: Optional[AuditService] = None) -> None:
        self._repo = repo or EventoAgendaRepo()
        self._configuracion = configuracion or ConfiguracionService()
        self._audit = audit or AuditService()

    # ── Lectura ───────────────────────────────────────────────────────────────────────────

    def listar(self, page: int = 1, page_size: int = 20, empresa_id: Optional[UUID] = None,
               user_id: Optional[str] = None, rol: Optional[str] = None,
               incluir_resueltas: bool = False) -> EventoListResponse:
        """La agenda, paginada por fecha ascendente. Los resueltos entran solo si se piden."""
        items, total = self._repo.find_all(page, page_size, empresa_id, user_id, rol,
                                           incluir_resueltas)
        return EventoListResponse(
            items=items, total=total, page=page, page_size=page_size,
            total_pages=max(1, ceil(total / page_size)) if page_size else 1)

    def obtener(self, id: UUID, empresa_id: Optional[UUID] = None,
                user_id: Optional[str] = None, rol: Optional[str] = None) -> EventoResponse:
        """Detalle. 404 idéntico para "no existe", "es de otra empresa" y "es privado de otro"."""
        fila = self._repo.find_by_id(str(id), empresa_id, user_id, rol)
        if not fila:
            raise AppError(*NO_ENCONTRADO)
        return fila

    def pendientes(self, empresa_id: Optional[UUID] = None, user_id: Optional[str] = None,
                   rol: Optional[str] = None,
                   hoy: Optional[date] = None) -> List[EventoResponse]:
        """Los eventos que hay que avisar hoy. Lo que consume el dashboard.

        Dos pasos, y el reparto entre ellos está explicado en `_eventos_pendientes`: la query
        acota por empresa, visibilidad, `NOT resuelta` y un techo de fecha EXACTO; el
        `fecha - dias_aviso <= hoy` —que PostgREST no puede expresar— se resuelve en Python
        sobre ese conjunto ya chico.

        `hoy` entra como parámetro (default: el día real) para que un test pueda fijar la fecha
        en vez de depender de cuándo corre.
        """
        hoy = hoy or date.today()
        candidatos = self._repo.find_candidatos_aviso(
            pendientes_mod.techo_de_fecha(hoy), empresa_id, user_id, rol)
        return pendientes_mod.filtrar(candidatos, hoy)

    # ── Escritura ─────────────────────────────────────────────────────────────────────────

    def crear(self, data: EventoCreate, empresa_id: UUID, user_id: str) -> EventoResponse:
        """Alta. Resuelve el `dias_aviso` por defecto y delega en `_eventos_write.crear`."""
        dias = data.dias_aviso if data.dias_aviso is not None else self._dias_aviso(empresa_id)
        return crear(self._repo, self._audit, data, empresa_id, dias, user_id)

    def editar(self, id: UUID, data: EventoUpdate, empresa_id: Optional[UUID],
               user_id: Optional[str], rol: Optional[str]) -> EventoResponse:
        """Edición parcial. Delegado a `_eventos_write.editar`."""
        return editar(self._repo, self._audit, id, data, empresa_id, user_id, rol)

    def resolver(self, id: UUID, resuelta: bool, empresa_id: Optional[UUID],
                 user_id: Optional[str], rol: Optional[str]) -> EventoResponse:
        """Marca o desmarca como resuelto. Delegado a `_eventos_write.resolver`."""
        return resolver(self._repo, self._audit, id, resuelta, empresa_id, user_id, rol)

    def borrar(self, id: UUID, empresa_id: Optional[UUID], user_id: Optional[str],
               rol: Optional[str]) -> None:
        """Baja física. Delegado a `_eventos_write.borrar`."""
        borrar(self._repo, self._audit, id, empresa_id, user_id, rol)

    def _dias_aviso(self, empresa_id: UUID) -> int:
        """El default de la empresa, o el global si todavía no tiene fila propia.

        Lo resuelve `ConfiguracionService`, que ya implementa ese COALESCE y es el único lugar
        donde vive. Reimplementarlo acá con una lectura directa daría dos criterios sobre cuál
        es "el parámetro vigente" el día que la resolución cambie.
        """
        return self._configuracion.get_parametros(empresa_id).dias_aviso_evento

"""
Repositorio de la agenda de eventos (migración 113). Acceso con supabase_admin.

Está partido en tres y la clase delega, así que sigue siendo la única puerta del service:
escrituras en `_evento_agenda_write_repo.py` · mapper en `_evento_agenda_row.py` · los tres
filtros de lectura en `_evento_agenda_filtros.py`. Acá quedan las TRES LECTURAS.

DOS VISTAS DE LA MISMA TABLA, con formas distintas a propósito:
  · `find_all` → la agenda. PAGINADA, por `fecha` ascendente, con el toggle de resueltos.
  · `find_candidatos_aviso` → lo que consume el dashboard. LISTA PLANA, sin paginar y sin
    resueltos: son los que caen dentro de su ventana de aviso, decenas y no miles.
Las dos ya tienen su índice desde la 113 (`idx_eventos_agenda_pendientes`, parcial sobre
`NOT resuelta`, e `idx_eventos_agenda_privados_autor`, parcial sobre las privadas).
"""
from datetime import date
from typing import List, Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._evento_agenda_filtros import con_empresa, con_pendientes, con_visibilidad
from repositories._evento_agenda_row import SELECT, TABLE, build
from repositories._evento_agenda_write_repo import actualizar, borrar, guardar, marcar_resuelta
from schemas.evento_agenda import EventoCreate, EventoResponse, EventoUpdate


class EventoAgendaRepo:
    def _visible(self, q, empresa_id, user_id, rol):
        """Los dos ejes de acceso, SIEMPRE juntos y en este orden: empresa ∩ visibilidad."""
        return con_visibilidad(con_empresa(q, empresa_id), user_id, rol)

    def find_all(self, page: int = 1, page_size: int = 20, empresa_id: Optional[UUID] = None,
                 user_id: Optional[str] = None, rol: Optional[str] = None,
                 incluir_resueltas: bool = False) -> Tuple[List[EventoResponse], int]:
        """Página de la agenda + el total REAL del filtro (sin paginar).

        Ordena por `fecha` ASCENDENTE: lo primero que se lee es lo más urgente, incluidos los
        vencidos sin resolver, que son justamente los que nadie atendió.
        """
        q = self._visible(supabase_admin.table(TABLE).select(SELECT, count="exact"),
                          empresa_id, user_id, rol)
        # `.order("id")` = desempate, y NO es cosmético: `fecha` es una FECHA (sin hora) y varios
        # eventos del mismo día son la norma. Sin segunda clave, el orden de los empatados no lo
        # garantiza nadie, y dos pedidos de páginas distintas pueden traer la MISMA fila dos
        # veces y saltear otra. Mismo criterio que la planilla de recategorizaciones.
        res = (con_pendientes(q, incluir_resueltas).order("fecha").order("id")
               .range((page - 1) * page_size, page * page_size - 1).execute())
        return build(res.data or []), (res.count or 0)

    def find_by_id(self, id: str, empresa_id: Optional[UUID] = None,
                   user_id: Optional[str] = None,
                   rol: Optional[str] = None) -> Optional[EventoResponse]:
        """Un evento, o None si no existe, es de otra empresa o es privado de otro."""
        q = self._visible(supabase_admin.table(TABLE).select(SELECT).eq("id", id),
                          empresa_id, user_id, rol)
        filas = build(q.limit(1).execute().data or [])
        return filas[0] if filas else None

    def find_candidatos_aviso(self, techo: date, empresa_id: Optional[UUID] = None,
                              user_id: Optional[str] = None,
                              rol: Optional[str] = None) -> List[EventoResponse]:
        """Los NO resueltos con `fecha <= techo`. El descarte fino lo hace el service.

        🔴 NO LLEVA `fecha >= hoy`, y es la mitad del diseño: un evento no desaparece por vencer,
        desaparece cuando alguien lo marca. Uno del 1/10 sin resolver tiene que seguir apareciendo
        el 15/10 — es el que se pasó por alto, o sea el que más importa.

        El `techo` lo calcula el service como `hoy + 365`, y 365 no es un número elegido: es el
        máximo que admite el CHECK `eventos_agenda_dias_aviso_check`, así que ningún evento fuera
        de ese horizonte puede estar todavía dentro de su ventana de aviso. El recorte es EXACTO,
        no una heurística: no descarta ningún candidato posible y evita traer la agenda entera.
        """
        q = self._visible(supabase_admin.table(TABLE).select(SELECT), empresa_id, user_id, rol)
        return build(con_pendientes(q, False).lte("fecha", str(techo))
                     .order("fecha").order("id").execute().data or [])

    def save(self, data: EventoCreate, empresa_id: UUID, dias_aviso: int,
             created_by: str) -> Optional[EventoResponse]:
        """Alta. Escribe y relee para que la fila salga con los nombres de join resueltos."""
        return self.find_by_id(guardar(data, empresa_id, dias_aviso, created_by)["id"])

    def update(self, id: str, data: EventoUpdate) -> Optional[EventoResponse]:
        """Edición parcial. Escribe y devuelve la fila resultante (o None si no existe)."""
        actualizar(id, data)
        return self.find_by_id(id)

    def set_resuelta(self, id: str, resuelta: bool,
                     usuario_id: Optional[str]) -> Optional[EventoResponse]:
        """Toggle de resuelta, en los dos sentidos. Delega en `marcar_resuelta`."""
        marcar_resuelta(id, resuelta, usuario_id)
        return self.find_by_id(id)

    def delete(self, id: str) -> None:
        """Baja física. El snapshot para la auditoría lo toma el service ANTES de llamar acá."""
        borrar(id)

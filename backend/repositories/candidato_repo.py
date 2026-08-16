"""
Repositorio de candidatos. Acceso a Supabase con supabase_admin.
Interfaz pública: find_candidatos · find_pagina · claves_de_grupo · find_by_id · save_candidato ·
asignar_vacante · update_etapa_candidato · delete · congelar_busqueda
Todas las operaciones reciben empresa_id opcional para filtrado multiempresa.

El mapper de fila vive en `_candidato_row.py`, el write path en `_candidato_write.py`, las dos
lecturas de la ingesta por mail en `_candidato_gmail.py` y EL LISTADO —con su paginación y su
conteo por grupo— en `_candidato_listado_repo.py`. El repo llegó a 100/100 exacto dos veces; el
listado salió la segunda porque es lo único que crece con cada filtro nuevo. Molde: `empleado_repo`.
"""
from typing import List, Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories import _candidato_gmail as _g
from repositories import _candidato_listado_repo as _l
from repositories import _candidato_write as _w
from repositories._candidato_row import _crow
from schemas.candidato import CandidatoCreate, CandidatoResponse

_C = "candidatos"


class CandidatoRepo:

    # ── Lecturas ──────────────────────────────────────────────────────────────

    def find_candidatos(self, vacante_id: str, empresa_id: Optional[UUID] = None) -> List[CandidatoResponse]:
        """Retorna candidatos de una vacante, filtrados por empresa si se provee."""
        q = supabase_admin.table(_C).select("*").eq("vacante_id", vacante_id).order("created_at")
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        return [_crow(r) for r in (q.execute().data or [])]

    # ── El LISTADO (delegado a _candidato_listado_repo, que es la parte que crece) ──

    def find_pagina(self, empresa_id: Optional[UUID] = None, sin_vacante: bool = False,
                    clasificacion: Optional[str] = None, page: int = 1, page_size: int = 20,
                    ) -> Tuple[List[CandidatoResponse], int]:
        """Una página del listado + el total del filtro. Delegado a _candidato_listado_repo."""
        return _l.pagina(empresa_id, sin_vacante, clasificacion, page, page_size)

    def claves_de_grupo(self, empresa_id: Optional[UUID] = None, sin_vacante: bool = False,
                        clasificacion: Optional[str] = None) -> List[dict]:
        """La clave de agrupamiento de cada fila del filtro, en UNA query."""
        return _l.claves_de_grupo(empresa_id, sin_vacante, clasificacion)

    def find_by_id(self, candidato_id: str, empresa_id: Optional[UUID] = None) -> Optional[CandidatoResponse]:
        """Busca un candidato por UUID. Si empresa_id se provee, valida pertenencia (fail-closed)."""
        q = supabase_admin.table(_C).select("*").eq("id", candidato_id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.maybe_single().execute()
        return _crow(res.data) if res and res.data else None

    def existe_cv_de_gmail(self, empresa_id: str, message_id: str, sha256: str) -> bool:
        """Delegado a _candidato_gmail.existe_cv (idempotencia por adjunto)."""
        return _g.existe_cv(empresa_id, message_id, sha256)

    def message_ids_procesados(self, message_ids) -> set:
        """Delegado a _candidato_gmail.message_ids_procesados (idempotencia por mensaje)."""
        return _g.message_ids_procesados(message_ids)

    # ── Escrituras (delegadas a _candidato_write) ─────────────────────────────

    def save_candidato(self, vacante_id: str, data: CandidatoCreate, empresa_id: str,
                       origen: Optional[dict] = None) -> CandidatoResponse:
        """Alta de candidato. Delegado a _candidato_write.guardar."""
        return _w.guardar(vacante_id, data, empresa_id, origen)

    def set_cv(self, candidato_id: str, cv_storage_path: str) -> None:
        """Delegado a _candidato_write.set_cv."""
        _w.set_cv(candidato_id, cv_storage_path)

    def asignar_vacante(self, candidato_id: str, vacante_id: str,
                        empresa_id: Optional[UUID] = None) -> Optional[CandidatoResponse]:
        """Asigna una vacante a un candidato huérfano. Delegado a _candidato_write."""
        return _w.asignar_vacante(candidato_id, vacante_id, empresa_id)

    def update_etapa_candidato(self, candidato_id: str, etapa: str,
                               empresa_id: Optional[UUID] = None) -> Optional[CandidatoResponse]:
        """Delegado a _candidato_write.update_etapa."""
        return _w.update_etapa(candidato_id, etapa, empresa_id)

    def delete(self, candidato_id: str, empresa_id: Optional[UUID] = None) -> None:
        """Delegado a _candidato_write.borrar."""
        _w.borrar(candidato_id, empresa_id)

    def congelar_busqueda(self, vacante_id: str, texto: str,
                          empresa_id: Optional[UUID] = None) -> None:
        """Delegado a _candidato_write.congelar_busqueda."""
        _w.congelar_busqueda(vacante_id, texto, empresa_id)

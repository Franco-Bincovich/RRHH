"""
Las TRANSICIONES del candidato por el embudo: a qué búsqueda pertenece, en qué etapa está y si
su postulación sigue viva.

Extraído de `repositories/_candidato_write.py`, que quedó en 106 contra un tope de 100 al sumarle
`update_estado` (el puente candidato→empleado de A4.2). **El corte no es por tamaño: responde solo
dónde va lo próximo.** Acá vive lo que MUEVE al candidato por el pipeline; allá, lo que escribe
sus DATOS (el INSERT con su `origen`, el CV, el borrado, y el congelado del nombre de la búsqueda
al borrar la vacante). Cuando A5 o el screening agreguen otra transición, no hay que preguntar.

Las tres comparten forma exacta —patch + `.eq("id")` + `.eq("empresa_id")` + `_crow`— y **eso NO
se dedupló en un `_patch()` compartido a propósito**: ese predicado de empresa es la barrera
multiempresa, y el repo la quiere legible en el WHERE de cada función, sin seguir una
indirección. Un helper compartido es la forma en que un día alguien agrega una transición que se
olvida de pasarlo y no se ve en el diff.

El movimiento fue VERBATIM: los cuerpos, sus docstrings y sus comentarios son idénticos a los que
estaban en `_candidato_write.py`. `CandidatoRepo` las sigue delegando en una línea, así que
**ningún caller externo cambió de import** — el único importador era el propio repo.

⚠️ Vive en `repositories/`, así que su límite es 100 líneas, como cualquier repositorio. No
hereda un límite más alto por ser un satélite.
"""
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._candidato_row import _crow
from schemas.candidato import CandidatoResponse

_C = "candidatos"


def asignar_vacante(candidato_id: str, vacante_id: str,
                    empresa_id: Optional[UUID] = None) -> Optional[CandidatoResponse]:
    """Le asigna una vacante a un candidato huérfano. None si no existe o es de otra empresa.

    🔴 El `empresa_id` viaja al WHERE (Forma A de la barrera): la validación de que la VACANTE
    sea de la misma empresa que el candidato la hace el service, porque necesita leer las dos
    filas. Acá se cierra la otra mitad — que el candidato al que se apunta sea alcanzable.

    ⚠️ NO limpia `busqueda_congelada`: ese texto es el título de la búsqueda que se borró y es
    parte del historial del candidato. Sobrescribirlo al reasignarlo perdería de dónde venía.
    """
    q = supabase_admin.table(_C).update({"vacante_id": vacante_id}).eq("id", candidato_id)
    if empresa_id:
        q = q.eq("empresa_id", str(empresa_id))
    res = q.execute()
    return _crow(res.data[0]) if res.data else None


def update_etapa(candidato_id: str, etapa: str,
                 empresa_id: Optional[UUID] = None) -> Optional[CandidatoResponse]:
    """Actualiza la etapa del pipeline de un candidato."""
    q = supabase_admin.table(_C).update({"etapa": etapa}).eq("id", candidato_id)
    if empresa_id:
        q = q.eq("empresa_id", str(empresa_id))
    res = q.execute()
    return _crow(res.data[0]) if res.data else None


def update_estado(candidato_id: str, estado: str,
                  empresa_id: Optional[UUID] = None) -> Optional[CandidatoResponse]:
    """Actualiza el ESTADO de la postulación (activo | descartado | contratado | en_espera).

    🔴 ES OTRA COLUMNA QUE `update_etapa`, Y NO SE UNIFICAN. `etapa` dice DÓNDE está en el
    proceso y `estado` dice SI la postulación sigue viva; alguien descartado en entrevista
    técnica conserva su etapa. Un solo método con la columna por parámetro dejaría que un
    caller escriba 'oferta' en `estado` sin que nada lo frene.

    Primer y único escritor hoy: el puente candidato→empleado (`_candidato_contratar`).
    """
    q = supabase_admin.table(_C).update({"estado": estado}).eq("id", candidato_id)
    if empresa_id:
        q = q.eq("empresa_id", str(empresa_id))
    res = q.execute()
    return _crow(res.data[0]) if res.data else None

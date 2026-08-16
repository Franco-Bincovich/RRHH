"""
Write path del repositorio de candidatos (extraído: el repo estaba en 100/100 exacto y la fase 6
suma dos métodos más).

Funciones libres que reciben lo que necesitan — mismo molde que `_empleado_write_repo.py`.
`CandidatoRepo` las delega en una línea, así que ningún call site cambia. La lógica se movió
VERBATIM: payloads, guardas y mensajes de error son idénticos.
"""
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._candidato_row import _crow
from schemas.candidato import CandidatoCreate, CandidatoResponse
from utils.errors import AppError
from utils.logger import logger

_C = "candidatos"


def guardar(vacante_id: str, data: CandidatoCreate, empresa_id: str,
            origen: Optional[dict] = None) -> CandidatoResponse:
    """Inserta un candidato con el empresa_id heredado de su vacante.

    `origen` son las columnas de PROCEDENCIA de la ingesta por mail (`fuente`,
    `gmail_message_id`, `cv_sha256`). Va aparte y NO en `CandidatoCreate`: aquel es lo que llega
    del formulario de alta, y ahí un cliente podría inventarse un `gmail_message_id` para
    saltarse la idempotencia.
    """
    payload = data.model_dump(exclude_none=True)
    payload["vacante_id"] = vacante_id
    payload["empresa_id"] = empresa_id
    payload["etapa"] = "postulado"
    payload.update(origen or {})
    res = supabase_admin.table(_C).insert(payload).execute()
    if not res.data:
        logger.error("Supabase insert vacío en candidatos")
        raise AppError("Error al crear candidato", "DB_ERROR", 500)
    return _crow(res.data[0])


def set_cv(candidato_id: str, cv_storage_path: str) -> None:
    """Guarda el storage_path del CV en la fila del candidato (bucket privado 'cvs')."""
    supabase_admin.table(_C).update({"cv_storage_path": cv_storage_path}).eq("id", candidato_id).execute()


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


def borrar(candidato_id: str, empresa_id: Optional[UUID] = None) -> None:
    """Borra FÍSICAMENTE la fila del candidato (filtra por empresa si se provee, fail-closed)."""
    q = supabase_admin.table(_C).delete().eq("id", candidato_id)
    if empresa_id:
        q = q.eq("empresa_id", str(empresa_id))
    q.execute()


def congelar_busqueda(vacante_id: str, texto: str, empresa_id: Optional[UUID] = None) -> None:
    """Graba busqueda_congelada en todos los candidatos de una vacante (antes de borrarla)."""
    q = supabase_admin.table(_C).update({"busqueda_congelada": texto}).eq("vacante_id", vacante_id)
    if empresa_id:
        q = q.eq("empresa_id", str(empresa_id))
    q.execute()

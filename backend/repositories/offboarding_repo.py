"""
Repositorio de offboarding — tabla `offboarding_instancias`.
Interfaz: find_activos · find_by_empleado · create_offboarding · find_instancia_min ·
update_entrevista · marcar_completado · update_activo (delegado).

Las tablas, el SELECT con joins y los mappers de fila viven en _offboarding_row.py.
Todo lo de la tabla `offboarding_activos` vive en _offboarding_activos_repo.py — el porqué del
corte (un archivo por tabla) está en el encabezado de ese archivo. `update_activo` se conserva
acá como delegador de una línea para que los call sites del service no cambien.
"""
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories import _offboarding_activos_repo as _activos
from repositories._offboarding_row import SELECT_JOINS as _EJ
from repositories._offboarding_row import TABLA_INSTANCIAS as _OI
from repositories._offboarding_row import inst_row as _inst_row
from schemas.offboarding import OffboardingCreate, OffboardingResponse
from utils.errors import AppError

_EXCL = ["completado", "cancelado"]


def _with_empresa(q, empresa_id: Optional[UUID]):
    return q.eq("empresa_id", str(empresa_id)) if empresa_id else q


class OffboardingRepo:
    def find_activos(self, empresa_id: Optional[UUID] = None) -> list[OffboardingResponse]:
        q = supabase_admin.table(_OI).select(f"*, {_EJ}").not_.in_("estado", _EXCL)
        return [_inst_row(r, _activos.activos_de(r["id"])) for r in (_with_empresa(q, empresa_id).execute().data or [])]

    def find_by_empleado(self, empleado_id: str, empresa_id: Optional[UUID] = None) -> Optional[OffboardingResponse]:
        q = supabase_admin.table(_OI).select(f"*, {_EJ}").eq("empleado_id", empleado_id).not_.in_("estado", _EXCL).limit(1)
        res = _with_empresa(q, empresa_id).maybe_single().execute()
        if not res.data:
            return None
        return _inst_row(res.data, _activos.activos_de(res.data["id"]))

    def create_offboarding(self, data: OffboardingCreate, empresa_id: str) -> OffboardingResponse:
        fecha_fin = data.fecha_ultimo_dia or (date.today() + timedelta(days=30))
        ins = supabase_admin.table(_OI).insert({
            "empleado_id": str(data.empleado_id), "motivo_egreso": data.motivo,
            "descripcion_motivo": data.descripcion_motivo, "empresa_id": empresa_id,
            "fecha_ultimo_dia": str(fecha_fin), "estado": "iniciado",
        }).execute()
        if not ins.data:
            raise AppError("Error al crear offboarding", "DB_ERROR", 500)
        inst_id = ins.data[0]["id"]
        _activos.crear_por_defecto(inst_id, empresa_id)
        return _inst_row(ins.data[0], _activos.activos_de(inst_id))

    def find_instancia_min(self, instancia_id: str, empresa_id: Optional[UUID] = None) -> Optional[dict]:
        """{id, empresa_id, estado, empleado_id} de la instancia, o None si no existe / es de otra
        empresa. Los activos no llevan barrera propia (se alcanzan por instancia_id), así que la
        barrera del módulo va sobre la instancia. Devuelve la fila —no un bool— para que el caller
        reuse su empresa_id.

        ⚠️ `estado` y `empleado_id` se sumaron al SELECT para la efectivización de la baja, que
        necesita los dos: el estado para rechazar un proceso ya cerrado y el empleado para saber a
        quién dar de baja. Van en ESTA query y no en una segunda porque es la misma fila y la
        barrera de empresa ya viaja acá — pedirla dos veces sería una ida de más a la base y, peor,
        dos lugares donde acordarse del `.eq("empresa_id")`. El otro caller
        (`marcar_activo_devuelto`) solo mira que la fila exista, así que las columnas de más no le
        cambian nada."""
        q = supabase_admin.table(_OI).select("id,empresa_id,estado,empleado_id").eq("id", instancia_id)
        res = _with_empresa(q, empresa_id).maybe_single().execute()
        return res.data if res and res.data else None

    def update_entrevista(self, instancia_id: str, entrevista_salida: bool,
                          notas: Optional[str], empresa_id: Optional[UUID] = None) -> bool:
        """Registra la entrevista de salida. El filtro de empresa va en el WHERE (forma A):
        una sola ida a la base, imposible de saltear."""
        q = supabase_admin.table(_OI).update(
            {"entrevista_salida": entrevista_salida, "notas_entrevista": notas}
        ).eq("id", instancia_id)
        return bool(_with_empresa(q, empresa_id).execute().data)

    def marcar_completado(self, instancia_id: str, empresa_id: Optional[UUID] = None) -> bool:
        """Cierra la instancia: `estado = 'completado'`. Filtro de empresa en el WHERE (forma A).

        NO toca `fecha_ultimo_dia`: esa columna es la PREVISIÓN cargada al abrir el trámite, y la
        fecha real de egreso se guarda en el empleado. Pisarla con lo efectivizado borraría la
        única evidencia de cuánto se desvió lo previsto de lo ocurrido."""
        q = supabase_admin.table(_OI).update({"estado": "completado"}).eq("id", instancia_id)
        return bool(_with_empresa(q, empresa_id).execute().data)

    def update_activo(self, instancia_id: str, activo_id: str, devuelto: bool) -> bool:
        """Delegado a _offboarding_activos_repo.update_activo."""
        return _activos.update_activo(instancia_id, activo_id, devuelto)

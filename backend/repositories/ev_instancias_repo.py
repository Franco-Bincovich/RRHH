"""Repositorio de instancias y resultados de evaluación de desempeño.

Los mappers de fila y el enriquecimiento por lotes viven en `_ev_instancias_row.py` (el repo
estaba en 146 líneas contra el límite de 100). Acá quedan solo las queries.
"""
from datetime import date
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._ev_instancias_row import enrich_rows, resultados as map_resultados
from schemas.evaluaciones import InstanciaDetalleResponse, InstanciaResponse
from utils.errors import AppError

_TI, _TR, _TC = "ev_instancias", "ev_resultados", "ev_criterios"




class EvInstanciasRepo:
    def find_all(self, empresa_id: Optional[UUID], ciclo_id: Optional[UUID] = None,
                 estado: Optional[str] = None) -> List[InstanciaResponse]:
        """Retorna instancias enriquecidas con nombres, filtradas por empresa/ciclo/estado."""
        q = supabase_admin.table(_TI).select("*").order("created_at", desc=True)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        if ciclo_id:
            q = q.eq("ciclo_id", str(ciclo_id))
        if estado:
            q = q.eq("estado", estado)
        return enrich_rows(q.execute().data or [])

    def find_by_id(self, id: str, empresa_id: Optional[UUID] = None) -> Optional[InstanciaDetalleResponse]:
        """Retorna instancia con todos sus resultados enriquecidos + datos de plantilla."""
        q = supabase_admin.table(_TI).select("*").eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.maybe_single().execute()
        if not (res and res.data):
            return None
        base_list = enrich_rows([res.data])
        if not base_list:
            return None
        base = base_list[0]
        resultados_raw = supabase_admin.table(_TR).select(
            f"*, {_TC}(nombre, peso, orden)"
        ).eq("instancia_id", id).execute().data or []
        resultados = map_resultados(resultados_raw)
        ciclo = supabase_admin.table("ev_ciclos").select(
            "nombre, ev_plantillas(tipo_escala, opciones_cualitativas, escala_min, escala_max)"
        ).eq("id", res.data["ciclo_id"]).maybe_single().execute()
        plantilla = (ciclo.data or {}).get("ev_plantillas") or {} if ciclo else {}
        return InstanciaDetalleResponse(
            **base.model_dump(), comentario_general=res.data.get("comentario_general"),
            resultados=resultados,
            plantilla_tipo_escala=plantilla.get("tipo_escala"),
            plantilla_opciones_cualitativas=plantilla.get("opciones_cualitativas"),
            plantilla_escala_min=plantilla.get("escala_min"),
            plantilla_escala_max=plantilla.get("escala_max"),
        )

    def create(self, ciclo_id: str, empleado_id: str, evaluador_id: Optional[str],
               empresa_id: str, criterios: List[dict]) -> Optional[InstanciaDetalleResponse]:
        """Crea instancia y genera filas vacías de ev_resultados por cada criterio."""
        ins = supabase_admin.table(_TI).insert({
            "ciclo_id": ciclo_id, "empleado_id": empleado_id,
            "evaluador_id": evaluador_id, "empresa_id": empresa_id,
        }).execute()
        if not ins.data:
            raise AppError("Error al crear la instancia", "DB_ERROR", 500)
        inst_id = ins.data[0]["id"]
        if criterios:
            supabase_admin.table(_TR).insert([
                {"instancia_id": inst_id, "criterio_id": c["id"], "empresa_id": empresa_id}
                for c in criterios
            ]).execute()
        return self.find_by_id(inst_id)

    def update_resultado(self, instancia_id: str, criterio_id: str, payload: dict) -> bool:
        res = supabase_admin.table(_TR).update(payload).eq(
            "instancia_id", instancia_id).eq("criterio_id", criterio_id).execute()
        return bool(res.data)

    def exists(self, ciclo_id: str, empleado_id: str) -> bool:
        """Verifica si ya existe una instancia para este par ciclo/empleado."""
        res = supabase_admin.table(_TI).select("id").eq("ciclo_id", ciclo_id).eq(
            "empleado_id", empleado_id).limit(1).execute()
        return bool(res.data)

    def finalizar(self, id: str, empresa_id: Optional[UUID],
                  puntaje_global: Optional[float], fecha: date) -> bool:
        payload = {"estado": "finalizada", "fecha_evaluacion": str(fecha)}
        if puntaje_global is not None:
            payload["puntaje_global"] = puntaje_global
        q = supabase_admin.table(_TI).update(payload).eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        return bool(q.execute().data)

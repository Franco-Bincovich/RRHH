"""
Repositorio de reportes generados — historial persistido en Supabase.
Interfaz pública: save · find_historial · find_by_id
empresa_id NULLABLE: null = reporte consolidado (todas las empresas).
Historial con empresa activa: muestra reportes de esa empresa + consolidados (null).
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.reporte import HistorialItem, ReporteResponse
from utils.errors import AppError

_TABLE = "reportes_generados"
_HIST_SELECT = "id, nombre, tipo, generado_por, created_at, empresa_id, empresas(nombre)"


class ReporteRepo:
    def save(
        self,
        nombre: str,
        tipo: str,
        datos: Dict[str, Any],
        generado_por: str,
        empresa_id: Optional[UUID] = None,
        parametros: Optional[Dict[str, Any]] = None,
    ) -> ReporteResponse:
        """Persiste un reporte en reportes_generados. empresa_id=None = consolidado de todas las empresas."""
        payload: Dict[str, Any] = {
            "nombre": nombre,
            "tipo": tipo,
            "datos": datos,
            "generado_por": generado_por,
        }
        if empresa_id:
            payload["empresa_id"] = str(empresa_id)
        if parametros:
            payload["parametros"] = parametros

        res = supabase_admin.table(_TABLE).insert(payload).execute()
        if not res.data:
            raise AppError("Error al guardar el reporte", "REPORTE_SAVE_ERROR", 500)

        r = res.data[0]
        # 🔴 `empresa_id` VA EN LA RESPUESTA. Se guardaba en la fila y se perdía al construir el
        # schema, así que `POST /api/reportes/generar` contestaba `empresa_id: null` SIEMPRE —
        # indistinguible de un consolidado de verdad. El campo existe en `ReporteResponse` desde
        # que se creó; lo que faltaba era pasarlo. Lo consume la auditoría de la generación, que
        # etiqueta el evento con la empresa de la ENTIDAD y no con la del header.
        return ReporteResponse(
            id=r["id"], nombre=r["nombre"], tipo=r["tipo"],
            datos=r["datos"], generado_por=r["generado_por"], created_at=r["created_at"],
            empresa_id=r.get("empresa_id"),
        )

    def find_by_id(self, reporte_id: str) -> Optional[ReporteResponse]:
        """Retorna un reporte completo (incluye datos) por su ID, o None si no existe."""
        res = supabase_admin.table(_TABLE).select("id, nombre, tipo, datos, generado_por, created_at, empresa_id").eq("id", reporte_id).limit(1).execute()
        if not res.data:
            return None
        r = res.data[0]
        # 🔴 `empresa_id` VA EN LA RESPUESTA. Se guardaba en la fila y se perdía al construir el
        # schema, así que `POST /api/reportes/generar` contestaba `empresa_id: null` SIEMPRE —
        # indistinguible de un consolidado de verdad. El campo existe en `ReporteResponse` desde
        # que se creó; lo que faltaba era pasarlo. Lo consume la auditoría de la generación, que
        # etiqueta el evento con la empresa de la ENTIDAD y no con la del header.
        return ReporteResponse(
            id=r["id"], nombre=r["nombre"], tipo=r["tipo"],
            datos=r["datos"], generado_por=r["generado_por"], created_at=r["created_at"],
            empresa_id=r.get("empresa_id"),
        )

    def find_historial(self, empresa_id: Optional[UUID] = None, limit: int = 50) -> List[HistorialItem]:
        """Historial de reportes por fecha desc. empresa_id=None = todos; con empresa = esa empresa + consolidados (null)."""
        q = supabase_admin.table(_TABLE).select(_HIST_SELECT).order("created_at", desc=True).limit(limit)
        if empresa_id:
            q = q.or_(f"empresa_id.eq.{str(empresa_id)},empresa_id.is.null")

        return [
            HistorialItem(
                id=r["id"], nombre=r["nombre"], tipo=r["tipo"],
                generado_por=r["generado_por"], created_at=r["created_at"],
                empresa_id=r.get("empresa_id"),
                empresa_nombre=(r.get("empresas") or {}).get("nombre"),
            )
            for r in (q.execute().data or [])
        ]

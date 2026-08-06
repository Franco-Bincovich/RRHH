"""
Servicio de Organigrama — vistas por proyecto (árbol desplegable + cards).
Flujo: router → service → DB
empresa_id filtra por empresa DUEÑA del proyecto. None = todos.
Empresas colaboradoras se derivan en Python: DISTINCT(empleado_empresa_id) != proyecto.empresa_id.
"""
from typing import Dict, List, Optional, Set
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.organigrama import (
    EmpresaLeyendaResponse, EmpleadoProyectoNodoResponse,
    OrgProyectosResponse, ProyectoOrgNodoResponse,
)
from utils.errors import AppError
from utils.logger import logger


class OrganigramaProyectosService:
    def get_organigrama_proyectos(self, empresa_id: Optional[UUID] = None) -> OrgProyectosResponse:
        """
        Devuelve todos los proyectos con asignaciones enriquecidas y conteo de proyectos por empleado.
        empresa_id filtra por empresa DUEÑA. None = todos los proyectos.
        El conteo total_proyectos de cada empleado se calcula sobre TODOS sus proyectos activos
        (no solo los filtrados), para que el tag "N proy." sea correcto.

        Returns:
            OrgProyectosResponse con proyectos + leyenda de empresas ordenada para paleta de colores.

        Raises:
            AppError: ORGANIGRAMA_ERROR (500).
        """
        eid = str(empresa_id) if empresa_id else None
        try:
            # 1. Proyectos (filtrado por empresa dueña si aplica)
            proy_q = supabase_admin.table("proyectos").select("id, nombre, estado, empresa_id").order("nombre")
            if eid:
                proy_q = proy_q.eq("empresa_id", eid)
            proyectos_data = proy_q.execute().data or []
            pids = [p["id"] for p in proyectos_data]

            # 2. Asignaciones activas
            asig_data: list = []
            if pids:
                asig_data = (
                    supabase_admin.table("proyecto_asignaciones")
                    .select("proyecto_id, empleado_id, empleado_empresa_id, rol, "
                            "valor_hora, fecha_desde, fecha_hasta")
                    .in_("proyecto_id", pids).eq("activo", True).execute().data or []
                )

            # 3. Batch-resolver nombres de empleados y empresas
            emp_ids: List[str] = list({a["empleado_id"] for a in asig_data})
            empresa_ids: List[str] = list(
                {a["empleado_empresa_id"] for a in asig_data} | {p["empresa_id"] for p in proyectos_data}
            )
            emp_map: Dict[str, dict] = (
                {e["id"]: e for e in
                 supabase_admin.table("empleados").select("id, nombre, apellido, roles")
                 .in_("id", emp_ids).execute().data or []}
                if emp_ids else {}
            )
            empresa_map: Dict[str, str] = (
                {e["id"]: e["nombre"] for e in
                 supabase_admin.table("empresas").select("id, nombre")
                 .in_("id", empresa_ids).execute().data or []}
                if empresa_ids else {}
            )

            # 4. Contar proyectos activos por empleado (sobre TODOS los proyectos, no solo los filtrados)
            conteo: Dict[str, int] = {}
            if emp_ids:
                cnt_rows = (
                    supabase_admin.table("proyecto_asignaciones")
                    .select("empleado_id, proyecto_id")
                    .in_("empleado_id", emp_ids).eq("activo", True).execute().data or []
                )
                por_emp: Dict[str, Set[str]] = {}
                for r in cnt_rows:
                    por_emp.setdefault(r["empleado_id"], set()).add(r["proyecto_id"])
                conteo = {k: len(v) for k, v in por_emp.items()}

            # 5. Agrupar asignaciones por proyecto
            asig_por_proy: Dict[str, list] = {}
            for a in asig_data:
                asig_por_proy.setdefault(a["proyecto_id"], []).append(a)

            # 6. Construir respuesta de proyectos
            proyectos_resp: List[ProyectoOrgNodoResponse] = []
            for p in proyectos_data:
                empleados = []
                for a in asig_por_proy.get(p["id"], []):
                    e = emp_map.get(a["empleado_id"], {})
                    n, ap = e.get("nombre", ""), e.get("apellido", "")
                    iniciales = f"{n[0] if n else ''}{ap[0] if ap else ''}".upper()
                    empleados.append(EmpleadoProyectoNodoResponse(
                        id=a["empleado_id"], nombre=n, apellido=ap,
                        iniciales=iniciales, cargo=(e.get("roles") or [e.get("cargo")])[0], rol=a["rol"],
                        empleado_empresa_id=a["empleado_empresa_id"],
                        empleado_empresa_nombre=empresa_map.get(a["empleado_empresa_id"]),
                        total_proyectos=conteo.get(a["empleado_id"], 1),
                        valor_hora=float(a.get("valor_hora") or 0),
                        fecha_desde=a.get("fecha_desde"), fecha_hasta=a.get("fecha_hasta"),
                    ))
                proyectos_resp.append(ProyectoOrgNodoResponse(
                    id=p["id"], nombre=p["nombre"], estado=p["estado"],
                    empresa_id=p["empresa_id"],
                    empresa_nombre=empresa_map.get(p["empresa_id"]),
                    total_asignados=len(empleados), empleados=empleados,
                ))

            # 7. Leyenda: todas las empresas activas ordenadas por nombre para la paleta de colores
            leyenda = [
                EmpresaLeyendaResponse(id=e["id"], nombre=e["nombre"])
                for e in (supabase_admin.table("empresas").select("id, nombre")
                          .eq("activa", True).order("nombre").execute().data or [])
            ]
        except Exception as exc:
            logger.error("Error al consultar organigrama proyectos", extra={"error": str(exc)})
            raise AppError("Error al obtener el organigrama de proyectos", "ORGANIGRAMA_ERROR", 500) from exc

        logger.info("Organigrama proyectos consultado", extra={"total_proyectos": len(proyectos_resp)})
        return OrgProyectosResponse(proyectos=proyectos_resp, empresas_orden=leyenda)

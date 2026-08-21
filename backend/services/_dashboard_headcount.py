"""
Headcount de activos por área, para el dashboard.

Vive aparte de `_dashboard_kpis` —que quedó en su límite al cablear la base de días hábiles
configurable (migración 085)— y el corte no es arbitrario: es otra cosa. `_dashboard_kpis`
calcula los 5 KPIs escalares de la Sesión 5, que se devuelven juntos en KPIsExtraResponse con
fail-safe compartido; esto arma una LISTA por área y `dashboard_service` la pide por separado,
con su propio `_safe`.

Se movió verbatim: no cambia nada de su comportamiento.

Desde el 21/8/2026 vive acá también el headcount POR EMPRESA, que es el KPI que pide
`docs/SISTEMA-DE-DISENO.md` §6. Son la misma clase de cosa —una lista de conteos de activos con
un `group by` distinto— y comparten el criterio de qué cuenta como activo; separarlos en dos
archivos habría sido separar dos definiciones que tienen que moverse juntas. 🔴 Lo que NO
comparten es qué pasa con los que no agrupan: ver el comentario de `calcular_headcount_empresa`.
"""
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.dashboard import HeadcountAreaResponse, HeadcountEmpresaResponse


def calcular_headcount(empresa_id: Optional[UUID] = None) -> List[HeadcountAreaResponse]:
    """Headcount de activos agrupado por área, filtrado por empresa."""
    eid = str(empresa_id) if empresa_id else None

    areas_q = supabase_admin.table("areas").select("id, nombre").eq("activo", True)
    if eid:
        areas_q = areas_q.eq("empresa_id", eid)
    area_nombres: dict[str, str] = {a["id"]: a["nombre"] for a in areas_q.execute().data}

    emp_q = supabase_admin.table("empleados").select("area_id").eq("estado", "activo")
    if eid:
        emp_q = emp_q.eq("empresa_id", eid)
    conteo: dict[str, int] = {}
    for emp in emp_q.execute().data:
        aid = emp.get("area_id")
        if aid and aid in area_nombres:
            conteo[aid] = conteo.get(aid, 0) + 1
    return sorted(
        [HeadcountAreaResponse(area_id=k, area=area_nombres[k], total=v) for k, v in conteo.items()],
        key=lambda x: x.total, reverse=True,
    )


def calcular_headcount_empresa(empresa_id: Optional[UUID] = None) -> List[HeadcountEmpresaResponse]:
    """Headcount de activos agrupado por EMPRESA (§6). Con el sidebar en una empresa: una fila.

    🔴 LA SUMA DE ESTA LISTA ES EL TOTAL DE ACTIVOS, SIEMPRE — y ahí está la diferencia con su
    hermana de arriba, que descarta a quien no tiene área o la tiene inactiva (y está bien que lo
    haga: "el reparto por área" no es "todos"). Acá no se puede descartar a nadie: es el mismo
    universo del KPI "Colaboradores activos", partido en dos, y dos números de la misma pantalla
    que no cierran es exactamente el problema que esta tanda vino a arreglar en la masa salarial.
    Por eso, y a propósito:
      · el conteo agrupa por `empresa_id` de la fila (NOT NULL) ANTES de mirar el catálogo, así
        que ninguna empresa se cae por no estar en el lookup;
      · el lookup de `empresas` NO filtra por `activa`. Una empresa desactivada con gente activa
        adentro sigue teniendo headcount, y esconderla restaría personas del total sin decirlo.
    """
    eid = str(empresa_id) if empresa_id else None
    emp_q = supabase_admin.table("empleados").select("empresa_id").eq("estado", "activo")
    if eid:
        emp_q = emp_q.eq("empresa_id", eid)
    conteo: dict[str, int] = {}
    for e in (emp_q.execute().data or []):
        clave = str(e.get("empresa_id"))
        conteo[clave] = conteo.get(clave, 0) + 1
    if not conteo:
        return []

    # Lookup batch (una query, no una por empresa). El nombre es DERIVADO: si no resuelve, la
    # fila sale igual con una etiqueta neutra — un nombre que falta no puede borrar personas.
    filas = (supabase_admin.table("empresas").select("id, nombre")
             .in_("id", list(conteo)).execute().data or [])
    nombres = {str(f["id"]): f.get("nombre") for f in filas}
    return sorted(
        [HeadcountEmpresaResponse(empresa_id=k, empresa=nombres.get(k) or "Sin nombre", total=v)
         for k, v in conteo.items()],
        key=lambda x: x.total, reverse=True,
    )

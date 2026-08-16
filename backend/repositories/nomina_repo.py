"""
Repositorio de nómina (costos_nomina). Acceso a Supabase con supabase_admin.
La tabla, el SELECT con joins y el mapper de fila viven en _nomina_row.py.
Interfaz pública: get_nomina_mes (sin paginar, para agregados) · find_pagina (el listado) ·
save_nomina · get_evolucion. El flujo de CARGA vive en `_nomina_write_repo.py` (este
archivo llegaba a 119/100 al sumarle la paginación).
empresa_id en escritura se hereda automáticamente del empleado (no se solicita explícito).
Todas las lecturas y el cálculo de evolución filtran por empresa_id cuando se provee.
"""
from typing import List, Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._nomina_evolucion import evolucion
from repositories._nomina_row import SELECT as _NOM_SEL
from repositories._nomina_row import TABLE as _NOM
from repositories._nomina_row import item as _a_item
from repositories._nomina_row import row as _to_nomina
from repositories._nomina_write_repo import guardar, periodos_cargados
from schemas.costo import EvolucionMes, HistorialSalarialItem, NominaCreate, NominaResponse


def _del_periodo(mes: int, anio: int, empresa_id: Optional[UUID]):
    """La query base del período. UNA definición para los dos lectores de abajo.

    Con una copia en cada uno, el listado y el dashboard podrían empezar a mirar conjuntos
    distintos del mismo mes sin que nada falle.
    """
    q = supabase_admin.table(_NOM).select(_NOM_SEL, count="exact").eq("mes", mes).eq("anio", anio)
    return q.eq("empresa_id", str(empresa_id)) if empresa_id else q


class NominaRepo:
    def get_nomina_mes(self, mes: int, anio: int, empresa_id: Optional[UUID] = None) -> List[NominaResponse]:
        """TODAS las filas del período, sin paginar. Si empresa_id se provee, filtra.

        🔴 NO PAGINA, Y ES A PROPÓSITO: sus tres callers necesitan el conjunto COMPLETO —
        `costo_service.get_dashboard_costos` agrupa por área y suma la masa salarial, el mismo
        método vuelve a llamarlo para el total del mes anterior, y `_costos_write` lo usa para
        armar el diff de auditoría. Paginarlo en el lugar habría dejado a los KPIs calculando
        sobre 20 filas, sin error y sin aviso — que es exactamente el bug que esta tanda de
        paginación existe para no repetir.
        El listado de pantalla usa `find_pagina`, abajo.
        """
        return [_to_nomina(r) for r in (_del_periodo(mes, anio, empresa_id).execute().data or [])]

    def find_pagina(self, mes: int, anio: int, empresa_id: Optional[UUID] = None,
                    page: int = 1, page_size: int = 20) -> Tuple[List[NominaResponse], int]:
        """Una página de la nómina del período + el total real del filtro.

        🔑 ORDENA POR EL APELLIDO DEL EMPLEADO, QUE VIVE EN OTRA TABLA. PostgREST lo permite sobre
        un embed to-one: `order=empleados(apellido)`, que es lo que produce `foreign_table=`.
        Verificado contra PostgREST 12.2.3 — el hint de FK (`!costos_nomina_empleado_emp_fkey`)
        va en el SELECT y NO en el order, donde da PGRST100.

        Se ordena por apellido y no por monto porque esto es una NÓMINA: se lee buscando a
        alguien. Un orden por bruto descendente pone a quien más cobra arriba de una pantalla que
        se comparte y se proyecta.

        ⚠️ El ORDER BY sobre la tabla unida NO puede usar índice, pero el WHERE sí:
        `idx_costos_nomina_empresa_periodo (empresa_id, anio, mes)` (migración 115) recorta el
        período —22.360 filas a 80 en la base de escala— y el sort corre sobre eso.
        """
        res = (_del_periodo(mes, anio, empresa_id)
               .order("apellido", foreign_table="empleados").order("id")
               .range((page - 1) * page_size, page * page_size - 1).execute())
        return [_to_nomina(r) for r in (res.data or [])], (res.count or 0)

    def find_by_empleado(self, empleado_id: str, empresa_id: Optional[UUID] = None) -> List[HistorialSalarialItem]:
        """Serie salarial del empleado, del período más reciente al más viejo.

        Ordena por (anio, mes) en la query y no en Python: la serie es el producto, y un orden
        que dependa del orden de llegada de las filas se rompe en silencio.
        `UNIQUE (empleado_id, anio, mes)` garantiza que no haya dos filas del mismo período.
        """
        q = (supabase_admin.table(_NOM).select("anio,mes,salario_bruto,cargas_sociales")
             .eq("empleado_id", empleado_id)
             .order("anio", desc=True).order("mes", desc=True))
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        return [_a_item(r) for r in (q.execute().data or [])]

    # ── Carga de nómina (delegada a _nomina_write_repo) ──

    def save_nomina(self, data: NominaCreate) -> NominaResponse:
        """Upsert de nómina. Delegado a _nomina_write_repo.guardar."""
        return guardar(data)

    def periodos_cargados(self, empresa_id: str) -> set[tuple]:
        """Períodos ya registrados en la empresa. Delegado a _nomina_write_repo."""
        return periodos_cargados(empresa_id)

    def get_evolucion(self, mes: int, anio: int, empresa_id: Optional[UUID] = None) -> List[EvolucionMes]:
        """Evolución de costos de los últimos 12 meses. Delegado a `_nomina_evolucion.evolucion`."""
        return evolucion(mes, anio, empresa_id)

"""
Servicio de Costos de Personal. Lógica de negocio del módulo de Costos.
Flujo: router → service → repository → DB
CRÍTICO: todo cálculo de totales y agregaciones filtra por empresa_id cuando se provee.
"""
from typing import List, Optional
from uuid import UUID

from repositories.empleado_repo import EmpleadoRepo
from repositories.nomina_repo import NominaRepo
from repositories.periodo_repo import PeriodoRepo
from repositories.presupuesto_repo import PresupuestoRepo
from schemas.costo import (
    CostoArea, DashboardCostosResponse, HistorialSalarialItem, NominaCreate, NominaResponse,
    PresupuestoCreate, PresupuestoResponse,
)
from services._costos_write import cargar_nomina, set_presupuesto_area
from services._empleado_scope import ensure_empleado_de_empresa
from services._limite_export import verificar_limite_export
from services._nomina_export import construir_filas_export
from services.audit_service import AuditService
from services.export import Descarga, build_export


class CostoService:
    def __init__(
        self,
        nomina_repo: Optional[NominaRepo] = None,
        presupuesto_repo: Optional[PresupuestoRepo] = None,
        audit: Optional[AuditService] = None,
        periodo_repo: Optional[PeriodoRepo] = None,
        empleado_repo: Optional[EmpleadoRepo] = None,
    ) -> None:
        self._nomina = nomina_repo or NominaRepo()
        self._presupuesto = presupuesto_repo or PresupuestoRepo()
        self._audit = audit or AuditService()
        self._periodos = periodo_repo or PeriodoRepo()
        self._empleados = empleado_repo or EmpleadoRepo()

    def get_dashboard_costos(self, mes: int, anio: int, empresa_id: Optional[UUID] = None) -> DashboardCostosResponse:
        """
        Construye el dashboard de costos para el período dado.
        CRÍTICO: todos los SUM/agrupaciones filtran por empresa_id cuando se provee.
        La clave del amap usa (empresa_id, area_nombre) para evitar colisiones entre empresas.

        Args:
            mes: Mes del período (1–12).
            anio: Año del período.
            empresa_id: Filtra por empresa. None = consolidado (todas las empresas).
        """
        rows = self._nomina.get_nomina_mes(mes, anio, empresa_id)
        total = sum(r.monto_bruto for r in rows)
        promedio = total / len(rows) if rows else 0.0

        prev_m = mes - 1 if mes > 1 else 12
        prev_y = anio if mes > 1 else anio - 1
        total_prev = sum(r.monto_bruto for r in self._nomina.get_nomina_mes(prev_m, prev_y, empresa_id))
        variacion = round((total - total_prev) / total_prev * 100, 2) if total_prev else None

        # Clave compuesta para evitar que dos empresas con el mismo nombre de área colisionen
        amap: dict[tuple[str, str], dict] = {}
        for r in rows:
            key = (r.empresa_id or "", r.area_nombre)
            if key not in amap:
                amap[key] = {
                    "empresa_nombre": r.empresa_nombre, "area_nombre": r.area_nombre,
                    "empleados": 0, "costo_mensual": 0.0, "presupuesto": 0.0,
                }
            amap[key]["empleados"] += 1
            amap[key]["costo_mensual"] += r.monto_bruto

        presupuestos = self._presupuesto.get_presupuestos_mes(mes, anio, empresa_id)
        for key, monto in presupuestos.items():
            if key in amap:
                amap[key]["presupuesto"] = monto

        return DashboardCostosResponse(
            total_nomina=total,
            costo_promedio=promedio,
            variacion_porcentual=variacion,
            costos_por_area=[CostoArea(**v) for v in amap.values()],
            evolucion_mensual=self._nomina.get_evolucion(mes, anio, empresa_id),
        )

    def get_nomina_mes(self, mes: int, anio: int, empresa_id: Optional[UUID] = None) -> List[NominaResponse]:
        """
        Retorna todos los registros de nómina para el período dado.

        Args:
            mes: Mes del período (1–12).
            anio: Año del período.
            empresa_id: Filtra por empresa. None = todas.
        """
        return self._nomina.get_nomina_mes(mes, anio, empresa_id)

    def get_historial_salarial(self, empleado_id: UUID, empresa_id: Optional[UUID] = None) -> List[HistorialSalarialItem]:
        """Serie salarial de un empleado, del período más reciente al más viejo.

        LA SERIE **ES** EL HISTORIAL, no hace falta el log de cambios: `costos_nomina` tiene
        UNIQUE (empleado_id, anio, mes), o sea una fila por mes. Con auditoría, el caso más
        común —sueldos importados por CSV y nunca editados a mano— daría historial vacío
        teniendo los sueldos cargados.

        DOS BARRERAS, las dos necesarias y distintas:
          · la de SECCIÓN (Seccion.COSTOS + READ) la aplica el router: quién puede ver sueldos;
          · la de EMPRESA se aplica acá, sobre el EMPLEADO objetivo. El `empresa_id` que el
            repo usa sale del header y no valida a qué empleado apuntás: sin este chequeo, un
            id de otra empresa devolvería su serie salarial igual.
        El 404 es el mismo que el de "el empleado no existe" — nunca un 403.

        Args:
            empleado_id: empleado del que se pide la serie.
            empresa_id: empresa activa del request. None = consolidado (no restringe).

        Returns:
            Lista de HistorialSalarialItem; vacía si el empleado no tiene nómina cargada, que
            NO es un error — hoy es el caso de los 19 empleados de producción.

        Raises:
            AppError: EMPLEADO_NOT_FOUND (404) si no existe o es de otra empresa.
        """
        ensure_empleado_de_empresa(self._empleados, empleado_id, empresa_id)
        return self._nomina.find_by_empleado(str(empleado_id), empresa_id)

    def exportar(self, mes: int, anio: int, empresa_id: Optional[UUID] = None, formato: str = "excel") -> Descarga:
        """Exporta la nómina del período con los MISMOS filtros que `get_nomina_mes` — lo que
        se ve en la pantalla es lo que sale en el archivo. El motor genérico no se toca."""
        rows = self._nomina.get_nomina_mes(mes, anio, empresa_id)
        verificar_limite_export(len(rows))
        datos = {"Nómina": construir_filas_export(rows)}
        # Guion y no barra: openpyxl rechaza "/" en el título de la hoja y el export moriría
        # con EXPORT_ERROR en vez de entregar el archivo.
        return build_export(nombre=f"Nómina {mes:02d}-{anio}", datos=datos, filename_base="nomina", formato=formato)

    def cargar_nomina(self, data: NominaCreate, empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None, rol: Optional[str] = None) -> NominaResponse:
        """Registra o actualiza la nómina de un empleado para un período. Ver _costos_write."""
        return cargar_nomina(self._nomina, self._periodos, self._audit, data, empresa_id, usuario_id, rol)

    def set_presupuesto_area(self, data: PresupuestoCreate, empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None) -> PresupuestoResponse:
        """Establece o actualiza el presupuesto de nómina de un área. Ver _costos_write."""
        return set_presupuesto_area(self._presupuesto, self._audit, data, empresa_id, usuario_id)

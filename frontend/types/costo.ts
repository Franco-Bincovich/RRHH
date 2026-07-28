export interface NominaCreate {
  empleado_id: string
  mes: number
  anio: number
  monto_bruto: number
  monto_neto: number
}

export interface Nomina {
  id: string
  empleado_id: string
  empresa_id: string | null
  empresa_nombre: string | null
  empleado_nombre: string
  area_nombre: string
  mes: number
  anio: number
  monto_bruto: number
  monto_neto: number
  total: number
}

/**
 * Un período de la serie salarial de un empleado.
 * Sin `total`: esa columna es bruto+cargas (el costo para la empresa), no lo que cobra la
 * persona, y en un legajo se leería como sueldo. El backend tampoco lo devuelve.
 */
export interface HistorialSalarialItem {
  anio: number
  mes: number
  monto_bruto: number
  monto_neto: number
}

export interface PresupuestoCreate {
  area_id: string
  mes: number
  anio: number
  presupuesto: number
}

export interface Presupuesto {
  id: string
  area_id: string
  area_nombre: string
  mes: number
  anio: number
  presupuesto: number
}

export interface CostoArea {
  empresa_nombre: string | null
  area_nombre: string
  empleados: number
  costo_mensual: number
  presupuesto: number
}

export interface EvolucionMes {
  mes: number
  anio: number
  total: number
}

export interface DashboardCostos {
  total_nomina: number
  costo_promedio: number
  variacion_porcentual: number | null
  costos_por_area: CostoArea[]
  evolucion_mensual: EvolucionMes[]
}

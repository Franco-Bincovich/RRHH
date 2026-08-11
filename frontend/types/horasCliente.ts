import type { Hora, Modalidad } from "@/types/proyecto"

/** Espejo de backend/schemas/horas_cliente.py. */

export interface KPIsHoras {
  horas_totales: number
  /** Clientes REALES: el grupo "Sin cliente" (cargas del camino viejo) NO suma acá. */
  clientes_con_carga: number
  empleados_que_cargaron: number
  registros: number
}

export interface LineaEmpleado {
  empleado_id: string | null
  empleado_nombre: string | null
  proyecto_texto: string | null
  tarea_texto: string | null
  modalidad: Modalidad | null
  horas: number
  registros: number
}

/** Cuánto puso cada sociedad del grupo contra un cliente. La suma es el total del cliente. */
export interface HorasDeEmpresa {
  empresa_nombre: string
  horas: number
}

export interface ClienteConHoras {
  /** null en el grupo "Sin cliente": son las cargas del camino viejo, que no tienen cliente. */
  cliente_id: string | null
  cliente_nombre: string
  /** Total del CLIENTE, sin recortar por sociedad. `por_empresa` lo reparte. */
  horas: number
  registros: number
  por_empresa: HorasDeEmpresa[]
  lineas: LineaEmpleado[]
}

export interface HorasPorCliente {
  mes: number
  anio: number
  kpis: KPIsHoras
  clientes: ClienteConHoras[]
}

export interface DetalleEmpleado {
  items: Hora[]
  total_horas: number
}

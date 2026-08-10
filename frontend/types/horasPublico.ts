/** Espejo de backend/schemas/horas_publico.py. */
import type { Modalidad } from "@/types/proyecto"

export type { Modalidad }

export interface Identificacion {
  nombre: string
  token: string
  expira_en: string
}

export interface ClientePublico {
  id: string
  nombre: string
}

export interface CargaDeLaSemana {
  fecha: string
  cliente_nombre: string | null
  proyecto_texto: string | null
  tarea_texto: string | null
  horas: number
  modalidad: Modalidad | null
}

export interface LicenciaDeLaSemana {
  fecha_desde: string
  fecha_hasta: string
  dias: number
  observaciones: string | null
}

export interface Semana {
  desde: string
  hasta: string
  total_horas: number
  cargas: CargaDeLaSemana[]
  licencias: LicenciaDeLaSemana[]
}

export interface CargaHorasBody {
  token: string
  fecha: string
  horas: number
  modalidad: Modalidad
  cliente_id: string
  proyecto_texto?: string
  tarea_texto?: string
  descripcion?: string
  idempotencia?: string
}

export interface CargaLicenciaBody {
  token: string
  fecha_desde: string
  fecha_hasta: string
  observaciones?: string
}

export interface CargaLicenciaResultado {
  id: string
  fecha_desde: string
  fecha_hasta: string
  dias: number
  horas_equivalentes: number
  /** True cuando el empleado no tiene `horas_contrato` y el backend asumió 8. Hay que MOSTRARLO. */
  horas_por_dia_estimadas: boolean
}

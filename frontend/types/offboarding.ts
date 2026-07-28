export type MotivoEgreso =
  | "renuncia"
  | "despido"
  | "acuerdo_mutuo"
  | "fin_contrato"
  | "jubilacion"
  | "fallecimiento"
  | "otro"

export interface ActivoResponse {
  id: string
  tipo_activo: string
  descripcion: string | null
  estado: string
  devuelto: boolean
}

export interface AccesoResponse {
  id: string
  tipo: string
  descripcion: string | null
  revocado: boolean
}

export interface OffboardingInstancia {
  id: string
  empleado_id: string
  empresa_id: string | null
  empresa_nombre: string | null
  empleado_nombre: string
  motivo: MotivoEgreso
  estado: string
  fecha_inicio: string
  progreso: number
  entrevista_salida: boolean
  notas_entrevista: string | null
  activos: ActivoResponse[]
  accesos: AccesoResponse[]
}

export interface OffboardingCreate {
  empleado_id: string
  motivo: MotivoEgreso
  fecha_ultimo_dia?: string
  descripcion_motivo?: string
}

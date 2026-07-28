export interface TemplateTarea {
  id: string
  template_id: string
  titulo: string
  descripcion: string | null
  semana: number
  orden: number
}

export interface OnboardingTemplate {
  id: string
  nombre: string
  empresa_id: string | null
  empresa_nombre: string | null
  descripcion: string | null
  /** Autor. null en templates previos al cableado del autor, o cuyo usuario se borró. */
  created_by: string | null
  created_by_nombre: string | null
  /** true = la ven todos los usuarios de la empresa; false = solo su autor. */
  es_publica: boolean
  tareas: TemplateTarea[]
  tareas_total: number
}

export interface OnboardingInstancia {
  id: string
  empleado_id: string
  empresa_id: string | null
  empresa_nombre: string | null
  empleado_nombre: string
  empleado_cargo: string | null
  empleado_area: string | null
  template_id: string
  estado: string
  fecha_inicio: string
  progreso: number
  tareas_completadas: number
  tareas_total: number
}

export interface TareaProgreso {
  progreso_id: string
  tarea_id: string
  titulo: string
  descripcion: string | null
  semana: number
  orden: number
  completada: boolean
}

export interface OnboardingDetalle extends OnboardingInstancia {
  tareas: TareaProgreso[]
}

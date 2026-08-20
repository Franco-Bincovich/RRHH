export interface Empleado {
  id: string
  nombre: string
  apellido: string
  email_corporativo: string
  empresa_id: string | null
  empresa_nombre: string | null
  area_id: string
  area_nombre: string | null
  roles: string[]
  cargo?: string | null // DEPRECADO (se quita en S6); usar roles
  modalidad_trabajo: "presencial" | "remoto" | "hibrido"
  tipo_contrato: string // texto libre (migración 065); el CSV de nómina trae valores abiertos
  fecha_ingreso: string
  telefono: string | null
  fecha_nacimiento: string | null
  dni: string | null
  cuil: string | null
  legajo: string | null
  manager_id: string | null // superior inmediato (id)
  manager_nombre: string | null // "Apellido, Nombre" resuelto por el backend
  // Espejo del CHECK `empleados_estado_check` (migración 120) y del `EstadoEmpleado` del
  // backend (`utils/estados_empleado.py`). Hasta el 18/8/2026 esta unión declaraba TRES valores
  // y el CHECK aceptaba cinco: le faltaba `suspendido` —que existe en la base desde siempre— y
  // `preingreso`. No era una omisión inofensiva: un preingreso que llegue por la API no
  // type-checkea contra esta unión, y eso rompe `next build` (no `next dev`, que transpila sin
  // chequear tipos — por eso se nota tarde y en el deploy).
  estado: "activo" | "baja" | "licencia" | "suspendido" | "preingreso"
  dias_vacaciones_asignados: number
  // Legajo ampliado (A1)
  email_personal: string | null
  tipo_documento: string | null
  sexo: string | null
  telefono_alternativo: string | null
  domicilio: string | null
  domicilio_calle: string | null
  domicilio_numero: string | null
  domicilio_piso_depto: string | null
  domicilio_localidad: string | null
  domicilio_provincia: string | null
  domicilio_cp: string | null
  estudios: string | null
  ubicacion: string | null
  turno: string | null
  horas_contrato: number | null
  organismo: string | null
  gerencia: string | null
  sector: string | null
  seniority: string | null
  perfil: string | null
  categoria: string | null
  referido: string | null
  es_lider: boolean
  created_at: string
}

export interface EmpleadoListResponse {
  items: Empleado[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

/**
 * Los DOS estados con los que un legajo puede NACER. Espejo del `EstadoAlta` del backend
 * (`utils/estados_empleado.py`), que es un `Literal["activo", "preingreso"]` — no de
 * `EstadoEmpleado`, que tiene cinco. `baja` o `licencia` en un alta no son estados iniciales
 * válidos: se llega a ellos por el flujo de offboarding o por una licencia, no dándose de alta.
 */
export type EstadoAlta = "activo" | "preingreso"

export interface EmpleadoCreate {
  empresa_id: string
  nombre: string
  apellido: string
  email_corporativo: string
  area_id: string
  roles: string[]
  modalidad_trabajo: string
  tipo_contrato: string
  fecha_ingreso: string
  /**
   * 🔴 SOLO EN EL ALTA. El pase `preingreso` → `activo` es el endpoint `/activar` (A3), no una
   * edición de campo: tiene una guarda propia —que la fecha de ingreso ya haya ocurrido— que
   * un PUT genérico se saltearía. Por eso el modal lo ofrece al crear y no al editar.
   * Ausente = `"activo"`, que es el default del backend.
   */
  estado?: EstadoAlta
  telefono?: string
  fecha_nacimiento?: string
  dni?: string
  cuil?: string
  legajo?: string
  manager_id?: string | null // superior inmediato (id); null explícito = limpiar (desasignar)
  cargo?: string // DEPRECADO (se quita en S6); el form ya no lo manda
  rol?: string // DEPRECADO (se quita en S6)
  dias_vacaciones_asignados?: number
  // Legajo ampliado (A1) — todos opcionales
  email_personal?: string
  tipo_documento?: string
  sexo?: string
  telefono_alternativo?: string
  domicilio?: string
  domicilio_calle?: string
  domicilio_numero?: string
  domicilio_piso_depto?: string
  domicilio_localidad?: string
  domicilio_provincia?: string
  domicilio_cp?: string
  estudios?: string
  ubicacion?: string
  turno?: string
  horas_contrato?: number
  organismo?: string
  gerencia?: string
  sector?: string
  seniority?: string
  perfil?: string
  categoria?: string
  referido?: string
  es_lider?: boolean
}

export type EmpleadoUpdate = Partial<EmpleadoCreate> & { estado?: string }

/** Proyección liviana de empleado para poblar selects (ej. superior inmediato). */
export interface EmpleadoSeleccionable {
  id: string
  nombre: string
  apellido: string
}

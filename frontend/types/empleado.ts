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
  /**
   * Los DOS datos de la baja. Vienen cargados SOLO en quien está de baja, así que en la enorme
   * mayoría de las filas son `null` y eso no es un faltante.
   *
   * 🔴 `motivo_baja` PUEDE SER NULL EN UNA BAJA REAL: una baja del import de nómina sin la
   * columna `Motivo Baja`, o sin instancia de offboarding detrás, no tiene motivo que contar.
   * La pantalla de Bajas lo muestra VACÍO — no le inventa un "Sin especificar", que convertiría
   * "no sabemos por qué se fue" en un motivo cargado.
   */
  fecha_egreso: string | null
  motivo_baja: string | null
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

/**
 * El vocabulario de orden que el listado (y su export) aceptan. Espejo del `OrdenEmpleados` del
 * backend (`schemas/_empleado_orden.py`); ausente = el orden de siempre, por apellido.
 *
 * 🔴 EL ORDEN LO PONE LA QUERY, NO EL CLIENTE, y es lo que hace que las dos pantallas nuevas
 * sean correctas con paginación: ordenar en el front reordena LA PÁGINA que llegó, así que con
 * 40 preingresos la primera página saldría ordenada entre sí pero no sería la de los que entran
 * primero. Por eso el param viaja al backend y ninguna tabla llama a `.sort()`.
 */
export type OrdenEmpleados = "fecha_ingreso_asc" | "fecha_egreso_desc"

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

/**
 * Los CUATRO estados que el PUT del legajo puede escribir. Espejo del `EstadoEditable` del
 * backend (`utils/estados_empleado.py`), que es un `Literal["activo", "licencia", "suspendido",
 * "preingreso"]`.
 *
 * 🔴 `baja` NO ESTÁ, y es la decisión de este tipo. Hasta el 20/8/2026 el PUT aceptaba los cinco
 * del CHECK, así que una edición cualquiera del legajo escribía `estado='baja'` **sin
 * `fecha_egreso` ni motivo** — sin pasar por `dar_de_baja`, que es donde las tres se escriben
 * juntas. Esa fila queda rota en los dos extremos del reporte a la vez y, desde que la pantalla
 * de Bajas ordena por `fecha_egreso DESC`, sale además primera de todo. La baja tiene dos vías y
 * solo dos: efectivizar un offboarding, o el import de nómina con `Fecha Baja`.
 *
 * ⚠️ NO es `EstadoEmpleado` (los cinco del CHECK, que es lo que el campo puede VALER y lo que
 * declara `Empleado.estado`): es lo que este camino puede ESCRIBIR. Son dos preguntas distintas
 * y el backend las tiene en dos Literals distintos por eso mismo.
 */
export type EstadoEditable = "activo" | "licencia" | "suspendido" | "preingreso"

/**
 * ⚠️ `Omit` + intersección, y NO `Partial<EmpleadoCreate> & { estado?: ... }` a secas. Con la
 * intersección sola, TypeScript INTERSECA los dos tipos del campo: `EstadoAlta & string` colapsa
 * a `EstadoAlta`, así que el tipo terminaba admitiendo DOS estados en vez de los cuatro que el
 * backend acepta — `licencia` y `suspendido` no se podían mandar y nadie lo notaba, porque el
 * `& { estado?: string }` se leía como si ensanchara. Medido con `tsc` el 20/8/2026.
 */
export type EmpleadoUpdate = Omit<Partial<EmpleadoCreate>, "estado"> & { estado?: EstadoEditable }

/** Proyección liviana de empleado para poblar selects (ej. superior inmediato). */
export interface EmpleadoSeleccionable {
  id: string
  nombre: string
  apellido: string
}

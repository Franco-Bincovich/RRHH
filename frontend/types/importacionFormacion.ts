/**
 * Tipos del import de Formación por Excel. Espejan `schemas/importacion_formacion.py`.
 *
 * Archivo propio y no dentro de `types/importacionObjetivos.ts` por la misma razón que del lado
 * del backend: son dos vocabularios distintos y mezclarlos obliga a leer el doble para entender
 * uno. El contrato de fondo sí es el mismo — el preview devuelve la fila YA RESUELTA y el
 * confirmar la recibe de vuelta: resolver para MOSTRAR, revalidar para ESCRIBIR.
 */

/** Una fila que NO se carga, con el motivo ya redactado por el backend para el usuario. */
export interface FilaFormacionError {
  fila: number
  identificador: string
  motivo: string
}

export interface FilaFormacionPreview {
  fila: number
  titulo: string
  /** Lo que decía la celda, para que el usuario reconozca su propia planilla. */
  colaborador: string
  /**
   * 🔴 UNO DE LOS DOS, NUNCA NINGUNO: o la persona matcheó contra el padrón (`empleado_id` +
   * `empleado_nombre`, el nombre del padrón para que se vea QUÉ matcheó) o entra como texto
   * suelto (`nombre_libre`). No matchear NO es un error: la formación queda cargada igual y la
   * persona se puede vincular después.
   */
  empleado_id: string | null
  empleado_nombre: string | null
  nombre_libre: string | null
  estado: "pendiente" | "en_curso" | "completado"
  fecha_asignacion: string | null
  fecha_completado: string | null
  proyecto: string | null
  anio: string | null
  mes: string | null
  /** Atributos del catálogo que esta fila aporta si su capacitación hay que crearla. */
  tipo: string | null
  entidad_capacitadora: string | null
  modalidad: string | null
  duracion_horas: number | null
  avisos: string[]
}

/** Un título que no existe en el catálogo de la empresa y el confirmar va a crear. */
export interface CapacitacionACrear {
  nombre: string
  tipo: string | null
  entidad_capacitadora: string | null
  modalidad: string | null
  duracion_horas: number | null
  avisos: string[]
}

/**
 * Dos nombres crudos distintos que probablemente sean la misma persona.
 *
 * 🔴 EL SISTEMA NO LOS UNIFICA Y NO DEBE: decide RRHH. Por eso viajan al front en vez de
 * resolverse en el backend — es el único grupo del preview que pide una acción HUMANA sobre el
 * archivo antes de importar.
 */
export interface ParParecido {
  nombre_a: string
  nombre_b: string
  motivo: string
}

export interface ImportacionFormacionPreview {
  filas_validas: FilaFormacionPreview[]
  errores: FilaFormacionError[]
  capacitaciones_a_crear: CapacitacionACrear[]
  /** Nombres que van a entrar como `nombre_libre`, sin vincular a un legajo. */
  sin_match: string[]
  pares_parecidos: ParParecido[]
  hoja_leida: string | null
  total_hojas: number
}

/**
 * 🔴 El resultado NO es binario. El lote no aborta por una fila con problemas: se cargan las
 * válidas y se reportan las otras, así que `importados > 0` y `errores.length > 0` conviven.
 */
export interface ImportacionFormacionResultado {
  importados: number
  errores: FilaFormacionError[]
  /** Nombres creados en el catálogo por este lote. */
  capacitaciones_creadas: string[]
}

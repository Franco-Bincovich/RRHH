/**
 * Tipos del import de objetivos por Excel. Espejan `schemas/importacion_objetivos.py`.
 *
 * Archivo propio y no dentro de `types/importacion.ts` por la misma razón que del lado del
 * backend: son dos vocabularios distintos y mezclarlos obliga a leer el doble para entender uno.
 */

/** Una fila que NO se va a cargar, con el motivo ya redactado por el backend para el usuario. */
export interface FilaObjetivoError {
  fila: number
  identificador: string
  motivo: string
}

export interface FilaObjetivoPreview {
  fila: number
  titulo: string
  /** Lo que decía la celda, para que el usuario reconozca su propia planilla. */
  responsable: string
  responsable_id: string
  responsable_nombre: string
  prioridad: string
  fecha_entrega: string | null
  descripcion: string | null
  /** Responsables adicionales ya resueltos (sin el dueño). */
  responsables_ids: string[]
  /** Lo que se va a cargar de menos y el usuario tiene que saber. Hoy solo "fecha". */
  faltantes: string[]
}

export interface ImportacionObjetivosPreview {
  filas_validas: FilaObjetivoPreview[]
  errores: FilaObjetivoError[]
  /** Cuál de las hojas se leyó — el backend lee siempre la primera. */
  hoja_leida: string | null
  total_hojas: number
}

/**
 * 🔴 El resultado NO es binario. El lote no aborta por una fila con problemas: se cargan las
 * válidas y se reportan las otras, así que `importados > 0` y `errores.length > 0` conviven.
 */
export interface ImportacionObjetivosResultado {
  importados: number
  errores: FilaObjetivoError[]
}

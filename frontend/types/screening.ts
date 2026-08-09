/**
 * Clasificador de CVs (migración 100): el criterio configurable y el resultado de una corrida.
 *
 * 🔴 Es un FILTRO DE DESCARTE, no una decisión. No rankea, no puntúa, no elige. Un humano revisa
 * siempre, incluido lo que quede en `no_relevante` — la pantalla no puede ocultarlos ni
 * colapsarlos por defecto, y la leyenda que lo dice va VISIBLE, no en un tooltip.
 */
import type { ClasificacionIA } from "@/types/candidato"

/**
 * Los cuatro campos configurables. Se INSERTAN COMO DATO dentro de la estructura fija del
 * prompt: no la reemplazan ni la extienden. NO son configurables —y no aparecen acá— la
 * separación system/user, el sanitizado del CV, las tres categorías, la validación de la salida
 * ni el sesgo "ante la duda, dudoso".
 */
export interface ScreeningCriterio {
  def_relevante: string
  def_dudoso: string
  def_no_relevante: string
  /** Opcional de verdad: vacío es el estado normal, no un pendiente. */
  instrucciones: string
}

export interface ScreeningCriterioResponse extends ScreeningCriterio {
  /**
   * `false` = la empresa está usando el criterio GLOBAL. Guardar en ese estado crea su fila
   * propia y la desengancha; "restaurar defaults" es exactamente volver acá.
   */
  es_propia: boolean
}

/** Qué pasó con un candidato en la corrida. Sin `clasificacion` ni `error` = no tenía CV legible. */
export interface CandidatoClasificado {
  candidato_id: string
  nombre: string
  clasificacion: ClasificacionIA | null
  motivo: string | null
  error: string | null
}

/**
 * Resultado NO BINARIO de la corrida: cuatro números distintos, ninguno deducible de los otros.
 *
 * · `clasificados` — llegaron al modelo y volvieron con una de las tres categorías.
 * · `sin_texto`    — el CV no se pudo leer (`screening_warning`): NO se clasifican y NO gastan
 *                    llamada. Van a revisión manual; no son un error del lote.
 * · `errores`      — el modelo devolvió algo inválido o la llamada falló. Quedan sin clasificar.
 * · `sin_procesar` — se acabó el presupuesto de tiempo, o quedaron fuera del tope por corrida.
 *                    Reintentable: el botón vuelve a tomarlos porque siguen sin clasificar.
 */
export interface ScreeningLoteResponse {
  clasificados: number
  sin_texto: number
  errores: number
  sin_procesar: number
  parcial: boolean
  tope_alcanzado: boolean
  segundos: number
  detalle: CandidatoClasificado[]
}

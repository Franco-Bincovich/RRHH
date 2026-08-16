/**
 * Configuración de reglas de negocio (migración 085).
 *
 * Todo resuelve por COALESCE(fila de mi empresa, fila global), y por eso cada bloque trae
 * `es_propia`: la pantalla necesita poder decir si estás mirando lo tuyo o lo heredado, porque
 * guardar mientras heredás CREA tu fila propia y te desengancha de la global.
 */

export interface Parametros {
  /** Denominador de la tasa de ausentismo. Era la constante 22 en el backend. */
  base_dias_habiles: number
  /** Mes contra el que se mide la antigüedad para ubicar al empleado en la escala. */
  corte_antiguedad_mes: number
  /**
   * Ventana en la que se pueden TOMAR vacaciones (p. ej. octubre→abril).
   *
   * ⚠️ CONCEPTO NUEVO Y HOY SOLO INFORMATIVO: no es cuándo se ganan los días ni cómo se mide
   * la antigüedad. El sistema GUARDA el valor y no lo aplica: NO hay validación que impida
   * cargar una licencia fuera de esta ventana, y no la habrá hasta definir si bloquea o solo
   * avisa. Ver el encabezado de la migración 085.
   */
  periodo_vacacional_desde_mes: number
  periodo_vacacional_hasta_mes: number
  /** En el primer año, mes desde el cual el ingreso otorga `primer_anio_dias`. */
  primer_anio_mes_corte: number
  primer_anio_dias: number
  /** Años que sobreviven los días no tomados antes de vencer. */
  vencimiento_anios: number
  /**
   * Migración 114. Días del período de prueba (LCT: 90). El "fin de período de prueba" de una
   * persona se calcula como `fecha_ingreso + periodo_prueba_dias`.
   *
   * ⚠️ HOY SOLO SE GUARDA Y SE MUESTRA: todavía no hay nada que lo calcule ni que avise. Está
   * expuesto porque es el valor que va a regir cuando eso se construya, y porque configurarlo
   * antes es gratis. Mismo estado que la ventana del período vacacional.
   */
  periodo_prueba_dias: number
  /**
   * Migración 114. Anticipación POR DEFECTO del aviso de un evento de agenda: con cuántos días
   * antes de la fecha aparece en el dashboard.
   *
   * 🔑 Es un DEFAULT, no una regla global: cada evento puede pisarlo con su propio `dias_aviso`.
   * Un evento que no lo trae toma este valor EN EL MOMENTO DEL ALTA y lo guarda como columna
   * propia, así que cambiarlo acá afecta a los eventos NUEVOS, no a los ya cargados.
   */
  dias_aviso_evento: number
}

export interface ParametrosResponse extends Parametros {
  es_propia: boolean
}

/** Un escalón: a partir de `antiguedad_anios` cumplidos corresponden `dias`. */
export interface TramoEscala {
  antiguedad_anios: number
  dias: number
}

export interface EscalaResponse {
  tramos: TramoEscala[]
  es_propia: boolean
}

export interface Configuracion {
  parametros: ParametrosResponse
  escala: EscalaResponse
}

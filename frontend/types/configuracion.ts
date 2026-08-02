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

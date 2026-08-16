/**
 * Tipos del circuito de RECEPCIÓN de candidatos por mail y de la publicación en LinkedIn.
 *
 * Salieron de `types/vacantes.ts`, que llegó a 201 contra un límite de 200 al sumarle
 * `VacanteListResponse`. El corte no es por tamaño: **ninguno de estos describe una vacante**.
 * Describen lo que pasa ANTES de que exista un candidato (qué mails llegaron, cuáles no se
 * pudieron resolver, cuánto alcanzó a procesar la corrida) y lo que pasa DESPUÉS de publicar
 * un aviso. Sus consumidores son tres archivos concretos: `MailsPendientes`,
 * `RevisarCasillaButton` y `services/vacantes.ts`.
 */

export interface LinkedinPublicarRequest {
  email_contacto: string
}

export interface LinkedinPublicarResponse {
  post_id: string
  url: string
  publicado_en: string
}

/** Un mail que la revisión de la casilla NO pudo resolver sola. */
export interface IngestaMailPendiente {
  message_id: string
  asunto: string
  remitente: string
  codigo: string | null
  descartados: string[]
  motivo: string | null
}

/**
 * El resumen de una corrida de "Revisar casilla".
 *
 * `ya_existian` viaja aparte de `candidatos_creados` a propósito: un reintento que dijera
 * "0 creados" parecería no haber hecho nada, cuando confirmó que la casilla ya estaba procesada.
 * `parcial` + `sin_procesar` son el corte por presupuesto de tiempo — sin ellos, una corrida
 * que se queda sin tiempo es indistinguible de una que terminó.
 */
export interface IngestaResultado {
  mails_leidos: number
  candidatos_creados: number
  ya_existian: number
  pendientes: IngestaMailPendiente[]
  parcial: boolean
  sin_procesar: number
  segundos: number
}

/** Un mail de la casilla que no matcheó ninguna búsqueda. NO se persiste: se relee cada vez. */
export interface MailPendiente {
  message_id: string
  asunto: string
  remitente: string
  fecha: string
  /** Contado por el backend SIN bajar los archivos (extensión + tamaño declarado). */
  adjuntos_validos: number
  nombres_adjuntos: string[]
  motivo: string
}

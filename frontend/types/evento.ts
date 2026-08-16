/**
 * Espejo de backend/schemas/evento_agenda.py (migración 113).
 *
 * Un evento de agenda es un RECORDATORIO con fecha, no un registro histórico: se puede editar y
 * borrar. El dashboard lo levanta cuando entra en su ventana de aviso (`fecha - dias_aviso`), y
 * desaparece de ahí cuando alguien lo marca resuelto — nunca por haber pasado de fecha.
 */

export interface Evento {
  id: string
  empresa_id: string
  nombre: string
  fecha: string
  descripcion: string | null
  /** Con cuántos días de anticipación avisa. El default por empresa sale de Configuración. */
  dias_aviso: number
  /** `true` = lo ve el equipo; `false` = solo quien lo creó (y gerencia, que lee todo). */
  es_publica: boolean
  resuelta: boolean
  resuelta_at: string | null
  resuelta_por: string | null
  resuelta_por_nombre: string | null
  created_by: string
  created_by_nombre: string | null
  empresa_nombre: string | null
  created_at: string
  updated_at: string | null
}

/**
 * `dias_aviso` va OPCIONAL y `null`/ausente significa "usá el default de la empresa", que el
 * backend lee de `parametros_empresa.dias_aviso_evento`. Mandar un número desde el front cuando
 * el usuario no lo tocó pisaría ese default con una copia que envejece sola.
 */
export interface EventoCreate {
  nombre: string
  fecha: string
  descripcion?: string
  dias_aviso?: number
  es_publica: boolean
}

export interface EventoUpdate {
  nombre?: string
  fecha?: string
  descripcion?: string
  dias_aviso?: number
  es_publica?: boolean
}

export interface EventoListResponse {
  items: Evento[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

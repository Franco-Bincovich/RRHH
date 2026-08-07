// Plantillas de mail (migración 087).

/** El cuerpo es MARKDOWN MÍNIMO, no HTML: el HTML lo genera el servidor al enviar. */
export interface Plantilla {
  id: string
  empresa_id: string | null
  clave: string
  contexto: string
  asunto: string
  cuerpo: string
  activa: boolean
  /**
   * Es la plantilla GLOBAL, no una propia de la empresa. Editarla NO la pisa para todas: crea
   * la versión de esta empresa, que a partir de ahí tiene precedencia.
   */
  es_global: boolean
  /**
   * El asunto o el cuerpo tienen alguna `{{variable}}`. **Lo calcula el BACKEND** y el front solo
   * lo lee: la regla "una plantilla con variables no se manda a una dirección suelta" tiene que
   * ser una sola. Con un regex propio acá, una divergencia habilitaría en pantalla algo que el
   * backend después rechaza con 422.
   */
  usa_variables: boolean
}

export interface PlantillasResponse {
  items: Plantilla[]
  /** contexto → variables disponibles. Viene del backend para que la UI ofrezca solo las
   * válidas y RRHH no las escriba a mano (que es de donde salen los typos). */
  contextos: Record<string, string[]>
}

/**
 * Una línea del historial de envíos (`mail_enviado`).
 *
 * NO trae `cuerpo_render`, y no es un olvido: el texto completo que recibió una persona no viaja
 * a una pantalla de listado. La allowlist de columnas vive en `repositories/mail_enviado_repo.py`.
 */
export interface MailEnviado {
  id: string
  plantilla_clave: string | null
  destinatario: string
  asunto_render: string
  estado: "enviado" | "fallido"
  /** El motivo, solo cuando `estado === "fallido"`. */
  error: string | null
  created_at: string
}

export interface MailHistorialResponse {
  items: MailEnviado[]
  /** El techo aplicado. El historial NO se pagina y NO expone un total: sirve para avisar que
   *  lo que se ve es un recorte de los últimos N, no el universo. */
  limite: number
}

/**
 * Filtros del historial. Viajan enteros de la UI al service (molde: `shared/filtros.ts`).
 *
 * Es un `type` con índice y no una `interface` para poder pasarlo a los helpers genéricos de
 * `shared/filtros.ts` (`setFiltro`, `filtrosActivos`), que piden `Record<string, ValorFiltro>`:
 * TS no considera que una `interface` satisfaga una firma de índice, aunque sus campos encajen.
 */
export type MailsFiltros = {
  [k: string]: string | undefined
  estado?: string
  fecha_desde?: string
  fecha_hasta?: string
}

/** Un destinatario al que NO se le pudo mandar, con el motivo tal cual lo dio el backend. */
export interface EnvioFallido {
  destinatario: string
  motivo: string
}

/**
 * El resultado de un envío masivo. 🔴 NO ES BINARIO, y por eso son cinco números y no un `ok`:
 * el backend manda de a uno con un PRESUPUESTO DE TIEMPO, así que un lote puede quedar a medias.
 * `omitidos` no es un fallo (ya se les había mandado hoy: es la idempotencia que hace que
 * reintentar el mismo lote continúe donde quedó en vez de mandar dos veces).
 */
export interface EnvioResponse {
  enviados: number
  omitidos: number
  fallidos: EnvioFallido[]
  /** Se agotó el presupuesto de tiempo: quedaron `sin_procesar` personas sin intentar. */
  parcial: boolean
  sin_procesar: number
  segundos: number | null
}

export interface PreviewResponse {
  asunto: string
  cuerpo_html: string
  /** Variables válidas que quedaron SIN VALOR con estos datos. Se marcan en amarillo: es donde
   * RRHH se entera ANTES de mandar, y no por el destinatario. */
  faltantes: string[]
  con_datos_reales: boolean
}

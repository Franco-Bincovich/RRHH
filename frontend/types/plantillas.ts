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
}

export interface PlantillasResponse {
  items: Plantilla[]
  /** contexto → variables disponibles. Viene del backend para que la UI ofrezca solo las
   * válidas y RRHH no las escriba a mano (que es de donde salen los typos). */
  contextos: Record<string, string[]>
}

export interface PreviewResponse {
  asunto: string
  cuerpo_html: string
  /** Variables válidas que quedaron SIN VALOR con estos datos. Se marcan en amarillo: es donde
   * RRHH se entera ANTES de mandar, y no por el destinatario. */
  faltantes: string[]
  con_datos_reales: boolean
}

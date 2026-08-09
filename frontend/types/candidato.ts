import type { ClasificacionIA, EtapaPipeline, OrigenClasificacion } from "@/types/vacantes"

export type { ClasificacionIA, OrigenClasificacion }

/** Lo que acepta el filtro: las tres, más el corte por "todavía sin clasificar". */
export type FiltroClasificacion = ClasificacionIA | "sin_clasificar"

/** Candidato con el nombre del grupo resuelto (vivo o congelado). Espejo de CandidatoGrupoResponse. */
export interface CandidatoConGrupo {
  id: string
  vacante_id: string | null
  nombre: string
  apellido: string
  email: string
  telefono: string | null
  cargo_anterior: string | null
  empresa_anterior: string | null
  etapa_pipeline: EtapaPipeline
  score_ia: number | null
  busqueda_congelada: string | null
  cv_storage_path: string | null
  /**
   * POR QUÉ el sistema no pudo leer el CV. Texto, no un flag: cada motivo pide una acción
   * distinta (pedir la contraseña, pedirlo en otro formato, abrirlo a mano). `cv_texto` no
   * viaja al front: es la entrada del clasificador y pesa hasta 20 KB por fila.
   */
  screening_warning: string | null
  /**
   * Filtro de descarte (mig 100). `null` = todavía no se clasificó.
   *
   * 🔴 NO es una decisión ni un ranking: un humano revisa SIEMPRE, incluidos los no_relevante.
   * Por eso la pantalla no puede ocultarlos ni colapsarlos por defecto, y por eso el motivo
   * viaja al lado — la etiqueta sola invita a confiar en ella.
   */
  clasificacion_ia: ClasificacionIA | null
  clasificacion_motivo: string | null
  clasificacion_origen: OrigenClasificacion | null
  created_at: string
  grupo_nombre: string | null
  busqueda_activa: boolean
}

/** Candidatos agrupados por búsqueda para la vista de la sección Candidatos. */
export interface GrupoCandidatos {
  nombre: string
  activa: boolean
  candidatos: CandidatoConGrupo[]
}

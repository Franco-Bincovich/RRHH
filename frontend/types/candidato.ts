import type { ClasificacionIA, EtapaPipeline, OrigenClasificacion } from "@/types/vacantes"

export type { ClasificacionIA, OrigenClasificacion }

/** Lo que acepta el filtro: las tres, más el corte por "todavía sin clasificar". */
export type FiltroClasificacion = ClasificacionIA | "sin_clasificar"

/**
 * Si la POSTULACIÓN sigue viva. Espejo de `EstadoCandidato` (`backend/schemas/candidato.py:39`),
 * que a su vez es el espejo del CHECK `candidatos_estado_check`.
 *
 * 🔴 ES OTRO EJE QUE `etapa_pipeline`, no una versión suya. La etapa dice DÓNDE está la persona
 * en el proceso (postulado → … → oferta); el estado dice SI sigue en carrera. Alguien descartado
 * en entrevista técnica conserva la etapa en la que se cayó, que es lo que permite medir en qué
 * punto se cae la gente. Por eso el puente a empleado exige LAS DOS cosas: etapa `oferta` y
 * estado `activo`.
 *
 * ⚠️ El backend viene exponiendo este campo desde A4.1 y este tipo NO lo declaraba, así que
 * llegaba por HTTP y el front lo descartaba sin que nadie lo notara — la misma falla silenciosa
 * que el comentario de `schemas/candidato.py:104-111` documenta del lado del mapper.
 */
export type EstadoCandidato = "activo" | "descartado" | "contratado" | "en_espera"

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
  estado: EstadoCandidato
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
  /**
   * Cuántos candidatos tiene la búsqueda EN TODO EL FILTRO, no en la página.
   *
   * 🔴 ES DISTINTO DE `candidatos.length` Y ESA ES LA RAZÓN DE QUE EXISTA. El listado se
   * pagina PLANO y la pantalla agrupa dentro de la página: una búsqueda de 40 candidatos
   * puede aparecer con 4 filas en la página 3. Sin este campo el encabezado diría "4", que
   * es un número plausible, falso, y que además CAMBIA al pasar de página.
   *
   * Lo calcula el backend (`_contar_grupos`) sobre el conjunto filtrado entero, con una sola
   * query de dos columnas — no un count por búsqueda, que serían N round trips.
   */
  totalGrupo: number
}

/** Una página del listado de candidatos. Espejo de `CandidatosPaginaResponse`. */
export interface CandidatosPagina {
  items: CandidatoConGrupo[]
  total: number
  page: number
  page_size: number
  total_pages: number
  /** nombre de grupo → cuántos tiene en TODO el filtro. Ver `GrupoCandidatos.totalGrupo`. */
  conteo_por_grupo: Record<string, number>
}

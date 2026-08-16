export type EstadoVacante = "nueva" | "en_proceso" | "con_candidatos" | "cerrada"

/**
 * Las tres categorías del filtro de descarte de CVs (mig 100). Espejo del CHECK de la base.
 *
 * Vive acá y NO en `candidato.ts` para que la dependencia entre los dos módulos siga yendo en
 * una sola dirección: `candidato.ts` ya importa `EtapaPipeline` de este archivo, así que
 * declararlo allá y usarlo acá cerraba el ciclo.
 */
export type ClasificacionIA = "relevante" | "dudoso" | "no_relevante"

/**
 * Quién puso la clasificación vigente (mig 101).
 *
 * 🔴 La pantalla lo muestra: quien revisa después tiene que poder distinguir una salida del
 * modelo de una decisión que alguien ya tomó. Sin eso, dos personas corrigen lo mismo dos veces
 * —o la segunda revierte a la primera sin saber que hubo una primera.
 */
export type OrigenClasificacion = "modelo" | "humano"

export type EtapaPipeline =
  | "postulado"
  | "assessment"
  | "entrevista_rrhh"
  | "entrevista_tecnica"
  | "oferta"

export type ModalidadVacante = "presencial" | "remoto" | "hibrido"

export interface Vacante {
  id: string
  /** `VAC-0001`. Lo genera la base (mig 097); RRHH no lo elige ni lo edita. NO es opcional. */
  codigo: string
  empresa_id: string | null
  empresa_nombre: string | null
  titulo: string
  area_id: string
  area_nombre: string | null
  descripcion: string | null
  requisitos: string | null
  tipo_contrato: string | null
  estado: EstadoVacante
  fecha_apertura: string | null
  created_at: string
  linkedin_post_id: string | null
  linkedin_url: string | null
  email_contacto: string | null
  copy_publicacion: string | null
  hashtags: string | null
  ubicacion: string | null
  modalidad: string | null
  jornada: string | null
  funciones: string | null
  formacion: string | null
  experiencia: string | null
  conocimientos_tecnicos: string | null
}

/**
 * Lo que RRHH copia para pegar en el aviso de LinkedIn.
 *
 * `texto` lo arma el BACKEND, no esta capa: es la instrucción que va a leer un candidato, y de
 * que se escriba igual todas las veces depende que el matcher encuentre el código. Si la armara
 * el front, cada aviso saldría con una variante y el CV terminaría en "sin asignar".
 *
 * `casilla` y `texto` son null cuando no hay casilla del sistema designada. `codigo` nunca lo es.
 */
export interface AvisoPostulacion {
  codigo: string
  casilla: string | null
  texto: string | null
}

export interface AsignacionResultado {
  candidatos_creados: string[]
  vacante_id: string
}

export interface VacanteCreate {
  empresa_id: string
  titulo: string
  area_id: string
  tipo_contrato: string
}

export interface VacanteUpdate {
  titulo?: string
  area_id?: string
  descripcion?: string
  requisitos?: string | null
  tipo_contrato?: string
  estado?: EstadoVacante
  copy_publicacion?: string | null
  hashtags?: string | null
  email_contacto?: string | null
  ubicacion?: string | null
  modalidad?: string | null
  jornada?: string | null
  funciones?: string | null
  formacion?: string | null
  experiencia?: string | null
  conocimientos_tecnicos?: string | null
}

export interface Candidato {
  id: string
  vacante_id: string
  nombre: string
  apellido: string
  email: string
  cargo_anterior: string | null
  empresa_anterior: string | null
  etapa_pipeline: EtapaPipeline
  score_ia: number | null
  /**
   * Resultado del filtro de descarte (mig 100). El backend ya lo mandaba —el endpoint del
   * pipeline usa el mismo `CandidatoResponse`—; sin estas líneas el tipo lo descartaba y la
   * tarjeta no podía mostrarlo, que es el punto donde más se necesita: es la pantalla desde la
   * que se aprieta el botón.
   */
  clasificacion_ia: ClasificacionIA | null
  clasificacion_motivo: string | null
  /** Quién puso la clasificación vigente (mig 101). `null` = no hay clasificación. */
  clasificacion_origen: OrigenClasificacion | null
  /** Ruta en el bucket PRIVADO `cvs`. No se linkea: se cambia por una signed URL al abrir. */
  cv_storage_path: string | null
  /** Por qué el archivo no se pudo leer. Distinto de un fallo del clasificador. */
  screening_warning: string | null
  created_at: string
}

export interface CandidatoCreate {
  nombre: string
  apellido: string
  email: string
  cargo_anterior?: string
  empresa_anterior?: string
  cv_url?: string
}

export interface VacanteListResponse {
  items: Vacante[]
  /**
   * 🔴 Total del FILTRO sin paginar, no `items.length`. `items` es una página: el contador del
   * encabezado tiene que leer esto, o dirá 20 sobre 200 sin que nada falle.
   */
  total: number
  page: number
  page_size: number
  total_pages: number
}

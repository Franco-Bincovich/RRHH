import type { EtapaPipeline } from "@/types/vacantes"

/**
 * El vocabulario del pipeline de selección: qué etapas hay, en qué orden y de qué color.
 *
 * Vivía adentro de `app/(dashboard)/vacantes/[id]/page.tsx`, que estaba en 452 líneas contra un
 * límite de 150 —el archivo más grande del front—. Se sacó al cortar esa página.
 *
 * 🔴 `ETAPAS` ES EL ORDEN DEL EMBUDO Y DE AHÍ SALE EL BOTÓN "→ siguiente": el componente calcula
 * la etapa próxima como `ETAPAS[indexOf(etapa) + 1]`. Reordenar este array cambia el circuito de
 * selección, no la presentación. La última no tiene siguiente y por eso no muestra el botón.
 *
 * ⚠️ Los colores son de COLUMNA, no semánticos: son cinco casilleros que hay que distinguir de un
 * vistazo mientras se arrastra la vista de izquierda a derecha, como las calles de un tablero. No
 * dicen "bien" ni "mal" —estar en `oferta` no es un logro del sistema, es una posición—, así que
 * no usan los pares `--success`/`--warning`/`--danger`, que sí significan eso en el resto del
 * producto. El chip de estado de la barra de identidad de la vacante es el que usa esos pares.
 */
export const ETAPAS: EtapaPipeline[] = [
  "postulado",
  "assessment",
  "entrevista_rrhh",
  "entrevista_tecnica",
  "oferta",
]

export const ETAPA_LABELS: Record<EtapaPipeline, string> = {
  postulado: "Postulado",
  assessment: "Assessment",
  entrevista_rrhh: "Entrevista Capital Humano",
  entrevista_tecnica: "Entrevista Técnica",
  oferta: "Oferta",
}

export const ETAPA_COLUMN_BG: Record<EtapaPipeline, string> = {
  postulado: "bg-slate-50 dark:bg-slate-800/40",
  assessment: "bg-amber-50 dark:bg-amber-900/20",
  entrevista_rrhh: "bg-blue-50 dark:bg-blue-900/20",
  entrevista_tecnica: "bg-purple-50 dark:bg-purple-900/20",
  oferta: "bg-emerald-50 dark:bg-emerald-900/20",
}

export const ETAPA_DOT: Record<EtapaPipeline, string> = {
  postulado: "bg-slate-400",
  assessment: "bg-amber-400",
  entrevista_rrhh: "bg-blue-500",
  entrevista_tecnica: "bg-purple-500",
  oferta: "bg-emerald-500",
}

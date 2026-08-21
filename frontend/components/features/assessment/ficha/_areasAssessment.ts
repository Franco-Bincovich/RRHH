/**
 * El vocabulario de dimensiones del resultado de un assessment: qué se muestra, en qué orden y
 * de qué color.
 *
 * Vivía adentro de `app/(dashboard)/assessment/[id]/page.tsx`, que estaba en 193 líneas contra un
 * límite de 150. Se sacó al agregarle la barra de identidad.
 *
 * ⚠️ `AREAS_ORDER` es el orden del modelo AREAS y NO alfabético: las cinco dimensiones se leen
 * juntas como perfil, y reordenarlas cambia la forma del radar sin cambiar un solo dato. Las dos
 * que no están en la tupla —cognitivo y técnico— existen en `AREAS_LABELS` a propósito: no son
 * del modelo AREAS, no entran al radar, y se listan aparte abajo.
 *
 * 🔴 LOS COLORES SON DE DIMENSIÓN, NO DE ESTADO, y por eso siguen siendo la paleta cruda y no los
 * pares semánticos. Un verde acá no dice "bien" y un rojo no dice "mal": son cinco etiquetas que
 * hay que poder distinguir de un vistazo, como las series de un gráfico. El chip de la barra de
 * identidad —que sí es semántico— usa los pares de la paleta; son dos cosas distintas.
 */
export const AREAS_ORDER = ["apertura", "responsabilidad", "estabilidad", "amabilidad", "sociabilidad"] as const

export const AREAS_LABELS: Record<string, string> = {
  apertura:        "Apertura",
  responsabilidad: "Responsabilidad",
  estabilidad:     "Estabilidad",
  amabilidad:      "Amabilidad",
  sociabilidad:    "Sociabilidad",
  cognitivo:       "Cognitivo",
  tecnico:         "Técnico",
}

export const AREAS_STYLE: Record<string, { bar: string; bg: string }> = {
  apertura:        { bar: "bg-blue-500",    bg: "bg-blue-50/50 dark:bg-blue-900/20"       },
  responsabilidad: { bar: "bg-emerald-500", bg: "bg-emerald-50/50 dark:bg-emerald-900/20" },
  estabilidad:     { bar: "bg-amber-500",   bg: "bg-amber-50/50 dark:bg-amber-900/20"     },
  amabilidad:      { bar: "bg-rose-500",    bg: "bg-rose-50/50 dark:bg-rose-900/20"       },
  sociabilidad:    { bar: "bg-purple-500",  bg: "bg-purple-50/50 dark:bg-purple-900/20"   },
  cognitivo:       { bar: "bg-sky-500",     bg: "bg-sky-50/50 dark:bg-sky-900/20"         },
  tecnico:         { bar: "bg-teal-500",    bg: "bg-teal-50/50 dark:bg-teal-900/20"       },
}

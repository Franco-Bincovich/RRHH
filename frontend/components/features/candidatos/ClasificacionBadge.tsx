import { Badge } from "@/components/ui/badge"
import type { ClasificacionIA } from "@/types/candidato"

/**
 * La etiqueta del filtro de descarte (mig 100).
 *
 * 🔴 LOS TRES COLORES SON DEL MISMO PESO VISUAL, a propósito. `no_relevante` NO va en rojo ni
 * atenuado: un rojo lo lee como "descartado" y un gris claro invita a saltearlo con la vista, y
 * las dos cosas son exactamente lo que este módulo no es. Un humano revisa siempre, incluidos
 * los no_relevante — la etiqueta informa, no decide.
 */
const ESTILOS: Record<ClasificacionIA, string> = {
  relevante: "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-100",
  dudoso: "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100",
  no_relevante: "border-slate-300 bg-slate-100 text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100",
}

const LABELS: Record<ClasificacionIA, string> = {
  relevante: "Relevante",
  dudoso: "Dudoso",
  no_relevante: "No relevante",
}

interface Props {
  clasificacion: ClasificacionIA | null
  /** Sin CV legible: se distingue de "todavía no se corrió" porque la acción es distinta. */
  sinTexto?: boolean
  /**
   * La corrida llegó al modelo y falló. 🔴 TRES estados sin clasificación, no uno:
   *   · nunca se corrió       → "Sin clasificar"   → acción: apretar el botón.
   *   · el CV no se pudo leer → "CV no legible"    → acción: pedirle otro CV al candidato.
   *   · el clasificador falló → "No se pudo clasificar" → acción: reintentar el botón.
   * Antes los tres decían lo mismo y el tercero además se perdía al recargar.
   */
  fallo?: boolean
}

export function ClasificacionBadge({ clasificacion, sinTexto, fallo }: Props) {
  if (!clasificacion) {
    // El orden importa: un CV ilegible nunca llega al clasificador, así que si vienen los dos
    // manda el warning del archivo — es la causa raíz y la que dice qué hacer.
    const texto = sinTexto ? "CV no legible" : fallo ? "No se pudo clasificar" : "Sin clasificar"
    return <Badge variant="outline" className="text-muted-foreground">{texto}</Badge>
  }
  return <Badge variant="outline" className={ESTILOS[clasificacion]}>{LABELS[clasificacion]}</Badge>
}

/**
 * La leyenda del módulo. VISIBLE, nunca en un tooltip: si hay que pasar el mouse para enterarse
 * de que esto no decide nada, la mitad de la gente no se entera.
 */
export function LeyendaDescarte() {
  return (
    <p className="rounded-lg border border-dashed bg-muted/40 p-3 text-xs text-muted-foreground">
      <strong className="text-foreground">Es un filtro de descarte, no una decisión.</strong>{" "}
      El sistema no elige ni ordena candidatos: solo separa lo que a primera vista no corresponde
      a la búsqueda. Revisá todos los CVs, incluidos los marcados como no relevantes.
    </p>
  )
}

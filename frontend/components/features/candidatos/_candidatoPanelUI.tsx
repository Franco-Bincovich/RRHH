import type { EtapaPipeline } from "@/types/vacantes"

/**
 * Los primitivos de presentación del panel de detalle de un candidato: el mapa de etiquetas de
 * etapa y las dos cajas con las que el panel arma sus secciones.
 *
 * Extraídos de `CandidatoDetailPanel.tsx`, que llegó a 154/150 al sumarle la contratación. El
 * corte es por CAPA: acá queda lo que no sabe nada del candidato ni de la API —dos componentes
 * sin estado y una tabla de textos—, y allá el drawer con su ciclo de vida, el foco y las
 * llamadas. Es también lo que deja lugar para las acciones nuevas sin volver a tocar el límite.
 */

export const ETAPA_LABELS: Record<EtapaPipeline, string> = {
  postulado: "Postulado",
  assessment: "Assessment",
  entrevista_rrhh: "Entrevista RRHH",
  entrevista_tecnica: "Entrevista Técnica",
  oferta: "Oferta",
}

/** Sección del panel: título + contenido. Base para ampliar a edición/notas a futuro. */
export function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</h3>
      {children}
    </section>
  )
}

/** Campo label + valor; no renderiza nada si el valor está vacío. */
export function Campo({ label, value }: { label: string; value: string | null }) {
  if (!value) return null
  return (
    <div className="flex justify-between gap-4 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="min-w-0 truncate text-right text-foreground">{value}</span>
    </div>
  )
}

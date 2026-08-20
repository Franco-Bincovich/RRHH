import { Mail } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { ClasificacionBadge } from "@/components/features/candidatos/ClasificacionBadge"
import type { EtapaPipeline } from "@/types/vacantes"
import type { CandidatoConGrupo } from "@/types/candidato"

const ETAPA_LABELS: Record<EtapaPipeline, string> = {
  postulado: "Postulado",
  assessment: "Assessment",
  entrevista_rrhh: "Entrevista Capital Humano",
  entrevista_tecnica: "Entrevista Técnica",
  oferta: "Oferta",
}

interface Props {
  candidato: CandidatoConGrupo
  onSelect: () => void
}

/** Fila de un candidato (clickeable): nombre, email, cargo anterior y etapa del pipeline. */
export function CandidatoRow({ candidato, onSelect }: Props) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect() } }}
      className="flex cursor-pointer flex-wrap items-center justify-between gap-2 rounded-lg border bg-card p-3 transition-colors hover:bg-muted/50"
    >
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-foreground">
          {candidato.nombre} {candidato.apellido}
        </p>
        <p className="flex items-center gap-1.5 truncate text-xs text-muted-foreground">
          <Mail className="size-3 shrink-0" /> {candidato.email}
        </p>
        {candidato.cargo_anterior && (
          <p className="truncate text-xs text-muted-foreground">{candidato.cargo_anterior}</p>
        )}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {/* Solo se muestra si ya se clasificó: un "Sin clasificar" en cada fila de una empresa
            que todavía no usa el screening sería ruido en todas las filas. En la ficha sí
            aparece siempre, porque ahí la pregunta "¿se corrió?" es pertinente. */}
        {candidato.clasificacion_ia && (
          <ClasificacionBadge clasificacion={candidato.clasificacion_ia} />
        )}
        <Badge variant="secondary">{ETAPA_LABELS[candidato.etapa_pipeline] ?? candidato.etapa_pipeline}</Badge>
      </div>
    </div>
  )
}

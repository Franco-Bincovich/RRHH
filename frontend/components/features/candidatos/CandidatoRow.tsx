import { Mail } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { ClasificacionBadge } from "@/components/features/candidatos/ClasificacionBadge"
import { EstadoCandidatoBadge } from "@/components/features/candidatos/EstadoCandidatoBadge"
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

/**
 * Fila de un candidato (clickeable): nombre, email, cargo anterior, DESENLACE y etapa.
 *
 * 🔴 LA FILA PINTA LOS DOS EJES, y hasta el 24/8/2026 pintaba uno solo. `etapa_pipeline` dice
 * DÓNDE llegó en el proceso y `estado` dice CÓMO terminó; contratar a alguien cambia el segundo
 * y deja el primero en "oferta" a propósito (es la métrica del embudo). Con una sola etiqueta,
 * la tarjeta de alguien ya contratado seguía diciendo **Oferta** para siempre. El porqué
 * completo está en `EstadoCandidatoBadge`.
 *
 * ⚠️ EL DESENLACE VA PRIMERO. Con la etapa a la izquierda, "Oferta" es lo que se lee de un
 * vistazo y el desenlace queda como una aclaración al costado — al revés de lo que importa.
 */
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
        <EstadoCandidatoBadge estado={candidato.estado} />
        {/* La etapa baja a `outline` cuando hay desenlace: sigue estando —es el dato del
            embudo— pero deja de competir por la atención con el que contesta la pregunta. */}
        <Badge variant={candidato.estado === "activo" ? "secondary" : "outline"}>
          {ETAPA_LABELS[candidato.etapa_pipeline] ?? candidato.etapa_pipeline}
        </Badge>
      </div>
    </div>
  )
}

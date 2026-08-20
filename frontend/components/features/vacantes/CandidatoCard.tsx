"use client"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { ClasificacionBadge } from "@/components/features/candidatos/ClasificacionBadge"
import type { ClasificacionIA, EtapaPipeline } from "@/types/vacantes"

const ETAPA_LABELS: Record<EtapaPipeline, string> = {
  postulado: "Postulado",
  assessment: "Assessment",
  entrevista_rrhh: "Entrevista Capital Humano",
  entrevista_tecnica: "Entrevista Técnica",
  oferta: "Oferta",
}

const ETAPA_VARIANTS: Record<EtapaPipeline, "default" | "secondary" | "outline"> = {
  postulado: "outline",
  assessment: "secondary",
  entrevista_rrhh: "default",
  entrevista_tecnica: "default",
  oferta: "secondary",
}

export interface CandidatoCardProps {
  nombre: string
  cargoAnterior: string
  fechaAplicacion: string
  etapa: EtapaPipeline
  /** Resultado del filtro de descarte. `null` = todavía sin clasificar. */
  clasificacion?: ClasificacionIA | null
  /** El motivo, en términos de lo que el CV dice. Va junto a la etiqueta, nunca sin ella. */
  motivo?: string | null
  /** El CV no se pudo leer. Es un estado distinto de "el clasificador falló". */
  sinTexto?: boolean
  /** Llegó al modelo y falló: hay motivo pero no hay clasificación. Reintentable. */
  fallo?: boolean
  /** Si la puso un humano, se dice — para que el revisor siguiente no la pise sin saberlo. */
  origen?: string | null
}

function getInitials(nombre: string): string {
  return nombre
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0] ?? "")
    .join("")
    .toUpperCase()
}

export function CandidatoCard({ nombre, cargoAnterior, fechaAplicacion, etapa, clasificacion,
                               motivo, sinTexto, fallo, origen }: CandidatoCardProps) {
  return (
    // 🔴 SIN `cursor-pointer` ni `hover:shadow-md`: la tarjeta nunca tuvo `onClick`, así que
    // esos estilos prometían un click que no existía. Las acciones son explícitas y viven
    // debajo (`CandidatoAccionesPipeline`). Una tarjeta que miente es peor que una que no invita.
    <div className="rounded-lg border bg-card p-3 shadow-sm">
      <div className="flex items-start gap-3">
        <Avatar>
          <AvatarFallback>{getInitials(nombre)}</AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-foreground">{nombre}</p>
          <p className="truncate text-xs text-muted-foreground">{cargoAnterior}</p>
        </div>
      </div>
      {/* 🔴 El motivo va SIEMPRE que haya etiqueta. Una etiqueta sola se lee como veredicto;
          con el motivo al lado se lee como observación, que es lo que es. */}
      <div className="mt-2.5 space-y-1">
        <ClasificacionBadge clasificacion={clasificacion ?? null} sinTexto={sinTexto} fallo={fallo} />
        {motivo && <p className="text-xs text-muted-foreground">{motivo}</p>}
        {origen === "humano" && (
          <p className="text-xs font-medium text-foreground">Corregido a mano</p>
        )}
      </div>
      <div className="mt-2.5 flex items-center justify-between gap-2">
        <Badge variant={ETAPA_VARIANTS[etapa]}>{ETAPA_LABELS[etapa]}</Badge>
        <span className="whitespace-nowrap text-xs text-muted-foreground">{fechaAplicacion}</span>
      </div>
    </div>
  )
}

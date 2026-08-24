"use client"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { ClasificacionBadge } from "@/components/features/candidatos/ClasificacionBadge"
import type { ClasificacionIA, EtapaPipeline } from "@/types/vacantes"
import { Card } from "@/components/ui/card"

const ETAPA_LABELS: Record<EtapaPipeline, string> = {
  postulado: "Postulado",
  assessment: "Assessment",
  entrevista_rrhh: "Entrevista Capital Humano",
  entrevista_tecnica: "Entrevista Técnica",
  oferta: "Oferta",
}

/**
 * 🔴 NINGUNA ETAPA ES AZUL, y ese es el cambio. Las dos entrevistas venían con
 * `variant="default"`, o sea `bg-primary`: un relleno azul en la tarjeta de cada candidato,
 * compitiendo con el único relleno azul que el patrón permite en una pantalla — el chip de filtro
 * (`docs/SISTEMA-DE-DISENO.md` §3). El pipeline es un EMBUDO y la escala lo sigue: contorno al
 * entrar, gris a medida que avanza y el par de éxito solo en `oferta`, que es el único hito que
 * esta tarjeta celebra. Los pares salen de la paleta, medidos en los dos temas por
 * `app/contrasteTokens.test.ts`.
 */
const ETAPA_ESTILOS: Record<EtapaPipeline, string> = {
  postulado: "",
  assessment: "bg-secondary text-secondary-foreground border-border",
  entrevista_rrhh: "bg-secondary text-secondary-foreground border-border",
  entrevista_tecnica: "bg-secondary text-secondary-foreground border-border",
  oferta: "bg-success-wash text-success border-success-line",
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
    <Card padding="none" interactive className="rounded-lg p-3 shadow-sm">
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
        <Badge variant="outline" className={ETAPA_ESTILOS[etapa]}>{ETAPA_LABELS[etapa]}</Badge>
        <span className="whitespace-nowrap text-xs text-muted-foreground">{fechaAplicacion}</span>
      </div>
    </Card>
  )
}

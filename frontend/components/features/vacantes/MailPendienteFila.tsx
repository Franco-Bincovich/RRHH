"use client"

import { Paperclip } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Select } from "@/components/ui/select"
import type { Vacante } from "@/types/vacantes"
import type { MailPendiente } from "@/types/vacantesIngesta"

/**
 * UN mail de la casilla que no matcheó, con su selector de búsqueda y su botón de asignar.
 *
 * Salió de `MailsPendientes.tsx`, que quedó en 155/150 al separar los DOS estados de error
 * (leer la casilla vs asignar un mail) — la división que ese arreglo pedía. El corte es por
 * capa y no por conteo: acá no hay estado ni fetch, solo la tarjeta; el orquestador se queda
 * con la carga, los errores y qué se muestra.
 *
 * ⚠️ `adjuntos_validos` viene contado por el backend SIN bajar los archivos (extensión + tamaño
 * declarado). Un mail con 0 no se puede asignar: no crearía ningún candidato.
 */
const MOTIVO: Record<string, string> = {
  sin_codigo: "Sin código en el asunto",
  codigo_ambiguo: "Más de un código en el asunto",
  vacante_desconocida: "El código no corresponde a ninguna búsqueda",
}

interface Props {
  mail: MailPendiente
  vacantes: Vacante[]
  elegida: string
  asignando: boolean
  onElegir: (vacanteId: string) => void
  onAsignar: () => void
}

export function MailPendienteFila({ mail, vacantes, elegida, asignando, onElegir, onAsignar }: Props) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-foreground">{mail.remitente || "(sin remitente)"}</p>
          <p className="truncate text-sm text-muted-foreground">{mail.asunto || "(sin asunto)"}</p>
          <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            <span>{mail.fecha}</span>
            <span className="inline-flex items-center gap-1">
              <Paperclip className="size-3" />
              {mail.adjuntos_validos} CV{mail.adjuntos_validos !== 1 ? "s" : ""}
              {mail.nombres_adjuntos.length > 0 && `: ${mail.nombres_adjuntos.join(", ")}`}
            </span>
            <span>{MOTIVO[mail.motivo] ?? mail.motivo}</span>
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Select
            className="w-auto"
            aria-label={`Asignar ${mail.asunto || mail.message_id} a una búsqueda`}
            value={elegida}
            onChange={(e) => onElegir(e.target.value)}
          >
            <option value="">Elegí una búsqueda…</option>
            {vacantes.map((v) => (
              <option key={v.id} value={v.id}>{v.codigo} · {v.titulo}</option>
            ))}
          </Select>
          <Button
            size="sm"
            className="min-h-10"
            disabled={!elegida || mail.adjuntos_validos === 0 || asignando}
            onClick={onAsignar}
          >
            {asignando ? "Asignando…" : "Asignar"}
          </Button>
        </div>
      </div>
    </div>
  )
}

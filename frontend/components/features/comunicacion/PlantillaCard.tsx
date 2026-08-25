"use client"

import { Pencil, Send } from "lucide-react"
import { AccionFila } from "@/components/ui/AccionFila"

import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import type { Plantilla } from "@/types/plantillas"

export function PlantillaCard({ plantilla, editable, bloqueo, onEditar, onEnviar }: {
  plantilla: Plantilla
  editable: boolean
  /**
   * Por qué HOY las dos acciones no pueden funcionar (vista consolidada), o `null`.
   *
   * 🔑 UNA SOLA PROP PARA LAS DOS porque las dos terminan en un endpoint que exige empresa
   * concreta: enviar (`POST /enviar`) y editar (el `PUT` que hace el modal al guardar). El
   * MOTIVO no se repite por tarjeta —serían N copias del mismo cartel en una grilla— sino que
   * lo muestra una vez `PlantillasSection`, arriba, junto al botón de alta. Acá va como `title`
   * sobre el wrapper, porque un `<AccionFila disabled>` no dispara eventos de mouse.
   */
  bloqueo: string | null
  onEditar: (p: Plantilla) => void
  onEnviar: (p: Plantilla) => void
}) {
  return (
    <Card padding="sm" interactive className="group flex h-full flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        <p className="min-w-0 flex-1 truncate text-sm font-semibold text-foreground">{plantilla.clave}</p>
        {/* "General" = la plantilla no cuelga de una empresa. Contorno y no relleno: el único
            relleno azul que el patrón permite en una pantalla es el chip de filtro (§3). */}
        {plantilla.es_global && <Badge variant="outline" className="shrink-0">General</Badge>}
      </div>

      {/* El asunto se lee ENTERO (dos líneas) y no truncado: es el texto que la persona ve en su
          bandeja, y es lo que se viene a revisar antes de mandar. */}
      <p className="line-clamp-2 text-xs leading-relaxed text-muted-foreground">{plantilla.asunto}</p>

      {editable && (
        <div className="mt-auto flex justify-end gap-1 pt-1" title={bloqueo ?? undefined}>
          <AccionFila aria-label={`Enviar ${plantilla.clave}`} disabled={Boolean(bloqueo)}
            onClick={() => onEnviar(plantilla)}>
            <Send className="size-4" aria-hidden="true" />
          </AccionFila>
          <AccionFila aria-label={`Editar ${plantilla.clave}`} disabled={Boolean(bloqueo)}
            onClick={() => onEditar(plantilla)}>
            <Pencil className="size-4" aria-hidden="true" />
          </AccionFila>
        </div>
      )}
    </Card>
  )
}

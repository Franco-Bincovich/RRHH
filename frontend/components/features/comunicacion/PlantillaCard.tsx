"use client"

import { Pencil, Send } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import type { Plantilla } from "@/types/plantillas"

/**
 * Una plantilla de mail, como TARJETA.
 *
 * 🔴 ES UNA TARJETA Y NO UNA FILA, y eso es lo que dice el sistema de diseño: §5 nombra a
 * comunicación junto a perfiles de puesto y reportes — "cada plantilla de mail guardada, una
 * tarjeta". El criterio de §5 es el que decide, no el tipo de dato: una tarjeta es para algo que
 * **se elige**, una fila para un registro que **se compara con el de al lado**. Nadie compara dos
 * plantillas entre sí: se busca la que hay que mandar o corregir, y para eso el asunto —el texto
 * que la persona va a ver en su bandeja— tiene que poder leerse entero, no truncado en una celda.
 *
 * ⚠️ Hasta el 21/8/2026 esto era una lista de filas dentro de un acordeón, y el propio archivo ya
 * anotaba que el acordeón sobraba ("un acordeón de un solo ítem adentro de una pestaña es
 * redundante, quedó pendiente a propósito"). Al pasar a tarjetas el acordeón se fue con él.
 *
 * 🔴 LAS DOS ACCIONES ESTÁN SIEMPRE VISIBLES y sólo cambian de color al apuntar (§3). En una
 * grilla, revelarlas en hover obliga a barrer la pantalla con el mouse para saber qué se puede
 * hacer con cada tarjeta. Van juntas detrás de `editable` —no de dos gates distintos— porque el
 * backend gatea `PUT /api/plantillas` y `POST /api/plantillas/enviar` con el MISMO permiso: un
 * botón de enviar visible para `gerencia_lectura` daría 403 al apretarlo.
 */
const ACCION_CLASS =
  "flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"

export function PlantillaCard({ plantilla, editable, onEditar, onEnviar }: {
  plantilla: Plantilla
  editable: boolean
  onEditar: (p: Plantilla) => void
  onEnviar: (p: Plantilla) => void
}) {
  return (
    <Card padding="sm" className="group flex h-full flex-col gap-2">
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
        <div className="mt-auto flex justify-end gap-1 pt-1">
          <button type="button" aria-label={`Enviar ${plantilla.clave}`} onClick={() => onEnviar(plantilla)}
            className={`${ACCION_CLASS} group-hover:text-primary`}>
            <Send className="size-4" aria-hidden="true" />
          </button>
          <button type="button" aria-label={`Editar ${plantilla.clave}`} onClick={() => onEditar(plantilla)}
            className={`${ACCION_CLASS} group-hover:text-primary`}>
            <Pencil className="size-4" aria-hidden="true" />
          </button>
        </div>
      )}
    </Card>
  )
}

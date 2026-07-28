"use client"

import { useState } from "react"
import { Download } from "lucide-react"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { buttonVariants } from "@/components/ui/button"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ApiError, type FormatoExport } from "@/services/api"

const OPCIONES: { formato: FormatoExport; label: string }[] = [
  { formato: "pdf", label: "PDF" },
  { formato: "excel", label: "Excel" },
  { formato: "csv", label: "CSV" },
  { formato: "word", label: "Word" },
]

/**
 * Mensaje a mostrar cuando un export falla.
 *
 * El backend arma mensajes accionables —"la consulta devuelve N filas, el máximo es M, usá los
 * filtros"— y descartarlos por un genérico tira justo lo que el usuario necesita para
 * resolverlo. Además "Intentá de nuevo" sería el consejo equivocado en ese caso: reintentar no
 * baja el total. El genérico queda solo para lo que NO es un error de la API (red caída, etc.),
 * donde reintentar sí es lo razonable.
 *
 * Exportada para poder testear la decisión sin un DOM: el proyecto corre vitest sin jsdom.
 */
export function mensajeDeError(e: unknown): string {
  return e instanceof ApiError ? e.message : "No se pudo exportar. Intentá de nuevo."
}

/** Menú "Exportar" genérico: dispara `onExport(formato)` en los 4 formatos del motor de export. */
export function ExportMenu({ onExport }: { onExport: (formato: FormatoExport) => Promise<void> }) {
  const [exportando, setExportando] = useState(false)

  async function handle(formato: FormatoExport) {
    setExportando(true)
    try {
      await onExport(formato)
      toast.success(`Exportado en ${formato.toUpperCase()}`)
    } catch (e) {
      // duration larga: estos mensajes se leen, no se ojean. El toast envuelve el texto
      // (sonner por default, sin regla de truncado propia), así que no se corta.
      toast.error(mensajeDeError(e), { duration: 8000 })
    } finally {
      setExportando(false)
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        disabled={exportando}
        className={cn(buttonVariants({ variant: "outline" }), "min-h-11 gap-2")}
      >
        <Download className="size-4" /> Exportar
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {OPCIONES.map((o) => (
          <DropdownMenuItem key={o.formato} className="min-h-11" onClick={() => handle(o.formato)}>
            {o.label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

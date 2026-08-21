"use client"

import { Star, Trash2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import type { Adjunto } from "@/types/adjunto"

interface Props {
  adjunto: Adjunto
  url: string | null
  canWrite: boolean
  busy: boolean
  onMarcarPrincipal: () => void
  onEliminar: () => void
}

/** Tile de una imagen de vacante: thumbnail + estado principal + acciones. */
export function ImagenCard({ adjunto, url, canWrite, busy, onMarcarPrincipal, onEliminar }: Props) {
  const esPrincipal = Boolean(adjunto.es_principal)
  return (
    <div
      className={`overflow-hidden rounded-xl border bg-card ${
        esPrincipal ? "border-primary ring-2 ring-primary/40" : "border-border"
      }`}
    >
      <div className="relative aspect-video bg-muted">
        {url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={url} alt={adjunto.nombre_archivo} className="size-full object-cover" />
        ) : (
          <Skeleton className="size-full" />
        )}
        {esPrincipal && (
          /* 🔴 NO ES AZUL: un `<Badge>` sin variante es `bg-primary`, el relleno que el patrón
             reserva al chip de filtro (§3). Va con el par de éxito, que además se lee sobre
             cualquier foto — el azul del sistema no tiene contraste garantizado contra una
             imagen arbitraria. */
          <Badge variant="outline" className="absolute left-2 top-2 gap-1 bg-success-wash text-success border-success-line">
            <Star className="size-3 fill-current" /> Principal
          </Badge>
        )}
      </div>

      <div className="flex items-center justify-between gap-2 p-2">
        <p className="min-w-0 truncate text-xs text-muted-foreground" title={adjunto.nombre_archivo}>
          {adjunto.nombre_archivo}
        </p>
        {canWrite && (
          <div className="flex shrink-0 items-center gap-1">
            {!esPrincipal && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 gap-1 text-xs"
                disabled={busy}
                onClick={onMarcarPrincipal}
              >
                <Star className="size-3.5" /> Hacer principal
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="h-8 text-destructive hover:text-destructive"
              disabled={busy}
              onClick={onEliminar}
              aria-label={`Eliminar ${adjunto.nombre_archivo}`}
            >
              <Trash2 className="size-3.5" />
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

"use client"

/**
 * Grilla de proyectos: presentacional. Cubre los cuatro estados del listado (cargando /
 * error / vacío / datos) y no sabe nada de filtros ni de fetch — extraída de la página, que
 * estaba en 156 líneas contra un límite de 150.
 *
 * Se llama Grid y no Table porque eso es lo que renderiza: tarjetas, no una tabla.
 */
import { useRouter } from "next/navigation"
import { FolderKanban } from "lucide-react"

import { GrillaTarjetas } from "@/components/ui/GrillaTarjetas"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { Proyecto, ProyectoEstado } from "@/types/proyecto"

const ARS = new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS", maximumFractionDigits: 0 })
const ESTADO_VARIANT: Record<ProyectoEstado, "default" | "secondary" | "destructive" | "outline"> = {
  activo: "default", pausado: "outline", cerrado: "secondary", cancelado: "destructive",
}

function CosteoBar({ pct }: { pct: number | null }) {
  if (pct === null) return <p className="text-xs text-muted-foreground">Sin presupuesto</p>
  const over = pct > 100
  return (
    <div className="space-y-1">
      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
        <div
          className={cn("h-full rounded-full", over ? "bg-destructive" : "bg-primary")}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      <p className={cn("text-xs", over ? "font-semibold text-destructive" : "text-muted-foreground")}>
        {pct.toFixed(1)}% consumido
      </p>
    </div>
  )
}

function ProyectoCard({ proyecto, canWrite, onEdit }: { proyecto: Proyecto; canWrite: boolean; onEdit: (p: Proyecto) => void }) {
  const router = useRouter()
  const { costeo } = proyecto
  return (
    <div className="flex flex-col gap-3 rounded-xl border bg-card p-5">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-foreground">{proyecto.nombre}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">{proyecto.empresa_nombre}</p>
        </div>
        <Badge variant={ESTADO_VARIANT[proyecto.estado]} className="shrink-0 capitalize">{proyecto.estado}</Badge>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-xs">
        <span className="text-muted-foreground">Presupuesto</span>
        <span className="text-right font-medium text-foreground">{ARS.format(proyecto.presupuesto)}</span>
        <span className="text-muted-foreground">Consumido</span>
        <span className="text-right font-medium text-foreground">{ARS.format(costeo.costo_acumulado)}</span>
        <span className="text-muted-foreground">Restante</span>
        <span className={cn("text-right font-medium", costeo.presupuesto_restante < 0 ? "text-destructive" : "text-foreground")}>
          {ARS.format(costeo.presupuesto_restante)}
        </span>
      </div>
      <CosteoBar pct={costeo.pct_consumido} />
      <div className="mt-auto flex gap-2 pt-1">
        <Button variant="outline" size="sm" className="min-h-[2.75rem] flex-1 text-xs" onClick={() => router.push(`/proyectos/${proyecto.id}`)}>
          Ver detalle
        </Button>
        {canWrite && (
          <Button variant="ghost" size="sm" className="min-h-[2.75rem] text-xs" onClick={() => onEdit(proyecto)}>
            Editar
          </Button>
        )}
      </div>
    </div>
  )
}


interface ProyectosGridProps {
  proyectos: Proyecto[]
  loading: boolean
  error: string | null
  canWrite: boolean
  onEdit: (p: Proyecto) => void
  onCrear: () => void
}

export function ProyectosGrid({ proyectos, loading, error, canWrite, onEdit, onCrear }: ProyectosGridProps) {
  if (loading) {
    return (
      <GrillaTarjetas className="animate-pulse">
        {[1, 2, 3].map((i) => <div key={i} className="h-60 rounded-xl border bg-muted" />)}
      </GrillaTarjetas>
    )
  }
  if (error) {
    return (
      <div className="flex flex-col items-center gap-2 py-16">
        <FolderKanban className="size-8 text-muted-foreground" />
        <p className="text-sm text-destructive">{error}</p>
      </div>
    )
  }
  if (proyectos.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-16">
        <FolderKanban className="size-8 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">No hay proyectos registrados.</p>
        {canWrite && (
          <Button size="sm" variant="outline" className="mt-1" onClick={onCrear}>Crear el primero</Button>
        )}
      </div>
    )
  }
  return (
    <GrillaTarjetas>
      {proyectos.map((p) => (
        <ProyectoCard key={p.id} proyecto={p} canWrite={canWrite} onEdit={onEdit} />
      ))}
    </GrillaTarjetas>
  )
}

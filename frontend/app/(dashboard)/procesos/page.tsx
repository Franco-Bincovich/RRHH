"use client"

import { useEffect, useState } from "react"
import { Activity } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { cn } from "@/lib/utils"
import { fetchProcesos } from "@/services/procesos"
import type { EstadoConteo, ProcesoResumen, ProcesosData } from "@/services/procesos"

// ─── Colores por estado ───────────────────────────────────────────────────────

const ESTADO_COLOR: Record<string, string> = {
  en_progreso: "bg-blue-500",
  iniciado:    "bg-blue-500",
  en_curso:    "bg-blue-500",
  haciendo:    "bg-blue-500",
  abierto:     "bg-blue-500",
  en_revision: "bg-amber-500",
  nueva:       "bg-slate-400",
  completado:  "bg-green-500",
  finalizada:  "bg-green-500",
  terminado:   "bg-green-500",
  cerrada:     "bg-slate-400",
  pendiente:   "bg-slate-300",
  por_hacer:   "bg-slate-300",
  cancelado:   "bg-red-500",
  cancelada:   "bg-red-500",
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function EstadoRow({ ec }: { ec: EstadoConteo }) {
  return (
    <div className="flex items-center justify-between py-1">
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "size-2 shrink-0 rounded-full",
            ESTADO_COLOR[ec.estado] ?? "bg-muted",
          )}
        />
        <span className="text-sm text-muted-foreground">{ec.label}</span>
      </div>
      <span className="text-sm font-semibold tabular-nums text-foreground">
        {ec.total}
      </span>
    </div>
  )
}

function ProcesoCard({ proceso }: { proceso: ProcesoResumen }) {
  return (
    <div className="flex flex-col rounded-xl border bg-card p-5">
      <div className="mb-4 flex items-start justify-between gap-3">
        <h3 className="text-sm font-semibold text-foreground">{proceso.label}</h3>
        <span className="shrink-0 text-2xl font-bold tabular-nums text-foreground">
          {proceso.total}
        </span>
      </div>
      <div className="divide-y divide-border">
        {proceso.estados.map((ec) => (
          <EstadoRow key={ec.estado} ec={ec} />
        ))}
      </div>
    </div>
  )
}

function ProcesosSkeletonGrid() {
  return (
    <div className="grid animate-pulse grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {Array.from({ length: 7 }).map((_, i) => (
        <div key={i} className="h-44 rounded-xl border bg-muted" />
      ))}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ProcesosPage() {
  const [data, setData] = useState<ProcesosData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchProcesos()
      .then(setData)
      .catch(() => setError("No se pudo cargar el panel de procesos."))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="Panel de Procesos"
        description="Estado actual de los procesos operativos de Capital Humano"
      />

      {loading ? (
        <ProcesosSkeletonGrid />
      ) : error ? (
        <div className="flex flex-col items-center gap-2 py-16 text-center">
          <Activity className="size-8 text-muted-foreground" />
          <p className="text-sm text-destructive">{error}</p>
        </div>
      ) : !data || data.procesos.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-16 text-center">
          <Activity className="size-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Sin datos de procesos.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {data.procesos.map((p) => (
            <ProcesoCard key={p.proceso} proceso={p} />
          ))}
        </div>
      )}
    </div>
  )
}

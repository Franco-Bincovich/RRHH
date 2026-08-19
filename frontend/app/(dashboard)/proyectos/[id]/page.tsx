"use client"

import { useCallback, useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { ArrowLeft, FolderKanban } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/PageHeader"
import { Badge } from "@/components/ui/badge"
import { Tab, TabList, TabPanel, Tabs } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { EquipoTab } from "@/components/features/proyectos/EquipoTab"
import { HorasTab } from "@/components/features/proyectos/HorasTab"
import { ProyectoModal } from "@/components/features/proyectos/ProyectoModal"
import { fetchProyecto, updateProyecto } from "@/services/proyectos"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { Proyecto, ProyectoUpdate } from "@/types/proyecto"

const ARS = new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS", maximumFractionDigits: 0 })
const ESTADO_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  activo: "default", pausado: "outline", cerrado: "secondary", cancelado: "destructive",
}

type Tab = "equipo" | "horas"

function CosteoPanel({ proyecto }: { proyecto: Proyecto }) {
  const { costeo } = proyecto
  const over = (costeo.pct_consumido ?? 0) > 100
  return (
    <div className="rounded-xl border bg-card p-5">
      <h2 className="mb-4 text-sm font-semibold text-foreground">Costeo</h2>
      <div className="grid grid-cols-3 gap-4 text-center">
        {([
          ["Presupuesto", ARS.format(proyecto.presupuesto), false],
          ["Consumido", ARS.format(costeo.costo_acumulado), over],
          ["Restante", ARS.format(costeo.presupuesto_restante), costeo.presupuesto_restante < 0],
        ] as [string, string, boolean][]).map(([label, value, danger]) => (
          <div key={label}>
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className={cn("mt-1 text-lg font-bold tabular-nums", danger ? "text-destructive" : "text-foreground")}>
              {value}
            </p>
          </div>
        ))}
      </div>
      {costeo.pct_consumido !== null && (
        <div className="mt-4 space-y-1">
          <div className="h-2 overflow-hidden rounded-full bg-muted">
            <div className={cn("h-full rounded-full", over ? "bg-destructive" : "bg-primary")}
              style={{ width: `${Math.min(costeo.pct_consumido, 100)}%` }} />
          </div>
          <p className={cn("text-right text-xs", over ? "font-semibold text-destructive" : "text-muted-foreground")}>
            {costeo.pct_consumido.toFixed(1)}% del presupuesto
          </p>
        </div>
      )}
    </div>
  )
}

export default function ProyectoDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const canWrite = useCanWrite()
  const [proyecto, setProyecto] = useState<Proyecto | null>(null)
  const [loading, setLoading]   = useState(true)
  const [tab, setTab]           = useState<Tab>("equipo")
  const [editOpen, setEditOpen] = useState(false)

  const loadProyecto = useCallback(async () => {
    try { setProyecto(await fetchProyecto(id)) }
    catch { toast.error("No se pudo cargar el proyecto.") }
    finally { setLoading(false) }
  }, [id])

  useEffect(() => { loadProyecto() }, [loadProyecto])

  async function handleSaveEdit(body: ProyectoUpdate) {
    try {
      await updateProyecto(id, body)
      toast.success("Proyecto actualizado")
      setEditOpen(false)
      await loadProyecto()
    } catch { toast.error("No se pudo actualizar el proyecto.") }
  }

  if (loading) return (
    <div className="space-y-4 animate-pulse">
      <div className="h-8 w-48 rounded bg-muted" />
      <div className="h-32 rounded-xl bg-muted" />
    </div>
  )
  if (!proyecto) return (
    <div className="flex flex-col items-center gap-2 py-16">
      <FolderKanban className="size-8 text-muted-foreground" />
      <p className="text-sm text-muted-foreground">Proyecto no encontrado.</p>
      <Button variant="outline" size="sm" onClick={() => router.push("/proyectos")}>Volver</Button>
    </div>
  )

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-3">
        <Button variant="ghost" size="icon" className="mt-0.5 size-8 shrink-0" onClick={() => router.push("/proyectos")}>
          <ArrowLeft className="size-4" />
        </Button>
        <div className="flex min-w-0 flex-1 items-start justify-between gap-4">
          <PageHeader title={proyecto.nombre} description={proyecto.empresa_nombre ?? ""} />
          <div className="flex shrink-0 items-center gap-2">
            <Badge variant={ESTADO_VARIANT[proyecto.estado]} className="capitalize">{proyecto.estado}</Badge>
            {canWrite && (
              <Button size="sm" variant="outline" className="min-h-[2.75rem]" onClick={() => setEditOpen(true)}>Editar</Button>
            )}
          </div>
        </div>
      </div>

      <CosteoPanel proyecto={proyecto} />

      <Tabs value={tab} onValueChange={setTab}>
        <TabList>
          <Tab value="equipo">Equipo</Tab>
          <Tab value="horas">Horas</Tab>
        </TabList>

        <TabPanel value="equipo">
          <EquipoTab proyectoId={id} proyectoEmpresaId={proyecto.empresa_id} canWrite={canWrite} />
        </TabPanel>
        <TabPanel value="horas">
          <HorasTab proyectoId={id} onRefresh={loadProyecto} canWrite={canWrite} />
        </TabPanel>
      </Tabs>

      <ProyectoModal open={editOpen} proyecto={proyecto}
        onClose={() => setEditOpen(false)} onSave={handleSaveEdit} />
    </div>
  )
}

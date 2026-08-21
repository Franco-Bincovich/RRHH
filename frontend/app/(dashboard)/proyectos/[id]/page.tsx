"use client"

import { useCallback, useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { FolderKanban, Pencil } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Tab, TabList, TabPanel, Tabs } from "@/components/ui/tabs"
import { EquipoTab } from "@/components/features/proyectos/EquipoTab"
import { HorasTab } from "@/components/features/proyectos/HorasTab"
import { ProyectoModal } from "@/components/features/proyectos/ProyectoModal"
import { BarraProyecto } from "@/components/features/proyectos/ficha/BarraProyecto"
import { CosteoPanel } from "@/components/features/proyectos/ficha/CosteoPanel"
import { fetchProyecto, updateProyecto } from "@/services/proyectos"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { Proyecto, ProyectoUpdate } from "@/types/proyecto"

type Tab = "equipo" | "horas"

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

  // El esqueleto tiene la GRILLA EXACTA que va a tener con datos (§3): la barra de identidad y el
  // panel de costeo. El `animate-pulse` de antes era el del componente (2s); el shimmer del
  // sistema de diseño es el de `Skeleton shimmer` y va a 1,2s.
  if (loading) return (
    <div className="space-y-6">
      <Skeleton shimmer className="h-[118px] w-full rounded-xl" />
      <Skeleton shimmer className="h-32 w-full rounded-xl" />
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
      {/* La ÚNICA acción de esta ficha es editar, así que es la primaria y va última por
          construcción (§3). Si alguna vez se suma otra —cerrar el proyecto, por ejemplo—, va
          ANTES de esta y en `variant="outline"`; el test de la barra cuenta los botones justo
          para que ese día alguien tenga que decidirlo. */}
      <BarraProyecto
        proyecto={proyecto}
        acciones={canWrite ? (
          <Button className="min-h-11 gap-2" onClick={() => setEditOpen(true)}>
            <Pencil className="size-4" />
            Editar
          </Button>
        ) : undefined}
      />

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

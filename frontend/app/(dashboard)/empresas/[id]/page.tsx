"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { ArrowLeft, Pencil } from "lucide-react"

import { Tab, TabList, TabPanel, Tabs } from "@/components/ui/tabs"
import { ErrorState, esNoEncontrado } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { EmpresaModal } from "@/components/features/empresas/EmpresaModal"
import { EmpresaAreasTab } from "@/components/features/empresas/EmpresaAreasTab"
import { BarraEmpresa } from "@/components/features/empresas/ficha/BarraEmpresa"
import { LogoPanel } from "@/components/features/empresas/ficha/LogoPanel"
import { fetchEmpresa } from "@/services/empresas"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { Empresa } from "@/types/empresa"

type Tab = "info" | "areas" | "proyectos"

const TAB_LABELS: Record<Tab, string> = {
  info: "Información",
  areas: "Áreas",
  proyectos: "Proyectos",
}

export default function EmpresaDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const canWrite = useCanWrite()

  const [empresa, setEmpresa] = useState<Empresa | null>(null)
  const [loading, setLoading] = useState(true)
  // El error se guarda ENTERO, no como booleano: `ErrorState` distingue el 404 (que es
  // tambien la respuesta de un recurso de otra empresa) mirando el ApiError.
  const [error, setError] = useState<unknown>(null)
  const [activeTab, setActiveTab] = useState<Tab>("info")
  const [editModalOpen, setEditModalOpen] = useState(false)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setEmpresa(await fetchEmpresa(id))
    } catch (e) {
      setError(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [id])

  // El esqueleto tiene la forma que la pantalla va a tener con datos (§3): la barra de identidad,
  // las solapas y el panel. Antes eran cinco rectángulos de 8px que no se parecían a nada.
  if (loading) {
    return (
      <div>
        <Skeleton shimmer className="mb-4 h-[118px] w-full rounded-xl" />
        <Skeleton shimmer className="mb-6 h-10 w-64 rounded-lg" />
        <Skeleton shimmer className="h-48 w-full max-w-md rounded-xl" />
      </div>
    )
  }

  if (error || !empresa) {
    return (
      <div>
        <Button variant="ghost" className="mb-4 -ml-2" onClick={() => router.back()}>
          <ArrowLeft className="mr-1 size-4" /> Volver
        </Button>
        <ErrorState
          error={error}
          description={esNoEncontrado(error) ? undefined : "No se pudo cargar la empresa."}
          action={load}
          onVolver={() => router.push("/empresas")}
        />
      </div>
    )
  }

  return (
    <div>
      {/* La ÚNICA acción de la ficha es editar, así que es la primaria y va última por
          construcción (§3). Subir el logo NO subió acá a propósito: es la acción de un panel
          —cambia una sola cosa de ese panel— y en la barra se leería con el mismo peso que
          "Editar", que abre el formulario entero. */}
      <BarraEmpresa
        empresa={empresa}
        acciones={canWrite ? (
          <Button className="min-h-11 gap-2" onClick={() => setEditModalOpen(true)}>
            <Pencil className="size-4" />
            Editar
          </Button>
        ) : undefined}
      />

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabList className="mb-6">
          <Tab value="info">{TAB_LABELS.info}</Tab>
          <Tab value="areas">{TAB_LABELS.areas}</Tab>
          {/* Deshabilitada, no oculta: la solapa comunica que la sección existe y todavía no.
              `disabled` la saca además de la navegación con flechas, que es lo que un `<button>`
              con `cursor-not-allowed` pintado a mano no hacía. */}
          <Tab value="proyectos" disabled>
            {TAB_LABELS.proyectos}
            <span className="ml-1.5 text-xs">(Próximamente)</span>
          </Tab>
        </TabList>

        <TabPanel value="info">
          <div className="max-w-md">
            <LogoPanel empresa={empresa} canWrite={canWrite} onCambiado={setEmpresa} />
          </div>
        </TabPanel>

        <TabPanel value="areas"><EmpresaAreasTab empresaId={empresa.id} canWrite={canWrite} /></TabPanel>
      </Tabs>

      <EmpresaModal
        open={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        onSuccess={(updated) => {
          setEmpresa(updated)
          setEditModalOpen(false)
        }}
        empresa={empresa}
      />
    </div>
  )
}

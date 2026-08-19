"use client"

import { useState, useEffect, useRef } from "react"
import { useParams, useRouter } from "next/navigation"
import { ArrowLeft, Building2, Pencil, Upload } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { Tab, TabList, TabPanel, Tabs } from "@/components/ui/tabs"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { EmpresaModal } from "@/components/features/empresas/EmpresaModal"
import { EmpresaAreasTab } from "@/components/features/empresas/EmpresaAreasTab"
import { fetchEmpresa, uploadLogo } from "@/services/empresas"
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
  const [error, setError] = useState(false)
  const [activeTab, setActiveTab] = useState<Tab>("info")
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [uploadingLogo, setUploadingLogo] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  async function load() {
    setLoading(true)
    setError(false)
    try {
      const data = await fetchEmpresa(id)
      setEmpresa(data)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [id])

  async function handleLogoChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !empresa) return
    setUploadingLogo(true)
    try {
      const updated = await uploadLogo(empresa.id, file)
      setEmpresa(updated)
    } catch {
      // error silencioso — usuario puede reintentar
    } finally {
      setUploadingLogo(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  if (loading) {
    return (
      <div>
        <Skeleton className="mb-6 h-8 w-48" />
        <Skeleton className="mb-4 h-10 w-64" />
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full rounded" />
          ))}
        </div>
      </div>
    )
  }

  if (error || !empresa) {
    return (
      <div>
        <Button variant="ghost" className="mb-4 -ml-2" onClick={() => router.back()}>
          <ArrowLeft className="mr-1 size-4" /> Volver
        </Button>
        <ErrorState description="No se pudo cargar la empresa." action={load} />
      </div>
    )
  }

  return (
    <div>
      {/* Breadcrumb */}
      <button
        onClick={() => router.push("/empresas")}
        className="mb-4 flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="size-4" />
        Empresas
      </button>

      <PageHeader
        title={empresa.nombre}
        description={empresa.razon_social ?? undefined}
        action={
          <div className="flex items-center gap-2">
            <Badge variant={empresa.activa ? "default" : "secondary"}>
              {empresa.activa ? "Activa" : "Inactiva"}
            </Badge>
            {canWrite && (
              <Button className="min-h-11" onClick={() => setEditModalOpen(true)}>
                <Pencil className="mr-1 size-4" />
                Editar
              </Button>
            )}
          </div>
        }
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

      {/* Tab: Información */}
      <TabPanel value="info">
        <div className="max-w-2xl space-y-6">
          {/* Logo */}
          <div className="flex items-center gap-4">
            <div className="flex size-20 items-center justify-center rounded-xl border bg-muted overflow-hidden shrink-0">
              {empresa.logo_url ? (
                <img
                  src={empresa.logo_url}
                  alt={`Logo de ${empresa.nombre}`}
                  className="size-full object-contain"
                />
              ) : (
                <Building2 className="size-8 text-muted-foreground" />
              )}
            </div>
            <div>
              <p className="text-sm font-medium mb-1">Logo</p>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleLogoChange}
              />
              {canWrite && (
                <Button
                  variant="outline"
                  size="sm"
                  className="min-h-9"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadingLogo}
                >
                  <Upload className="mr-1.5 size-3.5" />
                  {uploadingLogo ? "Subiendo..." : empresa.logo_url ? "Cambiar logo" : "Subir logo"}
                </Button>
              )}
            </div>
          </div>

          <Separator />

          {/* Datos */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="CUIT" value={empresa.cuit} />
            <Field label="Razón social" value={empresa.razon_social} />
            <Field label="Email" value={empresa.email} />
            <Field label="Teléfono" value={empresa.telefono} />
          </div>
          {empresa.direccion && (
            <Field label="Dirección" value={empresa.direccion} />
          )}
        </div>
      </TabPanel>

      {/* Tab: Áreas */}
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

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground mb-0.5">{label}</p>
      <p className="text-sm font-medium">
        {value ?? <span className="italic text-muted-foreground/60">—</span>}
      </p>
    </div>
  )
}

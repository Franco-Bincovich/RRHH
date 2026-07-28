"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Plus } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/PageHeader"
import { ConfirmDialog } from "@/components/ui/ConfirmDialog"
import { NuevoTemplateModal } from "@/components/features/onboarding/NuevoTemplateModal"
import { TemplatesList } from "@/components/features/onboarding/TemplatesList"
import { deleteTemplate, fetchTemplates } from "@/services/onboarding"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { OnboardingTemplate } from "@/types/onboarding"
import type { Empresa } from "@/types/empresa"

export default function TemplatesPage() {
  const router = useRouter()
  const canWrite = useCanWrite()
  const [empresaActivaId] = useState<string | null>(() => getEmpresaActivaId())
  const [templates, setTemplates] = useState<OnboardingTemplate[]>([])
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [aEliminar, setAEliminar] = useState<OnboardingTemplate | null>(null)

  useEffect(() => {
    const tasks: Promise<unknown>[] = [
      fetchTemplates().then(setTemplates),
    ]
    if (!empresaActivaId) {
      tasks.push(
        fetchEmpresas().then((res) => setEmpresas(res.items.filter((e) => e.activa))).catch(() => {}),
      )
    }
    Promise.all(tasks)
      .catch(() => setError("No se pudieron cargar los templates"))
      .finally(() => setLoading(false))
  }, [empresaActivaId])

  async function confirmarEliminar() {
    if (!aEliminar) return
    setDeletingId(aEliminar.id)
    try {
      await deleteTemplate(aEliminar.id)
      setTemplates((prev) => prev.filter((t) => t.id !== aEliminar.id))
      toast.success("Template eliminado")
      setAEliminar(null)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "No se pudo eliminar el template.")
    } finally {
      setDeletingId(null)
    }
  }

  // Mismo encabezado en los tres estados: durante la carga y ante un error no se puede
  // contar nada, y el alta queda fuera hasta que haya datos con los que convivir.
  const listo = !loading && !error
  const descripcion = loading
    ? "Cargando..."
    : error
      ? undefined
      : `${templates.length} template${templates.length !== 1 ? "s" : ""} configurado${templates.length !== 1 ? "s" : ""}`

  return (
    <div>
      <div className="relative">
        <PageHeader title="Templates de onboarding" description={descripcion} />
        {canWrite && listo && (
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="absolute right-0 top-0 flex min-h-10 items-center gap-1.5 rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Plus className="size-4" />
            <span className="hidden sm:inline">Nuevo template</span>
          </button>
        )}
      </div>

      <TemplatesList
        templates={templates}
        loading={loading}
        error={error}
        canWrite={canWrite}
        mostrarEmpresa={!empresaActivaId}
        deletingId={deletingId}
        onAbrir={(id) => router.push(`/onboarding/templates/${id}`)}
        onEliminar={setAEliminar}
      />

      <ConfirmDialog
        open={aEliminar !== null}
        onClose={() => setAEliminar(null)}
        onConfirm={confirmarEliminar}
        title="Eliminar template"
        description={`Se eliminará el template "${aEliminar?.nombre ?? ""}" y sus tareas. Si ya tiene onboardings iniciados no se borra: queda desactivado, para no romper el historial de esos procesos.`}
        confirmLabel="Eliminar"
        loading={deletingId !== null}
      />

      {modalOpen && (
        <NuevoTemplateModal
          empresas={empresas}
          empresaActivaId={empresaActivaId}
          onClose={() => setModalOpen(false)}
          onSuccess={(t) => {
            setTemplates((prev) => [t, ...prev])
            setModalOpen(false)
            router.push(`/onboarding/templates/${t.id}`)
          }}
        />
      )}
    </div>
  )
}

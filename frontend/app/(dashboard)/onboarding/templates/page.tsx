"use client"

import { useCallback, useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Plus } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { ConfirmDialog } from "@/components/ui/ConfirmDialog"
import { NuevoTemplateModal } from "@/components/features/onboarding/NuevoTemplateModal"
import { TemplatesList } from "@/components/features/onboarding/TemplatesList"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { deleteTemplate, exportarTemplates, fetchTemplates } from "@/services/onboarding"
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

  const cargar = useCallback(() => {
    setLoading(true); setError(null)
    const tasks: Promise<unknown>[] = [
      fetchTemplates().then(setTemplates),
    ]
    if (!empresaActivaId) {
      tasks.push(
        fetchEmpresas().then((res) => setEmpresas(res.items.filter((e) => e.activa))).catch(() => {}),
      )
    }
    void Promise.all(tasks)
      .catch(() => setError("No se pudieron cargar los templates"))
      .finally(() => setLoading(false))
  }, [empresaActivaId])

  useEffect(() => { cargar() }, [cargar])

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

  const nuevoBtn = (
    <Button className="min-h-11 gap-1.5" onClick={() => setModalOpen(true)}>
      <Plus className="size-4" />
      <span className="hidden sm:inline">Nuevo template</span>
    </Button>
  )

  return (
    <div>
      <div className="relative">
        <PageHeader title="Templates de onboarding" description={descripcion} />
        <div className="absolute right-0 top-0 flex items-center gap-2">
          {/* El archivo trae las MISMAS plantillas que la lista: mismo endpoint de origen y
              mismo recorte por visibilidad, que el backend resuelve con el token. */}
          {listo && templates.length > 0 && <ExportMenu onExport={exportarTemplates} />}
          {/* ⚠️ ERA UN `<button>` A MANO con `bg-primary`, su propio `hover:` y su propio
              `focus-visible:` — o sea, una copia del botón primario que el repo ya tiene, con la
              mitad de los estados y con 40px de alto en vez de los 44 que el repo usa para todo
              control táctil. Ahora sale del primitivo. */}
          {canWrite && listo && nuevoBtn}
        </div>
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
        onReintentar={cargar}
        accionVacio={canWrite ? nuevoBtn : undefined}
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

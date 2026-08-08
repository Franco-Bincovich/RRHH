"use client"

import { useState, useEffect } from "react"
import { Building2, Plus } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/PageHeader"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { EmpresaModal } from "@/components/features/empresas/EmpresaModal"
import { EmpresasTable } from "@/components/features/empresas/EmpresasTable"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { exportarEmpresas, fetchEmpresas, toggleEmpresaActiva } from "@/services/empresas"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { Empresa } from "@/types/empresa"

export default function EmpresasPage() {
  const canWrite = useCanWrite()
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Empresa | undefined>(undefined)
  const [togglingId, setTogglingId] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(false)
    try {
      const data = await fetchEmpresas()
      setEmpresas(data.items)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  function openCreate() {
    setEditing(undefined)
    setModalOpen(true)
  }

  function openEdit(empresa: Empresa) {
    setEditing(empresa)
    setModalOpen(true)
  }

  async function handleToggle(empresa: Empresa) {
    setTogglingId(empresa.id)
    try {
      await toggleEmpresaActiva(empresa.id, !empresa.activa)
      void load()
    } catch {
      toast.error("No se pudo cambiar el estado de la empresa. Intentá de nuevo.")
    } finally {
      setTogglingId(null)
    }
  }

  if (loading) {
    return (
      <div>
        <PageHeader title="Empresas" description="Cargando..." />
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <PageHeader title="Empresas" />
        <ErrorState description="No se pudieron cargar las empresas." action={load} />
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title="Empresas"
        description={`${empresas.length} empresa${empresas.length !== 1 ? "s" : ""}`}
        action={
          <div className="flex items-center gap-2">
            {/* El archivo sale del MISMO listado que la tabla y esta pantalla no tiene
                filtros: trae exactamente las empresas que se ven, activas e inactivas.
                Disponible también para gerencia_lectura — exportar es una lectura. */}
            {empresas.length > 0 && <ExportMenu onExport={exportarEmpresas} />}
            {canWrite && (
              <Button className="min-h-11" onClick={openCreate}>
                <Plus />
                Nueva empresa
              </Button>
            )}
          </div>
        }
      />

      {empresas.length === 0 ? (
        <EmptyState
          icon={<Building2 />}
          title="Sin empresas"
          description="Todavía no hay empresas registradas. Creá la primera."
          action={
            canWrite ? (
              <Button className="min-h-11" onClick={openCreate}>
                <Plus />
                Nueva empresa
              </Button>
            ) : undefined
          }
        />
      ) : (
        <EmpresasTable
          empresas={empresas}
          canWrite={canWrite}
          onEdit={openEdit}
          onToggle={handleToggle}
          togglingId={togglingId}
        />
      )}

      <EmpresaModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={() => { setModalOpen(false); void load() }}
        empresa={editing}
      />
    </div>
  )
}

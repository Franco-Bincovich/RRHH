"use client"

import { useState, useCallback, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Briefcase, Plus } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { VacanteModal } from "@/components/features/vacantes/VacanteModal"
import { VacantesTable } from "@/components/features/vacantes/VacantesTable"
import { RevisarCasillaButton } from "@/components/features/vacantes/RevisarCasillaButton"
import { MailsPendientes } from "@/components/features/vacantes/MailsPendientes"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { exportarVacantes, fetchVacantes } from "@/services/vacantes"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { EstadoVacante, Vacante } from "@/types/vacantes"
import type { Empresa } from "@/types/empresa"

const SELECT_CLASS =
  "min-h-[2rem] rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"

function TableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full rounded-lg" />
      ))}
    </div>
  )
}

function formatFecha(raw: string | null): string {
  if (!raw) return "—"
  const d = new Date(raw)
  return d.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" })
}

export default function VacantesPage() {
  const router = useRouter()
  const canWrite = useCanWrite()

  // empresa activa del topbar — estable durante la sesión (recarga al cambiar)
  const [empresaActivaId, setEmpresaActivaIdLocal] = useState<string | null>(null)

  const [vacantes, setVacantes] = useState<Vacante[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [estadoFilter, setEstadoFilter] = useState<EstadoVacante | "">("")
  const [modalOpen, setModalOpen] = useState(false)

  // filtro de empresa en columna (solo activo cuando topbar = "Todas")
  const [empresaFiltro, setEmpresaFiltro] = useState("")
  const [empresas, setEmpresas] = useState<Empresa[]>([])

  useEffect(() => {
    const id = getEmpresaActivaId()
    setEmpresaActivaIdLocal(id)
    if (!id) {
      fetchEmpresas()
        .then((res) => setEmpresas(res.items.filter((e) => e.activa)))
        .catch(() => {})
    }
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      // si topbar = "Todas" y hay filtro de columna activo, pasar override
      const empresaOverride = !empresaActivaId && empresaFiltro ? empresaFiltro : undefined
      const data = await fetchVacantes(estadoFilter || undefined, empresaOverride)
      setVacantes(data)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [estadoFilter, empresaActivaId, empresaFiltro])

  useEffect(() => {
    load()
  }, [load])

  const mostrarFiltroEmpresa = !empresaActivaId && empresas.length > 0

  return (
    <div>
      <PageHeader
        title="Vacantes"
        description={loading ? "Cargando..." : `${vacantes.length} vacante${vacantes.length !== 1 ? "s" : ""}`}
        action={
          <div className="flex items-center gap-2">
            {/* Exporta con el MISMO estado que filtra la pantalla. La empresa viaja por el
                header, igual que en el listado. Sin filas no se ofrece exportar. */}
            {!loading && !error && vacantes.length > 0 && (
              <ExportMenu onExport={(f) => exportarVacantes(f, estadoFilter || undefined, empresaFiltro || undefined)} />
            )}
            {/* Revisa la CASILLA entera, no esta pantalla: cada mail elige su vacante por el
                código del asunto. Por eso vive en el listado y no en la ficha de una vacante. */}
            {canWrite && <RevisarCasillaButton />}
            {canWrite && (
              <Button className="min-h-11" onClick={() => setModalOpen(true)}>
                <Plus />
                Nueva vacante
              </Button>
            )}
          </div>
        }
      />

      <div className="mb-4 flex flex-col gap-3 sm:flex-row">
        {mostrarFiltroEmpresa && (
          <select
            aria-label="Filtrar por empresa"
            className={SELECT_CLASS}
            value={empresaFiltro}
            onChange={(e) => { setEmpresaFiltro(e.target.value) }}
          >
            <option value="">Todas las empresas</option>
            {empresas.map((e) => (
              <option key={e.id} value={e.id}>{e.nombre}</option>
            ))}
          </select>
        )}
        <select
          aria-label="Filtrar por estado"
          className={SELECT_CLASS}
          value={estadoFilter}
          onChange={(e) => setEstadoFilter(e.target.value as EstadoVacante | "")}
        >
          <option value="">Todos los estados</option>
          <option value="nueva">Nueva</option>
          <option value="en_proceso">En proceso</option>
          <option value="con_candidatos">Con candidatos</option>
          <option value="cerrada">Cerrada</option>
        </select>
      </div>

      {loading && <TableSkeleton />}

      {!loading && error && <ErrorState action={load} />}

      {!loading && !error && vacantes.length === 0 && (
        <EmptyState
          icon={<Briefcase />}
          title="Sin resultados"
          description="No hay vacantes que coincidan con el filtro seleccionado."
        />
      )}

      {!loading && !error && vacantes.length > 0 && (
        <VacantesTable
          vacantes={vacantes}
          mostrarEmpresa={!empresaActivaId}
          onAbrir={(id) => router.push(`/vacantes/${id}`)}
        />
      )}

      {/* Los mails que no matchearon: se releen de la casilla, no hay estado propio. */}
      {canWrite && <MailsPendientes />}

      <VacanteModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={() => {
          setModalOpen(false)
          load()
        }}
      />
    </div>
  )
}

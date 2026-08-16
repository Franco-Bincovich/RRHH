"use client"

import { useState, useCallback, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Briefcase } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { Pagination } from "@/components/ui/Pagination"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { VacanteModal } from "@/components/features/vacantes/VacanteModal"
import { VacantesTable } from "@/components/features/vacantes/VacantesTable"
import { VacantesFiltros, VacantesTableSkeleton } from "@/components/features/vacantes/VacantesFiltros"
import { MailsPendientes } from "@/components/features/vacantes/MailsPendientes"
import { VacantesAcciones } from "@/components/features/vacantes/VacantesAcciones"
import { fetchVacantes } from "@/services/vacantes"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { EstadoVacante, Vacante } from "@/types/vacantes"
import type { Empresa } from "@/types/empresa"

const PAGE_SIZE = 20

export default function VacantesPage() {
  const router = useRouter()
  const canWrite = useCanWrite()

  // empresa activa del topbar — estable durante la sesión (recarga al cambiar)
  const [empresaActivaId, setEmpresaActivaIdLocal] = useState<string | null>(null)

  const [vacantes, setVacantes] = useState<Vacante[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [estadoFilter, setEstadoFilterRaw] = useState<EstadoVacante | "">("")
  const [modalOpen, setModalOpen] = useState(false)

  // filtro de empresa en columna (solo activo cuando topbar = "Todas")
  const [empresaFiltro, setEmpresaFiltroRaw] = useState("")
  // 🔴 Cambiar un filtro vuelve a la página 1 (invariante 4 del bloque B): filtrar parado en
  // la 7 pediría una página que el resultado nuevo no tiene y la grilla saldría vacía.
  const setEstadoFilter = (v: EstadoVacante | "") => { setPage(1); setEstadoFilterRaw(v) }
  const setEmpresaFiltro = (v: string) => { setPage(1); setEmpresaFiltroRaw(v) }
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
      const data = await fetchVacantes(estadoFilter || undefined, empresaOverride, page, PAGE_SIZE)
      setVacantes(data.items)
      setTotal(data.total)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [estadoFilter, empresaActivaId, empresaFiltro, page])

  useEffect(() => {
    load()
  }, [load])

  const mostrarFiltroEmpresa = !empresaActivaId && empresas.length > 0

  return (
    <div>
      <PageHeader
        title="Vacantes"
        // `total` y no `vacantes.length`: en la página 2 el largo de la página no dice cuántas hay.
        description={loading ? "Cargando..." : `${total} vacante${total !== 1 ? "s" : ""}`}
        action={
          <VacantesAcciones
            // `total > 0` y no `vacantes.length > 0`: en la página 2 el largo de la página no
            // dice si hay algo que exportar — lo dice el total del filtro.
            hayFilas={!loading && !error && total > 0}
            canWrite={canWrite} estadoFiltro={estadoFilter} empresaFiltro={empresaFiltro}
            onNueva={() => setModalOpen(true)}
          />
        }
      />

      <VacantesFiltros
        mostrarEmpresa={mostrarFiltroEmpresa} empresas={empresas}
        empresaFiltro={empresaFiltro} onEmpresa={setEmpresaFiltro}
        estadoFiltro={estadoFilter} onEstado={setEstadoFilter}
      />

      {loading && <VacantesTableSkeleton />}

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

      {total > PAGE_SIZE && (
        <Pagination page={page} total={total} pageSize={PAGE_SIZE} onPageChange={setPage} />
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

"use client"

import { useCallback, useEffect, useState } from "react"
import { ScrollText } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { AuditTable } from "@/components/features/auditoria/AuditTable"
import { AuditFilters } from "@/components/features/auditoria/AuditFilters"
import { AuditDetailModal } from "@/components/features/auditoria/AuditDetailModal"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Pagination } from "@/components/ui/Pagination"
import { Skeleton } from "@/components/ui/skeleton"
import { exportarAuditoria, fetchAuditoria, type AuditoriaFiltros } from "@/services/auditoria"
import { fetchUsuarios, type UsuarioOption } from "@/services/usuarios"
import type { AuditLog } from "@/types/auditoria"

const PAGE_SIZE = 20

function TableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full rounded-lg" />
      ))}
    </div>
  )
}

export default function AuditoriaPage() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [filtros, setFiltros] = useState<AuditoriaFiltros>({})
  const [usuarios, setUsuarios] = useState<UsuarioOption[]>([])
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    fetchUsuarios().then((r) => setUsuarios(r.items)).catch(() => {})
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const data = await fetchAuditoria({ ...filtros, page, page_size: PAGE_SIZE })
      setLogs(data.items)
      setTotal(data.total)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [page, filtros])

  useEffect(() => { load() }, [load])

  function handleFiltrosChange(next: AuditoriaFiltros) {
    setFiltros(next)
    setPage(1)
  }

  return (
    <div>
      <PageHeader
        title="Auditoría"
        description="Registro de cambios realizados en el sistema"
        action={
          !loading && !error && logs.length > 0 ? (
            <ExportMenu onExport={(f) => exportarAuditoria(f, filtros)} />
          ) : undefined
        }
      />

      <AuditFilters filtros={filtros} onChange={handleFiltrosChange} usuarios={usuarios} />

      {loading && <TableSkeleton />}
      {!loading && error && <ErrorState action={load} />}

      {!loading && !error && logs.length === 0 && (
        <EmptyState
          icon={<ScrollText />}
          title="No hay registros de auditoría todavía"
          description="Los cambios realizados en el sistema aparecerán acá a medida que ocurran."
        />
      )}

      {!loading && !error && logs.length > 0 && (
        <>
          <AuditTable logs={logs} onVerDetalle={setSelectedLog} />
          <Pagination page={page} total={total} pageSize={PAGE_SIZE} onPageChange={setPage} />
        </>
      )}

      <AuditDetailModal log={selectedLog} onClose={() => setSelectedLog(null)} />
    </div>
  )
}

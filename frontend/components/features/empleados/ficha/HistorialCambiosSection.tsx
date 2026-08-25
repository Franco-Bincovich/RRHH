"use client"

import { useEffect, useState } from "react"

import { Skeleton } from "@/components/ui/skeleton"
import { Pagination } from "@/components/ui/Pagination"
import { Section } from "@/components/features/empleados/ficha/_primitives"
import { AuditTable } from "@/components/features/auditoria/AuditTable"
import { AuditDetailModal } from "@/components/features/auditoria/AuditDetailModal"
import { fetchAuditoria } from "@/services/auditoria"
import type { AuditLog } from "@/types/auditoria"

const PAGE_SIZE_INICIAL = 10

/**
 * Sección autoabastecida: historial de cambios de un empleado en su ficha.
 * Fetchea el audit log filtrado por entidad="empleado" + registro_id={empleadoId}
 * (los cambios de ESE empleado). Maneja loading/error/vacío y paginado. Solo lectura.
 */
export function HistorialCambiosSection({ empleadoId }: { empleadoId: string }) {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(PAGE_SIZE_INICIAL)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [detalle, setDetalle] = useState<AuditLog | null>(null)

  useEffect(() => {
    if (!empleadoId) return
    let cancelled = false
    setLoading(true)
    setError(false)
    fetchAuditoria({ entidad: "empleado", registro_id: empleadoId, page, page_size: pageSize })
      .then((res) => { if (!cancelled) { setLogs(res.items); setTotal(res.total) } })
      .catch(() => { if (!cancelled) setError(true) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [empleadoId, page, pageSize])

  return (
    <Section title="Historial de cambios">
      <div className="col-span-full">
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : error ? (
          <p className="text-sm text-muted-foreground">
            No se pudo cargar el historial de cambios.
          </p>
        ) : logs.length === 0 ? (
          <p className="text-sm text-muted-foreground">Sin cambios registrados.</p>
        ) : (
          <>
            <AuditTable logs={logs} onVerDetalle={setDetalle} />
            {total > pageSize && (
              <Pagination page={page} total={total} pageSize={pageSize} onPageSizeChange={setPageSize} onPageChange={setPage} />
            )}
          </>
        )}
      </div>

      <AuditDetailModal log={detalle} onClose={() => setDetalle(null)} />
    </Section>
  )
}

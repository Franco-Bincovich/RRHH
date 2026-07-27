"use client"

import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import { Plus, Upload } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { Pagination } from "@/components/ui/Pagination"
import { EmpleadosTable } from "@/components/features/empleados/EmpleadosTable"
import { useFiltrosEmpleados } from "@/components/features/empleados/useFiltrosEmpleados"
import { EmpleadoModal } from "@/components/features/empleados/EmpleadoModal"
import { ImportarNominaModal } from "@/components/features/empleados/ImportarNominaModal"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { fetchEmpleados, exportarEmpleados } from "@/services/empleados"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { Empleado, EmpleadoListResponse } from "@/types/empleado"

const PAGE_SIZE = 20

export default function EmpleadosPage() {
  const router = useRouter()
  const canWrite = useCanWrite()

  const [data, setData] = useState<EmpleadoListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [page, setPage] = useState(1)
  const [newOpen, setNewOpen] = useState(false)
  const [importOpen, setImportOpen] = useState(false)

  const { empresaActivaId, empresaOverride, areaFiltro, estadoFiltro, debouncedSearch, campos } =
    useFiltrosEmpleados(() => setPage(1))

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const result = await fetchEmpleados({
        page,
        pageSize: PAGE_SIZE,
        search: debouncedSearch || undefined,
        estado: estadoFiltro || undefined,
        empresaId: empresaOverride,
        areaId: areaFiltro || undefined,
      })
      setData(result)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [page, debouncedSearch, estadoFiltro, areaFiltro, empresaOverride])

  useEffect(() => { load() }, [load])

  const items: Empleado[] = data?.items ?? []
  const total = data?.total ?? 0

  return (
    <div>
      <PageHeader
        title="Empleados"
        description={loading ? "Cargando..." : `${total} colaboradores`}
        action={
          <div className="flex items-center gap-2">
            {!loading && !error && items.length > 0 && (
              <ExportMenu onExport={(f) => exportarEmpleados({
                formato: f,
                search: debouncedSearch || undefined,
                estado: estadoFiltro || undefined,
                empresaId: empresaOverride,
                areaId: areaFiltro || undefined,
              })} />
            )}
            {canWrite && (
              <>
                <Button variant="outline" className="min-h-11 gap-1.5" onClick={() => setImportOpen(true)}>
                  <Upload className="size-4" />
                  Importar nómina
                </Button>
                <Button className="min-h-11" onClick={() => setNewOpen(true)}>
                  <Plus />
                  Nuevo empleado
                </Button>
              </>
            )}
          </div>
        }
      />

      <FiltersBar campos={campos} />

      <EmpleadosTable
        items={items}
        loading={loading}
        error={error}
        showEmpresa={!empresaActivaId}
        onRetry={load}
        onRowClick={(id) => router.push(`/empleados/${id}`)}
      />

      {!loading && !error && total > PAGE_SIZE && (
        <Pagination page={page} total={total} pageSize={PAGE_SIZE} onPageChange={setPage} />
      )}

      <EmpleadoModal
        open={newOpen}
        onClose={() => setNewOpen(false)}
        onSuccess={() => { setNewOpen(false); load() }}
      />

      <ImportarNominaModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onSuccess={() => { setImportOpen(false); load() }}
      />
    </div>
  )
}

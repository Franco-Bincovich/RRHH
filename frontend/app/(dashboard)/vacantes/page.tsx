"use client"

import { useState, useCallback, useEffect } from "react"
import { useRouter } from "next/navigation"

import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import { Pagination } from "@/components/ui/Pagination"
import { VacanteModal } from "@/components/features/vacantes/VacanteModal"
import { VacantesTable } from "@/components/features/vacantes/VacantesTable"
import { useFiltrosVacantes } from "@/components/features/vacantes/useFiltrosVacantes"
import { MailsPendientes } from "@/components/features/vacantes/MailsPendientes"
import { VacantesAcciones } from "@/components/features/vacantes/VacantesAcciones"
import { fetchVacantes } from "@/services/vacantes"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { EstadoVacante, Vacante } from "@/types/vacantes"

const PAGE_SIZE_INICIAL = 20

export default function VacantesPage() {
  const router = useRouter()
  const canWrite = useCanWrite()

  const [vacantes, setVacantes] = useState<Vacante[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(PAGE_SIZE_INICIAL)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)

  // 🔴 Cambiar un filtro vuelve a la página 1 (invariante 4 del bloque B): filtrar parado en la 7
  // pediría una página que el resultado nuevo no tiene y la grilla saldría vacía.
  const { empresaActivaId, empresaOverride, estadoFiltro, campos } =
    useFiltrosVacantes(() => setPage(1))

  const chips = chipsDeCampos(campos)

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const data = await fetchVacantes(estadoFiltro || undefined, empresaOverride, page, pageSize)
      setVacantes(data.items)
      // El total sale del wrapper del backend, NUNCA de `data.items.length`.
      setTotal(data.total)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [estadoFiltro, empresaOverride, page, pageSize])

  useEffect(() => {
    load()
  }, [load])

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
            canWrite={canWrite}
            estadoFiltro={(estadoFiltro || "") as EstadoVacante | ""}
            empresaFiltro={empresaOverride ?? ""}
            onNueva={() => setModalOpen(true)}
          />
        }
      />

      {/* `panel`: la forma completa del patrón de filtros (caja propia y los chips de la fila
          inferior). Reemplaza a `VacantesFiltros`, que eran dos `<Select>` sueltos sin chips.
          Sin "Más filtros": con dos filtros —y uno solo fuera del modo consolidado— esconder uno
          atrás de un botón no compra nada. Ver `_camposVacantes.ts`. */}
      <FiltersBar campos={campos} panel disabled={loading} />

      <VacantesTable
        vacantes={vacantes}
        loading={loading}
        error={error}
        mostrarEmpresa={!empresaActivaId}
        onRetry={load}
        onAbrir={(id) => router.push(`/vacantes/${id}`)}
        chips={chips}
        onLimpiarTodo={() => chips.forEach((c) => c.quitar())}
        accionVacio={canWrite ? (
          <Button className="min-h-11" onClick={() => setModalOpen(true)}>Crear la primera</Button>
        ) : undefined}
      />

      {/*
       * 🔴 EL PIE VA SIEMPRE QUE HAYA FILAS, no sólo cuando hay más de una página. Antes aparecía
       * con `total > pageSize` y además SIN esperar a que terminara la carga, así que la barra
       * se dibujaba sobre el esqueleto con el total del pedido anterior. El total que muestra es
       * el TOTAL FILTRADO del backend, no `vacantes.length`.
       */}
      {!loading && !error && vacantes.length > 0 && (
        <Pagination page={page} total={total} pageSize={pageSize} onPageSizeChange={setPageSize} onPageChange={setPage} />
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

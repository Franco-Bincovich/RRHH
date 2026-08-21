"use client"

import { useMemo, useState } from "react"
import { useRouter } from "next/navigation"

import { PageHeader } from "@/components/layout/PageHeader"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import { Pagination } from "@/components/ui/Pagination"
import { useListadoEmpleados } from "@/components/features/empleados/useListadoEmpleados"
import { useFiltrosPadron } from "@/components/features/shared/useFiltrosPadron"
import { BajasTable } from "@/components/features/bajas/BajasTable"
import { filtrosBajas } from "@/components/features/bajas/_bajas"
import { type EmpleadosFiltros } from "@/services/empleados"

const PAGE_SIZE_INICIAL = 20

/**
 * Quién se fue, cuándo y por qué. El listado de los legajos en `baja`, del más reciente al más
 * viejo.
 *
 * 🔴 EL ORDEN ES `fecha_egreso_desc` Y NO SE ELIGE: la pregunta que trae acá es "quién se fue
 * último". Va como parámetro al backend y no como `.sort()` en el cliente, por lo mismo que en
 * próximos ingresos: el listado pagina, y ordenar acá ordenaría la página, no la lista.
 *
 * 🔴 LOS NULOS DE `fecha_egreso` SALEN PRIMEROS, y es un límite MEDIDO del cliente, no un
 * descuido: en Postgres un `ORDER BY ... DESC` es `NULLS FIRST` por default y postgrest 0.17.2
 * no expone `nullslast`. Una baja sin fecha aparece arriba de las recientes; está pineado con un
 * test del backend (`_empleado_orden.ordenado`) para que sea una conducta declarada y no algo que
 * alguien descubra en pantalla. **No se tapa reordenando en el cliente** — sería tapar el único
 * síntoma de una fila a la que le falta el dato.
 *
 * ⚠️ ESTA PANTALLA NO DA DE BAJA A NADIE, y por eso no tiene ni un botón de escritura: la baja
 * tiene dos vías y solo dos —efectivizar un offboarding, o el import de nómina con `Fecha Baja`—,
 * que son las que escriben `estado`, `fecha_egreso` y motivo juntos. Ver `EstadoEditable`.
 */
export default function BajasPage() {
  const router = useRouter()

  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(PAGE_SIZE_INICIAL)

  const { empresaActivaId, empresaOverride, areaFiltro, debouncedSearch, campos } =
    useFiltrosPadron(() => setPage(1), "Buscar por nombre...")

  // El QUÉ lo arma `filtrosBajas` (el `estado` y el `orden` que definen la pantalla); acá solo se
  // memoriza, porque `useListadoEmpleados` lleva el objeto en las dependencias de su `recargar` y
  // uno nuevo por render dispararía un fetch por render.
  const filtros = useMemo<EmpleadosFiltros>(
    () => filtrosBajas({ search: debouncedSearch, empresaId: empresaOverride, areaId: areaFiltro }),
    [debouncedSearch, empresaOverride, areaFiltro],
  )

  const { data, loading, error, recargar, items, total } = useListadoEmpleados(filtros, page, pageSize)

  const chips = chipsDeCampos(campos)

  return (
    <div>
      <PageHeader
        title="Bajas"
        description={data ? `${total} bajas` : "Cargando..."}
      />

      <FiltersBar campos={campos} panel disabled={loading} />

      <BajasTable
        items={items}
        loading={loading}
        error={error}
        showEmpresa={!empresaActivaId}
        onRetry={recargar}
        onRowClick={(id) => router.push(`/empleados/${id}`)}
        chips={chips}
        onLimpiarTodo={() => chips.forEach((c) => c.quitar())}
      />

      {!loading && !error && items.length > 0 && (
        <Pagination
          page={page} total={total} pageSize={pageSize} onPageChange={setPage}
          onPageSizeChange={(n) => { setPageSize(n); setPage(1) }}
        />
      )}
    </div>
  )
}

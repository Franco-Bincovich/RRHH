"use client"

import { useMemo, useState } from "react"
import { useRouter } from "next/navigation"

import { PageHeader } from "@/components/layout/PageHeader"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import { Pagination } from "@/components/ui/Pagination"
import { useListadoEmpleados } from "@/components/features/empleados/useListadoEmpleados"
import { useActivarEmpleado } from "@/components/features/empleados/useActivarEmpleado"
import { useFiltrosPadron } from "@/components/features/shared/useFiltrosPadron"
import { ProximosIngresosTable } from "@/components/features/proximosIngresos/ProximosIngresosTable"
import { filtrosProximosIngresos } from "@/components/features/proximosIngresos/_proximosIngresos"
import { type EmpleadosFiltros } from "@/services/empleados"
import { useCanWrite } from "@/hooks/useCanWrite"

const PAGE_SIZE_INICIAL = 20

/**
 * Quién entra, y cuándo. El listado de los legajos en `preingreso` —los que existen pero todavía
 * no empezaron— con el acto de confirmar el ingreso a mano de cada fila.
 *
 * 🔴 EL ORDEN ES `fecha_ingreso_asc` Y NO SE ELIGE: la pregunta que trae a esta pantalla es
 * "quién entra primero", no "cómo se apellida". Va como parámetro al backend, no como `.sort()`
 * acá: el listado pagina, así que ordenar en el cliente ordenaría LA PÁGINA — con 40 preingresos
 * la primera saldría prolija y no sería la de los que entran antes. Ver `OrdenEmpleados`.
 *
 * 🔴 `estado: "preingreso"` TAMPOCO SE ELIGE, y por eso el filtro de estado no está en la barra
 * (ver `_camposPadron`). Sin este parámetro el listado ni siquiera los traería: el default del
 * backend EXCLUYE los preingresos a propósito (`_empleado_row.filtro_estado`), que es lo que
 * mantiene /empleados mostrando gente que ya entró.
 */
export default function ProximosIngresosPage() {
  const router = useRouter()
  const canWrite = useCanWrite()

  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(PAGE_SIZE_INICIAL)

  const { empresaActivaId, empresaOverride, areaFiltro, debouncedSearch, campos } =
    useFiltrosPadron(() => setPage(1), "Buscar por nombre...")

  // Un solo objeto de filtros, memorizado sobre los primitivos: `useListadoEmpleados` lo lleva en
  // las dependencias de su `recargar`, y un objeto nuevo por render dispararía un fetch por render.
  // El QUÉ lo arma `filtrosProximosIngresos` —incluidos el `estado` y el `orden` que definen la
  // pantalla—; acá solo se memoriza. Ver el porqué del corte en `_proximosIngresos.ts`.
  const filtros = useMemo<EmpleadosFiltros>(
    () => filtrosProximosIngresos({ search: debouncedSearch, empresaId: empresaOverride, areaId: areaFiltro }),
    [debouncedSearch, empresaOverride, areaFiltro],
  )

  const { data, loading, error, recargar, items, total } = useListadoEmpleados(filtros, page, pageSize)

  // Al confirmar un ingreso la persona deja de ser preingreso, así que su fila desaparece de esta
  // pantalla: se recarga el listado en vez de sacarla del array a mano. El total del encabezado y
  // la paginación salen del backend, y con un borrado local dirían uno más del que hay.
  const { activandoId, activar } = useActivarEmpleado(recargar)

  const chips = chipsDeCampos(campos)

  return (
    <div>
      <PageHeader
        title="Próximos ingresos"
        description={data ? `${total} próximos ingresos` : "Cargando..."}
      />

      <FiltersBar campos={campos} panel disabled={loading} />

      <ProximosIngresosTable
        items={items}
        loading={loading}
        error={error}
        showEmpresa={!empresaActivaId}
        onRetry={recargar}
        onRowClick={(id) => router.push(`/empleados/${id}`)}
        chips={chips}
        onLimpiarTodo={() => chips.forEach((c) => c.quitar())}
        onActivar={canWrite ? activar : undefined}
        activandoId={activandoId}
      />

      {/*
       * El pie va siempre que haya filas, no solo con más de una página: "Mostrando 1–12 de 40"
       * es el patrón, y el total que repite es el TOTAL FILTRADO del backend. Cambiar el tamaño
       * vuelve a la página 1, que con filas más grandes puede no existir.
       */}
      {!loading && !error && items.length > 0 && (
        <Pagination
          page={page} total={total} pageSize={pageSize} onPageChange={setPage}
          onPageSizeChange={(n) => { setPageSize(n); setPage(1) }}
        />
      )}
    </div>
  )
}

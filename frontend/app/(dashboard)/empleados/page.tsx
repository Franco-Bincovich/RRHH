"use client"

import { Suspense, useState, useMemo } from "react"
import { useRouter } from "next/navigation"

import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import { Pagination } from "@/components/ui/Pagination"
import { EmpleadosAcciones } from "@/components/features/empleados/EmpleadosAcciones"
import { EmpleadosTable } from "@/components/features/empleados/EmpleadosTable"
import { useFiltrosEmpleados } from "@/components/features/empleados/useFiltrosEmpleados"
import { EmpleadoModal } from "@/components/features/empleados/EmpleadoModal"
import { ImportarNominaModal } from "@/components/features/empleados/ImportarNominaModal"
import { SuperioresPendientesPanel } from "@/components/features/empleados/SuperioresPendientesPanel"
import { useListadoEmpleados } from "@/components/features/empleados/useListadoEmpleados"
import { type EmpleadosFiltros } from "@/services/empleados"
import { useCanWrite } from "@/hooks/useCanWrite"

/**
 * Filas por página INICIAL. Dejó de ser una constante fija cuando el pie tomó la forma del
 * sistema de diseño (§3: "Mostrando 1–12 de 1.042", selector de filas y paginación numérica):
 * el selector de filas es parte del patrón, así que el valor pasa a ser estado de la pantalla.
 */
const PAGE_SIZE_INICIAL = 20

/**
 * useFiltrosEmpleados llama a `useSearchParams` (siembra el filtro `sin_manager`, al que
 * linkea la alerta del dashboard), y eso EXIGE una barrera de Suspense: sin ella `next build`
 * falla con "Missing Suspense boundary with useSearchParams". En dev no se nota porque las
 * rutas se renderizan on-demand — es exactamente el caso de tsc/build verde vs. dev feliz.
 */
export default function EmpleadosPage() {
  return (
    <Suspense fallback={<PageHeader title="Colaboradores" description="Cargando..." />}>
      <EmpleadosListado />
    </Suspense>
  )
}

function EmpleadosListado() {
  const router = useRouter()
  const canWrite = useCanWrite()

  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(PAGE_SIZE_INICIAL)
  const [newOpen, setNewOpen] = useState(false)
  const [importOpen, setImportOpen] = useState(false)

  const { empresaActivaId, empresaOverride, areaFiltro, estadoFiltro, esLider, sinManager, proyectoId, debouncedSearch, campos } =
    useFiltrosEmpleados(() => setPage(1))

  /*
   * 🔴 UN SOLO OBJETO DE FILTROS PARA EL LISTADO Y PARA EL EXPORT (invariante b del molde del
   * bloque B). Antes las dos llamadas repetían la misma lista de siete campos escrita a mano: dos
   * copias que compilan igual aunque una se olvide de un filtro, y ahí el archivo sale con más
   * filas de las que se ven en pantalla. `useMemo` sobre los valores primitivos porque `load` lo
   * lleva en sus dependencias: un objeto nuevo por render dispararía un fetch por render.
   */
  const filtros = useMemo<EmpleadosFiltros>(() => ({
    search: debouncedSearch || undefined,
    estado: estadoFiltro || undefined,
    empresaId: empresaOverride,
    areaId: areaFiltro || undefined,
    esLider,
    sinManager,
    proyectoId,
  }), [debouncedSearch, estadoFiltro, empresaOverride, areaFiltro, esLider, sinManager, proyectoId])

  const { data, loading, error, recargar, items, total } = useListadoEmpleados(filtros, page, pageSize)

  const chips = chipsDeCampos(campos)

  return (
    <div>
      <PageHeader
        title="Colaboradores"
        /*
         * 🔴 EL CONTEO REAL SE MANTIENE DURANTE LA CARGA (§3: "el conteo real en el subtítulo, así
         * la pantalla no salta cuando llegan los datos"). `data` NO se limpia al refiltrar, así que
         * en una recarga el subtítulo sigue mostrando el total anterior en vez de parpadear a
         * "Cargando..." y volver. Sólo la primerísima carga —cuando todavía no hay `data`— no
         * tiene número que mostrar.
         */
        description={data ? `${total} colaboradores` : "Cargando..."}
        action={
          <EmpleadosAcciones
            filtros={filtros}
            mostrarExport={!loading && !error && items.length > 0}
            canWrite={canWrite}
            onImportar={() => setImportOpen(true)}
            onNuevo={() => setNewOpen(true)}
          />
        }
      />

      <SuperioresPendientesPanel onResuelto={recargar} />

      {/* `panel`: la forma completa del patrón de filtros (caja propia, "Más filtros" y los chips
          de la fila inferior). /empleados es la pantalla piloto; las demás siguen con la barra
          simple hasta que se migren de a una — ver el 🔴 de `FiltersBar`. */}
      {/* `disabled` durante la carga: los filtros quedan A LA VISTA con sus chips, pero no se
          pueden tocar (§3). Que desaparezcan o se vacíen sería peor — el usuario perdería de
          vista justo el filtro cuyo resultado está esperando. */}
      <FiltersBar campos={campos} panel disabled={loading} />

      <EmpleadosTable
        items={items}
        loading={loading}
        error={error}
        showEmpresa={!empresaActivaId}
        onRetry={recargar}
        onRowClick={(id) => router.push(`/empleados/${id}`)}
        chips={chips}
        onLimpiarTodo={() => chips.forEach((c) => c.quitar())}
        accionVacio={canWrite ? (
          <Button className="min-h-11" onClick={() => setNewOpen(true)}>Cargar el primero</Button>
        ) : undefined}
      />

      {/*
       * 🔴 EL PIE VA SIEMPRE QUE HAYA FILAS, no sólo cuando hay más de una página. Antes aparecía
       * con `total > PAGE_SIZE`: con 31 empleados y un filtro puesto, la pantalla dejaba de decir
       * cuántos resultados había justo cuando el filtro es el que hay que entender. "Mostrando
       * 1–12 de 1.042" es el patrón, y el total que repite es el TOTAL FILTRADO del backend.
       * Cambiar el tamaño vuelve a la página 1: la 4 puede no existir con filas más grandes.
       */}
      {!loading && !error && items.length > 0 && (
        <Pagination
          page={page} total={total} pageSize={pageSize} onPageChange={setPage}
          onPageSizeChange={(n) => { setPageSize(n); setPage(1) }}
        />
      )}

      <EmpleadoModal
        open={newOpen}
        onClose={() => setNewOpen(false)}
        onSuccess={() => { setNewOpen(false); recargar() }}
      />

      <ImportarNominaModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onSuccess={() => { setImportOpen(false); recargar() }}
      />
    </div>
  )
}

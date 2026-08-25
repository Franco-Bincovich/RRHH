"use client"

import { useMemo, useState } from "react"

import { PageHeader } from "@/components/layout/PageHeader"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { exportarCandidatos } from "@/services/candidatos"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import { CandidatosLista } from "@/components/features/candidatos/CandidatosLista"
import { CandidatoDetailPanel } from "@/components/features/candidatos/CandidatoDetailPanel"
import { agruparCandidatos } from "@/components/features/candidatos/agruparCandidatos"
import { construirCampos } from "@/components/features/candidatos/_camposCandidatos"
import { Pagination } from "@/components/ui/Pagination"
import { useCandidatos } from "@/hooks/useCandidatos"
import { LeyendaDescarte } from "@/components/features/candidatos/ClasificacionBadge"
import type { CandidatoConGrupo, FiltroClasificacion } from "@/types/candidato"

const PAGE_SIZE_INICIAL = 20

export default function CandidatosPage() {
  // 🔴 Los dos filtros viajan al backend, NO se aplican sobre el array: el export usa el mismo
  // traductor (`queryCandidatos`) y si se filtrara acá el archivo saldría con más filas que la
  // pantalla. Por eso los chips de esta pantalla dicen la verdad.
  const [asignacionFiltro, setAsignacionFiltro] = useState("")
  const [clasificacion, setClasificacion] = useState("")
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(PAGE_SIZE_INICIAL)

  const campos = construirCampos({
    asignacionFiltro, setAsignacionFiltro, clasificacion, setClasificacion,
    // Volver a 1 al cambiar un filtro (invariante 4 del Bloque B): con menos resultados, la
    // página en la que estabas puede quedar fuera del nuevo total y la pantalla se ve vacía
    // sobre un filtro que sí tiene datos.
    onFiltroChange: () => setPage(1),
  })
  const chips = chipsDeCampos(campos)

  const filtros = useMemo(() => ({
    sinVacante: asignacionFiltro === "sin",
    clasificacion: (clasificacion || undefined) as FiltroClasificacion | undefined,
  }), [asignacionFiltro, clasificacion])

  const { candidatos, total, conteoPorGrupo, loading, error, refetch } =
    useCandidatos(filtros, page, pageSize)
  const grupos = useMemo(() => agruparCandidatos(candidatos, conteoPorGrupo),
                         [candidatos, conteoPorGrupo])
  const [seleccionado, setSeleccionado] = useState<CandidatoConGrupo | null>(null)

  return (
    <div>
      <PageHeader
        title="Candidatos"
        /* 🔴 `total` y no `candidatos.length`: con paginación el largo del array es 20 y el
           encabezado diría "20 candidatos" para siempre, en cualquier padrón. */
        description={loading ? "Cargando..." : `${total} candidato${total !== 1 ? "s" : ""}`}
        action={<ExportMenu onExport={(f) => exportarCandidatos(f, filtros)} />}
      />

      {/* `panel`: la forma completa del patrón de filtros (caja propia y los chips de la fila
          inferior). Sin "Más filtros": con DOS filtros, esconder uno atrás de un botón deja la
          mitad de la pantalla inalcanzable a cambio de nada — ver `_camposCandidatos.ts`.
          `disabled` durante la carga: los controles quedan a la vista pero no se pueden tocar. */}
      <FiltersBar campos={campos} panel disabled={loading} />

      {/* Visible y arriba de la lista, no en un tooltip: quien filtra por clasificación tiene
          que leer que esto no decide nada ANTES de mirar los resultados. */}
      <div className="mb-4"><LeyendaDescarte /></div>

      <CandidatosLista
        grupos={grupos}
        loading={loading}
        error={error}
        chips={chips}
        onRetry={refetch}
        onSelect={setSeleccionado}
        onLimpiarTodo={() => chips.forEach((c) => c.quitar())}
      />

      {/*
       * Los grupos se arman DENTRO de la página: la paginación es plana y va al pie de todos, no
       * adentro de cada búsqueda.
       * 🔴 EL PIE VA SIEMPRE QUE HAYA FILAS, no sólo cuando hay más de una página. Antes aparecía
       * con `total > pageSize`, así que con un filtro puesto la pantalla dejaba de decir cuántos
       * resultados había justo cuando el filtro es lo que hay que entender. El total que muestra
       * es el TOTAL FILTRADO del backend, no `candidatos.length`.
       */}
      {!loading && !error && candidatos.length > 0 && (
        <Pagination page={page} total={total} pageSize={pageSize} onPageSizeChange={setPageSize} onPageChange={setPage} />
      )}

      <CandidatoDetailPanel
        candidato={seleccionado}
        open={seleccionado !== null}
        onClose={() => setSeleccionado(null)}
        onDeleted={refetch}
        onAsignada={refetch}
        onContratado={refetch}
      />
    </div>
  )
}

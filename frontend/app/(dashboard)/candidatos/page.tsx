"use client"

import { useMemo, useState } from "react"
import { UserSearch } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { exportarCandidatos } from "@/services/candidatos"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { CandidatoGrupo } from "@/components/features/candidatos/CandidatoGrupo"
import { CandidatoDetailPanel } from "@/components/features/candidatos/CandidatoDetailPanel"
import { agruparCandidatos } from "@/components/features/candidatos/agruparCandidatos"
import { useCandidatos } from "@/hooks/useCandidatos"
import { LeyendaDescarte } from "@/components/features/candidatos/ClasificacionBadge"
import type { CandidatoConGrupo, FiltroClasificacion } from "@/types/candidato"

const OPCIONES: { value: "" | FiltroClasificacion; label: string }[] = [
  { value: "", label: "Todas las clasificaciones" },
  { value: "relevante", label: "Relevante" },
  { value: "dudoso", label: "Dudoso" },
  // 🔴 Está en la lista como una más y NO se oculta ni se colapsa por defecto: la opción
  // por defecto es "todas". Esconder los no relevantes convertiría el filtro en la
  // decisión que este módulo justamente no toma.
  { value: "no_relevante", label: "No relevante" },
  { value: "sin_clasificar", label: "Sin clasificar" },
]

export default function CandidatosPage() {
  // 🔴 El filtro viaja al backend, NO se aplica sobre el array: el export usa el mismo traductor
  // (`queryCandidatos`) y si se filtrara acá el archivo saldría con más filas que la pantalla.
  const [sinVacante, setSinVacante] = useState(false)
  const [clasificacion, setClasificacion] = useState<"" | FiltroClasificacion>("")
  const filtros = { sinVacante, clasificacion: clasificacion || undefined }
  const { candidatos, loading, error, refetch } = useCandidatos(filtros)
  const grupos = useMemo(() => agruparCandidatos(candidatos), [candidatos])
  const [seleccionado, setSeleccionado] = useState<CandidatoConGrupo | null>(null)

  return (
    <div>
      <PageHeader
        title="Candidatos"
        description={loading ? "Cargando..." : `${candidatos.length} candidato${candidatos.length !== 1 ? "s" : ""}`}
        action={<ExportMenu onExport={(f) => exportarCandidatos(f, filtros)} />}
      />

      <div className="mb-4 flex flex-wrap items-center gap-4">
        <label className="flex w-fit items-center gap-2 text-sm text-foreground">
          <input
            type="checkbox"
            className="size-4 rounded border-input"
            checked={sinVacante}
            onChange={(e) => setSinVacante(e.target.checked)}
          />
          Solo los que no tienen búsqueda asignada
        </label>

        <select
          aria-label="Clasificación"
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          value={clasificacion}
          onChange={(e) => setClasificacion(e.target.value as "" | FiltroClasificacion)}
        >
          {OPCIONES.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      {/* Visible y arriba de la lista, no en un tooltip: quien filtra por clasificación tiene
          que leer que esto no decide nada ANTES de mirar los resultados. */}
      <div className="mb-4"><LeyendaDescarte /></div>

      {loading && (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full rounded-xl" />
          ))}
        </div>
      )}

      {!loading && error && <ErrorState action={refetch} />}

      {!loading && !error && candidatos.length === 0 && (
        <EmptyState
          icon={<UserSearch />}
          title="Todavía no hay candidatos cargados"
          description="Cuando cargues candidatos a tus búsquedas, van a aparecer acá agrupados."
        />
      )}

      {!loading && !error && grupos.map((grupo) => (
        <CandidatoGrupo key={grupo.nombre} grupo={grupo} onSelect={setSeleccionado} />
      ))}

      <CandidatoDetailPanel
        candidato={seleccionado}
        open={seleccionado !== null}
        onClose={() => setSeleccionado(null)}
        onDeleted={refetch}
        onAsignada={refetch}
      />
    </div>
  )
}

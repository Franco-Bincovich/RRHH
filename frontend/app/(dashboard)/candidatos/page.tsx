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
import type { CandidatoConGrupo } from "@/types/candidato"

export default function CandidatosPage() {
  const { candidatos, loading, error, refetch } = useCandidatos()
  const grupos = useMemo(() => agruparCandidatos(candidatos), [candidatos])
  const [seleccionado, setSeleccionado] = useState<CandidatoConGrupo | null>(null)

  return (
    <div>
      <PageHeader
        title="Candidatos"
        description={loading ? "Cargando..." : `${candidatos.length} candidato${candidatos.length !== 1 ? "s" : ""}`}
        action={<ExportMenu onExport={exportarCandidatos} />}
      />

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
      />
    </div>
  )
}

import { Badge } from "@/components/ui/badge"
import { CandidatoRow } from "@/components/features/candidatos/CandidatoRow"
import type { CandidatoConGrupo, GrupoCandidatos } from "@/types/candidato"

interface Props {
  grupo: GrupoCandidatos
  onSelect: (candidato: CandidatoConGrupo) => void
}

/** Card de un grupo (búsqueda): título + badge de estado + sus candidatos. */
export function CandidatoGrupo({ grupo, onSelect }: Props) {
  return (
    <section className="mb-6 rounded-xl border bg-card p-4 md:p-6">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <h2 className="text-base font-semibold text-foreground">{grupo.nombre}</h2>
        {grupo.activa ? (
          <Badge variant="outline">Activa</Badge>
        ) : (
          <Badge variant="secondary">Búsqueda cerrada</Badge>
        )}
        {/* 🔴 EL TOTAL DE LA BÚSQUEDA, NO LO VISIBLE. El listado se pagina plano y el grupo se
            arma dentro de la página, así que `candidatos.length` cambiaría al pasar de página
            sobre una búsqueda que no cambió. Cuando difieren se muestran los dos: decir "40"
            arriba de 4 filas, sin explicar el 4, es igual de confuso que decir "4". */}
        <span className="text-sm text-muted-foreground">
          {grupo.candidatos.length !== grupo.totalGrupo && `${grupo.candidatos.length} de `}
          {grupo.totalGrupo} candidato{grupo.totalGrupo !== 1 ? "s" : ""}
        </span>
      </div>
      <div className="space-y-2">
        {grupo.candidatos.map((c) => (
          <CandidatoRow key={c.id} candidato={c} onSelect={() => onSelect(c)} />
        ))}
      </div>
    </section>
  )
}

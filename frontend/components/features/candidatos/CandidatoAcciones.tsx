"use client"

import { AsignarVacanteCandidato } from "@/components/features/candidatos/AsignarVacanteCandidato"
import { EliminarCandidatoButton } from "@/components/features/candidatos/EliminarCandidatoButton"
import type { CandidatoConGrupo } from "@/types/candidato"

/**
 * Lo que se puede HACER con un candidato desde su panel: asignarle una búsqueda si está huérfano,
 * y borrarlo si no pertenece a ninguna viva.
 *
 * Sale de `CandidatoDetailPanel`, que quedó en 159/150 al sumarle la asignación. El panel
 * muestra datos; acá viven las acciones y sus condiciones, que son distintas entre sí:
 *
 * 🔴 `vacante_id === null` (asignar) NO es lo mismo que `!busqueda_activa` (borrar). El segundo
 * también es true cuando la búsqueda se borró y el candidato conserva el título congelado — ese
 * candidato SÍ se puede reasignar, y por eso las dos condiciones no se pueden unificar.
 */
interface Props {
  candidato: CandidatoConGrupo
  onClose: () => void
  onDeleted?: () => void
  onAsignada?: () => void
}

function Bloque({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-5">
      <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</h3>
      {children}
    </div>
  )
}

export function CandidatoAcciones({ candidato, onClose, onDeleted, onAsignada }: Props) {
  return (
    <>
      {candidato.vacante_id === null && (
        <Bloque title="Asignar a una búsqueda">
          <AsignarVacanteCandidato
            candidatoId={candidato.id}
            onAsignada={() => { onClose(); onAsignada?.() }}
          />
        </Bloque>
      )}
      {!candidato.busqueda_activa && (
        <Bloque title="Acciones">
          <EliminarCandidatoButton candidato={candidato} onDeleted={() => { onClose(); onDeleted?.() }} />
        </Bloque>
      )}
    </>
  )
}

"use client"

import { AsignarVacanteCandidato } from "@/components/features/candidatos/AsignarVacanteCandidato"
import { ContratarCandidatoButton } from "@/components/features/candidatos/ContratarCandidatoButton"
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
 *
 * 🔴 Y CONTRATAR PIDE DOS COSAS A LA VEZ, que tampoco se pueden unificar: `etapa_pipeline` en
 * "oferta" (dónde está en el proceso) Y `estado` en "activo" (si sigue en carrera). Alguien que
 * llegó a la oferta y después la rechazó queda con etapa "oferta" y estado "descartado": mirar
 * solo la etapa le ofrecería un botón que el backend rechaza con 409.
 */
interface Props {
  candidato: CandidatoConGrupo
  onClose: () => void
  onDeleted?: () => void
  onAsignada?: () => void
  onContratado?: () => void
}

function Bloque({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-5">
      <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</h3>
      {children}
    </div>
  )
}

export function CandidatoAcciones({
  candidato, onClose, onDeleted, onAsignada, onContratado,
}: Props) {
  const contratable = candidato.etapa_pipeline === "oferta" && candidato.estado === "activo"

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
      {contratable && (
        <Bloque title="Contratación">
          <ContratarCandidatoButton
            candidato={candidato}
            onContratado={() => { onClose(); onContratado?.() }}
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

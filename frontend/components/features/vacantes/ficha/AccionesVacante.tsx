"use client"

import { ExternalLink, Plus, Share2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { EliminarVacanteButton } from "@/components/features/vacantes/EliminarVacanteButton"
import type { Vacante } from "@/types/vacantes"

/**
 * Las acciones de la barra de identidad de la ficha de una vacante.
 *
 * 🔴 LA PRIMARIA VA ÚLTIMA (`docs/SISTEMA-DE-DISENO.md` §3), y el orden de este archivo ES el
 * orden de la pantalla: LinkedIn, eliminar, y "Agregar candidato" al final, sólida. Antes el orden
 * era LinkedIn → agregar → eliminar, o sea que la acción irreversible quedaba **después** de la
 * más usada, en el borde de la barra: el lugar al que va el ojo y al que va el pulgar. Mover el
 * botón destructivo al medio no lo esconde —sigue en rojo y sigue pidiendo confirmación— pero
 * deja de ser el que se aprieta de más.
 *
 * 🔴 LO DE LINKEDIN SON DOS COSAS DISTINTAS Y NO UN BOTÓN CON DOS ESTADOS: si ya se publicó es un
 * ENLACE al aviso (se sale del sistema, `target="_blank"`) y si no, un BOTÓN que abre el modal. Un
 * solo control que cambie de comportamiento según el estado sería el mismo elemento haciendo dos
 * cosas incomparables. El enlace se muestra aunque no haya permiso de escritura: mirar el aviso
 * publicado no es escribir.
 *
 * Se renderiza sólo con permiso de escritura salvo por ese enlace; el gate lo aplica la página.
 */
export function AccionesVacante({ vacante, canWrite, onPublicarLinkedin, onAgregarCandidato }: {
  vacante: Vacante
  canWrite: boolean
  onPublicarLinkedin: () => void
  onAgregarCandidato: () => void
}) {
  return (
    <>
      {vacante.linkedin_post_id ? (
        <a
          href={vacante.linkedin_url ?? "#"}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex min-h-11 items-center gap-2 rounded-md border border-[#0A66C2] px-3 py-2 text-sm font-medium text-[#0A66C2] transition-colors hover:bg-[#0A66C2]/10"
        >
          <Share2 className="size-4" />
          Publicada en LinkedIn
          <ExternalLink className="size-3" />
        </a>
      ) : canWrite ? (
        <Button
          variant="outline"
          className="min-h-11 gap-2 border-[#0A66C2] text-[#0A66C2] hover:bg-[#0A66C2]/10"
          onClick={onPublicarLinkedin}
        >
          <Share2 className="size-4" />
          Publicar en LinkedIn
        </Button>
      ) : null}

      {canWrite && <EliminarVacanteButton vacanteId={vacante.id} titulo={vacante.titulo} />}

      {canWrite && (
        <Button className="min-h-11 gap-2" onClick={onAgregarCandidato}>
          <Plus className="size-4" />
          Agregar candidato
        </Button>
      )}
    </>
  )
}

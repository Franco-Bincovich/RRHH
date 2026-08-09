"use client"

import { useState } from "react"
import { FileText } from "lucide-react"

import { CorregirClasificacion } from "@/components/features/screening/CorregirClasificacion"
import { Button } from "@/components/ui/button"
import { getCandidatoCvUrl } from "@/services/candidatos"
import type { Candidato } from "@/types/vacantes"

/**
 * Lo que se puede hacer con un candidato SIN salir de la ficha de la vacante: abrir su CV y
 * corregir su clasificación.
 *
 * 🔴 POR QUÉ ACÁ. Todo el flujo del screening ocurre en esta pantalla —se aprieta "revisar
 * casilla", se aprieta "clasificar", se leen los resultados— y hasta ahora el CV solo se podía
 * abrir desde /candidatos: `getCandidatoCvUrl` tenía un único caller, `CandidatoDetailPanel`.
 * Revisar exigía cambiar de sección y volver, por cada candidato.
 *
 * El botón del CV solo aparece si hay archivo. `cv_storage_path` es una ruta de un bucket
 * privado: no se muestra ni se linkea directo, se cambia por una signed URL en el momento de
 * abrirla (`GET /api/candidatos/{id}/cv-url`, 3600 s).
 */
export function CandidatoAccionesPipeline({ candidato, onCambio }: {
  candidato: Candidato
  onCambio?: () => void
}) {
  const [abriendo, setAbriendo] = useState(false)

  const abrirCv = async () => {
    setAbriendo(true)
    try {
      window.open(await getCandidatoCvUrl(candidato.id), "_blank", "noopener,noreferrer")
    } catch {
      /* el CV no se pudo firmar; el resto de la tarjeta sigue usable */
    } finally {
      setAbriendo(false)
    }
  }

  return (
    <div className="mt-1.5 space-y-1">
      {candidato.cv_storage_path && (
        <Button variant="ghost" size="sm" onClick={abrirCv} disabled={abriendo}>
          <FileText className="size-3.5" />
          {abriendo ? "Abriendo..." : "Ver CV"}
        </Button>
      )}
      <CorregirClasificacion
        candidatoId={candidato.id}
        actual={candidato.clasificacion_ia}
        motivoActual={candidato.clasificacion_motivo}
        onCorregido={onCambio}
      />
    </div>
  )
}

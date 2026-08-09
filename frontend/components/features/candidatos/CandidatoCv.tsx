"use client"

import { FileText, TriangleAlert } from "lucide-react"

import { Button } from "@/components/ui/button"

/**
 * El bloque "CV" de la ficha: el aviso de por qué no se pudo leer, y el botón para abrirlo.
 *
 * 🔴 EL WARNING VA ARRIBA DEL BOTÓN Y SIEMPRE QUE EXISTA. Un CV que el sistema no pudo leer no se
 * va a clasificar nunca; sin este aviso RRHH esperaría un resultado que no va a llegar, y con un
 * booleano tendría que abrir el archivo para saber qué pedirle al candidato. El motivo lo escribe
 * el backend (`services/_cv_texto.py`) y acá NO se traduce: cada texto nombra su acción.
 *
 * ⚠️ El warning y el archivo son independientes: un CV largo se procesó (hay texto) Y avisa que
 * se truncó. Por eso los dos se muestran juntos y no como alternativas.
 *
 * Sale de `CandidatoDetailPanel`, que quedó en 154/150 al sumarle el aviso.
 */
interface Props {
  storagePath: string | null
  warning: string | null
  loading: boolean
  onAbrir: () => void
}

export function CandidatoCv({ storagePath, warning, loading, onAbrir }: Props) {
  return (
    <>
      {warning && (
        <p className="mb-2 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200">
          <TriangleAlert className="mt-0.5 size-3.5 shrink-0" />
          {warning}
        </p>
      )}
      {storagePath ? (
        <Button variant="outline" className="gap-2" onClick={onAbrir} disabled={loading}>
          <FileText className="size-4" /> {loading ? "Abriendo…" : "Abrir CV"}
        </Button>
      ) : (
        <p className="text-sm text-muted-foreground">Sin CV cargado</p>
      )}
    </>
  )
}

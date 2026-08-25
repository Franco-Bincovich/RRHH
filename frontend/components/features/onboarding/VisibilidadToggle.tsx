"use client"

import { useState } from "react"
import { PISO_TACTIL } from "@/components/ui/AccionFila"
import { Lock, Users } from "lucide-react"
import { toast } from "sonner"

import { updateTemplate } from "@/services/onboarding"

interface VisibilidadToggleProps {
  templateId: string
  esPublica: boolean
  /** true si el usuario es el autor (o la plantilla no tiene autor). Si no, el control se ve
   *  pero no se puede accionar — igual que lo rechazaría el backend. */
  puedeCambiar: boolean
  onCambiada: (esPublica: boolean) => void
}

/**
 * Compartida / privada. Autocontenido: hace su propio PUT (patrón de AddTareaForm y
 * NuevoTemplateModal) y avisa al caller para que refleje el nuevo estado.
 *
 * SE MUESTRA SIEMPRE, deshabilitado cuando no sos el autor, en vez de esconderse: que una
 * plantilla sea privada es información útil para todo el que la mira —explica por qué no
 * aparece en la lista de un compañero—, y esconder el control dejaría el estado invisible.
 * La regla la aplica el backend igual (403 TEMPLATE_NO_SOS_AUTOR); esto no es la barrera.
 */
export function VisibilidadToggle({ templateId, esPublica, puedeCambiar, onCambiada }: VisibilidadToggleProps) {
  const [guardando, setGuardando] = useState(false)

  async function alternar() {
    if (!puedeCambiar || guardando) return
    const destino = !esPublica
    setGuardando(true)
    try {
      await updateTemplate(templateId, { es_publica: destino })
      onCambiada(destino)
      toast.success(destino ? "Ahora la ve todo el equipo" : "Ahora solo la ves vos")
    } catch {
      toast.error("No se pudo cambiar la visibilidad.")
    } finally {
      setGuardando(false)
    }
  }

  const Icono = esPublica ? Users : Lock
  const etiqueta = esPublica ? "Compartida" : "Privada"

  return (
    <button
      type="button"
      onClick={alternar}
      disabled={!puedeCambiar || guardando}
      aria-pressed={!esPublica}
      title={
        puedeCambiar
          ? esPublica
            ? "La ve todo el equipo. Clic para volverla privada."
            : "Solo la ves vos. Clic para compartirla."
          : "Solo quien la creó puede cambiar esto."
      }
      className={`${PISO_TACTIL} flex min-h-9 items-center gap-1.5 rounded-lg border px-2.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
        esPublica ? "text-muted-foreground" : "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400"
      } ${puedeCambiar ? "hover:bg-muted" : "cursor-default opacity-70"}`}
    >
      <Icono className="size-3.5" />
      {guardando ? "Guardando…" : etiqueta}
    </button>
  )
}

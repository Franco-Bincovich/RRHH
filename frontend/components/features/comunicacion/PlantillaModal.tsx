"use client"

import { useEffect, useState } from "react"

import { AccionesDelPie } from "@/components/features/comunicacion/PlantillaAcciones"
import { PlantillaCampos, type CampoPlantilla } from "@/components/features/comunicacion/PlantillaCampos"
import { PlantillaPreview } from "@/components/features/comunicacion/PlantillaPreview"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { guardarPlantilla, previewPlantilla } from "@/services/plantillas"
import type { Plantilla, PreviewResponse } from "@/types/plantillas"

interface Props {
  open: boolean
  plantilla: Plantilla | null
  contextos: Record<string, string[]>
  onClose: () => void
  onSuccess: () => void
}

/**
 * Editor de una plantilla de mail. MODAL ANCHO a propósito: /configuracion es `max-w-2xl`, que
 * alcanza para "22 días hábiles" y no para escribir el cuerpo de un mail. La sección lista; la
 * edición pasa acá.
 *
 * Las variables se insertan con un clic (ver `PlantillaVariables`) y el preview usa el mismo
 * renderer que el envío (ver `PlantillaPreview`).
 */
export function PlantillaModal({ open, plantilla, contextos, onClose, onSuccess }: Props) {
  const [clave, setClave] = useState("")
  const [contexto, setContexto] = useState("empleado")
  const [asunto, setAsunto] = useState("")
  const [cuerpo, setCuerpo] = useState("")
  const [preview, setPreview] = useState<PreviewResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [guardando, setGuardando] = useState(false)
  const [sinEmpresa, setSinEmpresa] = useState(false)

  useEffect(() => {
    if (!open) return
    setClave(plantilla?.clave ?? "")
    setContexto(plantilla?.contexto ?? "empleado")
    setAsunto(plantilla?.asunto ?? "")
    setCuerpo(plantilla?.cuerpo ?? "")
    setPreview(null)
    setError(null)
    // Se lee AL ABRIR y no al montar: el modal vive montado con `open=false` y el usuario puede
    // cambiar el selector del sidebar entre una apertura y la siguiente.
    setSinEmpresa(getEmpresaActivaId() === null)
  }, [open, plantilla])

  const valores = { clave, contexto, asunto, cuerpo }
  const setters: Record<CampoPlantilla, (v: string) => void> =
    { clave: setClave, contexto: setContexto, asunto: setAsunto, cuerpo: setCuerpo }

  async function verPreview() {
    setError(null)
    try {
      setPreview(await previewPlantilla({ contexto, asunto, cuerpo }))
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo previsualizar")
    }
  }

  async function guardar() {
    setGuardando(true)
    setError(null)
    try {
      await guardarPlantilla({ id: plantilla?.es_global ? undefined : plantilla?.id, clave, contexto, asunto, cuerpo })
      onSuccess()
    } catch (e) {
      // El 422 de variable inválida llega acá con la lista de las que sobran: es el mensaje
      // más útil del formulario y por eso se muestra tal cual viene del backend.
      setError(e instanceof Error ? e.message : "No se pudo guardar")
    } finally {
      setGuardando(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>{plantilla ? "Editar plantilla" : "Nueva plantilla"}</DialogTitle>
        </DialogHeader>

        {plantilla?.es_global && (
          <p className="rounded-lg border border-sky-200 bg-sky-50 p-2.5 text-sm text-sky-900 dark:border-sky-800 dark:bg-sky-950 dark:text-sky-100">
            Estás editando la plantilla <strong>general</strong>. Al guardar se crea la versión de
            tu empresa; la general queda intacta para las demás.
          </p>
        )}

        <PlantillaCampos
          valores={valores}
          onCambio={(campo, valor) => setters[campo](valor)}
          contextos={contextos}
          bloqueada={!!plantilla}
        />

        {preview && <PlantillaPreview preview={preview} />}

        {error && <p className="text-sm text-destructive">{error}</p>}

        {/* ⚠️ El `<DialogFooter>` tiene que quedar como hijo LITERAL de `DialogContent`: el
            diálogo reparte los hijos por tipo para fijar los extremos, y envolverlo en un
            componente propio lo mandaría al cuerpo scrollable (ver `partirHijos` en ui/dialog).
            Por eso lo que se extrajo es el CONTENIDO del pie, no el pie. */}
        <DialogFooter className={sinEmpresa ? "sm:justify-between" : undefined}>
          <AccionesDelPie
            sinEmpresa={sinEmpresa} guardando={guardando} valores={valores}
            onGuardar={guardar} onPreview={verPreview}
          />
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

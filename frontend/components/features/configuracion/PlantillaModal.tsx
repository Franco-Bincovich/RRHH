"use client"

import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import { PlantillaPreview } from "@/components/features/configuracion/PlantillaPreview"
import { PlantillaVariables } from "@/components/features/configuracion/PlantillaVariables"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
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

  useEffect(() => {
    if (!open) return
    setClave(plantilla?.clave ?? "")
    setContexto(plantilla?.contexto ?? "empleado")
    setAsunto(plantilla?.asunto ?? "")
    setCuerpo(plantilla?.cuerpo ?? "")
    setPreview(null)
    setError(null)
  }, [open, plantilla])

  function insertar(variable: string) {
    setCuerpo((actual) => `${actual}{{${variable}}}`)
  }

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

        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <Label htmlFor="pl-clave">Nombre interno</Label>
            <Input id="pl-clave" value={clave} onChange={(e) => setClave(e.target.value)}
                   placeholder="bienvenida_empleado" disabled={!!plantilla} />
          </div>
          <div>
            <Label htmlFor="pl-ctx">Tipo de mail</Label>
            <select id="pl-ctx" value={contexto} onChange={(e) => setContexto(e.target.value)}
                    disabled={!!plantilla}
                    className="h-9 w-full rounded-md border bg-background px-3 text-sm">
              {Object.keys(contextos).map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        </div>

        <div>
          <Label htmlFor="pl-asunto">Asunto</Label>
          <Input id="pl-asunto" value={asunto} onChange={(e) => setAsunto(e.target.value)} />
        </div>

        <div>
          <Label htmlFor="pl-cuerpo">Mensaje</Label>
          <Textarea id="pl-cuerpo" rows={10} value={cuerpo}
                    onChange={(e) => setCuerpo(e.target.value)}
                    placeholder="Hola {{nombre_empleado}}, ..." />
          <p className="mt-1 text-xs text-muted-foreground">
            Podés usar <strong>**negrita**</strong>, *itálica*, listas con “- ” y links
            [texto](https://…).
          </p>
        </div>

        <div>
          <Label>Variables disponibles</Label>
          <PlantillaVariables variables={contextos[contexto] ?? []} onInsertar={insertar} />
        </div>

        {preview && <PlantillaPreview preview={preview} />}

        {error && <p className="text-sm text-destructive">{error}</p>}

        <DialogFooter>
          <Button variant="outline" onClick={verPreview}>Previsualizar</Button>
          <Button onClick={guardar} disabled={guardando || !clave || !asunto || !cuerpo}>
            {guardando ? "Guardando…" : "Guardar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

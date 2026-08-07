"use client"

import { Button } from "@/components/ui/button"

/**
 * El contenido del pie: el aviso de modo consolidado y los dos botones.
 *
 * Exportado —y separado del `<DialogFooter>` que lo envuelve— para poder testearlo: `Dialog` de
 * base-ui monta por portal y vitest corre sin jsdom, así que renderizar el modal entero devuelve
 * string vacío. Acá vive la única lógica del pie (cuándo se puede guardar), que es lo que hay
 * que poder afirmar.
 *
 * 🔴 EL AVISO VA ACÁ, PEGADO AL BOTÓN QUE DESHABILITA, y no arriba de todo: un cartel en el
 * encabezado de un modal largo queda fuera de la vista justo cuando el usuario está mirando el
 * botón que no responde.
 */
export function AccionesDelPie({ sinEmpresa, guardando, valores, onGuardar, onPreview }: {
  sinEmpresa: boolean
  guardando: boolean
  valores: { clave: string; asunto: string; cuerpo: string }
  onGuardar: () => void
  onPreview: () => void
}) {
  const incompleto = !valores.clave || !valores.asunto || !valores.cuerpo
  return (
    <>
      {sinEmpresa && (
        <p className="text-sm text-muted-foreground sm:self-center">
          Para guardar, elegí una empresa en el selector de arriba a la izquierda.
        </p>
      )}
      <div className="flex flex-col-reverse gap-2 sm:flex-row">
        {/* Previsualizar NO se deshabilita: en consolidado el render funciona igual y es la
            mitad útil de la pantalla. Bloquear el modal entero le sacaría eso también. */}
        <Button variant="outline" onClick={onPreview}>Previsualizar</Button>
        <Button onClick={onGuardar} disabled={sinEmpresa || guardando || incompleto}>
          {guardando ? "Guardando…" : "Guardar"}
        </Button>
      </div>
    </>
  )
}

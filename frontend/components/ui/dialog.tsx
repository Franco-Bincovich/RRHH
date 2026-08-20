"use client"

import * as React from "react"
import { Dialog as DialogPrimitive } from "@base-ui/react/dialog"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { XIcon } from "lucide-react"

import {
  CLASES_CUERPO, CLASES_POPUP, CLASES_SCRIM_FORMULARIO, PATRON_FORMULARIO,
} from "@/components/ui/dialogClases"
// `partirHijos` los compara por identidad, así que hacen falta como VALOR, no solo re-exportados.
import { DialogFooter, DialogHeader } from "@/components/ui/dialogPartes"

// Re-export por compatibilidad: los importadores (y el test del primitivo) las piden desde acá.
export { CLASES_CUERPO, CLASES_POPUP } from "@/components/ui/dialogClases"
export { DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialogPartes"

function Dialog({ ...props }: DialogPrimitive.Root.Props) {
  return <DialogPrimitive.Root data-slot="dialog" {...props} />
}

function DialogTrigger({ ...props }: DialogPrimitive.Trigger.Props) {
  return <DialogPrimitive.Trigger data-slot="dialog-trigger" {...props} />
}

function DialogPortal({ ...props }: DialogPrimitive.Portal.Props) {
  return <DialogPrimitive.Portal data-slot="dialog-portal" {...props} />
}

function DialogClose({ ...props }: DialogPrimitive.Close.Props) {
  return <DialogPrimitive.Close data-slot="dialog-close" {...props} />
}

function DialogOverlay({
  className,
  ...props
}: DialogPrimitive.Backdrop.Props) {
  return (
    <DialogPrimitive.Backdrop
      data-slot="dialog-overlay"
      className={cn(
        "fixed inset-0 isolate z-50 bg-black/10 duration-100 supports-backdrop-filter:backdrop-blur-xs data-open:animate-in data-open:fade-in-0 data-closed:animate-out data-closed:fade-out-0",
        className
      )}
      {...props}
    />
  )
}

/**
 * Separa los hijos en encabezado / cuerpo / pie, para que el diálogo pueda fijar los dos
 * extremos y scrollear solo el medio.
 *
 * 🔴 SE HACE ACÁ Y NO PIDIÉNDOLE UN `<DialogBody>` A CADA MODAL porque son 47 y el problema
 * los afecta a todos: un modal más alto que la pantalla se desbordaba por arriba Y por abajo
 * (el popup está centrado con `-translate-y-1/2`), así que se perdían el título y los botones
 * a la vez. Pedir un wrapper nuevo arregla el modal que se toca y deja rotos los otros 46.
 *
 * El criterio es el TIPO del elemento, no un `data-slot` ni la posición: `c.type === DialogHeader`
 * no se puede escribir mal ni depende de que el header vaya primero. Verificado que en los modales
 * del repo el header y el footer son hijos DIRECTOS de `DialogContent` — si alguno los anidara en
 * un `<form>` o un `<div>`, caerían en el cuerpo y volverían a scrollear (no rompe, degrada al
 * comportamiento anterior).
 */
export function partirHijos(children: React.ReactNode) {
  const todos = React.Children.toArray(children)
  const es = (c: React.ReactNode, tipo: React.ElementType) =>
    React.isValidElement(c) && c.type === tipo
  return {
    header: todos.filter((c) => es(c, DialogHeader)),
    footer: todos.filter((c) => es(c, DialogFooter)),
    cuerpo: todos.filter((c) => !es(c, DialogHeader) && !es(c, DialogFooter)),
  }
}

function DialogContent({
  className,
  children,
  showCloseButton = true,
  patron,
  ...props
}: DialogPrimitive.Popup.Props & {
  showCloseButton?: boolean
  /** Patrón "Modal de formulario" del sistema de diseño. Opt-in — ver `dialogClases.ts`. */
  patron?: "formulario"
}) {
  const { header, footer, cuerpo } = partirHijos(children)
  const esFormulario = patron === "formulario"
  return (
    <DialogPortal>
      {/* El scrim viaja con el patrón: el vidrio del popup y el 35% del fondo son una sola
          decisión, y separarlos deja modales de vidrio sobre un scrim del 10%, que es cuando el
          vidrio deja de leerse como "esto está adelante". */}
      <DialogOverlay className={esFormulario ? CLASES_SCRIM_FORMULARIO : undefined} />
      <DialogPrimitive.Popup
        data-slot="dialog-content"
        data-patron={patron}
        className={cn(CLASES_POPUP, esFormulario && PATRON_FORMULARIO, className)}
        {...props}
      >
        {header}
        {cuerpo.length > 0 && (
          <div data-slot="dialog-body" className={CLASES_CUERPO}>
            {cuerpo}
          </div>
        )}
        {footer}
        {showCloseButton && (
          <DialogPrimitive.Close
            data-slot="dialog-close"
            render={
              <Button
                variant="ghost"
                className="absolute top-2 right-2"
                size="icon-sm"
              />
            }
          >
            <XIcon
            />
            <span className="sr-only">Close</span>
          </DialogPrimitive.Close>
        )}
      </DialogPrimitive.Popup>
    </DialogPortal>
  )
}

export {
  Dialog,
  DialogClose,
  DialogContent,
  DialogOverlay,
  DialogPortal,
  DialogTrigger,
}

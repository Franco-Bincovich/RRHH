"use client"

import * as React from "react"
import { Dialog as DialogPrimitive } from "@base-ui/react/dialog"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { XIcon } from "lucide-react"

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
 * 🔴 SE HACE ACÁ Y NO PIDIÉNDOLE UN `<DialogBody>` A CADA MODAL porque son 35 y el problema
 * los afecta a todos: un modal más alto que la pantalla se desbordaba por arriba Y por abajo
 * (el popup está centrado con `-translate-y-1/2`), así que se perdían el título y los botones
 * a la vez. Pedir un wrapper nuevo arregla el modal que se toca y deja rotos los otros 34.
 *
 * El criterio es el TIPO del elemento, no un `data-slot` ni la posición: `c.type === DialogHeader`
 * no se puede escribir mal ni depende de que el header vaya primero. Verificado que en los 35
 * modales del repo el header y el footer son hijos DIRECTOS de `DialogContent` — si alguno los
 * anidara en un `<form>` o un `<div>`, caerían en el cuerpo y volverían a scrollear (no rompe,
 * degrada al comportamiento anterior).
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

/**
 * Las clases del popup y del cuerpo, exportadas para poder testearlas.
 *
 * ⚠️ Están afuera del JSX SOLO por eso: `Dialog` de base-ui monta por PORTAL, y vitest corre sin
 * jsdom, así que `renderToStaticMarkup(<Dialog open>…)` devuelve string VACÍO — no hay forma de
 * afirmar el DOM del diálogo en esta suite. Sacando estas dos constantes, lo que sí queda
 * cubierto es la lógica que puede regresionar (el reparto de hijos) y las clases de las que
 * depende el scroll. Lo que NO queda cubierto es el armado final del JSX; son las 3 líneas de
 * abajo y `partirHijos` garantiza que el footer nunca esté en `cuerpo`, que es lo que haría
 * que se scrollee.
 */
export const CLASES_POPUP =
  // `flex flex-col` reemplaza al `grid` de shadcn: para una sola columna se ven igual, pero flex
  // es lo que permite que el cuerpo ENCOJA (flex-shrink) y los extremos no.
  // `max-h` con `dvh` y NO `vh`: en mobile `vh` cuenta la barra de direcciones aunque esté
  // desplegada, así que el modal queda más alto que lo que se ve. Las 2rem son el aire de 1rem
  // arriba y 1rem abajo.
  "fixed top-1/2 left-1/2 z-50 flex max-h-[calc(100dvh-2rem)] w-full max-w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 flex-col gap-4 rounded-xl bg-popover p-4 text-sm text-popover-foreground ring-1 ring-foreground/10 duration-100 outline-none sm:max-w-sm data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95 " +
  // `shrink-0` a los extremos por SELECTOR y no envolviéndolos en un div: sin él, flex los achica
  // a ellos antes que al cuerpo y el título se aplasta en vez de scrollear la parte larga. Va así
  // para no meter un nodo nuevo entre el popup y el footer — el footer sangra hasta el borde con
  // `-mx-4 -mb-4`, que se miden contra su padre.
  "[&>[data-slot=dialog-footer]]:shrink-0 [&>[data-slot=dialog-header]]:shrink-0"

export const CLASES_CUERPO =
  // `min-h-0` es lo que hace que el scroll ocurra: un hijo flex no baja de su tamaño de contenido
  // sin esto, así que sin él el cuerpo empuja y el modal se desborda igual que antes. `gap-4`
  // repone la separación que daba el contenedor: al envolver los hijos, dejaron de ser hermanos
  // del `gap` de arriba.
  "flex min-h-0 flex-col gap-4 overflow-y-auto"

function DialogContent({
  className,
  children,
  showCloseButton = true,
  ...props
}: DialogPrimitive.Popup.Props & {
  showCloseButton?: boolean
}) {
  const { header, footer, cuerpo } = partirHijos(children)
  return (
    <DialogPortal>
      <DialogOverlay />
      <DialogPrimitive.Popup
        data-slot="dialog-content"
        className={cn(CLASES_POPUP, className)}
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

function DialogHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="dialog-header"
      className={cn("flex flex-col gap-2", className)}
      {...props}
    />
  )
}

function DialogFooter({
  className,
  showCloseButton = false,
  children,
  ...props
}: React.ComponentProps<"div"> & {
  showCloseButton?: boolean
}) {
  return (
    <div
      data-slot="dialog-footer"
      className={cn(
        "-mx-4 -mb-4 flex flex-col-reverse gap-2 rounded-b-xl border-t bg-muted/50 p-4 sm:flex-row sm:justify-end",
        className
      )}
      {...props}
    >
      {children}
      {showCloseButton && (
        <DialogPrimitive.Close render={<Button variant="outline" />}>
          Close
        </DialogPrimitive.Close>
      )}
    </div>
  )
}

function DialogTitle({ className, ...props }: DialogPrimitive.Title.Props) {
  return (
    <DialogPrimitive.Title
      data-slot="dialog-title"
      className={cn(
        "font-heading text-base leading-none font-medium",
        className
      )}
      {...props}
    />
  )
}

function DialogDescription({
  className,
  ...props
}: DialogPrimitive.Description.Props) {
  return (
    <DialogPrimitive.Description
      data-slot="dialog-description"
      className={cn(
        "text-sm text-muted-foreground *:[a]:underline *:[a]:underline-offset-3 *:[a]:hover:text-foreground",
        className
      )}
      {...props}
    />
  )
}

export {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogOverlay,
  DialogPortal,
  DialogTitle,
  DialogTrigger,
}

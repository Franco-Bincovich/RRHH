"use client"

import * as React from "react"
import { Dialog as DialogPrimitive } from "@base-ui/react/dialog"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

/**
 * Los subcomponentes PRESENTACIONALES del diálogo: encabezado, pie, título y descripción.
 *
 * Salieron de `dialog.tsx` cuando el pie sumó el aviso de impacto del patrón de modal de
 * formulario. El corte tiene una condición que hay que respetar: **este archivo no importa nada
 * de `dialog.tsx`**. Es al revés — `partirHijos` compara contra `DialogHeader`/`DialogFooter` y
 * los toma de acá. Invertir la dirección crea un ciclo entre los dos módulos.
 *
 * `dialog.tsx` los re-exporta, así que los 47 modales siguen importando todo desde
 * `@/components/ui/dialog`.
 */

export function DialogHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="dialog-header"
      className={cn("flex flex-col gap-2", className)}
      {...props}
    />
  )
}

export function DialogFooter({
  className,
  showCloseButton = false,
  aviso,
  children,
  ...props
}: React.ComponentProps<"div"> & {
  showCloseButton?: boolean
  /**
   * Aviso de impacto, ámbar, **sobre** los botones (§3: "los avisos de impacto van en ámbar sobre
   * el pie"). Va acá y no al final del cuerpo por una razón concreta: el cuerpo SCROLLEA, así que
   * un aviso puesto ahí desaparece justo en el modal largo, que es donde más falta hace. El pie
   * es `shrink-0` y siempre se ve.
   * Sin `aviso`, el markup del pie es EXACTAMENTE el de antes — los otros 46 modales no se enteran.
   */
  aviso?: React.ReactNode
}) {
  const botones = (
    <>
      {children}
      {showCloseButton && (
        <DialogPrimitive.Close render={<Button variant="outline" />}>
          Close
        </DialogPrimitive.Close>
      )}
    </>
  )

  const FILA = "flex flex-col-reverse gap-2 sm:flex-row sm:justify-end"
  const CAJA = "-mx-4 -mb-4 rounded-b-xl border-t bg-muted/50 p-4"

  if (!aviso) {
    return (
      <div data-slot="dialog-footer" className={cn(CAJA, FILA, className)} {...props}>
        {botones}
      </div>
    )
  }

  return (
    <div data-slot="dialog-footer" className={cn(CAJA, "flex flex-col gap-3", className)} {...props}>
      {aviso}
      <div className={FILA}>{botones}</div>
    </div>
  )
}

export function DialogTitle({ className, ...props }: DialogPrimitive.Title.Props) {
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

export function DialogDescription({
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

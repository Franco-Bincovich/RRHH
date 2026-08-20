"use client"

import * as React from "react"

import { cn } from "@/lib/utils"
import { PATRON_DATOS } from "@/components/ui/tablePatron"

/**
 * 🔴 `patron="datos"` ES OPT-IN, Y ESO ES EL ALCANCE, NO UNA DUDA. Este primitivo tiene **31
 * consumidores**: escribir el patrón de tabla del sistema de diseño en las clases base habría
 * cambiado la densidad, el encabezado y el hover de 31 pantallas de una. Sin `patron`, una tabla
 * sale exactamente igual que antes — no se le agrega una sola clase.
 * El qué y el porqué, completos, en `components/ui/tablePatron.ts`.
 */

function Table({ className, patron, ...props }: React.ComponentProps<"table"> & { patron?: "datos" }) {
  return (
    <div
      data-slot="table-container"
      /*
       * 🔴 EL `pr-0.5` ES EL QUE EVITA EL SCROLL HORIZONTAL DEL HOVER, no es un margen estético.
       * La tabla es `w-full`: una fila desplazada 2px a la derecha termina 2px afuera del
       * contenedor, y como el contenedor es `overflow-x-auto` eso aparece como una barra de
       * scroll horizontal que va y viene al pasar el mouse por las filas. Con 2px de canaleta
       * (0.5 = 2px) la tabla mide 2px menos y el desplazamiento cae justo adentro.
       */
      className={cn("relative w-full overflow-x-auto", patron === "datos" && "pr-0.5")}
    >
      <table
        data-slot="table"
        data-patron={patron}
        className={cn("w-full caption-bottom text-sm", patron === "datos" && PATRON_DATOS, className)}
        {...props}
      />
    </div>
  )
}

function TableHeader({ className, ...props }: React.ComponentProps<"thead">) {
  return (
    <thead
      data-slot="table-header"
      className={cn("[&_tr]:border-b", className)}
      {...props}
    />
  )
}

function TableBody({ className, ...props }: React.ComponentProps<"tbody">) {
  return (
    <tbody
      data-slot="table-body"
      className={cn("[&_tr:last-child]:border-0", className)}
      {...props}
    />
  )
}

function TableFooter({ className, ...props }: React.ComponentProps<"tfoot">) {
  return (
    <tfoot
      data-slot="table-footer"
      className={cn(
        "border-t bg-muted/50 font-medium [&>tr]:last:border-b-0",
        className
      )}
      {...props}
    />
  )
}

function TableRow({ className, ...props }: React.ComponentProps<"tr">) {
  return (
    <tr
      data-slot="table-row"
      className={cn(
        "border-b transition-colors hover:bg-muted/50 has-aria-expanded:bg-muted/50 data-[state=selected]:bg-muted",
        className
      )}
      {...props}
    />
  )
}

function TableHead({ className, ...props }: React.ComponentProps<"th">) {
  return (
    <th
      data-slot="table-head"
      className={cn(
        "h-10 px-2 text-left align-middle font-medium whitespace-nowrap text-foreground [&:has([role=checkbox])]:pr-0",
        className
      )}
      {...props}
    />
  )
}

function TableCell({ className, ...props }: React.ComponentProps<"td">) {
  return (
    <td
      data-slot="table-cell"
      className={cn(
        "p-2 align-middle whitespace-nowrap [&:has([role=checkbox])]:pr-0",
        className
      )}
      {...props}
    />
  )
}

function TableCaption({
  className,
  ...props
}: React.ComponentProps<"caption">) {
  return (
    <caption
      data-slot="table-caption"
      className={cn("mt-4 text-sm text-muted-foreground", className)}
      {...props}
    />
  )
}

export {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
}

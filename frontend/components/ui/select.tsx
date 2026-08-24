"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { FieldError } from "@/components/ui/FieldError"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"

/**
 * El `<select>` del producto. **Envuelve el nativo, no lo reemplaza.**
 *
 * 🔴 POR QUÉ NATIVO Y NO UN DROPDOWN PROPIO — decisión de arquitectura, no se reabre acá.
 * En mobile el `<select>` nativo abre el picker del sistema operativo, que es mejor que cualquier
 * cosa que construyamos; el teclado (tipear para saltar a una opción) y el lector de pantalla
 * funcionan gratis; y la regla `.dark select option` de `globals.css` —que es la que hace legible
 * el popup en modo oscuro— sigue valiendo sin tocar una línea. Un dropdown custom perdería las
 * cuatro cosas y habría que reconstruirlas.
 *
 * 🔴 POR QUÉ EXISTE. Antes de este archivo había **81 `<select>` en 53 archivos** vestidos con
 * constantes de estilo copiadas entre archivos: `SELECT_CLASS` declarada en **14 archivos con 10
 * valores distintos**, `SEL` en 9 con 3, `SELECT_CLS` en 3 con 3, más 17 selects con la clase
 * escrita inline. Casi ninguna diferencia era una decisión: eran copias que driftearon. Dos
 * selects al lado en la misma pantalla podían tener distinto alto, distinto radio y distinto
 * anillo de foco (`ring-2` contra `ring-3`, `ring-ring` contra `ring-ring/50`).
 *
 * ⚠️ **`size` NO es el atributo nativo.** En HTML, `<select size={n}>` es la cantidad de filas
 * visibles. Acá `size` es la variante de alto, como en `components/ui/button.tsx`, y el atributo
 * nativo queda fuera del tipo a propósito (`Omit<..., "size">`): no lo usa ningún select del repo
 * —verificado— y dejar los dos significados sobre el mismo nombre es una trampa.
 */

const selectVariants = cva(
  // Base: el mismo idioma visual que `components/ui/input.tsx`, que es el primitivo hermano y el
  // que marca la convención (39 consumidores). Foco con `outline-none` SIEMPRE acompañado de un
  // `focus-visible:ring` — nunca `outline-none` solo, que deja el control sin foco visible para
  // quien navega con teclado. `text-foreground` va explícito porque un `<select>` no siempre
  // hereda el color del texto: varios navegadores le aplican el color del control del sistema.
  "w-full min-w-0 rounded-lg border border-input bg-transparent text-sm text-foreground transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-input/50 disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 dark:bg-input/30 dark:disabled:bg-input/80 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40",
  {
    variants: {
      /**
       * Los dos tamaños de `docs/SISTEMA-DE-DISENO.md` §3: **30px en la barra de filtros** y
       * **34px en los formularios**. Son dos, no uno, y por eso son variante y no un `className`
       * suelto en cada pantalla.
       *
       * 🔴 EL ALTO ES 44px HASTA EL BREAKPOINT `md`, Y ESO ES EL TOUCH TARGET.
       * Un control táctil necesita 44px de área tocable. En un `<select>` nativo esa área **es**
       * la caja del control: no hay forma de agrandarla con padding sin agrandar la caja, porque
       * el borde envuelve al padding. La única alternativa sería tapar el select con una capa
       * invisible de 44px y dibujar la caja de 30px en un `<div>` de atrás — y eso es reconstruir
       * el control, o sea justo lo que la decisión de arriba descarta.
       * Por eso el corte es por ANCHO DE PANTALLA y no por dispositivo: abajo de `md` (donde se
       * usa con el dedo) el control mide 44px; de `md` para arriba toma la altura densa que pide
       * el sistema de diseño. Es además lo que el repo ya venía haciendo a mano en la barra de
       * filtros (`min-h-11`) y en los modales de proyectos (`min-h-[2.75rem]`).
       */
      size: {
        sm: "h-11 px-2.5 md:h-[30px]",
        md: "h-11 px-3 md:h-[34px]",
      },
    },
    defaultVariants: { size: "md" },
  },
)

type SelectProps = Omit<React.ComponentProps<"select">, "size"> &
  VariantProps<typeof selectVariants> & {
    /** Etiqueta opcional. Si va, se asocia por `htmlFor` con el id del control. */
    label?: React.ReactNode
    /** Mensaje de error. Si va, marca `aria-invalid` y se anuncia por `aria-describedby`. */
    error?: string
  }

function Select({
  className,
  size,
  label,
  error,
  id,
  children,
  "aria-invalid": ariaInvalid,
  "aria-describedby": ariaDescribedBy,
  ...props
}: SelectProps) {
  // `useId` da un id estable entre servidor y cliente. Solo se usa si hace falta asociar algo:
  // un select sin label ni error no necesita id, y ponerle uno inventado ensucia el DOM.
  const generado = React.useId()
  const selectId = id ?? (label || error ? generado : undefined)
  const errorId = error && selectId ? `${selectId}-error` : undefined
  const describedBy = [ariaDescribedBy, errorId].filter(Boolean).join(" ") || undefined

  const control = (
    <select
      id={selectId}
      data-slot="select"
      aria-invalid={error ? true : ariaInvalid}
      aria-describedby={describedBy}
      className={cn(selectVariants({ size }), className)}
      {...props}
    >
      {children}
    </select>
  )

  // 🔴 SIN label NI error DEVUELVE EL `<select>` PELADO, sin ningún `<div>` alrededor.
  // No es una optimización: es lo que lo hace un reemplazo directo. De los 81 selects migrados,
  // la enorme mayoría ya vive adentro de un `<label className="flex flex-col gap-1.5">` propio o
  // es hijo directo de un grid/flex de la barra de filtros. Envolverlos siempre metería un nivel
  // de caja que rompería esos layouts uno por uno, y el componente pasaría de "cambiar la clase"
  // a "rehacer la pantalla".
  if (!label && !error) return control

  return (
    <div className="flex w-full flex-col gap-1.5">
      {label ? <Label htmlFor={selectId}>{label}</Label> : null}
      {control}
      {/*
       * El mensaje lo pinta `FieldError`, el primitivo único del segundo nivel de validación
       * (11px, §3): así este select no tiene su propia copia del tamaño. El `role="alert"` lo
       * pone el primitivo —para que el lector de pantalla lo anuncie al aparecer— y el `id` se
       * le pasa para colgarlo del `aria-describedby` del control, que lo lee al enfocarlo. Los
       * dos hacen falta: cubren el error que aparece con el foco en otro lado y el que ya
       * estaba cuando llegás al campo.
       */}
      <FieldError id={errorId}>{error}</FieldError>
    </div>
  )
}

export { Select, selectVariants }

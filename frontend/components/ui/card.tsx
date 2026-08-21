"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/**
 * La superficie del producto: paneles, secciones y tarjetas.
 *
 * 🔴 EL TRATAMIENTO ES EL DE `docs/SISTEMA-DE-DISENO.md` §2, Y ES UNA DECISIÓN TOMADA, NO UN
 * DEFAULT: **opaca, sin transparencia ni desenfoque.** La elevación la da un borde de 1px más un
 * escalón de luminosidad (`bg-card` contra `--background`), nunca una sombra difusa. El documento
 * cuenta por qué se probó con vidrio y se descartó: el texto secundario perdía casi un punto de
 * contraste (4,92 contra 5,49) y el límite entre tarjetas quedaba difuso justo donde hay que
 * comparar muchas de un vistazo. **El vidrio queda SOLO para el sidebar y los modales**, donde
 * comunica "esto está adelante"; en una grilla no comunica nada y cuesta rendimiento.
 *
 * 🔴 `interactive` NO ES DECORATIVO — ES LA DIFERENCIA ENTRE "SE PUEDE APRETAR" Y "NO".
 * El movimiento al apuntar (3px de elevación, borde iluminado, 160ms) es lo que le dice al
 * usuario que la superficie es un control. **Una card informativa no se mueve**, y ponerle hover
 * "porque queda lindo" promete un click que no existe. Por eso es una prop explícita y no algo
 * que la card haga siempre: la mayoría de las superficies del producto son paneles de lectura.
 *
 * ⚠️ Para las superficies que NO son un `<div>` —`<section aria-label>`, `<form>`, `<li>`,
 * `<button>`— está la prop `as`, y para los casos que no encajan está `cardVariants` exportado,
 * como `buttonVariants` en `button.tsx`.
 */
/*
 * `[--indicio-fondo:var(--card)]` no pinta nada acá: DECLARA, para todo el subárbol, con qué
 * color tapa `.scroll-x-indicio` (`app/utilidades.css`) su sombra de scroll. Una tabla adentro de
 * una tarjeta hereda el valor y su indicio deja de dibujar una franja del color de la página
 * sobre el borde de la tarjeta. La variable viaja por herencia de CSS: cero JavaScript y cero
 * props nuevas en los consumidores.
 */
const cardVariants = cva("rounded-xl border bg-card [--indicio-fondo:var(--card)]", {
  variants: {
    /**
     * Los dos escalones que el repo usaba de verdad. `lg` es el de los paneles (18 usos con el
     * literal `p-4 md:p-6`), `sm` el de las tarjetas de KPI y de listado.
     *
     * ⚠️ `sm` unificó dos formas que convivían: `p-4 md:p-5` y un `p-5` fijo. De `md` para arriba
     * son idénticas; abajo de `md` el `p-5` fijo daba 4px más. Se eligió la responsive porque en
     * mobile el aire de más se paga en pantalla, y mantener las dos habría sido una variante que
     * nadie puede explicar.
     */
    padding: {
      none: "",
      sm: "p-4 md:p-5",
      lg: "p-4 md:p-6",
    },
    /** Solo si la card ES un control. Ver el bloque de arriba. */
    interactive: {
      true:
        "cursor-pointer transition-all duration-[160ms] hover:-translate-y-[3px] " +
        "hover:border-primary/40 hover:shadow-md focus-visible:outline-none " +
        "focus-visible:ring-3 focus-visible:ring-ring/50",
      false: "",
    },
  },
  defaultVariants: { padding: "lg", interactive: false },
})

type CardProps<T extends React.ElementType> = {
  /** El elemento a renderizar. `<section>` cuando la superficie tiene `aria-label`, etc. */
  as?: T
} & VariantProps<typeof cardVariants> &
  Omit<React.ComponentPropsWithoutRef<T>, "as" | "className" | keyof VariantProps<typeof cardVariants>> & {
    className?: string
  }

function Card<T extends React.ElementType = "div">({
  as,
  padding,
  interactive,
  className,
  ...props
}: CardProps<T>) {
  const Componente = (as ?? "div") as React.ElementType
  return (
    <Componente
      data-slot="card"
      className={cn(cardVariants({ padding, interactive }), className)}
      {...props}
    />
  )
}

export { Card, cardVariants }

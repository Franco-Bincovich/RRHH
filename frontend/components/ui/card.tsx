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
 * 🔴 `interactive` DISTINGUE **TARJETA** DE **PANEL**, no "clickeable" de "no clickeable".
 * El movimiento al apuntar (3px de elevación, borde iluminado, 160ms) lo lleva TODA TARJETA:
 * las de KPI, perfil, proyecto, plantilla, reporte, proceso y las del organigrama, se puedan
 * apretar o no. Lo que NO lo lleva es un PANEL —una sección de lectura que ocupa el ancho de la
 * pantalla (`as="section"`, el historial, un formulario)—: ahí el movimiento no significa nada
 * porque no hay nada de qué distinguirlo.
 *
 * ⚠️ **Esto REVIERTE la decisión anterior**, que era "una card informativa no se mueve" y dejaba
 * sin movimiento a perfiles, reportes y plantillas. La regla nueva la fijó Franco el 23/8/2026 y
 * es de producto, no de implementación: en una grilla, que unas tarjetas respondan y otras no se
 * lee como que algunas están deshabilitadas. No volver a "arreglarlo" sin preguntar.
 *
 * 🔑 El movimiento vive ACÁ y en ningún otro lado: `decisionesVisuales.test.ts` rojea si alguien
 * lo reescribe a mano en un componente. Una tarjeta que no use este primitivo se queda sin él.
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

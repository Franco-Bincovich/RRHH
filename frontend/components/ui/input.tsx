import * as React from "react"
import { Input as InputPrimitive } from "@base-ui/react/input"

import { cn } from "@/lib/utils"

/**
 * 🔴 EL ALTO ES 44px HASTA EL BREAKPOINT `md`, Y ESO ES EL TOUCH TARGET.
 *
 * Es la MISMA regla que `components/ui/select.tsx` ya aplicaba, escrita ahí con todo su porqué:
 * abajo de `md` —donde el control se usa con el dedo— mide 44px; de `md` para arriba toma la
 * altura densa de 32px que pide `docs/SISTEMA-DE-DISENO.md` §3. El corte es por ANCHO DE PANTALLA
 * y no por dispositivo.
 *
 * 🔴 POR QUÉ APARECE ACÁ RECIÉN AHORA, y por qué era un bug y no una omisión estética. El select
 * ya medía 44px en mobile y el input 32px, así que **en el mismo formulario, dos controles
 * hermanos tenían alturas distintas en el teléfono**. Se ve en `/horas`, la pantalla que un
 * colaborador usa desde el celular para cargar sus horas: "Fecha" y "Horas" (inputs, 32px)
 * conviven en la misma grilla con "Modalidad" y "Cliente" (selects, 44px). El comentario de
 * `select.tsx` llama a este archivo "el primitivo hermano y el que marca la convención" — la
 * convención estaba escrita allá y faltaba acá.
 *
 * ⚠️ Los consumidores que ya forzaban 44px a mano (`min-h-[2.75rem]` en `/login` y en el campo de
 * contraseña) NO cambian: `min-height` le gana a `height`, así que siguen midiendo 44px también
 * en escritorio. No se les sacó la clase en esta tanda para no mezclar dos cambios; el día que se
 * limpien, van a tomar los 32px densos de `md` para arriba.
 */
function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <InputPrimitive
      type={type}
      data-slot="input"
      className={cn(
        "h-11 md:h-8 w-full min-w-0 rounded-lg border border-input bg-transparent px-2.5 py-1 text-base transition-colors outline-none file:inline-flex file:h-6 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-input/50 disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 md:text-sm dark:bg-input/30 dark:disabled:bg-input/80 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40",
        className
      )}
      {...props}
    />
  )
}

export { Input }

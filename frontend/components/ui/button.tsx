import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-lg border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap transition-all outline-none select-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 active:not-aria-[haspopup]:translate-y-px disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground [a]:hover:bg-primary/80",
        outline:
          "border-border bg-background hover:bg-muted hover:text-foreground aria-expanded:bg-muted aria-expanded:text-foreground dark:border-input dark:bg-input/30 dark:hover:bg-input/50",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/80 aria-expanded:bg-secondary aria-expanded:text-secondary-foreground",
        ghost:
          "hover:bg-muted hover:text-foreground aria-expanded:bg-muted aria-expanded:text-foreground dark:hover:bg-muted/50",
        destructive:
          "bg-destructive/10 text-destructive hover:bg-destructive/20 focus-visible:border-destructive/40 focus-visible:ring-destructive/20 dark:bg-destructive/20 dark:hover:bg-destructive/30 dark:focus-visible:ring-destructive/40",
        link: "text-primary underline-offset-4 hover:underline",
      },
      /**
       * 🔴 TODO BOTÓN MIDE 44px HASTA EL BREAKPOINT `md`, Y ARRIBA DE `md` EL TAMAÑO DEL DISEÑO.
       * Es la MISMA regla que `components/ui/select.tsx` (`h-11 md:h-[30px]`), aplicada acá el
       * 25/8/2026 al medir que **97 controles del producto quedaban por debajo del mínimo táctil
       * en 8 pantallas**: los de encabezado ya median 44 —porque cada uno traía un `min-h-11`
       * escrito a mano— pero los de fila median 32 y "Ver detalle" de /auditoria, 24.
       *
       * 🔑 EL CORTE ES POR ANCHO DE PANTALLA Y NO POR DISPOSITIVO, igual que en el select: abajo
       * de `md` es donde se usa con el dedo. Y **no agranda la caja en desktop**, que es la otra
       * mitad del requisito: `md:h-8` devuelve exactamente el alto que el sistema de diseño pide,
       * así que la densidad de una tabla de 46px de fila no cambia una sola línea.
       *
       * ⚠️ POR QUÉ NO ALCANZABA CON EL PADDING. En un `<button>` sí se podría agrandar el área
       * tocable con padding, pero eso mueve todo lo que tiene alrededor —en una celda de tabla,
       * empuja la fila— y deja la caja visible de un tamaño y el área de otro sólo en algunos
       * botones. Con la altura, el primitivo decide las dos cosas en un solo lugar.
       *
       * ⚠️ Los `min-h-11` que ya existen en los consumidores NO se sacaron en esta tanda: hoy son
       * redundantes abajo de `md` y siguen forzando 44px ARRIBA de `md`, que es lo que esos
       * botones ya hacían (son acciones principales de encabezado). Sacarlos cambiaría el desktop,
       * y eso es una decisión de diseño, no un efecto colateral del touch target.
       */
      size: {
        default:
          "h-11 md:h-8 gap-1.5 px-2.5 has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2",
        xs: "h-11 md:h-6 gap-1 rounded-[min(var(--radius-md),10px)] px-2 text-xs in-data-[slot=button-group]:rounded-lg has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-11 md:h-7 gap-1 rounded-[min(var(--radius-md),12px)] px-2.5 text-[0.8rem] in-data-[slot=button-group]:rounded-lg has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_svg:not([class*='size-'])]:size-3.5",
        lg: "h-11 md:h-9 gap-1.5 px-2.5 has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2",
        // Los `icon*` llevan `size-*`, que fija alto Y ancho: un botón de sólo ícono necesita las
        // dos medidas para ser tocable, no sólo la altura.
        icon: "size-11 md:size-8",
        "icon-xs":
          "size-11 md:size-6 rounded-[min(var(--radius-md),10px)] in-data-[slot=button-group]:rounded-lg [&_svg:not([class*='size-'])]:size-3",
        "icon-sm":
          "size-11 md:size-7 rounded-[min(var(--radius-md),12px)] in-data-[slot=button-group]:rounded-lg",
        "icon-lg": "size-11 md:size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }

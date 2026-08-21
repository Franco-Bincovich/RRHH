"use client"

import * as React from "react"
import { Tabs as TabsPrimitive } from "@base-ui/react/tabs"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/**
 * Las solapas del producto. **Envuelven la `Tabs` de `@base-ui/react`**, igual que `input.tsx`
 * envuelve su `Input` y `button.tsx` su `Button`: es la convención del repo y acá además compra
 * lo que más caro sale escribir a mano — `role="tablist"/"tab"/"tabpanel"`, `aria-selected`,
 * `aria-controls`, el foco itinerante y la navegación con flechas (← → Home End).
 *
 * 🔴 POR QUÉ EXISTE. Había **diez barras de solapas en el repo, en dos familias visuales**, y
 * ninguna sabía de las otras:
 *   · **subrayado** (7): capacitaciones · comunicación · evaluaciones · inventario ·
 *     proyectos/[id] · empresas/[id] · objetivos/ObjetivosVistas
 *   · **píldora** (3): assessment y sucesión —las dos con un `TAB_CLASS` byte-idéntico declarado
 *     en dos archivos distintos— y organigrama, que se la reescribió a mano sin constante.
 * Las siete del subrayado tampoco eran iguales entre sí: una pinta el activo con `text-primary` y
 * otra con `text-foreground`, y solo una de las siete compensaba el borde con `-mb-px`.
 *
 * 🔑 LAS DOS FAMILIAS SE CONSERVAN COMO VARIANTE, no se unificaron a una. `docs/SISTEMA-DE-DISENO.md`
 * **no define solapas** —sus cinco patrones son filtros, tabla, ficha, modal y vacío/carga—, así
 * que elegir entre subrayado y píldora sería una decisión de diseño tomada desde el código. Lo que
 * sí se unificó es todo lo demás: alto, foco, estado deshabilitado y accesibilidad. El default es
 * `underline` porque es lo que usan 7 de las 10.
 *
 * ⚠️ EL SALTO DE 2px QUE ESTO ARREGLA DE PASO: seis de las siete del subrayado agregaban
 * `border-b-2` **solo al activo**, así que la fila entera se movía 2px al cambiar de solapa. Acá
 * el borde está siempre y es transparente cuando no está activo.
 */

type VarianteTabs = "underline" | "pill"

/** La variante viaja por contexto para que no haya que repetirla en cada `<Tab>`. */
const VarianteContexto = React.createContext<VarianteTabs>("underline")

/**
 * ⚠️ `overflow-x-auto` EN LA BARRA: con cuatro solapas a 390px la última se sale de la pantalla
 * —medido en /evaluaciones, "Importaciones" quedaba 121px afuera— y `flex` a secas la cortaba
 * contra el borde sin dejarla alcanzable. Scrollea en vez de envolver porque una barra de
 * solapas en dos renglones deja el subrayado del activo separado del contenido que gobierna.
 * La pista de que hay más a la derecha la pone `.scroll-x-indicio` (ver `app/globals.css`).
 */
const listaVariants = cva("scroll-x-indicio flex overflow-x-auto", {
  variants: {
    variant: {
      underline: "gap-1 border-b border-border",
      pill: "inline-flex gap-0.5 rounded-xl bg-muted p-1",
    },
  },
  defaultVariants: { variant: "underline" },
})

const tabVariants = cva(
  // El `min-h-11` hasta `md` es el mismo criterio que el `size="sm"` de `select.tsx`: 44px de
  // área táctil donde se toca con el dedo, la altura densa de `md` para arriba.
  "inline-flex min-h-11 items-center justify-center text-sm font-medium whitespace-nowrap " +
    "transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/50 " +
    "disabled:cursor-not-allowed disabled:opacity-50 md:min-h-0",
  {
    variants: {
      variant: {
        underline:
          "-mb-px border-b-2 border-transparent px-4 pb-3 pt-1 text-muted-foreground " +
          "hover:text-foreground data-active:border-primary data-active:text-primary",
        pill:
          "rounded-lg px-5 py-2 text-muted-foreground hover:text-foreground " +
          "data-active:bg-background data-active:text-foreground data-active:shadow-sm",
      },
    },
    defaultVariants: { variant: "underline" },
  },
)

/**
 * Raíz. Genérica en el valor para que el `onValueChange` devuelva la unión de la pantalla
 * (`"catalogo" | "asignaciones"`) y no un `string` que haya que castear en cada call site.
 */
function Tabs<T extends string>({
  value,
  defaultValue,
  onValueChange,
  variant = "underline",
  className,
  children,
}: {
  value?: T
  defaultValue?: T
  onValueChange?: (value: T) => void
  variant?: VarianteTabs
  className?: string
  children: React.ReactNode
}) {
  return (
    <VarianteContexto.Provider value={variant}>
      <TabsPrimitive.Root
        value={value}
        defaultValue={defaultValue}
        onValueChange={(v) => onValueChange?.(v as T)}
        className={className}
        data-slot="tabs"
      >
        {children}
      </TabsPrimitive.Root>
    </VarianteContexto.Provider>
  )
}

function TabList({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.List>) {
  const variant = React.useContext(VarianteContexto)
  return (
    <TabsPrimitive.List
      data-slot="tab-list"
      className={cn(listaVariants({ variant }), className)}
      {...props}
    />
  )
}

function Tab({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Tab> & VariantProps<typeof tabVariants>) {
  const variant = React.useContext(VarianteContexto)
  return (
    <TabsPrimitive.Tab
      data-slot="tab"
      className={cn(tabVariants({ variant }), className)}
      {...props}
    />
  )
}

/**
 * El panel de una solapa. Se usa aunque la pantalla ya decida el contenido con un `&&`: es lo que
 * ata el `role="tabpanel"` con su `tab` por `aria-controls`, que es la mitad de la accesibilidad
 * que un puñado de `<button>` sueltos nunca da.
 */
function TabPanel({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.Panel>) {
  return <TabsPrimitive.Panel data-slot="tab-panel" className={className} {...props} />
}

export { Tabs, TabList, Tab, TabPanel }

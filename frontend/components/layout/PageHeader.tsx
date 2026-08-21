import type { ReactNode } from "react"

/**
 * El encabezado de pantalla: título, bajada y la fila de acciones a la derecha. **77 consumidores.**
 *
 * 🔴 LA FILA DE ACCIONES ENVUELVE EN MOBILE, Y ESO ES UN ARREGLO MEDIDO, NO UN AJUSTE.
 * Hasta el 21/8/2026 el contenedor de `action` era `shrink-0` a secas. En la fila de `sm` para
 * arriba eso es correcto —lo que se achica es el título, no los botones— pero abajo de `sm` el
 * layout es una COLUMNA y `shrink-0` deja al hijo con su ancho de contenido: tres botones en una
 * línea de 431px adentro de una pantalla de 390. **El botón primario de la pantalla salía
 * cortado al medio**: en /empleados se leía "+ Nuevo em" (57px afuera), en /costos "Cargar
 * nómina" (122px), y también pasaba en /vacantes y /proyectos. Medido con el navegador a 390px,
 * no a ojo.
 *
 * Dos piezas, y hacen falta las dos:
 *   · `flex-wrap` en el contenedor — envuelve las acciones que llegan sueltas (un fragmento con
 *     dos botones).
 *   · `[&>*]:flex-wrap` — la mayoría de los consumidores pasa **un solo `<div className="flex
 *     gap-2">`** con los botones adentro (`EmpleadosAcciones`, `CostosAcciones`), así que sin
 *     esto el contenedor de acá tiene un único hijo que no envuelve y el problema queda igual.
 *     Es la misma técnica de descendiente que usa `tablePatron.ts`: el arreglo vive en el
 *     primitivo y ningún consumidor tiene que enterarse.
 *   · `sm:shrink-0` en vez de `shrink-0` — de `sm` para arriba manda lo de siempre.
 *
 * ⚠️ No toca el ALTO de ningún control: los botones siguen con su `min-h-11` (44px de área
 * táctil). Envolver mueve botones de línea, no los achica.
 */
interface PageHeaderProps {
  title: string
  description?: string
  action?: ReactNode
}

export function PageHeader({ title, description, action }: PageHeaderProps) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <h1 className="truncate text-2xl font-semibold tracking-tight text-foreground">
          {title}
        </h1>
        {description && (
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {action && (
        <div className="flex flex-wrap items-center gap-2 sm:shrink-0 [&>*]:flex-wrap">{action}</div>
      )}
    </div>
  )
}

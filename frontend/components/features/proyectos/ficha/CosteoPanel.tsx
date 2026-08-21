import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { Proyecto } from "@/types/proyecto"

const ARS = new Intl.NumberFormat("es-AR", {
  style: "currency",
  currency: "ARS",
  maximumFractionDigits: 0,
})

/**
 * El panel de costeo de la ficha de un proyecto: presupuesto, consumido, restante y la barra de
 * ejecución.
 *
 * Vivía adentro de `app/(dashboard)/proyectos/[id]/page.tsx`. Se sacó al agregar la barra de
 * identidad, que le sumaba renglones a una página que ya tenía dos componentes definidos adentro.
 *
 * 🔴 QUÉ DICE ESTE PANEL Y QUÉ DICE LA BARRA DE ARRIBA, para que no se pisen: la barra dice el
 * **presupuesto** (el tamaño del proyecto) y este dice el **consumo contra ese presupuesto**. El
 * presupuesto se repite acá a propósito, porque es la referencia contra la que se leen los otros
 * dos números: sin él en la misma fila, "restante $400.000" no significa nada.
 *
 * El rojo aparece en dos condiciones distintas y no es redundancia: `pct > 100` pinta lo
 * consumido, y `restante < 0` pinta lo restante. Con presupuesto 0 el porcentaje es `null` —no
 * hay contra qué medir— y ahí la barra no se dibuja en vez de dibujarse llena.
 */
export function CosteoPanel({ proyecto }: { proyecto: Proyecto }) {
  const { costeo } = proyecto
  const over = (costeo.pct_consumido ?? 0) > 100
  return (
    <Card as="section" aria-label="Costeo" padding="sm">
      <h2 className="mb-4 text-sm font-semibold text-foreground">Costeo</h2>
      <div className="grid grid-cols-3 gap-4 text-center">
        {([
          ["Presupuesto", ARS.format(proyecto.presupuesto), false],
          ["Consumido", ARS.format(costeo.costo_acumulado), over],
          ["Restante", ARS.format(costeo.presupuesto_restante), costeo.presupuesto_restante < 0],
        ] as [string, string, boolean][]).map(([label, value, danger]) => (
          <div key={label}>
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className={cn("mt-1 text-lg font-bold tabular-nums", danger ? "text-destructive" : "text-foreground")}>
              {value}
            </p>
          </div>
        ))}
      </div>
      {costeo.pct_consumido !== null && (
        <div className="mt-4 space-y-1">
          <div className="h-2 overflow-hidden rounded-full bg-muted">
            <div className={cn("h-full rounded-full", over ? "bg-destructive" : "bg-primary")}
              style={{ width: `${Math.min(costeo.pct_consumido, 100)}%` }} />
          </div>
          <p className={cn("text-right text-xs", over ? "font-semibold text-destructive" : "text-muted-foreground")}>
            {costeo.pct_consumido.toFixed(1)}% del presupuesto
          </p>
        </div>
      )}
    </Card>
  )
}

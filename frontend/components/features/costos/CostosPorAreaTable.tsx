"use client"

import { Badge } from "@/components/ui/badge"
import {
  Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { pesos, totalesDeAreas } from "@/components/features/costos/formatos"
import type { DashboardCostos } from "@/types/costo"

/**
 * La tabla "Costos por área" con su pie de totales.
 *
 * Movida VERBATIM desde `costos/page.tsx` al partirla. Presentacional: recibe el dashboard ya
 * cargado y no fetchea.
 *
 * 🔴 SUS FILAS NO SON UNA PÁGINA. `costos_por_area` viene agregado del backend —UNA fila por
 * área, no una por empleado— así que el pie SUMA TODO lo que la tabla muestra y las dos cosas
 * coinciden por construcción. Es exactamente lo contrario del detalle de nómina, que sí pagina y
 * por eso no lleva pie de totales. No copiar este patrón allá.
 *
 * Los dos totales salen de `totalesDeAreas`, compartida con los KPIs: si el encabezado dice
 * "sobre 400 colaboradores" y el pie dijera 380, no habría error, habría dos verdades.
 */
export function CostosPorAreaTable({
  dashboard, mostrarEmpresa,
}: { dashboard: DashboardCostos; mostrarEmpresa: boolean }) {
  const { totalEmpleados, totalPresupuesto, desvioTotal } = totalesDeAreas(dashboard)

  const areas = dashboard.costos_por_area.map((a) => ({
    ...a,
    costoPromedio: a.empleados > 0 ? Math.round(a.costo_mensual / a.empleados) : 0,
    pctTotal:
      dashboard.total_nomina > 0
        ? ((a.costo_mensual / dashboard.total_nomina) * 100).toFixed(1)
        : "0.0",
    desvio: a.costo_mensual - a.presupuesto,
  }))

  return (
    <section className="rounded-xl border bg-card p-4 md:p-6" aria-label="Costos por área">
      <h2 className="mb-4 text-base font-semibold text-foreground">Costos por área</h2>
      <Table>
        <TableHeader>
          <TableRow>
            {mostrarEmpresa && <TableHead>Empresa</TableHead>}
            <TableHead>Área</TableHead>
            <TableHead className="text-right">Empleados</TableHead>
            <TableHead className="text-right">Costo mensual</TableHead>
            <TableHead className="text-right">Costo promedio</TableHead>
            <TableHead className="text-right">% del total</TableHead>
            <TableHead className="text-right">Presupuesto</TableHead>
            <TableHead className="text-right">Desvío</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {areas.map((a) => (
            <TableRow key={`${a.empresa_nombre ?? ""}${a.area_nombre}`}>
              {mostrarEmpresa && (
                <TableCell className="text-muted-foreground">{a.empresa_nombre ?? "—"}</TableCell>
              )}
              <TableCell className="font-medium">{a.area_nombre}</TableCell>
              <TableCell className="text-right text-muted-foreground">{a.empleados}</TableCell>
              <TableCell className="text-right">{pesos(a.costo_mensual)}</TableCell>
              <TableCell className="text-right text-muted-foreground">{pesos(a.costoPromedio)}</TableCell>
              <TableCell className="text-right text-muted-foreground">{a.pctTotal}%</TableCell>
              <TableCell className="text-right text-muted-foreground">
                {a.presupuesto > 0 ? pesos(a.presupuesto) : "—"}
              </TableCell>
              <TableCell className="text-right">
                {a.presupuesto > 0 ? (
                  a.desvio > 0 ? (
                    <Badge variant="destructive">+{pesos(a.desvio)}</Badge>
                  ) : (
                    <span className="text-sm text-emerald-600 dark:text-emerald-400">{pesos(a.desvio)}</span>
                  )
                ) : (
                  <span className="text-sm text-muted-foreground">—</span>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
        <TableFooter>
          <TableRow>
            {mostrarEmpresa && <TableCell />}
            <TableCell className="font-semibold">Total</TableCell>
            <TableCell className="text-right font-semibold">{totalEmpleados}</TableCell>
            <TableCell className="text-right font-semibold">{pesos(dashboard.total_nomina)}</TableCell>
            <TableCell className="text-right text-muted-foreground">
              {totalEmpleados > 0 ? pesos(Math.round(dashboard.total_nomina / totalEmpleados)) : "—"}
            </TableCell>
            <TableCell className="text-right text-muted-foreground">100%</TableCell>
            <TableCell className="text-right font-semibold">
              {totalPresupuesto > 0 ? pesos(totalPresupuesto) : "—"}
            </TableCell>
            <TableCell className="text-right">
              {totalPresupuesto > 0 ? (
                desvioTotal > 0 ? (
                  <Badge variant="destructive">+{pesos(desvioTotal)}</Badge>
                ) : (
                  <span className="text-sm text-emerald-600 dark:text-emerald-400">{pesos(desvioTotal)}</span>
                )
              ) : (
                <span className="text-sm text-muted-foreground">—</span>
              )}
            </TableCell>
          </TableRow>
        </TableFooter>
      </Table>
    </section>
  )
}

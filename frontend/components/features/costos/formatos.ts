import type { DashboardCostos } from "@/types/costo"

/**
 * Vocabulario y formato de la pantalla de Costos, más los dos totales que la tabla por área y
 * los KPIs comparten.
 *
 * Salió de `app/(dashboard)/costos/page.tsx`, que estaba en 624 líneas contra un límite de 150.
 * El movimiento es PURO: `pesos` y `varLabel` son idénticas a las que estaban embebidas.
 *
 * 🔑 `totalesDeAreas` vive ACÁ y no en un componente, y no es capricho: los dos `.reduce()` que
 * calcula los usan tanto los KPIs como el pie de la tabla por área. Con una copia en cada uno,
 * el encabezado y el pie de la misma pantalla podrían empezar a decir números distintos sobre
 * las mismas filas. Y al ser función pura se testea sin renderizar, que es lo único que este
 * proyecto puede hacer (vitest corre sin jsdom).
 */

export const MESES_CORTOS = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
export const MESES_LARGOS = [
  "Enero","Febrero","Marzo","Abril","Mayo","Junio",
  "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre",
]
export const ANIOS = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i)

export function pesos(n: number): string {
  const abs = Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".")
  return n < 0 ? `-$${abs}` : `$${abs}`
}

export function varLabel(v: number | null): string {
  if (v === null) return "Sin datos previos"
  return `${v >= 0 ? "+" : ""}${v.toFixed(1)} %`
}

/**
 * Los agregados de la pantalla, derivados de `costos_por_area`.
 *
 * ⚠️ SE CALCULAN SOBRE EL DASHBOARD, NO SOBRE LA NÓMINA. `costos_por_area` ya viene agregado por
 * el backend (`/api/costos/dashboard`) y trae UNA fila por área, no una por empleado: no es una
 * lista paginada y sumarla es correcto. La lista que SÍ pagina es el detalle de nómina, y de ahí
 * no sale ningún total — es la regla del molde (ver `components/ui/paginacionTotales.test.ts`).
 */
export function totalesDeAreas(dashboard: DashboardCostos | null) {
  const totalEmpleados = dashboard?.costos_por_area.reduce((s, a) => s + a.empleados, 0) ?? 0
  const totalPresupuesto = dashboard?.costos_por_area.reduce((s, a) => s + a.presupuesto, 0) ?? 0
  return {
    totalEmpleados,
    totalPresupuesto,
    desvioTotal: (dashboard?.total_nomina ?? 0) - totalPresupuesto,
  }
}

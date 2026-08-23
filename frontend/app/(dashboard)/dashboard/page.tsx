"use client"

import { useRol } from "@/hooks/useRol"
import { DashboardAdmin } from "@/components/features/dashboard/DashboardAdmin"
import { DashboardMando } from "@/components/features/dashboard/DashboardMando"

// Loading neutro mientras el rol no está resuelto (rol === null): SSR y el 1er render del
// client coinciden en este árbol → sin hydration mismatch, y sin flash del dashboard equivocado.
// Mismo skeleton (animate-pulse + bg-muted) que usan DashboardMando/DashboardAdmin adentro.
function DashboardLoading() {
  return (
    <div className="grid animate-pulse grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-hidden>
      {[1, 2, 3].map((i) => <div key={i} className="h-28 rounded-xl border bg-muted" />)}
    </div>
  )
}

// mandos_medios ve su propio dashboard (GET /api/dashboard-equipo, no le da 403);
// admin/gerencia mantienen el dashboard ejecutivo. El rol se resuelve tras montar (useRol).
export default function DashboardPage() {
  const rol = useRol()
  if (rol === null) return <DashboardLoading />
  // `rol` baja como prop: acá ya dejó de ser `null`, así que el dashboard ejecutivo resuelve el
  // permiso de cada KPI en su PRIMER render y sus links no parpadean. Ver el bloque de
  // `DashboardAdmin`.
  return rol === "mandos_medios" ? <DashboardMando /> : <DashboardAdmin rol={rol} />
}

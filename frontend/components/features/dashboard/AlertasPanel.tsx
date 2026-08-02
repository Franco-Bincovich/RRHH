import Link from "next/link"
import { AlertTriangle } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import type { AlertaDashboard } from "@/services/dashboard"
import { NIVEL_LABEL, NIVEL_VARIANT } from "./dashboardAdminData"

/**
 * Panel de alertas activas. Extraído de DashboardAdmin.tsx, que quedaba con 15 líneas de
 * margen contra su límite de 150.
 *
 * Presentacional puro: sin estado, sin fetch, sin ordenar. El orden lo decide el backend
 * (las accionables van arriba) y el destino de cada alerta también — acá NO se arma ninguna
 * ruta. Ver el comentario de `href` en services/dashboard.ts.
 *
 * NO se monta en DashboardMando a propósito: un mando medio no tiene WRITE sobre empleados,
 * así que las alertas de datos faltantes no son accionables para él.
 */
export function AlertasPanel({ alertas }: { alertas: AlertaDashboard[] }) {
  return (
    <section className="rounded-xl border bg-card p-4 md:p-6" aria-label="Alertas activas">
      <h2 className="mb-4 text-base font-semibold text-foreground">Alertas activas</h2>
      {alertas.length === 0 ? (
        <p className="text-sm text-muted-foreground">Sin alertas activas.</p>
      ) : (
        <ul className="divide-y divide-border" role="list">
          {alertas.map((alerta, i) => (
            <li key={i} className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
              <AlertTriangle className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
              {alerta.href ? (
                <Link
                  href={alerta.href}
                  className="min-w-0 flex-1 text-sm text-foreground hover:underline"
                >
                  {alerta.mensaje}
                </Link>
              ) : (
                <p className="min-w-0 flex-1 text-sm text-foreground">{alerta.mensaje}</p>
              )}
              <Badge variant={NIVEL_VARIANT[alerta.nivel]} className="shrink-0">{NIVEL_LABEL[alerta.nivel]}</Badge>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

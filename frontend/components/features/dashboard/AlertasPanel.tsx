"use client"

import Link from "next/link"
import { Accordion } from "@base-ui/react/accordion"
import { AlertTriangle } from "lucide-react"

import { ConfigSection } from "@/components/features/configuracion/ConfigSection"
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
 * ARRANCA ABIERTA (`defaultValue`), a diferencia del headcount: una alerta es accionable y el
 * punto de la card es que se vea. Se puede plegar para recuperar la pantalla cuando son muchas,
 * y el contador del encabezado sigue diciendo cuántas hay estando plegada.
 *
 * 🔑 El contador es SIEMPRE `alertas.length`, sin desglose por nivel y sin ocultarse en cero:
 * "0" es una respuesta legítima a "cuántas alertas tengo". Sale de los datos que ya llegan, no
 * hay request nuevo.
 *
 * NO se monta en DashboardMando a propósito: un mando medio no tiene WRITE sobre empleados,
 * así que las alertas de datos faltantes no son accionables para él.
 */
export function AlertasPanel({ alertas }: { alertas: AlertaDashboard[] }) {
  return (
    // `contents`: ver el comentario del Root en HeadcountPanel.
    <Accordion.Root defaultValue={["alertas"]} className="contents">
      <ConfigSection
        value="alertas"
        title="Alertas activas"
        badge={<Badge variant="secondary">{alertas.length}</Badge>}
        disabled={alertas.length === 0}
        preview={
          alertas.length === 0
            ? <p className="text-sm text-muted-foreground">Sin alertas activas.</p>
            : undefined
        }
      >
        {alertas.length === 0 ? null : (
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
      </ConfigSection>
    </Accordion.Root>
  )
}

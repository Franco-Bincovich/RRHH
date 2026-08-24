"use client"

import { useRouter } from "next/navigation"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { Proyecto, ProyectoEstado } from "@/types/proyecto"

/**
 * La tarjeta de un proyecto: nombre, empresa dueña, estado y el resumen del costeo.
 *
 * Sale de `ProyectosGrid.tsx`, que al sumarle el patrón del bloque B (el vacío con los valores
 * reales de los filtros, el esqueleto con shimmer y el error con reintento) llegaba a 180 líneas
 * contra un límite de 150. El corte es por responsabilidad: acá vive UNA tarjeta y allá los
 * cuatro estados del listado. Molde: `PerfilCard` / `PerfilesGrid`.
 */
const ARS = new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS", maximumFractionDigits: 0 })

/**
 * 🔴 NINGUNO ES AZUL, y ese es el cambio. `activo` venía con `variant="default"`, o sea
 * `bg-primary`: un relleno azul en la tarjeta de cada proyecto, compitiendo con el ÚNICO relleno
 * azul que el patrón permite en la pantalla — el chip de filtro (`docs/SISTEMA-DE-DISENO.md` §3).
 * Los pares salen de la paleta, medidos en los dos temas por `app/contrasteTokens.test.ts`.
 *
 * Los cuatro estados son un CICLO DE VIDA y la semántica lo sigue:
 *   · **activo** → ÉXITO. Está andando y consumiendo presupuesto: es el que la pantalla mide.
 *   · **pausado** → ATENCIÓN. Está frenado y sigue existiendo: es la tarjeta que pide una
 *     decisión, y por eso es la única que se destaca en reposo.
 *   · **cerrado** → NEUTRO. Terminó: no es un logro pendiente ni un problema.
 *   · **cancelado** → PELIGRO, el mismo rojo tenue que ya tenía con `variant="destructive"`.
 */
export const ESTADO_ESTILO: Record<ProyectoEstado, string> = {
  activo: "bg-success-wash text-success border-success-line",
  pausado: "bg-warning-wash text-warning border-warning-line",
  cerrado: "bg-secondary text-secondary-foreground border-border",
  cancelado: "bg-danger-wash text-destructive border-danger-line",
}

function CosteoBar({ pct }: { pct: number | null }) {
  if (pct === null) return <p className="text-xs text-muted-foreground">Sin presupuesto</p>
  const over = pct > 100
  return (
    <div className="space-y-1">
      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
        <div
          className={cn("h-full rounded-full", over ? "bg-destructive" : "bg-primary")}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      <p className={cn("text-xs", over ? "font-semibold text-destructive" : "text-muted-foreground")}>
        {pct.toFixed(1)}% consumido
      </p>
    </div>
  )
}

export function ProyectoCard({ proyecto, canWrite, onEdit }: {
  proyecto: Proyecto
  canWrite: boolean
  onEdit: (p: Proyecto) => void
}) {
  const router = useRouter()
  const { costeo } = proyecto
  // ⚠️ SIN HOVER DE TARJETA (§2). Es la que más lo tienta —hay ficha de detalle del otro lado—
  // pero la tarjeta NO es el control: los controles son los dos botones, y "Editar" abre otra
  // cosa que "Ver detalle". Hacer clickeable toda la superficie obligaría a frenarle la
  // propagación a "Editar" y dejaría dos destinos en el mismo gesto. Si alguna vez se decide
  // que la tarjeta entera navegue —es decisión de producto, no de estilo—, pasa a
  // `<Card interactive>` y "Ver detalle" se va.
  return (
    <Card padding="sm" interactive className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-foreground">{proyecto.nombre}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">{proyecto.empresa_nombre}</p>
        </div>
        {/* El estilo sale del mapa de arriba: ninguno de los cuatro es azul. */}
        <Badge variant="outline" className={cn("shrink-0 capitalize", ESTADO_ESTILO[proyecto.estado])}>
          {proyecto.estado}
        </Badge>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-xs">
        <span className="text-muted-foreground">Presupuesto</span>
        <span className="text-right font-medium text-foreground">{ARS.format(proyecto.presupuesto)}</span>
        <span className="text-muted-foreground">Consumido</span>
        <span className="text-right font-medium text-foreground">{ARS.format(costeo.costo_acumulado)}</span>
        <span className="text-muted-foreground">Restante</span>
        <span className={cn("text-right font-medium", costeo.presupuesto_restante < 0 ? "text-destructive" : "text-foreground")}>
          {ARS.format(costeo.presupuesto_restante)}
        </span>
      </div>
      <CosteoBar pct={costeo.pct_consumido} />
      <div className="mt-auto flex gap-2 pt-1">
        {/* Las dos acciones están SIEMPRE visibles, no aparecen al apuntar la tarjeta: en una
            grilla, revelarlas en hover obliga a barrer la pantalla con el mouse para saber qué
            se puede hacer con cada proyecto. */}
        <Button variant="outline" size="sm" className="min-h-[2.75rem] flex-1 text-xs" onClick={() => router.push(`/proyectos/${proyecto.id}`)}>
          Ver detalle
        </Button>
        {canWrite && (
          <Button variant="ghost" size="sm" className="min-h-[2.75rem] text-xs" onClick={() => onEdit(proyecto)}>
            Editar
          </Button>
        )}
      </div>
    </Card>
  )
}

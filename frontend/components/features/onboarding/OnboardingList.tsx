"use client"

import { ChevronRight } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { semanaLabel } from "@/components/features/onboarding/_onboardingLabels"
import type { OnboardingInstancia } from "@/types/onboarding"

/**
 * El listado de procesos de onboarding en curso, como tarjetas apilables.
 *
 * Salió de `app/(dashboard)/onboarding/page.tsx` al migrar esa pantalla al patrón del bloque B:
 * ese archivo estaba en **396 líneas contra un límite de 150** —deuda anotada en CLAUDE.md— y los
 * estados nuevos lo empujaban todavía más. El corte va por acá porque la página quedó como
 * orquestador: los tres estados los decide ella y esto es sólo el camino con datos.
 *
 * 🔴 EL PORCENTAJE DE ACÁ ES REAL Y NO CONTRADICE §7. En objetivos NO hay avance en %, y por eso
 * la pantalla de objetivos no lo insinúa; acá sí existe: `progreso` sale del backend contando
 * tareas completadas sobre el total del checklist, que es un dato que la persona marca una por
 * una. Son dos módulos distintos con dos modelos distintos.
 *
 * ⚠️ La barra usa `--primary` a propósito: es un indicador de PROGRESO, no una etiqueta de estado.
 * Lo que §3 reserva para el chip de filtro son los rellenos de badge que compiten por atención en
 * una celda de datos; una barra de avance es el dato mismo, y el repo ya la pinta así en el
 * costeo de proyectos.
 */
export function OnboardingList({ onboardings, mostrarEmpresa, deshabilitado, onAbrir }: {
  onboardings: OnboardingInstancia[]
  /** En modo consolidado se marca de qué empresa es cada proceso. */
  mostrarEmpresa: boolean
  /** Mientras se trae el detalle de uno, no se puede abrir otro. */
  deshabilitado: boolean
  onAbrir: (empleadoId: string) => void
}) {
  return (
    <ul className="space-y-3" role="list">
      {onboardings.map((inst) => (
        <li key={inst.id}>
          {/* 🔴 LA TARJETA ES EL CONTROL, así que lleva el movimiento al apuntar de
              `docs/SISTEMA-DE-DISENO.md` §2: **elevación de 3px con borde iluminado, 160ms**. No
              se escribe acá — sale de `interactive` de `components/ui/card.tsx`, que es el único
              lugar del repo donde ese tratamiento está definido. Hasta el 21/8/2026 esta tarjeta
              tenía su propia versión a mano (`hover:border-primary/40 hover:shadow-sm`, sin
              elevación y sin duración declarada): la mitad del patrón, distinta de la del vecino
              y sin nada que avisara que habían divergido. */}
          <Card
            as="button"
            interactive
            padding="sm"
            type="button"
            onClick={() => onAbrir(inst.empleado_id)}
            disabled={deshabilitado}
            className="group w-full text-left disabled:opacity-60"
          >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="font-medium text-foreground">{inst.empleado_nombre}</p>
            <p className="mt-0.5 text-sm text-muted-foreground">
          {inst.empleado_cargo ?? "—"} · {inst.empleado_area ?? "—"}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {mostrarEmpresa && inst.empresa_nombre && (
          <Badge variant="outline" className="text-xs">
            {inst.empresa_nombre}
          </Badge>
            )}
            <Badge variant="secondary">{semanaLabel(inst)}</Badge>
            {/* Siempre visible, sólo cambia de color al apuntar la tarjeta (§3). */}
                <ChevronRight className="size-4 text-muted-foreground transition-colors group-hover:text-primary" aria-hidden="true" />
          </div>
        </div>

        <div className="mt-3">
          <div className="mb-1 flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Inicio: {inst.fecha_inicio}</span>
            <span className="font-medium text-foreground">{inst.progreso}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-muted">
            <div
          className="h-full rounded-full bg-primary transition-all duration-300"
          style={{ width: `${inst.progreso}%` }}
            />
          </div>
        </div>
          </Card>
        </li>
      ))}
        </ul>
  )
}

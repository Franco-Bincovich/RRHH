"use client"

import { ChevronRight, ClipboardList, Lock, X } from "lucide-react"
import type { ReactNode } from "react"

import { Card } from "@/components/ui/card"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import type { OnboardingTemplate } from "@/types/onboarding"

interface TemplatesListProps {
  templates: OnboardingTemplate[]
  loading: boolean
  error: string | null
  canWrite: boolean
  /** Sufija cada fila con el nombre de la empresa. True en la vista consolidada. */
  mostrarEmpresa: boolean
  deletingId: string | null
  onAbrir: (id: string) => void
  /** Recibe el template entero: la confirmación lo nombra, no muestra un UUID. */
  onEliminar: (t: OnboardingTemplate) => void
  /** Reintento del error. Antes el `ErrorState` se dibujaba SIN accion: el usuario leia que algo
   *  fallo y no tenia con que volver a intentar salvo recargar la pestana entera. */
  onReintentar: () => void
  /** Que ofrecer cuando no hay datos: el alta. `undefined` si no puede escribir. */
  accionVacio?: ReactNode
}

/**
 * Listado de templates de onboarding: presentacional puro (loading / error / vacío / datos).
 * No fetchea ni tiene estado propio — la página conserva los datos y los handlers.
 */
export function TemplatesList({
  templates,
  loading,
  error,
  canWrite,
  mostrarEmpresa,
  deletingId,
  onAbrir,
  onEliminar,
  onReintentar,
  accionVacio,
}: TemplatesListProps) {
  if (loading) {
    return (
      <ul className="space-y-3">
        {[1, 2, 3].map((i) => (
          <li key={i}><Skeleton shimmer className="h-20 w-full rounded-xl" /></li>
        ))}
      </ul>
    )
  }

  if (error) return <ErrorState description={error} action={onReintentar} />

  if (templates.length === 0) {
    /*
     * 🔴 COPY PROPIO, y no `textoVacio`: esta pantalla no tiene filtros, así que el helper sólo
     * daría su rama genérica —"Cuando se cargue el primero va a aparecer acá"— y ahí se pierde lo
     * único que importa. Sin templates **no se puede iniciar ningún onboarding**: la pantalla de
     * al lado arranca eligiendo uno. No es "faltan datos", es una capacidad apagada.
     */
    return (
      <EmptyState
        icon={<ClipboardList />}
        title="Todavía no hay ningún template"
        description="Mientras no haya al menos uno, no se puede iniciar un onboarding: el proceso arranca eligiendo el template que define sus tareas."
        action={accionVacio}
      />
    )
  }

  return (
    <ul className="space-y-3" role="list">
      {templates.map((t) => (
        <li key={t.id} className="flex items-stretch gap-2">
          {/* 🔴 LA TARJETA ES EL CONTROL —abre la ficha del template—, así que lleva el
              movimiento al apuntar de `docs/SISTEMA-DE-DISENO.md` §2: **elevación de 3px con
              borde iluminado, 160ms**, y sale de `interactive` de `components/ui/card.tsx`. La
              ✕ de al lado NO va adentro: sería un botón dentro de otro botón (HTML inválido) y
              además la tarjeta que se levanta no debe arrastrar a la acción destructiva. */}
          <Card
            as="button"
            interactive
            padding="sm"
            type="button"
            onClick={() => onAbrir(t.id)}
            className="min-w-0 flex-1 text-left"
          >
            <div className="group flex items-center justify-between gap-3">
              <div className="min-w-0 flex-1">
                <p className="flex items-center gap-1.5 font-medium text-foreground">
                  {t.nombre}
                  {/* Solo las privadas se marcan: "compartida" es el estado normal y un chip
                      en cada fila sería ruido. Aparece solo si podés verla, así que o es tuya
                      o sos gerencia. */}
                  {!t.es_publica && (
                    <span
                      className="inline-flex items-center gap-1 rounded-md border border-warning-line bg-warning-wash px-1.5 py-0.5 text-[11px] font-medium text-warning"
                      title={t.created_by_nombre ? `Privada de ${t.created_by_nombre}` : "Privada"}
                    >
                      <Lock className="size-3" />
                      Privada
                    </span>
                  )}
                </p>
                {t.descripcion && (
                  <p className="mt-0.5 truncate text-sm text-muted-foreground">{t.descripcion}</p>
                )}
                <p className="mt-1 text-xs text-muted-foreground">
                  {t.tareas_total} tarea{t.tareas_total !== 1 ? "s" : ""}
                  {mostrarEmpresa && t.empresa_nombre && (
                    <span className="ml-2 text-muted-foreground/70">· {t.empresa_nombre}</span>
                  )}
                  {/* Sin autor no se escribe nada: "Creada por —" no aporta y ensucia la fila. */}
                  {t.created_by_nombre && (
                    <span className="ml-2 text-muted-foreground/70">· Creada por {t.created_by_nombre}</span>
                  )}
                </p>
              </div>
              {/* Siempre visible, solo cambia de color al apuntar la fila (§3). */}
              <ChevronRight className="size-4 shrink-0 text-muted-foreground transition-colors group-hover:text-primary" aria-hidden="true" />
            </div>
          </Card>
          {canWrite && (
            <button
              type="button"
              onClick={() => onEliminar(t)}
              disabled={deletingId === t.id}
              className="flex min-h-[44px] min-w-[44px] shrink-0 items-center justify-center rounded-xl border bg-card text-muted-foreground hover:bg-destructive/10 hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
              aria-label="Eliminar template"
            >
              <X className="size-4" />
            </button>
          )}
        </li>
      ))}
    </ul>
  )
}

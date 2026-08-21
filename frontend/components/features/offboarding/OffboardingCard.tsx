"use client"

import { Paperclip } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { EfectivizarBajaButton } from "@/components/features/offboarding/EfectivizarBajaButton"
import { EntrevistaSalida } from "@/components/features/offboarding/EntrevistaSalida"
import {
  MOTIVO_LABEL, MOTIVO_VARIANT, TIPO_ACTIVO_LABEL,
} from "@/components/features/offboarding/_offboardingLabels"
import type { ActivoResponse, OffboardingInstancia } from "@/types/offboarding"

/**
 * La tarjeta de UN proceso de offboarding: cabecera, progreso, checklist de activos, entrevista
 * de salida y la confirmación de la baja.
 *
 * Extraída de `app/(dashboard)/offboarding/page.tsx` (311/150). Presentacional salvo por el
 * botón de baja, que es autocontenido: el estado de la lista vive en `useOffboardings` y acá
 * solo se reciben los datos y los callbacks. Molde del reparto: `AsignacionesTab` /
 * `AsignacionesCapTable` en el módulo de formación.
 */
interface Props {
  instancia: OffboardingInstancia
  canWrite: boolean
  mostrarEmpresa: boolean
  saving: string | null
  onToggleActivo: (instanciaId: string, activo: ActivoResponse) => void
  onDocumentos: (instancia: OffboardingInstancia) => void
  onEntrevista: (id: string, realizada: boolean, notas: string | null) => void
  onEfectivizada: (id: string) => void
}

export function OffboardingCard({
  instancia, canWrite, mostrarEmpresa, saving,
  onToggleActivo, onDocumentos, onEntrevista, onEfectivizada,
}: Props) {
  const devueltos = instancia.activos.filter((a) => a.devuelto).length

  return (
    <li className="rounded-xl border bg-card p-4 md:p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium text-foreground">{instancia.empleado_nombre}</p>
          <p className="mt-0.5 text-sm text-muted-foreground">Egreso: {instancia.fecha_inicio}</p>
        </div>
        {/* 🔴 `sm:shrink-0` Y NO `shrink-0`: con `shrink-0` el contenedor toma su ancho de
            contenido, así que el `flex-wrap` que ya tenía NUNCA se activaba y a 390px la fila se
            iba 139px afuera de la pantalla. De `sm` para arriba manda lo de antes: lo que se
            achica es el nombre, no las acciones. */}
        <div className="flex min-w-0 flex-wrap items-center justify-end gap-2 sm:shrink-0">
          {mostrarEmpresa && instancia.empresa_nombre && (
            <Badge variant="outline" className="text-xs">{instancia.empresa_nombre}</Badge>
          )}
          <Badge variant={MOTIVO_VARIANT[instancia.motivo] ?? "secondary"}>
            {MOTIVO_LABEL[instancia.motivo] ?? instancia.motivo}
          </Badge>
          <Button variant="ghost" size="sm" className="min-h-11 gap-1.5"
            onClick={() => onDocumentos(instancia)}>
            <Paperclip className="size-4" /> Documentos
          </Button>
          {/* Última acción del proceso y la única irreversible, por eso va al final de la fila:
              el orden de lectura la deja después de haber visto el motivo y los documentos. */}
          {canWrite && (
            <EfectivizarBajaButton instancia={instancia} onEfectivizada={onEfectivizada} />
          )}
        </div>
      </div>

      <div className="mt-3">
        <div className="mb-1.5 flex items-center justify-between text-xs">
          <span className="text-muted-foreground">
            {devueltos} de {instancia.activos.length} activos devueltos
          </span>
          <span className="font-medium text-foreground">{instancia.progreso}%</span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-muted">
          <div className="h-full rounded-full bg-primary transition-all duration-300"
            style={{ width: `${instancia.progreso}%` }} />
        </div>
      </div>

      {instancia.activos.length > 0 ? (
        <ul className="mt-4 divide-y divide-border" role="list" aria-label="Activos corporativos">
          {instancia.activos.map((activo) => {
            const isSaving = saving === `${instancia.id}-${activo.id}`
            return (
              <li key={activo.id}>
                <label className={cn(
                  "flex items-center gap-2.5 py-2.5",
                  canWrite && "cursor-pointer transition-colors hover:text-primary",
                  isSaving && "opacity-60",
                )}>
                  {canWrite && (
                    <input
                      type="checkbox"
                      checked={activo.devuelto}
                      onChange={() => !isSaving && onToggleActivo(instancia.id, activo)}
                      disabled={isSaving}
                      className="size-4 shrink-0 accent-primary"
                    />
                  )}
                  <span className={cn(
                    "text-sm",
                    activo.devuelto
                      ? "text-muted-foreground line-through decoration-muted-foreground/60"
                      : "text-foreground",
                  )}>
                    {TIPO_ACTIVO_LABEL[activo.tipo_activo] ?? activo.tipo_activo}
                    {activo.descripcion && (
                      <span className="ml-1 text-xs text-muted-foreground">
                        — {activo.descripcion}
                      </span>
                    )}
                  </span>
                </label>
              </li>
            )
          })}
        </ul>
      ) : (
        <p className="mt-3 text-xs text-muted-foreground">
          Sin activos registrados para devolver.
        </p>
      )}

      <EntrevistaSalida instancia={instancia} canWrite={canWrite} onGuardado={onEntrevista} />
    </li>
  )
}

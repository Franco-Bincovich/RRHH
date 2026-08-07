"use client"

import { MOTIVO_VARIABLES } from "@/components/features/comunicacion/direccionesLibres"
import type { ModoEnvio } from "@/components/features/comunicacion/useEnvioPlantilla"
import { cn } from "@/lib/utils"

interface Props {
  modo: ModoEnvio
  /** La plantilla usa `{{variables}}` → el modo libre queda deshabilitado, con el motivo visible. */
  usaVariables: boolean
  onCambio: (m: ModoEnvio) => void
}

const OPCIONES: { id: ModoEnvio; label: string }[] = [
  { id: "empleados", label: "Empleados del sistema" },
  { id: "libre", label: "Escribir direcciones" },
]

/**
 * El selector de modo. Presentacional puro.
 *
 * 🔴 CUANDO LA PLANTILLA USA VARIABLES, EL MODO LIBRE SE DESHABILITA **ANTES**, con el motivo a
 * la vista — no un error después de apretar Enviar. La diferencia no es de estilo: para cuando
 * el error llega, el usuario ya escribió las direcciones, ya confirmó y ya cree que el mail
 * salió. El motivo va pegado al control que no responde, por la misma razón por la que el aviso
 * de "elegí una empresa" vive junto al botón que deshabilita.
 *
 * Son botones y no un `<select>`: son dos opciones excluyentes y una de ellas puede estar
 * deshabilitada con una explicación al lado, que en un `<option>` no se puede mostrar.
 */
export function EnvioModo({ modo, usaVariables, onCambio }: Props) {
  return (
    <div className="space-y-2">
      <div role="group" aria-label="A quién enviar" className="flex gap-1 rounded-lg border p-1">
        {OPCIONES.map((o) => {
          const deshabilitado = o.id === "libre" && usaVariables
          return (
            <button
              key={o.id}
              type="button"
              disabled={deshabilitado}
              aria-pressed={modo === o.id}
              onClick={() => onCambio(o.id)}
              className={cn(
                "flex-1 rounded-md px-3 py-1.5 text-sm transition-colors",
                modo === o.id ? "bg-primary text-primary-foreground" : "text-muted-foreground",
                deshabilitado && "cursor-not-allowed opacity-50",
              )}
            >
              {o.label}
            </button>
          )
        })}
      </div>

      {usaVariables && (
        <p className="text-xs text-amber-700 dark:text-amber-500">{MOTIVO_VARIABLES}</p>
      )}
    </div>
  )
}

"use client"

import { Plus, Trash2 } from "lucide-react"

import {
  agregarTramo, antiguedadesDuplicadas, editarTramo, quitarTramo,
} from "@/components/features/configuracion/escala"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import type { TramoEscala } from "@/types/configuracion"

/**
 * Editor de la escala de días de vacaciones por antigüedad.
 *
 * Es una LISTA y no un juego de campos fijos porque la cantidad de tramos la decide cada
 * empresa: se agregan y se quitan desde acá. Por eso la escala vive en su propia tabla y no
 * como columnas de parametros_empresa.
 *
 * Controlado: el estado y el guardado los lleva el padre, que es quien sabe si la escala es
 * propia o heredada.
 */
export function EscalaAntiguedad({
  tramos, onChange, editable,
}: {
  tramos: TramoEscala[]
  onChange: (t: TramoEscala[]) => void
  editable: boolean
}) {
  const duplicadas = antiguedadesDuplicadas(tramos)

  return (
    <div className="space-y-3">
      {tramos.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Sin tramos propios: se está usando la escala general.
        </p>
      ) : (
        <ul className="space-y-2" role="list">
          {tramos.map((t, i) => (
            <li key={i} className="flex flex-wrap items-center gap-2 text-sm">
              <span className="text-muted-foreground">Desde</span>
              <Input
                type="number"
                min={0}
                max={60}
                aria-label={`Antigüedad del tramo ${i + 1}`}
                disabled={!editable}
                value={t.antiguedad_anios}
                onChange={(e) => {
                  const n = Number(e.target.value)
                  if (!Number.isNaN(n)) onChange(editarTramo(tramos, i, "antiguedad_anios", n))
                }}
                className={`w-20 ${duplicadas.includes(t.antiguedad_anios) ? "border-destructive" : ""}`}
              />
              <span className="text-muted-foreground">años →</span>
              <Input
                type="number"
                min={1}
                max={365}
                aria-label={`Días del tramo ${i + 1}`}
                disabled={!editable}
                value={t.dias}
                onChange={(e) => {
                  const n = Number(e.target.value)
                  if (!Number.isNaN(n)) onChange(editarTramo(tramos, i, "dias", n))
                }}
                className="w-20"
              />
              <span className="text-muted-foreground">días</span>
              {editable && (
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={`Quitar el tramo ${i + 1}`}
                  onClick={() => onChange(quitarTramo(tramos, i))}
                >
                  <Trash2 className="size-4" />
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}

      {duplicadas.length > 0 && (
        <p className="text-sm text-destructive">
          Hay más de un tramo para {duplicadas.join(" y ")} años de antigüedad. Cada antigüedad
          puede aparecer una sola vez.
        </p>
      )}

      {editable && (
        <Button variant="outline" size="sm" onClick={() => onChange(agregarTramo(tramos))}>
          <Plus className="mr-2 size-4" />
          Agregar tramo
        </Button>
      )}
    </div>
  )
}

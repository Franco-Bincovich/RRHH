"use client"

import { FieldError } from "@/components/ui/FieldError"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  MAX_DESCRIPCION, MAX_DIAS_AVISO, MAX_NOMBRE, MIN_DIAS_AVISO,
  type ErroresEvento, type FormEvento,
} from "@/components/features/eventos/guardarEvento"

interface Props {
  form: FormEvento
  errores: ErroresEvento
  onCampo: <K extends keyof FormEvento>(campo: K, valor: FormEvento[K]) => void
}

/**
 * Los cinco campos del formulario de un evento. PRESENTACIONAL: sin estado, sin fetch, sin envío.
 *
 * Salió de `EventoModal.tsx`, que llegó a 178 líneas contra el límite de 150. El corte es el que
 * el repo ya usa en vacaciones (`CamposVacacion.tsx`): el modal queda con la shell —abrir,
 * cerrar, submit, error del servidor— y los campos con lo que se ve y se escribe.
 *
 * ⚠️ Sigue sin poder testearse con vitest: se renderiza dentro del `Dialog` de Radix, que monta
 * por portal, y a string sale vacío. Lo que hay que poder desmentir vive en `guardarEvento.ts`,
 * que sí es una función suelta.
 */
export function CamposEvento({ form, errores, onCampo }: Props) {
  return (
    <>
      <div className="space-y-1.5">
        <Label htmlFor="evento-nombre">
          Nombre <span className="text-destructive" aria-hidden>*</span>
        </Label>
        <Input
          id="evento-nombre" value={form.nombre} maxLength={MAX_NOMBRE}
          placeholder="Ej.: Feriado puente" aria-required
          aria-invalid={Boolean(errores.nombre)}
          onChange={(e) => onCampo("nombre", e.target.value)}
        />
        {errores.nombre && (
          <FieldError>{errores.nombre}</FieldError>
        )}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="evento-fecha">
          Fecha <span className="text-destructive" aria-hidden>*</span>
        </Label>
        <Input
          id="evento-fecha" type="date" value={form.fecha} aria-required
          aria-invalid={Boolean(errores.fecha)}
          onChange={(e) => onCampo("fecha", e.target.value)}
        />
        {errores.fecha && (
          <FieldError>{errores.fecha}</FieldError>
        )}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="evento-aviso">Avisar con</Label>
        {/* ⚠️ NACE VACÍO en el alta, y el placeholder dice por qué. Precargarlo con el default de
            la empresa parecería más amable y sería peor: el número quedaría CONGELADO en el
            evento, así que cambiarlo después en Configuración no movería nada y nadie entendería
            por qué. Vacío significa "seguí lo que diga Configuración". */}
        <Input
          id="evento-aviso" type="number" inputMode="numeric"
          min={MIN_DIAS_AVISO} max={MAX_DIAS_AVISO} value={form.diasAviso}
          placeholder="Lo que diga Configuración"
          aria-invalid={Boolean(errores.diasAviso)}
          onChange={(e) => onCampo("diasAviso", e.target.value)}
        />
        <p className="text-xs text-muted-foreground">
          Días de anticipación con los que aparece en el dashboard. Vacío usa el valor de
          Configuración.
        </p>
        {errores.diasAviso && (
          <FieldError>{errores.diasAviso}</FieldError>
        )}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="evento-descripcion">Descripción</Label>
        <Textarea
          id="evento-descripcion" value={form.descripcion} maxLength={MAX_DESCRIPCION}
          rows={3} aria-invalid={Boolean(errores.descripcion)}
          onChange={(e) => onCampo("descripcion", e.target.value)}
        />
        {errores.descripcion && (
          <FieldError>{errores.descripcion}</FieldError>
        )}
      </div>

      {/* El checkbox dice "Solo para mí" y guarda `es_publica = false`. La etiqueta está en
          primera persona a propósito: "no pública" obliga a pensar el negativo de una palabra
          que en la tabla ya se muestra como "Del equipo". */}
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox" className="size-4" checked={!form.esPublica}
          onChange={(e) => onCampo("esPublica", !e.target.checked)}
        />
        Solo para mí
      </label>
    </>
  )
}

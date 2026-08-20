import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"

import type { EstadoAlta } from "@/types/empleado"

import type { FormData } from "./_constants"

/**
 * Las dos opciones del estado de alta, EN CASTELLANO Y DICIENDO EL HECHO, no el valor crudo.
 * "Preingreso" es vocabulario del sistema; "Todavía no ingresó" es lo que la persona de Capital
 * Humano sabe cuando carga el legajo. El valor viaja igual al backend.
 *
 * Viven acá y no en `_constants.ts` porque son TEXTO DE ESTE CONTROL: el archivo de constantes
 * describe la forma del formulario, no cómo se llaman las cosas en pantalla (y además ya estaba
 * en 201 líneas contra un límite de 200).
 */
export const ESTADO_ALTA_OPCIONES: { value: EstadoAlta; label: string }[] = [
  { value: "activo", label: "Ya está trabajando" },
  { value: "preingreso", label: "Todavía no ingresó" },
]

/*
 * 🔴 SOLO EN EL ALTA. El pase `preingreso` → `activo` es el botón "Confirmar ingreso" de la
 * ficha (endpoint `/activar`, A3), que verifica que la fecha de ingreso ya haya ocurrido.
 * Ofrecerlo como campo editable acá dejaría activar a alguien salteándose esa guarda, y
 * además convertiría en "editable" un estado —`baja`, `licencia`— que se alcanza por otros
 * flujos y que este select ni siquiera puede representar.
 *
 * Va PEGADO a la fecha de ingreso porque es el campo del que se deriva: al elegir una fecha
 * futura, este select se mueve solo a "Todavía no ingresó" y el usuario lo ve pasar.
 */
export function EstadoAltaField({ value, onChange }: {
  value: FormData["estado"]
  onChange: (value: FormData["estado"]) => void
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor="estado_alta">¿La persona ya empezó?</Label>
      <Select
        className="w-auto"
        id="estado_alta"
        value={value}
        onChange={(e) => onChange(e.target.value as FormData["estado"])}
      >
        {ESTADO_ALTA_OPCIONES.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </Select>
    </div>
  )
}

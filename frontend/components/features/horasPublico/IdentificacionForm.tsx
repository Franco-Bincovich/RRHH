"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { normalizarDni } from "@/components/features/horasPublico/logica"

interface Props {
  dni: string
  onDni: (v: string) => void
  enviando: boolean
  onSubmit: (e: React.FormEvent) => void
}

/**
 * El paso 1: el DNI. Es la única pantalla que ve alguien que todavía no se identificó.
 *
 * `inputMode="numeric"` y no `type="number"`: en un celular abre el teclado numérico igual, pero
 * sin las flechitas de incremento ni el scroll que cambia el valor sin querer — un DNI no es una
 * cantidad. `autoComplete="off"` porque en una máquina compartida —el escenario de este link—
 * no queremos que el navegador ofrezca el documento de la persona anterior.
 *
 * El botón se deshabilita mientras no haya dígitos. Acá `disabled` SÍ es correcto (el campo
 * existe, la acción todavía no); lo que un test puede afirmar de eso es `normalizarDni`, que es
 * la función pura que lo decide.
 */
export function IdentificacionForm({ dni, onDni, enviando, onSubmit }: Props) {
  return (
    <form onSubmit={onSubmit} className="space-y-4 rounded-lg border bg-card p-4">
      <div className="space-y-1.5">
        <Label htmlFor="dni">Ingresá tu DNI</Label>
        <Input id="dni" inputMode="numeric" autoComplete="off"
               placeholder="Sin puntos ni guiones"
               value={dni} onChange={(e) => onDni(e.target.value)} />
      </div>
      <Button type="submit" className="min-h-11 w-full" disabled={enviando || !normalizarDni(dni)}>
        {enviando ? "Verificando..." : "Continuar"}
      </Button>
    </form>
  )
}

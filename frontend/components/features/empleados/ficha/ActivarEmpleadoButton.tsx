"use client"

import { useState } from "react"
import { toast } from "sonner"
import { UserCheck } from "lucide-react"

import { Button } from "@/components/ui/button"
import { ApiError } from "@/services/api"
import { activarEmpleado } from "@/services/empleados"
import type { Empleado } from "@/types/empleado"

/**
 * "Confirmar ingreso": el botón que pasa un legajo de `preingreso` a `activo`.
 *
 * Componente propio y no dos líneas en la ficha porque `empleados/[id]/page.tsx` está en
 * 133/150 y esto trae estado, llamada y manejo de tres errores distintos. Molde:
 * `EliminarCandidatoButton` (botón autocontenido que avisa al padre por callback).
 *
 * 🔴 NO LLEVA ConfirmDialog, a diferencia de la efectivización de una baja. La diferencia no es
 * de importancia sino de reversibilidad: activar a alguien por error se corrige editando el
 * estado en la ficha, mientras que efectivizar una baja escribe `fecha_egreso` y cierra la
 * instancia de offboarding, y desde la UI no hay vuelta atrás.
 *
 * 🔴 EL MENSAJE DEL BACKEND SE MUESTRA TAL CUAL, sin traducir ni resumir. `INGRESO_AUN_NO_OCURRIO`
 * ya dice la fecha que falta y qué hacer si la persona entró antes de lo previsto ("corregí la
 * fecha en el legajo y después activala"). Reemplazarlo por "no se pudo activar" deja al usuario
 * sin la única información que resuelve el caso — que es además el único error de los tres que
 * se puede encontrar operando normal: el 404 y el 409 exigen un id ajeno o una carrera entre dos
 * pestañas.
 */
export function ActivarEmpleadoButton(
  { empleado, onActivado }: { empleado: Empleado; onActivado: () => void },
) {
  const [activando, setActivando] = useState(false)

  async function activar() {
    setActivando(true)
    try {
      await activarEmpleado(empleado.id)
      toast.success(`${empleado.nombre} ${empleado.apellido} ya figura como activo`)
      onActivado()
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "No se pudo confirmar el ingreso.")
    } finally {
      setActivando(false)
    }
  }

  return (
    <Button
      variant="outline"
      className="min-h-11 gap-2"
      disabled={activando}
      onClick={activar}
    >
      <UserCheck className="size-4" />
      {activando ? "Confirmando..." : "Confirmar ingreso"}
    </Button>
  )
}

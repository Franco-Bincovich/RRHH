"use client"

import { UserCheck } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useActivarEmpleado } from "@/components/features/empleados/useActivarEmpleado"
import type { Empleado } from "@/types/empleado"

/**
 * "Confirmar ingreso" en la FICHA: el botón que pasa un legajo de `preingreso` a `activo`.
 *
 * Componente propio y no dos líneas en la ficha porque `empleados/[id]/page.tsx` está en
 * 133/150. Molde: `EliminarCandidatoButton` (botón autocontenido que avisa al padre por callback).
 *
 * ⚠️ LA LÓGICA YA NO VIVE ACÁ: se fue a `useActivarEmpleado` cuando apareció el segundo punto de
 * entrada del mismo acto —el botón de la fila en `/proximos-ingresos`—. Este archivo quedó con
 * lo único que es propio de la ficha: la FORMA del botón. El porqué de la llamada, del toast y
 * del manejo de los tres errores está escrito en el hook, no acá, para que no haya dos versiones.
 *
 * 🔴 NO LLEVA ConfirmDialog, a diferencia de la efectivización de una baja. La diferencia no es
 * de importancia sino de reversibilidad: activar a alguien por error se corrige editando el
 * estado en la ficha, mientras que efectivizar una baja escribe `fecha_egreso` y cierra la
 * instancia de offboarding, y desde la UI no hay vuelta atrás.
 */
export function ActivarEmpleadoButton(
  { empleado, onActivado }: { empleado: Empleado; onActivado: () => void },
) {
  const { activandoId, activar } = useActivarEmpleado(onActivado)
  const activando = activandoId === empleado.id

  return (
    <Button
      variant="outline"
      className="min-h-11 gap-2"
      disabled={activando}
      onClick={() => activar(empleado)}
    >
      <UserCheck className="size-4" />
      {activando ? "Confirmando..." : "Confirmar ingreso"}
    </Button>
  )
}

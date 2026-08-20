import { LogOut, Pencil } from "lucide-react"

import { Button } from "@/components/ui/button"
import type { Empleado } from "@/types/empleado"

import { ActivarEmpleadoButton } from "./ActivarEmpleadoButton"

/**
 * Las acciones de la barra de identidad de la ficha.
 *
 * 🔴 LA PRIMARIA VA ÚLTIMA (`docs/SISTEMA-DE-DISENO.md` §3), y el orden de este archivo ES el
 * orden de la pantalla: las de ciclo de vida primero, en `variant="outline"`, y "Editar" al
 * final, sólida. El motivo es que el ojo termina el recorrido donde está la acción que más se
 * usa, y que una acción irreversible —dar de baja— no puede ser la más fácil de apretar.
 *
 * 🔴 LAS DOS DE CICLO SON EXCLUYENTES POR CONSTRUCCIÓN: "Confirmar ingreso" sólo existe en
 * `preingreso` (es el único estado desde el que el backend acepta el pase) y "Iniciar
 * offboarding" sólo en `activo` — quien todavía no entró no se puede dar de baja. Nunca se ven
 * las dos juntas, así que la barra tiene a lo sumo dos botones.
 *
 * Se renderiza sólo con permiso de escritura; el gate lo aplica la página.
 */
export function AccionesFicha({ empleado, onActivado, onOffboarding, onEditar }: {
  empleado: Empleado
  onActivado: () => void
  onOffboarding: () => void
  onEditar: () => void
}) {
  return (
    <>
      {empleado.estado === "preingreso" && (
        <ActivarEmpleadoButton empleado={empleado} onActivado={onActivado} />
      )}
      {empleado.estado === "activo" && (
        <Button
          variant="outline"
          className="min-h-11 gap-2 text-destructive hover:bg-destructive/10 hover:text-destructive"
          onClick={onOffboarding}
        >
          <LogOut className="size-4" />
          Iniciar offboarding
        </Button>
      )}
      <Button className="min-h-11" onClick={onEditar}>
        <Pencil />
        Editar
      </Button>
    </>
  )
}

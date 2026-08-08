"use client"

import { Upload } from "lucide-react"

import { Button } from "@/components/ui/button"

/**
 * El botón "Importar" con su regla de habilitación y el motivo a la vista.
 *
 * Componente propio —y no dos líneas en la página— por dos razones: la página está en 130/150 y
 * no le entra la lógica, y esto es lo único del flujo que hay que poder afirmar sin montar el
 * modal (que va por portal y en vitest sin jsdom renderiza vacío). Molde: `PlantillaAcciones`.
 *
 * 🔴 EN MODO CONSOLIDADO NO SE IMPORTA, y el motivo se muestra PEGADO al botón. Importar es una
 * ACCIÓN: la empresa viaja en el body del confirmar, no en el header. Con "Todas las empresas"
 * elegido no hay ninguna a la cual cargarle los objetivos, y el backend rechazaría el body
 * igual — pero recién después de que el usuario armó el archivo y lo subió. Bloquearlo acá le
 * ahorra ese camino. Mismo criterio que el guardado de plantillas (`PlantillaAcciones`).
 *
 * ⚠️ El aviso va al lado del botón y no arriba de la pantalla: un cartel en el encabezado queda
 * fuera de la vista justo cuando el usuario está mirando el botón que no responde.
 */
export function ImportarObjetivosBoton(
  { sinEmpresa, onClick }: { sinEmpresa: boolean; onClick: () => void },
) {
  return (
    <div className="flex items-center gap-2">
      {sinEmpresa && (
        <span className="hidden text-xs text-muted-foreground sm:inline">
          Elegí una empresa para importar
        </span>
      )}
      <Button
        variant="outline"
        className="min-h-11 gap-2"
        disabled={sinEmpresa}
        onClick={onClick}
        title={sinEmpresa ? "Elegí una empresa en el selector de arriba a la izquierda" : undefined}
      >
        <Upload className="size-4" /> Importar
      </Button>
    </div>
  )
}

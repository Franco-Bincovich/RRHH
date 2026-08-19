"use client"

import { Upload } from "lucide-react"

import { Button } from "@/components/ui/button"

/**
 * El botón "Importar" del catálogo de formación, con su regla de habilitación y el motivo a la
 * vista. Copia exacta de `ImportarObjetivosBoton`, que resolvió el mismo problema.
 *
 * Componente propio —y no dos líneas en el tab— por dos razones: `CatalogoTab` está al límite y
 * no le entra la lógica, y esto es lo único del flujo que se puede afirmar sin montar el modal
 * (que va por portal y en vitest sin jsdom renderiza vacío).
 *
 * 🔴 EN MODO CONSOLIDADO NO SE IMPORTA, y el motivo se muestra PEGADO al botón. Importar es una
 * ACCIÓN: la empresa viaja en el form del preview y en el body del confirmar, no en el header.
 * Con "Todas las empresas" elegido no hay ninguna contra la cual matchear el padrón ni a cuál
 * cargarle los cursos, y el backend rechazaría igual — pero recién después de que el usuario
 * armó el archivo y lo subió. Bloquearlo acá le ahorra ese camino.
 *
 * ⚠️ El aviso va al lado del botón y no arriba de la pantalla: un cartel en el encabezado queda
 * fuera de la vista justo cuando el usuario está mirando el botón que no responde.
 */
export function ImportarFormacionBoton(
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

"use client"

import { Plus } from "lucide-react"

import { Button } from "@/components/ui/button"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { RevisarCasillaButton } from "@/components/features/vacantes/RevisarCasillaButton"
import { exportarVacantes } from "@/services/vacantes"
import type { EstadoVacante } from "@/types/vacantes"

/**
 * Las acciones del encabezado de /vacantes: exportar, revisar la casilla y crear.
 *
 * Salió de `vacantes/page.tsx`, que ya estaba en 178 contra un límite de 150 ANTES de esta sesión
 * (deuda anotada en CLAUDE.md) y no entraba al sumarle la paginación.
 *
 * 🔴 `hayFilas` NO es `vacantes.length > 0`: en la página 2 el largo de la página no dice si hay
 * algo que exportar. Lo decide el TOTAL del filtro, y por eso llega ya resuelto desde la página.
 */
interface Props {
  hayFilas: boolean
  canWrite: boolean
  estadoFiltro: EstadoVacante | ""
  empresaFiltro: string
  onNueva: () => void
}

export function VacantesAcciones({ hayFilas, canWrite, estadoFiltro, empresaFiltro, onNueva }: Props) {
  return (
    <div className="flex items-center gap-2">
      {/* Exporta con el MISMO estado que filtra la pantalla. La empresa viaja por el
          header, igual que en el listado. Sin filas no se ofrece exportar. */}
      {hayFilas && (
        <ExportMenu
          onExport={(f) => exportarVacantes(f, estadoFiltro || undefined, empresaFiltro || undefined)}
        />
      )}
      {/* Revisa la CASILLA entera, no esta pantalla: cada mail elige su vacante por el
          código del asunto. Por eso vive en el listado y no en la ficha de una vacante. */}
      {canWrite && <RevisarCasillaButton />}
      {canWrite && (
        <Button className="min-h-11" onClick={onNueva}>
          <Plus />
          Nueva vacante
        </Button>
      )}
    </div>
  )
}

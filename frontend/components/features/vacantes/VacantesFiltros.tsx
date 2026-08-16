"use client"

import { Skeleton } from "@/components/ui/skeleton"
import type { EstadoVacante } from "@/types/vacantes"
import type { Empresa } from "@/types/empresa"

/**
 * La barra de filtros de /vacantes y el esqueleto de su tabla.
 *
 * Salieron de `vacantes/page.tsx`, que ya estaba en 178 contra un límite de 150 ANTES de esta
 * sesión (deuda anotada en CLAUDE.md) y llegaba a 193 al sumarle la paginación. Presentacional y
 * controlado: no tiene estado propio ni fetchea.
 *
 * ⚠️ Los dos `onChange` llaman a setters que además VUELVEN A LA PÁGINA 1. Eso vive en la página,
 * no acá: este componente no sabe que hay paginación, y no tiene por qué.
 */
const SELECT_CLASS =
  "min-h-[2rem] rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"

interface Props {
  mostrarEmpresa: boolean
  empresas: Empresa[]
  empresaFiltro: string
  onEmpresa: (v: string) => void
  estadoFiltro: EstadoVacante | ""
  onEstado: (v: EstadoVacante | "") => void
}

export function VacantesFiltros({
  mostrarEmpresa, empresas, empresaFiltro, onEmpresa, estadoFiltro, onEstado,
}: Props) {
  return (
    <div className="mb-4 flex flex-col gap-3 sm:flex-row">
      {mostrarEmpresa && (
        <select
          aria-label="Filtrar por empresa"
          className={SELECT_CLASS}
          value={empresaFiltro}
          onChange={(e) => onEmpresa(e.target.value)}
        >
          <option value="">Todas las empresas</option>
          {empresas.map((e) => (
            <option key={e.id} value={e.id}>{e.nombre}</option>
          ))}
        </select>
      )}
      <select
        aria-label="Filtrar por estado"
        className={SELECT_CLASS}
        value={estadoFiltro}
        onChange={(e) => onEstado(e.target.value as EstadoVacante | "")}
      >
        <option value="">Todos los estados</option>
        <option value="nueva">Nueva</option>
        <option value="en_proceso">En proceso</option>
        <option value="con_candidatos">Con candidatos</option>
        <option value="cerrada">Cerrada</option>
      </select>
    </div>
  )
}

export function VacantesTableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full rounded-lg" />
      ))}
    </div>
  )
}

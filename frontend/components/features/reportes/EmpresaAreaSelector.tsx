"use client"

import { useMemo } from "react"

import type { Area } from "@/types/area"
import type { Empresa } from "@/types/empresa"

const SELECT_CLS =
  "flex min-h-[2.75rem] w-full rounded-md border border-input bg-background px-2 py-1 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"

// Selector de empresa (+ área opcional) del ARMADO MANUAL. La empresa elegida acá es la que se
// manda al backend — NO se lee del selector del sidebar. Las áreas se filtran por la empresa elegida
// (el área solo tiene sentido dentro de una empresa; con "Todas las empresas" el área queda inhabilitada).
export function EmpresaAreaSelector({
  id,
  empresas,
  areas,
  empresaId,
  areaId,
  usaArea,
  onEmpresaChange,
  onAreaChange,
}: {
  id: string
  empresas: Empresa[]
  areas: Area[]
  empresaId: string
  areaId: string
  usaArea: boolean
  onEmpresaChange: (v: string) => void
  onAreaChange: (v: string) => void
}) {
  const areasEmpresa = useMemo(
    () => (empresaId ? areas.filter((a) => a.empresa_id === empresaId) : []),
    [areas, empresaId],
  )

  return (
    <div className="flex flex-col gap-2">
      <div>
        <label htmlFor={`empresa-${id}`} className="mb-1 block text-xs font-medium text-foreground">
          Empresa
        </label>
        <select
          id={`empresa-${id}`}
          value={empresaId}
          onChange={(e) => onEmpresaChange(e.target.value)}
          className={SELECT_CLS}
        >
          <option value="">Todas las empresas</option>
          {empresas.map((e) => (
            <option key={e.id} value={e.id}>{e.nombre}</option>
          ))}
        </select>
      </div>

      {usaArea && (
        <div>
          <label htmlFor={`area-${id}`} className="mb-1 block text-xs font-medium text-foreground">
            Área
          </label>
          <select
            id={`area-${id}`}
            value={areaId}
            onChange={(e) => onAreaChange(e.target.value)}
            disabled={!empresaId}
            className={SELECT_CLS}
          >
            <option value="">{empresaId ? "Todas las áreas" : "Elegí una empresa primero"}</option>
            {areasEmpresa.map((a) => (
              <option key={a.id} value={a.id}>{a.nombre}</option>
            ))}
          </select>
        </div>
      )}
    </div>
  )
}

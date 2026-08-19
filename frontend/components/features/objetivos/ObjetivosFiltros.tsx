"use client"

import type { UserItem } from "@/types/objetivo"
import type { Empresa } from "@/types/empresa"
import { Select } from "@/components/ui/select"

/**
 * La barra de filtros del tablero de objetivos. Presentacional y controlada: no tiene estado
 * propio ni dispara fetch — recibe los valores y los setters de la página.
 *
 * Extraída porque app/(dashboard)/objetivos/page.tsx estaba en 149/150 y no admitía una línea
 * más. El corte va por acá porque este es el lado que crece con el rediseño del modelo (la
 * jerarquía suma al menos un control para elegir si se muestran los subobjetivos).
 *
 * El movimiento fue PURO: los cuatro selects, sus clases, sus aria-label y el orden de las
 * opciones son idénticos a los que estaban embebidos en la página. No se cambió a `FiltersBar`
 * ni a `useFiltros<Modulo>` a propósito: eso es un rediseño del filtro, no una división.
 */

interface Props {
  mostrarEmpresa: boolean
  empresas: Empresa[]
  usuarios: UserItem[]
  empresaFiltro: string
  setEmpresaFiltro: (v: string) => void
  estadoFiltro: string
  setEstadoFiltro: (v: string) => void
  prioridadFiltro: string
  setPrioridadFiltro: (v: string) => void
  responsableFiltro: string
  setResponsableFiltro: (v: string) => void
}

export function ObjetivosFiltros({
  mostrarEmpresa, empresas, usuarios,
  empresaFiltro, setEmpresaFiltro, estadoFiltro, setEstadoFiltro,
  prioridadFiltro, setPrioridadFiltro, responsableFiltro, setResponsableFiltro,
}: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {mostrarEmpresa && empresas.length > 0 && (
        <Select size="sm" className="w-auto" value={empresaFiltro} onChange={(e) => setEmpresaFiltro(e.target.value)} aria-label="Empresa">
          <option value="">Todas las empresas</option>
          {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
        </Select>
      )}
      <Select size="sm" className="w-auto" value={estadoFiltro} onChange={(e) => setEstadoFiltro(e.target.value)} aria-label="Estado">
        <option value="">Todos los estados</option>
        <option value="por_hacer">Por hacer</option>
        <option value="haciendo">Haciendo</option>
        <option value="terminado">Terminado</option>
      </Select>
      <Select size="sm" className="w-auto" value={prioridadFiltro} onChange={(e) => setPrioridadFiltro(e.target.value)} aria-label="Prioridad">
        <option value="">Todas las prioridades</option>
        <option value="alta">Alta</option>
        <option value="media">Media</option>
        <option value="baja">Baja</option>
      </Select>
      {usuarios.length > 0 && (
        <Select size="sm" className="w-auto" value={responsableFiltro} onChange={(e) => setResponsableFiltro(e.target.value)} aria-label="Responsable">
          <option value="">Todos los responsables</option>
          {usuarios.map((u) => <option key={u.id} value={u.id}>{u.nombre} {u.apellido}</option>)}
        </Select>
      )}
    </div>
  )
}

"use client"

import { Plus } from "lucide-react"
import type { ReactNode } from "react"

import { ExportMenu } from "@/components/features/export/ExportMenu"
import { ImportarObjetivosBoton } from "@/components/features/objetivos/ImportarObjetivosBoton"
import { Button } from "@/components/ui/button"
import { exportarObjetivos, type ObjetivosFiltros } from "@/services/objetivos"
import type { FormatoExport } from "@/services/api"

/**
 * Las acciones del encabezado de /objetivos: exportar, importar y crear.
 *
 * Salieron de `objetivos/page.tsx` al migrarla al patrón del bloque B: con el panel de filtros y
 * los chips, el archivo pasaba de las 150 líneas. Presentacional: no tiene estado propio.
 *
 * 🔴 EL EXPORT MANDA EL MISMO OBJETO DE FILTROS QUE EL LISTADO — el mismo, no una copia con los
 * mismos campos. Es la invariante del bloque: si un filtro llegara a uno solo de los dos, el
 * archivo saldría con más filas de las que se ven en pantalla, sin error y sin aviso.
 * 🔑 Antes eran cuatro props sueltas (`estado`, `responsable`, `prioridad`, `empresaOverride`) y
 * el filtro de VISTA habría sido la quinta que alguien tenía que acordarse de agregar acá además
 * de en el listado. Con el objeto entero no hay nada que acordarse: `tipo` viajó gratis.
 *
 * ⚠️ La empresa del import sale del sidebar o del filtro: importar es una ACCIÓN y necesita una
 * empresa concreta —es contra ese padrón que se resuelven los responsables—. En consolidado el
 * botón queda deshabilitado, no oculto: que exista y no se pueda usar dice más que no verlo.
 */
export function ObjetivosAcciones({
  canWrite, filtros, sinEmpresa, onImportar, nuevoBtn,
}: {
  canWrite: boolean
  filtros: ObjetivosFiltros
  sinEmpresa: boolean
  onImportar: () => void
  nuevoBtn: ReactNode
}) {
  return (
    <div className="flex gap-2">
      <ExportMenu
        onExport={(f: FormatoExport) => exportarObjetivos(f, filtros)}
      />
      {canWrite && <ImportarObjetivosBoton sinEmpresa={sinEmpresa} onClick={onImportar} />}
      {canWrite && nuevoBtn}
    </div>
  )
}

/** El botón de alta, que la página también usa como acción del estado vacío. */
export function NuevoObjetivoBoton({ onClick }: { onClick: () => void }) {
  return (
    <Button className="min-h-11 gap-2" onClick={onClick}>
      <Plus className="size-4" /> Nuevo objetivo
    </Button>
  )
}

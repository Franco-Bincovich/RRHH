"use client"

import { useEffect, useMemo, useState } from "react"

import { destinatarios, type Destinatario } from "@/components/features/comunicacion/envioAcciones"

/**
 * El estado del modo "empleados del sistema": la búsqueda y quiénes están tildados.
 *
 * Hook aparte —y SIMÉTRICO con `useEnvioLibre`— porque `useEnvioPlantilla` pasó de 80 líneas al
 * sumarle el segundo modo. El corte cae en el mismo lugar en los dos casos: cada modo se lleva
 * su propio estado y `useEnvioPlantilla` queda solo orquestando cuál está activo.
 *
 * `elegidos` sale de `destinatarios(empleados, sel)`, que es EXACTAMENTE la función que arma el
 * body del envío: así el número que se confirma ("vas a enviar a N") no puede diferir del que se
 * manda, ni siquiera si alguien queda seleccionado y desaparece del listado.
 */
export function useSeleccionEmpleados(open: boolean, empleados: Destinatario[]) {
  const [search, setSearch] = useState("")
  const [sel, setSel] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (!open) return
    setSearch("")
    setSel(new Set())
  }, [open])

  const visibles = useMemo(() => {
    const q = search.trim().toLowerCase()
    return q ? empleados.filter((e) => `${e.nombre} ${e.apellido}`.toLowerCase().includes(q)) : empleados
  }, [empleados, search])

  function toggle(id: string) {
    setSel((prev) => {
      const n = new Set(prev)
      if (n.has(id)) n.delete(id)
      else n.add(id)
      return n
    })
  }

  return { search, setSearch, sel, toggle, visibles, elegidos: destinatarios(empleados, sel) }
}

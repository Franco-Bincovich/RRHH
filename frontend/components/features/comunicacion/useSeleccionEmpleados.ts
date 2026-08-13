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
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * 🔴 POR QUÉ ESTA BÚSQUEDA SIGUE SIENDO EN MEMORIA, Y NO SE CABLEÓ `EmpleadoCombobox` (13/8/2026)
 *
 * El defecto es real y se suma al de la lista: `empleados` viene de `useDestinatarios`, que trae
 * UNA página de 100, así que buscar a alguien que existe pero está fuera de esos 100 responde
 * "nadie coincide". Aun así **no se movió a búsqueda contra el backend**, y no por costo:
 *
 * `destinatarios(empleados, sel)` INTERSECA la selección con la lista que tiene a mano
 * (`envioAcciones.ts:33`). Con la lista viniendo del servidor por término, quien fue tildado en
 * una búsqueda **desaparece de `empleados` al escribir la siguiente**, y con él su id sale del
 * body del envío — en silencio, y el cartel de confirmación diría el número ya recortado. Sería
 * cambiar "no encuentro a esta persona" por "el comunicado no le llegó y nadie se enteró", que
 * es estrictamente peor.
 *
 * LO QUE HACE FALTA para hacerlo bien, para que no haya que rediseñarlo desde cero: que la
 * selección deje de ser un `Set<string>` de ids y pase a ser un `Map<id, Destinatario>` que
 * sobreviva a los cambios de la lista. Ahí `elegidos` deja de depender de `empleados` y la
 * búsqueda server-side entra sin riesgo. Es una tanda propia.
 *
 * MIENTRAS TANTO, la pantalla lo DICE: `EnvioDestinatarios` avisa cuántos activos quedaron fuera
 * de la lista (`total` vs `traidos`). El recorte sigue estando; lo que ya no está es el silencio.
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

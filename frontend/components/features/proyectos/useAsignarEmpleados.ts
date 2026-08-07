"use client"

import { useEffect, useMemo, useState } from "react"

import { enviarArea, enviarSeleccion } from "@/components/features/proyectos/asignarAcciones"
import { useCandidatosProyecto } from "@/components/features/proyectos/useCandidatosProyecto"

/**
 * Qué está elegido en el alta múltiple, y qué se hace con eso.
 *
 * La CARGA de candidatos vive en `useCandidatosProyecto` y los ENVÍOS en `asignarAcciones`: acá
 * queda el estado del formulario y la selección. El corte salió de que este hook pasó de 80
 * líneas al sumarle el alta por área.
 *
 * 🔴 `yaEnElProyecto` y `faltan` NO cuestan un request: salen de `empleados` —los candidatos del
 * área, que ya se piden server-side— y de `yaAsignadosIds`, que llega por prop desde EquipoTab,
 * que los tiene para su propia lista. Es lo que hace que el resumen del área sea gratis.
 */
export function useAsignarEmpleados(
  open: boolean, proyectoId: string, yaAsignadosIds: string[], onSuccess: () => void,
) {
  const [areaFiltro, setAreaFiltro] = useState("")
  const [search, setSearch] = useState("")
  const [sel, setSel] = useState<Set<string>>(new Set())
  const [rol, setRol] = useState("")
  const [valorHora, setValorHora] = useState("0")
  const [fechaDesde, setFechaDesde] = useState("")
  const [fechaHasta, setFechaHasta] = useState("")
  const [saving, setSaving] = useState(false)
  const [asignandoArea, setAsignandoArea] = useState(false)

  const { empleados, areas, error: errorCandidatos, recargar: recargarCandidatos } = useCandidatosProyecto(open, areaFiltro)

  useEffect(() => {
    if (!open) return
    setSel(new Set()); setSearch(""); setAreaFiltro(""); setRol("")
    setValorHora("0"); setFechaDesde(""); setFechaHasta("")
  }, [open])

  const yaEnElProyecto = useMemo(
    () => empleados.filter((e) => yaAsignadosIds.includes(e.id)).length,
    [empleados, yaAsignadosIds])
  const faltan = empleados.length - yaEnElProyecto

  const visibles = useMemo(() => {
    const q = search.trim().toLowerCase()
    return q ? empleados.filter((e) => `${e.nombre} ${e.apellido}`.toLowerCase().includes(q)) : empleados
  }, [empleados, search])

  const allSelected = visibles.length > 0 && visibles.every((e) => sel.has(e.id))

  function toggle(id: string) {
    setSel((prev) => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n })
  }
  function toggleAll() {
    setSel((prev) => { const n = new Set(prev); visibles.forEach((e) => allSelected ? n.delete(e.id) : n.add(e.id)); return n })
  }

  async function handleSubmit() {
    if (sel.size === 0 || !rol.trim()) return
    setSaving(true)
    if (await enviarSeleccion(proyectoId, [...sel], { rol, valorHora, fechaDesde, fechaHasta })) onSuccess()
    setSaving(false)
  }

  async function handleAsignarArea() {
    if (!areaFiltro || !rol.trim()) return
    setAsignandoArea(true)
    if (await enviarArea(proyectoId, areaFiltro, { rol, valorHora, fechaDesde, fechaHasta })) onSuccess()
    setAsignandoArea(false)
  }

  return {
    empleados, areas, areaFiltro, setAreaFiltro, search, setSearch, sel, rol, setRol,
    valorHora, setValorHora, fechaDesde, setFechaDesde, fechaHasta, setFechaHasta,
    saving, asignandoArea, yaEnElProyecto, faltan, visibles, allSelected,
    toggle, toggleAll, handleSubmit, handleAsignarArea, errorCandidatos, recargarCandidatos,
  }
}

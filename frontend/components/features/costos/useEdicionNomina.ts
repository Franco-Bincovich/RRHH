"use client"

import { useState } from "react"

import { cargarNomina } from "@/services/costos"
import type { Nomina } from "@/types/costo"

/**
 * El modal de edición de una fila de nómina: qué fila, los dos montos, y el guardado.
 *
 * Hook aparte de `useNominaLista` porque son dos responsabilidades con ciclos de vida distintos
 * —la lista se recarga al cambiar de página, la edición no— y juntas pasaban el límite de 80.
 * Mismo criterio que `useSeleccionEmpleados`, que salió de `useEnvioPlantilla` por lo mismo.
 *
 * ⚠️ `onGuardado` dispara DOS recargas en el caller: la lista (la fila cambió) y el dashboard
 * (los KPIs salen de otra consulta). Editar un sueldo y refrescar solo la lista dejaría el
 * "Costo total nómina" con el número viejo, que es peor que no refrescar nada — el usuario ve el
 * cambio aplicado en la tabla y el total sin moverse, y no tiene forma de saber cuál miente.
 */
export function useEdicionNomina(mes: number, anio: number, onGuardado: () => Promise<void> | void) {
  const [item, setItem] = useState<Nomina | null>(null)
  const [bruto, setBruto] = useState("")
  const [neto, setNeto] = useState("")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")

  function open(fila: Nomina) {
    setItem(fila)
    setBruto(String(fila.monto_bruto))
    setNeto(String(fila.monto_neto))
    setError("")
  }

  async function save() {
    if (!item) return
    setSaving(true)
    setError("")
    try {
      await cargarNomina({
        empleado_id: item.empleado_id,
        mes,
        anio,
        monto_bruto: Number(bruto),
        monto_neto: Number(neto),
      })
      setItem(null)
      await onGuardado()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "No se pudo guardar. Intentá de nuevo.")
    } finally {
      setSaving(false)
    }
  }

  return { item, setItem, bruto, setBruto, neto, setNeto, saving, error, open, save }
}

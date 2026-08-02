"use client"

import { useCallback, useEffect, useState } from "react"
import { Link2Off, RefreshCw } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useCanWrite } from "@/hooks/useCanWrite"
import {
  fetchSuperioresPendientes,
  resolverSuperioresPendientes,
} from "@/services/superioresPendientes"
import type { SuperiorPendienteItem } from "@/types/importacion"

/**
 * Superiores que el import de nómina no pudo resolver, y el botón para reintentarlos.
 *
 * 🔴 SE AUTO-OCULTA CUANDO NO HAY NADA PENDIENTE (`total === 0`), que es el estado normal. No es
 * una sección del menú ni una pantalla: es un aviso que aparece solo cuando hay algo que hacer.
 * Con 0 pendientes, un panel vacío permanente sería ruido en la pantalla más usada del sistema.
 *
 * Por qué hace falta: el CSV trae el nombre del jefe, pero en el archivo real 5 de los 6 jefes NO
 * están cargados como empleados. El import guarda el nombre crudo; cuando RRHH da de alta al que
 * faltaba, este botón completa los `manager_id` sin volver a subir el archivo. Y sin `manager_id`
 * un usuario `mandos_medios` no ve absolutamente nada: su ownership se resuelve por ese campo.
 *
 * Un fallo al leer NO se muestra: el panel simplemente no aparece. Es información
 * complementaria del listado de empleados, y un cartel de error por algo que el usuario no pidió
 * distrae de la pantalla en la que está.
 */
export function SuperioresPendientesPanel({ onResuelto }: { onResuelto?: () => void }) {
  const canWrite = useCanWrite()
  const [items, setItems] = useState<SuperiorPendienteItem[]>([])
  const [resolviendo, setResolviendo] = useState(false)
  const [ultimoResueltos, setUltimoResueltos] = useState<number | null>(null)

  const cargar = useCallback(async () => {
    try {
      const res = await fetchSuperioresPendientes()
      setItems(res.items)
    } catch {
      setItems([])
    }
  }, [])

  useEffect(() => { void cargar() }, [cargar])

  async function handleResolver() {
    setResolviendo(true)
    try {
      const res = await resolverSuperioresPendientes()
      setItems(res.pendientes)
      setUltimoResueltos(res.resueltos)
      // El listado de empleados muestra el superior: si se asignó alguno, quedó desactualizado.
      if (res.resueltos > 0) onResuelto?.()
    } catch {
      // El estado no cambia: lo que se ve sigue siendo lo último confirmado por el backend.
    } finally {
      setResolviendo(false)
    }
  }

  if (items.length === 0) {
    // Se resolvió todo en este mismo clic: se confirma y recién después desaparece. Sin esto, el
    // panel se esfuma sin decir qué pasó y el usuario no sabe si funcionó.
    if (ultimoResueltos && ultimoResueltos > 0) {
      return (
        <p className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-100">
          Se asignaron {ultimoResueltos} superior{ultimoResueltos !== 1 ? "es" : ""}. No queda ninguno pendiente.
        </p>
      )
    }
    return null
  }

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-950">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-1.5 text-sm font-medium text-amber-900 dark:text-amber-100">
          <Link2Off className="size-4 shrink-0" />
          {items.length} empleado{items.length !== 1 ? "s" : ""} sin superior asignado
        </p>
        {canWrite && (
          <Button
            variant="outline"
            size="sm"
            className="min-h-9 gap-1.5"
            onClick={handleResolver}
            disabled={resolviendo}
          >
            <RefreshCw className={`size-4${resolviendo ? " animate-spin" : ""}`} />
            {resolviendo ? "Resolviendo..." : "Resolver pendientes"}
          </Button>
        )}
      </div>
      <p className="mt-1.5 text-sm text-amber-900 dark:text-amber-100">
        El import leyó el superior del archivo pero no lo encontró entre los empleados cargados.
        Dalos de alta y volvé a intentar — no hace falta subir el CSV otra vez.
      </p>
      <ul className="mt-2 space-y-1 text-sm text-amber-900 dark:text-amber-100" role="list">
        {items.map((p) => (
          <li key={p.empleado_id}>
            {p.empleado} → <strong>{p.superior}</strong> ({p.motivo})
          </li>
        ))}
      </ul>
    </div>
  )
}

"use client"

import { useEffect, useState } from "react"

import { Historial } from "@/components/ui/Historial"
import { Skeleton } from "@/components/ui/skeleton"
import { Section } from "@/components/features/empleados/ficha/_primitives"
import { entradasHistorial } from "@/components/features/recategorizaciones/_cambios"
import { fetchHistorialRecategorizaciones } from "@/services/recategorizaciones"
import type { Recategorizacion } from "@/types/recategorizacion"

/**
 * El historial de recategorizaciones del colaborador, en su ficha: cuándo le cambió el rol, la
 * seniority o la categoría, de qué valor a cuál y por qué.
 *
 * 🔴 USA `components/ui/Historial`, EL MISMO PRIMITIVO QUE EL HISTORIAL SALARIAL. Es lista y no
 * tabla (§3): un historial se lee por la fecha y por el salto de un valor a otro, no por
 * columnas. Y el chip **"Vigente"** lo decide el primitivo —la primera entrada de la lista— y no
 * este componente: marcar todos o ninguno es el error obvio, y dejarlo en manos de cada pantalla
 * lo garantiza en la tercera. La lista llega ordenada de más reciente a más antigua desde el
 * backend y NO se reordena acá.
 *
 * 🔴 NO SE GATEA POR COSTOS, a diferencia de `HistorialSalarialSection`. El backend tampoco gatea
 * la ruta: el historial de rol y seniority le sirve a cualquiera que pueda ver el legajo y es el
 * 90% del valor del módulo. Lo único que depende de COSTOS es `impacto_salarial`, que **este
 * panel no muestra** — la ficha contesta "qué cambió y por qué", el monto se mira en la planilla.
 *
 * ⚠️ EL PANEL SE RENDERIZA AUNQUE NO HAYA NADA, con su texto de vacío. Hoy es el caso de los 31
 * colaboradores: esconderlo dejaría a alguien buscando dónde se registra un cambio de categoría.
 *
 * ⚠️ SIN ACCIÓN DE BORRAR NI DE EDITAR. El backend no publica DELETE (rompería la cadena de
 * valores anteriores) y editar se hace desde la planilla, que es donde está el formulario. Un
 * panel de ficha que abriera un modal de escritura duplicaría ese formulario en dos lugares.
 */
export function RecategorizacionesSection({ empleadoId }: { empleadoId: string }) {
  const [items, setItems] = useState<Recategorizacion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!empleadoId) return
    let cancelado = false
    setLoading(true)
    setError(false)
    fetchHistorialRecategorizaciones(empleadoId)
      .then((res) => { if (!cancelado) setItems(res) })
      .catch(() => { if (!cancelado) setError(true) })
      .finally(() => { if (!cancelado) setLoading(false) })
    return () => { cancelado = true }
  }, [empleadoId])

  return (
    <Section title="Recategorizaciones">
      <div className="col-span-full">
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : error ? (
          <p className="text-sm text-muted-foreground">
            No se pudo cargar el historial de recategorizaciones.
          </p>
        ) : (
          <Historial
            entradas={entradasHistorial(items)}
            vacio="Todavía no se registraron recategorizaciones de esta persona."
          />
        )}
      </div>
    </Section>
  )
}

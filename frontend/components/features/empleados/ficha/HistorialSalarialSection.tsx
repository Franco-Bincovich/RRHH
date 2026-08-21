"use client"

import { useEffect, useState } from "react"

import { Historial } from "@/components/ui/Historial"
import { Skeleton } from "@/components/ui/skeleton"
import { Section } from "@/components/features/empleados/ficha/_primitives"
import { cambiosSalariales, resumenSerie } from "@/components/features/empleados/ficha/_cambiosSalariales"
import { useCanRead } from "@/hooks/useCanWrite"
import { fetchHistorialSalarial } from "@/services/costos"
import type { HistorialSalarialItem } from "@/types/costo"

/**
 * ¿Corresponde pedir la serie al backend?
 *
 * Función aparte y exportada porque vive dentro de un `useEffect`, y el proyecto corre vitest
 * SIN jsdom: en un render a string los efectos no se ejecutan, así que un test que mirara "no
 * llamó al fetch" pasaría siempre, incluso con el guard borrado. Sacándola acá la decisión se
 * verifica de verdad.
 *
 * Sin permiso NO se pide: ocultar el bloque pero consultar igual dejaría el 403 en la red, que
 * confirma que la serie existe.
 */
export function debeCargar(empleadoId: string, puedeVerCostos: boolean): boolean {
  return Boolean(empleadoId) && puedeVerCostos
}

/**
 * Historial salarial del empleado en su ficha: un renglón por período con sueldo cargado.
 *
 * SEPARADA DE HistorialCambiosSection, no fusionada, por dos razones concretas:
 *  · las fuentes se paginan server-side por separado y dos streams paginados no se fusionan
 *    en uno solo sin traerse todo de ambos lados;
 *  · las formas no son compatibles — un evento de auditoría tiene usuario, acción y diff; una
 *    fila de nómina tiene período y monto. Una tabla que sirva para las dos no sirve para
 *    ninguna.
 *
 * NO SALE DEL LOG DE CAMBIOS, sale de los datos. `costos_nomina` guarda una fila por empleado
 * por mes (UNIQUE empleado_id, anio, mes), así que la progresión ya está ahí. Con auditoría,
 * el caso más común —sueldos importados por CSV y nunca editados a mano— mostraría un
 * historial vacío teniendo los sueldos cargados.
 *
 * ⚠️ El sueldo es un dato de COSTOS y la ficha vive bajo EMPLEADOS: la sección no se renderiza
 * si el rol no puede leer costos. Hoy no existe un rol así, pero el día que exista la ficha no
 * puede volverse la puerta de atrás a los sueldos. El backend gatea igual.
 */
export function HistorialSalarialSection({ empleadoId }: { empleadoId: string }) {
  const puedeVerCostos = useCanRead("costos")
  const [items, setItems] = useState<HistorialSalarialItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!debeCargar(empleadoId, puedeVerCostos)) return
    let cancelado = false
    setLoading(true)
    setError(false)
    fetchHistorialSalarial(empleadoId)
      .then((res) => { if (!cancelado) setItems(res) })
      .catch(() => { if (!cancelado) setError(true) })
      .finally(() => { if (!cancelado) setLoading(false) })
    return () => { cancelado = true }
  }, [empleadoId, puedeVerCostos])

  if (!puedeVerCostos) return null

  const cambios = cambiosSalariales(items)

  return (
    <Section title="Historial salarial">
      <div className="col-span-full">
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : error ? (
          <p className="text-sm text-muted-foreground">
            No se pudo cargar el historial salarial.
          </p>
        ) : items.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Todavía no hay sueldos cargados para este colaborador.
          </p>
        ) : (
          <>
            {/* 🔴 LISTA, NO TABLA (§3): un historial se lee por la fecha y por el salto de un
                valor a otro, no por columnas. La derivación —qué meses son un cambio real— vive
                en `_cambiosSalariales.ts`, que es puro y se testea sin renderizar. */}
            <Historial entradas={cambios} vacio="Todavía no hay sueldos cargados." />
            <p className="mt-3 text-xs text-muted-foreground">{resumenSerie(items, cambios.length)}</p>
          </>
        )}
      </div>
    </Section>
  )
}

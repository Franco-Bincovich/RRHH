"use client"

import { useEffect, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { Section } from "@/components/features/empleados/ficha/_primitives"
import { fetchAsignaciones } from "@/services/inventario"
import type { Asignacion } from "@/types/inventario"

const DEVOLUCION_LABEL: Record<string, string> = {
  ok: "Devuelto en buen estado",
  "con_daño": "Devuelto con daño",
}

/** Texto del estado de una asignación: en uso, o devuelto (con su detalle) en la fecha dada. */
function estadoDevolucion(a: Asignacion): { texto: string; enUso: boolean } {
  if (!a.fecha_devolucion) return { texto: "En uso", enUso: true }
  const detalle = a.estado_devolucion ? DEVOLUCION_LABEL[a.estado_devolucion] : "Devuelto"
  return { texto: `${detalle} el ${a.fecha_devolucion}`, enUso: false }
}

/**
 * Sección autoabastecida: lista el inventario asignado a un empleado en su ficha.
 * Hace su propio fetch (GET /inventario/asignaciones?empleado_id=) y maneja loading/vacío/error.
 * Solo lectura; la gestión de asignaciones vive en el módulo de Inventario.
 */
export function InventarioSection({ empleadoId }: { empleadoId: string }) {
  const [asignaciones, setAsignaciones] = useState<Asignacion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!empleadoId) return
    let cancelled = false
    setLoading(true)
    setError(false)
    fetchAsignaciones({ empleadoId })
      .then((res) => { if (!cancelled) setAsignaciones(res.items) })
      .catch(() => { if (!cancelled) setError(true) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [empleadoId])

  return (
    <Section title="Inventario asignado">
      <div className="col-span-full">
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : error ? (
          <p className="text-sm text-muted-foreground">
            No se pudo cargar el inventario asignado.
          </p>
        ) : asignaciones.length === 0 ? (
          <p className="text-sm text-muted-foreground">Sin inventario asignado.</p>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Equipo</TableHead>
                  <TableHead>N° de serie</TableHead>
                  <TableHead>Asignado el</TableHead>
                  <TableHead>Estado</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {asignaciones.map((a) => {
                  const estado = estadoDevolucion(a)
                  return (
                    <TableRow key={a.id}>
                      <TableCell>
                        <span className="font-medium text-foreground">{a.item_nombre ?? "—"}</span>
                        {a.item_tipo && (
                          <span className="block text-xs text-muted-foreground">{a.item_tipo}</span>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {a.item_numero_serie ?? "—"}
                      </TableCell>
                      <TableCell className="whitespace-nowrap">{a.fecha_asignacion}</TableCell>
                      <TableCell>
                        {/* 🔴 NO ES AZUL: `variant="default"` es `bg-primary`, el relleno que
                            §3 le reserva al chip de filtro — y acá eran SEIS pastillas azules
                            sólidas en la tabla de la ficha, compitiendo con el botón primario
                            de la barra de identidad que está justo arriba. "En uso" es un
                            estado VIGENTE, así que va con el par de éxito, el mismo que
                            `ImagenCard` eligió para "Principal" por el mismo motivo. */}
                        <Badge
                          variant="outline"
                          className={estado.enUso ? "bg-success-wash text-success border-success-line" : undefined}
                        >
                          {estado.texto}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </Section>
  )
}

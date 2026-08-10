"use client"

import { useCallback, useEffect, useState } from "react"
import { Trash2 } from "lucide-react"
import { toast } from "sonner"

import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { deleteCargaHoras, fetchDetalleEmpleado, type HorasClienteFiltros } from "@/services/horasCliente"
import { formatFechaCorta, textoDeCarga } from "@/components/features/horasCliente/detalleFormato"
import type { Hora } from "@/types/proyecto"

interface Props {
  empleadoId: string | null
  empleadoNombre: string
  filtros: HorasClienteFiltros
  canWrite: boolean
  onClose: () => void
  onBorrado: () => void
}

/**
 * "Ver detalle": las cargas DÍA POR DÍA de un empleado, con la opción de borrar cada una.
 *
 * 🔴 NO HAY EDITAR, y no es que falte. `HorasService` declara los registros inmutables por
 * decisión escrita; agregar un update es revocarla, no sumar una feature. El costo real está
 * enumerado en `services/horas_cliente_service.py::_QUE_FALTARIA_PARA_EDITAR`.
 *
 * ⚠️ Este componente usa `Dialog` de Radix, que monta por PORTAL: con vitest sin jsdom,
 * `renderToStaticMarkup` devuelve "". Por eso lo que se testea son las funciones puras que
 * decide (`detalleFormato`), no el markup — un test de este componente pasaría con el contenido
 * entero borrado.
 */
export function DetalleEmpleadoModal(
  { empleadoId, empleadoNombre, filtros, canWrite, onClose, onBorrado }: Props,
) {
  const [items, setItems] = useState<Hora[]>([])
  const [loading, setLoading] = useState(false)
  const [borrando, setBorrando] = useState<string | null>(null)

  const cargar = useCallback(async () => {
    if (!empleadoId) return
    setLoading(true)
    try {
      setItems((await fetchDetalleEmpleado(empleadoId, filtros)).items)
    } catch {
      toast.error("No se pudo cargar el detalle.")
    } finally {
      setLoading(false)
    }
  }, [empleadoId, filtros])

  useEffect(() => { void cargar() }, [cargar])

  async function borrar(id: string) {
    setBorrando(id)
    try {
      await deleteCargaHoras(id)
      await cargar()
      onBorrado()
    } catch {
      toast.error("No se pudo eliminar la carga.")
    } finally {
      setBorrando(null)
    }
  }

  return (
    <Dialog open={Boolean(empleadoId)} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Cargas de {empleadoNombre}</DialogTitle>
        </DialogHeader>
        {loading ? (
          <p className="text-sm text-muted-foreground">Cargando...</p>
        ) : items.length === 0 ? (
          <p className="text-sm text-muted-foreground">Sin cargas en el período.</p>
        ) : (
          <div className="max-h-96 space-y-1 overflow-y-auto">
            {items.map((h) => (
              <div key={h.id} className="flex items-center justify-between gap-3 rounded-md border p-2 text-sm">
                <div className="min-w-0">
                  <span className="font-medium tabular-nums">{formatFechaCorta(h.fecha)}</span>
                  <span className="ml-2 tabular-nums">{h.horas} h</span>
                  <span className="ml-2 text-xs text-muted-foreground">{textoDeCarga(h)}</span>
                </div>
                {canWrite && (
                  <Button variant="ghost" size="icon" aria-label={`Eliminar carga del ${h.fecha}`}
                          disabled={borrando === h.id} onClick={() => borrar(h.id)}>
                    <Trash2 className="size-4 text-destructive" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

"use client"

import { useEffect, useState } from "react"

import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import {
  ENTIDAD_LABEL, EVENTO_LABEL, SIN_CAMBIOS_AUDITADOS, campoLabel, clavesVisibles,
  formatCampoValor, formatFechaHora, soloTraiaDerivados,
} from "@/components/features/auditoria/auditLabels"
import { fetchAreas } from "@/services/areas"
import type { AuditLog } from "@/types/auditoria"

interface AuditDetailModalProps {
  log: AuditLog | null
  onClose: () => void
}

/**
 * Detalle de un evento de auditoría. Muestra cada campo como "Etiqueta: valor" (alta/baja)
 * o "Etiqueta: antes → después" (modificación), con valores formateados (sin JSON crudo).
 */
export function AuditDetailModal({ log, onClose }: AuditDetailModalProps) {
  const antes = log?.datos_anteriores ?? {}
  const nuevos = log?.datos_nuevos ?? {}
  // Las claves derivadas de joins quedan afuera: ver CAMPOS_DERIVADOS en auditLabels.
  const keys = clavesVisibles(antes, nuevos)
  const sinCambiosReales = soloTraiaDerivados(antes, nuevos)
  const esUpdate = Object.keys(antes).length > 0 && Object.keys(nuevos).length > 0
  const titulo = log ? (EVENTO_LABEL[log.evento] ?? log.evento) : ""

  // Las áreas se piden SOLO si el evento abierto tiene un area_id que traducir: la mayoría
  // no lo tiene, y el modal está montado (cerrado) en toda la ficha de empleado.
  const [areas, setAreas] = useState<Record<string, string> | null>(null)
  const necesitaAreas = keys.includes("area_id")

  useEffect(() => {
    if (!necesitaAreas || areas !== null) return
    let cancelado = false
    fetchAreas()
      .then((as) => {
        if (!cancelado) setAreas(Object.fromEntries(as.map((a) => [a.id, a.nombre])))
      })
      // Sin áreas el detalle igual se muestra: un mapa vacío degrada a "Área eliminada (id…)",
      // que es preferible a no poder abrir el evento.
      .catch(() => { if (!cancelado) setAreas({}) })
    return () => { cancelado = true }
  }, [necesitaAreas, areas])

  let encabezadoCambios = "Cambios"
  if (!esUpdate && Object.keys(nuevos).length > 0) encabezadoCambios = "Datos registrados"
  else if (!esUpdate && Object.keys(antes).length > 0) encabezadoCambios = "Valores antes de eliminar"

  return (
    <Dialog open={log !== null} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{titulo}</DialogTitle>
        </DialogHeader>

        {log && (
          <div className="space-y-4">
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
              <dt className="text-muted-foreground">Fecha</dt>
              <dd>{formatFechaHora(log.created_at)}</dd>
              <dt className="text-muted-foreground">Usuario</dt>
              <dd>{log.usuario_nombre ?? "Sistema"}</dd>
              <dt className="text-muted-foreground">Empresa</dt>
              <dd>{log.empresa_nombre ?? "—"}</dd>
              <dt className="text-muted-foreground">Sección</dt>
              <dd>{ENTIDAD_LABEL[log.entidad] ?? log.entidad}</dd>
            </dl>

            <div>
              <h4 className="mb-2 text-sm font-semibold text-foreground">{encabezadoCambios}</h4>
              {keys.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  {sinCambiosReales ? SIN_CAMBIOS_AUDITADOS : "Sin datos de detalle."}
                </p>
              ) : (
                <ul className="space-y-1.5 text-sm" role="list">
                  {keys.map((k) => (
                    <li key={k} className="flex flex-wrap gap-x-2">
                      <span className="font-medium">{campoLabel(k)}:</span>
                      {esUpdate ? (
                        <span>
                          <span className="text-muted-foreground line-through">
                            {formatCampoValor(k, antes[k], areas)}
                          </span>
                          {" → "}
                          <span>{formatCampoValor(k, nuevos[k], areas)}</span>
                        </span>
                      ) : (
                        <span>
                          {formatCampoValor(
                            k, Object.keys(nuevos).length > 0 ? nuevos[k] : antes[k], areas,
                          )}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

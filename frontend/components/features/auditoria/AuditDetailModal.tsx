"use client"

import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import {
  ENTIDAD_LABEL, EVENTO_LABEL, SIN_CAMBIOS_AUDITADOS, campoLabel, clavesVisibles,
  formatFechaHora, formatValor, soloTraiaDerivados,
} from "@/components/features/auditoria/auditLabels"
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

  let encabezadoCambios = "Cambios"
  if (!esUpdate && Object.keys(nuevos).length > 0) encabezadoCambios = "Datos registrados"
  else if (!esUpdate && Object.keys(antes).length > 0) encabezadoCambios = "Valores antes de eliminar"

  return (
    <Dialog open={log !== null} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      <DialogContent className="max-h-[90vh] max-w-lg overflow-y-auto">
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
                          <span className="text-muted-foreground line-through">{formatValor(antes[k])}</span>
                          {" → "}
                          <span>{formatValor(nuevos[k])}</span>
                        </span>
                      ) : (
                        <span>{formatValor(Object.keys(nuevos).length > 0 ? nuevos[k] : antes[k])}</span>
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

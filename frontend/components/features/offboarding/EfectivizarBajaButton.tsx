"use client"

import { useState } from "react"
import { toast } from "sonner"
import { UserMinus } from "lucide-react"

import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { MOTIVO_LABEL } from "@/components/features/offboarding/_offboardingLabels"
import { ApiError } from "@/services/api"
import { efectivizarBaja } from "@/services/offboarding"
import type { OffboardingInstancia } from "@/types/offboarding"

/**
 * "Confirmar baja": el acto que da de baja al empleado y cierra el proceso de offboarding.
 *
 * 🔴 ES IRREVERSIBLE DESDE LA UI y es el único camino que pone a alguien en `estado='baja'`.
 * Abrir el trámite ya no lo hace: hasta que esto corre, la persona sigue contando en headcount,
 * organigrama, ausentismo y saldo de vacaciones. Por eso el diálogo dice qué va a pasar antes de
 * que pase, y el botón que lo dispara es `destructive`.
 *
 * 🔴 POR QUÉ UN Dialog PROPIO Y NO `ConfirmDialog`. Este acto necesita un DATO —la fecha real de
 * egreso— y `ConfirmDialog` no acepta children: solo título, descripción y botones. Encadenar
 * "pedir fecha" y después "confirmar" en dos modales sería peor que un modal que muestra la
 * consecuencia y el campo juntos, que es donde el usuario tiene que decidir. Cumple la misma
 * función: nada se escribe hasta el segundo clic, y ese botón dice qué hace.
 *
 * ⚠️ EL `max` DEL INPUT ES LA UI IMPIDIENDO LA FECHA FUTURA, no la validación. La de verdad la
 * hace el backend (`FECHA_EGRESO_FUTURA`), y su mensaje se muestra igual si llega — un `max` de
 * HTML se saltea con devtools y no dice nada sobre el otro rechazo posible, el de una fecha
 * anterior al ingreso (`FECHA_EGRESO_INVALIDA`), que acá no se puede anticipar: la instancia no
 * trae la `fecha_ingreso` del empleado, solo la del trámite.
 */
export function EfectivizarBajaButton(
  { instancia, onEfectivizada }: {
    instancia: OffboardingInstancia; onEfectivizada: (id: string) => void
  },
) {
  const hoy = new Date().toISOString().slice(0, 10)
  const [open, setOpen] = useState(false)
  const [fecha, setFecha] = useState(hoy)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState("")

  function cerrar() {
    setOpen(false); setError(""); setFecha(hoy); setGuardando(false)
  }

  async function confirmar() {
    setGuardando(true); setError("")
    try {
      await efectivizarBaja(instancia.id, fecha)
      toast.success(`Baja de ${instancia.empleado_nombre} registrada`)
      cerrar()
      onEfectivizada(instancia.id)
    } catch (e) {
      // El mensaje del backend, tal cual: los dos errores de fecha dicen exactamente qué
      // corregir, y los dos 409 (proceso ya cerrado, empleado ya de baja) dicen que otra
      // pestaña se adelantó. Un genérico acá obliga a adivinar cuál de los cuatro fue.
      setError(e instanceof ApiError ? e.message : "No se pudo registrar la baja.")
    } finally {
      setGuardando(false)
    }
  }

  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        className="min-h-11 gap-1.5 text-destructive hover:bg-destructive/10 hover:text-destructive"
        onClick={() => setOpen(true)}
      >
        <UserMinus className="size-4" /> Confirmar baja
      </Button>

      <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) cerrar() }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Confirmar la baja de {instancia.empleado_nombre}</DialogTitle>
          </DialogHeader>

          <div className="flex flex-col gap-4 py-2">
            <p className="text-sm text-muted-foreground">
              {MOTIVO_LABEL[instancia.motivo] ?? instancia.motivo}. Al confirmar, la persona pasa
              a estado <strong className="text-foreground">baja</strong> y deja de contar en
              headcount, organigrama, ausentismo y saldo de vacaciones. El proceso de offboarding
              se cierra. <strong className="text-foreground">No se puede deshacer.</strong>
            </p>

            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-foreground">Último día trabajado</span>
              <input
                type="date"
                value={fecha}
                max={hoy}
                onChange={(e) => setFecha(e.target.value)}
                className="min-h-11 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
              />
              {/* La previsión que se cargó al abrir el trámite se muestra como referencia, no
                  como valor por defecto: el default es HOY porque lo normal es confirmar la baja
                  el día que ocurre, y arrancar con la previsión invitaría a aceptarla sin
                  mirarla — que es justamente cómo se pierde el dato de cuánto se desvió. */}
              <span className="text-xs text-muted-foreground">
                Previsto al abrir el proceso: {instancia.fecha_inicio}
              </span>
            </label>

            {error && (
              <p className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive" role="alert">
                {error}
              </p>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" className="min-h-11" onClick={cerrar} disabled={guardando}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              className="min-h-11"
              onClick={confirmar}
              disabled={guardando || !fecha}
            >
              {guardando ? "Registrando..." : "Confirmar baja"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

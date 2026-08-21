"use client"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import type { useEdicionNomina } from "@/components/features/costos/useEdicionNomina"

/**
 * El modal de edición de una fila de nómina.
 *
 * Salió de `NominaSection.tsx` al migrar esa tabla al patrón del bloque B: con el esqueleto, el
 * vacío y el pie nuevos, el archivo llegaba a 183 líneas contra un límite de 150. El corte es por
 * responsabilidad —la tabla lista, el modal edita— y el estado sigue viviendo entero en
 * `useEdicionNomina`, que es quien sabe guardar.
 *
 * ⚠️ ESTE MODAL NO TIENE LA VALIDACIÓN EN DOS NIVELES DEL PATRÓN, y no es un olvido: no tiene
 * NINGUNO de los dos. No hay un mensaje por campo —hay un único `ed.error` que viene del servidor
 * y se muestra abajo—, así que un banner `<FormErrores>` diría "Revisá 0 campos" siempre, que es
 * peor que no tenerlo. Construir la validación de este formulario (bruto ≥ 0, neto ≤ bruto) es una
 * tanda propia; está reportado.
 */
export function EditarNominaModal({ ed }: { ed: ReturnType<typeof useEdicionNomina> }) {
  return (
    <Dialog open={ed.item !== null} onOpenChange={(open) => { if (!open) ed.setItem(null) }}>
      {/* El ancho (560px) y los campos de 34px los pone el patrón, no el modal. */}
      <DialogContent patron="formulario">
        <DialogHeader>
          <DialogTitle>Editar nómina — {ed.item?.empleado_nombre}</DialogTitle>
          {/* 🔴 UNA LÍNEA QUE EXPLICA LA CONSECUENCIA, no lo que el modal es (§3). Lo que el
              usuario no puede deducir de dos campos de números es que ese sueldo alimenta los
              KPIs de arriba, la masa salarial del dashboard y el historial salarial del legajo. */}
          <DialogDescription>
            El monto corregido se ve al instante en los costos del período, en la masa salarial del
            dashboard y en el historial salarial de esa persona.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="edit-bruto">Monto bruto</Label>
            <Input id="edit-bruto" type="number" min={0} value={ed.bruto}
              onChange={(e) => ed.setBruto(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="edit-neto">Monto neto</Label>
            <Input id="edit-neto" type="number" min={0} value={ed.neto}
              onChange={(e) => ed.setNeto(e.target.value)} />
          </div>
          {ed.error && <p className="text-sm text-destructive" role="alert">{ed.error}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => ed.setItem(null)} disabled={ed.saving}>
            Cancelar
          </Button>
          <Button onClick={ed.save} disabled={ed.saving}>
            {ed.saving ? "Guardando…" : "Guardar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

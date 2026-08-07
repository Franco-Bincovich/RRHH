"use client"

import { EnvioDestinatarios } from "@/components/features/configuracion/EnvioDestinatarios"
import { EnvioPie } from "@/components/features/configuracion/EnvioPie"
import { EnvioResultado } from "@/components/features/configuracion/EnvioResultado"
import { useEnvioPlantilla } from "@/components/features/configuracion/useEnvioPlantilla"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import type { Plantilla } from "@/types/plantillas"

interface Props {
  open: boolean
  plantilla: Plantilla | null
  onClose: () => void
}

/**
 * Elegir destinatarios y mandar la plantilla. Tres pasos en la misma ventana: elegir, confirmar,
 * y el resumen de lo que pasó.
 *
 * 🔴 EL RESUMEN NO SE CIERRA SOLO. Un envío puede terminar parcial o con fallos y ese detalle no
 * entra en un toast: el modal se queda con los números hasta que el usuario cierre. Es también
 * lo que le permite volver a mandar el mismo grupo si quedó cortado, sabiendo cuántos faltan.
 *
 * El armado es fino a propósito —la lista, el pie y el resumen son componentes aparte— porque
 * `Dialog` de base-ui monta por PORTAL y vitest corre sin jsdom: lo que quede escrito acá adentro
 * no se puede testear. Acá queda solo el cableado.
 */
export function EnviarPlantillaModal({ open, plantilla, onClose }: Props) {
  const {
    visibles, cargando, errorCarga, recargar, sinEmpresa, search, setSearch, sel, toggle,
    elegidos, paso, setPaso, enviando, resultado, error, confirmar,
  } = useEnvioPlantilla(open, plantilla?.clave ?? "")

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Enviar «{plantilla?.clave ?? ""}»</DialogTitle>
        </DialogHeader>

        {paso === "resultado" && resultado ? (
          <EnvioResultado res={resultado} />
        ) : (
          <EnvioDestinatarios
            visibles={visibles} sel={sel} search={search} cargando={cargando && !sinEmpresa}
            error={errorCarga} onSearch={setSearch} onToggle={toggle} onReintentar={recargar}
          />
        )}

        {error && <p className="text-sm text-destructive">{error}</p>}

        {/* ⚠️ El `<DialogFooter>` tiene que quedar como hijo LITERAL de `DialogContent`: el
            diálogo reparte los hijos por tipo para fijar los extremos (ver `partirHijos`). */}
        <DialogFooter className={sinEmpresa || paso === "confirmar" ? "sm:justify-between" : undefined}>
          {paso === "resultado" ? (
            <Button onClick={onClose}>Cerrar</Button>
          ) : (
            <EnvioPie
              cantidad={elegidos.length} confirmando={paso === "confirmar"} enviando={enviando}
              sinEmpresa={sinEmpresa} onPedirConfirmacion={() => setPaso("confirmar")}
              onVolver={() => setPaso("seleccion")} onEnviar={confirmar} onCancelar={onClose}
            />
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

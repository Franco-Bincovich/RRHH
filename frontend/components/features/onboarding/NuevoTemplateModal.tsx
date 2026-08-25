"use client"

import { useState } from "react"

import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { avisarGuardado } from "@/components/features/shared/avisoGuardado"
import { createTemplate } from "@/services/onboarding"
import type { Empresa } from "@/types/empresa"
import type { OnboardingTemplate } from "@/types/onboarding"

interface NuevoTemplateModalProps {
  empresas: Empresa[]
  empresaActivaId: string | null
  onClose: () => void
  onSuccess: (t: OnboardingTemplate) => void
}

/**
 * Alta de un template de onboarding. Autocontenido: hace su propio POST y devuelve el template
 * creado por `onSuccess`.
 *
 * ═══════════════════════════════════════════════════════════════════════════════════
 * 🔴 ERA EL ÚNICO MODAL DEL PRODUCTO ESCRITO A MANO. MIGRADO AL PRIMITIVO EL 25/8/2026.
 * ═══════════════════════════════════════════════════════════════════════════════════
 * Antes esto eran dos `<div className="fixed">` sueltos con `role="dialog"` puesto a mano. El
 * síntoma reportado fue **que no cerraba con Escape, el único de 114**, pero Escape era apenas
 * lo visible: un modal a mano tampoco tiene **trampa de foco** (con Tab se sale del diálogo y se
 * navega la página de atrás, que está `aria-hidden` para el lector de pantalla), ni **bloqueo del
 * scroll** del body, ni **devuelve el foco** al control que lo abrió al cerrarse. Las cuatro cosas
 * las trae `Dialog` (Base UI) y ninguna se ve mirando la pantalla — por eso el bug se reportó como
 * "no cierra con Escape" y no como "este modal es inaccesible".
 *
 * 🔑 Y ADEMÁS SE LLEVÓ EL RESTO DEL PATRÓN GRATIS: `patron="formulario"` pone el ancho de 560px,
 * el `max-h` en `dvh` (no `vh`, que en mobile cuenta la barra de direcciones) y el scroll en el
 * CUERPO y no en el popup — o sea que el título y los botones no se van con el scroll. Los campos
 * pasaron a `Input`/`Textarea`/`Select`, que traen los 34px y el piso táctil de 44px abajo de `md`.
 *
 * El selector de empresa solo aparece cuando el topbar está en "Todas": crear es una ACCIÓN, así
 * que la empresa viaja como parámetro explícito del form (no por el header `X-Empresa-Id`). Con
 * una empresa activa se usa esa; ver el principio Vista vs Acción en CLAUDE.md.
 */
export function NuevoTemplateModal({
  empresas, empresaActivaId, onClose, onSuccess,
}: NuevoTemplateModalProps) {
  const [nombre, setNombre] = useState("")
  const [descripcion, setDescripcion] = useState("")
  const [empresaId, setEmpresaId] = useState<string>(empresaActivaId ?? empresas[0]?.id ?? "")
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleGuardar() {
    if (!nombre.trim() || !empresaId || guardando) return
    setGuardando(true)
    setError(null)
    try {
      const t = await createTemplate({
        nombre: nombre.trim(),
        empresa_id: empresaId,
        descripcion: descripcion.trim() || undefined,
      })
      avisarGuardado("Plantilla de onboarding", "f", false)
      onSuccess(t)
    } catch {
      setError("No se pudo crear la plantilla. Intentá de nuevo.")
      setGuardando(false)
    }
  }

  return (
    <Dialog open onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      <DialogContent patron="formulario">
        <DialogHeader>
          <DialogTitle>Nueva plantilla de onboarding</DialogTitle>
          {/* Una línea que explica la CONSECUENCIA, no lo que el modal es (§3): lo que no se
              deduce mirando los campos es que la plantilla nace VACÍA y pública. */}
          <DialogDescription>
            Nace vacía: las tareas se agregan después, desde su ficha. Queda visible para el resto
            del equipo hasta que su autor la vuelva privada.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {!empresaActivaId && empresas.length > 0 && (
            <div>
              <Label htmlFor="tmpl-empresa" className="mb-1.5 block text-sm">Empresa</Label>
              <Select
                id="tmpl-empresa"
                value={empresaId}
                onChange={(e) => setEmpresaId(e.target.value)}
              >
                {empresas.map((e) => (
                  <option key={e.id} value={e.id}>{e.nombre}</option>
                ))}
              </Select>
            </div>
          )}

          <div>
            <Label htmlFor="tmpl-nombre" className="mb-1.5 block text-sm">Nombre</Label>
            <Input
              id="tmpl-nombre"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="ej. Onboarding Técnico"
            />
          </div>

          <div>
            <Label htmlFor="tmpl-desc" className="mb-1.5 block text-sm">
              Descripción <span className="font-normal text-muted-foreground">(opcional)</span>
            </Label>
            <Textarea
              id="tmpl-desc"
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
              rows={3}
              placeholder="Para qué sirve esta plantilla…"
            />
          </div>

          {error && <p className="text-sm text-destructive" role="alert">{error}</p>}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose} disabled={guardando}>
            Cancelar
          </Button>
          <Button
            type="button"
            onClick={handleGuardar}
            disabled={!nombre.trim() || !empresaId || guardando}
          >
            {guardando ? "Creando…" : "Crear plantilla"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

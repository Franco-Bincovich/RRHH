"use client"

import { useState } from "react"
import { X } from "lucide-react"

import { createTemplate } from "@/services/onboarding"
import type { OnboardingTemplate } from "@/types/onboarding"
import type { Empresa } from "@/types/empresa"
import { Select } from "@/components/ui/select"

interface NuevoTemplateModalProps {
  empresas: Empresa[]
  empresaActivaId: string | null
  onClose: () => void
  onSuccess: (t: OnboardingTemplate) => void
}

/**
 * Alta de un template de onboarding. Autocontenido: hace su propio POST y devuelve el
 * template creado por `onSuccess`.
 *
 * El selector de empresa solo aparece cuando el topbar está en "Todas": crear es una ACCIÓN,
 * así que la empresa viaja como parámetro explícito del form (no por el header X-Empresa-Id).
 * Con una empresa activa se usa esa; ver el principio Vista vs Acción en CLAUDE.md.
 */
export function NuevoTemplateModal({ empresas, empresaActivaId, onClose, onSuccess }: NuevoTemplateModalProps) {
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
      onSuccess(t)
    } catch {
      setError("No se pudo crear el template. Intentá de nuevo.")
      setGuardando(false)
    }
  }

  return (
    <>
      <div className="fixed inset-0 z-50 bg-black/40" aria-hidden="true" onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-nuevo-tmpl"
        className="fixed inset-x-4 top-1/2 z-50 -translate-y-1/2 rounded-2xl bg-background p-6 shadow-2xl ring-1 ring-border sm:inset-auto sm:left-1/2 sm:w-[28rem] sm:-translate-x-1/2"
      >
        <div className="mb-5 flex items-center justify-between gap-2">
          <h2 id="modal-nuevo-tmpl" className="text-base font-semibold text-foreground">
            Nuevo template
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="flex min-h-9 min-w-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <X className="size-4" />
          </button>
        </div>

        <div className="space-y-4">
          {/* Selector de empresa — solo visible cuando topbar = "Todas" */}
          {!empresaActivaId && empresas.length > 0 && (
            <div>
              <label htmlFor="tmpl-empresa" className="mb-1.5 block text-sm font-medium text-foreground">
                Empresa
              </label>
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
            <label htmlFor="tmpl-nombre" className="mb-1.5 block text-sm font-medium text-foreground">
              Nombre
            </label>
            <input
              id="tmpl-nombre"
              type="text"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="ej. Onboarding Técnico"
              className="w-full rounded-lg border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <div>
            <label htmlFor="tmpl-desc" className="mb-1.5 block text-sm font-medium text-foreground">
              Descripción <span className="text-muted-foreground font-normal">(opcional)</span>
            </label>
            <textarea
              id="tmpl-desc"
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
              rows={3}
              placeholder="Descripción del template..."
              className="w-full rounded-lg border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-none"
            />
          </div>
        </div>

        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleGuardar}
            disabled={!nombre.trim() || !empresaId || guardando}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
          >
            {guardando ? "Creando…" : "Crear template"}
          </button>
        </div>
      </div>
    </>
  )
}

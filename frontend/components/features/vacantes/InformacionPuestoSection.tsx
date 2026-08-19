"use client"

import { useState } from "react"
import { toast } from "sonner"
import { ClipboardList } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { updateVacante } from "@/services/vacantes"
import type { Vacante } from "@/types/vacantes"

interface InformacionPuestoSectionProps {
  vacante: Vacante
  canWrite: boolean
  onSaved: (v: Vacante) => void
}

const CAMPOS = [
  { key: "funciones", label: "Funciones", placeholder: "Tareas y responsabilidades del puesto…" },
  { key: "requisitos", label: "Requisitos", placeholder: "Requisitos excluyentes y deseables…" },
  { key: "formacion", label: "Formación", placeholder: "Estudios / títulos requeridos…" },
  { key: "experiencia", label: "Experiencia", placeholder: "Años y tipo de experiencia…" },
  { key: "conocimientos_tecnicos", label: "Conocimientos técnicos", placeholder: "Herramientas, tecnologías, idiomas…" },
] as const

type CampoKey = (typeof CAMPOS)[number]["key"]

/** Información del puesto (texto libre, insumo para el matching de CVs con IA). Edición inline. */
export function InformacionPuestoSection({ vacante, canWrite, onSaved }: InformacionPuestoSectionProps) {
  const [valores, setValores] = useState<Record<CampoKey, string>>({
    funciones: vacante.funciones ?? "",
    requisitos: vacante.requisitos ?? "",
    formacion: vacante.formacion ?? "",
    experiencia: vacante.experiencia ?? "",
    conocimientos_tecnicos: vacante.conocimientos_tecnicos ?? "",
  })
  const [saving, setSaving] = useState(false)

  const set = (key: CampoKey, value: string) => setValores((prev) => ({ ...prev, [key]: value }))

  const handleGuardar = async () => {
    setSaving(true)
    try {
      const updated = await updateVacante(vacante.id, {
        funciones: valores.funciones.trim() || null,
        requisitos: valores.requisitos.trim() || null,
        formacion: valores.formacion.trim() || null,
        experiencia: valores.experiencia.trim() || null,
        conocimientos_tecnicos: valores.conocimientos_tecnicos.trim() || null,
      })
      onSaved(updated)
      toast.success("Información del puesto guardada")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "No se pudo guardar la información del puesto.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card as="section" className="mb-8">
      <div className="mb-4 flex items-center gap-2">
        <ClipboardList className="size-4 text-muted-foreground" />
        <h2 className="text-base font-semibold text-foreground">Información del puesto</h2>
      </div>

      <div className="space-y-4">
        {CAMPOS.map(({ key, label, placeholder }) => (
          <div key={key} className="flex flex-col gap-1.5">
            <Label htmlFor={key}>{label}</Label>
            <Textarea
              id={key}
              rows={3}
              placeholder={placeholder}
              value={valores[key]}
              disabled={!canWrite}
              onChange={(e) => set(key, e.target.value)}
            />
          </div>
        ))}

        {canWrite && (
          <div className="flex justify-end">
            <Button className="min-h-10" onClick={handleGuardar} disabled={saving}>
              {saving ? "Guardando…" : "Guardar"}
            </Button>
          </div>
        )}
      </div>
    </Card>
  )
}

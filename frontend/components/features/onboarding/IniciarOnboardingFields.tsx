"use client"

import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { EmpleadoCombobox } from "@/components/features/shared/EmpleadoCombobox"
import type { Empleado } from "@/types/empleado"
import type { OnboardingTemplate } from "@/types/onboarding"

/**
 * Los dos campos del alta de onboarting: la persona y el template. Presentacional y controlado —
 * no fetchea, no valida y no tiene estado propio.
 *
 * 🔴 Salió de `IniciarOnboardingModal.tsx` porque ese archivo llegaba a 160 líneas contra un
 * límite de 150. El corte deja al modal con lo que decide —qué se puede elegir, qué se manda y
 * qué pasa si falla— y acá lo que se dibuja.
 */
export function IniciarOnboardingFields({
  selectedId, onSelectEmpleado, yaTienen,
  templates, selectedTemplateId, onSelectTemplate, error,
}: {
  selectedId: string
  onSelectEmpleado: (e: Empleado | null) => void
  /** Quienes ya tienen un onboarding en curso: el backend los rechaza con 409. */
  yaTienen: string[]
  /** Ya filtrados por la empresa del empleado elegido. */
  templates: OnboardingTemplate[]
  selectedTemplateId: string
  onSelectTemplate: (id: string) => void
  error: string | null
}) {
  return (
    <div className="space-y-4 py-2">
      <div className="space-y-1.5">
        <Label htmlFor="emp-select">Colaborador</Label>
        {/*
          El cartel "Todos los colaboradores activos ya tienen un onboarding en curso" se fue con
          la lista precargada: con búsqueda contra el backend nadie tiene el padrón entero en
          memoria, así que esa afirmación no se puede sostener. El combobox dice lo que sí
          sabe — "sin resultados para lo que buscaste" —, que además era el mensaje correcto
          en el caso frecuente (alguien que no aparecía por estar fuera de los primeros 100).
        */}
        <EmpleadoCombobox
          id="emp-select"
          value={selectedId}
          excluirIds={yaTienen}
          onChange={onSelectEmpleado}
        />
      </div>

      {selectedId && (
        <div className="space-y-1.5">
          <Label htmlFor="tmpl-select">Template</Label>
          {templates.length > 0 ? (
            <Select
              id="tmpl-select"
              value={selectedTemplateId}
              onChange={(e) => onSelectTemplate(e.target.value)}
            >
              {templates.map((t) => (
                <option key={t.id} value={t.id}>{t.nombre}</option>
              ))}
            </Select>
          ) : (
            <p className="text-xs text-muted-foreground">
              No hay templates configurados para la empresa de este colaborador.
            </p>
          )}
        </div>
      )}

      {error && <p className="text-sm text-destructive" role="alert">{error}</p>}
    </div>
  )
}

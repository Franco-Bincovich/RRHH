"use client"

import { EmpleadoCombobox } from "@/components/features/shared/EmpleadoCombobox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select } from "@/components/ui/select"
import { type FormData, type FormErrors } from "@/components/features/areas/areaForm"
import type { Empresa } from "@/types/empresa"

interface Props {
  form: FormData
  errors: FormErrors
  empresas: Empresa[]
  /** Nombre del responsable ya guardado, para que la EDICIÓN no muestre un campo en blanco. */
  responsableNombre?: string
  onResponsable: (id: string) => void
  /** En la edición el select de empresa no se muestra: un área no se muda de sociedad. */
  isEdit: boolean
  onField: (key: keyof FormData) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => void
}

/**
 * Los campos del formulario de área. PRESENTACIONAL: sin estado, sin fetch, sin efectos.
 *
 * Existe como componente aparte para que `AreaModal` no vuelva a pasarse de 150 líneas. Molde:
 * `ObjetivoFormFields.tsx`, que hace exactamente esto para el modal de objetivos.
 */
export function AreaFormFields({
  form, errors, empresas, responsableNombre, onResponsable, isEdit, onField,
}: Props) {
  return (
    <div className="flex flex-col gap-4 py-2">
      {!isEdit && (
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="area_empresa">
            Empresa
            <span className="ml-0.5 text-destructive" aria-hidden>*</span>
          </Label>
          <Select
            id="area_empresa"
            value={form.empresa_id}
            onChange={onField("empresa_id")}
            aria-required
            aria-invalid={Boolean(errors.empresa_id)}
          >
            <option value="">Seleccionar empresa</option>
            {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
          </Select>
          {errors.empresa_id && (
            <p className="text-xs text-destructive" role="alert">{errors.empresa_id}</p>
          )}
        </div>
      )}
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="nombre">
          Nombre
          <span className="ml-0.5 text-destructive" aria-hidden>*</span>
        </Label>
        <Input
          id="nombre"
          value={form.nombre}
          onChange={onField("nombre")}
          aria-invalid={Boolean(errors.nombre)}
          aria-required
          maxLength={100}
        />
        {errors.nombre && (
          <p className="text-xs text-destructive" role="alert">{errors.nombre}</p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="descripcion">Descripción</Label>
        <Textarea
          id="descripcion"
          value={form.descripcion}
          onChange={onField("descripcion")}
          rows={3}
          className="resize-none"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="responsable_id">
          Responsable <span className="text-muted-foreground">(opcional)</span>
        </Label>
        {/*
          Es OPCIONAL: "Cambiar" en el combobox deja el campo vacío otra vez, que acá significa
          "sin responsable asignado" — el `<option value="">` que reemplaza.
        */}
        <EmpleadoCombobox
          id="responsable_id"
          value={form.responsable_id}
          empresaId={form.empresa_id || undefined}
          etiquetaInicial={responsableNombre}
          onChange={(emp) => onResponsable(emp?.id ?? "")}
        />
      </div>
    </div>
  )
}

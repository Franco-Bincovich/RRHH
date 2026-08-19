"use client"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select } from "@/components/ui/select"
import { TIPOS_VACACION, type VacacionFormData, type VacacionFormErrors } from "./vacacionesForm"

type FieldHandler = (
  e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
) => void

interface CamposVacacionProps {
  form: VacacionFormData
  errors: VacacionFormErrors
  field: (key: keyof VacacionFormData) => FieldHandler
  toggle: (key: "pendiente" | "liquidada") => (e: React.ChangeEvent<HTMLInputElement>) => void
}

const CHECK_CLASS = "size-4 rounded border-input accent-primary"

/**
 * Campos del alta de vacaciones. Presentacional.
 *
 * El tilde "No se tomó" es el que decide a qué TABLA va el registro: tildado esconde las
 * fechas y pide cantidad de días (van a vacaciones_pendientes), destildado pide el rango
 * (va a solicitudes_vacaciones). No es un detalle de UI: un día no tomado no tiene fecha
 * porque nadie faltó ningún día. Ver backend/migrations/083.
 */
export function CamposVacacion({ form, errors, field, toggle }: CamposVacacionProps) {
  return (
    <>
      <label className="flex items-center gap-2 text-sm text-foreground">
        <input type="checkbox" className={CHECK_CLASS} checked={form.pendiente} onChange={toggle("pendiente")} />
        No se tomó (días pendientes)
      </label>

      {!form.pendiente && (
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="tipo">Tipo</Label>
          <Select id="tipo" value={form.tipo} onChange={field("tipo")}>
            {TIPOS_VACACION.map(({ value, label }) => <option key={value} value={value}>{label}</option>)}
          </Select>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="periodo">Período <span className="text-destructive" aria-hidden>*</span></Label>
          <Input id="periodo" type="number" inputMode="numeric" min={2000} max={2100} value={form.periodo}
                 onChange={field("periodo")} aria-required aria-invalid={Boolean(errors.periodo)} />
          <p className="text-xs text-muted-foreground">Año al que corresponde, puede no ser el año en que se tomó.</p>
          {errors.periodo && <p className="text-xs text-destructive" role="alert">{errors.periodo}</p>}
        </div>
        {form.pendiente && (
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="dias_pendientes">Días pendientes <span className="text-destructive" aria-hidden>*</span></Label>
            <Input id="dias_pendientes" type="number" inputMode="numeric" min={1} value={form.dias_pendientes}
                   onChange={field("dias_pendientes")} aria-required aria-invalid={Boolean(errors.dias_pendientes)} />
            {errors.dias_pendientes && <p className="text-xs text-destructive" role="alert">{errors.dias_pendientes}</p>}
          </div>
        )}
      </div>

      {!form.pendiente && (
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="fecha_desde">Desde <span className="text-destructive" aria-hidden>*</span></Label>
            <Input id="fecha_desde" type="date" value={form.fecha_desde} onChange={field("fecha_desde")} aria-required aria-invalid={Boolean(errors.fecha_desde)} />
            {errors.fecha_desde && <p className="text-xs text-destructive" role="alert">{errors.fecha_desde}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="fecha_hasta">Hasta <span className="text-destructive" aria-hidden>*</span></Label>
            <Input id="fecha_hasta" type="date" value={form.fecha_hasta} min={form.fecha_desde} onChange={field("fecha_hasta")} aria-required aria-invalid={Boolean(errors.fecha_hasta)} />
            {errors.fecha_hasta && <p className="text-xs text-destructive" role="alert">{errors.fecha_hasta}</p>}
          </div>
        </div>
      )}

      <label className="flex items-center gap-2 text-sm text-foreground">
        <input type="checkbox" className={CHECK_CLASS} checked={form.liquidada} onChange={toggle("liquidada")} />
        Liquidada (ya se pagó)
      </label>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="comentario">Comentario</Label>
        <Textarea id="comentario" value={form.comentario} onChange={field("comentario")} rows={2} className="resize-none" />
      </div>
    </>
  )
}

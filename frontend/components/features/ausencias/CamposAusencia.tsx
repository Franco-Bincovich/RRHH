"use client"

import { FieldError } from "@/components/ui/FieldError"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select } from "@/components/ui/select"
import type { TipoAusencia } from "@/types/ausencias"
import { NUEVO_TIPO, type AusenciaFormData, type AusenciaFormErrors } from "./ausenciasForm"

type FieldHandler = (
  e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
) => void

interface CamposAusenciaProps {
  form: AusenciaFormData
  errors: AusenciaFormErrors
  field: (key: keyof AusenciaFormData) => FieldHandler
  onJustificada: (checked: boolean) => void
  tipos: TipoAusencia[]
  nuevoTipo: string
  onNuevoTipo: (v: string) => void
  creandoTipo: boolean
  onCrearTipo: () => void
}

/** Campos propios de la ausencia: tipo (+ crear tipo inline) + fechas + justificada + motivo. */
export function CamposAusencia({
  form, errors, field, onJustificada, tipos, nuevoTipo, onNuevoTipo, creandoTipo, onCrearTipo,
}: CamposAusenciaProps) {
  return (
    <>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="tipo_id">Tipo de ausencia <span className="text-destructive" aria-hidden>*</span></Label>
        {/* 🔴 SELECT ENCADENADO padre → subtipo (mig 088), con los padres en un <optgroup> y
            sus hijos adentro. Se eligió esto sobre dos <select> separados por una razón de
            producto: un tipo PADRE QUE TIENE HIJOS SE PUEDE ELEGIR DIRECTO, porque no toda
            "enfermedad familiar" tiene subtipo — y forzar la hoja obligaría a crear un "Otro"
            debajo de CADA padre, o sea multiplicar por N el anti-tipo que la 088 desactiva.
            Con dos selects, "elegir el padre y dejar el segundo vacío" se lee como un formulario
            a medio llenar; con un solo select agrupado, es una opción más.
            Consecuencia asumida: el total de un padre NO es la suma de sus hijos — incluye sus
            propias filas directas. Es el dato real; esconderlo con un subtipo falso sería peor. */}
        <Select id="tipo_id" value={form.tipo_id} onChange={field("tipo_id")} aria-required aria-invalid={Boolean(errors.tipo_id)}>
          <option value="">Seleccionar tipo</option>
          {tipos.filter((t) => !t.padre_id).map((padre) => {
            const hijos = tipos.filter((t) => t.padre_id === padre.id)
            return hijos.length === 0 ? (
              <option key={padre.id} value={padre.id}>{padre.nombre}</option>
            ) : (
              <optgroup key={padre.id} label={padre.nombre}>
                <option value={padre.id}>{padre.nombre} (sin detallar)</option>
                {hijos.map((h) => <option key={h.id} value={h.id}>{h.nombre}</option>)}
              </optgroup>
            )
          })}
          {/* Un hijo cuyo padre no está en la lista (padre desactivado) se muestra igual: si no,
              una ausencia ya cargada con ese tipo no se podría editar. */}
          {tipos.filter((t) => t.padre_id && !tipos.some((p) => p.id === t.padre_id))
                .map((t) => <option key={t.id} value={t.id}>{t.nombre}</option>)}
          <option value={NUEVO_TIPO}>+ Crear tipo nuevo...</option>
        </Select>
        {errors.tipo_id && <FieldError>{errors.tipo_id}</FieldError>}
      </div>

      {form.tipo_id === NUEVO_TIPO && (
        <div className="flex flex-col gap-1.5 rounded-lg border border-border bg-muted/30 p-3">
          <Label htmlFor="nuevo_tipo" className="text-xs text-muted-foreground">Nombre del nuevo tipo</Label>
          <div className="flex gap-2">
            <Input id="nuevo_tipo" value={nuevoTipo} onChange={(e) => onNuevoTipo(e.target.value)} placeholder="ej. Licencia por maternidad" className="h-8 text-sm" />
            <Button type="button" size="sm" className="h-8 shrink-0" disabled={!nuevoTipo.trim() || creandoTipo} onClick={onCrearTipo}>
              {creandoTipo ? "..." : "Crear"}
            </Button>
          </div>
          {errors.nuevo_tipo && <FieldError>{errors.nuevo_tipo}</FieldError>}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="fecha_desde">Desde <span className="text-destructive" aria-hidden>*</span></Label>
          <Input id="fecha_desde" type="date" value={form.fecha_desde} onChange={field("fecha_desde")} aria-required aria-invalid={Boolean(errors.fecha_desde)} />
          {errors.fecha_desde && <FieldError>{errors.fecha_desde}</FieldError>}
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="fecha_hasta">Hasta <span className="text-destructive" aria-hidden>*</span></Label>
          <Input id="fecha_hasta" type="date" value={form.fecha_hasta} min={form.fecha_desde} onChange={field("fecha_hasta")} aria-required aria-invalid={Boolean(errors.fecha_hasta)} />
          {errors.fecha_hasta && <FieldError>{errors.fecha_hasta}</FieldError>}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <input type="checkbox" id="justificada" checked={form.justificada} onChange={(e) => onJustificada(e.target.checked)} className="h-4 w-4 cursor-pointer rounded border border-input accent-primary" />
        <Label htmlFor="justificada" className="cursor-pointer font-normal">Ausencia justificada</Label>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="motivo">Motivo <span className="text-muted-foreground text-xs font-normal">(opcional)</span></Label>
        <Textarea id="motivo" value={form.motivo} onChange={field("motivo")} rows={2} className="resize-none" placeholder="Descripción breve" />
      </div>
    </>
  )
}

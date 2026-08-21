"use client"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { MAX_HORAS_DIA, type FormHoras, type FormLicencia } from "./logica"
import type { ClientePublico } from "@/types/horasPublico"

/**
 * Los campos de los DOS modos de carga, cada uno en su componente.
 *
 * Salieron de `CargaForm`, que quedaba en 158 líneas contra el límite de 150 al sumarle el banner
 * de validación. El corte es por MODO y no por cantidad de líneas: son dos formularios distintos
 * que nunca se ven juntos y que mandan a dos endpoints con bodies disjuntos.
 *
 * 🔴 EN MODO LICENCIA LOS CAMPOS DE HORAS NO SE DESHABILITAN: NO SE RENDERIZAN. El porqué está en
 * `CargaForm`, que es quien elige cuál de los dos montar.
 */
type Err = (k: string) => React.ReactNode

export function CamposHoras({ form, onForm, clientes, err, min, max }: {
  form: FormHoras
  onForm: (f: FormHoras) => void
  clientes: ClientePublico[]
  err: Err
  min: string
  max: string
}) {
  return (
    <>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="fecha">Fecha</Label>
          {/* `min`/`max` acotan el calendario a la ventana que el backend acepta. Se calculan en
              hora LOCAL: con UTC, quien carga de noche veía mañana ofrecida. Ver `ventanaFechas`. */}
          <Input id="fecha" type="date" value={form.fecha} min={min} max={max}
                 onChange={(e) => onForm({ ...form, fecha: e.target.value })} />
          {err("fecha")}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="horas">Horas</Label>
          <Input id="horas" type="number" step="0.5" min="0.5" max={MAX_HORAS_DIA}
                 value={form.horas}
                 onChange={(e) => onForm({ ...form, horas: e.target.value })} />
          {err("horas")}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="modalidad">Modalidad</Label>
          <Select id="modalidad" value={form.modalidad}
                  onChange={(e) => onForm({ ...form, modalidad: e.target.value })}>
            <option value="">Elegí una</option>
            <option value="home_office">Home Office</option>
            <option value="on_site">On site</option>
          </Select>
          {err("modalidad")}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="cliente">Cliente</Label>
          <Select id="cliente" value={form.cliente_id}
                  onChange={(e) => onForm({ ...form, cliente_id: e.target.value })}>
            <option value="">Elegí uno</option>
            {clientes.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
          </Select>
          {err("cliente_id")}
        </div>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="proyecto">Proyecto (opcional)</Label>
          <Input id="proyecto" value={form.proyecto_texto} maxLength={200}
                 onChange={(e) => onForm({ ...form, proyecto_texto: e.target.value })} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="tarea">Tarea (opcional)</Label>
          <Input id="tarea" value={form.tarea_texto} maxLength={200}
                 onChange={(e) => onForm({ ...form, tarea_texto: e.target.value })} />
        </div>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="descripcion">Descripción (opcional)</Label>
        <Textarea id="descripcion" rows={2} maxLength={1000} value={form.descripcion}
                  onChange={(e) => onForm({ ...form, descripcion: e.target.value })} />
      </div>
    </>
  )
}

export function CamposLicencia({ form, onForm, err, min, max }: {
  form: FormLicencia
  onForm: (f: FormLicencia) => void
  err: Err
  min: string
  max: string
}) {
  return (
    <>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="desde">Desde</Label>
          <Input id="desde" type="date" value={form.fecha_desde} min={min} max={max}
                 onChange={(e) => onForm({ ...form, fecha_desde: e.target.value })} />
          {err("fecha_desde")}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="hasta">Hasta</Label>
          <Input id="hasta" type="date" value={form.fecha_hasta} min={min} max={max}
                 onChange={(e) => onForm({ ...form, fecha_hasta: e.target.value })} />
          {err("fecha_hasta")}
        </div>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="observaciones">Observaciones (opcional)</Label>
        <Textarea id="observaciones" rows={2} maxLength={1000} value={form.observaciones}
                  onChange={(e) => onForm({ ...form, observaciones: e.target.value })} />
      </div>
    </>
  )
}

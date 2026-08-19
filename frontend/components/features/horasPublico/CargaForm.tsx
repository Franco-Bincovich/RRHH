"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select } from "@/components/ui/select"
import {
  MAX_HORAS_DIA, puedeEnviar, ventanaFechas,
  type FormHoras, type FormLicencia, type Modo,
} from "@/components/features/horasPublico/logica"
import type { ClientePublico } from "@/types/horasPublico"

interface Props {
  modo: Modo
  onModo: (m: Modo) => void
  horas: FormHoras
  onHoras: (f: FormHoras) => void
  licencia: FormLicencia
  onLicencia: (f: FormLicencia) => void
  clientes: ClientePublico[]
  errores: Record<string, string>
  enviando: boolean
  hoy: Date
}

/**
 * El formulario. Horas o licencia, nunca los dos.
 *
 * 🔴 AL ELEGIR LICENCIA, LOS CAMPOS DE HORAS NO SE DESHABILITAN: **NO SE RENDERIZAN**.
 * Dos motivos, y el segundo es el que decide:
 *   1. Un `disabled` sobre el Button/Input de shadcn no se puede afirmar en un test — el markup
 *      trae la clase `disabled:` SIEMPRE, con y sin la prop, así que `not.toContain("disabled")`
 *      es una aserción que no puede fallar nunca.
 *   2. Los dos endpoints del backend reciben bodies DISJUNTOS: el de licencia ni siquiera acepta
 *      `horas` ni `cliente_id`. Un campo gris en pantalla sugeriría que existe pero está
 *      bloqueado; la verdad es que en ese modo no existe.
 *
 * El botón de enviar SÍ usa `disabled` mientras faltan obligatorios — ahí es correcto: el campo
 * existe, la acción todavía no. Lo que un test puede afirmar de eso es `puedeEnviar()`, que es
 * la función pura que lo decide.
 */
export function CargaForm(p: Props) {
  const { min, max } = ventanaFechas(p.hoy)
  const err = (k: string) =>
    p.errores[k] ? <p className="text-xs text-destructive">{p.errores[k]}</p> : null

  return (
    <div className="space-y-4">
      <div className="flex gap-2" role="radiogroup" aria-label="Qué querés cargar">
        {(["horas", "licencia"] as Modo[]).map((m) => (
          <Button key={m} type="button" variant={p.modo === m ? "default" : "outline"}
                  className="min-h-11 flex-1" aria-pressed={p.modo === m}
                  onClick={() => p.onModo(m)}>
            {m === "horas" ? "Horas trabajadas" : "Licencia"}
          </Button>
        ))}
      </div>

      {p.modo === "horas" ? (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="fecha">Fecha</Label>
              <Input id="fecha" type="date" value={p.horas.fecha} min={min} max={max}
                     onChange={(e) => p.onHoras({ ...p.horas, fecha: e.target.value })} />
              {err("fecha")}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="horas">Horas</Label>
              <Input id="horas" type="number" step="0.5" min="0.5" max={MAX_HORAS_DIA}
                     value={p.horas.horas}
                     onChange={(e) => p.onHoras({ ...p.horas, horas: e.target.value })} />
              {err("horas")}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="modalidad">Modalidad</Label>
              <Select id="modalidad" value={p.horas.modalidad}
                      onChange={(e) => p.onHoras({ ...p.horas, modalidad: e.target.value })}>
                <option value="">Elegí una</option>
                <option value="home_office">Home Office</option>
                <option value="on_site">On site</option>
              </Select>
              {err("modalidad")}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="cliente">Cliente</Label>
              <Select id="cliente" value={p.horas.cliente_id}
                      onChange={(e) => p.onHoras({ ...p.horas, cliente_id: e.target.value })}>
                <option value="">Elegí uno</option>
                {p.clientes.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
              </Select>
              {err("cliente_id")}
            </div>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="proyecto">Proyecto (opcional)</Label>
              <Input id="proyecto" value={p.horas.proyecto_texto} maxLength={200}
                     onChange={(e) => p.onHoras({ ...p.horas, proyecto_texto: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="tarea">Tarea (opcional)</Label>
              <Input id="tarea" value={p.horas.tarea_texto} maxLength={200}
                     onChange={(e) => p.onHoras({ ...p.horas, tarea_texto: e.target.value })} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="descripcion">Descripción (opcional)</Label>
            <Textarea id="descripcion" rows={2} maxLength={1000} value={p.horas.descripcion}
                      onChange={(e) => p.onHoras({ ...p.horas, descripcion: e.target.value })} />
          </div>
        </>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="desde">Desde</Label>
              <Input id="desde" type="date" value={p.licencia.fecha_desde} min={min} max={max}
                     onChange={(e) => p.onLicencia({ ...p.licencia, fecha_desde: e.target.value })} />
              {err("fecha_desde")}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="hasta">Hasta</Label>
              <Input id="hasta" type="date" value={p.licencia.fecha_hasta} min={min} max={max}
                     onChange={(e) => p.onLicencia({ ...p.licencia, fecha_hasta: e.target.value })} />
              {err("fecha_hasta")}
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="observaciones">Observaciones (opcional)</Label>
            <Textarea id="observaciones" rows={2} maxLength={1000}
                      value={p.licencia.observaciones}
                      onChange={(e) => p.onLicencia({ ...p.licencia, observaciones: e.target.value })} />
          </div>
        </>
      )}

      <Button type="submit" className="min-h-11 w-full"
              disabled={p.enviando || !puedeEnviar(p.modo, p.horas, p.licencia)}>
        {p.enviando ? "Enviando..." : "Enviar"}
      </Button>
    </div>
  )
}
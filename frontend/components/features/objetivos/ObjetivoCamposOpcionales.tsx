"use client"

import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Select } from "@/components/ui/select"
import type { FormData } from "@/components/features/objetivos/ObjetivoFormFields"
import type { Objetivo, UserItem } from "@/types/objetivo"

/**
 * La segunda mitad del formulario de objetivo: los campos OPCIONALES.
 *
 * Extraído de ObjetivoFormFields (125/150), que no admitía los dos campos que vienen. El
 * movimiento fue PURO: el JSX, las clases, los ids y el ORDEN de los controles son idénticos a
 * los que estaban embebidos allá.
 *
 * 🔴 POR QUÉ EL CORTE VA EN "OBLIGATORIO vs OPCIONAL" Y NO EN "DATOS vs CLASIFICACIÓN".
 * El corte por significado exigía separar `prioridad` de `responsable`, y esos dos comparten una
 * grilla de dos columnas: partirlos habría cambiado el markup renderizado, o sea que ya no
 * habría sido un movimiento puro. El único límite que cae entre dos hijos directos del
 * contenedor —sin tocar una sola clase— es el que separa los tres campos con asterisco (empresa,
 * título, responsable, más prioridad, que siempre tiene valor) de los cuatro que la propia UI ya
 * rotula "(opcional)". Es un seam que estaba en el código, no uno inventado para el corte.
 *
 * 📌 QUÉ CRECE ACÁ. Los dos campos nuevos del módulo son opcionales y van en este archivo:
 * `periodicidad` junto a la fecha de entrega (los dos son el plazo) y `areas_involucradas` como
 * texto libre. El bloque obligatorio de arriba no se toca.
 *
 * ⚠️ `SEL` VIVE ACÁ Y NO EN ObjetivoFormFields, que es quien más lo usa, por una razón concreta:
 * así la dependencia entre los dos archivos apunta en UNA sola dirección (FormFields → este). Al
 * revés quedaba un ciclo — FormFields importando el componente y este importando la constante—,
 * y duplicar el string de clases es la divergencia silenciosa que el repo evita. Lo único que
 * viaja en sentido contrario es el TIPO `FormData`, y un `import type` se borra en compilación:
 * no es una arista en runtime.
 */

interface Props {
  form: FormData
  usuarios: UserItem[]
  /** Candidatos a padre: SOLO raíces, y sin el objetivo que se está editando. */
  padres: Objetivo[]
  field: (key: keyof FormData) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => void
  onToggleResponsable: (id: string) => void
}

export function ObjetivoCamposOpcionales({ form, usuarios, padres, field, onToggleResponsable }: Props) {
  return (
    <>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="obj_fecha">Fecha de entrega <span className="text-xs text-muted-foreground font-normal">(opcional)</span></Label>
        <Input id="obj_fecha" type="date" value={form.fecha_entrega} onChange={field("fecha_entrega")} />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="obj_padre">Objetivo padre <span className="text-xs text-muted-foreground font-normal">(opcional)</span></Label>
        {/* Solo raíces: la jerarquía admite dos niveles, así que colgar de un subobjetivo daría
            un 422 del backend. El selector no ofrece lo que el backend va a rechazar. */}
        <Select id="obj_padre" value={form.parent_id} onChange={field("parent_id")}>
          <option value="">Sin padre — es un objetivo principal</option>
          {padres.map((p) => <option key={p.id} value={p.id}>{p.titulo}</option>)}
        </Select>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label>Otros responsables <span className="text-xs text-muted-foreground font-normal">(opcional)</span></Label>
        {/* Checkboxes y NO un <select multiple>: el nativo exige ctrl/cmd+click, que es justo
            lo que un usuario no descubre solo. Mismo criterio que FiltersBar del bloque B. */}
        <div className="flex max-h-28 flex-col gap-1 overflow-y-auto rounded-lg border border-input p-2">
          {usuarios.filter((u) => u.id !== form.responsable_id).map((u) => (
            <label key={u.id} className="flex items-center gap-2 text-sm text-foreground">
              <input
                type="checkbox"
                checked={form.responsables.includes(u.id)}
                onChange={() => onToggleResponsable(u.id)}
              />
              {u.nombre} {u.apellido}
            </label>
          ))}
          {usuarios.length <= 1 && <p className="text-xs text-muted-foreground">No hay otros usuarios.</p>}
        </div>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="obj_desc">Descripción <span className="text-xs text-muted-foreground font-normal">(opcional)</span></Label>
        <Textarea id="obj_desc" value={form.descripcion} onChange={field("descripcion")} rows={2} className="resize-none" />
      </div>
    </>
  )
}

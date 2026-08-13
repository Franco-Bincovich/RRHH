"use client"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ObjetivoCamposOpcionales, SEL } from "@/components/features/objetivos/ObjetivoCamposOpcionales"
import type { Objetivo, PrioridadObjetivo, UserItem } from "@/types/objetivo"
import type { Empresa } from "@/types/empresa"

/**
 * Los campos del formulario de objetivo. Presentacional: sin estado, sin fetch, sin submit —
 * todo eso vive en ObjetivoModal.tsx, que es quien lo usa.
 *
 * Extraído porque ObjetivoModal estaba en 156/150, YA por encima del límite antes de tocarlo.
 * El corte va por acá y no por el estado porque este es el lado que crece: el rediseño del
 * modelo suma un selector de objetivo padre y un multi-select de responsables, y los dos son
 * controles de formulario.
 *
 * El movimiento fue PURO: el JSX, las clases y los ids son idénticos a los que estaban
 * embebidos en el modal.
 *
 * ── Segundo corte (125/150 → acá) ────────────────────────────────────────────
 * Los cuatro campos OPCIONALES —fecha de entrega, objetivo padre, otros responsables y
 * descripción— se fueron a ObjetivoCamposOpcionales.tsx, que es donde entran los dos campos
 * nuevos del módulo. Acá quedan los que la UI marca con asterisco, más `prioridad`, que comparte
 * grilla con `responsable` y no se puede separar sin cambiar el markup. El porqué del límite
 * elegido está escrito en el encabezado de ese archivo.
 *
 * Este archivo sigue siendo el dueño de `FormData` y `FormErrors` —los importa ObjetivoModal— y
 * la única punta que el modal conoce: el corte de abajo no cambió una sola línea del modal.
 */

export type FormData = {
  empresa_id: string
  responsable_id: string
  titulo: string
  descripcion: string
  prioridad: PrioridadObjetivo
  fecha_entrega: string
  parent_id: string
  /** Responsables ADICIONALES al dueño. El dueño nunca está acá: lo agrega el backend. */
  responsables: string[]
}

export type FormErrors = Partial<Record<keyof FormData, string>>

interface Props {
  form: FormData
  errors: FormErrors
  empresas: Empresa[]
  usuarios: UserItem[]
  /** Candidatos a padre: SOLO raíces, y sin el objetivo que se está editando. */
  padres: Objetivo[]
  isEdit: boolean
  field: (key: keyof FormData) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => void
  onToggleResponsable: (id: string) => void
}

export function ObjetivoFormFields({
  form, errors, empresas, usuarios, padres, isEdit, field, onToggleResponsable,
}: Props) {
  return (
    <div className="flex flex-col gap-4 py-2">
      {!isEdit && (
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="obj_empresa">Empresa <span className="text-destructive" aria-hidden>*</span></Label>
          <select id="obj_empresa" className={SEL} value={form.empresa_id} onChange={field("empresa_id")} aria-required aria-invalid={Boolean(errors.empresa_id)}>
            <option value="">Seleccionar empresa</option>
            {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
          </select>
          {errors.empresa_id && <p className="text-xs text-destructive" role="alert">{errors.empresa_id}</p>}
        </div>
      )}
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="obj_titulo">Título <span className="text-destructive" aria-hidden>*</span></Label>
        <Input id="obj_titulo" value={form.titulo} onChange={field("titulo")} aria-required aria-invalid={Boolean(errors.titulo)} placeholder="ej. Actualizar políticas de licencias" />
        {errors.titulo && <p className="text-xs text-destructive" role="alert">{errors.titulo}</p>}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="obj_responsable">Responsable <span className="text-destructive" aria-hidden>*</span></Label>
          <select id="obj_responsable" className={SEL} value={form.responsable_id} onChange={field("responsable_id")} aria-required aria-invalid={Boolean(errors.responsable_id)}>
            <option value="">{usuarios.length === 0 ? "Cargando..." : "Seleccionar usuario"}</option>
            {usuarios.map((u) => <option key={u.id} value={u.id}>{u.nombre} {u.apellido}</option>)}
          </select>
          {errors.responsable_id && <p className="text-xs text-destructive" role="alert">{errors.responsable_id}</p>}
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="obj_prioridad">Prioridad</Label>
          <select id="obj_prioridad" className={SEL} value={form.prioridad} onChange={field("prioridad")}>
            <option value="alta">Alta</option>
            <option value="media">Media</option>
            <option value="baja">Baja</option>
          </select>
        </div>
      </div>
      <ObjetivoCamposOpcionales
        form={form} usuarios={usuarios} padres={padres}
        field={field} onToggleResponsable={onToggleResponsable}
      />
    </div>
  )
}

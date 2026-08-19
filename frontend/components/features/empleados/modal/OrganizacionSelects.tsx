import type { ChangeEvent } from "react"

import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { type FieldFactory, type FormData, type FormErrors } from "./_constants"
import type { Area } from "@/types/area"
import type { EmpleadoSeleccionable } from "@/types/empleado"
import type { Empresa } from "@/types/empresa"

interface Props {
  form: FormData
  errors: FormErrors
  isEdit: boolean
  empresas: Empresa[]
  empresasLoading: boolean
  areas: Area[]
  areasLoading: boolean
  seleccionables: EmpleadoSeleccionable[]
  currentEmpleadoId?: string
  field: FieldFactory
  onEmpresaChange: (e: ChangeEvent<HTMLSelectElement>) => void
}

/**
 * Selects de empresa (solo crear), área (filtrada por empresa en crear, todas en editar)
 * y superior inmediato (empleados activos de la empresa, excluyendo al propio en edición).
 * Controlado por el orquestador. Fragmento hijo directo de la grilla.
 */
export function OrganizacionSelects({
  form, errors, isEdit, empresas, empresasLoading, areas, areasLoading,
  seleccionables, currentEmpleadoId, field, onEmpresaChange,
}: Props) {
  // En edición, uno no puede ser su propio superior.
  const superiores = seleccionables.filter((e) => e.id !== currentEmpleadoId)
  return (
    <>
      {!isEdit && (
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="empresa_id">
            Empresa
            <span className="ml-0.5 text-destructive" aria-hidden>*</span>
          </Label>
          <Select
            className="w-auto"
            id="empresa_id"
            value={form.empresa_id}
            onChange={onEmpresaChange}
            disabled={empresasLoading}
            aria-invalid={Boolean(errors.empresa_id)}
            aria-required
          >
            <option value="">
              {empresasLoading ? "Cargando..." : "Seleccionar empresa"}
            </option>
            {empresas.map((emp) => (
              <option key={emp.id} value={emp.id}>{emp.nombre}</option>
            ))}
          </Select>
          {errors.empresa_id && (
            <p className="text-xs text-destructive" role="alert">{errors.empresa_id}</p>
          )}
        </div>
      )}

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="area_id">
          Área
          <span className="ml-0.5 text-destructive" aria-hidden>*</span>
        </Label>
        <Select
          className="w-auto"
          id="area_id"
          value={form.area_id}
          onChange={field("area_id")}
          disabled={areasLoading || (!isEdit && !form.empresa_id)}
          aria-invalid={Boolean(errors.area_id)}
          aria-required
        >
          <option value="">
            {areasLoading
              ? "Cargando áreas..."
              : !isEdit && !form.empresa_id
              ? "Primero seleccioná una empresa"
              : "Seleccionar área"}
          </option>
          {areas.map((a) => (
            <option key={a.id} value={a.id}>{a.nombre}</option>
          ))}
        </Select>
        {errors.area_id && (
          <p className="text-xs text-destructive" role="alert">{errors.area_id}</p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="manager_id">Superior inmediato</Label>
        <Select
          className="w-auto"
          id="manager_id"
          value={form.manager_id}
          onChange={field("manager_id")}
        >
          <option value="">Sin superior</option>
          {superiores.map((e) => (
            <option key={e.id} value={e.id}>{e.apellido}, {e.nombre}</option>
          ))}
        </Select>
      </div>
    </>
  )
}

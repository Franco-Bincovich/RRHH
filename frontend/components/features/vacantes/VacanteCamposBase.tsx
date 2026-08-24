"use client"

import { FieldError } from "@/components/ui/FieldError"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import type { VacanteFormData, VacanteFormErrors } from "@/components/features/vacantes/vacanteForm"
import type { Area } from "@/types/area"
import type { Empresa } from "@/types/empresa"

/**
 * Los cuatro campos del alta de vacante. Presentacional: sin estado, sin fetch, sin submit —
 * todo eso se queda en VacanteModal.tsx, su único consumidor. Extraído porque el modal estaba en
 * 251/150. El movimiento fue PURO: JSX, clases, ids, `aria-*` y el ORDEN son idénticos.
 *
 * 🔴 LOS DOS CONJUNTOS QUE VIENEN, Y POR QUÉ NO ESTÁN EN DOS ARCHIVOS.
 * La feature del perfil de puesto parte estos campos en dos que se comportan distinto:
 *   · DE PROCESO — `empresa_id` y `area_id`. Un perfil es del GRUPO y `areas.empresa_id` es NOT
 *     NULL (más el trigger `trg_emp_vacantes`), así que un perfil NO puede traer ninguno.
 *   · DESCRIPTIVOS — `titulo` y `tipo_contrato`. Son los que el perfil copia.
 * El acoplamiento está en el código: empresa y área comparten `areas`, `areasLoading` y un
 * handler propio que resetea el área; los otros dos solo usan `field`.
 *
 * 🔴 PERO EL DOM LOS ALTERNA: empresa · título · área · tipo de contrato. Separarlos obliga a
 * reordenar la pantalla, y eso deja de ser un movimiento puro — la misma pared contra la que
 * chocó el corte de ObjetivoFormFields. Así que los cuatro quedan acá y la separación vive donde
 * SÍ se puede expresar sin tocar el markup: el contrato de props, agrupado y rotulado abajo.
 * Los campos descriptivos NUEVOS (funciones, requisitos, formación, experiencia, conocimientos
 * técnicos) no vienen a este archivo: nacen en el suyo, como `ObjetivoCamposOpcionales`.
 */

interface Props {
  form: VacanteFormData
  errors: VacanteFormErrors
  // ── De proceso: atan la vacante a UNA empresa. Un perfil del grupo no puede llenarlos. ──
  empresas: Empresa[]
  areas: Area[]
  areasLoading: boolean
  /** Handler propio y no `field`: cambiar de empresa RESETEA el área elegida. */
  onEmpresaChange: (e: React.ChangeEvent<HTMLSelectElement>) => void
  // ── Descriptivos: `titulo` y `tipo_contrato` son los que el perfil de puesto copia. ──
  field: (key: keyof VacanteFormData) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => void
}

export function VacanteCamposBase({
  form, errors, empresas, areas, areasLoading, onEmpresaChange, field,
}: Props) {
  return (
    <div className="flex flex-col gap-4 py-2">

      {/* Empresa */}
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="empresa_id">
          Empresa
          <span className="ml-0.5 text-destructive" aria-hidden>*</span>
        </Label>
        <Select
          id="empresa_id"
          value={form.empresa_id}
          onChange={onEmpresaChange}
          aria-invalid={Boolean(errors.empresa_id)}
          aria-required
        >
          <option value="">Seleccionar empresa</option>
          {empresas.map((e) => (
            <option key={e.id} value={e.id}>{e.nombre}</option>
          ))}
        </Select>
        {errors.empresa_id && (
          <FieldError>{errors.empresa_id}</FieldError>
        )}
      </div>

      {/* Título */}
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="titulo">
          Título
          <span className="ml-0.5 text-destructive" aria-hidden>*</span>
        </Label>
        <Input
          id="titulo"
          value={form.titulo}
          onChange={field("titulo")}
          aria-invalid={Boolean(errors.titulo)}
          aria-required
        />
        {errors.titulo && (
          <FieldError>{errors.titulo}</FieldError>
        )}
      </div>

      {/* Área — dependiente de empresa */}
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="area_id">
          Área
          <span className="ml-0.5 text-destructive" aria-hidden>*</span>
        </Label>
        <Select
          id="area_id"
          value={form.area_id}
          onChange={field("area_id")}
          disabled={!form.empresa_id || areasLoading}
          aria-invalid={Boolean(errors.area_id)}
          aria-required
        >
          <option value="">
            {!form.empresa_id ? "Seleccioná primero una empresa" : areasLoading ? "Cargando..." : "Seleccionar área"}
          </option>
          {areas.map((a) => (
            <option key={a.id} value={a.id}>{a.nombre}</option>
          ))}
        </Select>
        {errors.area_id && (
          <FieldError>{errors.area_id}</FieldError>
        )}
      </div>

      {/* Tipo de contrato */}
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="tipo_contrato">
          Tipo de contrato
          <span className="ml-0.5 text-destructive" aria-hidden>*</span>
        </Label>
        <Select
          id="tipo_contrato"
          value={form.tipo_contrato}
          onChange={field("tipo_contrato")}
        >
          <option value="efectivo">Relación de dependencia</option>
          <option value="plazo_fijo">Plazo fijo</option>
          <option value="contratado">Contratado</option>
          <option value="pasantia">Pasantía</option>
        </Select>
      </div>
    </div>
  )
}

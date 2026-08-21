import { EmpleadoCombobox } from "@/components/features/shared/EmpleadoCombobox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import type { Empleado } from "@/types/empleado"
import type { Recategorizacion } from "@/types/recategorizacion"

import { CampoNuevo } from "./CampoNuevo"
import { MAX_MOTIVO, type ErroresRecategorizacion, type FormRecategorizacion } from "./guardarRecategorizacion"

/**
 * El CUERPO del formulario de recategorización. Separado del modal a propósito: el `Dialog` monta
 * por portal y con vitest sin jsdom renderiza a `""`, así que todo lo que haya que poder
 * desmentir tiene que estar afuera de él.
 *
 * 🔴 LOS TRES VALORES ANTERIORES NO SE PIDEN NI SE DEJAN ESCRIBIR: los pone el backend y se
 * MUESTRAN cuando vuelven. El porqué completo está en `CampoNuevo`.
 *
 * 🔴 EL COLABORADOR NO SE PUEDE CAMBIAR EN LA EDICIÓN. `RecategorizacionUpdate` no acepta
 * `empleado_id`: mover una recategorización de persona invalidaría los `*_anterior` de las dos
 * cadenas —la que deja y la que integra— sin ninguna señal. Acá el selector va `disabled` con el
 * motivo escrito al lado, no escondido: esconderlo dejaría la ficha de edición sin decir sobre
 * quién es la fila.
 *
 * 🔴 SIN ESTADO NI APROBACIÓN (§7). Es registro puro: se carga y queda cargado. No hay un select
 * de "estado" ni un botón de "enviar a aprobación", porque no existen del otro lado.
 */
export function RecategorizacionForm({
  form, errores, onChange, onEmpleadoChange, original, mostrarImpacto,
}: {
  form: FormRecategorizacion
  errores: ErroresRecategorizacion
  onChange: (campo: keyof FormRecategorizacion, valor: string) => void
  onEmpleadoChange: (e: Empleado | null) => void
  /** La fila que se está editando. `undefined` = alta. De acá salen los valores anteriores. */
  original?: Recategorizacion
  /** `false` (sin COSTOS + READ) esconde el campo de impacto entero, no lo deshabilita. */
  mostrarImpacto: boolean
}) {
  const esEdicion = Boolean(original)

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="recat-empleado">
          Colaborador <span className="text-destructive" aria-hidden>*</span>
        </Label>
        <EmpleadoCombobox
          id="recat-empleado"
          value={form.empleadoId}
          onChange={onEmpleadoChange}
          etiquetaInicial={original?.empleado_nombre ?? undefined}
          disabled={esEdicion}
          mensajeDeshabilitado="No se puede mover una recategorización de persona"
          invalid={Boolean(errores.empleadoId)}
        />
        {esEdicion && (
          <p className="text-xs text-muted-foreground">
            El colaborador no se puede cambiar: la corrección es registrar la recategorización
            buena, no mover ésta.
          </p>
        )}
        {errores.empleadoId && (
          <p className="text-sm text-destructive" role="alert">{errores.empleadoId}</p>
        )}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="recat-fecha">Fecha efectiva</Label>
        {/* Editable HACIA ATRÁS: es cuándo RIGIÓ el cambio, no cuándo se carga. El aviso de lo
            que eso implica lo pone el modal, en ámbar sobre el pie. */}
        <Input
          id="recat-fecha"
          type="date"
          value={form.fechaEfectiva}
          onChange={(e) => onChange("fechaEfectiva", e.target.value)}
        />
      </div>

      {/* Los tres pares. Al menos uno tiene que venir cargado — lo exige el CHECK de la base y lo
          repite la validación local para no gastar un viaje a la red. */}
      <CampoNuevo id="recat-rol" label="Rol nuevo" anterior={original?.rol_anterior}
                  value={form.rolNuevo} onChange={(v) => onChange("rolNuevo", v)} />
      <CampoNuevo id="recat-seniority" label="Seniority nueva" anterior={original?.seniority_anterior}
                  value={form.seniorityNueva} onChange={(v) => onChange("seniorityNueva", v)} />
      <CampoNuevo id="recat-categoria" label="Categoría nueva" anterior={original?.categoria_anterior}
                  value={form.categoriaNueva} onChange={(v) => onChange("categoriaNueva", v)} />
      {errores.cambios && (
        <p className="text-sm text-destructive" role="alert">{errores.cambios}</p>
      )}

      <div className="space-y-1.5">
        <Label htmlFor="recat-motivo">
          Motivo <span className="text-destructive" aria-hidden>*</span>
        </Label>
        <Textarea
          id="recat-motivo"
          rows={3}
          value={form.motivo}
          maxLength={MAX_MOTIVO}
          aria-invalid={Boolean(errores.motivo)}
          onChange={(e) => onChange("motivo", e.target.value)}
        />
        {errores.motivo && (
          <p className="text-sm text-destructive" role="alert">{errores.motivo}</p>
        )}
      </div>

      {mostrarImpacto && (
        <div className="space-y-1.5">
          <Label htmlFor="recat-impacto">Impacto salarial</Label>
          {/* 🔴 UN MONTO EN PESOS, NO UN PORCENTAJE (§7). El rótulo y el placeholder lo dicen:
              "impacto porcentual" es una de las cosas que un prototipo prometió y no existen. */}
          <Input
            id="recat-impacto"
            inputMode="decimal"
            value={form.impactoSalarial}
            placeholder="Monto en pesos, opcional. Ej.: 150000"
            onChange={(e) => onChange("impactoSalarial", e.target.value)}
          />
        </div>
      )}
    </div>
  )
}

"use client"

import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { FormErrores } from "@/components/ui/FormErrores"
import { getRol } from "@/services/permisos"
import { SeleccionEmpleado } from "@/components/features/shared/SeleccionEmpleado"
import { CamposAusencia } from "./CamposAusencia"
import { AusenciaAdjuntos } from "./AusenciaAdjuntos"
import { useAusenciaForm } from "./useAusenciaForm"
import { useTiposAusencia } from "./useTiposAusencia"
import type { Ausencia } from "@/types/ausencias"

interface AusenciaModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
  editing?: Ausencia | null
}

export function AusenciaModal({ open, onClose, onSuccess, editing }: AusenciaModalProps) {
  const isMando = getRol() === "mandos_medios"
  const { form, setForm, errors, setErrors, submitting, serverError, pendientes, setPendientes,
          field, submit } = useAusenciaForm(open, editing, isMando)
  const { tipos, nuevoTipo, setNuevoTipo, creandoTipo, crearTipo } = useTiposAusencia(open)

  const isEditing = Boolean(editing)
  // El PRIMER nivel de la validación es la CUENTA, no la lista de campos: el "qué corrijo" lo
  // contesta el segundo nivel, en cada campo. Ver `components/ui/FormErrores.tsx`.
  const cantidadErrores = Object.values(errors).filter(Boolean).length

  function handleEmpresaChange(empresaId: string) {
    setForm((p) => ({ ...p, empresa_id: empresaId, empleado_id: "" }))
    setErrors((p) => ({ ...p, empresa_id: undefined, empleado_id: undefined }))
  }

  function handleEmpleadoChange(empleadoId: string) {
    setForm((p) => ({ ...p, empleado_id: empleadoId }))
    if (errors.empleado_id) setErrors((p) => ({ ...p, empleado_id: undefined }))
  }

  async function handleCrearTipo() {
    const created = await crearTipo()
    if (created) {
      setForm((p) => ({ ...p, tipo_id: created.id }))
      setErrors((p) => ({ ...p, tipo_id: undefined, nuevo_tipo: undefined }))
    } else if (nuevoTipo.trim()) {
      setErrors((p) => ({ ...p, nuevo_tipo: "No se pudo crear el tipo" }))
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    void submit(onSuccess)
  }

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      {/* El ancho (560px) y los campos de 34px los pone el patrón, no el modal: por eso ya no
          lleva `max-w-lg`. */}
      <DialogContent patron="formulario">
        <DialogHeader>
          <DialogTitle>{isEditing ? "Editar ausencia" : "Registrar ausencia"}</DialogTitle>
          {/* 🔴 UNA LÍNEA QUE EXPLICA LA CONSECUENCIA, no lo que el modal es (§3). Lo que el
              usuario no puede saber mirando la pantalla es qué pasa DESPUÉS de Guardar. */}
          <DialogDescription>
            {isEditing
              ? "Los cambios quedan registrados en la auditoría con tu usuario y se ven en el listado al instante."
              : "Se registra la ausencia y, si el tipo computa, pasa a contar en el ausentismo del mes."}
          </DialogDescription>
        </DialogHeader>

        <form id="ausencia-form" onSubmit={handleSubmit} noValidate>
          <div className="flex flex-col gap-4 py-2">
            <FormErrores cantidad={cantidadErrores} />
            {!isEditing && (
              <SeleccionEmpleado
                isMando={isMando}
                empresaId={form.empresa_id}
                empleadoId={form.empleado_id}
                onEmpresaChange={handleEmpresaChange}
                onEmpleadoChange={handleEmpleadoChange}
                errorEmpresa={errors.empresa_id}
                errorEmpleado={errors.empleado_id}
              />
            )}

            <CamposAusencia
              form={form}
              errors={errors}
              field={field}
              onJustificada={(checked) => setForm((p) => ({ ...p, justificada: checked }))}
              tipos={tipos}
              nuevoTipo={nuevoTipo}
              onNuevoTipo={setNuevoTipo}
              creandoTipo={creandoTipo}
              onCrearTipo={handleCrearTipo}
            />
            <AusenciaAdjuntos isEditing={isEditing} ausenciaId={editing?.id}
              pendientes={pendientes} onPendientesChange={setPendientes} disabled={submitting} />
          </div>

          {serverError && <p className="mt-2 text-sm text-destructive" role="alert">{serverError}</p>}
        </form>

        <DialogFooter>
          <Button type="button" variant="outline" className="min-h-11" onClick={onClose} disabled={submitting}>Cancelar</Button>
          <Button type="submit" form="ausencia-form" className="min-h-11" disabled={submitting}>
            {submitting ? "Guardando..." : isEditing ? "Guardar cambios" : "Registrar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

"use client"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { AvisoImpacto } from "@/components/ui/AvisoImpacto"
import { Button } from "@/components/ui/button"
import { FormErrores } from "@/components/ui/FormErrores"
import type { Empleado } from "@/types/empleado"
import { hoyISO } from "./modal/form-utils"
import { useEmpleadoForm } from "./modal/useEmpleadoForm"
import { useEmpleadoFormData } from "./modal/useEmpleadoFormData"
import { DatosPersonalesFields } from "./modal/DatosPersonalesFields"
import { DatosLaboralesFields } from "./modal/DatosLaboralesFields"

interface EmpleadoModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
  empleado?: Empleado
}

export function EmpleadoModal({ open, onClose, onSuccess, empleado }: EmpleadoModalProps) {
  const {
    isEdit, form, errors, submitting, serverError, cantidadErrores,
    field, onValue, onLider, onRoles, onEstadoAlta, handleEmpresaChange, handleSubmit,
  } = useEmpleadoForm(open, empleado, onSuccess)

  const { empresas, empresasLoading, areas, areasLoading, rolesSugeridos, seleccionables } =
    useEmpleadoFormData(open, isEdit, form.empresa_id, isEdit ? empleado?.empresa_id ?? "" : form.empresa_id)

  /*
   * 🔴 EL AVISO EXPLICA LA CONSECUENCIA DE LO ELEGIDO, no el problema del formulario. Hasta que
   * el alta pudo nacer en `preingreso`, este cartel avisaba de un bug ("se crea activa igual");
   * ahora que el usuario elige, lo que no puede deducir de la pantalla es qué implica cada
   * opción — si esa persona entra o no en la dotación del mes, que es el número que el directorio
   * mira. Sólo aparece cuando la fecha es futura: con fecha pasada las dos opciones significan lo
   * mismo y el cartel sería ruido.
   */
  const ingresoFuturo = !isEdit && form.fecha_ingreso > hoyISO()

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      {/* El ancho lo pone el patrón (560px, §3), no el modal: por eso ya no lleva `max-w-2xl`. */}
      <DialogContent patron="formulario">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Editar empleado" : "Nuevo empleado"}</DialogTitle>
          {/*
           * 🔴 UNA LÍNEA QUE EXPLICA LA CONSECUENCIA, no lo que el modal es (§3). "Cargá los datos
           * del empleado" describe el formulario y no le dice nada a nadie; lo que el usuario no
           * puede saber mirando la pantalla es qué pasa DESPUÉS de apretar Guardar.
           */}
          <DialogDescription>
            {isEdit
              ? "Los cambios quedan registrados en la auditoría con tu usuario y se ven en la ficha al instante."
              : "Se crea el legajo y la persona pasa a contar en la dotación de la empresa que elijas."}
          </DialogDescription>
        </DialogHeader>

        <form id="empleado-form" onSubmit={handleSubmit} noValidate className="space-y-5">
          {/* Primer nivel de la validación: la cuenta, arriba de todo. El segundo nivel —qué
              corregir— va en cada campo. */}
          <FormErrores cantidad={cantidadErrores} />

          <section>
            <h3 className="mb-3 text-sm font-semibold text-foreground">Información personal</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <DatosPersonalesFields form={form} errors={errors} field={field} onValue={onValue} />
            </div>
          </section>

          <section>
            <h3 className="mb-3 text-sm font-semibold text-foreground">Información laboral</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <DatosLaboralesFields
                form={form}
                errors={errors}
                isEdit={isEdit}
                empresas={empresas}
                empresasLoading={empresasLoading}
                areas={areas}
                areasLoading={areasLoading}
                seleccionables={seleccionables} currentEmpleadoId={empleado?.id}
                rolesSugeridos={rolesSugeridos}
                field={field}
                onEmpresaChange={handleEmpresaChange}
                onRolesChange={onRoles}
                onValue={onValue}
                onLider={onLider}
                onEstadoAlta={onEstadoAlta}
              />
            </div>
          </section>

          {serverError && (
            <p className="text-sm text-destructive" role="alert">{serverError}</p>
          )}
        </form>

        <DialogFooter
          aviso={ingresoFuturo ? (
            <AvisoImpacto>
              {form.estado === "preingreso" ? (
                <>
                  El legajo queda en <strong className="font-semibold">preingreso</strong>: la
                  persona <strong className="font-semibold">no cuenta en la dotación</strong> ni
                  en las altas del mes hasta que alguien confirme el ingreso desde su ficha.
                </>
              ) : (
                <>
                  La fecha de ingreso todavía no llegó y el legajo se crea{" "}
                  <strong className="font-semibold">activo</strong>: la persona{" "}
                  <strong className="font-semibold">cuenta en la dotación desde hoy</strong> y en
                  las altas de este mes.
                </>
              )}
            </AvisoImpacto>
          ) : undefined}
        >
          {/* Secundario FANTASMA y primario sólido, abajo a la derecha (§3). */}
          <Button
            type="button"
            variant="ghost"
            className="min-h-11"
            onClick={onClose}
            disabled={submitting}
          >
            Cancelar
          </Button>
          <Button
            type="submit"
            form="empleado-form"
            className="min-h-11"
            disabled={submitting}
          >
            {submitting ? "Guardando..." : isEdit ? "Guardar cambios" : "Crear empleado"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

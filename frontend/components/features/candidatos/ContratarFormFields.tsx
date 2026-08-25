"use client"

import { FieldError } from "@/components/ui/FieldError"
import { Input } from "@/components/ui/input"
import { RolesInput } from "@/components/ui/RolesInput"
import type { ErroresContratar, FormContratar } from "@/components/features/candidatos/_contratarForm"

/**
 * Los tres campos del formulario de contratación: el email corporativo, el rol y la fecha
 * acordada de ingreso. Son los únicos datos que el puente candidato → empleado no puede derivar
 * (el resto sale del candidato y de su vacante).
 *
 * Salió de `ContratarCandidatoButton.tsx`, que quedó en 175 contra el límite de 150 al ganar la
 * validación por campo. Molde: `AreaModal`/`ClienteModal` — los campos a un `*FormFields.tsx` y
 * la validación a un `_*.ts` puro, que es lo único que se puede testear sin jsdom. El botón se
 * queda con el acto (abrir, confirmar, manejar el error del backend).
 *
 * Presentacional y controlado: no tiene estado, no fetchea, no valida. Recibe los valores, los
 * errores ya calculados y los setters.
 */
export function ContratarFormFields({
  form, errores, sugerencias, hoy, emailPersonal, onCampo,
}: {
  form: FormContratar
  errores: ErroresContratar
  sugerencias: string[]
  /** ISO de hoy, para el `min` del date. Viene de arriba: el mismo valor que usa la validación. */
  hoy: string
  /** El mail con el que se postuló. Se muestra para evitar el error de pegarlo acá. */
  emailPersonal: string
  onCampo: <K extends keyof FormContratar>(campo: K, valor: FormContratar[K]) => void
}) {
  return (
    <>
      <label className="flex flex-col gap-1.5">
        <span className="text-sm font-medium text-foreground">Email corporativo</span>
        <Input
          type="email" value={form.email} placeholder="nombre@empresa.com"
          aria-invalid={Boolean(errores.email)}
          onChange={(e) => onCampo("email", e.target.value)}
        />
        <FieldError>{errores.email}</FieldError>
        {/* Se aclara porque el error natural es pegar el mail con el que se postuló: la
            columna es única en TODO el sistema y ese valor queda quemado para siempre. */}
        <span className="text-xs text-muted-foreground">
          No es el personal ({emailPersonal}), que queda igual en la ficha.
        </span>
      </label>

      {/* 🔑 El `<div>` envolvente no es decorativo: `RolesInput` ya trae su propio `<Label>`, así
          que el mensaje de error tiene que ir afuera de él y no adentro de otro `<label>` — dos
          labels apuntando al mismo control hacen que el lector de pantalla anuncie el campo dos
          veces. */}
      <div>
        <RolesInput
          value={form.roles} onChange={(r) => onCampo("roles", r)} suggestions={sugerencias}
          label="Rol en el legajo" required
        />
        <FieldError>{errores.roles}</FieldError>
      </div>

      <label className="flex flex-col gap-1.5">
        <span className="text-sm font-medium text-foreground">Fecha de ingreso acordada</span>
        {/* `min` = hoy: el backend exige una fecha hacia adelante y rechaza el pasado con
            FECHA_INGRESO_PASADA. Es la UI evitando el viaje, no la validación — el `min` de un
            input de fecha no impide tipear el valor a mano, y por eso `_contratarForm` lo
            vuelve a chequear. */}
        <Input type="date" value={form.fecha} min={hoy}
          aria-invalid={Boolean(errores.fecha)}
          onChange={(e) => onCampo("fecha", e.target.value)} />
        <FieldError>{errores.fecha}</FieldError>
      </label>
    </>
  )
}

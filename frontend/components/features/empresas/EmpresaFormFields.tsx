"use client"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"

import type { EmpresaFormData, EmpresaFormErrors } from "./empresaForm"

/**
 * Los campos del formulario de empresa. PRESENTACIONAL: sin estado, sin fetch, sin efectos —
 * recibe el form, sus errores y un `onField` por clave.
 *
 * Sale de `EmpresaModal.tsx` por la misma razón que `AreaFormFields` salió de `AreaModal`: el
 * modal estaba en 226/150 antes de esta tanda y el patrón de modal de formulario le sumaba más.
 * Acá vive el RENDER; la definición del formulario está en `empresaForm.ts` y el ciclo de vida
 * en el modal.
 *
 * ⚠️ EL SEGUNDO NIVEL DE LA VALIDACIÓN VIVE ACÁ: el mensaje debajo de cada campo, con
 * `aria-invalid` en el control y `role="alert"` en el texto. El primero —el banner con la cuenta—
 * lo pone el modal, arriba de todo. Los dos son necesarios y contestan preguntas distintas:
 * "¿cuánto me falta?" y "¿qué corrijo?".
 */
export function EmpresaFormFields({ form, errors, onField }: {
  form: EmpresaFormData
  errors: EmpresaFormErrors
  onField: (key: keyof EmpresaFormData) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void
}) {
  return (
    <>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="nombre">
          Nombre <span className="ml-0.5 text-destructive" aria-hidden>*</span>
        </Label>
        <Input
          id="nombre"
          value={form.nombre}
          onChange={onField("nombre")}
          aria-invalid={Boolean(errors.nombre)}
          aria-required
        />
        {errors.nombre && (
          <p className="text-xs text-destructive" role="alert">{errors.nombre}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="razon_social">Razón social</Label>
          <Input id="razon_social" value={form.razon_social} onChange={onField("razon_social")} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="cuit">CUIT</Label>
          <Input
            id="cuit"
            value={form.cuit}
            onChange={onField("cuit")}
            placeholder="XX-XXXXXXXX-X"
            aria-invalid={Boolean(errors.cuit)}
          />
          {errors.cuit && (
            <p className="text-xs text-destructive" role="alert">{errors.cuit}</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="telefono">Teléfono</Label>
          <Input id="telefono" value={form.telefono} onChange={onField("telefono")} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" value={form.email} onChange={onField("email")} />
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="direccion">Dirección</Label>
        <Textarea
          id="direccion"
          value={form.direccion}
          onChange={onField("direccion")}
          rows={2}
          className="resize-none"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="logo_url">URL del logo</Label>
        <Input
          id="logo_url"
          value={form.logo_url}
          onChange={onField("logo_url")}
          placeholder="https://..."
        />
        <p className="text-xs text-muted-foreground">
          Para subir desde archivo usá la sección de logo en el detalle de la empresa.
        </p>
      </div>
    </>
  )
}

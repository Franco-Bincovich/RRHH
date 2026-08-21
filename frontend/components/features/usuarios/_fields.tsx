"use client"

import { useState } from "react"
import { Eye, EyeOff } from "lucide-react"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"

interface TextFieldProps {
  id: string
  label: string
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  error?: string
  type?: string
}

/** Campo de texto requerido con label, asterisco y error inline (form de alta de usuario). */
export function TextField({ id, label, value, onChange, error, type }: TextFieldProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>
        {label} <span className="ml-0.5 text-destructive" aria-hidden>*</span>
      </Label>
      <Input
        id={id}
        type={type}
        value={value}
        onChange={onChange}
        aria-invalid={Boolean(error)}
        aria-required
      />
      {error && <p className="text-xs text-destructive" role="alert">{error}</p>}
    </div>
  )
}

interface PasswordFieldProps {
  id: string
  label: string
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  error?: string
  autoComplete?: string
  disabled?: boolean
  placeholder?: string
}

/**
 * Campo de contraseña con mostrar/ocultar y error inline. Lo usan el form de cambio de contraseña
 * y el de `/login` — que hasta esta tanda tenía su propia copia del campo, del ojo y del
 * `aria-label` de mostrar/ocultar, con el mismo markup escrito dos veces.
 *
 * 🔴 EL BOTÓN DEL OJO MIDE 44px Y ANTES MEDÍA 16. Era un `<button>` sin caja, del tamaño del
 * ícono, centrado con `-translate-y-1/2`: en un teléfono es un blanco de 16px al lado del borde
 * de la pantalla. Ahora ocupa el alto completo del campo y 44px de ancho (`inset-y-0 w-11`), sin
 * mover el ícono de lugar. El `pr-11` del input es lo que evita que el texto de la contraseña
 * pase por debajo.
 *
 * `tabIndex={-1}` se conserva: mostrar la contraseña no es un paso del formulario y meterlo en el
 * recorrido del tabulador obliga a saltarlo en cada campo.
 */
export function PasswordField({ id, label, value, onChange, error, autoComplete, disabled, placeholder }: PasswordFieldProps) {
  const [show, setShow] = useState(false)
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <div className="relative">
        <Input
          id={id}
          type={show ? "text" : "password"}
          value={value}
          onChange={onChange}
          autoComplete={autoComplete}
          disabled={disabled}
          placeholder={placeholder}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-error` : undefined}
          className="min-h-[2.75rem] pr-11"
        />
        <button
          type="button"
          onClick={() => setShow((v) => !v)}
          disabled={disabled}
          tabIndex={-1}
          aria-label={show ? "Ocultar contraseña" : "Mostrar contraseña"}
          className="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-r-lg text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none"
        >
          {show ? <EyeOff className="size-4" aria-hidden /> : <Eye className="size-4" aria-hidden />}
        </button>
      </div>
      {error && <p id={`${id}-error`} className="text-xs text-destructive" role="alert">{error}</p>}
    </div>
  )
}

interface SelectOption {
  value: string
  label: string
}

interface SelectFieldProps {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  options: readonly SelectOption[]
  error?: string
}

/** Selector requerido con label, asterisco y error inline (mismo patrón que TextField). */
export function SelectField({ id, label, value, onChange, options, error }: SelectFieldProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>
        {label} <span className="ml-0.5 text-destructive" aria-hidden>*</span>
      </Label>
      <Select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={Boolean(error)}
        aria-required
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </Select>
      {error && <p className="text-xs text-destructive" role="alert">{error}</p>}
    </div>
  )
}

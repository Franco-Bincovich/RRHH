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
}

/** Campo de contraseña con mostrar/ocultar y error inline. Reusado en el form de cambio. */
export function PasswordField({ id, label, value, onChange, error, autoComplete, disabled }: PasswordFieldProps) {
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
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-error` : undefined}
          className="min-h-[2.75rem] pr-10"
        />
        <button
          type="button"
          onClick={() => setShow((v) => !v)}
          disabled={disabled}
          tabIndex={-1}
          aria-label={show ? "Ocultar contraseña" : "Mostrar contraseña"}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground disabled:pointer-events-none"
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

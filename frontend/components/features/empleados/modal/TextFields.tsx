import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import type { FieldFactory, FormData, FormErrors, TextField } from "./_constants"

/**
 * Renderiza una lista de inputs de texto (controlados). Reusable por las secciones
 * Personal y Laboral. El estado vive en el orquestador: recibe valores (form),
 * errores y la fábrica de handlers por campo. Fragmento hijo directo de la grilla.
 */
export function TextFields({
  fields,
  form,
  errors,
  field,
}: {
  fields: ReadonlyArray<TextField>
  form: FormData
  errors: FormErrors
  field: FieldFactory
}) {
  return (
    <>
      {fields.map(({ field: key, label, required, type, placeholder }) => (
        <div key={key} className="flex flex-col gap-1.5">
          <Label htmlFor={key}>
            {label}
            {required && (
              <span className="ml-0.5 text-destructive" aria-hidden>*</span>
            )}
          </Label>
          <Input
            id={key}
            type={type ?? "text"}
            value={form[key]}
            onChange={field(key)}
            placeholder={placeholder}
            aria-invalid={Boolean(errors[key])}
            aria-required={required}
          />
          {errors[key] && (
            <p className="text-[11px] text-destructive" role="alert">{errors[key]}</p>
          )}
        </div>
      ))}
    </>
  )
}

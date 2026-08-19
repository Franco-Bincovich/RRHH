import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { TextFields } from "./TextFields"
import { AutocompleteFields } from "./AutocompleteFields"
import { DomicilioFields } from "./DomicilioFields"
import { PERSONAL_AUTOCOMPLETE, PERSONAL_CONTACT_FIELDS, PERSONAL_DOC_FIELDS, PERSONAL_IDENTITY_FIELDS, type AutocompleteKey, type FieldFactory, type FormData, type FormErrors } from "./_constants"

/**
 * Sección "Información personal" (controlada). Orden: identidad → documento
 * (tipo + número + CUIT/CUIL juntos) → sexo (F/M fijo) → contacto → domicilio. El estado vive
 * en el orquestador.
 */
export function DatosPersonalesFields({
  form,
  errors,
  field,
  onValue,
}: {
  form: FormData
  errors: FormErrors
  field: FieldFactory
  onValue: (key: AutocompleteKey) => (value: string) => void
}) {
  return (
    <>
      <TextFields fields={PERSONAL_IDENTITY_FIELDS} form={form} errors={errors} field={field} />

      {/* Documento: tipo (autocompletado) + número + CUIT/CUIL, juntos */}
      <AutocompleteFields fields={PERSONAL_AUTOCOMPLETE} form={form} onValue={onValue} />
      <TextFields fields={PERSONAL_DOC_FIELDS} form={form} errors={errors} field={field} />

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="sexo">Sexo</Label>
        <Select className="w-auto" id="sexo" value={form.sexo} onChange={field("sexo")}>
          <option value="">Sin especificar</option>
          <option value="F">Femenino</option>
          <option value="M">Masculino</option>
        </Select>
      </div>

      <TextFields fields={PERSONAL_CONTACT_FIELDS} form={form} errors={errors} field={field} />

      {/* Domicilio, agrupado: seis campos que se completan juntos. */}
      <DomicilioFields form={form} errors={errors} field={field} />
    </>
  )
}

"use client"

import { useEffect, useState } from "react"

import { Label } from "@/components/ui/label"
import { TextFields } from "./TextFields"
import { fetchProvincias } from "@/services/provincias"
import {
  DOMICILIO_FIELDS, SELECT_CLASS,
  type FieldFactory, type FormData, type FormErrors,
} from "./_constants"

/**
 * Bloque "Domicilio" del modal de empleado: los cinco campos de texto más el select de
 * provincia.
 *
 * PROVINCIA ES UN SELECT CERRADO, no un input. Es lo único que separa un campo estructurado
 * de uno de texto libre con nombre nuevo: si cada persona escribe "Cba", "Córdoba" y "CORDOBA",
 * agrupar por provincia vuelve a ser imposible, que es justo lo que estos campos vinieron a
 * arreglar. El backend valida contra la misma lista y responde 422 si el valor no está.
 *
 * Las opciones se PIDEN al backend (`/api/empleados/provincias`) en vez de estar acá: una copia
 * local se separaría de la del backend en silencio y el usuario podría elegir una opción que
 * después es rechazada al guardar. Ver services/provincias.ts.
 *
 * Si la lista no carga, el select queda con la opción vacía y el campo simplemente no se
 * completa: es preferible a caer a un input libre, que guardaría un valor que el backend
 * rechazaría igual.
 */
export function DomicilioFields({
  form,
  errors,
  field,
}: {
  form: FormData
  errors: FormErrors
  field: FieldFactory
}) {
  const [provincias, setProvincias] = useState<string[]>([])

  useEffect(() => {
    let cancelado = false
    fetchProvincias()
      .then((p) => { if (!cancelado) setProvincias(p) })
      .catch(() => { if (!cancelado) setProvincias([]) })
    return () => { cancelado = true }
  }, [])

  return (
    <>
      <TextFields fields={DOMICILIO_FIELDS} form={form} errors={errors} field={field} />

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="domicilio_provincia">Provincia</Label>
        <select
          id="domicilio_provincia"
          className={SELECT_CLASS}
          value={form.domicilio_provincia}
          onChange={field("domicilio_provincia")}
        >
          <option value="">Sin especificar</option>
          {provincias.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      </div>
    </>
  )
}

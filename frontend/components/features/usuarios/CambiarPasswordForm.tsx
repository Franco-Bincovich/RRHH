"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Loader2 } from "lucide-react"
import { toast } from "sonner"

import { AvisoError } from "@/components/ui/AvisoError"
import { Button } from "@/components/ui/button"
import { FormErrores } from "@/components/ui/FormErrores"
import { PasswordField } from "@/components/features/usuarios/_fields"
import { EMPTY, validarCambio, type FormData, type FormErrors } from "@/components/features/usuarios/_cambiarPassword"
import { cambiarPassword } from "@/services/usuarios"
import { getSession, saveSession, ApiError } from "@/services/api"

/**
 * Form de cambio de contraseña. `forced` = primer login (sin volver, redirige al éxito).
 *
 * 🔴 LLEVA EL BANNER DE RESUMEN Y `/login` NO, y la diferencia no es de criterio sino de forma.
 * Acá las reglas están ENCADENADAS: `confirmar` se compara contra `nueva`, así que arreglar la
 * nueva contraseña puede romper la confirmación que estaba bien, y el mensaje de `nueva` cambia
 * según cuál de las dos reglas falle. Corregir un campo puede dejar la misma cantidad de errores
 * que antes, y la cuenta del banner es lo único que dice si se está convergiendo. En `/login` hay
 * dos campos independientes, los dos siempre a la vista: ahí el banner repetiría en una línea lo
 * que ya se lee en rojo dos renglones más abajo.
 *
 * El banner va ARRIBA del primer campo, que es donde lo pone el resto del repo (`AreaModal`,
 * `AusenciaModal`, `ClienteModal`) y donde el lector de pantalla lo encuentra al recorrer el form.
 */
export function CambiarPasswordForm({ forced }: { forced: boolean }) {
  const router = useRouter()
  const [form, setForm] = useState<FormData>(EMPTY)
  const [errors, setErrors] = useState<FormErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState("")

  function field(key: keyof FormData) {
    return (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.value
      setForm((p) => ({ ...p, [key]: val }))
      if (errors[key]) setErrors((p) => ({ ...p, [key]: undefined }))
      if (serverError) setServerError("")
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errs = validarCambio(form)
    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      return
    }
    setSubmitting(true)
    setServerError("")
    try {
      await cambiarPassword(form.actual, form.nueva)
      toast.success("Contraseña actualizada")
      const s = getSession()
      if (s) saveSession({ ...s, user: { ...s.user, must_change_password: false } })
      if (forced) {
        router.replace("/dashboard")
      } else {
        setForm(EMPTY)
      }
    } catch (err) {
      setServerError(
        err instanceof ApiError
          ? err.message
          : "Error de conexión. Verificá tu red e intentá de nuevo.",
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      <FormErrores cantidad={Object.values(errors).filter(Boolean).length} />

      <PasswordField
        id="actual" label="Contraseña actual" value={form.actual} onChange={field("actual")}
        error={errors.actual} autoComplete="current-password" disabled={submitting}
      />
      <PasswordField
        id="nueva" label="Nueva contraseña" value={form.nueva} onChange={field("nueva")}
        error={errors.nueva} autoComplete="new-password" disabled={submitting}
      />
      <PasswordField
        id="confirmar" label="Confirmar nueva contraseña" value={form.confirmar} onChange={field("confirmar")}
        error={errors.confirmar} autoComplete="new-password" disabled={submitting}
      />

      {serverError && <AvisoError>{serverError}</AvisoError>}

      <div className="flex gap-3">
        <Button type="submit" className="min-h-[2.75rem] flex-1" disabled={submitting}>
          {submitting ? (
            <><Loader2 className="mr-2 size-4 animate-spin" aria-hidden />Cambiando…</>
          ) : (
            "Cambiar contraseña"
          )}
        </Button>
      </div>
    </form>
  )
}

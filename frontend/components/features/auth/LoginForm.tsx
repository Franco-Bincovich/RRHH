"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Loader2 } from "lucide-react"

import { FieldError } from "@/components/ui/FieldError"
import { AvisoError } from "@/components/ui/AvisoError"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { PasswordField } from "@/components/features/usuarios/_fields"
import { login } from "@/services/auth"
import { saveSession, ApiError } from "@/services/api"

import { validarLogin, type ErroresLogin, type FormLogin } from "./_loginForm"

const VACIO: FormLogin = { username: "", password: "" }

/**
 * El formulario de ingreso.
 *
 * 🔴 NO LLEVA EL BANNER DE RESUMEN (`FormErrores`), Y ES UNA DECISIÓN, NO UN OLVIDO. La validación
 * en dos niveles de §3 existe porque en un formulario largo el borde rojo puede quedar abajo del
 * scroll: se aprieta Guardar, no pasa nada visible, y la lectura razonable es que el sistema está
 * roto. Acá hay **dos campos y los dos están siempre a la vista, también en un teléfono**: el
 * banner diría "Revisá 2 campos" arriba de dos mensajes rojos que ya se leen. El segundo nivel
 * —el mensaje por campo, que dice qué corregir— sí está.
 *
 * 🔴 EL ERROR DEL SERVIDOR NO REEMPLAZA EL FORMULARIO. Va en un `AvisoError` adentro del form, con
 * lo que la persona escribió intacto. Un `ErrorState` acá —que es lo que la pantalla usaría si el
 * error fuera de carga— borraría el usuario ya tipeado ante una contraseña equivocada.
 *
 * El campo de contraseña es `PasswordField`, el mismo del cambio de contraseña: esta pantalla
 * tenía su propia copia del input, del ojo y del `aria-label` de mostrar/ocultar.
 */
export function LoginForm() {
  const router = useRouter()
  const [form, setForm] = useState<FormLogin>(VACIO)
  const [errores, setErrores] = useState<ErroresLogin>({})
  const [enviando, setEnviando] = useState(false)
  const [errorServidor, setErrorServidor] = useState("")

  function campo(key: keyof FormLogin) {
    return (e: React.ChangeEvent<HTMLInputElement>) => {
      const valor = e.target.value
      setForm((prev) => ({ ...prev, [key]: valor }))
      if (errores[key]) setErrores((prev) => ({ ...prev, [key]: undefined }))
      if (errorServidor) setErrorServidor("")
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errs = validarLogin(form)
    if (Object.keys(errs).length > 0) {
      setErrores(errs)
      return
    }
    setEnviando(true)
    setErrorServidor("")
    try {
      saveSession(await login(form.username.trim(), form.password))
      router.replace("/dashboard")
    } catch (err) {
      setErrorServidor(
        err instanceof ApiError
          ? err.message
          : "Error de conexión. Verificá tu red e intentá de nuevo.",
      )
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      <div className="space-y-1.5">
        <Label htmlFor="username">Usuario</Label>
        <Input
          id="username"
          type="text"
          autoComplete="username"
          placeholder="tu.usuario"
          value={form.username}
          onChange={campo("username")}
          disabled={enviando}
          aria-invalid={Boolean(errores.username)}
          aria-describedby={errores.username ? "username-error" : undefined}
          className="min-h-[2.75rem]"
        />
        <FieldError id="username-error">{errores.username}</FieldError>
      </div>

      <PasswordField
        id="password"
        label="Contraseña"
        value={form.password}
        onChange={campo("password")}
        error={errores.password}
        autoComplete="current-password"
        disabled={enviando}
        placeholder="••••••••"
      />

      {errorServidor && <AvisoError>{errorServidor}</AvisoError>}

      <Button type="submit" className="min-h-[2.75rem] w-full" disabled={enviando}>
        {enviando ? (
          <>
            <Loader2 className="mr-2 size-4 animate-spin" aria-hidden />
            Ingresando…
          </>
        ) : (
          "Ingresar"
        )}
      </Button>
    </form>
  )
}

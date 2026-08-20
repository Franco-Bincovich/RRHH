"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Building2, Eye, EyeOff, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { login } from "@/services/auth"
import { getSession, saveSession, ApiError } from "@/services/api"

// ─── Types ────────────────────────────────────────────────────────────────────

interface FormState {
  username: string
  password: string
}

interface FormErrors {
  username?: string
  password?: string
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function validate(form: FormState): FormErrors {
  const errors: FormErrors = {}
  if (!form.username.trim()) errors.username = "El usuario es requerido"
  if (!form.password) errors.password = "La contraseña es requerida"
  return errors
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function LoginPage() {
  const router = useRouter()

  const [form, setForm] = useState<FormState>({ username: "", password: "" })
  const [errors, setErrors] = useState<FormErrors>({})
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [serverError, setServerError] = useState("")

  // Si ya hay sesión al montar, saltar el login. getSession lee de localStorage,
  // así que el chequeo va en useEffect (no existe en SSR).
  useEffect(() => {
    if (getSession()) router.replace("/dashboard")
  }, [router])

  function handleChange(field: keyof FormState) {
    return (e: React.ChangeEvent<HTMLInputElement>) => {
      setForm((prev) => ({ ...prev, [field]: e.target.value }))
      if (errors[field]) setErrors((prev) => ({ ...prev, [field]: undefined }))
      if (serverError) setServerError("")
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    const fieldErrors = validate(form)
    if (Object.keys(fieldErrors).length > 0) {
      setErrors(fieldErrors)
      return
    }

    setLoading(true)
    setServerError("")

    try {
      const session = await login(form.username.trim(), form.password)
      saveSession(session)
      router.replace("/dashboard")
    } catch (err) {
      if (err instanceof ApiError) {
        setServerError(err.message)
      } else {
        setServerError("Error de conexión. Verificá tu red e intentá de nuevo.")
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-sm">

        {/* Logo */}
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary shadow-lg">
            <Building2 className="size-7 text-primary-foreground" />
          </div>
          <div className="text-center">
            <h1 className="text-xl font-bold tracking-tight text-foreground">HR Karstec</h1>
            <p className="mt-1 text-sm text-muted-foreground">Ingresá a tu cuenta</p>
          </div>
        </div>

        {/* Card */}
        <div className="rounded-2xl border bg-card p-6 shadow-sm">
          <form onSubmit={handleSubmit} noValidate className="space-y-5">

            {/* Usuario */}
            <div className="space-y-1.5">
              <Label htmlFor="username">Usuario</Label>
              <Input
                id="username"
                type="text"
                autoComplete="username"
                placeholder="tu.usuario"
                value={form.username}
                onChange={handleChange("username")}
                disabled={loading}
                aria-invalid={Boolean(errors.username)}
                aria-describedby={errors.username ? "username-error" : undefined}
                className="min-h-[2.75rem]"
              />
              {errors.username && (
                <p id="username-error" className="text-xs text-destructive" role="alert">
                  {errors.username}
                </p>
              )}
            </div>

            {/* Contraseña */}
            <div className="space-y-1.5">
              <Label htmlFor="password">Contraseña</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={form.password}
                  onChange={handleChange("password")}
                  disabled={loading}
                  aria-invalid={Boolean(errors.password)}
                  aria-describedby={errors.password ? "password-error" : undefined}
                  className="min-h-[2.75rem] pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  disabled={loading}
                  aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground disabled:pointer-events-none"
                  tabIndex={-1}
                >
                  {showPassword
                    ? <EyeOff className="size-4" aria-hidden />
                    : <Eye className="size-4" aria-hidden />
                  }
                </button>
              </div>
              {errors.password && (
                <p id="password-error" className="text-xs text-destructive" role="alert">
                  {errors.password}
                </p>
              )}
            </div>

            {/* Error de servidor */}
            {serverError && (
              <div
                role="alert"
                className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-sm text-destructive"
              >
                {serverError}
              </div>
            )}

            {/* Submit */}
            <Button
              type="submit"
              className="w-full min-h-[2.75rem]"
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 size-4 animate-spin" aria-hidden />
                  Ingresando…
                </>
              ) : (
                "Ingresar"
              )}
            </Button>

          </form>
        </div>

        {/* Footer */}
        <p className="mt-6 text-center text-xs text-muted-foreground">
          ¿Problemas para ingresar? Contactá a Capital Humano.
        </p>

      </div>
    </div>
  )
}

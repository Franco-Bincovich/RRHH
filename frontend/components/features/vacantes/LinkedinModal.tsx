"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ApiError } from "@/services/api"
import { publicarLinkedin } from "@/services/vacantes"
import { avisarHecho } from "@/components/features/shared/avisoGuardado"

/**
 * Publicar la vacante en LinkedIn vía Zernio, pidiendo el email de contacto del aviso.
 *
 * Vivía adentro de `app/(dashboard)/vacantes/[id]/page.tsx` (452 líneas, el archivo más grande del
 * front). Se sacó al cortar esa página; el componente no cambió.
 *
 * 🔴 "ZERNIO NO ESTÁ CONFIGURADO" NO ES UN ERROR MÁS, y por eso tiene su propia rama: es el único
 * caso en el que el usuario puede resolverlo solo, y el aviso lleva el link a Configuración en vez
 * de un texto rojo que no dice qué hacer. Cuando aparece, el botón de publicar se esconde: dejarlo
 * invitaría a reintentar algo que va a fallar igual hasta cargar la API key.
 */
export function LinkedinModal({ open, vacanteId, defaultEmail, onClose, onSuccess }: {
  open: boolean
  vacanteId: string
  defaultEmail: string
  onClose: () => void
  onSuccess: () => void
}) {
  const router = useRouter()
  const [email, setEmail] = useState(defaultEmail)
  const [loading, setLoading] = useState(false)
  const [notConfigured, setNotConfigured] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setEmail(defaultEmail)
      setNotConfigured(false)
      setError(null)
    }
  }, [open, defaultEmail])

  const handlePublicar = async () => {
    if (!email.trim()) return
    setLoading(true)
    setNotConfigured(false)
    setError(null)
    try {
      await publicarLinkedin(vacanteId, { email_contacto: email.trim() })
      avisarHecho("Búsqueda publicada en LinkedIn")
      onSuccess()
      onClose()
    } catch (err) {
      if (err instanceof ApiError && err.code === "ZERNIO_NOT_CONFIGURED") {
        setNotConfigured(true)
      } else {
        setError(err instanceof Error ? err.message : "Error al publicar")
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Publicar en LinkedIn</DialogTitle>
          <DialogDescription>
            Se publicará la vacante en LinkedIn via Zernio con el email de contacto indicado.
          </DialogDescription>
        </DialogHeader>

        {notConfigured ? (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200">
            Zernio no está configurado.{" "}
            <button
              className="font-medium underline underline-offset-2"
              onClick={() => router.push("/configuracion")}
            >
              Ir a Configuración
            </button>{" "}
            para agregar tu API key.
          </div>
        ) : (
          <div className="space-y-3">
            <div>
              <Label htmlFor="linkedin-email" className="mb-1.5 block text-sm">
                Email de contacto
              </Label>
              <Input
                id="linkedin-email"
                type="email"
                placeholder="rrhh@empresa.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Cancelar
          </Button>
          {!notConfigured && (
            <Button onClick={handlePublicar} disabled={loading || !email.trim()}>
              {loading ? "Publicando…" : "Publicar"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

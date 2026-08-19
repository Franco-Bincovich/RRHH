"use client"

import { useState } from "react"
import { toast } from "sonner"
import { Megaphone } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select } from "@/components/ui/select"
import { updateVacante } from "@/services/vacantes"
import type { Vacante } from "@/types/vacantes"

interface PublicacionSectionProps {
  vacante: Vacante
  canWrite: boolean
  onSaved: (v: Vacante) => void
}

/** Datos de publicación de la vacante (copy, hashtags, contacto). Edición inline. */
export function PublicacionSection({ vacante, canWrite, onSaved }: PublicacionSectionProps) {
  const [copy, setCopy] = useState(vacante.copy_publicacion ?? "")
  const [hashtags, setHashtags] = useState(vacante.hashtags ?? "")
  const [email, setEmail] = useState(vacante.email_contacto ?? "")
  const [ubicacion, setUbicacion] = useState(vacante.ubicacion ?? "")
  const [modalidad, setModalidad] = useState(vacante.modalidad ?? "")
  const [jornada, setJornada] = useState(vacante.jornada ?? "")
  const [saving, setSaving] = useState(false)

  const handleGuardar = async () => {
    setSaving(true)
    try {
      const updated = await updateVacante(vacante.id, {
        copy_publicacion: copy.trim() || null,
        hashtags: hashtags.trim() || null,
        email_contacto: email.trim() || null,
        ubicacion: ubicacion.trim() || null,
        modalidad: modalidad || null,
        jornada: jornada.trim() || null,
      })
      onSaved(updated)
      toast.success("Publicación guardada")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "No se pudo guardar la publicación.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card as="section" className="mb-8">
      <div className="mb-4 flex items-center gap-2">
        <Megaphone className="size-4 text-muted-foreground" />
        <h2 className="text-base font-semibold text-foreground">Publicación</h2>
      </div>

      <div className="space-y-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="copy_publicacion">Copy del post</Label>
          <Textarea
            id="copy_publicacion"
            rows={4}
            placeholder="Texto de la publicación para redes…"
            value={copy}
            disabled={!canWrite}
            onChange={(e) => setCopy(e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="hashtags">Hashtags</Label>
          <Input
            id="hashtags"
            placeholder="#BúsquedaLaboral #MarDelPlata"
            value={hashtags}
            disabled={!canWrite}
            onChange={(e) => setHashtags(e.target.value)}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="email_contacto">Email de contacto</Label>
            <Input
              id="email_contacto"
              type="email"
              placeholder="rrhh@empresa.com"
              value={email}
              disabled={!canWrite}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ubicacion">Ubicación</Label>
            <Input
              id="ubicacion"
              placeholder="Mar del Plata"
              value={ubicacion}
              disabled={!canWrite}
              onChange={(e) => setUbicacion(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="modalidad">Modalidad</Label>
            <Select
              id="modalidad"
              value={modalidad}
              disabled={!canWrite}
              onChange={(e) => setModalidad(e.target.value)}
            >
              <option value="">Sin especificar</option>
              <option value="presencial">Presencial</option>
              <option value="remoto">Remoto</option>
              <option value="hibrido">Híbrido</option>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="jornada">Jornada</Label>
            <Input
              id="jornada"
              placeholder="Part time 6hs"
              value={jornada}
              disabled={!canWrite}
              onChange={(e) => setJornada(e.target.value)}
            />
          </div>
        </div>

        {canWrite && (
          <div className="flex justify-end">
            <Button className="min-h-10" onClick={handleGuardar} disabled={saving}>
              {saving ? "Guardando…" : "Guardar"}
            </Button>
          </div>
        )}
      </div>
    </Card>
  )
}

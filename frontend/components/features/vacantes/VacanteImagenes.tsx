"use client"

import { useCallback, useEffect, useState } from "react"
import { ConfirmDialog } from "@/components/ui/ConfirmDialog"
import { confirmarEliminarImagen } from "@/components/features/shared/confirmaciones"
import { useConfirmacion } from "@/components/features/shared/useConfirmacion"
import { toast } from "sonner"
import { ImageIcon } from "lucide-react"

import { Skeleton } from "@/components/ui/skeleton"
import { Card } from "@/components/ui/card"
import { FileUpload } from "@/components/features/adjuntos/FileUpload"
import { ImagenCard } from "@/components/features/vacantes/ImagenCard"
import { useCanWrite } from "@/hooks/useCanWrite"
import {
  eliminarAdjunto,
  fetchAdjuntos,
  getAdjuntoUrl,
  marcarAdjuntoPrincipal,
  subirAdjunto,
} from "@/services/adjuntos"
import type { Adjunto } from "@/types/adjunto"

const ENTIDAD = "vacante"
const ACCEPT = ".jpg,.jpeg,.png,.webp"

/** Sección de imágenes de una vacante: subir + preview + marcar principal + borrar.
 * Reusa el sistema de adjuntos (entidad="vacante"). La principal es la placa de LinkedIn. */
export function VacanteImagenes({ vacanteId }: { vacanteId: string }) {
  const [imagenes, setImagenes] = useState<Adjunto[]>([])
  const aEliminar = useConfirmacion<Adjunto>()
  const [urls, setUrls] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)
  const canWrite = useCanWrite()

  const recargar = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const res = await fetchAdjuntos(ENTIDAD, vacanteId)
      const soloImagenes = res.items.filter((a) => (a.mime_type ?? "").startsWith("image/"))
      setImagenes(soloImagenes)
      const pares = await Promise.all(
        soloImagenes.map(async (a) => [a.id, await getAdjuntoUrl(a.id).catch(() => "")] as const),
      )
      setUrls(Object.fromEntries(pares.filter(([, u]) => u)))
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [vacanteId])

  useEffect(() => {
    if (vacanteId) void recargar()
  }, [vacanteId, recargar])

  async function handleUpload(file: File) {
    await subirAdjunto(ENTIDAD, vacanteId, file)
    toast.success("Imagen subida")
    await recargar()
  }

  async function handlePrincipal(id: string) {
    setBusyId(id)
    try {
      await marcarAdjuntoPrincipal(id)
      toast.success("Imagen principal actualizada")
      await recargar()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "No se pudo marcar como principal.")
    } finally {
      setBusyId(null)
    }
  }

  async function handleEliminar(a: Adjunto) {
    setBusyId(a.id)
    try {
      await eliminarAdjunto(a.id)
      toast.success("Imagen eliminada")
      await recargar()
    } catch {
      toast.error("No se pudo eliminar la imagen.")
    } finally {
      setBusyId(null)
    }
  }

  return (
    <Card as="section" className="mb-8">
      <div className="mb-1 flex items-center gap-2">
        <ImageIcon className="size-4 text-muted-foreground" />
        <h2 className="text-base font-semibold text-foreground">Imágenes</h2>
      </div>
      <p className="mb-4 text-xs text-muted-foreground">
        La imagen marcada como principal es la placa que se usará al publicar en LinkedIn.
      </p>

      <div className="space-y-4">
        {canWrite && <FileUpload onUpload={handleUpload} accept={ACCEPT} label="Subir imagen" />}

        {loading ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Skeleton className="aspect-video rounded-xl" />
            <Skeleton className="aspect-video rounded-xl" />
          </div>
        ) : error ? (
          <p className="text-sm text-muted-foreground">No se pudieron cargar las imágenes.</p>
        ) : imagenes.length === 0 ? (
          <p className="text-sm text-muted-foreground">Sin imágenes.</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {imagenes.map((a) => (
              <ImagenCard
                key={a.id}
                adjunto={a}
                url={urls[a.id] ?? null}
                canWrite={canWrite}
                busy={busyId === a.id}
                onMarcarPrincipal={() => handlePrincipal(a.id)}
                onEliminar={() => aEliminar.pedir(a)}
              />
            ))}
          </div>
        )}
      </div>

      <ConfirmDialog
        open={aEliminar.abierto}
        onClose={aEliminar.cerrar}
        onConfirm={() => {
          const x = aEliminar.pendiente
          aEliminar.cerrar()
          if (x) void handleEliminar(x)
        }}
        loading={busyId !== null}
        {...confirmarEliminarImagen(aEliminar.pendiente ?? {})}
      />
    </Card>
  )
}

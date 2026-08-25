"use client"

import { useCallback, useEffect, useState } from "react"
import { ConfirmDialog } from "@/components/ui/ConfirmDialog"
import { confirmarEliminarAdjunto } from "@/components/features/shared/confirmaciones"
import { useConfirmacion } from "@/components/features/shared/useConfirmacion"
import { avisarHecho } from "@/components/features/shared/avisoGuardado"
import { ApiError } from "@/services/api"
import { toast } from "sonner"
import { Download, Trash2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Section } from "@/components/features/empleados/ficha/_primitives"
import { FileUpload } from "@/components/features/adjuntos/FileUpload"
import { useCanWrite } from "@/hooks/useCanWrite"
import { eliminarAdjunto, fetchAdjuntos, getAdjuntoUrl, subirAdjunto } from "@/services/adjuntos"
import type { Adjunto } from "@/types/adjunto"

/** Tamaño de archivo legible: bytes → KB o MB. */
function tamanoLegible(bytes: number | null): string {
  if (!bytes) return "—"
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

interface Props {
  entidad: string
  entidadId: string
  titulo?: string
}

/**
 * Sección autoabastecida de documentos adjuntos de una entidad (empleado, vacacion, …).
 * Hace su propio fetch y maneja subir/listar/descargar/eliminar. Reusable en cualquier
 * ficha: recibe entidad + entidadId. La escritura se oculta según el permiso de la ruta.
 */
export function AdjuntosSection({ entidad, entidadId, titulo = "Documentos" }: Props) {
  const [adjuntos, setAdjuntos] = useState<Adjunto[]>([])
  const aEliminar = useConfirmacion<Adjunto>()
  const [borrandoId, setBorrandoId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const canWrite = useCanWrite()

  const recargar = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const res = await fetchAdjuntos(entidad, entidadId)
      setAdjuntos(res.items)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [entidad, entidadId])

  useEffect(() => {
    if (entidadId) void recargar()
  }, [entidadId, recargar])

  async function handleUpload(file: File) {
    await subirAdjunto(entidad, entidadId, file)
    toast.success("Documento subido")
    await recargar()
  }

  async function handleDescargar(a: Adjunto) {
    try {
      const url = await getAdjuntoUrl(a.id)
      window.open(url, "_blank", "noopener,noreferrer")
    } catch {
      toast.error("No se pudo abrir el documento")
    }
  }

  async function handleEliminar(a: Adjunto) {
    setBorrandoId(a.id)
    try {
      await eliminarAdjunto(a.id)
      avisarHecho("Documento eliminado")
      await recargar()
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "No se pudo eliminar el documento.")
    } finally {
      setBorrandoId(null)
    }
  }

  return (
    <Section title={titulo}>
      <div className="col-span-full space-y-3">
        {canWrite && <FileUpload onUpload={handleUpload} label="Subir documento" />}

        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : error ? (
          <p className="text-sm text-muted-foreground">No se pudieron cargar los documentos.</p>
        ) : adjuntos.length === 0 ? (
          <p className="text-sm text-muted-foreground">Sin documentos.</p>
        ) : (
          <ul className="divide-y rounded-lg border">
            {adjuntos.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 p-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-foreground">{a.nombre_archivo}</p>
                  <p className="text-xs text-muted-foreground">
                    {a.categoria ? `${a.categoria} · ` : ""}
                    {tamanoLegible(a.tamano_bytes)} · {a.created_at.slice(0, 10)}
                  </p>
                </div>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" className="min-h-11 gap-1.5" onClick={() => handleDescargar(a)}>
                    <Download className="size-4" /> Descargar
                  </Button>
                  {canWrite && (
                    <Button
                      variant="ghost"
                      className="min-h-11 gap-1.5 text-destructive hover:text-destructive"
                      onClick={() => aEliminar.pedir(a)}
                      aria-label={`Eliminar ${a.nombre_archivo}`}
                    >
                      <Trash2 className="size-4" /> Eliminar
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ul>
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
        loading={borrandoId !== null}
        {...confirmarEliminarAdjunto(aEliminar.pendiente ?? {})}
      />
    </Section>
  )
}

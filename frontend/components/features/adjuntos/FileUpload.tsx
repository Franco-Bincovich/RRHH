"use client"

import { useRef, useState } from "react"
import { Upload } from "lucide-react"

import { Button } from "@/components/ui/button"
import { MAX_SUBIDA_MB } from "@/lib/limitesSubida"

const DEFAULT_ACCEPT = ".pdf,.docx,.xlsx,.jpg,.jpeg,.png,.webp"

interface Props {
  /** Envía el archivo elegido. El componente maneja el estado subiendo/error alrededor. */
  onUpload: (file: File) => Promise<void>
  accept?: string
  /** Default: el límite compartido (ver lib/limitesSubida). Solo pasarlo para bajarlo. */
  maxSizeMB?: number
  label?: string
  disabled?: boolean
}

/**
 * Botón de subida de archivos reutilizable: input oculto + trigger visible.
 * Valida tamaño y tipo en el cliente (feedback inmediato antes de subir), muestra
 * "Subiendo..." mientras corre onUpload y un error claro si algo falla. Resetea el
 * input tras cada intento para poder volver a elegir el mismo archivo.
 */
export function FileUpload({
  onUpload,
  accept = DEFAULT_ACCEPT,
  maxSizeMB = MAX_SUBIDA_MB,
  label = "Subir archivo",
  disabled = false,
}: Props) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  function validar(file: File): string | null {
    if (file.size > maxSizeMB * 1024 * 1024) {
      return `El archivo supera el tamaño máximo de ${maxSizeMB} MB`
    }
    const exts = accept
      .split(",")
      .map((t) => t.trim().toLowerCase())
      .filter((t) => t.startsWith("."))
    if (exts.length && !exts.some((ext) => file.name.toLowerCase().endsWith(ext))) {
      return "Tipo de archivo no permitido"
    }
    return null
  }

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const invalido = validar(file)
    if (invalido) {
      setError(invalido)
      if (inputRef.current) inputRef.current.value = ""
      return
    }
    setUploading(true)
    setError("")
    try {
      await onUpload(file)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "No se pudo subir el archivo")
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ""
    }
  }

  return (
    <div className="flex flex-col gap-1">
      <Button
        type="button"
        variant="outline"
        className="min-h-11 w-fit gap-2"
        disabled={disabled || uploading}
        onClick={() => inputRef.current?.click()}
      >
        <Upload className="size-4" />
        {uploading ? "Subiendo..." : label}
      </Button>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={handleFile}
        disabled={disabled || uploading}
      />
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}

"use client"

import { useRef } from "react"
import { Paperclip, X } from "lucide-react"

import { Label } from "@/components/ui/label"
import { MAX_SUBIDA_MB, mensajeSuperaTamano } from "@/lib/limitesSubida"

const ACCEPT = ".pdf,.doc,.docx"
const EXTS = ["pdf", "doc", "docx"]

/** Valida tipo y tamaño del CV en el cliente. Devuelve mensaje de error o null si es válido. */
function validarCv(file: File): string | null {
  const ext = file.name.split(".").pop()?.toLowerCase() ?? ""
  if (!EXTS.includes(ext)) return "Formato no permitido. Usá PDF o Word (.pdf, .doc, .docx)."
  if (file.size > MAX_SUBIDA_MB * 1024 * 1024) return `${mensajeSuperaTamano("CV")}.`
  return null
}

interface Props {
  file: File | null
  error: string
  onChange: (file: File | null, error: string) => void
}

/** Campo de archivo OPCIONAL para el CV: valida en cliente, muestra el nombre y permite quitarlo. */
export function CvField({ file, error, onChange }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)

  function handle(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null
    if (!f) return onChange(null, "")
    const err = validarCv(f)
    onChange(err ? null : f, err ?? "")
    if (err && inputRef.current) inputRef.current.value = ""
  }

  function quitar() {
    onChange(null, "")
    if (inputRef.current) inputRef.current.value = ""
  }

  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor="cv">CV (opcional)</Label>
      {file ? (
        <div className="flex items-center justify-between gap-2 rounded-lg border bg-muted/40 px-3 py-2">
          <span className="flex min-w-0 items-center gap-2 text-sm text-foreground">
            <Paperclip className="size-4 shrink-0" />
            <span className="truncate">{file.name}</span>
          </span>
          <button
            type="button"
            onClick={quitar}
            aria-label="Quitar CV"
            className="shrink-0 text-muted-foreground hover:text-destructive"
          >
            <X className="size-4" />
          </button>
        </div>
      ) : (
        <input
          ref={inputRef}
          id="cv"
          type="file"
          accept={ACCEPT}
          onChange={handle}
          className="block w-full text-sm text-muted-foreground file:mr-3 file:rounded-md file:border-0 file:bg-muted file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-muted/70"
        />
      )}
      {error && <p className="text-xs text-destructive" role="alert">{error}</p>}
      {!error && <p className="text-xs text-muted-foreground">PDF o Word, hasta {MAX_SUBIDA_MB} MB.</p>}
    </div>
  )
}

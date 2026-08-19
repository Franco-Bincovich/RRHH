"use client"

import { useState } from "react"
import { Loader2, Upload } from "lucide-react"

import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { NominaResultView } from "@/components/features/empleados/NominaResultView"
import { importarNominaEmpleados } from "@/services/importacion"
import type { ImportacionNominaEmpleadosResult } from "@/types/importacion"

const COLUMNAS_27 =
  "Apellido; Nombre; DNI; CUIT; Sexo; Edad; Email; Fecha Nacimiento; Fecha Ingreso; " +
  "Fecha Ingreso Reconocida; Organismo; Gerencia; Sector; Equipo; Rol; Seniority; Categoria; " +
  "Modalidad Contratacion; Co-sourcing; Apellido Superior; Nombre Superior; Liderazgo; " +
  "Ubicación Física; Carga Horaria; Product Owner; Fecha Baja; Motivo Baja"

export interface ImportarNominaModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

export function ImportarNominaModal({ open, onClose, onSuccess }: ImportarNominaModalProps) {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [result, setResult] = useState<ImportacionNominaEmpleadosResult | null>(null)
  // 🔴 Se disparó un import, sin importar cómo terminó. NO es lo mismo que tener `result`:
  // si el request muere por timeout o corte de red, la respuesta no llega pero el backend YA
  // escribió N empleados. Refrescar solo con `result` dejaba a RRHH cerrando el modal con la
  // lista vieja, creyendo que no se cargó nada mientras la base tenía 73 empleados nuevos.
  // Ante la duda se refresca: mostrar datos frescos nunca es peor que mostrarlos viejos.
  const [intentado, setIntentado] = useState(false)

  // Al cerrar tras un intento de import, refresca la lista de empleados.
  function resetAndClose() {
    if (loading) return
    if (intentado) onSuccess()
    setFile(null); setError(""); setResult(null); setIntentado(false); onClose()
  }

  function importarOtro() {
    setFile(null); setError(""); setResult(null)   // `intentado` NO se limpia: ya se tocó la base
  }

  async function run() {
    if (!file) return
    setLoading(true); setError(""); setIntentado(true)
    try {
      setResult(await importarNominaEmpleados(file))
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al importar la nómina.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) resetAndClose() }}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>{result ? "Resultado de la importación" : "Importar nómina de empleados"}</DialogTitle>
        </DialogHeader>

        {!result ? (
          <div className="space-y-4 py-2">
            <label
              className="flex min-h-40 cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-border p-6 transition-colors hover:border-primary/50 hover:bg-muted/30"
            >
              <Upload className="size-8 text-muted-foreground" />
              {file ? (
                <div className="text-center">
                  <p className="font-medium text-foreground">{file.name}</p>
                  <p className="text-sm text-muted-foreground">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
              ) : (
                <div className="text-center">
                  <p className="font-medium text-foreground">Elegí el archivo CSV de nómina</p>
                  <p className="text-sm text-muted-foreground">27 columnas, separado por «;», codificación latin1</p>
                </div>
              )}
              <input
                type="file"
                accept=".csv"
                className="hidden"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) { setFile(f); setError("") } e.target.value = "" }}
              />
            </label>

            <div className="rounded-lg border bg-muted/30 p-3 text-xs">
              <p className="mb-1.5 font-medium text-foreground">Se crean empleados, empresas (Organismo) y áreas (Sector) desde el archivo.</p>
              <p className="font-mono leading-relaxed text-muted-foreground">{COLUMNAS_27}</p>
            </div>
          </div>
        ) : (
          <NominaResultView result={result} />
        )}

        {error && <p className="text-sm text-destructive" role="alert">{error}</p>}

        <DialogFooter>
          {!result ? (
            <>
              <Button type="button" variant="outline" className="min-h-11" onClick={resetAndClose} disabled={loading}>
                Cancelar
              </Button>
              <Button type="button" className="min-h-11" disabled={!file || loading} onClick={run}>
                {loading ? <><Loader2 className="size-4 animate-spin" />Importando...</> : "Importar"}
              </Button>
            </>
          ) : (
            <>
              <Button type="button" variant="outline" className="min-h-11" onClick={importarOtro}>Importar otro</Button>
              <Button type="button" className="min-h-11" onClick={resetAndClose}>Listo</Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

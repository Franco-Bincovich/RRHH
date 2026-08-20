"use client"

import { useState, useEffect } from "react"
import { AlertTriangle, CheckCircle2, Download, Loader2, Upload, XCircle } from "lucide-react"

import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Select } from "@/components/ui/select"
import { confirmarImportacionNomina, previewImportacionNominaCSV } from "@/services/importacion"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { ImportacionNominaPreview } from "@/types/importacion"
import type { Empresa } from "@/types/empresa"

// ─── Helpers ──────────────────────────────────────────────────────────────────

const MESES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]

function pesos(n: number): string {
  return `$${Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".")}`
}

// ─── Template CSV ─────────────────────────────────────────────────────────────

const TEMPLATE_ROWS = [
  "dni,anio,mes,salario_bruto,neto",
  "12345678,2024,5,850000,680000",
].join("\n")

function downloadTemplate() {
  const blob = new Blob([TEMPLATE_ROWS], { type: "text/csv;charset=utf-8;" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = "template_nomina.csv"
  a.click()
  URL.revokeObjectURL(url)
}

// ─── Types ────────────────────────────────────────────────────────────────────

type Step = "upload" | "preview" | "confirm"

export interface ImportarNominaCSVModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ImportarNominaCSVModal({ open, onClose, onSuccess }: ImportarNominaCSVModalProps) {
  const [step, setStep] = useState<Step>("upload")
  const [dragging, setDragging] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState("")
  const [preview, setPreview] = useState<ImportacionNominaPreview | null>(null)

  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [empresaId, setEmpresaId] = useState("")
  const [empresaLoading, setEmpresaLoading] = useState(false)

  useEffect(() => {
    if (!open) return
    setEmpresaLoading(true)
    fetchEmpresas()
      .then((res) => {
        const activas = res.items.filter((e) => e.activa)
        setEmpresas(activas)
        const activeId = getEmpresaActivaId()
        if (activeId && activas.some((e) => e.id === activeId)) {
          setEmpresaId(activeId)
        } else if (activas.length === 1) {
          setEmpresaId(activas[0].id)
        }
      })
      .catch(() => {})
      .finally(() => setEmpresaLoading(false))
  }, [open])

  function resetAndClose() {
    if (loading || confirming) return
    setStep("upload")
    setFile(null)
    setPreview(null)
    setError("")
    onClose()
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped?.name.toLowerCase().endsWith(".csv")) {
      setFile(dropped)
      setError("")
    } else {
      setError("Solo se aceptan archivos .csv")
    }
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0]
    if (selected) { setFile(selected); setError("") }
    e.target.value = ""
  }

  async function handlePreview() {
    if (!file || !empresaId) return
    setLoading(true)
    setError("")
    try {
      const result = await previewImportacionNominaCSV(file, empresaId)
      setPreview(result)
      setStep("preview")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al procesar el archivo.")
    } finally {
      setLoading(false)
    }
  }

  async function handleConfirm() {
    if (!preview || !empresaId) return
    setConfirming(true)
    setError("")
    try {
      await confirmarImportacionNomina(preview.filas_validas, empresaId)
      onSuccess()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al importar nómina.")
      setConfirming(false)
    }
  }

  const validCount = preview?.filas_validas.length ?? 0
  const errorCount = preview?.errores.length ?? 0
  const updateCount = preview?.filas_validas.filter((f) => f.es_actualizacion).length ?? 0
  const newCount = validCount - updateCount
  const empresaNombre = empresas.find((e) => e.id === empresaId)?.nombre ?? ""

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) resetAndClose() }}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>
            {step === "upload" && "Importar nómina desde CSV"}
            {step === "preview" && "Vista previa — nómina"}
            {step === "confirm" && "Confirmar importación de nómina"}
          </DialogTitle>
        </DialogHeader>

        {/* ── STEP 1: Upload ──────────────────────────────────────────────── */}
        {step === "upload" && (
          <div className="space-y-4 py-2">
            {/* Empresa destino */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-foreground">
                Empresa destino <span className="text-destructive">*</span>
              </label>
              {empresaLoading ? (
                <div className="h-9 animate-pulse rounded-lg bg-muted" />
              ) : (
                <Select
                  value={empresaId}
                  onChange={(e) => setEmpresaId(e.target.value)}
                >
                  <option value="">Seleccioná una empresa...</option>
                  {empresas.map((e) => (
                    <option key={e.id} value={e.id}>{e.nombre}</option>
                  ))}
                </Select>
              )}
              <p className="text-xs text-muted-foreground">
                El DNI de cada fila se busca entre los empleados de esta empresa. El empresa_id en nómina se hereda del empleado encontrado.
              </p>
            </div>

            {/* Dropzone */}
            <div
              role="button"
              tabIndex={0}
              className={[
                "flex min-h-40 cursor-pointer flex-col items-center justify-center gap-3",
                "rounded-xl border-2 border-dashed p-6 transition-colors",
                dragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/50 hover:bg-muted/30",
              ].join(" ")}
              onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              onClick={() => document.getElementById("nomina-csv-input")?.click()}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") document.getElementById("nomina-csv-input")?.click() }}
            >
              <Upload className="size-8 text-muted-foreground" />
              {file ? (
                <div className="text-center">
                  <p className="font-medium text-foreground">{file.name}</p>
                  <p className="text-sm text-muted-foreground">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
              ) : (
                <div className="text-center">
                  <p className="font-medium text-foreground">Arrastrá tu archivo CSV aquí</p>
                  <p className="text-sm text-muted-foreground">o hacé clic para seleccionarlo</p>
                </div>
              )}
              <input id="nomina-csv-input" type="file" accept=".csv" className="hidden" onChange={handleFileInput} />
            </div>

            <Button type="button" variant="outline" size="sm" className="min-h-9 gap-1.5" onClick={downloadTemplate}>
              <Download className="size-4" />
              Descargar template CSV
            </Button>

            <div className="rounded-lg border bg-muted/30 p-3 text-xs">
              <p className="mb-1.5 font-medium text-foreground">Columnas del template:</p>
              <p className="font-mono text-muted-foreground">dni, anio, mes, salario_bruto, neto</p>
              <div className="mt-2 grid grid-cols-1 gap-1 text-muted-foreground sm:grid-cols-2">
                <span><strong>dni:</strong> identifica al colaborador dentro de la empresa</span>
                <span><strong>anio / mes:</strong> período de la nómina (ej. 2024 / 5)</span>
                <span><strong>salario_bruto / neto:</strong> importes numéricos ≥ 0</span>
                <span className="sm:col-span-1"><strong>Si ya existe</strong> nómina para ese colaborador + período, se actualizará.</span>
              </div>
            </div>
          </div>
        )}

        {/* ── STEP 2: Preview ─────────────────────────────────────────────── */}
        {step === "preview" && preview && (
          <div className="space-y-3 py-2">
            <div className="flex flex-wrap gap-4 text-sm">
              {newCount > 0 && (
                <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="size-4" />
                  {newCount} alta{newCount !== 1 ? "s" : ""} nueva{newCount !== 1 ? "s" : ""}
                </span>
              )}
              {updateCount > 0 && (
                <span className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400">
                  <AlertTriangle className="size-4" />
                  {updateCount} actualización{updateCount !== 1 ? "es" : ""} (período ya existe)
                </span>
              )}
              {errorCount > 0 && (
                <span className="flex items-center gap-1.5 text-destructive">
                  <XCircle className="size-4" />
                  {errorCount} error{errorCount !== 1 ? "es" : ""}
                </span>
              )}
            </div>

            {updateCount > 0 && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
                Las filas marcadas con <strong>Actualizará</strong> tienen nómina existente en <strong>{empresaNombre}</strong> para ese empleado y período. Al confirmar, se sobrescribirán los montos.
              </div>
            )}

            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Fila</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Estado</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Colaborador</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">DNI</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Período</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Bruto</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Neto</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Detalle</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.filas_validas.map((fila) => (
                    <tr
                      key={`v-${fila.fila}`}
                      className={["border-b last:border-0", fila.es_actualizacion ? "bg-amber-500/5" : "bg-emerald-500/5"].join(" ")}
                    >
                      <td className="px-3 py-2 text-muted-foreground">{fila.fila}</td>
                      <td className="px-3 py-2">
                        {fila.es_actualizacion ? (
                          <span className="flex items-center gap-1 text-xs font-medium text-amber-600 dark:text-amber-400">
                            <AlertTriangle className="size-3.5" />Actualizará
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                            <CheckCircle2 className="size-3.5" />Alta nueva
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 font-medium">{fila.nombre_empleado}</td>
                      <td className="px-3 py-2 font-mono text-xs text-muted-foreground">{fila.dni}</td>
                      <td className="px-3 py-2 text-muted-foreground">{MESES[fila.mes - 1]} {fila.anio}</td>
                      <td className="px-3 py-2 text-right text-muted-foreground">{pesos(fila.salario_bruto)}</td>
                      <td className="px-3 py-2 text-right text-muted-foreground">{pesos(fila.neto)}</td>
                      <td className="px-3 py-2 text-muted-foreground">—</td>
                    </tr>
                  ))}
                  {preview.errores.map((err, idx) => (
                    <tr key={`e-${err.fila}-${idx}`} className="border-b bg-destructive/5 last:border-0">
                      <td className="px-3 py-2 text-muted-foreground">{err.fila}</td>
                      <td className="px-3 py-2">
                        <span className="flex items-center gap-1 text-xs font-medium text-destructive">
                          <XCircle className="size-3.5" />Error
                        </span>
                      </td>
                      <td className="px-3 py-2 text-muted-foreground" colSpan={5}>—</td>
                      <td className="px-3 py-2 text-xs text-destructive">{err.error}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── STEP 3: Confirm ─────────────────────────────────────────────── */}
        {step === "confirm" && (
          <div className="py-8 text-center">
            <CheckCircle2 className="mx-auto mb-4 size-12 text-emerald-500" />
            <p className="text-lg font-semibold text-foreground">
              {newCount > 0 && `${newCount} alta${newCount !== 1 ? "s" : ""} nueva${newCount !== 1 ? "s" : ""}`}
              {newCount > 0 && updateCount > 0 && " · "}
              {updateCount > 0 && `${updateCount} actualización${updateCount !== 1 ? "es" : ""}`}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">Empresa: <strong>{empresaNombre}</strong></p>
            <p className="mt-1 text-sm text-muted-foreground">
              Los registros existentes (mismo empleado + período) se actualizarán con los montos del CSV.
            </p>
          </div>
        )}

        {error && <p className="text-sm text-destructive" role="alert">{error}</p>}

        <DialogFooter>
          <Button type="button" variant="outline" className="min-h-11" onClick={resetAndClose} disabled={loading || confirming}>
            Cancelar
          </Button>

          {step === "upload" && (
            <Button type="button" className="min-h-11" disabled={!file || !empresaId || loading} onClick={handlePreview}>
              {loading ? <><Loader2 className="size-4 animate-spin" />Procesando...</> : "Vista previa"}
            </Button>
          )}

          {step === "preview" && (
            <>
              <Button type="button" variant="outline" className="min-h-11" onClick={() => { setStep("upload"); setPreview(null) }}>
                Volver
              </Button>
              <Button type="button" className="min-h-11" disabled={validCount === 0} onClick={() => setStep("confirm")}>
                Confirmar {validCount} operación{validCount !== 1 ? "es" : ""}
              </Button>
            </>
          )}

          {step === "confirm" && (
            <>
              <Button type="button" variant="outline" className="min-h-11" onClick={() => setStep("preview")} disabled={confirming}>
                Volver
              </Button>
              <Button type="button" className="min-h-11" disabled={confirming} onClick={handleConfirm}>
                {confirming ? <><Loader2 className="size-4 animate-spin" />Importando...</> : "Sí, importar"}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

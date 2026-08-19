"use client"

import { useEffect, useState } from "react"
import { Loader2, Upload } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Empresa } from "@/types/empresa"

interface Props {
  empresaId: string
  periodo: string
  cargando: boolean
  error: string | null
  onEmpresa: (id: string) => void
  onPeriodo: (p: string) => void
  onSubmit: (empresaId: string, periodo: string, notas: File, desglose: File) => void
}

function ArchivoInput({ label, descripcion, file, onFile }: {
  label: string; descripcion: string; file: File | null; onFile: (f: File | null) => void
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium">{label}</label>
      <p className="text-xs text-muted-foreground">{descripcion}</p>
      <input
        type="file" accept=".csv"
        onChange={(e) => onFile(e.target.files?.[0] ?? null)}
        className="block w-full text-sm text-muted-foreground file:mr-3 file:rounded-lg file:border file:border-input file:bg-transparent file:px-3 file:py-1.5 file:text-sm file:text-foreground"
      />
      {file && <p className="text-xs text-muted-foreground">Elegido: {file.name}</p>}
    </div>
  )
}

// Paso 1: elegir empresa (import necesita una concreta) + período + los dos CSV, bien diferenciados.
export function SubirPaso({ empresaId, periodo, cargando, error, onEmpresa, onPeriodo, onSubmit }: Props) {
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [notas, setNotas] = useState<File | null>(null)
  const [desglose, setDesglose] = useState<File | null>(null)

  useEffect(() => {
    fetchEmpresas()
      .then((r) => {
        setEmpresas(r.items)
        if (!empresaId) onEmpresa(getEmpresaActivaId() ?? r.items[0]?.id ?? "")
      })
      .catch(() => undefined)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const listo = Boolean(empresaId && periodo.trim() && notas && desglose && !cargando)

  return (
    <div className="max-w-2xl space-y-5">
      <div className="space-y-1.5">
        <label className="text-sm font-medium">Empresa</label>
        <Select value={empresaId} onChange={(e) => onEmpresa(e.target.value)}>
          <option value="">Elegí una empresa</option>
          {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
        </Select>
      </div>
      <div className="space-y-1.5">
        <label className="text-sm font-medium">Período</label>
        <Input value={periodo} onChange={(e) => onPeriodo(e.target.value)} placeholder="Ej: Ciclo 2026" />
      </div>
      <ArchivoInput label="1 · Notas finales"
        descripcion="CSV con una fila por persona y su nota final."
        file={notas} onFile={setNotas} />
      <ArchivoInput label="2 · Desglose por competencia"
        descripcion="CSV con una fila por persona y tipo de evaluador (autoevaluación, par, etc.)."
        file={desglose} onFile={setDesglose} />
      {error && <p className="text-sm text-destructive" role="alert">{error}</p>}
      <Button
        disabled={!listo}
        onClick={() => { if (notas && desglose) onSubmit(empresaId, periodo.trim(), notas, desglose) }}
      >
        {cargando ? <Loader2 className="size-4 animate-spin" /> : <Upload className="size-4" />}
        Ver preview
      </Button>
    </div>
  )
}

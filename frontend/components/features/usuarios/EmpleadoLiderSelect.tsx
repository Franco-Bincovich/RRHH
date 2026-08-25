"use client"

import { useMemo, useState } from "react"
import { PISO_TACTIL } from "@/components/ui/AccionFila"
import { Check, Search } from "lucide-react"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"
import type { EmpleadoLider } from "@/services/usuarios"

interface EmpleadoLiderSelectProps {
  value: string // id del empleado seleccionado; "" = sin vincular
  onChange: (id: string) => void
  options: EmpleadoLider[]
  loading: boolean
  error: boolean
  onRetry: () => void
  hint?: string // texto de ayuda bajo el label (varía según qué empleados se listan)
}

function etiqueta(e: EmpleadoLider): string {
  return `${e.apellido}, ${e.nombre}${e.legajo ? ` · ${e.legajo}` : ""}`
}

const HINT_DEFAULT = "Opcional. Solo se listan colaboradores marcados como líderes."

/** Selector buscable de empleados para vincular al usuario. Incluye "sin vincular". */
export function EmpleadoLiderSelect({ value, onChange, options, loading, error, onRetry, hint }: EmpleadoLiderSelectProps) {
  const [query, setQuery] = useState("")

  const filtradas = useMemo(() => {
    const q = query.trim().toLowerCase()
    return q ? options.filter((e) => etiqueta(e).toLowerCase().includes(q)) : options
  }, [options, query])

  if (error) {
    return (
      <div className="flex flex-col gap-1.5">
        <Label>Colaborador vinculado</Label>
        <div className="rounded-md border border-destructive/40 p-3 text-sm">
          <span className="text-destructive">No se pudieron cargar los colaboradores.</span>{" "}
          <button type="button" className="underline hover:text-primary" onClick={onRetry}>
            Reintentar
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor="empleado-lider-search">Colaborador vinculado</Label>
      <p className="text-xs text-muted-foreground">{hint ?? HINT_DEFAULT}</p>
      <div className="relative">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          id="empleado-lider-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={loading ? "Cargando..." : "Buscar por nombre o legajo..."}
          className="pl-8"
          disabled={loading}
          autoComplete="off"
        />
      </div>
      <ul role="listbox" aria-label="Colaboradores" className="max-h-44 overflow-y-auto rounded-md border">
        <li>
          <Opcion selected={value === ""} onClick={() => onChange("")}>
            <span className="italic text-muted-foreground">Sin vincular</span>
          </Opcion>
        </li>
        {filtradas.map((e) => (
          <li key={e.id}>
            <Opcion selected={value === e.id} onClick={() => onChange(e.id)}>
              {etiqueta(e)}
            </Opcion>
          </li>
        ))}
        {!loading && filtradas.length === 0 && (
          <li className="px-3 py-2 text-sm text-muted-foreground">Sin resultados.</li>
        )}
      </ul>
    </div>
  )
}

function Opcion({ selected, onClick, children }: { selected: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      role="option"
      aria-selected={selected}
      className={cn(
        PISO_TACTIL,
        "flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-muted",
        selected && "bg-muted/60",
      )}
      onClick={onClick}
    >
      <span>{children}</span>
      {selected && <Check className="size-4 shrink-0 text-primary" />}
    </button>
  )
}

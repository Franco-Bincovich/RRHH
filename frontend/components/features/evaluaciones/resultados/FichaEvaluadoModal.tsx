"use client"

import { useEffect, useState } from "react"

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { fetchFicha } from "@/services/evaluacionReportes"
import type { FichaResponse } from "@/types/evaluacionReportes"

const LABEL: Record<string, string> = {
  AUTOEVALUACION: "Auto", AUTOEVALUACION_LIDER: "Auto (líder)", SUPERIOR_INMEDIATO: "Superior",
  PAR: "Par", COLABORADOR: "Colaborador", LIBRES: "Libres",
}

interface Props {
  loteId: string
  evaluadoId: string
  onClose: () => void
}

export function FichaEvaluadoModal({ loteId, evaluadoId, onClose }: Props) {
  const [f, setF] = useState<FichaResponse | null>(null)

  useEffect(() => {
    fetchFicha(loteId, evaluadoId).then(setF).catch(() => onClose())
  }, [loteId, evaluadoId]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose() }}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>{f ? `${f.apellido} ${f.nombre}` : "Ficha del evaluado"}</DialogTitle>
        </DialogHeader>
        {!f ? (
          <Skeleton className="h-64 w-full rounded-lg" />
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {f.perfil === "lider" ? "Perfil líder" : "Perfil general"}
              {f.sector ? ` · ${f.sector}` : ""}
              {f.nota_final != null ? ` · Nota final ${f.nota_final}` : " · Sin nota final"}
            </p>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-border text-left">
                    <th className="p-2">Competencia</th>
                    {f.tipos.map((t) => <th key={t} className="p-2 text-center">{LABEL[t] ?? t}</th>)}
                    <th className="p-2 text-center">Prom. terceros</th>
                  </tr>
                </thead>
                <tbody>
                  {f.competencias.map((c) => (
                    <tr key={c} className="border-b border-border/50">
                      <td className="p-2">{c}</td>
                      {f.tipos.map((t) => <td key={t} className="p-2 text-center">{f.celdas[c]?.[t] ?? "—"}</td>)}
                      <td className="p-2 text-center font-medium">{f.promedio_terceros[c] ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

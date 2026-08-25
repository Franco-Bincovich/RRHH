"use client"

import { useEffect, useState } from "react"
import { toast } from "sonner"
import { X } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { EstadoCandidatoBadge } from "@/components/features/candidatos/EstadoCandidatoBadge"
import { Button } from "@/components/ui/button"
import { CandidatoClasificacion } from "@/components/features/candidatos/CandidatoClasificacion"
import { CandidatoCv } from "@/components/features/candidatos/CandidatoCv"
import { CandidatoAcciones } from "@/components/features/candidatos/CandidatoAcciones"
import {
  Campo, ETAPA_LABELS, Section,
} from "@/components/features/candidatos/_candidatoPanelUI"
import { getCandidatoCvUrl } from "@/services/candidatos"
import type { CandidatoConGrupo } from "@/types/candidato"

interface Props {
  candidato: CandidatoConGrupo | null
  open: boolean
  onClose: () => void
  onDeleted?: () => void
  onAsignada?: () => void
  onContratado?: () => void
}

/** Panel lateral (drawer) de solo lectura con el detalle del candidato, en secciones. */
export function CandidatoDetailPanel({
  candidato, open, onClose, onDeleted, onAsignada, onContratado,
}: Props) {
  const [loadingCv, setLoadingCv] = useState(false)

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose() }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open, onClose])

  if (!open || !candidato) return null
  const c = candidato

  async function abrirCv() {
    setLoadingCv(true)
    try {
      window.open(await getCandidatoCvUrl(c.id), "_blank", "noopener,noreferrer")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "No se pudo abrir el CV.")
    } finally {
      setLoadingCv(false)
    }
  }

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/40" onClick={onClose} aria-hidden />
      <aside
        role="dialog"
        aria-label="Detalle del candidato"
        className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col overflow-y-auto border-l bg-background shadow-xl"
      >
        <header className="flex items-start justify-between gap-2 border-b p-4">
          <div className="min-w-0">
            <h2 className="truncate text-lg font-semibold text-foreground">{c.nombre} {c.apellido}</h2>
            <p className="truncate text-sm text-muted-foreground">{c.email}</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Cerrar" className="shrink-0 text-muted-foreground hover:text-foreground">
            <X className="size-5" />
          </button>
        </header>

        <div className="flex-1 space-y-6 p-4">
          <Section title="Datos personales">
            <Campo label="Nombre" value={c.nombre} />
            <Campo label="Apellido" value={c.apellido} />
            <Campo label="Email" value={c.email} />
            <Campo label="Teléfono" value={c.telefono} />
          </Section>

          <Section title="Experiencia">
            <Campo label="Cargo anterior" value={c.cargo_anterior} />
            <Campo label="Empresa anterior" value={c.empresa_anterior} />
            {!c.cargo_anterior && !c.empresa_anterior && (
              <p className="text-sm text-muted-foreground">Sin datos de experiencia.</p>
            )}
          </Section>

          <Section title="Búsqueda">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm text-foreground">{c.grupo_nombre ?? "Sin búsqueda"}</span>
              {c.busqueda_activa ? (
                <Badge variant="outline">Activa</Badge>
              ) : (
                <Badge variant="secondary">Búsqueda cerrada</Badge>
              )}
            </div>
          </Section>

          {/* 🔴 LOS DOS EJES, NO UNO. El panel mostraba sólo la etapa, así que después de
              contratar seguía diciendo "Oferta" — el mismo bug que la tarjeta del listado. La
              etapa dice DÓNDE llegó (y contratar no la toca, a propósito: es el embudo) y el
              estado dice CÓMO terminó. Ver `EstadoCandidatoBadge`. */}
          <Section title={c.estado === "activo" ? "Etapa" : "Etapa y desenlace"}>
            <span className="flex flex-wrap items-center gap-2">
              <Badge variant={c.estado === "activo" ? "secondary" : "outline"}>
                {ETAPA_LABELS[c.etapa_pipeline] ?? c.etapa_pipeline}
              </Badge>
              <EstadoCandidatoBadge estado={c.estado} />
            </span>
          </Section>

          <Section title="Preselección">
            <CandidatoClasificacion candidato={c} onCorregido={onDeleted} />
          </Section>

          <Section title="CV">
            <CandidatoCv
              storagePath={c.cv_storage_path}
              warning={c.screening_warning}
              loading={loadingCv}
              onAbrir={abrirCv}
            />
          </Section>

          <CandidatoAcciones
            candidato={c}
            onClose={onClose}
            onDeleted={onDeleted}
            onAsignada={onAsignada}
            onContratado={onContratado}
          />
        </div>
      </aside>
    </>
  )
}

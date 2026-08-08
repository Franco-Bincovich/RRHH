"use client"

import { useEffect, useState } from "react"
import { UserMinus, Paperclip } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/PageHeader"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/EmptyState"
import { AdjuntosDialog } from "@/components/features/adjuntos/AdjuntosDialog"
import { cn } from "@/lib/utils"
import { EntrevistaSalida } from "@/components/features/offboarding/EntrevistaSalida"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { exportarOffboardings, fetchOffboardings, marcarActivoDevuelto } from "@/services/offboarding"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { ActivoResponse, MotivoEgreso, OffboardingInstancia } from "@/types/offboarding"

// ─── Constants ────────────────────────────────────────────────────────────────

const MOTIVO_LABEL: Record<MotivoEgreso, string> = {
  renuncia:      "Renuncia",
  despido:       "Desvinculación",
  acuerdo_mutuo: "Acuerdo mutuo",
  fin_contrato:  "Fin de contrato",
  jubilacion:    "Jubilación",
  fallecimiento: "Fallecimiento",
  otro:          "Otro motivo",
}

const MOTIVO_VARIANT: Record<MotivoEgreso, "secondary" | "destructive"> = {
  renuncia:      "secondary",
  despido:       "destructive",
  acuerdo_mutuo: "secondary",
  fin_contrato:  "secondary",
  jubilacion:    "secondary",
  fallecimiento: "destructive",
  otro:          "secondary",
}

const TIPO_ACTIVO_LABEL: Record<string, string> = {
  laptop:           "Laptop de trabajo",
  celular:          "Teléfono corporativo",
  monitor:          "Monitor",
  tarjeta_acceso:   "Tarjeta de acceso",
  licencia_software:"Licencias de software",
  llave:            "Llaves",
  uniforme:         "Uniforme",
  otro:             "Activo corporativo",
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function OffboardingPage() {
  const canWrite = useCanWrite()
  const [offboardings, setOffboardings] = useState<OffboardingInstancia[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState<string | null>(null)
  const [empresaActivaId] = useState<string | null>(() => getEmpresaActivaId())
  const [docsFor, setDocsFor] = useState<OffboardingInstancia | null>(null)

  useEffect(() => {
    fetchOffboardings()
      .then(setOffboardings)
      .catch(() => setError("No se pudieron cargar los offboardings"))
      .finally(() => setLoading(false))
  }, [])

  async function toggleActivo(
    instanciaId: string,
    activo: ActivoResponse,
  ) {
    const newDevuelto = !activo.devuelto
    const key = `${instanciaId}-${activo.id}`
    setSaving(key)

    setOffboardings((prev) =>
      prev.map((o) =>
        o.id !== instanciaId
          ? o
          : {
              ...o,
              activos: o.activos.map((a) =>
                a.id === activo.id
                  ? { ...a, devuelto: newDevuelto, estado: newDevuelto ? "devuelto" : "pendiente" }
                  : a,
              ),
              progreso: calcProgress(
                o.activos.map((a) =>
                  a.id === activo.id ? { ...a, devuelto: newDevuelto } : a,
                ),
              ),
            },
      ),
    )

    try {
      await marcarActivoDevuelto(instanciaId, activo.id, newDevuelto)
    } catch {
      toast.error("No se pudo actualizar el activo. Intentá de nuevo.")
      // Revert on failure
      setOffboardings((prev) =>
        prev.map((o) =>
          o.id !== instanciaId
            ? o
            : {
                ...o,
                activos: o.activos.map((a) =>
                  a.id === activo.id ? activo : a,
                ),
                progreso: calcProgress(o.activos),
              },
        ),
      )
    } finally {
      setSaving(null)
    }
  }

  function calcProgress(activos: ActivoResponse[]): number {
    if (activos.length === 0) return 0
    const done = activos.filter((a) => a.devuelto).length
    return Math.round((done / activos.length) * 100)
  }

  // mostrar empresa solo cuando el topbar está en "Todas"
  const mostrarEmpresa = !empresaActivaId

  // ─── Loading skeleton ────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div>
        <PageHeader title="Offboarding" description="Cargando..." />
        <ul className="space-y-4" role="list">
          {[1, 2].map((i) => (
            <li key={i} className="h-40 animate-pulse rounded-xl bg-muted" />
          ))}
        </ul>
      </div>
    )
  }

  // ─── Error state ─────────────────────────────────────────────────────────────

  if (error) {
    return (
      <div>
        <PageHeader title="Offboarding" description="Error al cargar" />
        <p className="text-sm text-destructive">{error}</p>
      </div>
    )
  }

  // ─── Main render ─────────────────────────────────────────────────────────────

  return (
    <div>
      <PageHeader
        title="Offboarding"
        description={`${offboardings.length} procesos activos`}
        // El archivo sale del MISMO listado que las tarjetas y esta pantalla no tiene filtros:
        // trae exactamente los procesos que se ven. Sin procesos no se ofrece exportar.
        action={offboardings.length > 0 ? <ExportMenu onExport={exportarOffboardings} /> : undefined}
      />

      {offboardings.length === 0 ? (
        <EmptyState
          icon={<UserMinus />}
          title="Sin procesos activos"
          description="No hay empleados en proceso de offboarding actualmente."
        />
      ) : (
        <ul className="space-y-4" role="list">
          {offboardings.map((inst) => {
            const motivo = inst.motivo as MotivoEgreso

            return (
              <li key={inst.id} className="rounded-xl border bg-card p-4 md:p-5">
                {/* Header */}
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-medium text-foreground">{inst.empleado_nombre}</p>
                    <p className="mt-0.5 text-sm text-muted-foreground">
                      Egreso: {inst.fecha_inicio}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {mostrarEmpresa && inst.empresa_nombre && (
                      <Badge variant="outline" className="text-xs">
                        {inst.empresa_nombre}
                      </Badge>
                    )}
                    <Badge
                      variant={MOTIVO_VARIANT[motivo] ?? "secondary"}
                    >
                      {MOTIVO_LABEL[motivo] ?? motivo}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="min-h-11 gap-1.5"
                      onClick={() => setDocsFor(inst)}
                    >
                      <Paperclip className="size-4" /> Documentos
                    </Button>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="mt-3">
                  <div className="mb-1.5 flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">
                      {inst.activos.filter((a) => a.devuelto).length} de{" "}
                      {inst.activos.length} activos devueltos
                    </span>
                    <span className="font-medium text-foreground">{inst.progreso}%</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-primary transition-all duration-300"
                      style={{ width: `${inst.progreso}%` }}
                    />
                  </div>
                </div>

                {/* Activos checklist */}
                {inst.activos.length > 0 ? (
                  <ul
                    className="mt-4 divide-y divide-border"
                    role="list"
                    aria-label="Activos corporativos"
                  >
                    {inst.activos.map((activo) => {
                      const key = `${inst.id}-${activo.id}`
                      const isSaving = saving === key
                      return (
                        <li key={activo.id}>
                          <label
                            className={cn(
                              "flex items-center gap-2.5 py-2.5",
                              canWrite && "cursor-pointer transition-colors hover:text-primary",
                              isSaving && "opacity-60",
                            )}
                          >
                            {canWrite && (
                              <input
                                type="checkbox"
                                checked={activo.devuelto}
                                onChange={() => !isSaving && toggleActivo(inst.id, activo)}
                                disabled={isSaving}
                                className="size-4 shrink-0 accent-primary"
                              />
                            )}
                            <span
                              className={cn(
                                "text-sm",
                                activo.devuelto
                                  ? "text-muted-foreground line-through decoration-muted-foreground/60"
                                  : "text-foreground",
                              )}
                            >
                              {TIPO_ACTIVO_LABEL[activo.tipo_activo] ?? activo.tipo_activo}
                              {activo.descripcion && (
                                <span className="ml-1 text-xs text-muted-foreground">
                                  — {activo.descripcion}
                                </span>
                              )}
                            </span>
                          </label>
                        </li>
                      )
                    })}
                  </ul>
                ) : (
                  <p className="mt-3 text-xs text-muted-foreground">
                    Sin activos registrados para devolver.
                  </p>
                )}

                <EntrevistaSalida
                  instancia={inst}
                  canWrite={canWrite}
                  onGuardado={(id, realizada, notas) =>
                    setOffboardings((prev) =>
                      prev.map((o) =>
                        o.id === id
                          ? { ...o, entrevista_salida: realizada, notas_entrevista: notas }
                          : o,
                      ),
                    )
                  }
                />
              </li>
            )
          })}
        </ul>
      )}

      <AdjuntosDialog
        open={!!docsFor}
        onClose={() => setDocsFor(null)}
        entidad="offboarding"
        entidadId={docsFor?.id ?? ""}
        titulo={`Offboarding · ${docsFor?.empleado_nombre ?? ""}`}
      />
    </div>
  )
}

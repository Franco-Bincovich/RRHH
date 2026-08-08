"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { ChevronRight, Plus, Settings2, UserCheck, X } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { Badge } from "@/components/ui/badge"
import { EmptyState } from "@/components/ui/EmptyState"
import { OnboardingChecklist } from "@/components/features/onboarding/OnboardingChecklist"
import { fetchEmpleados } from "@/services/empleados"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { exportarOnboardings, fetchOnboardingEmpleado, fetchOnboardings, fetchTemplates, iniciarOnboarding } from "@/services/onboarding"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { Empleado } from "@/types/empleado"
import type { OnboardingDetalle, OnboardingInstancia, OnboardingTemplate } from "@/types/onboarding"

// ─── Helpers ──────────────────────────────────────────────────────────────────

function semanaLabel(inst: OnboardingInstancia): string {
  if (inst.progreso >= 100) return "Completado"
  if (inst.tareas_total === 0) return "Semana 1"
  const semanasCompletadas = Math.floor(inst.tareas_completadas / (inst.tareas_total / 4))
  return `Semana ${Math.min(semanasCompletadas + 1, 4)}`
}

// ─── IniciarModal ──────────────────────────────────────────────────────────────

interface IniciarModalProps {
  activos: OnboardingInstancia[]
  onClose: () => void
  onSuccess: (instancia: OnboardingInstancia) => void
}

function IniciarModal({ activos, onClose, onSuccess }: IniciarModalProps) {
  const [empleados, setEmpleados] = useState<Empleado[]>([])
  const [templates, setTemplates] = useState<OnboardingTemplate[]>([])
  const [loadingEmp, setLoadingEmp] = useState(true)
  const [selectedId, setSelectedId] = useState("")
  const [selectedTemplateId, setSelectedTemplateId] = useState("")
  const [iniciando, setIniciando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const ids = new Set(activos.map((o) => o.empleado_id))
    Promise.all([
      fetchEmpleados({ page: 1, pageSize: 100, estado: "activo" }),
      fetchTemplates(),
    ])
      .then(([emps, tmpls]) => {
        setEmpleados(emps.items.filter((e) => !ids.has(e.id)))
        setTemplates(tmpls)
      })
      .catch(() => setError("No se pudieron cargar los datos"))
      .finally(() => setLoadingEmp(false))
  }, [activos])

  // Filtra templates para mostrar solo los de la misma empresa que el empleado elegido
  const selectedEmpleado = empleados.find((e) => e.id === selectedId)
  const filteredTemplates =
    selectedId && selectedEmpleado?.empresa_id
      ? templates.filter((t) => t.empresa_id === selectedEmpleado.empresa_id)
      : templates

  useEffect(() => {
    if (filteredTemplates.length > 0) {
      setSelectedTemplateId(filteredTemplates[0].id)
    } else {
      setSelectedTemplateId("")
    }
  }, [selectedId])

  async function handleIniciar() {
    if (!selectedId || iniciando) return
    setIniciando(true)
    setError(null)
    try {
      const instancia = await iniciarOnboarding(selectedId, selectedTemplateId || undefined)
      onSuccess(instancia)
    } catch {
      setError("No se pudo iniciar el onboarding. Verificá que el empleado no tenga uno activo.")
      setIniciando(false)
    }
  }

  return (
    <>
      <div
        className="fixed inset-0 z-50 bg-black/40"
        aria-hidden="true"
        onClick={onClose}
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-iniciar-title"
        className="fixed inset-x-4 top-1/2 z-50 -translate-y-1/2 rounded-2xl bg-background p-6 shadow-2xl ring-1 ring-border sm:inset-auto sm:left-1/2 sm:w-[26rem] sm:-translate-x-1/2"
      >
        {/* Header */}
        <div className="mb-5 flex items-center justify-between gap-2">
          <h2
            id="modal-iniciar-title"
            className="text-base font-semibold text-foreground"
          >
            Iniciar onboarding
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="flex min-h-9 min-w-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <X className="size-4" />
          </button>
        </div>

        {/* Selects */}
        <div className="space-y-4">
          <div>
            <label
              htmlFor="emp-select"
              className="mb-1.5 block text-sm font-medium text-foreground"
            >
              Empleado
            </label>

            {loadingEmp ? (
              <div className="h-10 animate-pulse rounded-lg bg-muted" />
            ) : (
              <select
                id="emp-select"
                value={selectedId}
                onChange={(e) => setSelectedId(e.target.value)}
                className="w-full rounded-lg border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-60"
              >
                <option value="">Seleccioná un empleado…</option>
                {empleados.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.nombre} {e.apellido}
                    {e.roles?.[0] ?? e.cargo ? ` — ${e.roles?.[0] ?? e.cargo}` : ""}
                  </option>
                ))}
              </select>
            )}

            {!loadingEmp && !error && empleados.length === 0 && (
              <p className="mt-1.5 text-xs text-muted-foreground">
                Todos los empleados activos ya tienen un onboarding en curso.
              </p>
            )}
          </div>

          {!loadingEmp && selectedId && (
            <div>
              <label
                htmlFor="tmpl-select"
                className="mb-1.5 block text-sm font-medium text-foreground"
              >
                Template
              </label>
              {filteredTemplates.length > 0 ? (
                <select
                  id="tmpl-select"
                  value={selectedTemplateId}
                  onChange={(e) => setSelectedTemplateId(e.target.value)}
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  {filteredTemplates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.nombre}
                    </option>
                  ))}
                </select>
              ) : (
                <p className="text-xs text-muted-foreground">
                  No hay templates configurados para la empresa de este empleado.
                </p>
              )}
            </div>
          )}
        </div>

        {error && (
          <p className="mt-3 text-sm text-destructive">{error}</p>
        )}

        {/* Actions */}
        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleIniciar}
            disabled={!selectedId || !selectedTemplateId || iniciando || loadingEmp}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
          >
            {iniciando ? "Iniciando…" : "Iniciar"}
          </button>
        </div>
      </div>
    </>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function OnboardingPage() {
  const canWrite = useCanWrite()
  const [onboardings, setOnboardings] = useState<OnboardingInstancia[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [detalle, setDetalle] = useState<OnboardingDetalle | null>(null)
  const [loadingDetalle, setLoadingDetalle] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [empresaActivaId] = useState<string | null>(() => getEmpresaActivaId())

  useEffect(() => {
    fetchOnboardings()
      .then(setOnboardings)
      .catch(() => setError("No se pudieron cargar los onboardings"))
      .finally(() => setLoading(false))
  }, [])

  async function handleSelect(empleadoId: string) {
    if (detalle?.empleado_id === empleadoId) {
      setDetalle(null)
      return
    }
    setLoadingDetalle(true)
    try {
      const d = await fetchOnboardingEmpleado(empleadoId)
      setDetalle(d)
    } catch {
      // Silently fail — no bloquea la lista
    } finally {
      setLoadingDetalle(false)
    }
  }

  function handleTareaToggled(tareaId: string, completada: boolean) {
    if (!detalle) return
    const updatedTareas = detalle.tareas.map((t) =>
      t.tarea_id === tareaId ? { ...t, completada } : t,
    )
    const done = updatedTareas.filter((t) => t.completada).length
    const total = updatedTareas.length
    const pct = total > 0 ? Math.round((done / total) * 100) : 0
    setDetalle({ ...detalle, tareas: updatedTareas, progreso: pct, tareas_completadas: done })
    setOnboardings((prev) =>
      prev.map((o) =>
        o.empleado_id === detalle.empleado_id
          ? { ...o, progreso: pct, tareas_completadas: done }
          : o,
      ),
    )
  }

  function handleOnboardingIniciado(instancia: OnboardingInstancia) {
    setOnboardings((prev) => [instancia, ...prev])
    setModalOpen(false)
  }

  // mostrar columna empresa solo cuando el topbar está en "Todas"
  const mostrarEmpresa = !empresaActivaId

  // ─── Loading skeleton ────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div>
        <PageHeader title="Onboarding" description="Cargando..." />
        <ul className="space-y-3" role="list">
          {[1, 2, 3].map((i) => (
            <li key={i} className="h-24 animate-pulse rounded-xl bg-muted" />
          ))}
        </ul>
      </div>
    )
  }

  // ─── Error state ─────────────────────────────────────────────────────────────

  if (error) {
    return (
      <div>
        <PageHeader title="Onboarding" description="Error al cargar" />
        <p className="text-sm text-destructive">{error}</p>
      </div>
    )
  }

  // ─── Main render ─────────────────────────────────────────────────────────────

  return (
    <div>
      {/* Header + acciones */}
      <div className="relative">
        <PageHeader
          title="Onboarding"
          description={`${onboardings.length} colaboradores en proceso`}
        />
        <div className="absolute right-0 top-0 flex items-center gap-2">
          {/* Exportar es LECTURA: no va detrás de canWrite. */}
          <ExportMenu onExport={exportarOnboardings} />
          <Link
            href="/onboarding/templates"
            className="flex min-h-10 items-center gap-1.5 rounded-lg border px-3 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Settings2 className="size-4" />
            <span className="hidden sm:inline">Gestionar templates</span>
          </Link>
          {canWrite && (
            <button
              type="button"
              onClick={() => setModalOpen(true)}
              className="flex min-h-10 items-center gap-1.5 rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Plus className="size-4" />
              <span className="hidden sm:inline">Iniciar onboarding</span>
            </button>
          )}
        </div>
      </div>

      {onboardings.length === 0 ? (
        <EmptyState
          icon={<UserCheck />}
          title="Sin procesos activos"
          description="No hay empleados en proceso de onboarding actualmente."
        />
      ) : (
        <ul className="space-y-3" role="list">
          {onboardings.map((inst) => (
            <li key={inst.id}>
              <button
                type="button"
                onClick={() => handleSelect(inst.empleado_id)}
                disabled={loadingDetalle}
                className="w-full rounded-xl border bg-card p-4 text-left transition-all hover:border-primary/40 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-medium text-foreground">{inst.empleado_nombre}</p>
                    <p className="mt-0.5 text-sm text-muted-foreground">
                      {inst.empleado_cargo ?? "—"} · {inst.empleado_area ?? "—"}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {mostrarEmpresa && inst.empresa_nombre && (
                      <Badge variant="outline" className="text-xs">
                        {inst.empresa_nombre}
                      </Badge>
                    )}
                    <Badge variant="secondary">{semanaLabel(inst)}</Badge>
                    <ChevronRight className="size-4 text-muted-foreground" />
                  </div>
                </div>

                <div className="mt-3">
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Inicio: {inst.fecha_inicio}</span>
                    <span className="font-medium text-foreground">{inst.progreso}%</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-primary transition-all duration-300"
                      style={{ width: `${inst.progreso}%` }}
                    />
                  </div>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Backdrop del checklist */}
      {detalle && (
        <div
          className="fixed inset-0 z-30 bg-black/20 dark:bg-black/40"
          aria-hidden="true"
          onClick={() => setDetalle(null)}
        />
      )}

      {/* Checklist panel */}
      {detalle && (
        <OnboardingChecklist
          detalle={detalle}
          canWrite={canWrite}
          onClose={() => setDetalle(null)}
          onTareaToggled={handleTareaToggled}
        />
      )}

      {/* Modal iniciar onboarding */}
      {modalOpen && (
        <IniciarModal
          activos={onboardings}
          onClose={() => setModalOpen(false)}
          onSuccess={handleOnboardingIniciado}
        />
      )}
    </div>
  )
}

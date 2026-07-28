"use client"

import { useState, useEffect, useCallback } from "react"
import { DollarSign, FileSpreadsheet, FileText, Pencil, TrendingUp, Upload, Users } from "lucide-react"
import type { LucideIcon } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { NominaModal } from "@/components/features/costos/NominaModal"
import { ImportarNominaCSVModal } from "@/components/features/costos/ImportarNominaCSVModal"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { cargarNomina, exportarNomina, fetchDashboardCostos, fetchNominaMes } from "@/services/costos"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { DashboardCostos, EvolucionMes, Nomina } from "@/types/costo"

// ─── Constants ────────────────────────────────────────────────────────────────

const MESES_CORTOS = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
const MESES_LARGOS = [
  "Enero","Febrero","Marzo","Abril","Mayo","Junio",
  "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre",
]
const ANIOS = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i)

// ─── Helpers ──────────────────────────────────────────────────────────────────

function pesos(n: number): string {
  const abs = Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".")
  return n < 0 ? `-$${abs}` : `$${abs}`
}

function varLabel(v: number | null): string {
  if (v === null) return "Sin datos previos"
  return `${v >= 0 ? "+" : ""}${v.toFixed(1)} %`
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function PeriodSelector({
  mes,
  anio,
  onChangeMes,
  onChangeAnio,
}: {
  mes: number
  anio: number
  onChangeMes: (m: number) => void
  onChangeAnio: (y: number) => void
}) {
  const cls =
    "rounded-md border bg-background px-3 py-1.5 text-sm text-foreground " +
    "focus:outline-none focus:ring-2 focus:ring-ring"
  return (
    <div className="flex items-center gap-2">
      <select value={mes} onChange={(e) => onChangeMes(Number(e.target.value))} className={cls}>
        {MESES_LARGOS.map((label, i) => (
          <option key={i + 1} value={i + 1}>
            {label}
          </option>
        ))}
      </select>
      <select value={anio} onChange={(e) => onChangeAnio(Number(e.target.value))} className={cls}>
        {ANIOS.map((y) => (
          <option key={y} value={y}>
            {y}
          </option>
        ))}
      </select>
    </div>
  )
}

function KpiCard({
  title,
  value,
  icon: Icon,
  description,
  accent,
}: {
  title: string
  value: string
  icon: LucideIcon
  description: string
  accent?: boolean
}) {
  return (
    <div className="rounded-xl border bg-card p-4 md:p-5">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-muted-foreground">{title}</p>
        <span className="shrink-0 rounded-lg bg-primary/10 p-1.5 text-primary">
          <Icon className="size-4" />
        </span>
      </div>
      <p
        className={`mt-3 text-2xl font-bold tracking-tight ${
          accent ? "text-emerald-600 dark:text-emerald-400" : "text-foreground"
        }`}
      >
        {value}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">{description}</p>
    </div>
  )
}

function EvolucionChart({ data }: { data: EvolucionMes[] }) {
  if (!data.length) return null
  const max = Math.max(...data.map((d) => d.total))
  const BAR_MAX_PX = 128

  return (
    <section
      className="rounded-xl border bg-card p-4 md:p-6"
      aria-label="Evolución mensual del costo de nómina"
    >
      <h2 className="mb-5 text-base font-semibold text-foreground">Evolución mensual</h2>
      <div className="flex h-32 gap-3">
        {data.map((d) => {
          const barPx = max > 0 ? Math.round((d.total / max) * BAR_MAX_PX) : 0
          const label =
            d.total >= 1_000_000
              ? `$${(d.total / 1_000_000).toFixed(1)}M`
              : `$${(d.total / 1_000).toFixed(0)}k`
          return (
            <div
              key={`${d.mes}-${d.anio}`}
              className="relative flex flex-1 items-end rounded-sm bg-muted/20"
            >
              <span
                className="absolute left-0 right-0 text-center text-xs text-muted-foreground"
                style={{ bottom: `${barPx + 6}px` }}
              >
                {label}
              </span>
              <div
                aria-hidden="true"
                className="w-full rounded-t-sm bg-primary"
                style={{ height: `${barPx}px` }}
              />
            </div>
          )
        })}
      </div>
      <div className="mt-2 flex gap-3">
        {data.map((d) => (
          <div
            key={`${d.mes}-${d.anio}`}
            className="flex-1 text-center text-xs font-medium text-muted-foreground"
          >
            {MESES_CORTOS[d.mes - 1]}
          </div>
        ))}
      </div>
    </section>
  )
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-56 rounded-xl" />
      <Skeleton className="h-72 rounded-xl" />
      <Skeleton className="h-64 rounded-xl" />
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CostosPage() {
  const canWrite = useCanWrite()
  const now = new Date()
  // empresa activa del topbar — estable (el topbar recarga la página al cambiar)
  const [empresaActivaId] = useState<string | null>(() =>
    typeof window !== "undefined" ? getEmpresaActivaId() : null
  )
  const [mes, setMes] = useState(now.getMonth() + 1)
  const [anio, setAnio] = useState(now.getFullYear())
  const [dashboard, setDashboard] = useState<DashboardCostos | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [nominaOpen, setNominaOpen] = useState(false)
  const [importarNominaOpen, setImportarNominaOpen] = useState(false)

  const [nomina, setNomina] = useState<Nomina[]>([])
  const [nominaListLoading, setNominaListLoading] = useState(true)
  const [nominaListError, setNominaListError] = useState(false)

  const [editItem, setEditItem] = useState<Nomina | null>(null)
  const [editBruto, setEditBruto] = useState("")
  const [editNeto, setEditNeto] = useState("")
  const [editSaving, setEditSaving] = useState(false)
  const [editError, setEditError] = useState("")

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const data = await fetchDashboardCostos(mes, anio)
      setDashboard(data)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [mes, anio])

  const loadNomina = useCallback(async () => {
    setNominaListLoading(true)
    setNominaListError(false)
    try {
      const data = await fetchNominaMes(mes, anio)
      setNomina(data)
    } catch {
      setNominaListError(true)
    } finally {
      setNominaListLoading(false)
    }
  }, [mes, anio])

  useEffect(() => { load() }, [load])
  useEffect(() => { loadNomina() }, [loadNomina])

  function openEdit(item: Nomina) {
    setEditItem(item)
    setEditBruto(String(item.monto_bruto))
    setEditNeto(String(item.monto_neto))
    setEditError("")
  }

  async function saveEdit() {
    if (!editItem) return
    setEditSaving(true)
    setEditError("")
    try {
      await cargarNomina({
        empleado_id: editItem.empleado_id,
        mes,
        anio,
        monto_bruto: Number(editBruto),
        monto_neto: Number(editNeto),
      })
      setEditItem(null)
      await Promise.all([load(), loadNomina()])
    } catch (err: unknown) {
      setEditError(err instanceof Error ? err.message : "No se pudo guardar. Intentá de nuevo.")
    } finally {
      setEditSaving(false)
    }
  }

  const isEmpty =
    !loading && !error && dashboard !== null && dashboard.costos_por_area.length === 0

  const totalEmpleados =
    dashboard?.costos_por_area.reduce((s, a) => s + a.empleados, 0) ?? 0
  const totalPresupuesto =
    dashboard?.costos_por_area.reduce((s, a) => s + a.presupuesto, 0) ?? 0
  const desvioTotal = (dashboard?.total_nomina ?? 0) - totalPresupuesto

  const prevMes = mes === 1 ? 12 : mes - 1
  const prevAnio = mes === 1 ? anio - 1 : anio

  const kpis = dashboard
    ? [
        {
          title: "Costo total nómina",
          value: pesos(dashboard.total_nomina),
          icon: DollarSign,
          description: `Mensual bruto — ${MESES_LARGOS[mes - 1]} ${anio}`,
        },
        {
          title: "Costo promedio / empleado",
          value: pesos(dashboard.costo_promedio),
          icon: Users,
          description: `Sobre ${totalEmpleados} colaboradores`,
        },
        {
          title: "Variación vs mes anterior",
          value: varLabel(dashboard.variacion_porcentual),
          icon: TrendingUp,
          description: `vs ${MESES_CORTOS[prevMes - 1]} ${prevAnio}`,
          accent: (dashboard.variacion_porcentual ?? 1) <= 0,
        },
        {
          title: "Áreas en nómina",
          value: String(dashboard.costos_por_area.length),
          icon: FileText,
          description: `${dashboard.costos_por_area.filter((a) => a.presupuesto > 0).length} con presupuesto cargado`,
        },
      ]
    : []

  const areas = (dashboard?.costos_por_area ?? []).map((a) => ({
    ...a,
    costoPromedio: a.empleados > 0 ? Math.round(a.costo_mensual / a.empleados) : 0,
    pctTotal:
      dashboard && dashboard.total_nomina > 0
        ? ((a.costo_mensual / dashboard.total_nomina) * 100).toFixed(1)
        : "0.0",
    desvio: a.costo_mensual - a.presupuesto,
  }))

  return (
    <div className="space-y-6">
      <PageHeader
        title="Costos de Personal"
        description={`Nómina y presupuesto — ${MESES_LARGOS[mes - 1]} ${anio}`}
        action={
          <div className="flex items-center gap-2">
            <PeriodSelector
              mes={mes}
              anio={anio}
              onChangeMes={setMes}
              onChangeAnio={setAnio}
            />
            {canWrite && (
              <>
                <Button variant="outline" className="min-h-11 gap-1.5" onClick={() => setImportarNominaOpen(true)}>
                  <FileSpreadsheet className="size-4" />
                  Importar CSV
                </Button>
                <Button className="min-h-11 gap-1.5" onClick={() => setNominaOpen(true)}>
                  <Upload className="size-4" />
                  Cargar nómina
                </Button>
              </>
            )}
          </div>
        }
      />

      {loading && <DashboardSkeleton />}

      {error && (
        <ErrorState
          description="No se pudo cargar el dashboard de costos."
          action={load}
        />
      )}

      {isEmpty && (
        <EmptyState
          icon={<DollarSign />}
          title="Sin datos de nómina"
          description={`No hay registros de nómina para ${MESES_LARGOS[mes - 1]} ${anio}. Cargá la nómina del período para ver los costos.`}
          action={
            canWrite ? (
              <Button
                type="button"
                className="mt-1 min-h-11 gap-1.5"
                onClick={() => setNominaOpen(true)}
              >
                <Upload className="size-4" />
                Cargar nómina
              </Button>
            ) : undefined
          }
        />
      )}

      {!loading && !error && !isEmpty && dashboard && (
        <>
          {/* KPIs */}
          <section aria-label="Indicadores de costos">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {kpis.map((kpi) => (
                <KpiCard key={kpi.title} {...kpi} />
              ))}
            </div>
          </section>

          {/* Evolución */}
          <EvolucionChart data={dashboard.evolucion_mensual} />

          {/* Tabla por área */}
          <section
            className="rounded-xl border bg-card p-4 md:p-6"
            aria-label="Costos por área"
          >
            <h2 className="mb-4 text-base font-semibold text-foreground">Costos por área</h2>
            <Table>
              <TableHeader>
                <TableRow>
                  {!empresaActivaId && <TableHead>Empresa</TableHead>}
                  <TableHead>Área</TableHead>
                  <TableHead className="text-right">Empleados</TableHead>
                  <TableHead className="text-right">Costo mensual</TableHead>
                  <TableHead className="text-right">Costo promedio</TableHead>
                  <TableHead className="text-right">% del total</TableHead>
                  <TableHead className="text-right">Presupuesto</TableHead>
                  <TableHead className="text-right">Desvío</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {areas.map((a) => (
                  <TableRow key={`${a.empresa_nombre ?? ""}${a.area_nombre}`}>
                    {!empresaActivaId && (
                      <TableCell className="text-muted-foreground">{a.empresa_nombre ?? "—"}</TableCell>
                    )}
                    <TableCell className="font-medium">{a.area_nombre}</TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {a.empleados}
                    </TableCell>
                    <TableCell className="text-right">{pesos(a.costo_mensual)}</TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {pesos(a.costoPromedio)}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {a.pctTotal}%
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {a.presupuesto > 0 ? pesos(a.presupuesto) : "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      {a.presupuesto > 0 ? (
                        a.desvio > 0 ? (
                          <Badge variant="destructive">+{pesos(a.desvio)}</Badge>
                        ) : (
                          <span className="text-sm text-emerald-600 dark:text-emerald-400">
                            {pesos(a.desvio)}
                          </span>
                        )
                      ) : (
                        <span className="text-sm text-muted-foreground">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
              <TableFooter>
                <TableRow>
                  {!empresaActivaId && <TableCell />}
                  <TableCell className="font-semibold">Total</TableCell>
                  <TableCell className="text-right font-semibold">{totalEmpleados}</TableCell>
                  <TableCell className="text-right font-semibold">
                    {pesos(dashboard.total_nomina)}
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">
                    {totalEmpleados > 0
                      ? pesos(Math.round(dashboard.total_nomina / totalEmpleados))
                      : "—"}
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">100%</TableCell>
                  <TableCell className="text-right font-semibold">
                    {totalPresupuesto > 0 ? pesos(totalPresupuesto) : "—"}
                  </TableCell>
                  <TableCell className="text-right">
                    {totalPresupuesto > 0 ? (
                      desvioTotal > 0 ? (
                        <Badge variant="destructive">+{pesos(desvioTotal)}</Badge>
                      ) : (
                        <span className="text-sm text-emerald-600 dark:text-emerald-400">
                          {pesos(desvioTotal)}
                        </span>
                      )
                    ) : (
                      <span className="text-sm text-muted-foreground">—</span>
                    )}
                  </TableCell>
                </TableRow>
              </TableFooter>
            </Table>
          </section>
        </>
      )}

      {/* Detalle de nómina */}
      {!loading && (
        <section
          className="rounded-xl border bg-card p-4 md:p-6"
          aria-label="Detalle de nómina"
        >
          <div className="mb-4 flex items-center justify-between gap-2">
            <h2 className="text-base font-semibold text-foreground">Detalle de nómina</h2>
            {!nominaListLoading && !nominaListError && nomina.length > 0 && (
              <ExportMenu onExport={(f) => exportarNomina(f, mes, anio)} />
            )}
          </div>
          {nominaListLoading ? (
            <Skeleton className="h-40 rounded-lg" />
          ) : nominaListError ? (
            <ErrorState
              description="No se pudo cargar el detalle de nómina."
              action={loadNomina}
            />
          ) : nomina.length === 0 ? (
            <EmptyState
              icon={<Users />}
              title="Sin registros"
              description={`No hay nómina cargada para ${MESES_LARGOS[mes - 1]} ${anio}.`}
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Empleado</TableHead>
                  {!empresaActivaId && <TableHead>Empresa</TableHead>}
                  <TableHead>Área</TableHead>
                  <TableHead className="text-right">Monto bruto</TableHead>
                  <TableHead className="text-right">Monto neto</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {nomina.map((n) => (
                  <TableRow key={n.id}>
                    <TableCell className="font-medium">{n.empleado_nombre}</TableCell>
                    {!empresaActivaId && (
                      <TableCell className="text-muted-foreground">{n.empresa_nombre ?? "—"}</TableCell>
                    )}
                    <TableCell className="text-muted-foreground">{n.area_nombre}</TableCell>
                    <TableCell className="text-right">{pesos(n.monto_bruto)}</TableCell>
                    <TableCell className="text-right">{pesos(n.monto_neto)}</TableCell>
                    <TableCell className="text-right">
                      {canWrite && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="min-h-9 gap-1"
                          onClick={() => openEdit(n)}
                        >
                          <Pencil className="size-3.5" />
                          Editar
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </section>
      )}

      <NominaModal
        open={nominaOpen}
        onClose={() => setNominaOpen(false)}
        onSuccess={() => {
          setNominaOpen(false)
          load()
          loadNomina()
        }}
      />

      <ImportarNominaCSVModal
        open={importarNominaOpen}
        onClose={() => setImportarNominaOpen(false)}
        onSuccess={() => {
          setImportarNominaOpen(false)
          load()
          loadNomina()
        }}
      />

      <Dialog open={editItem !== null} onOpenChange={(open) => { if (!open) setEditItem(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar nómina — {editItem?.empleado_nombre}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="edit-bruto">Monto bruto</Label>
              <Input
                id="edit-bruto"
                type="number"
                min={0}
                value={editBruto}
                onChange={(e) => setEditBruto(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="edit-neto">Monto neto</Label>
              <Input
                id="edit-neto"
                type="number"
                min={0}
                value={editNeto}
                onChange={(e) => setEditNeto(e.target.value)}
              />
            </div>
            {editError && <p className="text-sm text-destructive">{editError}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditItem(null)} disabled={editSaving}>
              Cancelar
            </Button>
            <Button onClick={saveEdit} disabled={editSaving}>
              {editSaving ? "Guardando…" : "Guardar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

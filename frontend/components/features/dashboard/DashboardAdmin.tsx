"use client"

import { useEffect, useState } from "react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/PageHeader"
import { useCanWrite } from "@/hooks/useCanWrite"
import { resolverAtencion } from "@/services/dashboard"
import { AlertasPanel } from "./AlertasPanel"
import { AtencionPanel } from "./AtencionPanel"
import { buildKpis, cargarDatosAdmin, type DatosAdmin, type KpiCardData } from "./dashboardAdminData"
import { DashboardExtras } from "./DashboardExtras"
import { HeadcountPanel } from "./HeadcountPanel"

function KpiCard({ kpi }: { kpi: KpiCardData }) {
  const Icon = kpi.icon
  return (
    <div className="rounded-xl border bg-card p-4 md:p-5">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-muted-foreground">{kpi.title}</p>
        <span className="shrink-0 rounded-lg bg-primary/10 p-1.5 text-primary">
          <Icon className="size-4" />
        </span>
      </div>
      <p className="mt-3 text-2xl font-bold tracking-tight text-foreground">{kpi.value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{kpi.description}</p>
    </div>
  )
}

function KpiSkeleton() {
  return (
    <div className="grid animate-pulse grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3, 4, 5, 6].map((i) => <div key={i} className="h-28 rounded-xl border bg-muted" />)}
    </div>
  )
}

export function DashboardAdmin() {
  const [datos, setDatos] = useState<DatosAdmin | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [resolviendo, setResolviendo] = useState<string | null>(null)
  // El permiso de RESOLVER es el de EVENTOS, no el del dashboard: resolver una alerta manual
  // escribe un evento de agenda, y el backend gatea con EVENTOS + WRITE. Con el permiso de la
  // pantalla, gerencia_lectura vería un botón que le responde 403.
  const canResolver = useCanWrite("eventos")

  useEffect(() => {
    cargarDatosAdmin()
      .then(setDatos)
      .catch(() => setError("No se pudo cargar el dashboard."))
      .finally(() => setLoading(false))
  }, [])

  async function resolver(eventoId: string) {
    setResolviendo(eventoId)
    try {
      await resolverAtencion(eventoId)
      // La alerta se saca de la lista local en vez de recargar todo: el evento resuelto sale de
      // la ventana de aviso, así que un refetch traería lo mismo menos esta fila — y le
      // agregaría un parpadeo a los nueve KPIs para quitar un renglón.
      setDatos((prev) => prev && {
        ...prev, atencion: prev.atencion.filter((a) => a.evento_id !== eventoId),
      })
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "No se pudo resolver la alerta.")
    } finally {
      setResolviendo(null)
    }
  }

  const data = datos?.dashboard ?? null
  const kpis = data ? buildKpis(data) : []

  return (
    <div className="space-y-6">
      <PageHeader title="Dashboard Ejecutivo" description="Resumen del estado de la organización" />

      {/* KPIs — 1 col mobile / 2 col tablet / 3 col desktop */}
      <section aria-label="Indicadores clave">
        {loading ? (
          <KpiSkeleton />
        ) : error ? (
          <p className="py-8 text-center text-sm text-destructive">{error}</p>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {kpis.map((kpi) => <KpiCard key={kpi.title} kpi={kpi} />)}
          </div>
        )}
      </section>

      {/* Headcount + Alertas — las dos plegables: sus listas crecen con la plantilla.
          🔴 `items-start` (grid estira por defecto): sin él, plegar una card NO le baja el alto
          —se estira a la de su vecina— y el acordeón queda sin efecto, que es lo único que
          hace. Con Headcount abierta en 12 áreas, Alertas plegada quedaba como un rectángulo
          vacío de ~850px con el título arriba. El precio asumido es que con las dos abiertas y
          largos distintos dejan de verse parejas.
          ⚠️ NO se lo pongas a la grilla de KPIs de arriba: esas SÍ necesitan el stretch, porque
          su `description` es de largo variable y sin él las 3 de cada fila quedan desparejas. */}
      {/* 🔴 DOS PANELES DE AVISOS, Y NO SON LO MISMO — se midió, la intersección es CERO.
          "Requiere tu atención" (arriba, ancho completo) es lo accionable sobre PERSONAS:
          ingresos próximos, fines de período de prueba y eventos de agenda en ventana.
          "Alertas activas" (abajo) es la salud del SISTEMA: tablas vacías que dejan un módulo
          inutilizable, campos del padrón sin cargar, y dos derivadas de KPIs.
          Va arriba y solo porque es lo que se hace ESTA semana con gente; lo otro es una deuda
          de carga que se arrastra. Los títulos dicen cuál es cuál para que no se lean como dos
          listas de lo mismo. Ver docs/DEUDA-TECNICA.md: si los bloqueos de módulo son "alerta"
          o son otra cosa lo define Capital Humano en el reestilado del dashboard. */}
      {datos && (
        <>
          {datos.atencionError ? (
            <p className="text-sm text-destructive">
              No se pudo cargar &quot;Requiere tu atención&quot;. El resto del dashboard está al día.
            </p>
          ) : (
            <AtencionPanel
              alertas={datos.atencion}
              canResolver={canResolver}
              resolviendo={resolviendo}
              onResolver={resolver}
            />
          )}
        </>
      )}

      {data && (
        <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
          <HeadcountPanel areas={data.headcount_por_area} />
          <AlertasPanel alertas={data.alertas} />
        </div>
      )}

      {/* KPIs Sesión 5 — distribución + cumpleaños/aniversarios */}
      {data && <DashboardExtras data={data.kpis_extra} />}
    </div>
  )
}

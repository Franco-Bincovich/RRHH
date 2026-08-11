"use client"

import { useCallback, useEffect, useState } from "react"
import { Clock } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { Input } from "@/components/ui/input"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { KPIsHorasPanel } from "@/components/features/horasCliente/KPIsHorasPanel"
import { ClientesColapsables } from "@/components/features/horasCliente/ClientesColapsables"
import { DetalleEmpleadoModal } from "@/components/features/horasCliente/DetalleEmpleadoModal"
import { cargarHorasCliente } from "@/components/features/horasCliente/cargarHorasCliente"
import { exportarHorasPorCliente } from "@/services/horasCliente"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { HorasPorCliente } from "@/types/horasCliente"

/**
 * "Horas por cliente" — solo RRHH. ORQUESTADOR: estado y navegación; los KPIs, el árbol y el
 * detalle viven en `components/features/horasCliente/`, y la carga en `cargarHorasCliente.ts`
 * (testeable sin jsdom).
 *
 * ⚠️ El filtro de EMPRESA no está acá: lo pone el selector del sidebar (header `X-Empresa-Id`),
 * porque esto es una VISTA. Mirar = manda el sidebar; hacer = manda el form. El único "hacer" de
 * esta pantalla es el borrado, que va por id y no necesita empresa.
 */
export default function HorasPorClientePage() {
  const canWrite = useCanWrite()
  const hoy = new Date()
  const [mes, setMes] = useState(hoy.getMonth() + 1)
  const [anio, setAnio] = useState(hoy.getFullYear())
  const [datos, setDatos] = useState<HorasPorCliente | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [detalle, setDetalle] = useState<{ id: string; nombre: string } | null>(null)

  const filtros = { mes, anio }
  const load = useCallback(
    () => cargarHorasCliente({ mes, anio }, { setDatos, setLoading, setError }),
    [mes, anio],
  )
  useEffect(() => { void load() }, [load])

  const filtrosUI = (
    <div className="flex items-center gap-2">
      <Input type="number" min={1} max={12} value={mes} className="w-20"
             aria-label="Mes" onChange={(e) => setMes(Number(e.target.value))} />
      <Input type="number" min={2000} max={2100} value={anio} className="w-24"
             aria-label="Año" onChange={(e) => setAnio(Number(e.target.value))} />
      {/* El MISMO filtro que el listado: el archivo no puede traer filas que no se ven. */}
      <ExportMenu onExport={(formato) => exportarHorasPorCliente(formato, filtros)} />
    </div>
  )

  if (loading) {
    return (
      <div>
        <PageHeader title="Horas por cliente" description="Cargando..." />
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      </div>
    )
  }

  if (error || !datos) {
    return (
      <div>
        <PageHeader title="Horas por cliente" />
        <ErrorState description={error ?? "No se pudieron cargar las horas."} action={load} />
      </div>
    )
  }

  return (
    <div>
      <PageHeader title="Horas por cliente"
                  description={`${datos.kpis.horas_totales} horas cargadas`}
                  action={filtrosUI} />
      {/* 🔴 En todas las demás pantallas el selector de empresa del sidebar filtra; acá no.
          Sin decirlo, un operador que cambia de empresa y ve el mismo número cree que se
          colgó. Lenguaje llano: los usuarios son cuatro personas de RRHH. */}
      <p className="mb-4 rounded-lg border bg-muted/40 px-4 py-2.5 text-sm text-muted-foreground">
        Acá ves las horas completas de cada cliente, sumando todas las empresas. El selector de
        empresa del menú no cambia estos números. Abrí un cliente para ver cuántas horas puso
        cada empresa.
      </p>
      <KPIsHorasPanel kpis={datos.kpis} />
      {datos.clientes.length === 0 ? (
        <EmptyState icon={<Clock />} title="Sin cargas en el período"
                    description="Nadie cargó horas en el mes seleccionado." />
      ) : (
        <ClientesColapsables
          clientes={datos.clientes}
          onVerDetalle={(id, nombre) => setDetalle({ id, nombre })}
        />
      )}
      <DetalleEmpleadoModal
        empleadoId={detalle?.id ?? null}
        empleadoNombre={detalle?.nombre ?? ""}
        filtros={filtros}
        canWrite={canWrite}
        onClose={() => setDetalle(null)}
        onBorrado={load}
      />
    </div>
  )
}
